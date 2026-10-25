import os
from pathlib import Path
import sqlite3
import tempfile

import pytest

from database_sync import (
    create_encrypted_database_snapshot,
    decrypt_snapshot_bytes,
    encrypt_snapshot_bytes,
    GitHubDatabaseSync,
    protect_sync_token,
    SyncableSQLiteConnection,
    unprotect_sync_token,
)


TEST_TOKEN = "not-a-real-github-token-for-local-tests"


def test_encrypted_snapshot_round_trips_and_hides_plaintext():
    source = b"employee audit sample that must not appear in the public repository"

    encrypted = encrypt_snapshot_bytes(source, TEST_TOKEN)

    assert source not in encrypted
    assert decrypt_snapshot_bytes(encrypted, TEST_TOKEN) == source


def test_encrypted_snapshot_rejects_modified_ciphertext():
    encrypted = encrypt_snapshot_bytes(b"sample database bytes", TEST_TOKEN)
    altered = encrypted[:-1] + bytes([encrypted[-1] ^ 1])

    with pytest.raises(ValueError, match="Snapshot decryption failed"):
        decrypt_snapshot_bytes(altered, TEST_TOKEN)


def test_database_snapshot_includes_authentication_and_excludes_local_settings(tmp_path):
    database_path = tmp_path / "customer.db"
    source = sqlite3.connect(database_path)
    source.executescript(
        """
        CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE auth_users(id INTEGER PRIMARY KEY, password_hash TEXT NOT NULL);
        CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL);
        CREATE TABLE attendance(id INTEGER PRIMARY KEY, status TEXT NOT NULL);
        INSERT INTO settings VALUES('working_weekdays', '0,1,2,3,4');
        INSERT INTO settings VALUES('github_sync_token_dpapi', 'local protected credential');
        INSERT INTO auth_users VALUES(1, 'local password hash');
        INSERT INTO employees VALUES(1, 'Example Employee');
        INSERT INTO tasks VALUES(1, 'Example task');
        INSERT INTO attendance VALUES(1, 'Present');
        """
    )
    source.commit()
    source.close()

    encrypted = create_encrypted_database_snapshot(database_path, TEST_TOKEN)
    snapshot_path = tmp_path / "decrypted.db"
    snapshot_path.write_bytes(decrypt_snapshot_bytes(encrypted, TEST_TOKEN))
    snapshot = sqlite3.connect(snapshot_path)
    try:
        tables = {
            row[0]
            for row in snapshot.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "auth_users" in tables
        assert snapshot.execute("SELECT password_hash FROM auth_users").fetchone()[0] == "local password hash"
        assert snapshot.execute("SELECT name FROM employees").fetchone()[0] == "Example Employee"
        assert snapshot.execute("SELECT title FROM tasks").fetchone()[0] == "Example task"
        assert snapshot.execute("SELECT status FROM attendance").fetchone()[0] == "Present"
        assert snapshot.execute("SELECT key FROM settings").fetchall() == [("working_weekdays",)]
    finally:
        snapshot.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI is used for local token storage")
def test_sync_token_is_protected_for_the_current_windows_user():
    protected = protect_sync_token(TEST_TOKEN)

    assert TEST_TOKEN not in protected
    assert unprotect_sync_token(protected) == TEST_TOKEN


def test_successful_database_commits_stay_local_until_manual_push(tmp_path):
    database_path = tmp_path / "customer.db"
    sync = GitHubDatabaseSync(
        database_path, "example/repository", "a" * 32,
        worker_url="https://sync.example", encryption_secret=TEST_TOKEN,
    )
    connection = sqlite3.connect(database_path, factory=SyncableSQLiteConnection)
    connection.set_commit_callback(sync.mark_pending)
    connection.execute("CREATE TABLE entries(value TEXT)")
    connection.execute("INSERT INTO entries VALUES('saved locally')")

    connection.commit()

    assert connection.execute("SELECT value FROM entries").fetchone()[0] == "saved locally"
    assert sync.is_dirty
    assert sync._thread is None
    assert sync.status == "Changes waiting to push to encrypted cloud storage"
    connection.close()
    sync.close()


def test_worker_push_refuses_to_overwrite_undecryptable_remote_snapshot(tmp_path, monkeypatch):
    database_path = tmp_path / "customer.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE entries(value TEXT)")
    connection.execute("INSERT INTO entries VALUES('local')")
    connection.commit()
    connection.close()

    sync = GitHubDatabaseSync(
        database_path, "example/repository", "b" * 32,
        worker_url="https://sync.example", encryption_secret=TEST_TOKEN,
    )
    # Protect the only remote copy: a mismatched key must stop the upload.
    existing = encrypt_snapshot_bytes(b"existing customer snapshot", "different-legacy-secret")
    monkeypatch.setattr(sync, "_pull_encrypted_snapshot", lambda **kwargs: existing)
    requests = []

    def fake_request(method, endpoint, **kwargs):
        requests.append((method, endpoint, kwargs))
        raise AssertionError("An undecryptable remote snapshot must never be overwritten")

    monkeypatch.setattr(sync, "_worker_request", fake_request)
    with pytest.raises(RuntimeError, match="Upload was stopped to protect remote customer data"):
        sync._sync_once()

    assert not any(endpoint == "/push" for _, endpoint, _ in requests)
    assert sync.status != "Synced"
    sync.close()


def test_database_sync_implementation_is_bundled_not_downloaded_at_runtime():
    source_path = Path(__file__).resolve().parents[1] / "database_sync.py"
    source = source_path.read_text(encoding="utf-8")
    assert "def _load():" not in source
    assert "raw.githubusercontent.com/yalangisexter-ux/audit-report" not in source
    assert "def download_latest_snapshot(" in source


