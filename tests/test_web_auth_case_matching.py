import sqlite3

import app as desktop_app
from web_auth_shim import _find_active_login_user


def make_auth_db(accounts):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE auth_users(
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL COLLATE BINARY UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )"""
    )
    for username, password in accounts:
        salt, digest = desktop_app.hash_pin(password)
        conn.execute(
            "INSERT INTO auth_users(username,password_salt,password_hash,active) VALUES(?,?,?,1)",
            (username, salt, digest),
        )
    return conn


def test_login_accepts_case_variant_when_only_one_account_matches():
    conn = make_auth_db([("Admin", "TestPass123")])
    try:
        row = _find_active_login_user(conn, "admin", "TestPass123")
        assert row is not None
        assert row["username"] == "Admin"
    finally:
        conn.close()


def test_login_keeps_case_distinct_admin_accounts_separate():
    conn = make_auth_db([("Admin", "UpperPass123"), ("admin", "LowerPass123")])
    try:
        upper = _find_active_login_user(conn, "Admin", "UpperPass123")
        lower = _find_active_login_user(conn, "admin", "LowerPass123")
        ambiguous = _find_active_login_user(conn, "AdMiN", "UpperPass123")
        assert upper["username"] == "Admin"
        assert lower["username"] == "admin"
        assert ambiguous is None
    finally:
        conn.close()
