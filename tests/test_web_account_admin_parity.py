"""Regression tests for desktop-equivalent web account administration."""
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

import api_server as api
import app as desktop_app


def setup_account_client(tmp_path, monkeypatch, current_user_id=1, standalone=False):
    monkeypatch.setenv("WEB_STANDALONE", "1" if standalone else "0")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    db_path = tmp_path / "account-admin.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL COLLATE BINARY UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            security_question TEXT NOT NULL,
            answer_salt TEXT NOT NULL,
            answer_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL
        );
        CREATE TABLE web_auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        """
    )
    now = datetime.now().isoformat(timespec="seconds")
    users = [
        (1, "owner", "Account Owner", "Admin", 1),
        (2, "staff", "Staff Account", "Staff", 1),
        (3, "developer", "Developer Account", "Developer", 1),
    ]
    for user_id, username, display_name, role, active in users:
        salt, digest = desktop_app.hash_pin("OriginalPass123")
        answer_salt, answer_hash = desktop_app.hash_pin("recovery answer")
        conn.execute(
            """INSERT INTO auth_users(
                   id,username,display_name,role,password_salt,password_hash,
                   security_question,answer_salt,answer_hash,active,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                user_id, username, display_name, role, salt, digest,
                desktop_app.SECURITY_QUESTIONS[0], answer_salt, answer_hash,
                active, now, now,
            ),
        )

    admin_token = secrets.token_urlsafe(24)
    staff_token = secrets.token_urlsafe(24)
    tokens = {1: admin_token, 2: staff_token}
    if standalone:
        expires = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")
        for user_id, token in tokens.items():
            conn.execute(
                "INSERT INTO web_auth_sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                (hashlib.sha256(token.encode("utf-8")).hexdigest(), user_id, now, expires),
            )
    conn.commit()
    conn.close()

    def override_get_db():
        db = sqlite3.connect(str(db_path), check_same_thread=False)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db
    if not standalone:
        api.ACTIVE_SESSIONS[admin_token] = {
            "id": 1, "username": "owner", "display_name": "Account Owner", "role": "Admin"
        }
        api.ACTIVE_SESSIONS[staff_token] = {
            "id": 2, "username": "staff", "display_name": "Staff Account", "role": "Staff"
        }
    client = TestClient(api.app)
    headers = {"Authorization": "Bearer " + (admin_token if current_user_id == 1 else staff_token)}

    def cleanup():
        api.app.dependency_overrides.pop(api.get_db, None)
        api.ACTIVE_SESSIONS.pop(admin_token, None)
        api.ACTIVE_SESSIONS.pop(staff_token, None)

    return client, headers, db_path, cleanup, admin_token, staff_token


def test_admin_creates_active_account_with_desktop_pbkdf2_hashes(tmp_path, monkeypatch):
    client, headers, db_path, cleanup, *_ = setup_account_client(tmp_path, monkeypatch)
    try:
        password = "NewCoachPass456"
        answer = "  Blue   Mountain  "
        response = client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "username": "coach",
                "display_name": "New Coach",
                "role": "HR",
                "password": password,
                "security_question": desktop_app.SECURITY_QUESTIONS[1],
                "security_answer": answer,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["active"] is True
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT username,role,active,password_salt,password_hash,answer_salt,answer_hash FROM auth_users WHERE username='coach'"
            ).fetchone()
            assert row[:3] == ("coach", "HR", 1)
            assert desktop_app.hash_pin(password, row[3])[1] == row[4]
            normalized = desktop_app.normalized_answer(answer)
            assert desktop_app.hash_pin(normalized, row[5])[1] == row[6]
            assert conn.execute(
                "SELECT action,details FROM audit_log ORDER BY id DESC LIMIT 1"
            ).fetchone() == ("User account created", "coach (HR)")
        finally:
            conn.close()

        # Usernames are exact-case identities, matching the desktop database:
        # "STAFF" and "staff" are distinct accounts.
        case_variant = client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "username": "STAFF",
                "display_name": "Uppercase Staff",
                "role": "Staff",
                "password": password,
                "security_question": desktop_app.SECURITY_QUESTIONS[0],
                "security_answer": "Answer",
            },
        )
        assert case_variant.status_code == 200, case_variant.text

        # An exact duplicate must still be rejected.
        duplicate = client.post(
            "/api/auth/users",
            headers=headers,
            json={
                "username": "STAFF",
                "display_name": "Duplicate",
                "role": "Staff",
                "password": password,
                "security_question": desktop_app.SECURITY_QUESTIONS[0],
                "security_answer": "Answer",
            },
        )
        assert duplicate.status_code == 409
    finally:
        cleanup()