def test_push_uses_worker_and_keeps_installation_scoped_path(tmp_path, monkeypatch):
    database_path = tmp_path / "customer.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE entries(value TEXT)")
    connection.execute("INSERT INTO entries VALUES('local')")
    connection.commit()
    connection.close()

    sync = GitHubDatabaseSync(
        database_path, "example/repository", "c" * 32,
        worker_url="https://sync.example", encryption_secret=TEST_TOKEN,
    )
    monkeypatch.setattr(sync, "_pull_encrypted_snapshot", lambda: None)
    requests = []

    def fake_request(method, endpoint, **kwargs):
        requests.append((method, endpoint, kwargs))
        if endpoint == "/push":
            return {"success": True}
        raise AssertionError("Unexpected worker endpoint")

    monkeypatch.setattr(sync, "_worker_request", fake_request)
    sync._sync_once()

    assert requests[0][1] == "/push"
    assert requests[0][2]["payload"]["content"]
    assert sync.status == "Synced"
    sync.close()


def test_worker_network_failure_does_not_change_local_database(tmp_path, monkeypatch):
    database_path = tmp_path / "customer.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE entries(value TEXT)")
    connection.execute("INSERT INTO entries VALUES('safe')")
    connection.commit()
    connection.close()

    sync = GitHubDatabaseSync(
        database_path, "example/repository", "d" * 32,
        worker_url="https://sync.example", encryption_secret=TEST_TOKEN,
    )
    monkeypatch.setattr(sync, "_pull_encrypted_snapshot", lambda: None)
    monkeypatch.setattr(sync, "_worker_request", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network down")))
    with pytest.raises(RuntimeError, match="network down"):
        sync._sync_once()
    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute("SELECT value FROM entries").fetchone()[0] == "safe"
    finally:
        connection.close()
    sync.close()


def test_missing_encryption_key_never_overwrites_remote_snapshot(tmp_path, monkeypatch):
    sync = GitHubDatabaseSync(
        tmp_path / "customer.db", "example/repository", "e" * 32,
        worker_url="https://sync.example",
    )
    monkeypatch.setattr(sync, "_pull_encrypted_snapshot", lambda **kwargs: b"legacy encrypted snapshot")
    with pytest.raises(RuntimeError, match="No compatible local encryption secret"):
        sync._sync_once()
    sync.close()


def test_download_latest_snapshot_with_candidate_secret_and_prefer_latest(tmp_path, monkeypatch):
    source_db = tmp_path / "source.db"
    conn = sqlite3.connect(source_db)
    conn.execute("CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO employees VALUES(1, 'Alice')")
    conn.commit()
    conn.close()

    secret = "CustomDeveloperSecret123!"
    encrypted = create_encrypted_database_snapshot(source_db, secret)

    dest_db = tmp_path / "dest.db"
    sync = GitHubDatabaseSync(
        dest_db, "example/repository", "f" * 32,
        worker_url="https://sync.example", encryption_secret="DifferentSecret456!",
    )
    passed_args = {}

    def fake_pull(target_installation_id="", prefer_latest=False):
        passed_args["target_installation_id"] = target_installation_id
        passed_args["prefer_latest"] = prefer_latest
        return encrypted

    monkeypatch.setattr(sync, "_pull_encrypted_snapshot", fake_pull)
    raw = sync.download_latest_snapshot(candidate_secret=secret, prefer_latest=True)
    assert len(raw) > 0
    assert passed_args["prefer_latest"] is True

    # Validate decrypted database contents
    test_conn = sqlite3.connect(f"file:memdb?mode=memory&cache=shared")
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as h:
        tmp_f = Path(h.name)
        h.write(raw)
    try:
        check_conn = sqlite3.connect(str(tmp_f))
        assert check_conn.execute("SELECT name FROM employees").fetchone()[0] == "Alice"
        check_conn.close()
    finally:
        tmp_f.unlink(missing_ok=True)
    sync.close()


def test_download_latest_snapshot_accepts_mobile_json_manifest(tmp_path, monkeypatch):
    """Mobile/APK pushes JSON (not SQLite). Desktop must accept and return it for merge."""
    import json

    secret = "Devlopershouse@1996#"
    manifest = {
        "version": "1.3.25",
        "auth_users": [
            {
                "username": "sharedadmin",
                "display_name": "Shared Admin",
                "role": "Admin",
                "password_salt": "salt",
                "password_hash": "hash",
                "active": 1,
            }
        ],
        "employees": [{"id": 1, "name": "Mobile Employee", "employee_code": "M1"}],
        "tasks": [],
        "attendance": {},
        "source": "mobile-apk",
    }
    encrypted = encrypt_snapshot_bytes(json.dumps(manifest).encode("utf-8"), secret)

    dest_db = tmp_path / "dest.db"
    sync = GitHubDatabaseSync(
        dest_db,
        "example/repository",
        "c4cf201d3c68e2fcaf60aa05fd423d9a",
        worker_url="https://sync.example",
        encryption_secret=secret,
    )
    monkeypatch.setattr(sync, "_pull_encrypted_snapshot", lambda **kwargs: encrypted)
    raw = sync.download_latest_snapshot(prefer_latest=True)
    parsed = json.loads(raw.decode("utf-8"))
    assert parsed["auth_users"][0]["username"] == "sharedadmin"
    assert parsed["employees"][0]["name"] == "Mobile Employee"
    sync.close()
