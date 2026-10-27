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
    # 1. Mark attendance
    mark_payload = {
        "employee_id": 1,
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