def test_admin_changes_role_without_modifying_existing_password_hash(tmp_path, monkeypatch):
    client, headers, db_path, cleanup, *_ = setup_account_client(tmp_path, monkeypatch)
    try:
        conn = sqlite3.connect(db_path)
        before = conn.execute(
            "SELECT password_salt,password_hash FROM auth_users WHERE id=2"
        ).fetchone()
        conn.close()
        response = client.patch("/api/auth/users/2/role", headers=headers, json={"role": "HR"})
        assert response.status_code == 200, response.text
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT role,password_salt,password_hash FROM auth_users WHERE id=2"
            ).fetchone()
            assert row == ("HR", before[0], before[1])
            assert conn.execute(
                "SELECT action,details FROM audit_log ORDER BY id DESC LIMIT 1"
            ).fetchone() == ("User role changed", "staff -> HR")
        finally:
            conn.close()
    finally:
        cleanup()


def test_last_active_admin_cannot_be_demoted(tmp_path, monkeypatch):
    client, headers, db_path, cleanup, *_ = setup_account_client(tmp_path, monkeypatch)
    try:
        response = client.patch("/api/auth/users/1/role", headers=headers, json={"role": "Staff"})
        assert response.status_code == 409
        conn = sqlite3.connect(db_path)
        try:
            assert conn.execute("SELECT role FROM auth_users WHERE id=1").fetchone()[0] == "Admin"
        finally:
            conn.close()
    finally:
        cleanup()


def test_admin_password_reset_uses_pbkdf2_and_invalidates_target_session(tmp_path, monkeypatch):
    client, headers, db_path, cleanup, _, staff_token = setup_account_client(tmp_path, monkeypatch)
    try:
        new_password = "ResetCoachPass789"
        response = client.post(
            "/api/auth/users/2/password-reset",
            headers=headers,
            json={"new_password": new_password},
        )
        assert response.status_code == 200, response.text
        assert staff_token not in api.ACTIVE_SESSIONS
        conn = sqlite3.connect(db_path)
        try:
            salt, digest = conn.execute(
                "SELECT password_salt,password_hash FROM auth_users WHERE id=2"
            ).fetchone()
            assert desktop_app.hash_pin(new_password, salt)[1] == digest
            assert conn.execute(
                "SELECT action,details FROM audit_log ORDER BY id DESC LIMIT 1"
            ).fetchone() == ("User password reset by admin", "staff")
        finally:
            conn.close()
    finally:
        cleanup()


def test_staff_cannot_create_accounts_change_roles_or_reset_passwords(tmp_path, monkeypatch):
    client, _, db_path, cleanup, _, staff_token = setup_account_client(tmp_path, monkeypatch, current_user_id=2)
    headers = {"Authorization": "Bearer " + staff_token}
    try:
        payload = {
            "username": "blocked",
            "display_name": "Blocked User",
            "role": "Staff",
            "password": "StrongPass456",
            "security_question": desktop_app.SECURITY_QUESTIONS[0],
            "security_answer": "Answer",
        }
        assert client.post("/api/auth/users", headers=headers, json=payload).status_code == 403
        assert client.patch("/api/auth/users/3/role", headers=headers, json={"role": "HR"}).status_code == 403
        assert client.post(
            "/api/auth/users/2/password-reset",
            headers=headers,
            json={"new_password": "AnotherPass456"},
        ).status_code == 403
        conn = sqlite3.connect(db_path)
        try:
            assert conn.execute("SELECT COUNT(*) FROM auth_users WHERE username='blocked'").fetchone()[0] == 0
        finally:
            conn.close()
    finally:
        cleanup()


def test_customer_admin_cannot_modify_or_reset_developer_account(tmp_path, monkeypatch):
    client, headers, db_path, cleanup, *_ = setup_account_client(tmp_path, monkeypatch)
    try:
        role = client.patch("/api/auth/users/3/role", headers=headers, json={"role": "Staff"})
        password = client.post(
            "/api/auth/users/3/password-reset",
            headers=headers,
            json={"new_password": "ChangedDeveloperPass789"},
        )
        assert role.status_code == 403
        assert password.status_code == 403
        conn = sqlite3.connect(db_path)
        try:
            assert conn.execute("SELECT role FROM auth_users WHERE id=3").fetchone()[0] == "Developer"
        finally:
            conn.close()
    finally:
        cleanup()


