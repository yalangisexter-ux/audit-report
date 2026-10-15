import sqlite3
import os

import pytest

from database_sync import (
    create_encrypted_database_snapshot,
    decrypt_snapshot_bytes,
    encrypt_snapshot_bytes,
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


def test_database_snapshot_excludes_authentication_and_local_settings(tmp_path):
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
        assert "auth_users" not in tables
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


def test_successful_database_commits_request_sync_without_breaking_local_save():
    connection = sqlite3.connect(":memory:", factory=SyncableSQLiteConnection)
    requested = []
    connection.set_commit_callback(lambda: requested.append(True))
    connection.execute("CREATE TABLE entries(value TEXT)")
    connection.execute("INSERT INTO entries VALUES('saved locally')")

    connection.commit()

    assert connection.execute("SELECT value FROM entries").fetchone()[0] == "saved locally"
    assert requested == [True]
    connection.close()
