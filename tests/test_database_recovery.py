import sqlite3
from pathlib import Path

import database_recovery


def make_customer_db(path: Path, employees=1, tasks=2):
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE auth_users(id INTEGER PRIMARY KEY, username TEXT);
        CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT);
        CREATE TABLE attendance(id INTEGER PRIMARY KEY, status TEXT);
    """)
    conn.executemany("INSERT INTO auth_users VALUES(?,?)", [(1, "Admin"), (2, "admin")])
    conn.executemany("INSERT INTO employees VALUES(?,?)", [(i + 1, f"Employee {i + 1}") for i in range(employees)])
    conn.executemany("INSERT INTO tasks VALUES(?,?)", [(i + 1, f"Task {i + 1}") for i in range(tasks)])
    conn.commit()
    conn.close()


def test_recovery_imports_valid_customer_db_before_startup(tmp_path, monkeypatch):
    source_root = tmp_path / "external-drive"
    source = source_root / "Customer" / "EmployeeAuditManager" / "employee_audit.db"
    source.parent.mkdir(parents=True)
    make_customer_db(source, employees=4, tasks=9)
    target = tmp_path / "new-profile" / "EmployeeAuditManager" / "employee_audit.db"
    monkeypatch.setattr(database_recovery, "_drives", lambda: [source_root])

    result = database_recovery.recover_database_before_startup(target)

    assert result["status"] == "recovered"
    conn = sqlite3.connect(target)
    try:
        assert conn.execute("SELECT username FROM auth_users ORDER BY id").fetchall() == [("Admin",), ("admin",)]
        assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 9
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()


def test_recovery_never_replaces_populated_current_database(tmp_path, monkeypatch):
    root = tmp_path / "external-drive"
    source = root / "old" / "employee_audit.db"
    source.parent.mkdir(parents=True)
    make_customer_db(source, employees=10, tasks=20)
    target = tmp_path / "current" / "employee_audit.db"
    target.parent.mkdir(parents=True)
    make_customer_db(target, employees=1, tasks=1)
    monkeypatch.setattr(database_recovery, "_drives", lambda: [root])

    result = database_recovery.recover_database_before_startup(target)

    assert result["status"] == "existing_database_kept"
    conn = sqlite3.connect(target)
    try:
        assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
    finally:
        conn.close()


def test_recovery_refuses_ambiguous_equal_candidates(tmp_path, monkeypatch):
    root = tmp_path / "external-drive"
    for name in ("one", "two"):
        path = root / name / "employee_audit.db"
        path.parent.mkdir(parents=True)
        make_customer_db(path, employees=2, tasks=3)
    target = tmp_path / "new" / "employee_audit.db"
    monkeypatch.setattr(database_recovery, "_drives", lambda: [root])

    try:
        database_recovery.recover_database_before_startup(target)
    except RuntimeError as exc:
        assert "Multiple equally complete" in str(exc)
    else:
        raise AssertionError("Ambiguous customer databases must not be selected silently")
    assert not target.exists()

def test_recovery_restores_business_records_and_preserves_new_local_accounts(tmp_path, monkeypatch):
    root = tmp_path / "external-drive"
    source = root / "old" / "employee_audit.db"
    source.parent.mkdir(parents=True)
    make_customer_db(source, employees=5, tasks=12)

    target = tmp_path / "current" / "employee_audit.db"
    target.parent.mkdir(parents=True)
    conn = sqlite3.connect(target)
    conn.executescript("""
        CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE auth_users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE,
            display_name TEXT DEFAULT '', role TEXT DEFAULT 'Admin',
            password_salt TEXT DEFAULT '', password_hash TEXT DEFAULT '',
            security_question TEXT DEFAULT '', answer_salt TEXT DEFAULT '',
            answer_hash TEXT DEFAULT '', active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT);
        CREATE TABLE attendance(id INTEGER PRIMARY KEY, status TEXT);
        INSERT INTO auth_users(username) VALUES('LocalOnly');
    """)
    conn.commit()
    conn.close()
    monkeypatch.setattr(database_recovery, "_drives", lambda: [root])

    result = database_recovery.recover_database_before_startup(target)

    assert result["status"] == "recovered"
    conn = sqlite3.connect(target)
    try:
        usernames = {r[0] for r in conn.execute("SELECT username FROM auth_users")}
        assert {"Admin", "admin", "LocalOnly"}.issubset(usernames)
        assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 5
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 12
    finally:
        conn.close()
