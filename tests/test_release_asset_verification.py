"""Tests for secure verification of downloaded GitHub release installers."""
import hashlib

import pytest

import app


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
    assert 'QWidget#homeContent { background: rgba(15,23,42,0.94)' in source
    assert 'QWidget#pageContent { background: rgba(15,23,42,0.92)' in source
    assert 'QWidget#sessionStrip { background: rgba(11,18,32,0.94)' in source
    assert 'QWidget#guideItem { background: rgba(17,24,39,0.92)' in source
    assert 'background: rgba(248,250,252,0.96)' in source


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
