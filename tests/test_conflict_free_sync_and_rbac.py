"""Tests for conflict-free synchronization, RBAC authorization, and unique user credentials."""
import sqlite3
import pytest
import app
import database_sync


def setup_test_schema(conn: sqlite3.Connection):
    """Create complete schema matching app.py for merge tests."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
          display_name TEXT NOT NULL DEFAULT '',
          role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
          password_salt TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          security_question TEXT NOT NULL,
          answer_salt TEXT NOT NULL,
          answer_hash TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS employees(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_code TEXT UNIQUE,
          name TEXT NOT NULL, department TEXT DEFAULT '', designation TEXT DEFAULT '',
          phone TEXT DEFAULT '', email TEXT DEFAULT '', joining_date TEXT DEFAULT '',
          active INTEGER DEFAULT 1, notes TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
          task_date TEXT NOT NULL, title TEXT NOT NULL, details TEXT DEFAULT '',
          due_time TEXT DEFAULT '', priority TEXT DEFAULT 'Normal',
          status TEXT DEFAULT 'Not started', progress INTEGER DEFAULT 0,
          proof_url TEXT DEFAULT '', proof_note TEXT DEFAULT '', submitted_at TEXT DEFAULT '',
          manager_note TEXT DEFAULT '', expose_link INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
          FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS attendance(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
          work_date TEXT NOT NULL, check_in TEXT DEFAULT '', check_out TEXT DEFAULT '',
          break_minutes INTEGER DEFAULT 0, attendance_status TEXT DEFAULT 'Unmarked',
          attendance_note TEXT DEFAULT '', updated_at TEXT NOT NULL, UNIQUE(employee_id, work_date),
          FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS holidays(
          holiday_date TEXT PRIMARY KEY, holiday_name TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS employee_targets(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
          target_date TEXT NOT NULL, target TEXT DEFAULT '', target_status TEXT DEFAULT '',
          updated_at TEXT NOT NULL, UNIQUE(employee_id, target_date),
          FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS archived_documents(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NULL,
          report_date TEXT DEFAULT '', file_name TEXT NOT NULL, mime_type TEXT DEFAULT 'application/pdf',
          content BLOB NOT NULL, notes TEXT DEFAULT '', uploaded_at TEXT NOT NULL,
          FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE SET NULL
        );
    """)
    conn.commit()


def test_is_privileged_user_distinguishes_admin_dev_from_limited_roles():
    # Admin and Developer roles have full privileges
    assert app.is_privileged_user("Admin") is True
    assert app.is_privileged_user("admin") is True
    assert app.is_privileged_user("ADMIN") is True
    assert app.is_privileged_user("Developer") is True
    assert app.is_privileged_user("developer") is True
    assert app.is_privileged_user("DEVELOPER") is True

    # User dicts
    assert app.is_privileged_user({"role": "Admin", "username": "boss"}) is True
    assert app.is_privileged_user({"role": "Developer", "username": "coder"}) is True
    assert app.is_privileged_user({"role": "Staff", "username": "staff1"}) is False
    assert app.is_privileged_user({"role": "HR", "username": "hr1"}) is False
    assert app.is_privileged_user({"role": "Employee", "username": "emp1"}) is False

    # Limited roles
    assert app.is_privileged_user("HR") is False
    assert app.is_privileged_user("Staff") is False
    assert app.is_privileged_user("Employee") is False
    assert app.is_privileged_user("Guest") is False
    assert app.is_privileged_user("") is False
    assert app.is_privileged_user(None) is False


