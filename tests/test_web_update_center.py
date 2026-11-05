"""Regression coverage for the web update center and protected rollback catalog."""
import hashlib
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import api_server as api
import web_parity_routes as routes


def _create_update_database(path: Path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL COLLATE BINARY,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL
        );
        """
    )
    for user_id, username, role, password in (
        (1, "Admin", "Admin", "Customer-Password-987"),
        (2, "admin", "Developer", "Developer-Password-987"),
    ):
        salt, digest = api.desktop_app.hash_pin(password)
        conn.execute(
            "INSERT INTO auth_users(id,username,password_salt,password_hash,active) VALUES(?,?,?,?,1)",
            (user_id, username, salt, digest),
        )
    conn.commit()
    conn.close()


def _client_for_database(path: Path, user=None):
    def override_get_db():
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    api.app.dependency_overrides[api.get_db] = override_get_db
    if user is None:
        api.app.dependency_overrides.pop(api.get_current_user, None)
    else:
        api.app.dependency_overrides[api.get_current_user] = lambda: dict(user)
    return TestClient(api.app)


def _release(tag, *, draft=False, prerelease=False, url=None, size=12_000_000, digest=None):
    download_url = url or (
        "https://github.com/yalangisexter-ux/audit-report/releases/download/"
        + tag + "/RawStrengthEmployeeAuditManager-Setup.exe"
    )
    asset = {
        "name": "RawStrengthEmployeeAuditManager-Setup.exe",
        "browser_download_url": download_url,
        "size": size,
    }
    if digest is not None:
        asset["digest"] = digest
    return {
        "tag_name": tag,
        "name": "Raw Strength Employee Audit Manager " + tag,
        "draft": draft,
        "prerelease": prerelease,
        "published_at": "2026-11-05T10:00:00Z",
        "html_url": "https://github.com/yalangisexter-ux/audit-report/releases/tag/" + tag,
        "body": "Release notes for " + tag,
        "assets": [asset],
    }


class _FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def _mock_release_catalog(monkeypatch, payload):
    routes._UPDATE_RELEASE_CACHE["entries"] = None
    routes._UPDATE_RELEASE_CACHE["expires_at"] = 0.0
    monkeypatch.setattr(
        routes,
        "urlopen",
        lambda _request, timeout=8: _FakeResponse(payload),
    )


def _clear_overrides():
    api.app.dependency_overrides.pop(api.get_db, None)
    api.app.dependency_overrides.pop(api.get_current_user, None)


def test_update_center_selects_latest_published_stable_installer_and_rejects_untrusted_assets(tmp_path, monkeypatch):
    path = tmp_path / "update-center.db"
    _create_update_database(path)
    _mock_release_catalog(
        monkeypatch,
        [
            _release("v1.3.82", digest="sha256:" + ("a" * 64)),
            _release("v1.3.80", digest="sha256:" + ("b" * 64)),
            _release("v1.3.79"),
            _release("v1.3.99", draft=True),
            _release("v1.3.90", prerelease=True),
            _release("v1.3.78", url="https://example.invalid/installer.exe"),
            _release("v1.3.77", size=900_000),
            _release("v1.3.76", digest="sha1:" + ("c" * 40)),
        ],
    )
    client = _client_for_database(
        path, {"id": 3, "username": "Staff", "role": "Staff"}
    )
    try:
        response = client.get("/api/update-center")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "ok"
        assert body["current_version"] == "1.3.81"
        assert body["latest_version"] == "1.3.82"
        assert body["update_available"] is True
        assert body["previous_release_count"] == 2
        assert body["latest_release"]["download_url"].startswith(
            "https://github.com/yalangisexter-ux/audit-report/releases/download/"
        )
        assert body["latest_release"]["sha256"] == "a" * 64
    finally:
        _clear_overrides()


def test_rollback_options_require_admin_or_developer_and_current_account_password(tmp_path, monkeypatch):
    path = tmp_path / "rollback-options.db"
    _create_update_database(path)
    _mock_release_catalog(
        monkeypatch,
        [
            _release("v1.3.82"),
            _release("v1.3.80"),
            _release("v1.3.79"),
        ],
    )
    client = _client_for_database(
        path, {"id": 1, "username": "Admin", "role": "Admin"}
    )
    before = sqlite3.connect(path)
    try:
        hashes_before = before.execute(
            "SELECT username,password_salt,password_hash FROM auth_users ORDER BY id"
        ).fetchall()
    finally:
        before.close()

    try:
        denied = client.post(
            "/api/update-center/rollback-options", json={"password": "wrong-password"}
        )
        assert denied.status_code == 403

        allowed = client.post(
            "/api/update-center/rollback-options",
            json={"password": "Customer-Password-987"},
        )
        assert allowed.status_code == 200, allowed.text
        body = allowed.json()
        assert [item["version"] for item in body["versions"]] == ["1.3.80", "1.3.79"]
        assert "browser cannot run the installer" in body["message"].lower()

        check = sqlite3.connect(path)
        try:
            hashes_after = check.execute(
                "SELECT username,password_salt,password_hash FROM auth_users ORDER BY id"
            ).fetchall()
            assert hashes_after == hashes_before
            assert check.execute(
                "SELECT action,details FROM audit_log ORDER BY id"
            ).fetchall() == [
                ("Application rollback denied", "Admin"),
                ("Application rollback authorized", "Admin"),
            ]
        finally:
            check.close()
    finally:
        _clear_overrides()


def test_rollback_options_denies_staff_without_writing_audit_or_exposing_previous_installers(tmp_path, monkeypatch):
    path = tmp_path / "rollback-staff.db"
    _create_update_database(path)
    _mock_release_catalog(monkeypatch, [_release("v1.3.80")])
    client = _client_for_database(
        path, {"id": 3, "username": "Staff", "role": "Staff"}
    )
    try:
        response = client.post(
            "/api/update-center/rollback-options", json={"password": "anything"}
        )
        assert response.status_code == 403
        conn = sqlite3.connect(path)
        try:
            assert conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0
        finally:
            conn.close()
    finally:
        _clear_overrides()


def test_update_center_requires_login_when_web_login_is_mandatory(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_REQUIRE_LOGIN", "1")
    path = tmp_path / "update-center-auth.db"
    _create_update_database(path)
    _mock_release_catalog(monkeypatch, [_release("v1.3.82")])
    client = _client_for_database(path)
    try:
        response = client.get("/api/update-center")
        assert response.status_code == 401
    finally:
        _clear_overrides()


def test_update_center_ui_distinguishes_windows_installer_from_hosted_web_deployment():
    root = Path(__file__).resolve().parents[1]
    app_source = (root / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    component = (root / "frontend" / "src" / "UpdateCenter.jsx").read_text(encoding="utf-8")

    assert "import UpdateCenter from './UpdateCenter';" in app_source
    assert "<UpdateCenter apiFetch={apiFetch}" in app_source
    assert "Download Windows installer" in component
    assert "Download previous versions" in component or "Load previous versions" in component
    assert "The browser cannot install or execute it." in component
    assert "does not perform rollback in the browser" in component
    assert "dangerouslySetInnerHTML" not in component
    assert "window.location" not in component
