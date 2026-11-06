"""Regression coverage for Windows-equivalent holiday permissions in web UI/API."""
from pathlib import Path


def test_holiday_controls_and_api_permissions_match_windows_admin_developer_gate():
    root = Path(__file__).resolve().parents[1]
    desktop = (root / "app.py").read_text(encoding="utf-8")
    frontend = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    api = (root / "api_server.py").read_text(encoding="utf-8")

    declare_start = desktop.index("    def declare_holiday(self):")
    remove_start = desktop.index("    def remove_holiday(self):", declare_start)
    declare_block = desktop[declare_start:remove_start]
    remove_end = desktop.index("\n    def ", remove_start + 5)
    remove_block = desktop[remove_start:remove_end]

    assert "if not self.is_admin_or_dev:" in declare_block
    assert "if not self.is_admin_or_dev:" in remove_block
    assert "const canAdminEmployees=['admin','developer'].includes" in frontend
    assert "{canAdminEmployees?<form" in frontend
    assert "onDelete={canAdminEmployees ? (h=>del('/holidays/'+h.holiday_date)) : undefined}" in frontend

    route_start = api.index('@app.post("/api/holidays")')
    route_end = api.index("# --- Business Tracking (Products & Services) ---", route_start)
    holiday_routes = api[route_start:route_end]
    assert holiday_routes.count('_require_employee_roles(user, {"admin", "developer"})') == 2
    assert '_record_account_audit(conn, "Holiday declared"' in holiday_routes
    assert '_record_account_audit(\n        conn,\n        "Holiday removed"' in holiday_routes
