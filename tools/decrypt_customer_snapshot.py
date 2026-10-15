"""Download and decrypt one encrypted customer database snapshot."""

import argparse
import getpass
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
    parser.add_argument("installation_id", help="32-character ID shown in the app's Settings")
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

    token = getpass.getpass("GitHub sync token (input hidden): ")
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
            if "auth_users" in tables:
                raise ValueError("The snapshot unexpectedly contains login credentials; export stopped.")
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
    print(f"Decrypted business-data snapshot saved to: {output}")


if __name__ == "__main__":
    main()