def test_conflict_free_snapshot_merge_unifies_records_without_data_loss(tmp_path):
    local_db_path = tmp_path / "local.db"
    remote_db_path = tmp_path / "remote.db"

    # Set up local database
    local_conn = sqlite3.connect(local_db_path)
    local_conn.row_factory = sqlite3.Row
    setup_test_schema(local_conn)

    # Insert local Admin and Developer accounts
    local_conn.execute(
        "INSERT INTO auth_users (username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '2026-10-17 08:00:00', '2026-10-17 08:00:00')",
        ("admin", "Admin User", "Admin", "salt1", "hash1", "Q?", "asalt1", "ahash1")
    )
    local_conn.execute(
        "INSERT INTO auth_users (username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '2026-10-17 08:00:00', '2026-10-17 08:00:00')",
        ("developer_user", "Dev User", "Developer", "salt2", "hash2", "Q?", "asalt2", "ahash2")
    )

    # Insert local Employee Alice (ID 1)
    cur = local_conn.execute(
        "INSERT INTO employees (name, employee_code, department, designation, phone, email, joining_date, active, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 1, '2026-01-01')",
        ("Alice Smith", "EMP001", "Engineering", "Lead Engineer", "555-0101", "alice@example.com", "2026-01-01")
    )
    local_alice_id = cur.lastrowid

    # Insert local Attendance for Alice: morning check-in at 09:00, no check-out yet
    local_conn.execute(
        "INSERT INTO attendance (employee_id, work_date, check_in, check_out, attendance_status, attendance_note, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, '2026-10-17 09:00:00')",
        (local_alice_id, "2026-10-17", "09:00", "", "Present", "Morning shift started")
    )

    # Insert local Task for Alice: in progress 50%
    local_conn.execute(
        "INSERT INTO tasks (employee_id, task_date, title, details, status, progress, manager_note, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, '2026-10-15', '2026-10-15')",
        (local_alice_id, "2026-10-15", "Quarterly Audit", "Prepare audit documents", "In Progress", 50, "Drafting in progress")
    )
    local_conn.commit()

    # Set up remote database with different auto-increment IDs
    remote_conn = sqlite3.connect(remote_db_path)
    remote_conn.row_factory = sqlite3.Row
    setup_test_schema(remote_conn)

    # Remote tries to declare admin as Staff (must NOT demote local admin!)
    remote_conn.execute(
        "INSERT INTO auth_users (username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '2026-10-17 09:00:00', '2026-10-17 09:00:00')",
        ("admin", "Admin User", "Staff", "salt1_rem", "hash1_rem", "Q?", "asalt1", "ahash1")
    )
    # Remote introduces a new Staff user
    remote_conn.execute(
        "INSERT INTO auth_users (username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '2026-10-17 09:30:00', '2026-10-17 09:30:00')",
        ("staff_worker", "Staff Worker", "Staff", "salt3", "hash3", "Q?", "asalt3", "ahash3")
    )

    # Remote has Alice with a different auto-increment ID (e.g. 5)
    # Also Bob (EMP002, ID 6)
    remote_conn.execute(
        "INSERT INTO employees (id, name, employee_code, department, designation, phone, email, joining_date, active, created_at) "
        "VALUES (5, 'Alice Smith', 'EMP001', 'Engineering', 'Lead Engineer', '555-0101', 'alice@example.com', '2026-01-01', 1, '2026-01-01')"
    )
    remote_conn.execute(
        "INSERT INTO employees (id, name, employee_code, department, designation, phone, email, joining_date, active, created_at) "
        "VALUES (6, 'Bob Jones', 'EMP002', 'Operations', 'Auditor', '555-0102', 'bob@example.com', '2026-02-01', 1, '2026-02-01')"
    )

    # Remote records Alice's check-out at 18:00
    remote_conn.execute(
        "INSERT INTO attendance (employee_id, work_date, check_in, check_out, attendance_status, attendance_note, updated_at) "
        "VALUES (5, '2026-10-17', '', '18:00', 'Present', 'Evening shift concluded', '2026-10-17 18:00:00')"
    )
    # Remote records Bob's attendance
    remote_conn.execute(
        "INSERT INTO attendance (employee_id, work_date, check_in, check_out, attendance_status, attendance_note, updated_at) "
        "VALUES (6, '2026-10-17', '09:15', '17:45', 'Present', 'Full shift completed', '2026-10-17 17:45:00')"
    )

    # Remote records Alice's task progress updated to 100% Completed
    remote_conn.execute(
        "INSERT INTO tasks (employee_id, task_date, title, details, status, progress, manager_note, created_at, updated_at) "
        "VALUES (5, '2026-10-15', 'Quarterly Audit', 'Prepare audit documents', 'Completed', 100, 'All audit sections finalized', '2026-10-15', '2026-10-17 17:00:00')"
    )
    # Remote records Bob's task
    remote_conn.execute(
        "INSERT INTO tasks (employee_id, task_date, title, details, status, progress, manager_note, created_at, updated_at) "
        "VALUES (6, '2026-10-17', 'Facility Inspection', 'Inspect physical premises', 'In Progress', 30, 'Hallway checked', '2026-10-17', '2026-10-17 16:00:00')"
    )

    # Remote adds a declared holiday
    remote_conn.execute(
        "INSERT INTO holidays (holiday_date, holiday_name, created_at) VALUES ('2026-12-25', 'Christmas Day', '2026-10-17 10:00:00')"
    )

    remote_conn.commit()
    remote_conn.close()

    # Perform conflict-free additive merge
    changes = app.merge_remote_database_snapshot(local_conn, remote_db_path)
    assert sum(changes.values()) > 0
    assert changes["users"] >= 1
    assert changes["employees"] >= 1
    assert changes["attendance"] >= 1
    assert changes["tasks"] >= 1

    # 1. Verify User Accounts
    users = {row["username"]: row["role"] for row in local_conn.execute("SELECT username, role FROM auth_users").fetchall()}
    assert "admin" in users
    # Admin cannot be demoted to Staff by remote snapshot!
    assert users["admin"] == "Admin"
    assert users["developer_user"] == "Developer"
    assert users["staff_worker"] == "Staff"
    # Ensure no duplicate usernames
    all_usernames = [row["username"].lower() for row in local_conn.execute("SELECT username FROM auth_users").fetchall()]
    assert len(all_usernames) == len(set(all_usernames))

    # 2. Verify Employees
    emp_names = [row["name"] for row in local_conn.execute("SELECT name FROM employees ORDER BY id").fetchall()]
    assert "Alice Smith" in emp_names
    assert "Bob Jones" in emp_names
    # Alice is not duplicated
    assert emp_names.count("Alice Smith") == 1

    bob_id = local_conn.execute("SELECT id FROM employees WHERE employee_code = 'EMP002'").fetchone()["id"]

    # 3. Verify Attendance Union Merge
    alice_att = local_conn.execute(
        "SELECT check_in, check_out, attendance_note FROM attendance WHERE employee_id = ? AND work_date = '2026-10-17'",
        (local_alice_id,)
    ).fetchone()
    assert alice_att is not None
    # Both check_in from local (09:00) and check_out from remote (18:00) must be preserved!
    assert alice_att["check_in"] == "09:00"
    assert alice_att["check_out"] == "18:00"
    # Notes are unified
    assert "Morning shift started" in alice_att["attendance_note"]
    assert "Evening shift concluded" in alice_att["attendance_note"]

    # Bob's attendance was mapped to local bob_id
    bob_att = local_conn.execute(
        "SELECT check_in, check_out FROM attendance WHERE employee_id = ? AND work_date = '2026-10-17'",
        (bob_id,)
    ).fetchone()
    assert bob_att is not None
    assert bob_att["check_in"] == "09:15"
    assert bob_att["check_out"] == "17:45"

    # 4. Verify Tasks Union Merge
    alice_task = local_conn.execute(
        "SELECT status, progress, manager_note FROM tasks WHERE employee_id = ? AND title = 'Quarterly Audit'",
        (local_alice_id,)
    ).fetchone()
    assert alice_task is not None
    assert alice_task["status"] == "Completed"
    assert alice_task["progress"] == 100
    assert "All audit sections finalized" in alice_task["manager_note"]

    # Bob's task mapped properly
    bob_task = local_conn.execute(
        "SELECT title, progress FROM tasks WHERE employee_id = ?",
        (bob_id,)
    ).fetchone()
    assert bob_task is not None
    assert bob_task["title"] == "Facility Inspection"
    assert bob_task["progress"] == 30

    # 5. Verify Holiday Merged
    holiday = local_conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date = '2026-12-25'").fetchone()
    assert holiday is not None
    assert holiday["holiday_name"] == "Christmas Day"

    local_conn.close()


