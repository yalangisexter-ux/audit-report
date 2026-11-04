"""Unit tests for FastAPI REST API endpoints.
Validates that all business logic, endpoints, and custom task tracking work seamlessly over HTTP.
"""
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
if hasattr(_test_db, "close_github_sync"):
    _test_db.close_github_sync(timeout=0)
if hasattr(_test_db, "conn") and _test_db.conn:
    _test_db.conn.close()

from fastapi.testclient import TestClient
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
