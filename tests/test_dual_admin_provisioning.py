import sqlite3

import app as desktop_app
from tools.force_admin_login_heal import ensure_admin_accounts


def test_dual_admin_provisioning_preserves_ids_and_sets_requested_roles(tmp_path):
    db_path = tmp_path / "accounts.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE BINARY UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            security_question TEXT NOT NULL DEFAULT '',
            answer_salt TEXT NOT NULL DEFAULT '',
            answer_hash TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    salt, digest = desktop_app.hash_pin("old-customer-password")
    conn.execute(
        """INSERT INTO auth_users
           (id,username,display_name,role,password_salt,password_hash,created_at,updated_at)
           VALUES (7,'Admin','Old name','Admin',?,?, '2026-01-01','2026-01-01')""",
        (salt, digest),
    )
    conn.commit()
    conn.close()

    assert ensure_admin_accounts(db_path, "Shiva@01", "kiran123") == 2
    assert ensure_admin_accounts(db_path, "Shiva@01", "kiran123") == 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = {
            row["username"]: row
            for row in conn.execute(
                "SELECT * FROM auth_users WHERE username IN ('Admin','admin')"
            )
        }
        assert set(rows) == {"Admin", "admin"}
        assert rows["Admin"]["id"] == 7
        assert rows["Admin"]["role"] == "Admin"
        assert rows["admin"]["role"] == "Developer"
        for username, password in (("Admin", "Shiva@01"), ("admin", "kiran123")):
            row = rows[username]
            _, actual = desktop_app.hash_pin(password, row["password_salt"])
            assert actual == row["password_hash"]
        assert conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] == 2
    finally:
        conn.close()


def test_dual_admin_provisioning_requires_both_secrets(tmp_path):
    try:
        ensure_admin_accounts(tmp_path / "missing.db", "Shiva@01", "")
    except RuntimeError as exc:
        assert "Both web administrator" in str(exc)
    else:
        raise AssertionError("Missing developer secret must fail closed")