def test_dirty_sync_callback_triggers_on_mark_pending(tmp_path):
    callback_fired = False

    def on_dirty():
        nonlocal callback_fired
        callback_fired = True

    database_path = tmp_path / "sync_test.db"
    sync = database_sync.GitHubDatabaseSync(
        database_path, "example/repo", "c" * 32,
        worker_url="https://sync.example", encryption_secret="test_secret",
    )
    sync._on_dirty_callback = on_dirty
    try:
        sync.mark_pending()
        assert callback_fired is True
    finally:
        sync.close()


def test_unique_username_constraint_case_insensitive(tmp_path):
    db_path = tmp_path / "unique_users.db"
    conn = sqlite3.connect(db_path)
    setup_test_schema(conn)

    # Insert lowercase 'admin'
    conn.execute(
        "INSERT INTO auth_users (username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at) "
        "VALUES ('admin', 'Primary Admin', 'Admin', 's1', 'h1', 'Q', 'as1', 'ah1', 1, '2026-10-17', '2026-10-17')"
    )
    conn.commit()

    # Attempting to insert uppercase 'ADMIN' must raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO auth_users (username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at) "
            "VALUES ('ADMIN', 'Duplicate Admin', 'Admin', 's2', 'h2', 'Q', 'as2', 'ah2', 1, '2026-10-17', '2026-10-17')"
        )

    # Attempting to insert mixed-case 'Admin' must also raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO auth_users (username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at) "
            "VALUES ('Admin', 'Duplicate Admin 2', 'Staff', 's3', 'h3', 'Q', 'as3', 'ah3', 1, '2026-10-17', '2026-10-17')"
        )

    conn.close()


