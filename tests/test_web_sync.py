from pathlib import Path
import sqlite3

from web_sync import merge_snapshot_databases, validate_snapshot


def make_database(path: Path, employees):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE auth_users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, updated_at TEXT, password_hash TEXT)")
    db.execute("CREATE TABLE employees(id INTEGER PRIMARY KEY, employee_code TEXT UNIQUE, name TEXT, updated_at TEXT)")
    db.execute("CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT, updated_at TEXT)")
    db.execute("INSERT INTO auth_users VALUES(1, 'Admin', '2026-01-01', 'hash')")
    db.executemany("INSERT INTO employees VALUES(?,?,?,?)", employees)
    db.commit()
    db.close()


def test_merge_preserves_local_rows_and_imports_remote_rows(tmp_path):
    local = tmp_path / "local.db"
    remote = tmp_path / "remote.db"
    make_database(local, [(1, "EMP001", "Local", "2026-01-01")])
    make_database(remote, [(2, "EMP002", "Remote", "2026-01-02")])

    result = merge_snapshot_databases(local, remote)
    db = sqlite3.connect(local)
    try:
        names = {row[0] for row in db.execute("SELECT name FROM employees")}
    finally:
        db.close()

    assert names == {"Local", "Remote"}
    assert result["inserted"] >= 1


def test_merge_uses_newer_updated_at_for_same_row(tmp_path):
    local = tmp_path / "local.db"
    remote = tmp_path / "remote.db"
    make_database(local, [(1, "EMP001", "Old", "2026-01-01")])
    make_database(remote, [(1, "EMP001", "New", "2026-01-02")])

    merge_snapshot_databases(local, remote)
    db = sqlite3.connect(local)
    try:
        assert db.execute("SELECT name FROM employees WHERE id=1").fetchone()[0] == "New"
    finally:
        db.close()


def test_snapshot_validator_checks_required_tables(tmp_path):
    path = tmp_path / "snapshot.db"
    make_database(path, [])
    assert validate_snapshot(path)["employees"] == 0
