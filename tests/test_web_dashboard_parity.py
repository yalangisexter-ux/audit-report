"""Regression tests for desktop-equivalent web dashboard telemetry and productivity."""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

import api_server


def _create_dashboard_database(path: Path):
    today = date.today()
    start = today - timedelta(days=6)
    holiday = today - timedelta(days=2)
    leave_day = today - timedelta(days=1)
    present_before_holiday = today - timedelta(days=3)

    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            employee_code TEXT,
            name TEXT NOT NULL,
            department TEXT,
            designation TEXT,
            joining_date TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            attendance_status TEXT,
            check_in TEXT,
            check_out TEXT
        );
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT,
            progress REAL,
            due_time TEXT,
            priority TEXT,
            task_date TEXT NOT NULL,
            department TEXT
        );
        CREATE TABLE holidays (
            holiday_date TEXT PRIMARY KEY,
            holiday_name TEXT
        );
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.execute(
        """INSERT INTO employees
           (id,employee_code,name,department,designation,joining_date,active,display_order)
           VALUES(1,'RSC-001','Active Coach','Coaching','Senior Coach',?,1,10)""",
        (start.isoformat(),),
    )
    conn.execute(
        """INSERT INTO employees
           (id,employee_code,name,department,designation,joining_date,active,display_order)
           VALUES(2,'RSC-002','Active Trainer','Training','Trainer',NULL,1,20)"""
    )
    conn.execute(
        """INSERT INTO employees
           (id,employee_code,name,department,designation,joining_date,active,display_order)
           VALUES(3,'RSC-003','Inactive Employee','Operations','Former Staff',NULL,0,30)"""
    )

    for work_day, status, check_in in (
        (today, "Present", "09:00"),
        (leave_day, "Leave", ""),
        (holiday, "Present", "09:15"),
        (present_before_holiday, "Present", "08:55"),
    ):
        conn.execute(
            """INSERT INTO attendance
               (employee_id,work_date,attendance_status,check_in,check_out)
               VALUES(1,?,?,?,?)""",
            (work_day.isoformat(), status, check_in, ""),
        )
    conn.execute(
        "INSERT INTO holidays(holiday_date,holiday_name) VALUES(?,?)",
        (holiday.isoformat(), "Dashboard regression holiday"),
    )
    conn.execute(
        "INSERT INTO settings(key,value) VALUES('working_weekdays','0,1,2,3,4,5')"
    )

    for task_id, title, status, progress in (
        (1, "Completed assignment", "Completed", 100),
        (2, "Submitted assignment", "Submitted", 100),
        (3, "In-progress assignment", "In progress", 50),
        (4, "Legacy unselected assignment", "Not selected", 100),
        (5, "Cancelled assignment", "Cancelled", 0),
    ):
        conn.execute(
            """INSERT INTO tasks
               (id,employee_id,title,status,progress,due_time,priority,task_date,department)
               VALUES(?,1,?,?,?,'18:00','Normal',?,'Coaching')""",
            (task_id, title, status, progress, today.isoformat()),
        )
    conn.commit()
    conn.close()


def test_dashboard_matches_desktop_kpis_roster_and_productivity_formula(tmp_path):
    path = tmp_path / "dashboard-parity.db"
    _create_dashboard_database(path)

    def override_get_db():
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    api_server.app.dependency_overrides[api_server.get_db] = override_get_db
    api_server.app.dependency_overrides[api_server.get_current_user] = lambda: {
        "id": 1, "username": "DashboardTest", "role": "Admin"
    }
    try:
        response = TestClient(api_server.app).get("/api/dashboard")
        assert response.status_code == 200, response.text
        body = response.json()
        kpis = body["kpis"]

        assert kpis["total_employees"] == 2
        assert kpis["present_today"] == 1
        assert kpis["absent_today"] == 0
        assert kpis["leave_today"] == 0
        assert kpis["not_checked_today"] == 1
        assert kpis["checkins_today"] == 1
        assert kpis["attendance_rate"] == 50
        assert kpis["open_tasks"] == 2
        assert kpis["completed_tasks"] == 2

        assert len(body["recent_employees"]) == 2
        assert all(row["active"] == 1 for row in body["recent_employees"])
        assert len(body["attendance_roster"]) == 2
        assert body["attendance_roster"][0]["status"] == "Present"
        assert body["attendance_roster"][1]["status"] == "Not checked"
        assert len(body["today_tasks"]) == 5

        coach = next(row for row in body["productivity"] if row["employee_id"] == 1)
        assert coach["working_days"] == 6
        assert coach["attendance_eligible_days"] == 5
        assert coach["present_count"] == 2
        assert coach["task_count"] == 5
        assert coach["completed"] == 2
        assert coach["task_score"] == 50.0
        assert coach["attendance_score"] == 40.0
        assert coach["score"] == 47

        trainer = next(row for row in body["productivity"] if row["employee_id"] == 2)
        assert trainer["score"] == 0
        assert "Inactive Employee" not in {row["name"] for row in body["productivity"]}
    finally:
        api_server.app.dependency_overrides.pop(api_server.get_db, None)
        api_server.app.dependency_overrides.pop(api_server.get_current_user, None)


def test_web_dashboard_renders_all_desktop_dashboard_panels():
    root = Path(__file__).resolve().parents[1]
    source = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    for label in (
        "OPERATIONS COMMAND // REAL-TIME WORKFORCE AUDIT",
        "Recent Employees",
        "Today's Tasks",
        "Today's Attendance",
        "Employee Productivity",
        "Productivity Summary",
        "Quick Actions",
    ):
        assert label in source
    assert "data.dashboard?.attendance_roster" in source
    assert "data.dashboard?.productivity" in source
    assert "data.dashboard?.recent_employees" in source
