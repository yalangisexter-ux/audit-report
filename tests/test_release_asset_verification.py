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

    def fail_backup(self, destination, pages=-1, progress=None, name="main", sleep=0.250):
        raise __import__("sqlite3").OperationalError("simulated backup failure")

    monkeypatch.setattr(__import__("sqlite3").Connection, "backup", fail_backup)
    with pytest.raises(RuntimeError, match="migrations were cancelled"):
        app.create_pre_migration_backup(source_path, tmp_path / "backups")
