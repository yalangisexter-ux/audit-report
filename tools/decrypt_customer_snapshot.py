"""Download and decrypt one encrypted business database snapshot."""

import argparse
import getpass
import os
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database_sync import decrypt_snapshot_bytes  # noqa: E402


REPOSITORY = "yalangisexter-ux/audit-report"


def main():
    parser = argparse.ArgumentParser(
        description="Download and decrypt an encrypted customer database snapshot."
    )
    parser.add_argument("installation_id", help="32-character snapshot ID shown in the app's Settings")
    parser.add_argument("--output", type=Path, help="Where to save the decrypted SQLite copy")
    args = parser.parse_args()
    if len(args.installation_id) != 32 or any(ch not in "0123456789abcdef" for ch in args.installation_id):
        parser.error("installation_id must be the 32-character ID shown in Settings")

    url = (
        f"https://raw.githubusercontent.com/{REPOSITORY}/main/"
        f"customer-data/{args.installation_id}.db.enc"
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RawStrengthEmployeeAuditManager-snapshot-reader"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            encrypted = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            parser.error("No snapshot exists for that installation ID yet.")
        parser.error(f"Could not download snapshot (HTTP {exc.code}).")
    except Exception as exc:
        parser.error(f"Could not download snapshot: {exc}")

    token = (os.environ.get("DB_SYNC_ENCRYPTION_SECRET") or "").strip()
    if not token:
        token = getpass.getpass("Existing DB_SYNC_ENCRYPTION_SECRET (input hidden): ").strip()
    if not token:
        parser.error("DB_SYNC_ENCRYPTION_SECRET is required; do not use a GitHub personal access token.")
    try:
        database_bytes = decrypt_snapshot_bytes(encrypted, token)
    except Exception as exc:
        parser.error(str(exc))

    output = args.output or Path.cwd() / f"customer-{args.installation_id}.db"
    output = output.resolve()
    if output.exists():
        parser.error(f"Refusing to overwrite an existing file: {output}")
    try:
        with tempfile.NamedTemporaryFile(prefix="rsc_validate_", suffix=".db", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(database_bytes)
        connection = sqlite3.connect(str(temp_path))
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError("The decrypted file failed SQLite integrity validation.")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if not {"employees", "tasks", "attendance"}.issubset(tables):
                raise ValueError("The decrypted file is missing required business tables.")
            if "auth_users" not in tables:
                raise ValueError("The snapshot is missing auth_users; both required accounts cannot be verified.")
            user_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(auth_users)").fetchall()
            }
            if "username" not in user_columns:
                raise ValueError("auth_users is missing its username column.")
            admin_customer = connection.execute(
                "SELECT COUNT(*) FROM auth_users WHERE username = ? COLLATE BINARY", ("Admin",)
            ).fetchone()[0]
            admin_developer = connection.execute(
                "SELECT COUNT(*) FROM auth_users WHERE username = ? COLLATE BINARY", ("admin",)
            ).fetchone()[0]
            if admin_customer != 1 or admin_developer != 1:
                raise ValueError(
                    "Snapshot must contain exactly one case-sensitive Admin and one case-sensitive admin account."
                )
            counts = {}
            for table in ("employees", "tasks", "attendance", "holidays"):
                if table in tables:
                    counts[table] = connection.execute(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).fetchone()[0]
        finally:
            connection.close()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(database_bytes)
    except Exception as exc:
        parser.error(f"Could not validate/save the decrypted database: {exc}")
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except (NameError, OSError):
            pass
    print(f"Validated snapshot saved to: {output}")
    print("Accounts verified (case-sensitive): Admin=1, admin=1")
    for table, count in counts.items():
        print(f"{table}: {count}")


if __name__ == "__main__":
    main()
