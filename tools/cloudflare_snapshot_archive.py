"""Archive and validate every encrypted Raw Strength customer database snapshot.

The archive contains only the already-encrypted snapshot files plus a SHA-256
manifest. Validation decrypts one snapshot at a time in memory using the same
compatibility decoder as the desktop sync implementation; no plaintext database
is written to the archive. Temporary SQLite files used only for validation are
deleted immediately.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Running this file directly puts tools/ rather than the repository root on sys.path.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from database_sync import decrypt_snapshot_bytes

SNAPSHOT_NAME = re.compile(r"^[0-9a-f]{32}\.db\.enc$")
SQLITE_MAGIC = b"SQLite format 3\x00"
JSON_MARKER = b"\n__RSC_JSON__\n"
CANONICAL_ACCOUNT_COLUMNS = {
    "username",
    "display_name",
    "role",
    "password_salt",
    "password_hash",
    "security_question",
    "answer_salt",
    "answer_hash",
    "active",
    "created_at",
    "updated_at",
}
VALID_ROLES = {"Admin", "Developer", "HR", "Staff", "Employee"}


def _snapshot_files(source_dir: Path) -> list[Path]:
    if not source_dir.is_dir():
        raise ValueError(f"Snapshot directory does not exist: {source_dir}")
    files = sorted(path for path in source_dir.iterdir() if path.is_file() and path.name.endswith(".db.enc"))
    invalid = [path.name for path in files if not SNAPSHOT_NAME.fullmatch(path.name)]
    if invalid:
        raise ValueError(f"Unexpected encrypted snapshot filename(s): {len(invalid)}")
    if not files:
        raise ValueError("No encrypted customer snapshots were found.")
    return files


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_archive(source_dir: Path, archive_path: Path, manifest_path: Path) -> dict[str, Any]:
    """Archive every encrypted snapshot without decrypting or changing its bytes."""
    files = _snapshot_files(source_dir)
    manifest = {
        "format": "raw-strength-encrypted-customer-snapshot-archive-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_count": len(files),
        "total_encrypted_bytes": sum(path.stat().st_size for path in files),
        "snapshots": [
            {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
            for path in files
        ],
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes)

    with tarfile.open(archive_path, mode="w:gz", compresslevel=6) as archive:
        for path in files:
            archive.add(path, arcname=f"customer-data/{path.name}", recursive=False)
        info = tarfile.TarInfo("customer-data/manifest.json")
        info.size = len(manifest_bytes)
        info.mtime = int(datetime.now(timezone.utc).timestamp())
        archive.addfile(info, io.BytesIO(manifest_bytes))

    result = {
        "snapshot_count": len(files),
        "total_encrypted_bytes": manifest["total_encrypted_bytes"],
        "archive_bytes": archive_path.stat().st_size,
        "archive_sha256": _sha256_file(archive_path),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    print(json.dumps(result, sort_keys=True))
    return result


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _open_sqlite_payload(sqlite_bytes: bytes) -> sqlite3.Connection:
    """Open a SQLite image in memory, with a temp-file fallback for damaged images."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(sqlite_bytes)
        connection.execute("SELECT 1").fetchone()
        return connection
    except Exception:
        connection.close()

    # Use a dedicated temporary directory and a normal read-only SQLite
    # connection. Some SQLite builds on hosted runners reject immutable file
    # URIs for temp files even when the file exists; the URI failure is
    # reported as "unable to open database file". A private directory also
    # prevents collisions and keeps cleanup deterministic.
    directory = tempfile.mkdtemp(prefix="rsc_validate_")
    path = os.path.join(directory, "snapshot.sqlite3")
    try:
        Path(path).write_bytes(sqlite_bytes)
        os.chmod(path, 0o400)

        class _ValidationConnection(sqlite3.Connection):
            pass

        connection = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
            timeout=20,
            factory=_ValidationConnection,
        )
        connection.execute("SELECT 1").fetchone()
        connection._rsc_temp_path = path
        connection._rsc_temp_dir = directory
        return connection
    except Exception as exc:
        try:
            os.unlink(path)
        except OSError:
            pass
        try:
            os.rmdir(directory)
        except OSError:
            pass
        raise RuntimeError(
            f"SQLite temporary-file fallback failed ({type(exc).__name__}: {exc}); "
            f"temp directory writable={os.access(os.path.dirname(directory), os.W_OK)}"
        ) from exc


