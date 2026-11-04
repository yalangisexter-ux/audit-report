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


def test_merge_remaps_colliding_employee_and_task_ids_without_overwriting_local_rows(tmp_path):
    local = tmp_path / "local-collision.db"
    remote = tmp_path / "remote-collision.db"

    schema = """
        CREATE TABLE auth_users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, updated_at TEXT, password_hash TEXT);
        CREATE TABLE employees(id INTEGER PRIMARY KEY AUTOINCREMENT, employee_code TEXT UNIQUE, name TEXT, department TEXT, updated_at TEXT);
        CREATE TABLE tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, task_date TEXT, title TEXT, status TEXT, updated_at TEXT,
                           FOREIGN KEY(employee_id) REFERENCES employees(id));
    """
    for path in (local, remote):
        db = sqlite3.connect(path)
        db.executescript(schema)
        db.execute("INSERT INTO auth_users VALUES(1,'Admin','2026-01-01','hash')")
        db.commit()
        db.close()

    db = sqlite3.connect(local)
    db.execute("INSERT INTO employees VALUES(1,'EMP001','Local Employee','Ops','2026-01-01')")
    db.execute("INSERT INTO tasks VALUES(1,1,'2026-01-03','Local task','In progress','2026-01-01')")
    db.commit()
    db.close()

    db = sqlite3.connect(remote)
    db.execute("INSERT INTO employees VALUES(1,'EMP002','Remote Employee','Ops','2026-01-02')")
    db.execute("INSERT INTO tasks VALUES(1,1,'2026-01-03','Remote task','Completed','2026-01-02')")
    db.commit()
    db.close()

    result = merge_snapshot_databases(local, remote)
    db = sqlite3.connect(local)
    try:
        employees = {row[0]: row[1] for row in db.execute("SELECT id,employee_code FROM employees")}
        tasks = db.execute("SELECT title,employee_id FROM tasks ORDER BY title").fetchall()
        assert employees == {1: "EMP001", 2: "EMP002"}
        assert tasks == [("Local task", 1), ("Remote task", 2)]
        assert result["inserted"] >= 2
    finally:
        db.close()


def test_web_sync_requires_explicit_encryption_secret(tmp_path, monkeypatch):
    from web_sync import WebDatabaseSync

    monkeypatch.delenv("DB_SYNC_ENCRYPTION_SECRET", raising=False)
    monkeypatch.setenv("DB_SYNC_INSTALLATION_ID", "080717e78653166d64cd2bcf72c75c76")
    monkeypatch.setenv("DB_SYNC_WORKER_URL", "https://raw-strength-audit-db-sync.yalangisexter.workers.dev")
    manager = WebDatabaseSync(tmp_path / "web.db")
    assert manager.configured is False
    assert manager.bootstrap() is False
    assert "DB_SYNC_ENCRYPTION_SECRET" in manager.last_pull["error"]



def test_bootstrap_rejects_business_snapshot_without_customer_login_users(tmp_path, monkeypatch):
    from web_sync import WebDatabaseSync

    monkeypatch.setenv("DB_SYNC_ENCRYPTION_SECRET", "test-encryption-secret")
    monkeypatch.setenv("DB_SYNC_INSTALLATION_ID", "080717e78653166d64cd2bcf72c75c76")
    monkeypatch.setenv("DB_SYNC_WORKER_URL", "https://sync.example")
    path = tmp_path / "web-no-users.db"
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE auth_users(id INTEGER PRIMARY KEY, username TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT);
        INSERT INTO employees VALUES(1, 'Existing employee');
        INSERT INTO tasks VALUES(1, 'Existing task');
        """
    )
    db.commit()
    db.close()

    manager = WebDatabaseSync(path)
    manager.last_pull = {"ok": True, "auth_users": 0, "employees": 1, "tasks": 1}
    manager._pull_merge = lambda: {"changed": False, "inserted": 0, "updated": 0, "conflicts": 0}
    try:
        assert manager.bootstrap() is False
        assert manager.last_pull["ok"] is False
        assert "zero active login users" in manager.last_pull["error"]
        assert "first-admin setup remains disabled" in manager.last_pull["error"]
    finally:
        if manager.sync is not None:
            manager.sync.close()
