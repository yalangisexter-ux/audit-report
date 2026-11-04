"""Unit tests for FastAPI REST API endpoints.
Validates that all business logic, endpoints, and custom task tracking work seamlessly over HTTP.
"""
import sqlite3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

import tempfile
import app as desktop_app
import business_tracking

# Use an isolated test database so production data is never touched
_isolated_db = Path(tempfile.gettempdir()) / "test_api_server_isolated.db"
desktop_app.DB_PATH = str(_isolated_db)

_test_db = desktop_app.Database()
try:
    business_tracking.setup_business_tables(_test_db.conn)
except Exception:
    pass
_test_db.conn.execute(
    """INSERT OR IGNORE INTO auth_users(
           username,display_name,role,password_salt,password_hash,
           security_question,answer_salt,answer_hash,active,created_at,updated_at
       ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
    ("api-test-bootstrap", "API Test Admin", "Admin", "salt", "hash",
     "First school", "salt", "hash", "2026-01-01", "2026-01-01"),
)
_test_db.conn.commit()
if hasattr(_test_db, "close_github_sync"):
    _test_db.close_github_sync(timeout=0)
if hasattr(_test_db, "conn") and _test_db.conn:
    _test_db.conn.close()

from fastapi.testclient import TestClient
import api_server
from api_server import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["database_connected"] is True

def test_api_dashboard():
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "kpis" in data
    assert "total_employees" in data["kpis"]
    assert "present_today" in data["kpis"]
    assert "open_tasks" in data["kpis"]

def test_api_employees_crud():
    import secrets
    # 1. Fetch employees
    res = client.get("/api/employees")
    assert res.status_code == 200
    employees = res.json()
    assert isinstance(employees, list)

    # 2. Create new employee with unique code
    unique_code = f"ATH-{secrets.token_hex(3).upper()}"
    new_emp = {
        "name": "REST Test Athlete",
        "employee_code": unique_code,
        "department": "Calisthenics Coaching",
        "designation": "Master Coach",
        "phone": "9998887776",
        "email": "testathlete@rawstrength.in",
        "notes": "Created via automated REST API test",
    }
    create_res = client.post("/api/employees", json=new_emp)
    assert create_res.status_code == 200
    created = create_res.json()
    emp_id = created["id"]
    assert emp_id > 0

    # 3. Update employee
    update_res = client.put(f"/api/employees/{emp_id}", json={
        "name": "REST Test Athlete Updated",
        "employee_code": unique_code,
        "department": "Calisthenics Elite",
        "phone": "9998887770"
    })
    assert update_res.status_code == 200

    # 4. Delete employee (soft-delete)
    del_res = client.delete(f"/api/employees/{emp_id}")
    assert del_res.status_code == 200

def test_api_tasks_with_custom_fields():
    # 1. Create task with custom key-values (e.g. Tracked By, Equipment)
    task_payload = {
        "title": "Muscle-up Bar Inspection",
        "department": "Maintenance",
        "priority": "High",
        "status": "In progress",
        "progress": 65,
        "details": "Check outdoor rig stability",
        "custom_fields": [
            {"key": "Tracked By", "value": "Senior Coach Vikram"},
            {"key": "Equipment", "value": "Titan Rig 4"}
        ]
    }
    create_res = client.post("/api/tasks", json=task_payload)
    assert create_res.status_code == 200
    task_data = create_res.json()
    task_id = task_data["id"]
    assert task_id > 0

    # 2. Get task list and verify presence of custom fields
    list_res = client.get("/api/tasks")
    assert list_res.status_code == 200
    tasks = list_res.json()
    found = next((t for t in tasks if t["id"] == task_id), None)
    assert found is not None
    keys_map = {row["key"]: row["value"] for row in found.get("custom_fields", []) if isinstance(row, dict)}
    assert keys_map.get("Tracked By") == "Senior Coach Vikram"
    assert keys_map.get("Equipment") == "Titan Rig 4"

    # 3. Update task status & progress
    upd_res = client.put(f"/api/tasks/{task_id}", json={
        "title": "Muscle-up Bar Inspection",
        "status": "Completed",
        "progress": 100,
        "custom_fields": [
            {"key": "Tracked By", "value": "Senior Coach Vikram"},
            {"key": "Inspection Result", "value": "Passed"}
        ]
    })
    assert upd_res.status_code == 200
    assert upd_res.json()["status"] == "Completed"
    assert upd_res.json()["progress"] == 100

    # 4. Clean up test task
    client.delete(f"/api/tasks/{task_id}")

def test_api_attendance_and_holidays():
    import secrets

    employee_res = client.post("/api/employees", json={
        "name": "Attendance Basic API Test",
        "employee_code": f"ATT-BASIC-{secrets.token_hex(3).upper()}",
        "department": "Testing",
    })
    assert employee_res.status_code == 200
    employee_id = employee_res.json()["id"]

    # 1. Mark attendance
    mark_payload = {
        "employee_id": employee_id,
        "status": "Present",
        "notes": "Checked in via REST API",
        "check_in": "06:00",
        "check_out": "14:00"
    }
    res = client.post("/api/attendance/mark", json=mark_payload)
    assert res.status_code == 200

    # 2. Fetch attendance
    list_res = client.get("/api/attendance")
    assert list_res.status_code == 200
    assert "roster" in list_res.json()
    assert isinstance(list_res.json()["roster"], list)

    # 3. Holidays
    h_res = client.get("/api/holidays")
    assert h_res.status_code == 200
    assert isinstance(h_res.json(), list)

def test_api_attendance_saves_selected_date_and_clears_absent_times():
    import secrets
    import sqlite3

    employee_res = client.post("/api/employees", json={
        "name": "Attendance API Regression",
        "employee_code": f"ATT-{secrets.token_hex(3).upper()}",
        "department": "Testing",
    })
    assert employee_res.status_code == 200
    employee_id = employee_res.json()["id"]
    work_date = "2026-11-03"

    present_res = client.post("/api/attendance/mark", json={
        "employee_id": employee_id,
        "work_date": work_date,
        "attendance_status": "Present",
        "check_in": "09:00",
        "check_out": "18:00",
        "break_minutes": 30,
        "attendance_note": "Regression test",
    })
    assert present_res.status_code == 200
    assert present_res.json()["attendance"]["work_date"] == work_date

    absent_res = client.post("/api/attendance/mark", json={
        "employee_id": employee_id,
        "work_date": work_date,
        "attendance_status": "Absent",
    })
    assert absent_res.status_code == 200
    saved = absent_res.json()["attendance"]
    assert saved["attendance_status"] == "Absent"
    assert saved["check_in"] == ""
    assert saved["check_out"] == ""

    roster_res = client.get(f"/api/attendance?work_date={work_date}")
    assert roster_res.status_code == 200
    roster = next(row for row in roster_res.json()["roster"] if row["employee_id"] == employee_id)
    assert roster_res.json()["date"] == work_date
    assert roster["attendance_status"] == "Absent"
    assert roster["check_in"] == ""
    assert roster["check_out"] == ""

    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        row = connection.execute(
            "SELECT work_date, attendance_status, check_in, check_out FROM attendance WHERE employee_id=? AND work_date=?",
            (employee_id, work_date),
        ).fetchone()
        assert row == (work_date, "Absent", "", "")
    finally:
        connection.close()


def test_api_business_tracking():
    # Products
    p_res = client.get("/api/business/products")
    assert p_res.status_code == 200
    assert isinstance(p_res.json(), list)

    # Services
    s_res = client.get("/api/business/services")
    assert s_res.status_code == 200
    assert isinstance(s_res.json(), list)

def test_api_settings():
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "settings" in data
    assert "app_version" in data

def test_api_system_updates(monkeypatch):
    import json
    fake_releases = json.dumps([{
        "tag_name": "v1.3.62",
        "draft": False,
        "prerelease": False,
        "published_at": "2026-10-27T12:00:00Z",
        "assets": [{
            "name": "RawStrengthEmployeeAuditManager-Setup.exe",
            "browser_download_url": "https://github.com/yalangisexter-ux/audit-report/releases/download/v1.3.62/RawStrengthEmployeeAuditManager-Setup.exe",
            "size": 75604753,
        }]
    }]).encode("utf-8")

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return fake_releases

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    res = client.get("/api/system/check-updates")
    assert res.status_code == 200
    data = res.json()
    assert "current_version" in data
    assert "latest_version" in data
    assert "has_update" in data
    assert "github_releases_url" in data


def test_api_account_registration_and_recovery_are_safe():
    import sqlite3
    import secrets

    username = "web-reg-" + secrets.token_hex(4)
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        connection.execute(
            "INSERT OR IGNORE INTO auth_users(username,display_name,role,password_salt,password_hash,security_question,answer_salt,answer_hash,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,1,?,?)",
            ("test-admin", "Test Admin", "Admin", "salt", "hash", "First school", "salt", "hash", "2026-01-01", "2026-01-01"),
        )
        connection.execute("UPDATE auth_users SET role='Admin',active=1 WHERE username='test-admin'")
        connection.commit()
    finally:
        connection.close()

    payload = {
        "username": username,
        "display_name": "Web Registration Test",
        "password": "TestPass123",
        "security_question": "What was the name of your first school?",
        "security_answer": "Green Valley",
    }
    created = client.post("/api/auth/register", json=payload)
    assert created.status_code == 200
    assert created.json()["pending_approval"] is True

    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        row = connection.execute(
            "SELECT role,active,password_salt,password_hash FROM auth_users WHERE username=?",
            (username,),
        ).fetchone()
        assert row[0] == "Staff"
        assert row[1] == 0
        assert row[2] and row[3]
        connection.execute("UPDATE auth_users SET active=1 WHERE username=?", (username,))
        connection.commit()
    finally:
        connection.close()

    question = client.post("/api/auth/recovery-question", json={"username": username.upper()})
    assert question.status_code == 200
    assert question.json()["security_question"] == payload["security_question"]

    reset = client.post("/api/auth/password-reset", json={
        "username": username.upper(),
        "security_answer": "  green   valley ",
        "new_password": "NewPass456",
    })
    assert reset.status_code == 200

    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        row = connection.execute(
            "SELECT password_salt,password_hash FROM auth_users WHERE username=?",
            (username,),
        ).fetchone()
        _, expected = desktop_app.hash_pin("NewPass456", row[0])
        assert secrets.compare_digest(expected, row[1])
    finally:
        connection.close()



def _api_test_workday():
    from datetime import date, timedelta
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    connection.row_factory = sqlite3.Row
    try:
        setting = connection.execute(
            "SELECT value FROM settings WHERE key='working_weekdays'"
        ).fetchone()
        try:
            weekdays = {int(value) for value in (setting["value"] if setting else "0,1,2,3,4").split(",") if value.strip()}
        except (TypeError, ValueError):
            weekdays = {0, 1, 2, 3, 4}
        holidays = {
            row["holiday_date"]
            for row in connection.execute("SELECT holiday_date FROM holidays").fetchall()
        }
    finally:
        connection.close()
    candidate = date.today()
    for _ in range(45):
        if candidate.weekday() in weekdays and candidate.isoformat() not in holidays:
            return candidate
        candidate -= timedelta(days=1)
    raise AssertionError("Could not find a scheduled non-holiday workday for attendance API tests")


def test_api_attendance_summary_matches_desktop_workday_rules():
    work_day = _api_test_workday()
    employee = client.post("/api/employees", json={
        "name": "Attendance Summary Parity Test",
        "employee_code": "ATT-SUM-" + work_day.strftime("%Y%m%d"),
        "joining_date": work_day.isoformat(),
        "department": "Testing",
    })
    assert employee.status_code == 200
    employee_id = employee.json()["id"]

    marked = client.post("/api/attendance/mark", json={
        "employee_id": employee_id,
        "work_date": work_day.isoformat(),
        "attendance_status": "Present",
        "check_in": "09:00",
        "check_out": "17:00",
    })
    assert marked.status_code == 200

    response = client.get("/api/attendance/summary", params={"work_date": work_day.isoformat()})
    assert response.status_code == 200
    summary = next(row for row in response.json()["rows"] if row["employee_id"] == employee_id)
    assert summary["start_date"] == work_day.isoformat()
    assert summary["work_days"] == 1
    assert summary["present"] == 1
    assert summary["absent"] == 0
    assert summary["leave"] == 0
    assert summary["holidays"] == 0
    assert summary["total_present"] == 1


def test_api_attendance_bulk_edit_is_atomic_and_validates_times():
    work_day = _api_test_workday()
    employee = client.post("/api/employees", json={
        "name": "Attendance Bulk Edit Test",
        "employee_code": "ATT-BULK-" + work_day.strftime("%Y%m%d"),
        "joining_date": work_day.isoformat(),
        "department": "Testing",
    })
    assert employee.status_code == 200
    employee_id = employee.json()["id"]

    initial = client.post("/api/attendance/mark", json={
        "employee_id": employee_id,
        "work_date": work_day.isoformat(),
        "attendance_status": "Present",
        "check_in": "09:00",
        "check_out": "17:00",
        "attendance_note": "Initial note",
    })
    assert initial.status_code == 200

    bulk = client.post("/api/attendance/bulk-edit", json={
        "work_date": work_day.isoformat(),
        "employee_ids": [employee_id],
        "apply_status": True,
        "status": "Leave",
        "apply_remarks": True,
        "remarks": "Bulk leave",
    })
    assert bulk.status_code == 200
    assert bulk.json()["updated"] == 1

    roster = client.get("/api/attendance", params={"work_date": work_day.isoformat()})
    assert roster.status_code == 200
    row = next(item for item in roster.json()["roster"] if item["employee_id"] == employee_id)
    assert row["attendance_status"] == "Leave"
    assert row["check_in"] == ""
    assert row["check_out"] == ""
    assert row["attendance_note"] == "Bulk leave"

    invalid_time = client.post("/api/attendance/mark", json={
        "employee_id": employee_id,
        "work_date": work_day.isoformat(),
        "attendance_status": "Present",
        "check_in": "9:00",
    })
    assert invalid_time.status_code == 422

    missing_checkin = client.post("/api/attendance/mark", json={
        "employee_id": employee_id,
        "work_date": work_day.isoformat(),
        "attendance_status": "Present",
        "check_out": "17:00",
    })
    assert missing_checkin.status_code == 422



def test_api_attendance_preserves_recognized_worked_day_detail_statuses():
    import secrets
    work_day = _api_test_workday()
    employee = client.post("/api/employees", json={
        "name": "Attendance Detail Status Test",
        "employee_code": "ATT-DETAIL-" + secrets.token_hex(3).upper(),
        "joining_date": work_day.isoformat(),
        "department": "Testing",
    })
    assert employee.status_code == 200
    employee_id = employee.json()["id"]

    check_in = client.post("/api/attendance/mark", json={
        "employee_id": employee_id,
        "work_date": work_day.isoformat(),
        "attendance_status": "Late Check-in",
        "check_in": "09:15",
    })
    assert check_in.status_code == 200
    assert check_in.json()["attendance"]["attendance_status"] == "Late Check-in"

    check_out = client.post("/api/attendance/mark", json={
        "employee_id": employee_id,
        "work_date": work_day.isoformat(),
        "attendance_status": "Late Check-in",
        "check_out": "17:00",
    })
    assert check_out.status_code == 200
    saved = check_out.json()["attendance"]
    assert saved["attendance_status"] == "Late Check-in"
    assert saved["check_in"] == "09:15"
    assert saved["check_out"] == "17:00"


def test_employee_directory_groups_fields_and_reordering():
    import secrets
    group_a = "Directory Alpha " + secrets.token_hex(3)
    group_b = "Directory Beta " + secrets.token_hex(3)
    assert client.post("/api/employee-groups", json={"name": group_a}).status_code == 200
    assert client.post("/api/employee-groups", json={"name": group_b}).status_code == 200
    code_a = "DIR-A-" + secrets.token_hex(3).upper()
    code_b = "DIR-B-" + secrets.token_hex(3).upper()
    created_a = client.post("/api/employees", json={
        "name": "Directory Athlete A", "employee_code": code_a, "department": group_a,
        "designation": "Senior Coach", "phone": "9000000001", "email": "directory-a@example.test",
        "joining_date": "2026-01-15", "notes": "Directory notes A",
    })
    created_b = client.post("/api/employees", json={
        "name": "Directory Athlete B", "employee_code": code_b, "department": group_b,
        "designation": "Coach", "joining_date": "2026-02-10",
    })
    assert created_a.status_code == 200 and created_b.status_code == 200
    employee_a, employee_b = created_a.json()["id"], created_b.json()["id"]
    rows = client.get("/api/employees?active_only=false").json()
    row_a = next(row for row in rows if row["id"] == employee_a)
    assert (row_a["joining_date"], row_a["notes"], row_a["email"]) == ("2026-01-15", "Directory notes A", "directory-a@example.test")
    task = client.post("/api/tasks", json={"employee_id": employee_a, "task_date": "2026-11-05", "title": "Directory rename propagation", "department": group_a})
    assert task.status_code == 200
    renamed = group_a + " Renamed"
    assert client.patch("/api/employee-groups", json={"old_name": group_a, "new_name": renamed}).status_code == 200
    employee_after = next(row for row in client.get("/api/employees?active_only=false").json() if row["id"] == employee_a)
    task_after = next(row for row in client.get("/api/tasks").json() if row["id"] == task.json()["id"])
    assert employee_after["department"] == renamed and task_after["department"] == renamed
    assert client.put("/api/employee-groups/order", json={"group_names": [group_b, renamed]}).status_code == 200
    names = [row["name"] for row in client.get("/api/employee-groups").json()]
    assert names.index(group_b) < names.index(renamed)
    reordered = client.put("/api/employee-directory/reorder", json={"items": [
        {"id": employee_a, "display_order": 20, "department": renamed},
        {"id": employee_b, "display_order": 10, "department": group_b},
    ]})
    assert reordered.status_code == 200
    employees = client.get("/api/employees?active_only=false").json()
    row_a = next(row for row in employees if row["id"] == employee_a)
    row_b = next(row for row in employees if row["id"] == employee_b)
    assert row_a["display_order"] == 20 and row_b["display_order"] == 10 and row_b["department"] == group_b
    assert client.request("DELETE", "/api/employee-groups", json={"name": group_b}).status_code == 200
    row_b = next(row for row in client.get("/api/employees?active_only=false").json() if row["id"] == employee_b)
    assert row_b["department"] == ""


def test_employee_directory_role_permissions_and_safe_permanent_delete(tmp_path, monkeypatch):
    import api_server
    import secrets
    monkeypatch.setattr(desktop_app, "BACKUP_DIR", tmp_path / "employee-backups")
    original_overrides = dict(api_server.app.dependency_overrides)
    def set_role(role):
        api_server.app.dependency_overrides[api_server.get_current_user] = lambda: {
            "id": 987654, "username": "employee-directory-role-test",
            "display_name": "Employee Directory Role Test", "role": role,
        }
    try:
        set_role("Staff")
        denied = client.post("/api/employees", json={"name": "Denied Staff Employee", "employee_code": "DENIED-" + secrets.token_hex(3).upper()})
        assert denied.status_code == 403
        assert client.post("/api/employee-groups", json={"name": "Denied Section"}).status_code == 403
        assert client.put("/api/employee-directory/reorder", json={"items": []}).status_code == 403
        set_role("HR")
        code = "HR-DIRECTORY-" + secrets.token_hex(3).upper()
        created = client.post("/api/employees", json={"name": "HR Managed Employee", "employee_code": code, "department": "HR Directory QA"})
        assert created.status_code == 200
        employee_id = created.json()["id"]
        status_res = client.patch(f"/api/employees/{employee_id}/status", json={"active": False})
        assert status_res.status_code == 200 and status_res.json()["active"] == 0
        assert client.delete(f"/api/employees/{employee_id}/permanent").status_code == 403
        inactive = client.get("/api/employees?active_only=false&search=" + code).json()
        assert len(inactive) == 1 and inactive[0]["active"] == 0
        set_role("Admin")
        client.post("/api/tasks", json={"employee_id": employee_id, "task_date": "2026-11-05", "title": "Permanent delete regression task"})
        client.post("/api/attendance/mark", json={"employee_id": employee_id, "work_date": "2026-11-05", "attendance_status": "Present", "check_in": "09:00"})
        deleted = client.delete(f"/api/employees/{employee_id}/permanent")
        assert deleted.status_code == 200
        backup_path = tmp_path / "employee-backups" / deleted.json()["backup_file"]
        assert backup_path.is_file()
        backup_conn = sqlite3.connect(str(backup_path))
        try:
            assert backup_conn.execute("SELECT name FROM employees WHERE id=?", (employee_id,)).fetchone()[0] == "HR Managed Employee"
        finally:
            backup_conn.close()
        db_conn = sqlite3.connect(str(desktop_app.DB_PATH))
        try:
            assert db_conn.execute("SELECT COUNT(*) FROM employees WHERE id=?", (employee_id,)).fetchone()[0] == 0
            assert db_conn.execute("SELECT COUNT(*) FROM tasks WHERE employee_id=?", (employee_id,)).fetchone()[0] == 0
            assert db_conn.execute("SELECT COUNT(*) FROM attendance WHERE employee_id=?", (employee_id,)).fetchone()[0] == 0
        finally:
            db_conn.close()
    finally:
        api_server.app.dependency_overrides.clear()
        api_server.app.dependency_overrides.update(original_overrides)


def test_task_api_round_trips_desktop_fields_and_preserves_submission_timestamp():
    import secrets
    import sqlite3

    employee = client.post("/api/employees", json={
        "name": "Task Parity Employee",
        "employee_code": "TASK-PARITY-" + secrets.token_hex(3).upper(),
        "department": "Operations",
    })
    assert employee.status_code == 200
    employee_id = employee.json()["id"]
    task_date = "2026-11-05"
    payload = {
        "employee_id": employee_id,
        "task_date": task_date,
        "title": "Full task parity regression",
        "department": "Operations",
        "details": "Task description retained",
        "due_time": "17:45",
        "priority": "Urgent",
        "status": "Completed",
        "progress": 75,
        "target_qty": "12",
        "actual_qty": "12",
        "proof_url": "https://example.test/evidence/one\nhttps://example.test/evidence/two",
        "proof_note": "Two evidence links",
        "next_action": "Review evidence",
        "manager_note": "Review evidence",
        "expose_link": 1,
        "custom_values": [
            {"key": "Tracked By", "value": "QA"},
            {"key": "Equipment", "value": "Rig 4"},
        ],
    }
    created = client.post("/api/tasks", json=payload)
    assert created.status_code == 200
    task_id = created.json()["id"]
    assert created.json()["progress"] == 100
    assert created.json()["submitted_at"]

    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        connection.execute("UPDATE tasks SET submitted_at=? WHERE id=?", ("2026-10-30 09:15:00", task_id))
        connection.commit()
    finally:
        connection.close()

    updated_payload = {**payload, "status": "Completed", "progress": 100, "proof_note": "Verified"}
    updated = client.put(f"/api/tasks/{task_id}", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["submitted_at"] == "2026-10-30 09:15:00"

    filtered = client.get(f"/api/tasks?employee_id={employee_id}&task_date={task_date}")
    assert filtered.status_code == 200
    row = next(item for item in filtered.json() if item["id"] == task_id)
    assert row["due_time"] == "17:45"
    assert row["details"] == "Task description retained"
    assert row["target_qty"] == "12" and row["actual_qty"] == "12"
    assert row["proof_note"] == "Verified"
    assert row["expose_link"] == 1
    assert row["submitted_at"] == "2026-10-30 09:15:00"
    custom = {item["key"]: item["value"] for item in row["custom_fields"]}
    assert custom == {"Tracked By": "QA", "Equipment": "Rig 4"}

    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        connection.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        connection.execute("DELETE FROM employees WHERE id=?", (employee_id,))
        connection.commit()
    finally:
        connection.close()


def test_task_bulk_edit_changes_only_selected_fields_and_sets_submission_time():
    import secrets
    import sqlite3

    employee = client.post("/api/employees", json={
        "name": "Task Bulk Parity Employee",
        "employee_code": "TASK-BULK-" + secrets.token_hex(3).upper(),
        "department": "Operations",
    })
    assert employee.status_code == 200
    employee_id = employee.json()["id"]
    created_ids = []
    for title in ("Bulk task one", "Bulk task two", "Untouched task"):
        created = client.post("/api/tasks", json={
            "employee_id": employee_id,
            "task_date": "2026-11-05",
            "title": title,
            "target_qty": "25",
            "actual_qty": "4",
            "priority": "Low",
            "status": "Not started",
            "next_action": "Original follow-up",
            "custom_values": [{"key": "Client", "value": "Keep this value"}],
        })
        assert created.status_code == 200
        created_ids.append(created.json()["id"])

    result = client.post("/api/tasks/bulk-edit", json={
        "task_ids": created_ids[:2],
        "updates": {"title": "Bulk-updated task", "status": "Completed", "next_action": "Bulk follow-up", "expose_link": True, "custom_values": "Client: Bulk\nLocation: Zone 2"},
    })
    assert result.status_code == 200
    assert result.json()["updated"] == 2
    rows = client.get("/api/tasks?employee_id=" + str(employee_id)).json()
    by_id = {row["id"]: row for row in rows}
    for task_id in created_ids[:2]:
        row = by_id[task_id]
        assert row["title"] == "Bulk-updated task"
        assert row["status"] == "Completed" and row["progress"] == 100
        assert row["target_qty"] == "25" and row["actual_qty"] == "4"
        assert row["next_action"] == "Bulk follow-up"
        assert row["manager_note"] == "Bulk follow-up"
        assert row["expose_link"] == 1
        assert row["submitted_at"]
        custom = {item["key"]: item["value"] for item in row["custom_fields"]}
        assert custom == {"Client": "Bulk", "Location": "Zone 2"}
    untouched = by_id[created_ids[2]]
    assert untouched["status"] == "Not started"
    assert untouched["target_qty"] == "25" and untouched["actual_qty"] == "4"

    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        connection.executemany("DELETE FROM tasks WHERE id=?", [(task_id,) for task_id in created_ids])
        connection.execute("DELETE FROM employees WHERE id=?", (employee_id,))
        connection.commit()
    finally:
        connection.close()


def test_task_delete_is_restricted_to_admin_and_developer():
    import secrets

    employee = client.post("/api/employees", json={
        "name": "Task Permission Employee",
        "employee_code": "TASK-RBAC-" + secrets.token_hex(3).upper(),
        "department": "Operations",
    })
    assert employee.status_code == 200
    employee_id = employee.json()["id"]
    created = client.post("/api/tasks", json={
        "employee_id": employee_id,
        "task_date": "2026-11-05",
        "title": "Task deletion permission regression",
    })
    assert created.status_code == 200
    task_id = created.json()["id"]
    original_overrides = dict(api_server.app.dependency_overrides)
    try:
        api_server.app.dependency_overrides[api_server.get_current_user] = lambda: {
            "id": 991001, "username": "task-staff-test", "display_name": "Task Staff Test", "role": "Staff"
        }
        denied = client.delete(f"/api/tasks/{task_id}")
        assert denied.status_code == 403
        api_server.app.dependency_overrides[api_server.get_current_user] = lambda: {
            "id": 991002, "username": "task-admin-test", "display_name": "Task Admin Test", "role": "Admin"
        }
        allowed = client.delete(f"/api/tasks/{task_id}")
        assert allowed.status_code == 200
    finally:
        api_server.app.dependency_overrides.clear()
        api_server.app.dependency_overrides.update(original_overrides)
    import sqlite3
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        connection.execute("DELETE FROM employees WHERE id=?", (employee_id,))
        connection.commit()
    finally:
        connection.close()


def test_task_api_preserves_explicit_not_selected_status():
    import secrets
    import sqlite3

    employee = client.post("/api/employees", json={
        "name": "Task Blank Status Employee",
        "employee_code": "TASK-BLANK-" + secrets.token_hex(3).upper(),
        "department": "Operations",
    })
    assert employee.status_code == 200
    employee_id = employee.json()["id"]
    payload = {
        "employee_id": employee_id,
        "task_date": "2026-11-05",
        "title": "Task with no selected status",
        "status": "",
    }
    created = client.post("/api/tasks", json=payload)
    assert created.status_code == 200
    task_id = created.json()["id"]
    assert created.json()["status"] == ""
    filtered = client.get("/api/tasks?status=")
    assert filtered.status_code == 200
    assert any(row["id"] == task_id and row["status"] == "" for row in filtered.json())
    updated = client.put(f"/api/tasks/{task_id}", json=payload)
    assert updated.status_code == 200
    assert updated.json()["status"] == ""

    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        connection.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        connection.execute("DELETE FROM employees WHERE id=?", (employee_id,))
        connection.commit()
    finally:
        connection.close()

def test_employee_tracker_task_list_filters_by_employee_and_date():
    import secrets
    import sqlite3

    employee_a = client.post("/api/employees", json={
        "name": "Tracker Filter Employee A",
        "employee_code": "TRACKER-A-" + secrets.token_hex(3).upper(),
        "department": "Operations",
    })
    employee_b = client.post("/api/employees", json={
        "name": "Tracker Filter Employee B",
        "employee_code": "TRACKER-B-" + secrets.token_hex(3).upper(),
        "department": "Operations",
    })
    assert employee_a.status_code == 200 and employee_b.status_code == 200
    employee_a_id = employee_a.json()["id"]
    employee_b_id = employee_b.json()["id"]
    created_ids = []
    for employee_id, task_date, title in (
        (employee_a_id, "2026-11-05", "Tracker selected day"),
        (employee_a_id, "2026-11-04", "Tracker previous day"),
        (employee_b_id, "2026-11-05", "Tracker other employee"),
    ):
        created = client.post("/api/tasks", json={
            "employee_id": employee_id,
            "task_date": task_date,
            "title": title,
            "status": "In progress",
            "progress": 40,
        })
        assert created.status_code == 200
        created_ids.append(created.json()["id"])

    filtered = client.get(
        f"/api/tasks?employee_id={employee_a_id}&task_date=2026-11-05"
    )
    assert filtered.status_code == 200
    assert [row["id"] for row in filtered.json() if row["id"] in created_ids] == [created_ids[0]]

    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        connection.executemany("DELETE FROM tasks WHERE id=?", [(task_id,) for task_id in created_ids])
        connection.executemany("DELETE FROM employees WHERE id=?", [(employee_a_id,), (employee_b_id,)])
        connection.commit()
    finally:
        connection.close()


def test_employee_tracker_web_tab_exposes_desktop_task_workflow():
    app_source = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    tracker_source = (ROOT / "frontend" / "src" / "TaskManager.jsx").read_text(encoding="utf-8")

    assert 'mode="tracker"' in app_source
    assert "Employee Activity &amp; Progression" in tracker_source
    assert "Select employee" in tracker_source
    assert "Task date" in tracker_source
    assert "Average task progress" in tracker_source
    assert "completed','submitted','cancelled','blocked','in progress" in tracker_source
    assert "onClick={()=>openEdit(task)}" in tracker_source
    assert "onClick={()=>openProof(task)}" in tracker_source
    assert "{canDelete&&" in tracker_source


def test_web_print_center_preview_applies_employee_exclusion_and_field_options():
    import secrets
    suffix = secrets.token_hex(4).upper()
    included = client.post("/api/employees", json={
        "name": "Report Included " + suffix,
        "employee_code": "RPT-IN-" + suffix,
        "notes": "PRIVATE_INCLUDED_NOTE",
        "email": "report-in-" + suffix.lower() + "@example.test",
    })
    excluded = client.post("/api/employees", json={
        "name": "Report Excluded " + suffix,
        "employee_code": "RPT-EX-" + suffix,
        "notes": "PRIVATE_EXCLUDED_NOTE",
    })
    assert included.status_code == 200
    assert excluded.status_code == 200

    response = client.post("/api/reports/preview", json={
        "date": date.today().isoformat(),
        "report_type": "Employee Details",
        "exclude_employee_id": excluded.json()["id"],
        "options": {
            "details_identity": True,
            "details_contact": False,
            "details_joining": False,
            "details_status": True,
            "details_notes": False,
        },
    })
    assert response.status_code == 200
    preview = response.json()["preview_text"]
    assert included.json()["name"] in preview
    assert excluded.json()["name"] not in preview
    assert "PRIVATE_INCLUDED_NOTE" not in preview
    assert "PRIVATE_EXCLUDED_NOTE" not in preview
    assert included.json()["email"] not in preview


def test_web_print_center_exports_pdf_docx_and_csv():
    import secrets
    suffix = secrets.token_hex(4).upper()
    created = client.post("/api/employees", json={
        "name": "Report Export " + suffix,
        "employee_code": "RPT-OUT-" + suffix,
        "department": "Export QA",
    })
    assert created.status_code == 200

    base_payload = {
        "date": date.today().isoformat(),
        "report_type": "Employee Details",
        "employee_id": created.json()["id"],
        "options": {
            "details_identity": True,
            "details_contact": True,
            "details_joining": True,
            "details_status": True,
            "details_notes": False,
        },
    }
    csv_response = client.post("/api/reports/export", json={**base_payload, "output_format": "csv"})
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert csv_response.content.startswith(b"\xef\xbb\xbf")
    assert b"Report Export " in csv_response.content

    docx_response = client.post("/api/reports/export", json={**base_payload, "output_format": "docx"})
    assert docx_response.status_code == 200
    assert docx_response.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert docx_response.content.startswith(b"PK")

    pdf_response = client.post("/api/reports/export", json={**base_payload, "output_format": "pdf"})
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert pdf_response.content.startswith(b"%PDF-")