def _close_sqlite_connection(connection: sqlite3.Connection) -> None:
    path = getattr(connection, "_rsc_temp_path", None)
    directory = getattr(connection, "_rsc_temp_dir", None)
    try:
        connection.close()
    finally:
        if path:
            try:
                os.chmod(path, 0o600)
                os.unlink(path)
            except OSError:
                pass
        if directory:
            try:
                os.rmdir(directory)
            except OSError:
                pass


def _validate_sqlite_payload(payload: bytes, *, canonical: bool) -> dict[str, Any]:
    sqlite_bytes, marker, json_bytes = payload.partition(JSON_MARKER)
    if not sqlite_bytes.startswith(SQLITE_MAGIC):
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Snapshot payload is neither SQLite nor valid JSON.") from exc
        if canonical:
            raise ValueError("Canonical customer snapshot is not a SQLite database.")
        if not isinstance(parsed, (dict, list)):
            raise ValueError("Legacy JSON snapshot has an unsupported top-level value.")
        return {"format": "json", "table_count": 0, "row_counts": {}, "auth_user_count": 0}

    if marker and json_bytes:
        try:
            json.loads(json_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Snapshot's appended JSON manifest is invalid.") from exc

    try:
        connection = _open_sqlite_payload(sqlite_bytes)
    except Exception as exc:
        raise ValueError(
            f"SQLite payload could not be opened after decrypt ({type(exc).__name__}: {exc}). "
            "The encrypted file may be truncated or damaged."
        ) from exc

    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise ValueError("SQLite integrity_check did not return ok.")
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise ValueError(f"SQLite foreign_key_check reported {len(foreign_key_errors)} violation(s).")

        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if not row[0].startswith("sqlite_")
        }
        row_counts: dict[str, int] = {}
        for table in sorted(tables):
            row_counts[table] = int(
                connection.execute(f"SELECT COUNT(*) FROM {_quote_identifier(table)}").fetchone()[0]
            )

        auth_user_count = 0
        has_admin = False
        has_lower_admin = False
        if "auth_users" in tables:
            table_info = connection.execute("PRAGMA table_info(auth_users)").fetchall()
            auth_columns = {row[1] for row in table_info}
            if "username" in auth_columns:
                rows = connection.execute("SELECT * FROM auth_users").fetchall()
                auth_user_count = len(rows)
                username_index = next(index for index, column in enumerate(table_info) if column[1] == "username")
                usernames = [str(row[username_index]) for row in rows]
                if len(usernames) != len(set(usernames)):
                    raise ValueError("auth_users contains duplicate case-sensitive usernames.")
                has_admin = usernames.count("Admin") == 1
                has_lower_admin = usernames.count("admin") == 1

            if canonical:
                missing = sorted(CANONICAL_ACCOUNT_COLUMNS - auth_columns)
                if missing:
                    raise ValueError("Canonical auth_users schema is missing required account metadata.")
                rows = connection.execute(
                    "SELECT username, role, active, password_salt, password_hash, "
                    "security_question, answer_salt, answer_hash, created_at, updated_at "
                    "FROM auth_users WHERE username COLLATE BINARY IN (?, ?)",
                    ("Admin", "admin"),
                ).fetchall()
                by_username = {row[0]: row for row in rows}
                if len(rows) != 2 or set(by_username) != {"Admin", "admin"}:
                    raise ValueError("Canonical snapshot does not contain exactly one Admin and one admin account.")
                for username, row in by_username.items():
                    if row[1] not in VALID_ROLES or row[2] not in (0, 1):
                        raise ValueError(f"Canonical {username} account has invalid role or active flag.")
                    if any(value is None or str(value) == "" for value in row[3:]):
                        raise ValueError(f"Canonical {username} account is missing password/security metadata.")
        elif canonical:
            raise ValueError("Canonical snapshot has no auth_users table.")

        if canonical and not (has_admin and has_lower_admin):
            raise ValueError("Canonical snapshot failed the case-sensitive Admin/admin identity check.")

        return {
            "format": "sqlite",
            "table_count": len(tables),
            "row_counts": row_counts,
            "auth_user_count": auth_user_count,
            "has_Admin": has_admin,
            "has_admin": has_lower_admin,
        }
    finally:
        _close_sqlite_connection(connection)


