"""Tests for secure verification of downloaded GitHub release installers."""
import hashlib

import pytest

import app


def test_valid_hhmm_rejects_malformed_attendance_times():
    assert app.valid_hhmm("09:30") is True
    assert app.valid_hhmm("23:59") is True
    assert app.valid_hhmm("24:00") is False
    assert app.valid_hhmm("9:30") is False
    assert app.valid_hhmm("noon") is False


def test_release_asset_checksum_accepts_matching_sha256():
    data = b"trusted installer payload"
    asset = {"digest": "sha256:" + hashlib.sha256(data).hexdigest()}
    assert app.verify_release_asset_bytes(data, asset) is True


def test_release_asset_checksum_rejects_modified_payload():
    asset = {"digest": "sha256:" + hashlib.sha256(b"original").hexdigest()}
    with pytest.raises(ValueError, match="checksum verification failed"):
        app.verify_release_asset_bytes(b"modified", asset)


def test_release_asset_requires_digest_for_updates():
    with pytest.raises(ValueError, match="no SHA-256 digest"):
        app.verify_release_asset_bytes(b"payload", {}, require_digest=True)


def test_legacy_rollback_asset_can_be_used_without_digest():
    # Older releases may not expose digest metadata; size and trusted HTTPS URL
    # are checked by the rollback flow before this helper is called.
    assert app.verify_release_asset_bytes(b"legacy payload", {}, require_digest=False) is False


def test_release_asset_rejects_malformed_digest():
    with pytest.raises(ValueError, match="invalid SHA-256 digest"):
        app.verify_release_asset_bytes(b"payload", {"digest": "md5:abc"})



def test_pre_migration_backup_is_a_valid_sqlite_snapshot(tmp_path):
    source_path = tmp_path / "employee_audit.db"
    backup_dir = tmp_path / "backups"
    connection = __import__("sqlite3").connect(source_path)
    connection.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO employees (name) VALUES (?)", ("Existing employee",))
    connection.commit()
    connection.close()

    backup_path = app.create_pre_migration_backup(source_path, backup_dir)

    assert backup_path is not None
    backup = __import__("sqlite3").connect(backup_path)
    assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert backup.execute("SELECT name FROM employees").fetchone()[0] == "Existing employee"
    backup.close()


def test_pre_migration_backup_failure_stops_migrations(tmp_path, monkeypatch):
    source_path = tmp_path / "employee_audit.db"
    connection = __import__("sqlite3").connect(source_path)
    connection.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT)")
    connection.commit()
    connection.close()

    sqlite3 = __import__("sqlite3")

    def fail_connect(*args, **kwargs):
        raise sqlite3.OperationalError("simulated backup failure")

    monkeypatch.setattr(sqlite3, "connect", fail_connect)
    with pytest.raises(RuntimeError, match="migrations were cancelled"):
        app.create_pre_migration_backup(source_path, tmp_path / "backups")



def test_bundled_wallpaper_artwork_is_available():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for name in ("galaxy.svg", "lord_shiva.svg", "love_couples.svg", "milky_way_waves.svg", "ocean_waves.svg"):
        artwork = root / "assets" / "wallpapers" / name
        assert artwork.is_file()
        assert "<svg" in artwork.read_text(encoding="utf-8")


def test_home_ui_restores_icons_and_quick_dropdowns():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "homeThemeDropdown" in source
    assert "homeWallpaperDropdown" in source
    assert 'icon_label = QLabel(symbol)' in source
    assert 'QPixmap' in source
    assert 'QWidget#appPageSurface { background: transparent; color: #0F172A; }' in source
    assert 'QWidget#appPageSurface { background: transparent; color: #F8FAFC; }' in source
    assert 'background-color: #F8FAFC' in source
    assert 'background-color: #111827' in source
    assert 'combobox-popup: 0' in source
    assert 'QComboBox QListView::item:selected' in source
    assert 'page.setObjectName("appPageSurface")' in source
    assert 'page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)' in source
    assert 'QWidget#homeContent, QWidget#pageContent { background-color: #F8FAFC' in source
    assert 'QWidget#homeContent, QWidget#pageContent { background-color: #111827' in source
    assert 'page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)' in source
    assert 'QComboBox QAbstractItemView::item:selected' in source
    assert 'QWidget#guideItem { background: rgba(17,24,39,0.92)' in source
    assert 'QTextEdit#reportPreview { background: #111827' in source
    assert 'QPrintPreviewDialog' in source
    assert 'def open_print_preview(self):' in source
    assert 'QPrintPreviewDialog(printer, self)' in source
    assert "def apply_content_surface_styles(self, theme_name=None):" in source
    assert 'QWidget#kpiCard, QWidget#dashboardPanel { background-color: #FFFFFF; color: #0F172A;' in source
    assert 'QWidget#kpiCard, QWidget#dashboardPanel { background-color: #0F172A; color: #F8FAFC;' in source
    assert 'QWidget#settingsContent { background-color: #F8FAFC; color: #0F172A; }' in source
    assert 'QWidget#settingsContent { background-color: #111827; color: #F8FAFC; }' in source
    assert 'background, foreground, border = "#FFFFFF", "#0F172A", "#E2E8F0"' in source
    assert 'background, foreground, border = "#111827", "#F8FAFC", "#64748B"' in source
    assert "self.apply_content_surface_styles(theme_name)" in source


