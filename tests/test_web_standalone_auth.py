"""Regression coverage for standalone web login and protected API sessions."""
import hashlib
import sqlite3
from datetime import datetime

from fastapi.testclient import TestClient

import app as desktop_app
import api_server as api
import web_auth_shim  # registers the production web login route


def test_standalone_login_token_authenticates_protected_api(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_STANDALONE", "1")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    db_path = tmp_path / "standalone-auth.db"
    password = "Customer-Admin-Test-Password"
    salt, password_hash = desktop_app.hash_pin(password)

    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL COLLATE BINARY,
            display_name TEXT,
            role TEXT,
            password_salt TEXT,
            password_hash TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE web_auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """INSERT INTO auth_users
           (id, username, display_name, role, password_salt, password_hash, active)
           VALUES (1, 'Admin', 'Customer Administrator', 'Admin', ?, ?, 1)""",
        (salt, password_hash),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(desktop_app, "DB_PATH", db_path)
    monkeypatch.setattr(web_auth_shim, "_ensure_bootstrap_admin", lambda _path: None)

    def override_get_db():
        db = sqlite3.connect(db_path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    previous_sessions = dict(api.ACTIVE_SESSIONS)
    api.app.dependency_overrides[api.get_db] = override_get_db
    try:
        client = TestClient(api.app)
        login = client.post(
            "/api/auth/login",
            json={"username": "Admin", "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["token"]
        assert token

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text
        assert me.json()["user"]["username"] == "Admin"
        assert me.json()["user"]["role"] == "Admin"

        stored = sqlite3.connect(db_path)
        try:
            assert stored.execute("SELECT COUNT(*) FROM web_auth_sessions").fetchone()[0] == 1
        finally:
            stored.close()
    finally:
        api.ACTIVE_SESSIONS.clear()
        api.ACTIVE_SESSIONS.update(previous_sessions)
        api.app.dependency_overrides.pop(api.get_db, None)


def test_standalone_setup_is_blocked_without_verified_empty_snapshot(tmp_path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setenv("WEB_STANDALONE", "1")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_ALLOW_FIRST_ADMIN_SETUP", "1")
    monkeypatch.setattr(
        api,
        "WEB_SYNC_MANAGER",
        SimpleNamespace(configured=False, last_pull={"ok": False, "auth_users": 0}),
    )
    db_path = tmp_path / "standalone-setup.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY, username TEXT, display_name TEXT, role TEXT,
            password_salt TEXT, password_hash TEXT, security_question TEXT,
            answer_salt TEXT, answer_hash TEXT, active INTEGER, created_at TEXT, updated_at TEXT
        )"""
    )
    conn.commit()
    conn.close()

    def override_get_db():
        db = sqlite3.connect(db_path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db
    try:
        client = TestClient(api.app)
        response = client.post(
            "/api/auth/setup",
            json={
                "username": "Admin",
                "display_name": "Administrator",
                "password": "New-Password-For-Test",
                "security_question": "Test question",
                "security_answer": "Test answer",
            },
        )
        assert response.status_code == 403, response.text
        stored = sqlite3.connect(db_path)
        try:
            assert stored.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] == 0
        finally:
            stored.close()
    finally:
        api.app.dependency_overrides.pop(api.get_db, None)



def test_standalone_requires_a_session_even_when_login_flag_is_disabled(tmp_path, monkeypatch):
    """Standalone deployments must never inherit the legacy first-user fallback."""
    monkeypatch.setenv("WEB_STANDALONE", "1")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "0")
    db_path = tmp_path / "standalone-fail-closed.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            display_name TEXT,
            role TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE web_auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL
        );
        INSERT INTO auth_users(id, username, display_name, role, active)
        VALUES (1, 'Admin', 'Customer Administrator', 'Admin', 1);
        """
    )
    conn.commit()
    conn.close()

    def override_get_db():
        db = sqlite3.connect(db_path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db
    try:
        client = TestClient(api.app)
        assert client.get("/api/auth/me").status_code == 401
        invalid = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-standalone-token"},
        )
        assert invalid.status_code == 401
    finally:
        api.app.dependency_overrides.pop(api.get_db, None)



def test_standalone_login_keeps_customer_and_developer_admin_accounts_distinct(tmp_path, monkeypatch):
    """Exact-case Admin/admin accounts must authenticate as separate identities."""
    monkeypatch.setenv("WEB_STANDALONE", "1")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "0")
    db_path = tmp_path / "standalone-admin-identities.db"

    customer_password = "Customer-Admin-Test-Password"
    developer_password = "Developer-Admin-Test-Password"
    customer_salt, customer_hash = desktop_app.hash_pin(customer_password)
    developer_salt, developer_hash = desktop_app.hash_pin(developer_password)

    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL COLLATE BINARY UNIQUE,
            display_name TEXT,
            role TEXT,
            password_salt TEXT,
            password_hash TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE web_auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        """
    )
    conn.executemany(
        """INSERT INTO auth_users
           (id, username, display_name, role, password_salt, password_hash, active)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        [
            (1, "Admin", "Customer Administrator", "Admin", customer_salt, customer_hash),
            (2, "admin", "Developer (Test Mode)", "Developer", developer_salt, developer_hash),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(desktop_app, "DB_PATH", db_path)
    monkeypatch.setattr(web_auth_shim, "_ensure_bootstrap_admin", lambda _path: None)


    def override_get_db():
        db = sqlite3.connect(db_path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    previous_sessions = dict(api.ACTIVE_SESSIONS)
    api.app.dependency_overrides[api.get_db] = override_get_db
    try:
        client = TestClient(api.app)
        identities = [
            ("Admin", customer_password, 1, "Admin"),
            ("admin", developer_password, 2, "Developer"),
        ]
        tokens = {}
        for username, password, user_id, role in identities:
            login = client.post(
                "/api/auth/login",
                json={"username": username, "password": password},
            )
            assert login.status_code == 200, login.text
            token = login.json()["token"]
            assert token
            tokens[username] = token

            me = client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me.status_code == 200, me.text
            assert me.json()["user"]["id"] == user_id
            assert me.json()["user"]["username"] == username
            assert me.json()["user"]["role"] == role

        assert tokens["Admin"] != tokens["admin"]
        assert client.post(
            "/api/auth/login",
            json={"username": "ADMIN", "password": customer_password},
        ).status_code == 401
        assert client.post(
            "/api/auth/login",
            json={"username": "admin", "password": customer_password},
        ).status_code == 401

        # Persistent sessions must resolve to the same exact-case account after
        # the process-local cache is discarded, without rewriting credentials.
        api.ACTIVE_SESSIONS.clear()
        for username, password, user_id, role in identities:
            me = client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {tokens[username]}"},
            )
            assert me.status_code == 200, me.text
            assert me.json()["user"]["id"] == user_id
            assert me.json()["user"]["username"] == username
            assert me.json()["user"]["role"] == role

        stored = sqlite3.connect(db_path)
        try:
            accounts = stored.execute(
                "SELECT id,username,password_salt,password_hash FROM auth_users ORDER BY id"
            ).fetchall()
            assert accounts == [
                (1, "Admin", customer_salt, customer_hash),
                (2, "admin", developer_salt, developer_hash),
            ]
            sessions = stored.execute(
                "SELECT token_hash,user_id FROM web_auth_sessions ORDER BY user_id"
            ).fetchall()
            assert sessions == [
                (hashlib.sha256(tokens["Admin"].encode("utf-8")).hexdigest(), 1),
                (hashlib.sha256(tokens["admin"].encode("utf-8")).hexdigest(), 2),
            ]
            assert all(token not in {row[0] for row in sessions} for token in tokens.values())
        finally:
            stored.close()
    finally:
        api.ACTIVE_SESSIONS.clear()
        api.ACTIVE_SESSIONS.update(previous_sessions)
        api.app.dependency_overrides.pop(api.get_db, None)
