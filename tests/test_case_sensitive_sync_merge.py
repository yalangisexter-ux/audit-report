import json
import sqlite3

import app
from database_sync import SyncableSQLiteConnection
import pytest


AUTH_SCHEMA = """
CREATE TABLE auth_users (
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
)
"""


def auth_connection(factory=sqlite3.Connection):
    conn = sqlite3.connect(":memory:", factory=factory)
    conn.row_factory = sqlite3.Row
    conn.execute(AUTH_SCHEMA)
    return conn


def insert_user(conn, username, role, salt, digest, updated_at):
    return conn.execute(
        """INSERT INTO auth_users(
               username, display_name, role, password_salt, password_hash,
               security_question, answer_salt, answer_hash, active, created_at, updated_at
           ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
        (username, username, role, salt, digest, "", "", "", "2026-01-01T00:00:00", updated_at),
    ).lastrowid


def assert_two_admin_identities(conn):
    rows = {
        row["username"]: dict(row)
        for row in conn.execute("SELECT * FROM auth_users ORDER BY username").fetchall()
    }
    assert set(rows) >= {"Admin", "admin"}
    assert rows["Admin"]["role"] == "Admin"
    assert rows["Admin"]["password_salt"] == "customer-salt"
    assert rows["Admin"]["password_hash"] == "customer-hash"
    assert rows["admin"]["role"] == "Developer"
    assert rows["admin"]["password_salt"] == "developer-salt"
    assert rows["admin"]["password_hash"] == "developer-hash"


def test_sqlite_snapshot_merge_preserves_case_distinct_admin_credentials(tmp_path):
    local = auth_connection()
    insert_user(local, "Admin", "Admin", "customer-salt", "customer-hash", "2026-11-05T12:00:00")

    remote_path = tmp_path / "remote-customer.db"
    remote = sqlite3.connect(remote_path)
    remote.execute(AUTH_SCHEMA)
    insert_user(remote, "Admin", "Admin", "stale-customer-salt", "stale-customer-hash", "2026-11-04T12:00:00")
    insert_user(remote, "admin", "Developer", "developer-salt", "developer-hash", "2026-11-05T11:00:00")
    remote.commit()
    remote.close()

    stats = app.merge_remote_database_snapshot(local, remote_path)

    assert stats["users"] == 1
    assert_two_admin_identities(local)
    assert local.execute("SELECT id FROM auth_users WHERE username='Admin' COLLATE BINARY").fetchone()[0] == 1
    assert local.in_transaction  # A nested merge must not commit the caller's pending Admin insert.
    local.commit()
    local.close()


def json_merge_connection(factory=sqlite3.Connection):
    conn = auth_connection(factory=factory)
    conn.executescript("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code TEXT, name TEXT, department TEXT DEFAULT '',
            designation TEXT DEFAULT '', phone TEXT DEFAULT '', email TEXT DEFAULT ''
        );
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, work_date TEXT, check_in TEXT DEFAULT '',
            check_out TEXT DEFAULT '', attendance_status TEXT DEFAULT 'Unmarked',
            attendance_note TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, task_date TEXT, title TEXT, department TEXT DEFAULT '',
            details TEXT DEFAULT '', due_time TEXT DEFAULT '', priority TEXT DEFAULT 'Normal',
            status TEXT DEFAULT 'Not started', progress INTEGER DEFAULT 0,
            proof_url TEXT DEFAULT '', proof_note TEXT DEFAULT '', submitted_at TEXT DEFAULT '',
            manager_note TEXT DEFAULT '', expose_link INTEGER DEFAULT 0,
            target_qty TEXT DEFAULT '', actual_qty TEXT DEFAULT '', next_action TEXT DEFAULT '',
            custom_values TEXT DEFAULT '', created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE holidays (
            holiday_date TEXT PRIMARY KEY, holiday_name TEXT, created_at TEXT
        );
    """)
    return conn


def test_json_snapshot_merge_preserves_case_distinct_admin_credentials():
    local = json_merge_connection()
    insert_user(local, "Admin", "Admin", "customer-salt", "customer-hash", "2026-11-05T12:00:00")
    payload = {
        "auth_users": [
            {
                "username": "Admin", "display_name": "Customer Administrator", "role": "Admin",
                "password_salt": "stale-customer-salt", "password_hash": "stale-customer-hash",
                "active": 1, "updated_at": "2026-11-04T12:00:00",
            },
            {
                "username": "admin", "display_name": "Developer Administrator", "role": "Developer",
                "password_salt": "developer-salt", "password_hash": "developer-hash",
                "active": 1, "updated_at": "2026-11-05T11:00:00",
            },
        ],
        "employees": [], "attendance": [], "tasks": [], "holidays": {},
    }

    stats = app.merge_remote_json_snapshot(local, json.dumps(payload))

    assert stats["users"] == 1
    assert_two_admin_identities(local)
    assert local.in_transaction  # A nested merge must not commit the caller's pending Admin insert.
    local.commit()
    local.close()


