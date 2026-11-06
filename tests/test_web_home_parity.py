"""Regression coverage for the distinct desktop Home workspace and its business snapshot."""

import sqlite3
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient

import api_server
import business_tracking


def _business_snapshot_database(path: Path):
    connection = sqlite3.connect(path)
    business_tracking.setup_business_tables(connection)
    connection.execute(
        """INSERT INTO bt_products(name, opening_stock, reorder_level, updated_at)
           VALUES('Low stock item', 5, 6, '2026-11-06 09:00:00')"""
    )
    connection.execute(
        """INSERT INTO bt_products(name, opening_stock, reorder_level, updated_at)
           VALUES('Healthy item', 20, 5, '2026-11-06 09:00:00')"""
    )
    connection.execute(
        """INSERT INTO bt_products(name, opening_stock, reorder_level, updated_at)
           VALUES('No reorder threshold', 0, 0, '2026-11-06 09:00:00')"""
    )
    connection.executemany(
        """INSERT INTO bt_orders(order_date, order_value, updated_at)
           VALUES(?, ?, ?)""",
        [
            ("2026-11-06", 250.0, "2026-11-06 09:00:00"),
            ("2026-11-06", 125.5, "2026-11-06 09:05:00"),
        ],
    )
    connection.executemany(
        "INSERT INTO bt_members(name, status) VALUES(?, ?)",
        [("Active member", "Active"), ("Expired member", "Expired")],
    )
    connection.executemany(
        """INSERT INTO bt_activities(employee_id, task_type, created_at)
           VALUES(?, ?, ?)""",
        [
            (1, "Inventory audit", "2026-11-06 09:00:00"),
            (1, "Customer follow-up", "2026-11-06 09:10:00"),
            (2, "Order packing", "2026-11-06 09:20:00"),
        ],
    )
    connection.commit()
    connection.close()


def _override_database(path: Path):
    def override_get_db():
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    api_server.app.dependency_overrides[api_server.get_db] = override_get_db


def test_home_business_snapshot_matches_desktop_inventory_and_operations_counts(tmp_path):
    path = tmp_path / "home-business.db"
    _business_snapshot_database(path)
    _override_database(path)
    api_server.app.dependency_overrides[api_server.get_current_user] = lambda: {
        "id": 1,
        "username": "HomeTest",
        "display_name": "Home Test",
        "role": "Admin",
    }
    try:
        response = TestClient(api_server.app).get("/api/home/business-snapshot")
        assert response.status_code == 200, response.text
        assert response.json() == {
            "version": api_server.APP_VERSION,
            "products": 3,
            "low_stock": 1,
            "orders": 2,
            "members": 1,
            "activities": 3,
            "total_sales": 375.5,
        }
    finally:
        api_server.app.dependency_overrides.pop(api_server.get_db, None)
        api_server.app.dependency_overrides.pop(api_server.get_current_user, None)


def test_home_business_snapshot_requires_an_authenticated_user(tmp_path):
    path = tmp_path / "home-business-auth.db"
    sqlite3.connect(path).close()
    _override_database(path)

    def reject_user():
        raise HTTPException(status_code=401, detail="Login required")

    api_server.app.dependency_overrides[api_server.get_current_user] = reject_user
    try:
        response = TestClient(api_server.app).get("/api/home/business-snapshot")
        assert response.status_code == 401
    finally:
        api_server.app.dependency_overrides.pop(api_server.get_db, None)
        api_server.app.dependency_overrides.pop(api_server.get_current_user, None)


def test_web_home_is_a_distinct_screen_with_the_desktop_workspace_guide():
    root = Path(__file__).resolve().parents[1]
    app_source = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    home_source = (root / "frontend" / "src" / "HomeWorkspace.jsx").read_text(encoding="utf-8")

    assert "tab==='home'&&<HomeWorkspace" in app_source
    assert "tab==='dashboard'&&<>" in app_source
    assert "['homeBusiness','/home/business-snapshot',null]" in app_source

    for title in (
        "Workspace guide",
        "Dashboard",
        "Employees",
        "Task Manager",
        "Employee Tracker",
        "Attendance",
        "Print Center",
        "EOD Archive",
        "Business Tracking",
        "Store Directory",
        "Live Chat",
        "Settings & Backup",
        "Business tracking &amp; operations",
        "Catalog Products",
        "Reorder Alerts",
        "Customer Orders",
        "Active Members",
    ):
        assert title in home_source

    assert "onCustomWallpaperUpload" in home_source
    assert "Previous versions" in home_source
    assert "The browser does not execute or roll back a Windows installer." in home_source
