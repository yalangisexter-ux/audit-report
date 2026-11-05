"""Regression coverage for the web self-service password-change flow."""
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

import app as desktop_app
import api_server as api


def _password_db(path: Path, *, both_accounts: bool = True):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL COLLATE BINARY,
            display_name TEXT,
            role TEXT,
            password_salt TEXT,
            password_hash TEXT,
            security_question TEXT,
            answer_salt TEXT,
            answer_hash TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE web_auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL
        );
        """
    )
    accounts = [
        (1, "Admin", "Customer Administrator", "Admin", "Customer-Old-Password9"),
    ]
    if both_accounts:
        accounts.append((2, "admin", "Developer Test Account", "Developer", "Developer-Old-Password9"))
    now = datetime.now().isoformat(timespec="seconds")
    for user_id, username, display_name, role, password in accounts:
        salt, digest = desktop_app.hash_pin(password)
        conn.execute(
            """INSERT INTO auth_users
               (id,username,display_name,role,password_salt,password_hash,
                security_question,answer_salt,answer_hash,active,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,1,?,?)""",
            (user_id, username, display_name, role, salt, digest,
             "Test recovery question", "answer-salt", "answer-hash", now, now),
        )
        token = f"session-for-{username}"
        conn.execute(
            "INSERT INTO web_auth_sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
            (hashlib.sha256(token.encode("utf-8")).hexdigest(), user_id, now,
             (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")),
        )
    conn.commit()
    conn.close()


def _client_for_db(path: Path):
    def override_get_db():
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    api.app.dependency_overrides[api.get_db] = override_get_db
    return TestClient(api.app)


def _stored_user(path: Path, username: str):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return dict(conn.execute(
            "SELECT * FROM auth_users WHERE username=? COLLATE BINARY", (username,)
        ).fetchone())
    finally:
        conn.close()


def test_password_change_preserves_case_distinct_accounts_and_invalidates_only_target_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_STANDALONE", "1")
    path = tmp_path / "password-change.db"
    _password_db(path)
    client = _client_for_db(path)
    monkeypatch.setattr(api, "ACTIVE_SESSIONS", {
        "customer-memory-session": {"id": 1, "username": "Admin", "role": "Admin"},
        "developer-memory-session": {"id": 2, "username": "admin", "role": "Developer"},
    })
    try:
        before_customer = _stored_user(path, "Admin")
        before_developer = _stored_user(path, "admin")
        response = client.post(
            "/api/auth/change-password",
            json={
                "username": "Admin",
                "current_password": "Customer-Old-Password9",
                "new_password": "Customer-New-Password9",
            },
        )
        assert response.status_code == 200, response.text
        assert "sign in" in response.json()["message"].lower()

        after_customer = _stored_user(path, "Admin")
        after_developer = _stored_user(path, "admin")
        _, new_digest = desktop_app.hash_pin("Customer-New-Password9", after_customer["password_salt"])
        _, old_digest = desktop_app.hash_pin("Customer-Old-Password9", after_customer["password_salt"])
        assert new_digest == after_customer["password_hash"]
        assert old_digest != after_customer["password_hash"]
        assert after_customer["password_salt"] != before_customer["password_salt"]
        assert after_developer["password_salt"] == before_developer["password_salt"]
        assert after_developer["password_hash"] == before_developer["password_hash"]

        conn = sqlite3.connect(path)
        try:
            assert conn.execute("SELECT user_id FROM web_auth_sessions ORDER BY user_id").fetchall() == [(2,)]
            assert conn.execute(
                "SELECT action,details FROM audit_log"
            ).fetchall() == [("Password changed", "Admin")]
        finally:
            conn.close()
        assert "customer-memory-session" not in api.ACTIVE_SESSIONS
        assert "developer-memory-session" in api.ACTIVE_SESSIONS
    finally:
        api.app.dependency_overrides.pop(api.get_db, None)


def test_password_change_rejects_wrong_current_password_and_weak_new_password_without_mutation(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_STANDALONE", "1")
    path = tmp_path / "password-change-invalid.db"
    _password_db(path, both_accounts=False)
    client = _client_for_db(path)
    try:
        before = _stored_user(path, "Admin")
        wrong = client.post(
            "/api/auth/change-password",
            json={
                "username": "Admin",
                "current_password": "Not-The-Current-Password9",
                "new_password": "Customer-New-Password9",
            },
        )
        assert wrong.status_code == 403
        weak = client.post(
            "/api/auth/change-password",
            json={
                "username": "Admin",
                "current_password": "Customer-Old-Password9",
                "new_password": "short",
            },
        )
        assert weak.status_code == 422
        after = _stored_user(path, "Admin")
        assert after["password_salt"] == before["password_salt"]
        assert after["password_hash"] == before["password_hash"]
        conn = sqlite3.connect(path)
        try:
            assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
        finally:
            conn.close()
    finally:
        api.app.dependency_overrides.pop(api.get_db, None)


def test_password_change_rejects_ambiguous_case_insensitive_account_lookup(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_STANDALONE", "1")
    path = tmp_path / "password-change-ambiguous.db"
    _password_db(path)
    client = _client_for_db(path)
    try:
        response = client.post(
            "/api/auth/change-password",
            json={
                "username": "AdMiN",
                "current_password": "Customer-Old-Password9",
                "new_password": "Customer-New-Password9",
            },
        )
        assert response.status_code == 400
        customer = _stored_user(path, "Admin")
        developer = _stored_user(path, "admin")
        assert customer["password_hash"] == desktop_app.hash_pin(
            "Customer-Old-Password9", customer["password_salt"]
        )[1]
        assert developer["password_hash"] == desktop_app.hash_pin(
            "Developer-Old-Password9", developer["password_salt"]
        )[1]
    finally:
        api.app.dependency_overrides.pop(api.get_db, None)


def test_web_sign_in_exposes_self_service_password_change_form():
    source = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    assert "Change password" in source
    assert "submitPasswordChange" in source
    assert "/auth/change-password" in source
    assert "current_password" in source
    assert "confirm_password" in source
