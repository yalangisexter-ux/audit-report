"""Regression coverage for Windows Settings actions migrated to the web app."""
import ast
import csv
import io
import sqlite3
import re
from pathlib import Path

from fastapi.testclient import TestClient

import api_server as api


class _CommitTrackingConnection(sqlite3.Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commit_calls = 0

    def commit(self):
        self.commit_calls += 1
        return super().commit()


def _create_settings_database(path: Path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            employee_code TEXT,
            name TEXT,
            department TEXT,
            designation TEXT,
            phone TEXT,
            email TEXT,
            joining_date TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            display_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            expose_link INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL
        );
        """
    )
    conn.executemany(
        """INSERT INTO employees
           (id,employee_code,name,department,designation,phone,email,joining_date,active,notes,display_order)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (1, "EMP,001", 'Asha "Coach"', "Operations, South", "Coach",
             "+91 90000 00001", "asha@example.com", "2024-01-02", 1,
             "First line, with comma\nSecond line", 20),
            (2, "EMP002", "Inactive Coach", "Operations", "Coach",
             "", "", "2023-02-03", 0, "Former employee", 10),
        ],
    )
    conn.executemany(
        "INSERT INTO tasks(id,expose_link,updated_at) VALUES(?,?,?)",
        [(1, 0, ""), (2, 0, "")],
    )
    conn.commit()
    conn.close()


def _client_for_database(path: Path, user=None, *, track_commits=False):
    connections = []

    def override_get_db():
        factory = _CommitTrackingConnection if track_commits else sqlite3.Connection
        conn = sqlite3.connect(str(path), check_same_thread=False, factory=factory)
        conn.row_factory = sqlite3.Row
        connections.append(conn)
        try:
            yield conn
        finally:
            conn.close()

    api.app.dependency_overrides[api.get_db] = override_get_db
    if user is None:
        api.app.dependency_overrides.pop(api.get_current_user, None)
    else:
        api.app.dependency_overrides[api.get_current_user] = lambda: dict(user)
    return TestClient(api.app), connections


def _clear_overrides():
    api.app.dependency_overrides.pop(api.get_db, None)
    api.app.dependency_overrides.pop(api.get_current_user, None)


def test_employee_csv_matches_desktop_columns_and_includes_inactive_records(tmp_path):
    path = tmp_path / "employee-export.db"
    _create_settings_database(path)
    client, _connections = _client_for_database(
        path, {"id": 7, "username": "Staff", "role": "Staff"}
    )
    try:
        response = client.get("/api/employees/export.csv")
        assert response.status_code == 200, response.text
        assert response.headers["content-disposition"] == 'attachment; filename="employees.csv"'
        assert response.headers["cache-control"] == "no-store"
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        assert rows[0] == [
            "Record ID", "Employee ID", "Name", "Department", "Role",
            "Phone", "Email", "Joining date", "Status", "Notes",
        ]
        assert rows[1] == [
            "1", "EMP,001", 'Asha "Coach"', "Operations, South", "Coach",
            "+91 90000 00001", "asha@example.com", "2024-01-02", "Active",
            "First line, with comma\nSecond line",
        ]
        assert rows[2][1] == "EMP002"
        assert rows[2][8] == "Inactive"
    finally:
        _clear_overrides()


def test_global_expose_links_updates_all_tasks_settings_audit_and_commit(tmp_path):
    path = tmp_path / "expose-links.db"
    _create_settings_database(path)
    client, connections = _client_for_database(
        path,
        {"id": 8, "username": "Staff", "role": "Staff"},
        track_commits=True,
    )
    try:
        response = client.post("/api/settings/expose-all-links")
        assert response.status_code == 200, response.text
        assert response.json() == {"success": True, "enabled": True, "updated": 2}
        assert connections[-1].commit_calls == 1

        conn = sqlite3.connect(path)
        try:
            task_rows = conn.execute(
                "SELECT expose_link,updated_at FROM tasks ORDER BY id"
            ).fetchall()
            assert len(task_rows) == 2
            assert all(row[0] == 1 and row[1] for row in task_rows)
            assert dict(conn.execute("SELECT key,value FROM settings").fetchall()) == {
                "global_expose_link": "1",
                "report_opt_expose_link": "1",
            }
            assert conn.execute(
                "SELECT action,details FROM audit_log"
            ).fetchall() == [("Global expose links enabled", "Updated 2 tasks")]
        finally:
            conn.close()
    finally:
        _clear_overrides()