def validate_all(
    source_dir: Path,
    secret: str,
    canonical_id: str,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Decrypt and validate every snapshot in memory; require the canonical accounts."""
    if not secret or not secret.strip():
        raise ValueError("DB_SYNC_ENCRYPTION_SECRET is required for snapshot validation.")
    if not re.fullmatch(r"[0-9a-f]{32}", canonical_id):
        raise ValueError("Canonical installation ID must be 32 lowercase hexadecimal characters.")

    files = _snapshot_files(source_dir)
    canonical_path = source_dir / f"{canonical_id}.db.enc"
    if canonical_path not in files:
        raise ValueError("The canonical customer snapshot is missing from customer-data.")

    failures: list[dict[str, str]] = []
    canonical_summary: dict[str, Any] | None = None
    canonical_failure: dict[str, str] | None = None
    validated = 0
    formats: dict[str, int] = {"sqlite": 0, "json": 0}
    canonical_encrypted_sha256 = ""

    for path in files:
        is_canonical = path == canonical_path
        try:
            encrypted = path.read_bytes()
            payload = decrypt_snapshot_bytes(encrypted, secret)
            summary = _validate_sqlite_payload(payload, canonical=is_canonical)
            validated += 1
            formats[summary["format"]] = formats.get(summary["format"], 0) + 1
            if is_canonical:
                canonical_summary = summary
                canonical_encrypted_sha256 = hashlib.sha256(encrypted).hexdigest()
        except Exception as exc:
            failure = {
                "file": path.name,
                "error_type": type(exc).__name__,
                "reason": str(exc).replace("\n", " ")[:240],
            }
            failures.append(failure)
            if is_canonical:
                canonical_failure = failure

    report = {
        "format": "raw-strength-snapshot-validation-v1",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_count": len(files),
        "validated_count": validated,
        "failure_count": len(failures),
        "format_counts": formats,
        "canonical_snapshot": f"{canonical_id}.db.enc",
        "canonical_encrypted_sha256": canonical_encrypted_sha256,
        "canonical": canonical_summary,
        "canonical_failure": canonical_failure,
        "failures": failures,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "snapshot_count": len(files),
                "validated_count": validated,
                "failure_count": len(failures),
                "format_counts": formats,
                "canonical_Admin": bool(canonical_summary and canonical_summary.get("has_Admin")),
                "canonical_admin": bool(canonical_summary and canonical_summary.get("has_admin")),
                "canonical_failure": canonical_failure,
                "other_failures": [item for item in failures if item["file"] != canonical_path.name],
            },
            sort_keys=True,
        )
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    archive_parser = subparsers.add_parser("archive", help="Archive all encrypted snapshots.")
    archive_parser.add_argument("--source-dir", required=True, type=Path)
    archive_parser.add_argument("--archive-output", required=True, type=Path)
    archive_parser.add_argument("--manifest-output", required=True, type=Path)

    validate_parser = subparsers.add_parser("validate", help="Validate every encrypted snapshot.")
    validate_parser.add_argument("--source-dir", required=True, type=Path)
    validate_parser.add_argument("--canonical-id", required=True)
    validate_parser.add_argument("--report-output", required=True, type=Path)
    validate_parser.add_argument(
        "--secret-env",
        default="DB_SYNC_ENCRYPTION_SECRET",
        help="Environment variable containing the existing snapshot encryption secret.",
    )

    args = parser.parse_args()
    if args.command == "archive":
        create_archive(args.source_dir, args.archive_output, args.manifest_output)
        return

    secret = os.environ.get(args.secret_env, "")
    report = validate_all(args.source_dir, secret, args.canonical_id, args.report_output)
    if report["failure_count"] or report["validated_count"] != report["snapshot_count"]:
        raise SystemExit(1)
    canonical = report.get("canonical") or {}
    if not canonical.get("has_Admin") or not canonical.get("has_admin"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
