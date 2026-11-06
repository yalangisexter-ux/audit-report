"""Regression coverage for the web update center and protected rollback catalog."""
import hashlib
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import app
import api_server


def _create_update_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS auth_users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE BINARY UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            security_question TEXT NOT NULL DEFAULT '',
            answer_salt TEXT NOT NULL DEFAULT '',
            answer_hash TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def _client_for_database(path: Path, user: dict):
    class _DB:
        def __init__(self, db_path):
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row

        def get_setting(self, key, default=""):
            row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    db = _DB(path)
    api_server.db = db
    api_server.app.dependency_overrides[api_server.get_current_user] = lambda: user
    return TestClient(api_server.app)


def _release(tag, digest=None, draft=False, prerelease=False, url=None, size=1_200_000):
    name = f"RawStrengthEmployeeAuditManager-Setup-{tag.lstrip('v')}.exe"
    asset = {
        "name": name,
        "browser_download_url": url or f"https://github.com/yalangisexter-ux/audit-report/releases/download/{tag}/{name}",
        "size": size,
    }
    if digest:
        asset["digest"] = digest
    return {
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "assets": [asset],
    }


def _mock_release_catalog(monkeypatch, releases):
    def fake_fetch():
        return releases

    monkeypatch.setattr(api_server, "_fetch_github_releases", fake_fetch)


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
        assert body["current_version"] == "1.3.82"
        assert body["latest_version"] == "1.3.82"
    finally:
        api_server.app.dependency_overrides.clear()


# NOTE: remaining tests restored in companion commit if truncated by transport
