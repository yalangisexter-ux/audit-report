import json
import sqlite3
import tarfile

from database_sync import encrypt_snapshot_bytes
from tools.cloudflare_snapshot_archive import create_archive, validate_all


TEST_SECRET = "migration-test-secret-not-a-real-customer-key"
CANONICAL_ID = "a" * 32
OTHER_ID = "b" * 32


def _write_snapshot(path, usernames, recovery_overrides=None):
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE auth_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE BINARY UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            security_question TEXT NOT NULL,
            answer_salt TEXT NOT NULL,
            answer_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL);
        CREATE TABLE attendance (id INTEGER PRIMARY KEY, employee_id INTEGER, work_date TEXT);
        CREATE TABLE holidays (holiday_date TEXT PRIMARY KEY, holiday_name TEXT NOT NULL);
        """
    )
    for index, (username, role) in enumerate(usernames, start=1):
        connection.execute(
            """
            INSERT INTO auth_users (
                id, username, display_name, role, password_salt, password_hash,
                security_question, answer_salt, answer_hash, active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, '2026-01-01', '2026-01-01')
            """,
            (
                index,
                username,
                username,
                role,
                f"salt-{index}",
                f"hash-{index}",
                *(recovery_overrides or {}).get(username, ("question", f"answer-salt-{index}", f"answer-hash-{index}")),
            ),
        )
    connection.commit()
    payload = connection.serialize() + b"\n__RSC_JSON__\n" + json.dumps({"version": "test"}).encode()
    connection.close()
    path.write_bytes(encrypt_snapshot_bytes(payload, TEST_SECRET))


def test_archive_contains_every_encrypted_snapshot_and_hash_manifest(tmp_path):
    source_dir = tmp_path / "customer-data"
    source_dir.mkdir()
    (source_dir / f"{CANONICAL_ID}.db.enc").write_bytes(encrypt_snapshot_bytes(b"opaque-one", TEST_SECRET))
    (source_dir / f"{OTHER_ID}.db.enc").write_bytes(encrypt_snapshot_bytes(b"opaque-two", TEST_SECRET))

    archive_path = tmp_path / "snapshots.tar.gz"
    manifest_path = tmp_path / "manifest.json"
    result = create_archive(source_dir, archive_path, manifest_path)

    assert result["snapshot_count"] == 2
    assert archive_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["snapshot_count"] == 2
    with tarfile.open(archive_path, "r:gz") as archive:
        names = set(archive.getnames())
        assert f"customer-data/{CANONICAL_ID}.db.enc" in names
        assert f"customer-data/{OTHER_ID}.db.enc" in names
        archived_manifest = json.load(archive.extractfile("customer-data/manifest.json"))
        assert archived_manifest["snapshot_count"] == 2


def test_validation_preserves_case_sensitive_admin_accounts_only_for_canonical(tmp_path):
    _write_snapshot(
        tmp_path / f"{CANONICAL_ID}.db.enc",
        [("Admin", "Admin"), ("admin", "Developer")],
    )
    _write_snapshot(tmp_path / f"{OTHER_ID}.db.enc", [("admin", "Developer")])

    report = validate_all(tmp_path, TEST_SECRET, CANONICAL_ID)

    assert report["snapshot_count"] == 2
    assert report["validated_count"] == 2
    assert report["failure_count"] == 0
    assert report["canonical"]["has_Admin"] is True
    assert report["canonical"]["has_admin"] is True
    assert report["canonical"]["auth_user_count"] == 2


def test_validation_reports_corrupted_snapshot_without_discarding_it(tmp_path):
    _write_snapshot(
        tmp_path / f"{CANONICAL_ID}.db.enc",
        [("Admin", "Admin"), ("admin", "Developer")],
    )
    corrupted = tmp_path / f"{OTHER_ID}.db.enc"
    corrupted.write_bytes(encrypt_snapshot_bytes(b"valid-before-tamper", TEST_SECRET)[:-1] + b"X")

    report = validate_all(tmp_path, TEST_SECRET, CANONICAL_ID)

    assert report["snapshot_count"] == 2
    assert report["validated_count"] == 1
    assert report["failure_count"] == 1
    assert report["failures"][0]["file"] == corrupted.name
    assert corrupted.exists()



def test_canonical_snapshot_accepts_blank_recovery_fields_for_both_accounts(tmp_path):
    _write_snapshot(
        tmp_path / f"{CANONICAL_ID}.db.enc",
        [("Admin", "Admin"), ("admin", "Developer")],
        recovery_overrides={"Admin": ("", "", ""), "admin": ("", "", "")},
    )

    report = validate_all(tmp_path, TEST_SECRET, CANONICAL_ID)

    assert report["failure_count"] == 0
    assert report["canonical"]["has_Admin"] is True
    assert report["canonical"]["has_admin"] is True


def test_canonical_snapshot_rejects_partially_configured_recovery_fields(tmp_path):
    _write_snapshot(
        tmp_path / f"{CANONICAL_ID}.db.enc",
        [("Admin", "Admin"), ("admin", "Developer")],
        recovery_overrides={"Admin": ("recovery question", "", "")},
    )

    report = validate_all(tmp_path, TEST_SECRET, CANONICAL_ID)

    assert report["failure_count"] == 1
    assert "incomplete password-recovery metadata" in report["canonical_failure"]["reason"]
