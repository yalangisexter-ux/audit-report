"""Unit tests for FastAPI REST API endpoints.
Validates that all business logic, endpoints, and custom task tracking work seamlessly over HTTP.
"""
import sqlite3
from datetime import date
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

def test_render_root_head_probe_returns_success():
    response = client.head("/")
    assert response.status_code == 200
    assert response.content == b""

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

def test_legacy_bulk_attendance_requires_authenticated_session(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    work_date = "2999-01-01"
    params = {"work_date": work_date, "status": "Present"}

    denied = client.post("/api/attendance/bulk", params=params)
    assert denied.status_code == 401

    token = "legacy-attendance-bulk-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 990301,
        "username": "legacy-attendance-bulk-test",
        "display_name": "Legacy Attendance Bulk Test",
        "role": "Staff",
    }
    try:
        allowed = client.post(
            "/api/attendance/bulk",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["success"] is True
        assert isinstance(allowed.json()["count"], int)
    finally:
        api_server.ACTIVE_SESSIONS.pop(token, None)
        connection = sqlite3.connect(str(desktop_app.DB_PATH))
        try:
            connection.execute("DELETE FROM attendance WHERE work_date=?", (work_date,))
            connection.commit()
        finally:
            connection.close()


def test_holiday_management_requires_authorized_role_and_valid_dates():
    from fastapi import HTTPException

    dependency = api_server.get_current_user
    app.dependency_overrides[dependency] = lambda: {"username": "customer-test", "role": "Customer"}
    try:
        denied = client.post("/api/holidays", json={
            "holiday_date": "2026-12-25",
            "holiday_name": "Christmas",
        })
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.pop(dependency, None)

    app.dependency_overrides[dependency] = lambda: {"username": "hr-test", "role": "HR"}
    try:
        invalid = client.post("/api/holidays", json={
            "holiday_date": "25-12-2026",
            "holiday_name": "Christmas",
        })
        assert invalid.status_code == 422

        saved = client.post("/api/holidays", json={
            "holiday_date": "2026-12-25",
            "holiday_name": " Christmas ",
        })
        assert saved.status_code == 200
        rows = client.get("/api/holidays")
        assert rows.status_code == 200
        assert any(
            row["holiday_date"] == "2026-12-25" and row["holiday_name"] == "Christmas"
            for row in rows.json()
        )
        removed = client.delete("/api/holidays/2026-12-25")
        assert removed.status_code == 200
    finally:
        app.dependency_overrides.pop(dependency, None)


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


def test_api_business_tracking(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    token = "business-list-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 990, "username": "business-list-test", "display_name": "Business Test", "role": "Admin"
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        assert client.get("/api/business/products").status_code == 401
        assert client.get("/api/business/services").status_code == 401
        assert client.get("/api/business/orders").status_code == 401
        assert client.get("/api/business/members").status_code == 401
        assert client.get("/api/business/activities").status_code == 401
        assert client.get("/api/business/overview").status_code == 401
        assert client.get("/api/business/stock-ledger").status_code == 401

        for path in (
            "/api/business/products", "/api/business/services", "/api/business/orders",
            "/api/business/members", "/api/business/activities", "/api/business/overview",
            "/api/business/stock-ledger",
        ):
            response = client.get(path, headers=headers)
            assert response.status_code == 200, (path, response.text)
    finally:
        api_server.ACTIVE_SESSIONS.pop(token, None)


def test_business_tracking_full_workflow_and_stock_ledger(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_STANDALONE", "0")
    token = "business-workflow-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 991, "username": "business-workflow-test", "display_name": "Business Workflow Test", "role": "Admin"
    }
    headers = {"Authorization": f"Bearer {token}"}
    sku = "BT-" + secrets.token_hex(5).upper()
    employee_code = "BIZ-" + secrets.token_hex(4).upper()
    product_id = service_id = member_id = order_id = activity_id = employee_id = None
    try:
        product = client.post("/api/business/products", headers=headers, json={
            "name": "Business Ledger Test Product", "sku": sku, "category": "equipment",
            "brand": "RSC", "package_type": "Box", "base_unit": "PCS",
            "opening_stock": 20, "received_qty": 5, "reserved_qty": 0,
            "dispatched_qty": 0, "free_qty": 0, "returned_qty": 0,
            "damaged_qty": 0, "expired_qty": 0, "quarantined_qty": 0,
            "purchase_cost": 40, "selling_price": 75, "reorder_level": 2,
            "batch_number": "BATCH-01", "expiry_date": "2027-12-31", "storage_location": "Rack A",
        })
        assert product.status_code == 200, product.text
        product_id = product.json()["id"]

        listed = client.get("/api/business/products", headers=headers)
        item = next(row for row in listed.json() if row["id"] == product_id)
        assert item["available_stock"] == 25
        assert item["package_type"] == "Box" and item["batch_number"] == "BATCH-01"

        for movement, quantity, expected in (("reserve", 3, 22), ("dispatch", 2, 20), ("release", 1, 21)):
            result = client.post("/api/business/stock-ledger", headers=headers, json={
                "product_id": product_id, "txn_type": movement, "quantity": quantity, "unit": "PCS",
                "reference": "TEST-ORDER", "notes": "Automated ledger regression",
            })
            assert result.status_code == 200, result.text
            assert result.json()["available_stock"] == expected

        ledger = client.get("/api/business/stock-ledger", headers=headers, params={"product_id": product_id})
        assert ledger.status_code == 200 and len(ledger.json()) == 3
        overdraw = client.post("/api/business/stock-ledger", headers=headers, json={
            "product_id": product_id, "txn_type": "dispatch", "quantity": 999,
        })
        assert overdraw.status_code == 409

        service = client.post("/api/business/services", headers=headers, json={
            "name": "Business API Coaching", "category": "Strength", "description": "Regression service",
            "training_mode": "Hybrid", "service_unit": "Session", "session_duration": 60,
            "num_sessions": 8, "plan_validity": 30, "standard_price": 1500, "active": 1,
        })
        assert service.status_code == 200, service.text
        service_id = service.json()["id"]

        employee = client.post("/api/employees", headers=headers, json={
            "name": "Business Workflow Employee", "employee_code": employee_code, "department": "Operations",
        })
        assert employee.status_code == 200, employee.text
        employee_id = employee.json()["id"]

        order = client.post("/api/business/orders", headers=headers, json={
            "order_code": "ORD-" + secrets.token_hex(3).upper(), "customer_name": "Test Customer",
            "order_date": date.today().isoformat(), "channel": "gym counter", "contact": "9999999999",
            "payment_mode": "UPI", "status": "Pending", "discount": 50, "order_value": 1500,
            "invoice_number": "INV-TEST", "shipment_id": "SHIP-TEST", "assigned_employee_id": employee_id,
            "notes": "Order workflow regression",
        })
        assert order.status_code == 200, order.text
        order_id = order.json()["id"]
        assert client.patch(f"/api/business/orders/{order_id}", headers=headers, json={"status": "Confirmed"}).status_code == 200

        member = client.post("/api/business/members", headers=headers, json={
            "full_name": "Business Test Member", "service_id": service_id, "phone": "8888888888",
            "training_mode": "Hybrid", "registration_date": date.today().isoformat(),
            "start_date": date.today().isoformat(), "end_date": "2026-12-31",
            "sessions_purchased": 8, "sessions_completed": 2, "assigned_trainer_id": employee_id,
            "status": "Active", "payment_status": "Paid", "invoice_ref": "MEM-TEST",
            "notes": "Member workflow regression",
        })
        assert member.status_code == 200, member.text
        member_id = member.json()["id"]
        update_member = client.patch(f"/api/business/members/{member_id}", headers=headers, json={
            "sessions_completed": 3, "payment_status": "Paid",
        })
        assert update_member.status_code == 200
        member_row = next(row for row in client.get("/api/business/members", headers=headers).json() if row["id"] == member_id)
        assert member_row["sessions_completed"] == 3 and member_row["sessions_purchased"] == 8

        activity = client.post("/api/business/activities", headers=headers, json={
            "employee_id": employee_id, "related_order_id": order_id, "related_service_id": service_id,
            "task_type": "Training", "product_id": product_id, "quantity": 2, "unit": "Session",
            "task_status": "In Progress", "proof_ref": "https://example.invalid/proof",
            "remarks": "Activity workflow regression",
        })
        assert activity.status_code == 200, activity.text
        activity_id = activity.json()["id"]
        assert client.patch(f"/api/business/activities/{activity_id}", headers=headers, json={
            "task_status": "Completed",
        }).status_code == 200
        activity_row = next(row for row in client.get("/api/business/activities", headers=headers).json() if row["id"] == activity_id)
        assert activity_row["employee_name"] == "Business Workflow Employee"
        assert activity_row["completion_time"]

        overview = client.get("/api/business/overview", headers=headers).json()
        assert overview["products"] >= 1 and overview["orders"] >= 1
        assert overview["members"] >= 1 and overview["activities"] >= 1
    finally:
        connection = sqlite3.connect(str(desktop_app.DB_PATH))
        try:
            if activity_id is not None:
                connection.execute("DELETE FROM bt_activities WHERE id=?", (activity_id,))
            if member_id is not None:
                connection.execute("DELETE FROM bt_members WHERE id=?", (member_id,))
            if order_id is not None:
                connection.execute("DELETE FROM bt_orders WHERE id=?", (order_id,))
            if product_id is not None:
                connection.execute("DELETE FROM bt_stock_ledger WHERE product_id=?", (product_id,))
                connection.execute("DELETE FROM bt_products WHERE id=?", (product_id,))
            if service_id is not None:
                connection.execute("DELETE FROM bt_services WHERE id=?", (service_id,))
            if employee_id is not None:
                connection.execute("DELETE FROM employees WHERE id=?", (employee_id,))
            connection.commit()
        finally:
            connection.close()
        api_server.ACTIVE_SESSIONS.pop(token, None)


def test_api_settings_require_admin_session(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    admin_token = "settings-admin-" + secrets.token_hex(8)
    staff_token = "settings-staff-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[admin_token] = {
        "id": 9801, "username": "settings-admin", "display_name": "Settings Admin", "role": "Admin"
    }
    api_server.ACTIVE_SESSIONS[staff_token] = {
        "id": 9802, "username": "settings-staff", "display_name": "Settings Staff", "role": "Staff"
    }
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        assert client.get("/api/settings").status_code == 401
        assert client.post("/api/settings", json={"settings_permission_test": "1"}).status_code == 401
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        assert client.get("/api/settings", headers=staff_headers).status_code == 403
        assert client.post("/api/settings", headers=staff_headers, json={"settings_permission_test": "1"}).status_code == 403

        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/api/settings", headers=admin_headers)
        assert response.status_code == 200
        assert "settings" in response.json()
        assert "app_version" in response.json()
        updated = client.post(
            "/api/settings", headers=admin_headers, json={"settings_permission_test": "1"}
        )
        assert updated.status_code == 200
        assert connection.execute(
            "SELECT value FROM settings WHERE key='settings_permission_test'"
        ).fetchone()[0] == "1"
    finally:
        connection.execute("DELETE FROM settings WHERE key='settings_permission_test'")
        connection.commit()
        connection.close()
        api_server.ACTIVE_SESSIONS.pop(admin_token, None)
        api_server.ACTIVE_SESSIONS.pop(staff_token, None)

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
        weekdays.add(6)
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


def test_web_working_weekday_settings_require_admin_and_keep_sunday(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    admin_token = "working-week-admin-" + secrets.token_hex(8)
    staff_token = "working-week-staff-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[admin_token] = {
        "id": 9803, "username": "working-week-admin", "display_name": "Working Week Admin", "role": "Admin"
    }
    api_server.ACTIVE_SESSIONS[staff_token] = {
        "id": 9804, "username": "working-week-staff", "display_name": "Working Week Staff", "role": "Staff"
    }
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    original = connection.execute(
        "SELECT value FROM settings WHERE key='working_weekdays'"
    ).fetchone()
    try:
        connection.execute(
            "INSERT INTO settings(key,value) VALUES('working_weekdays','0,1,2,3,4') "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
        )
        connection.commit()

        assert client.get("/api/settings/working-weekdays").status_code == 401
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        assert client.get("/api/settings/working-weekdays", headers=staff_headers).status_code == 403
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        current = client.get("/api/settings/working-weekdays", headers=admin_headers)
        assert current.status_code == 200
        assert current.json()["weekdays"] == [0, 1, 2, 3, 4, 6]
        assert current.json()["sunday_required"] is True

        saved = client.put(
            "/api/settings/working-weekdays",
            headers=admin_headers,
            json={"weekdays": [0, 1, 2, 3, 4]},
        )
        assert saved.status_code == 200
        assert saved.json()["weekdays"] == [0, 1, 2, 3, 4, 6]
        assert connection.execute(
            "SELECT value FROM settings WHERE key='working_weekdays'"
        ).fetchone()[0] == "0,1,2,3,4,6"

        invalid = client.put(
            "/api/settings/working-weekdays",
            headers=admin_headers,
            json={"weekdays": [0, 7]},
        )
        assert invalid.status_code == 422
    finally:
        if original:
            connection.execute(
                "UPDATE settings SET value=? WHERE key='working_weekdays'", (original[0],)
            )
        else:
            connection.execute("DELETE FROM settings WHERE key='working_weekdays'")
        connection.commit()
        connection.close()
        api_server.ACTIVE_SESSIONS.pop(admin_token, None)
        api_server.ACTIVE_SESSIONS.pop(staff_token, None)


def test_api_attendance_summary_counts_sunday_with_legacy_weekday_setting(monkeypatch):
    from datetime import timedelta
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    token = "sunday-attendance-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 9805, "username": "sunday-attendance", "display_name": "Sunday Attendance", "role": "Admin"
    }
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    original = connection.execute(
        "SELECT value FROM settings WHERE key='working_weekdays'"
    ).fetchone()
    employee_id = None
    try:
        holidays = {
            row[0] for row in connection.execute("SELECT holiday_date FROM holidays").fetchall()
        }
        sunday = date.today() - timedelta(days=(date.today().weekday() + 1) % 7)
        for _ in range(52):
            if sunday.isoformat() not in holidays:
                break
            sunday -= timedelta(days=7)
        else:
            raise AssertionError("Could not find a non-holiday Sunday for attendance summary testing")

        connection.execute(
            "INSERT INTO settings(key,value) VALUES('working_weekdays','0,1,2,3,4') "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
        )
        connection.commit()
        headers = {"Authorization": f"Bearer {token}"}
        employee = client.post(
            "/api/employees",
            headers=headers,
            json={
                "name": "Sunday Attendance Summary Test",
                "employee_code": "ATT-SUNDAY-" + secrets.token_hex(4).upper(),
                "joining_date": sunday.isoformat(),
                "department": "Testing",
            },
        )
        assert employee.status_code == 200, employee.text
        employee_id = int(employee.json()["id"])

        marked = client.post(
            "/api/attendance/mark",
            headers=headers,
            json={
                "employee_id": employee_id,
                "work_date": sunday.isoformat(),
                "attendance_status": "Present",
                "check_in": "09:00",
                "check_out": "17:00",
            },
        )
        assert marked.status_code == 200, marked.text

        response = client.get(
            "/api/attendance/summary",
            headers=headers,
            params={"work_date": sunday.isoformat()},
        )
        assert response.status_code == 200, response.text
        summary = next(row for row in response.json()["rows"] if row["employee_id"] == employee_id)
        assert summary["work_days"] == 1
        assert summary["present"] == 1
        assert summary["absent"] == 0
        assert summary["leave"] == 0
        assert summary["total_present"] == 1
    finally:
        if employee_id is not None:
            connection.execute("DELETE FROM attendance WHERE employee_id=?", (employee_id,))
            connection.execute("DELETE FROM employees WHERE id=?", (employee_id,))
        if original:
            connection.execute(
                "UPDATE settings SET value=? WHERE key='working_weekdays'", (original[0],)
            )
        else:
            connection.execute("DELETE FROM settings WHERE key='working_weekdays'")
        connection.commit()
        connection.close()
        api_server.ACTIVE_SESSIONS.pop(token, None)


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
    included_name = "Report Included " + suffix
    excluded_name = "Report Excluded " + suffix
    included_email = "report-in-" + suffix.lower() + "@example.test"
    included = client.post("/api/employees", json={
        "name": included_name,
        "employee_code": "RPT-IN-" + suffix,
        "notes": "PRIVATE_INCLUDED_NOTE",
        "email": included_email,
    })
    excluded = client.post("/api/employees", json={
        "name": excluded_name,
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
    assert included_name in preview
    assert excluded_name not in preview
    assert "PRIVATE_INCLUDED_NOTE" not in preview
    assert "PRIVATE_EXCLUDED_NOTE" not in preview
    assert included_email not in preview


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
    assert csv_response.headers["cache-control"] == "no-store, no-cache, must-revalidate"
    assert csv_response.headers["x-content-type-options"] == "nosniff"
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
    # Print Center must generate the same branded, multi-page PDF structure as the desktop EXE.
    assert b"/Subtype /Image" in pdf_response.content  # embedded Raw Strength logo
    assert b"/Author (Raw Strength Calisthenics)" in pdf_response.content
    assert b"/Title (Employee Details)" in pdf_response.content
    # ReportLab embeds the font using its internal DejaVu face name and a subset prefix,
    # not the registration alias (RawStrengthSans). Verify the actual TTF is embedded.
    assert b"DejaVuSans" in pdf_response.content
    assert b"/FontFile2" in pdf_response.content

    # Each supported Print Center report type uses the same branded PDF renderer.
    for report_type in ("Audit / EOD", "Employee Attendance", "Employee Productivity"):
        typed_pdf = client.post(
            "/api/reports/export",
            json={**base_payload, "report_type": report_type, "output_format": "pdf"},
        )
        assert typed_pdf.status_code == 200
        assert typed_pdf.headers["content-type"].startswith("application/pdf")
        assert typed_pdf.content.startswith(b"%PDF-")
        assert b"/Subtype /Image" in typed_pdf.content

    # The Print Center preview action opens this generated PDF, not a browser print of page text.
    print_center_source = (ROOT / "frontend" / "src" / "PrintCenter.jsx").read_text(encoding="utf-8")
    assert "output_format: 'pdf'" in print_center_source
    assert "window.print()" not in print_center_source
    assert "Open PDF preview / Print" in print_center_source

def test_web_business_products_and_print_center_use_full_stock_ledger(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    token = "stock-ledger-report-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 992, "username": "stock-ledger-report", "display_name": "Stock Ledger Report", "role": "Admin"
    }
    headers = {"Authorization": f"Bearer {token}"}
    sku = "STOCK-" + secrets.token_hex(4).upper()
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    connection.row_factory = sqlite3.Row
    try:
        business_tracking.setup_business_tables(connection)
        connection.execute(
            """INSERT INTO bt_products(
                sku,name,category,brand,base_unit,opening_stock,received_qty,
                reserved_qty,dispatched_qty,free_qty,returned_qty,damaged_qty,
                expired_qty,quarantined_qty,reorder_level,selling_price,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sku, "Ledger Stock Regression", "QA", "Raw Strength", "PCS",
                100, 50, 10, 20, 5, 3, 2, 1, 4, 10, 25, "2026-11-05 00:00:00",
            ),
        )
        connection.commit()

        products_response = client.get("/api/business/products", headers=headers)
        assert products_response.status_code == 200
        product = next(row for row in products_response.json() if row["sku"] == sku)
        assert product["available_stock"] == 111

        report = api_server._build_report_preview(
            api_server.ReportOptionsModel(
                date=date.today().isoformat(),
                report_type="Audit / EOD",
                options={"business_products": True},
            ),
            connection,
        )
        assert "Ledger Stock Regression" in report["preview_text"]
        assert " | 111 | " in report["preview_text"]
    finally:
        api_server.ACTIVE_SESSIONS.pop(token, None)
        connection.execute("DELETE FROM bt_products WHERE sku=?", (sku,))
        connection.commit()
        connection.close()


def test_web_archive_read_requires_login_and_supports_view_export_and_rbac(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    staff_token = "archive-staff-" + secrets.token_hex(8)
    admin_token = "archive-admin-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[staff_token] = {
        "id": 901, "username": "archive-staff", "display_name": "Archive Staff", "role": "Staff"
    }
    api_server.ACTIVE_SESSIONS[admin_token] = {
        "id": 902, "username": "archive-admin", "display_name": "Archive Admin", "role": "Admin"
    }
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    connection.row_factory = sqlite3.Row
    pdf_content = b"%PDF-1.4\\narchive access regression\\n%%EOF"
    try:
        cursor = connection.execute(
            """INSERT INTO archived_documents(
                employee_id,report_date,file_name,mime_type,content,notes,uploaded_at
            ) VALUES(NULL,?,?,?,?,?,?)""",
            ("2026-11-04", "archive-access-test.pdf", "application/pdf",
             sqlite3.Binary(pdf_content), "access regression", "2026-11-04 09:00:00"),
        )
        document_id = cursor.lastrowid
        connection.commit()

        assert client.get("/api/archive").status_code == 401
        assert client.get(f"/api/archive/{document_id}/view").status_code == 401
        assert client.get(f"/api/archive/{document_id}/download").status_code == 401

        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        listed = client.get("/api/archive", headers=staff_headers)
        assert listed.status_code == 200
        assert any(row["id"] == document_id for row in listed.json())

        viewed = client.get(f"/api/archive/{document_id}/view", headers=staff_headers)
        assert viewed.status_code == 200
        assert viewed.content == pdf_content
        assert viewed.headers["content-disposition"].startswith("inline;")
        assert "no-store" in viewed.headers["cache-control"]
        assert viewed.headers["x-content-type-options"] == "nosniff"

        exported = client.get(f"/api/archive/{document_id}/download", headers=staff_headers)
        assert exported.status_code == 200
        assert exported.content == pdf_content
        assert exported.headers["content-disposition"].startswith("attachment;")
        assert "no-store" in exported.headers["cache-control"]

        assert client.delete(f"/api/archive/{document_id}", headers=staff_headers).status_code == 403
        deleted = client.delete(
            f"/api/archive/{document_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert deleted.status_code == 200
        assert client.get(f"/api/archive/{document_id}/view", headers=staff_headers).status_code == 404
    finally:
        api_server.ACTIVE_SESSIONS.pop(staff_token, None)
        api_server.ACTIVE_SESSIONS.pop(admin_token, None)
        connection.execute("DELETE FROM archived_documents WHERE file_name=?", ("archive-access-test.pdf",))
        connection.commit()
        connection.close()


def test_web_archive_upload_preserves_employee_date_and_notes(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    token = "archive-upload-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 903, "username": "archive-admin", "display_name": "Archive Admin", "role": "Admin"
    }
    headers = {"Authorization": f"Bearer {token}"}
    employee_code = "ARC-" + secrets.token_hex(4).upper()
    employee_id = None
    archive_id = None
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        employee_response = client.post(
            "/api/employees",
            json={"name": "Archive Association Test", "employee_code": employee_code, "department": "QA"},
            headers=headers,
        )
        assert employee_response.status_code == 200
        employee_id = employee_response.json()["id"]

        pdf_content = b"%PDF-1.4\\nmetadata upload regression\\n%%EOF"
        uploaded = client.post(
            "/api/archive",
            data={
                "employee_id": str(employee_id),
                "report_date": "2026-11-04",
                "notes": "Imported from desktop archive",
            },
            files={"file": ("history.pdf", pdf_content, "application/pdf")},
            headers=headers,
        )
        assert uploaded.status_code == 200
        archive_id = uploaded.json()["id"]

        listed = client.get("/api/archive", headers=headers)
        assert listed.status_code == 200
        row = next(item for item in listed.json() if item["id"] == archive_id)
        assert row["employee_id"] == employee_id
        assert row["employee_name"] == "Archive Association Test"
        assert row["report_date"] == "2026-11-04"
        assert row["notes"] == "Imported from desktop archive"

        invalid = client.post(
            "/api/archive",
            data={"report_date": "2026-11-04"},
            files={"file": ("not-a-pdf.pdf", b"not a pdf", "application/pdf")},
            headers=headers,
        )
        assert invalid.status_code == 400
    finally:
        api_server.ACTIVE_SESSIONS.pop(token, None)
        if archive_id is not None:
            connection.execute("DELETE FROM archived_documents WHERE id=?", (archive_id,))
        if employee_id is not None:
            connection.execute("DELETE FROM employees WHERE id=?", (employee_id,))
        connection.commit()
        connection.close()



def test_web_system_database_info_and_manual_encrypted_sync_require_login(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    token = "web-system-settings-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 950, "username": "web-system-settings", "display_name": "Web System Settings", "role": "Admin"
    }

    class FakeSyncManager:
        def public_status(self):
            return {
                "configured": True, "status": "Synced", "dirty": False, "busy": False,
                "last_sync": "2026-11-05T00:00:00", "last_error": "", "installation_id": "a" * 32,
                "last_pull": {"usernames": ["must-not-be-exposed"]},
            }

        def sync_now(self, conn):
            assert conn.execute("SELECT 1").fetchone()[0] == 1
            return {"success": True, "status": "Synced", "inserted": 0, "updated": 0, "conflicts": 0}

    monkeypatch.setattr(api_server, "WEB_SYNC_MANAGER", FakeSyncManager())
    headers = {"Authorization": f"Bearer {token}"}
    try:
        assert client.get("/api/system/db-info").status_code == 401
        info = client.get("/api/system/db-info", headers=headers)
        assert info.status_code == 200
        payload = info.json()
        assert payload["database_connected"] is True
        assert payload["database_integrity"] == "ok"
        assert payload["app_version"]
        assert "database_path" not in payload
        assert "must-not-be-exposed" not in info.text
        assert payload["sync"]["configured"] is True

        synced = client.post("/api/system/sync-now", headers=headers)
        assert synced.status_code == 200
        assert synced.json()["success"] is True
        assert synced.json()["status"] == "Synced"
    finally:
        api_server.ACTIVE_SESSIONS.pop(token, None)


def test_web_database_backup_is_authenticated_and_restore_is_admin_only(monkeypatch, tmp_path):
    import secrets

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    staff_token = "web-db-staff-" + secrets.token_hex(8)
    admin_token = "web-db-admin-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[staff_token] = {
        "id": 951, "username": "web-db-staff", "display_name": "Web DB Staff", "role": "Staff"
    }
    api_server.ACTIVE_SESSIONS[admin_token] = {
        "id": 952, "username": "web-db-admin", "display_name": "Web DB Admin", "role": "Admin"
    }
    monkeypatch.setattr(desktop_app, "EXPORT_DIR", tmp_path)
    previous_sessions = {
        key: value for key, value in api_server.ACTIVE_SESSIONS.items()
        if key not in {staff_token, admin_token}
    }
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    database_path = Path(desktop_app.DB_PATH)
    preimport_backups = set(database_path.parent.glob(
        database_path.stem + ".before-import-*" + database_path.suffix
    ))
    try:
        assert client.get("/api/web-database/export").status_code == 401
        backup = client.get("/api/web-database/export", headers=staff_headers)
        assert backup.status_code == 200
        assert backup.content.startswith(b"SQLite format 3\x00")
        assert "no-store" in backup.headers.get("cache-control", "")

        db = sqlite3.connect(str(database_path))
        try:
            accounts_before = db.execute(
                "SELECT id, username, password_salt, password_hash FROM auth_users ORDER BY id"
            ).fetchall()
            employees_before = db.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
            tasks_before = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        finally:
            db.close()

        denied = client.post(
            "/api/web-database/import",
            headers=staff_headers,
            files={"file": ("customer.db", backup.content, "application/octet-stream")},
        )
        assert denied.status_code == 403

        invalid = client.post(
            "/api/web-database/import",
            headers=admin_headers,
            files={"file": ("customer.db", b"not a database", "application/octet-stream")},
        )
        assert invalid.status_code == 400

        restored = client.post(
            "/api/web-database/import",
            headers=admin_headers,
            files={"file": ("customer.db", backup.content, "application/octet-stream")},
        )
        assert restored.status_code == 200
        assert restored.json()["success"] is True
        assert restored.json()["counts"]["auth_users"] == len(accounts_before)
        assert not api_server.ACTIVE_SESSIONS.get(admin_token)

        db = sqlite3.connect(str(database_path))
        try:
            accounts_after = db.execute(
                "SELECT id, username, password_salt, password_hash FROM auth_users ORDER BY id"
            ).fetchall()
            employees_after = db.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
            tasks_after = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            auth_schema = db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_users'"
            ).fetchone()[0].upper()
            assert "COLLATE BINARY" in auth_schema
        finally:
            db.close()
        assert accounts_after == accounts_before
        assert employees_after == employees_before
        assert tasks_after == tasks_before
    finally:
        api_server.ACTIVE_SESSIONS.clear()
        api_server.ACTIVE_SESSIONS.update(previous_sessions)
        for backup_path in set(database_path.parent.glob(
            database_path.stem + ".before-import-*" + database_path.suffix
        )) - preimport_backups:
            backup_path.unlink(missing_ok=True)

def test_web_employee_productivity_report_counts_sunday_for_legacy_weekday_setting(monkeypatch):
    import secrets
    from datetime import timedelta

    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "0")
    monkeypatch.setenv("WEB_STANDALONE", "0")
    token = "sunday-productivity-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 9817,
        "username": "sunday-productivity",
        "display_name": "Sunday Productivity",
        "role": "Admin",
    }
    headers = {"Authorization": f"Bearer {token}"}
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    original = connection.execute(
        "SELECT value FROM settings WHERE key='working_weekdays'"
    ).fetchone()
    employee_id = None
    try:
        holidays = {
            row[0] for row in connection.execute("SELECT holiday_date FROM holidays").fetchall()
        }
        sunday = date.today() - timedelta(days=(date.today().weekday() + 1) % 7)
        for _ in range(52):
            if sunday.isoformat() not in holidays:
                break
            sunday -= timedelta(days=7)
        else:
            raise AssertionError("Could not find a non-holiday Sunday for productivity report testing")

        connection.execute(
            "INSERT INTO settings(key,value) VALUES('working_weekdays','0,1,2,3,4') "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
        )
        connection.commit()

        created = client.post(
            "/api/employees",
            headers=headers,
            json={
                "name": "Sunday Productivity Report Test",
                "employee_code": "RPT-SUNDAY-" + secrets.token_hex(4).upper(),
                "joining_date": sunday.isoformat(),
                "department": "Testing",
            },
        )
        assert created.status_code == 200, created.text
        employee_id = int(created.json()["id"])

        response = client.post(
            "/api/reports/preview",
            headers=headers,
            json={
                "date": sunday.isoformat(),
                "report_type": "Employee Productivity",
                "employee_id": employee_id,
                "options": {
                    "productivity_identity": True,
                    "productivity_metrics": True,
                    "productivity_explanation": True,
                    "productivity_tracking": True,
                    "productivity_tasks": False,
                },
            },
        )
        assert response.status_code == 200, response.text
        preview = response.json()["preview_text"]
        assert "Working days: 1" in preview
        assert "Attendance-eligible days: 1" in preview
    finally:
        if employee_id is not None:
            connection.execute("DELETE FROM tasks WHERE employee_id=?", (employee_id,))
            connection.execute("DELETE FROM attendance WHERE employee_id=?", (employee_id,))
            connection.execute("DELETE FROM employee_targets WHERE employee_id=?", (employee_id,))
            connection.execute("DELETE FROM employees WHERE id=?", (employee_id,))
        if original:
            connection.execute(
                "UPDATE settings SET value=? WHERE key='working_weekdays'", (original[0],)
            )
        else:
            connection.execute("DELETE FROM settings WHERE key='working_weekdays'")
        connection.commit()
        connection.close()
        api_server.ACTIVE_SESSIONS.pop(token, None)

def test_web_store_directory_list_and_summary_require_authentication(monkeypatch):
    monkeypatch.setenv("WEB_STANDALONE", "0")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    assert client.get("/api/customers/prospects").status_code == 401
    assert client.get("/api/customers/summary").status_code == 401


def test_web_store_directory_create_persists_location_and_deduplicates(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_STANDALONE", "0")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "0")
    token = "store-directory-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 9818,
        "username": "store-directory",
        "display_name": "Store Directory QA",
        "role": "Admin",
    }
    headers = {"Authorization": f"Bearer {token}"}
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    connection.row_factory = sqlite3.Row
    suffix = secrets.token_hex(4).upper()
    business_name = "Directory QA Store " + suffix
    address = "Plot 12, Main Road, Benz Circle, Vijayawada, Andhra Pradesh 520010"
    extended_address = address + ", Near Test Landmark"
    prospect_id = None
    try:
        payload = {
            "business_name": business_name,
            "business_category": "Sports Nutrition",
            "kind": "Store",
            "state": "Andhra Pradesh",
            "city": "Vijayawada",
            "area": "Benz Circle",
            "contact_person": "QA Contact",
            "phone": "+91 9000000000",
            "email": "directory-qa@example.test",
            "address": address,
            "website": "https://example.test/store",
            "maps": "",
            "followup_date": "2026-11-07",
            "call_time": "10:30",
            "connection": "Not Connected",
            "verified": "No",
            "response": "Awaiting confirmation",
            "notes": "Directory QA record",
        }
        first = client.post("/api/customers/prospects", headers=headers, json=payload)
        assert first.status_code == 200, first.text
        first_result = first.json()
        prospect_id = int(first_result["id"])
        assert first_result["inserted"] == 1
        assert first_result["duplicates"] == 0

        duplicate_payload = {
            **payload,
            "business_name": business_name.upper(),
            "address": extended_address,
        }
        second = client.post(
            "/api/customers/prospects", headers=headers, json=duplicate_payload
        )
        assert second.status_code == 200, second.text
        second_result = second.json()
        assert second_result["id"] == prospect_id
        assert second_result["duplicate"] is True
        assert second_result["duplicates"] == 1

        saved = connection.execute(
            "SELECT * FROM customer_prospects WHERE id=?", (prospect_id,)
        ).fetchone()
        assert saved is not None
        assert saved["business_category"] == "Sports Nutrition"
        assert saved["address"] == extended_address
        assert saved["website"] == "https://example.test/store"
        assert saved["maps"].startswith("https://www.google.com/maps/search/")
        assert saved["followup_date"] == "2026-11-07"
        assert saved["call_time"] == "10:30"
        assert saved["source_type"] == "Web"
        assert saved["source_status"] == "Needs direct confirmation"

        search = client.get(
            "/api/customers/prospects",
            headers=headers,
            params={"q": "Benz Circle"},
        )
        assert search.status_code == 200
        assert any(int(row["id"]) == prospect_id for row in search.json())
        count = connection.execute(
            "SELECT COUNT(*) FROM customer_prospects WHERE dedupe_key=?",
            (saved["dedupe_key"],),
        ).fetchone()[0]
        assert count == 1
    finally:
        if prospect_id is not None:
            connection.execute(
                "DELETE FROM customer_prospects WHERE id=?", (prospect_id,)
            )
            connection.commit()
        connection.close()
        api_server.ACTIVE_SESSIONS.pop(token, None)


def test_web_store_directory_ui_exposes_location_filters_and_map_links():
    source = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    assert 'label="Full postal address" name="address"' in source
    assert 'label="Official website" name="website"' in source
    assert 'label="Google Maps URL (optional)" name="maps"' in source
    assert "prospectStateFilter" in source
    assert "prospectWebsiteFilter" in source
    assert "prospectVerificationFilter" in source
    assert "Open Maps" in source
    assert 'target="_blank" rel="noopener noreferrer"' in source
    assert "editRecord.editType==='prospects'" in source
    assert "editType==='prospects'?'/customers/prospects/'+id" in source
    assert "onEdit={canAdminEmployees?" in source
    assert "onDelete={canAdminEmployees?" in source

def test_sensitive_read_endpoints_require_an_authenticated_session(monkeypatch):
    import secrets

    monkeypatch.setenv("WEB_STANDALONE", "0")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    paths = (
        "/api/dashboard",
        "/api/employees?active_only=false",
        "/api/chat/messages?channel=general",
        "/api/print-center/summary",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code == 401, (path, response.status_code, response.text)

    token = "protected-read-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[token] = {
        "id": 9820,
        "username": "protected-read-qa",
        "display_name": "Protected Read QA",
        "role": "Admin",
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        for path in paths:
            response = client.get(path, headers=headers)
            assert response.status_code == 200, (path, response.status_code, response.text)
    finally:
        api_server.ACTIVE_SESSIONS.pop(token, None)

def test_web_store_directory_edit_is_admin_only_and_recomputes_branch_dedupe(monkeypatch):
    import secrets
    import customer_prospects as prospects

    monkeypatch.setenv("WEB_STANDALONE", "0")
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    admin_token = "store-edit-admin-" + secrets.token_hex(8)
    staff_token = "store-edit-staff-" + secrets.token_hex(8)
    api_server.ACTIVE_SESSIONS[admin_token] = {
        "id": 9821, "username": "store-edit-admin", "display_name": "Store Edit Admin", "role": "Admin"
    }
    api_server.ACTIVE_SESSIONS[staff_token] = {
        "id": 9822, "username": "store-edit-staff", "display_name": "Store Edit Staff", "role": "Staff"
    }
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    suffix = secrets.token_hex(4).upper()
    first_id = second_id = None
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    connection.row_factory = sqlite3.Row
    try:
        first = client.post("/api/customers/prospects", headers=admin_headers, json={
            "business_name": "Directory Edit Alpha " + suffix,
            "kind": "Store", "state": "Andhra Pradesh", "city": "Vijayawada",
            "address": "12 Alpha Road, Vijayawada, Andhra Pradesh 520010",
        })
        assert first.status_code == 200, first.text
        first_id = int(first.json()["id"])
        second = client.post("/api/customers/prospects", headers=admin_headers, json={
            "business_name": "Directory Edit Beta " + suffix,
            "kind": "Store", "state": "Andhra Pradesh", "city": "Vijayawada",
            "address": "14 Beta Road, Vijayawada, Andhra Pradesh 520010",
        })
        assert second.status_code == 200, second.text
        second_id = int(second.json()["id"])

        staff_edit = client.patch(
            f"/api/customers/prospects/{first_id}", headers=staff_headers,
            json={"contact_person": "Unauthorized edit"},
        )
        staff_delete = client.delete(
            f"/api/customers/prospects/{first_id}", headers=staff_headers
        )
        assert staff_edit.status_code == 403
        assert staff_delete.status_code == 403

        duplicate_edit = client.patch(
            f"/api/customers/prospects/{first_id}", headers=admin_headers,
            json={"business_name": "Directory Edit Beta " + suffix},
        )
        assert duplicate_edit.status_code == 409, duplicate_edit.text

        unique_name = "Directory Edit Gym " + suffix
        updated = client.patch(
            f"/api/customers/prospects/{first_id}", headers=admin_headers,
            json={
                "business_name": unique_name, "kind": "Gym", "state": "Telangana",
                "city": "Hyderabad", "address": "8 Test Avenue, Hyderabad, Telangana 500001",
                "maps": "",
            },
        )
        assert updated.status_code == 200, updated.text
        saved = connection.execute(
            "SELECT * FROM customer_prospects WHERE id=?", (first_id,)
        ).fetchone()
        assert saved is not None
        assert saved["business_name"] == unique_name
        assert saved["kind"] == "Gym"
        assert saved["state"] == "Telangana"
        assert saved["city"] == "Hyderabad"
        assert saved["maps"].startswith("https://www.google.com/maps/search/")
        assert saved["dedupe_key"] == prospects.prospect_dedupe_key(dict(saved))
        assert saved["contact_person"] != "Unauthorized edit"
    finally:
        ids = [value for value in (first_id, second_id) if value is not None]
        if ids:
            connection.executemany("DELETE FROM customer_prospects WHERE id=?", [(value,) for value in ids])
            connection.commit()
        connection.close()
        api_server.ACTIVE_SESSIONS.pop(admin_token, None)
        api_server.ACTIVE_SESSIONS.pop(staff_token, None)


def test_store_directory_scrape_uses_managed_connection_for_encrypted_sync(monkeypatch):
    import secrets
    import customer_prospects
    import web_parity_routes

    class SyncManager:
        configured = True

        def __init__(self):
            self.pending = 0

        def mark_pending(self):
            self.pending += 1

    manager = SyncManager()
    monkeypatch.setenv("WEB_STANDALONE", "1")
    monkeypatch.setattr(api_server, "WEB_SYNC_MANAGER", manager)
    monkeypatch.setattr(api_server, "ensure_database", lambda: None)

    suffix = secrets.token_hex(5).upper()
    business_name = "Scrape Sync Callback QA " + suffix
    record = dict(customer_prospects.RESEARCHED_WEB_LEADS[0])
    record.update({
        "business_name": business_name,
        "business_category": "Sports Nutrition",
        "kind": "Store",
        "state": "Andhra Pradesh",
        "city": "Vijayawada",
        "area": "Benz Circle",
        "address": "Shop 12, MG Road, Vijayawada, Andhra Pradesh 520010",
        "phone": "90000" + suffix[:5],
        "email": "scrape-" + suffix.lower() + "@example.test",
        "website": "https://scrape-sync-" + suffix.lower() + ".example.test",
        "maps": "",
    })
    monkeypatch.setattr(
        customer_prospects,
        "crawl_search_engine_results",
        lambda **_kwargs: [record],
    )

    job_id = "scrape-sync-" + suffix.lower()
    web_parity_routes._jobs[job_id] = {"id": job_id, "status": "running"}
    connection = sqlite3.connect(str(desktop_app.DB_PATH))
    try:
        web_parity_routes._run_scrape(job_id, "Andhra Pradesh", "sports nutrition", 5, True)
        assert web_parity_routes._jobs[job_id]["status"] == "completed"
        assert web_parity_routes._jobs[job_id]["result"]["inserted"] == 1
        assert manager.pending == 1, "The scrape commit must notify the encrypted snapshot sync manager."
        saved = connection.execute(
            "SELECT id FROM customer_prospects WHERE business_name=?",
            (business_name,),
        ).fetchone()
        assert saved is not None
        connection.execute("DELETE FROM customer_prospects WHERE id=?", (saved[0],))
        connection.commit()
    finally:
        connection.close()
        web_parity_routes._jobs.pop(job_id, None)

def test_customer_prospect_api_keyset_pagination_returns_every_row_once():
    import web_ops_routes

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            "CREATE TABLE customer_prospects (id INTEGER PRIMARY KEY, business_name TEXT, state TEXT)"
        )
        connection.executemany(
            "INSERT INTO customer_prospects(id,business_name,state) VALUES(?,?,?)",
            [(record_id, f"Pagination Store {record_id}", "Haryana") for record_id in range(1, 2506)],
        )
        connection.commit()

        collected = []
        before_id = None
        while True:
            page = web_ops_routes.list_customer_prospects(
                state="Haryana", limit=1000, before_id=before_id,
                conn=connection, user={"username": "pagination-test", "role": "Staff"},
            )
            collected.extend(int(row["id"]) for row in page)
            if len(page) < 1000:
                break
            before_id = int(page[-1]["id"])

        assert len(collected) == 2505
        assert collected == list(range(2505, 0, -1))
        assert len(set(collected)) == 2505
    finally:
        connection.close()

def test_store_directory_web_ui_exposes_workbook_import_regional_dashboard_and_exports():
    source = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    for endpoint in (
        "/customers/import",
        "/customers/dashboard-import",
        "/customers/regional-summary",
        "/customers/export?",
        "/customers/regional-export?",
    ):
        assert endpoint in source, f"Store Directory UI is missing {endpoint}"
    for label in (
        "Import and merge workbook",
        "Import regional benchmark",
        "Regional coverage",
        "Export filtered Store Directory:",
        "Regional dashboard export:",
    ):
        assert label in source, f"Store Directory UI is missing {label}"
    assert "disabled={!canAdminEmployees||!storeWorkbook||storeImportBusy}" in source
    assert "disabled={!canAdminEmployees||!dashboardWorkbook||dashboardImportBusy}" in source
    assert "Existing customer IDs, notes, follow-ups and records are merged, not deleted or replaced." in source