def test_rbac_main_window_property():
    class DummyWindow:
        def __init__(self, user):
            self.current_user = user

        @property
        def is_admin_or_dev(self):
            return app.is_privileged_user(self.current_user)

    assert DummyWindow({"role": "Admin", "username": "customer"}).is_admin_or_dev is True
    assert DummyWindow({"role": "Developer", "username": "developer"}).is_admin_or_dev is True
    assert DummyWindow({"role": "Staff", "username": "staff1"}).is_admin_or_dev is False
    assert DummyWindow({"role": "HR", "username": "hr1"}).is_admin_or_dev is False
    assert DummyWindow({"role": "Employee", "username": "emp1"}).is_admin_or_dev is False
    assert DummyWindow(None).is_admin_or_dev is False


def test_merge_remote_json_snapshot_integrates_mobile_data(tmp_path):
    local_db_path = tmp_path / "local_for_json.db"
    conn = sqlite3.connect(local_db_path)
    conn.row_factory = sqlite3.Row
    setup_test_schema(conn)

    # Local has Alice (EMP001) with morning check-in
    cur = conn.execute(
        "INSERT INTO employees (name, employee_code, department, designation, phone, email, joining_date, active, created_at) "
        "VALUES ('Alice Smith', 'EMP001', 'Engineering', 'Lead', '555-01', 'alice@test.com', '2026-01-01', 1, '2026-01-01')"
    )
    alice_id = cur.lastrowid
    conn.execute(
        "INSERT INTO attendance (employee_id, work_date, check_in, check_out, attendance_status, attendance_note, updated_at) "
        "VALUES (?, '2026-10-18', '08:45', '', 'Present', 'Arrived early', '2026-10-18 08:45:00')",
        (alice_id,)
    )
    conn.execute(
        "INSERT INTO tasks (employee_id, task_date, title, details, status, progress, manager_note, created_at, updated_at) "
        "VALUES (?, '2026-10-18', 'Daily Standup', 'Sync with team', 'In Progress', 40, 'Underway', '2026-10-18', '2026-10-18')",
        (alice_id,)
    )
    conn.commit()

    # Mobile payload: Alice checked out at 17:30 + new employee Bob + new task
    mobile_json = {
        "version": "1.3.14",
        "employees": [
            {"id": 99, "name": "Alice Smith", "employee_code": "EMP001", "department": "Engineering"},
            {"id": 100, "name": "Bob Stone", "employee_code": "EMP002", "department": "Support", "phone": "555-02"}
        ],
        "attendance": {
            "99_2026-10-18": {
                "employee_id": 99,
                "work_date": "2026-10-18",
                "check_in": "",
                "check_out": "17:30",
                "attendance_status": "Present",
                "attendance_note": "Left on time"
            }
        },
        "tasks": [
            {
                "employee_id": 99,
                "task_date": "2026-10-18",
                "title": "Daily Standup",
                "status": "Completed",
                "progress": 100,
                "manager_note": "All items discussed"
            },
            {
                "employee_id": 100,
                "task_date": "2026-10-18",
                "title": "Onboarding",
                "status": "In Progress",
                "progress": 50
            }
        ],
        "holidays": {"2026-11-01": "Company Anniversary"}
    }

    # Save to a JSON file and merge
    json_file = tmp_path / "mobile_sync.json"
    json_file.write_text(__import__("json").dumps(mobile_json), encoding="utf-8")

    stats = app.merge_remote_database_snapshot(conn, json_file)
    assert stats["employees"] >= 1
    assert stats["attendance"] >= 1
    assert stats["tasks"] >= 1

    # Verify Alice's attendance merged both morning check-in and evening check-out
    att = conn.execute("SELECT check_in, check_out, attendance_note FROM attendance WHERE employee_id=? AND work_date='2026-10-18'", (alice_id,)).fetchone()
    assert att["check_in"] == "08:45"
    assert att["check_out"] == "17:30"
    assert "Arrived early" in att["attendance_note"]
    assert "Left on time" in att["attendance_note"]

    # Verify Alice's task progress advanced to 100% Completed
    task = conn.execute("SELECT status, progress, manager_note FROM tasks WHERE employee_id=? AND title='Daily Standup'", (alice_id,)).fetchone()
    assert task["status"] == "Completed"
    assert task["progress"] == 100
    assert "All items discussed" in task["manager_note"]

    # Verify Bob was created and his task was mapped to Bob's new local ID
    bob = conn.execute("SELECT id, name FROM employees WHERE employee_code='EMP002'").fetchone()
    assert bob is not None
    bob_task = conn.execute("SELECT title, progress FROM tasks WHERE employee_id=?", (bob["id"],)).fetchone()
    assert bob_task is not None
    assert bob_task["title"] == "Onboarding"

    # Verify holiday merged
    hol = conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date='2026-11-01'").fetchone()
    assert hol["holiday_name"] == "Company Anniversary"

    conn.close()