def test_employee_export_and_global_expose_links_require_login(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    path = tmp_path / "unauthenticated-settings.db"
    _create_settings_database(path)
    client, _connections = _client_for_database(path)
    try:
        export_response = client.get("/api/employees/export.csv")
        expose_response = client.post("/api/settings/expose-all-links")
        assert export_response.status_code == 401
        assert expose_response.status_code == 401
    finally:
        _clear_overrides()


def test_settings_screen_renders_both_desktop_data_actions():
    source = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.jsx").read_text(
        encoding="utf-8"
    )
    assert "Employee data actions" in source
    assert "downloadEmployeesCsv" in source
    assert "/employees/export.csv" in source
    assert "Expose all proof links" in source
    assert "/settings/expose-all-links" in source

def test_google_sheets_sync_customer_admin_merges_without_changing_account_credentials(tmp_path, monkeypatch):
    import google_sheets_sync

    path = tmp_path / "google-sheets-customer-admin.db"
    _create_settings_database(path)
    setup = sqlite3.connect(path)
    setup.execute(
        """CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL COLLATE BINARY,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )"""
    )
    setup.execute(
        "INSERT INTO auth_users VALUES(1, 'Admin', 'Customer Admin', 'Admin', 'pbkdf2-customer-hash', 1)"
    )
    setup.commit()
    setup.close()

    def fake_sync(db):
        assert db.active_user["username"] == "Admin"
        db.conn.execute("UPDATE employees SET notes='Merged from master workbook' WHERE id=1")
        db.conn.commit()
        return {"employees": 1, "tasks": 2}

    monkeypatch.setattr(google_sheets_sync, "sync_from_live_google_sheet", fake_sync)
    client, connections = _client_for_database(
        path,
        {"id": 1, "username": "Admin", "display_name": "Customer Admin", "role": "Admin"},
        track_commits=True,
    )
    try:
        response = client.post("/api/settings/google-sheets-sync", json={})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "synced"
        assert response.json()["updated"] == 3
        assert connections[-1].commit_calls == 1
        conn = sqlite3.connect(path)
        try:
            assert conn.execute("SELECT notes FROM employees WHERE id=1").fetchone()[0] == "Merged from master workbook"
            assert conn.execute("SELECT username,password_hash FROM auth_users").fetchone() == (
                "Admin", "pbkdf2-customer-hash"
            )
        finally:
            conn.close()
    finally:
        _clear_overrides()


def test_google_sheets_sync_requires_developer_password_for_exact_lowercase_admin(tmp_path, monkeypatch):
    import cloudflare_chat
    import google_sheets_sync

    path = tmp_path / "google-sheets-developer.db"
    _create_settings_database(path)
    sync_calls = []

    def fake_sync(db):
        sync_calls.append(db.active_user["username"])
        return {"stores": 1}

    monkeypatch.setattr(google_sheets_sync, "sync_from_live_google_sheet", fake_sync)
    monkeypatch.setattr(cloudflare_chat, "verify_developer_password", lambda password: password == "unit-test-only-developer-secret")
    client, _connections = _client_for_database(
        path,
        {"id": 2, "username": "admin", "display_name": "Developer", "role": "Admin"},
    )
    try:
        missing = client.post("/api/settings/google-sheets-sync", json={})
        wrong = client.post("/api/settings/google-sheets-sync", json={"developer_password": "wrong"})
        valid = client.post("/api/settings/google-sheets-sync", json={"developer_password": "unit-test-only-developer-secret"})
        assert missing.status_code == 403
        assert wrong.status_code == 403
        assert valid.status_code == 200, valid.text
        assert valid.json()["status"] == "synced"
        assert sync_calls == ["admin"]
    finally:
        _clear_overrides()