def test_live_wallpapers_use_high_resolution_photos_with_animation():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "class WallpaperPhotoLoader(QThread)" in source
    assert "PHOTO_WALLPAPERS" in source
    assert "images.unsplash.com/photo-1707057538849-f723c167324b" in source
    assert "images.unsplash.com/photo-1429305223369-4d065fdb6f53" in source
    assert "images.unsplash.com/photo-1533743725296-2e099eed32c6" in source
    assert "wallpaper_pixmap" in source
    assert "zoom = 1.035 + 0.012 * math.sin(self.phase * 0.35)" in source
    assert "Real photographic wallpapers use a slow Ken Burns pan/zoom" in source
    assert "QSvgRenderer" not in source


def test_release_build_bundles_photo_wallpapers_for_offline_use():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "master.yml").read_text(encoding="utf-8")
    app_source = (root / "app.py").read_text(encoding="utf-8")
    assert "Download high-resolution photographic wallpaper assets" in workflow
    assert '"galaxy.jpg"' in workflow
    assert '"milky_way.jpg"' in workflow
    assert '"ocean_waves.jpg"' in workflow
    assert '"lord_shiva.jpg"' in workflow
    assert '"love_couples.jpg"' in workflow
    assert 'Path("assets") / "wallpapers" / "photos" / filename' in app_source
    assert '--add-data "assets;assets"' in workflow


def test_dashboard_clock_colorful_icons_and_print_preview_regression():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "def refresh_dashboard_clock(self):" in source
    assert "self._dashboard_clock_timer.start(1000)" in source
    assert '"🟢"' in source and '"🔴"' in source and '"🟣"' in source
    assert "Live print preview — updates when report options change" in source
    assert "self.report_summary.setMinimumHeight(220)" in source
    assert "def preview_report(self):" in source
    assert "def print_report(self):" in source


def test_release_version_tuple_normalizes_v_prefix_and_rejects_invalid_tags():
    assert app.release_version_tuple("v1.2.31") == (1, 2, 31)
    assert app.release_version_tuple("1.2.32") == (1, 2, 32)
    with pytest.raises(ValueError):
        app.release_version_tuple("v1.2")
    with pytest.raises(ValueError):
        app.release_version_tuple("v1.2.3-rc1")


def test_update_worker_uses_latest_published_stable_release(monkeypatch):
    release = {
        "tag_name": "v1.2.36",
        "draft": False,
        "prerelease": False,
        "published_at": "2026-10-14T08:00:00Z",
        "assets": [],
    }
    requested = []
    monkeypatch.setattr(
        app.UpdateWorker,
        "request_bytes",
        staticmethod(lambda url, accept="application/vnd.github+json": (
            requested.append(url) or __import__("json").dumps(release).encode()
        )),
    )
    worker = app.UpdateWorker("1.2.35")
    emitted = []
    worker.current.connect(lambda version: emitted.append(("current", version)))
    worker.failed.connect(lambda message: emitted.append(("failed", message)))
    worker.ready.connect(lambda path, version: emitted.append(("ready", version)))

    worker.run()

    assert requested == [
        "https://api.github.com/repos/yalangisexter-ux/audit-report/releases/latest"
    ]
    assert emitted
    assert emitted[0][0] == "failed"
    assert "missing a trusted installer" in emitted[0][1]
def test_update_worker_retries_after_a_read_timeout(monkeypatch):
    release = {
        "tag_name": "v1.2.36",
        "draft": False,
        "prerelease": False,
        "published_at": "2026-10-14T08:00:00Z",
        "assets": [],
    }
    attempts = []

    def request(url, accept="application/vnd.github+json"):
        attempts.append(url)
        if len(attempts) == 1:
            raise TimeoutError("The read operation timed out")
        return __import__("json").dumps(release).encode()

    monkeypatch.setattr(app.UpdateWorker, "request_bytes", staticmethod(request))
    monkeypatch.setattr(__import__("time"), "sleep", lambda _seconds: None)
    worker = app.UpdateWorker("1.2.35")
    emitted = []
    worker.failed.connect(lambda message: emitted.append(message))

    worker.run()

    assert len(attempts) == 2
    assert emitted
    assert "missing a trusted installer" in emitted[0]


def test_previous_release_choices_only_returns_installable_stable_versions_sorted_newest_first():
    def release(tag, *, draft=False, prerelease=False, published=True, size=1000000, url=None):
        return {
            "tag_name": tag,
            "draft": draft,
            "prerelease": prerelease,
            "published_at": "2026-10-14T00:00:00Z" if published else None,
            "assets": [{
                "name": "RawStrengthEmployeeAuditManager-Setup.exe",
                "browser_download_url": url or (
                    "https://github.com/yalangisexter-ux/audit-report/releases/download/"
                    + tag + "/RawStrengthEmployeeAuditManager-Setup.exe"
                ),
                "size": size,
            }],
        }

    releases = [
        release("v1.2.10"),
        release("v1.2.31"),
        release("v1.2.99", prerelease=True),
        release("v9.0.0", draft=True),
        release("v1.2.30", published=False),
        release("v1.2.29", size=999999),
        release("v1.2.28", url="https://example.com/installer.exe"),
        release("not-a-version"),
        release("v1.2.32"),
    ]
    choices = app.previous_release_choices(releases, "1.2.32")
    assert [choice[0] for choice in choices] == ["v1.2.31", "v1.2.10"]