def test_hybrid_snapshot_contains_sqlite_and_json_manifest(tmp_path):
    db_path = tmp_path / "hybrid_test.db"
    conn = sqlite3.connect(db_path)
    setup_test_schema(conn)
    conn.execute("INSERT INTO employees (name, employee_code, created_at) VALUES ('Charlie', 'EMP003', '2026-10-18')")
    conn.commit()
    conn.close()

    token = "test_token_123"
    encrypted = database_sync.create_encrypted_database_snapshot(db_path, token)
    decrypted = database_sync.decrypt_snapshot_bytes(encrypted, token)

    # 1. Verify it can be opened by sqlite3 directly
    snap_db_path = tmp_path / "hybrid_decrypted.db"
    snap_db_path.write_bytes(decrypted)
    snap_conn = sqlite3.connect(snap_db_path)
    assert snap_conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    emp = snap_conn.execute("SELECT name FROM employees").fetchone()
    assert emp[0] == "Charlie"
    snap_conn.close()

    # 2. Verify it contains the embedded JSON manifest marker
    marker = b"\n__RSC_JSON__\n"
    idx = decrypted.rfind(marker)
    assert idx != -1
    json_str = decrypted[idx + len(marker):].decode("utf-8")
    parsed = __import__("json").loads(json_str)
    assert parsed["version"] == "1.3.14"
    assert any(e["name"] == "Charlie" for e in parsed["employees"])