def test_google_sheets_sync_denies_staff_and_reports_offline_without_replacing_local_data(tmp_path, monkeypatch):
    import google_sheets_sync

    path = tmp_path / "google-sheets-offline.db"
    _create_settings_database(path)
    monkeypatch.setattr(google_sheets_sync, "sync_from_live_google_sheet", lambda _db: {})
    client, _connections = _client_for_database(
        path,
        {"id": 3, "username": "Staff", "display_name": "Staff", "role": "Staff"},
    )
    try:
        denied = client.post("/api/settings/google-sheets-sync", json={})
        assert denied.status_code == 403
    finally:
        _clear_overrides()

    client, _connections = _client_for_database(
        path,
        {"id": 1, "username": "Admin", "display_name": "Customer Admin", "role": "Admin"},
    )
    try:
        response = client.post("/api/settings/google-sheets-sync", json={})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "offline"
        assert response.json()["updated"] == 0
        conn = sqlite3.connect(path)
        try:
            assert conn.execute("SELECT notes FROM employees WHERE id=1").fetchone()[0] == "First line, with comma\nSecond line"
        finally:
            conn.close()
    finally:
        _clear_overrides()


def test_settings_screen_exposes_google_sheets_sync_and_developer_password_gate():
    source = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.jsx").read_text(
        encoding="utf-8"
    )
    assert "Google Sheets master sync" in source
    assert "/settings/google-sheets-sync" in source
    assert "Developer password (required for lowercase developer account)" in source
    assert "This is a pull operation, not an upload to Google Sheets." in source



def test_web_appearance_options_match_windows_desktop():
    root = Path(__file__).resolve().parents[1]
    desktop = (root / "app.py").read_text(encoding="utf-8")
    web = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")

    desktop_wallpapers = re.search(
        r"class AnimatedBackground.*?STYLES\s*=\s*(\([^\n]+\))",
        desktop,
        re.DOTALL,
    )
    web_wallpapers = re.search(
        r"const WALLPAPER_STYLES\s*=\s*(\[[^\n]+\])\s*;",
        web,
    )
    assert desktop_wallpapers and web_wallpapers
    assert tuple(ast.literal_eval(web_wallpapers.group(1))) == ast.literal_eval(
        desktop_wallpapers.group(1)
    )

    desktop_themes = re.search(
        r"self\.theme_combo\.addItems\((\[[^\]]+\])\)",
        desktop,
    )
    web_themes = re.search(
        r"const APPEARANCE_THEMES\s*=\s*(\[[^\]]+\])",
        web,
    )
    assert desktop_themes and web_themes
    assert [value.lower() for value in ast.literal_eval(desktop_themes.group(1))] == (
        ast.literal_eval(web_themes.group(1))
    )


def test_web_custom_wallpaper_is_local_and_does_not_write_shared_customer_settings():
    root = Path(__file__).resolve().parents[1]
    web = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    helper_section = web[
        web.index("const APPEARANCE_THEMES") : web.index("export default function App()")
    ]

    assert "window.indexedDB.open('rsc-web-appearance',1)" in helper_section
    assert "get('custom-wallpaper')" in helper_section
    assert "put(file,'custom-wallpaper')" in helper_section
    assert "delete('custom-wallpaper')" in helper_section
    assert "localStorage.setItem('rsc_web_theme',theme)" in web
    assert "localStorage.setItem('rsc_web_wallpaper',wallpaper)" in web
    assert "15*1024*1024" in web
    assert "writeCustomWallpaper(file)" in web
    assert "deleteCustomWallpaper()" in web
    assert "/api/settings" not in helper_section