def test_standalone_role_change_invalidates_persistent_target_sessions(tmp_path, monkeypatch):
    client, headers, db_path, cleanup, _, staff_token = setup_account_client(
        tmp_path, monkeypatch, standalone=True
    )
    try:
        response = client.patch("/api/auth/users/2/role", headers=headers, json={"role": "HR"})
        assert response.status_code == 200, response.text
        conn = sqlite3.connect(db_path)
        try:
            target_sessions = conn.execute(
                "SELECT COUNT(*) FROM web_auth_sessions WHERE user_id=2"
            ).fetchone()[0]
            assert target_sessions == 0
            assert conn.execute("SELECT role FROM auth_users WHERE id=2").fetchone()[0] == "HR"
        finally:
            conn.close()
    finally:
        cleanup()


def test_managed_accounts_allow_case_distinct_customer_and_developer_admins(tmp_path, monkeypatch):
    client, headers, db_path, cleanup, *_ = setup_account_client(tmp_path, monkeypatch)
    developer_token = secrets.token_urlsafe(24)
    api.ACTIVE_SESSIONS[developer_token] = {
        "id": 3,
        "username": "developer",
        "display_name": "Developer Account",
        "role": "Developer",
    }
    developer_headers = {"Authorization": "Bearer " + developer_token}
    created_tokens = []
    customer_password = "CustomerAdmin123"
    developer_password = "DeveloperAdmin123"

    def account_payload(username, display_name, role, password):
        return {
            "username": username,
            "display_name": display_name,
            "role": role,
            "password": password,
            "security_question": desktop_app.SECURITY_QUESTIONS[0],
            "security_answer": "Recovery answer",
        }

    try:
        customer = client.post(
            "/api/auth/users",
            headers=headers,
            json=account_payload("Admin", "Customer Administrator", "Admin", customer_password),
        )
        assert customer.status_code == 200, customer.text

        developer = client.post(
            "/api/auth/users",
            headers=developer_headers,
            json=account_payload("admin", "Developer Administrator", "Developer", developer_password),
        )
        assert developer.status_code == 200, developer.text

        duplicate = client.post(
            "/api/auth/users",
            headers=headers,
            json=account_payload("Admin", "Duplicate Customer", "Staff", "DuplicatePass123"),
        )
        assert duplicate.status_code == 409

        customer_login = client.post(
            "/api/auth/login",
            json={"username": "Admin", "password": customer_password},
        )
        developer_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": developer_password},
        )
        assert customer_login.status_code == 200, customer_login.text
        assert developer_login.status_code == 200, developer_login.text
        assert customer_login.json()["user"]["role"] == "Admin"
        assert developer_login.json()["user"]["role"] == "Developer"
        created_tokens.extend([customer_login.json()["token"], developer_login.json()["token"]])

        conn = sqlite3.connect(db_path)
        try:
            rows = {
                row[0]: row[1:]
                for row in conn.execute(
                    "SELECT username,role,password_salt,password_hash FROM auth_users "
                    "WHERE username IN ('Admin','admin')"
                ).fetchall()
            }
            assert rows["Admin"][0] == "Admin"
            assert desktop_app.hash_pin(customer_password, rows["Admin"][1])[1] == rows["Admin"][2]
            assert rows["admin"][0] == "Developer"
            assert desktop_app.hash_pin(developer_password, rows["admin"][1])[1] == rows["admin"][2]
        finally:
            conn.close()
    finally:
        for token in created_tokens:
            api.ACTIVE_SESSIONS.pop(token, None)
        api.ACTIVE_SESSIONS.pop(developer_token, None)
        cleanup()


