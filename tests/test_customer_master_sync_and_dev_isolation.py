"""Tests for customer master sync vs developer test mode isolation.

Validates:
1. User classification: Master Customer ('Admin / Taruna') vs Developer Testing ('admin').
2. Database auto-provisioning: Ensures both 'taruna' and 'admin' are provisioned.
3. Commit hook suppression: SQLite commits by 'admin' do NOT dirty cloud sync.
4. Continuous Google Sheets sync: Blocked from uploading/pushing when 'admin' is active.
5. Master Excel snapshot protection: Test tasks tagged by 'admin' are excluded,
   and test snapshot is isolated from customer master database.
"""
import sqlite3
import pytest
from pathlib import Path
import app
import google_sheets_sync


def test_user_classification_taruna_vs_admin():
    admin_u = {"username": "admin", "role": "Developer", "display_name": "admin (Developer - Test Mode)"}
    taruna_u = {"username": "taruna", "role": "Admin", "display_name": "Admin / Taruna (Customer Master)"}
    hr_u = {"username": "sanjana", "role": "HR", "display_name": "Sanjana"}

    # is_developer_test_user
    assert app.is_developer_test_user(admin_u) is True
    assert app.is_developer_test_user("admin") is True
    assert app.is_developer_test_user({"username": "admin", "role": "Admin"}) is True
    assert app.is_developer_test_user(taruna_u) is False
    assert app.is_developer_test_user("taruna") is False
    assert app.is_developer_test_user({"username": "taruna", "role": "Admin"}) is False
    assert app.is_developer_test_user(hr_u) is False

    # is_master_customer_user
    assert app.is_master_customer_user(taruna_u) is True
    assert app.is_master_customer_user("taruna") is True
    assert app.is_master_customer_user("Admin / Taruna") is True
    assert app.is_master_customer_user(admin_u) is False
    assert app.is_master_customer_user("admin") is False
    assert app.is_master_customer_user(hr_u) is False


def test_database_setup_provisions_both_taruna_and_admin(tmp_path, monkeypatch):
    db_file = tmp_path / "test_provision.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_file))

    # Pre-seed with just admin
    conn = sqlite3.connect(db_file)
    conn.executescript("""
        CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE auth_users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
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
        INSERT INTO auth_users VALUES (1, 'admin', 'Administrator', 'Admin', 'salt123', 'hash123', 'Q?', 'asalt', 'ahash', 1, '2026-10-01', '2026-10-01');
    """)
    conn.commit()
    conn.close()

    db = app.Database()
    rows = {r["username"].lower(): dict(r) for r in db.conn.execute("SELECT * FROM auth_users").fetchall()}

    assert "admin" in rows
    assert "Developer" in rows["admin"]["role"] or "admin" in rows["admin"]["display_name"]
    assert "taruna" in rows
    assert rows["taruna"]["role"] == "Admin"
    assert "Taruna" in rows["taruna"]["display_name"]
    # Shared password salt/hash so customer can sign in immediately
    assert rows["taruna"]["password_hash"] == "hash123"


def test_commit_hook_suppressed_for_developer_test_user(tmp_path, monkeypatch):
    db_file = tmp_path / "test_hook.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_file))
    db = app.Database()

    marked = []
    class DummySync:
        def mark_pending(self):
            marked.append(True)

    db.github_sync = DummySync()

    # When active user is developer 'admin'
    db.set_active_user({"username": "admin", "role": "Developer"})
    db.conn.execute("CREATE TABLE IF NOT EXISTS test_t (x INT)")
    db.conn.execute("INSERT INTO test_t VALUES (1)")
    db.conn.commit()
    assert len(marked) == 0, "Developer commit must NOT trigger mark_pending"

    # When active user is customer 'taruna'
    db.set_active_user({"username": "taruna", "role": "Admin", "display_name": "Admin / Taruna"})
    db.conn.execute("INSERT INTO test_t VALUES (2)")
    db.conn.commit()
    assert len(marked) == 1, "Customer commit MUST trigger mark_pending"


def test_google_sheets_continuous_sync_paused_in_dev_test_mode():
    class MockDB:
        def __init__(self, user):
            self.active_user = user
            self.conn = sqlite3.connect(":memory:")

    dev_db = MockDB({"username": "admin", "role": "Developer"})
    res = google_sheets_sync.continuous_auto_sync(dev_db)
    assert res.get("status") == "test_mode"
    assert "Developer test mode active" in res.get("message", "")


def test_master_database_snapshot_excludes_dev_test_tasks(tmp_path):
    conn = sqlite3.connect(tmp_path / "snap.db")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT, employee_code TEXT, email TEXT, phone TEXT, role TEXT, department TEXT, designation TEXT, joining_date TEXT, salary TEXT, active INT);
        CREATE TABLE tasks(id INTEGER PRIMARY KEY, employee_id INT, task_date TEXT, title TEXT, details TEXT, due_time TEXT, status TEXT, progress INT, proof_url TEXT, proof_note TEXT, manager_note TEXT, custom_values TEXT, updated_at TEXT);
        CREATE TABLE attendance(id INTEGER PRIMARY KEY, employee_id INT, date TEXT, status TEXT, check_in TEXT, check_out TEXT, total_hours TEXT, remarks TEXT, updated_at TEXT);
        CREATE TABLE customer_prospects(state TEXT, city TEXT, area TEXT, business_category TEXT, business_name TEXT, phone TEXT, email TEXT, address TEXT, maps TEXT, website TEXT);

        INSERT INTO employees VALUES (1, 'Taruna', 'RS-001', 'taruna@example.com', '9999999999', 'Admin', 'Management', 'Head', '2026-01-01', '50000', 1);
        INSERT INTO tasks VALUES (1, 1, '2026-10-24', 'Customer Master Task', 'Important', '18:00', 'Submitted', 100, '', '', '', '', '2026-10-24 10:00:00');
        INSERT INTO tasks VALUES (2, 1, '2026-10-24', 'Developer Test Task', 'Testing only', '18:00', 'In progress', 50, '', '', '', '[["created_by", "admin"], ["test_mode", "true"]]', '2026-10-24 11:00:00');
    """)
    conn.commit()

    class MockDB:
        def __init__(self, c, user):
            self.conn = c
            self.active_user = user

    # 1. Customer export: saves to Google_Sheets_Master_Database.xlsx and excludes test task
    out_master = tmp_path / "Google_Sheets_Master_Database.xlsx"
    cust_db = MockDB(conn, {"username": "taruna", "role": "Admin", "display_name": "Admin / Taruna"})
    saved_path = google_sheets_sync.save_master_database_snapshot(cust_db, custom_path=out_master)

    import openpyxl
    wb = openpyxl.load_workbook(saved_path)
    ws_tasks = wb["Tasks"]
    task_titles = [row[3] for row in ws_tasks.iter_rows(values_only=True) if row[3] != "Title"]
    wb.close()

    assert "Customer Master Task" in task_titles
    assert "Developer Test Task" not in task_titles, "Test task must NOT appear in master snapshot"