def test_web_appearance_controls_and_wallpaper_contrast_styles_render():
    root = Path(__file__).resolve().parents[1]
    web = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    css = (root / "frontend" / "src" / "index.css").read_text(encoding="utf-8")

    assert 'Panel title="Appearance & wallpaper"' in web
    assert 'aria-label="Application theme"' in web
    assert 'aria-label="Live wallpaper"' in web
    assert 'onChange={uploadCustomWallpaper}' in web
    assert "onClick={resetCustomWallpaper}" in web
    assert 'className="webapp-root' in web
    for theme in ("day", "night", "ocean", "sunset"):
        assert f'data-rsc-theme="{theme}"' in web + css
    for style in (
        "Ambient Glow", "Aurora Waves", "Starfield", "Floating Bubbles",
        "Rainfall", "Matrix Drift", "Galaxy", "Milky Way", "Milky Way Waves",
        "Ocean Waves", "Lord Shiva", "Love Couple", "Love & Couples",
        "Cyberpunk Neon", "Calisthenics Power", "Cosmic Nebula", "Custom Image",
    ):
        assert f'data-rsc-wallpaper="{style}"' in css or style in web
    assert "opaque workspace cards keep employee data readable" in css


def test_legacy_clock_mode_api_remains_available_to_staff_for_compatibility(tmp_path):
    path = tmp_path / "clock-mode.db"
    _create_settings_database(path)
    client, connections = _client_for_database(
        path, {"id": 12, "username": "Staff", "role": "Staff"}, track_commits=True
    )
    try:
        default = client.get("/api/settings/clock-mode")
        assert default.status_code == 200
        assert default.json() == {"mode": "digital"}

        saved = client.put("/api/settings/clock-mode", json={"mode": "Analog"})
        assert saved.status_code == 200, saved.text
        assert saved.json() == {"success": True, "mode": "analog"}
        assert connections[-1].commit_calls == 1

        conn = sqlite3.connect(path)
        try:
            assert conn.execute(
                "SELECT value FROM settings WHERE key='clock_mode'"
            ).fetchone() == ("analog",)
        finally:
            conn.close()

        invalid = client.put("/api/settings/clock-mode", json={"mode": "binary"})
        assert invalid.status_code == 422
    finally:
        _clear_overrides()


def test_legacy_clock_mode_api_requires_authentication(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    path = tmp_path / "clock-mode-auth.db"
    _create_settings_database(path)
    client, _connections = _client_for_database(path)
    try:
        assert client.get("/api/settings/clock-mode").status_code == 401
        assert client.put(
            "/api/settings/clock-mode", json={"mode": "analog"}
        ).status_code == 401
    finally:
        _clear_overrides()


def test_web_clock_controls_match_desktop_digital_analog_setting():
    root = Path(__file__).resolve().parents[1]
    desktop = (root / "app.py").read_text(encoding="utf-8")
    web = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")

    assert 'self.clock_mode_combo.addItems(["Digital", "Analog"])' in desktop
    assert 'self.db.get_setting("clock_mode", "digital")' in desktop
    assert 'className="block space-y-2 text-xs font-semibold text-slate-400">Clock display mode' in web
    assert 'aria-label="Clock display mode"' in web
    assert 'function AnalogClock({ now })' in web
    assert "localStorage.getItem('rsc_web_clock_mode')" in web
    assert "localStorage.setItem('rsc_web_clock_mode',normalized)" in web
    assert '/settings/clock-mode' not in web
    assert 'toLocaleTimeString(undefined,{hour:' in web
    assert 'saveClockMode(clockMode===\'digital\'?\'analog\':\'digital\')' in web


def test_web_clock_mode_is_browser_local_and_survives_app_reload():
    root = Path(__file__).resolve().parents[1]
    web = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")

    assert "localStorage.getItem('rsc_web_clock_mode')||'digital'" in web
    assert "localStorage.setItem('rsc_web_clock_mode',normalized)" in web
    assert "Clock display mode is stored in this browser" in web
    assert "apiFetch('/settings/clock-mode')" not in web