def test_auth_recovery_lookup_is_exact_when_admin_accounts_are_case_distinct():
    conn = auth_connection()
    customer_id = insert_user(conn, "Admin", "Admin", "customer-salt", "customer-hash", "2026-11-05T12:00:00")
    developer_id = insert_user(conn, "admin", "Developer", "developer-salt", "developer-hash", "2026-11-05T12:00:00")
    try:
        assert app.find_active_auth_user(conn, "Admin")["id"] == customer_id
        assert app.find_active_auth_user(conn, "admin")["id"] == developer_id
        assert app.find_active_auth_user(conn, "AdMiN") is None
    finally:
        conn.close()


def test_auth_recovery_lookup_allows_case_variant_only_when_unambiguous():
    conn = auth_connection()
    account_id = insert_user(conn, "Admin", "Admin", "customer-salt", "customer-hash", "2026-11-05T12:00:00")
    try:
        assert app.find_active_auth_user(conn, "admin")["id"] == account_id
    finally:
        conn.close()


def test_json_snapshot_merge_failure_rolls_back_only_its_nested_savepoint():
    local = json_merge_connection()
    insert_user(local, "Admin", "Admin", "customer-salt", "customer-hash", "2026-11-05T12:00:00")
    remote_developer = {
        "username": "admin",
        "display_name": "Developer Administrator",
        "role": "Developer",
        "password_salt": "developer-salt",
        "password_hash": "developer-hash",
        "active": 1,
        "created_at": "2026-11-05T11:00:00",
        "updated_at": "2026-11-05T11:00:00",
    }
    payload = {
        "auth_users": [remote_developer, dict(remote_developer)],
        "employees": [],
        "attendance": [],
        "tasks": [],
        "holidays": {},
    }
    try:
        with pytest.raises(sqlite3.IntegrityError):
            app.merge_remote_json_snapshot(local, payload)
        assert local.in_transaction
        usernames = [
            row[0] for row in local.execute("SELECT username FROM auth_users ORDER BY username").fetchall()
        ]
        assert usernames == ["Admin"]
        local.commit()
    finally:
        local.close()


def test_sqlite_snapshot_merge_triggers_sync_commit_callback_when_it_owns_transaction(tmp_path):
    local = auth_connection(factory=SyncableSQLiteConnection)
    insert_user(local, "Admin", "Admin", "customer-salt", "customer-hash", "2026-11-05T12:00:00")
    local.commit()
    callbacks = []
    local.set_commit_callback(lambda: callbacks.append("committed"))

    remote_path = tmp_path / "callback-remote.db"
    remote = sqlite3.connect(remote_path)
    remote.execute(AUTH_SCHEMA)
    insert_user(remote, "admin", "Developer", "developer-salt", "developer-hash", "2026-11-05T13:00:00")
    remote.commit()
    remote.close()
    try:
        stats = app.merge_remote_database_snapshot(local, remote_path)
        assert stats["users"] == 1
        assert callbacks == ["committed"]
        assert not local.in_transaction
    finally:
        local.close()


def test_json_snapshot_merge_triggers_sync_commit_callback_when_it_owns_transaction():
    local = json_merge_connection(factory=SyncableSQLiteConnection)
    insert_user(local, "Admin", "Admin", "customer-salt", "customer-hash", "2026-11-05T12:00:00")
    local.commit()
    callbacks = []
    local.set_commit_callback(lambda: callbacks.append("committed"))
    payload = {
        "auth_users": [{
            "username": "admin",
            "display_name": "Developer Administrator",
            "role": "Developer",
            "password_salt": "developer-salt",
            "password_hash": "developer-hash",
            "active": 1,
            "created_at": "2026-11-05T13:00:00",
            "updated_at": "2026-11-05T13:00:00",
        }],
        "employees": [],
        "attendance": [],
        "tasks": [],
        "holidays": {},
    }
    try:
        stats = app.merge_remote_json_snapshot(local, payload)
        assert stats["users"] == 1
        assert callbacks == ["committed"]
        assert not local.in_transaction
    finally:
        local.close()