def test_public_registration_allows_case_distinct_admin_and_blocks_exact_duplicate(tmp_path, monkeypatch):
    client, headers, db_path, cleanup, *_ = setup_account_client(tmp_path, monkeypatch)
    customer_password = "CustomerAdmin123"
    registration_password = "PendingCoach123"
    now = datetime.now().isoformat(timespec="seconds")
    customer_salt, customer_hash = desktop_app.hash_pin(customer_password)
    answer_salt, answer_hash = desktop_app.hash_pin("Customer recovery answer")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO auth_users(
                   username,display_name,role,password_salt,password_hash,
                   security_question,answer_salt,answer_hash,active,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
            (
                "Admin", "Customer Administrator", "Admin", customer_salt, customer_hash,
                desktop_app.SECURITY_QUESTIONS[0], answer_salt, answer_hash, now, now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    payload = {
        "username": "admin",
        "display_name": "Pending Coach",
        "password": registration_password,
        "security_question": desktop_app.SECURITY_QUESTIONS[1],
        "security_answer": "Coach recovery answer",
    }
    created_tokens = []
    try:
        registered = client.post("/api/auth/register", json=payload)
        assert registered.status_code == 200, registered.text
        assert registered.json()["pending_approval"] is True

        duplicate = client.post("/api/auth/register", json=payload)
        assert duplicate.status_code == 409

        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT id,active FROM auth_users WHERE username='admin' COLLATE BINARY"
            ).fetchone()
            assert row is not None and row[1] == 0
        finally:
            conn.close()

        activated = client.patch(
            f"/api/auth/users/{row[0]}/active",
            headers=headers,
            json={"active": True},
        )
        assert activated.status_code == 200, activated.text

        customer_login = client.post(
            "/api/auth/login",
            json={"username": "Admin", "password": customer_password},
        )
        registered_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": registration_password},
        )
        assert customer_login.status_code == 200, customer_login.text
        assert registered_login.status_code == 200, registered_login.text
        assert customer_login.json()["user"]["role"] == "Admin"
        assert registered_login.json()["user"]["role"] == "Staff"
        created_tokens.extend([customer_login.json()["token"], registered_login.json()["token"]])
    finally:
        for token in created_tokens:
            api.ACTIVE_SESSIONS.pop(token, None)
        cleanup()

def test_customer_scrape_job_status_is_private_to_creator(tmp_path, monkeypatch):
    import web_parity_routes

    client, admin_headers, _, cleanup, _, staff_token = setup_account_client(tmp_path, monkeypatch)
    staff_headers = {"Authorization": "Bearer " + staff_token}
    submitted = []
    monkeypatch.setattr(
        web_parity_routes._pool,
        "submit",
        lambda function, *args: submitted.append((function, args)),
    )
    job_id = None
    try:
        started = client.post(
            "/api/customers/scrape",
            headers=admin_headers,
            json={"state": "Andhra Pradesh", "query": "sports nutrition", "max_results": 3},
        )
        assert started.status_code == 200, started.text
        job_id = started.json()["job_id"]
        assert len(submitted) == 1

        own_status = client.get(f"/api/customers/scrape/{job_id}", headers=admin_headers)
        assert own_status.status_code == 200, own_status.text
        assert own_status.json()["query"] == "sports nutrition"
        assert "owner_key" not in own_status.json()
        assert "created_at" not in own_status.json()

        other_status = client.get(f"/api/customers/scrape/{job_id}", headers=staff_headers)
        assert other_status.status_code == 404
    finally:
        if job_id:
            with web_parity_routes._jobs_lock:
                web_parity_routes._jobs.pop(job_id, None)
        cleanup()


def test_scrape_job_pruning_expires_finished_jobs_but_keeps_running_jobs():
    import web_parity_routes

    with web_parity_routes._jobs_lock:
        original = dict(web_parity_routes._jobs)
        try:
            web_parity_routes._jobs.clear()
            web_parity_routes._jobs.update({
                "expired": {"id": "expired", "status": "completed", "created_at": 0},
                "recent": {"id": "recent", "status": "failed", "created_at": 100},
                "active": {"id": "active", "status": "running", "created_at": 0},
            })
            web_parity_routes._prune_scrape_jobs_locked(
                now=web_parity_routes._SCRAPE_JOB_TTL_SECONDS + 101
            )
            assert "expired" not in web_parity_routes._jobs
            assert "recent" in web_parity_routes._jobs
            assert "active" in web_parity_routes._jobs
        finally:
            web_parity_routes._jobs.clear()
            web_parity_routes._jobs.update(original)


def test_scrape_owner_fallback_keeps_case_sensitive_account_names():
    import web_parity_routes

    assert web_parity_routes._scrape_owner_key({"username": "Admin"}) != (
        web_parity_routes._scrape_owner_key({"username": "admin"})
    )
