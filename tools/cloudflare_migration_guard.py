"""Strict pre-migration validation for the Raw Strength Cloudflare D1 cutover.

This tool decrypts only with DB_SYNC_ENCRYPTION_SECRET (no fallback keys), validates
both case-sensitive accounts and source/target schema compatibility, verifies that
the target D1 export is still empty, and encrypts the D1 pre-migration SQL backup.
It never writes customer rows to D1.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
import zlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"RSCDB1"
AAD = b"RawStrengthEmployeeAuditManager:encrypted-customer-database:v1"
HEADER_SIZE = len(MAGIC) + 16 + 12
REQUIRED_ACCOUNT_COLUMNS = {
    "username", "display_name", "role", "password_salt", "password_hash",
    "security_question", "answer_salt", "answer_hash", "active", "created_at", "updated_at",
}
VALID_ROLES = {"Admin", "Developer", "HR", "Staff", "Employee"}


def decrypt_snapshot(path: Path, secret: str) -> bytes:
    encrypted = path.read_bytes()
    if len(encrypted) <= HEADER_SIZE or not encrypted.startswith(MAGIC):
        raise ValueError("Source is not a supported RSCDB1 encrypted snapshot.")
    header = encrypted[:HEADER_SIZE]
    salt = encrypted[len(MAGIC):len(MAGIC) + 16]
    nonce = encrypted[len(MAGIC) + 16:HEADER_SIZE]
    key = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=300_000).derive(
        secret.strip().encode("utf-8")
    )
    compressed = AESGCM(key).decrypt(nonce, encrypted[HEADER_SIZE:], header + AAD)
    return zlib.decompress(compressed)


def encrypt_bytes(payload: bytes, secret: str) -> bytes:
    import secrets

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    header = MAGIC + salt + nonce
    key = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=300_000).derive(
        secret.strip().encode("utf-8")
    )
    return header + AESGCM(key).encrypt(nonce, zlib.compress(payload, level=6), header + AAD)


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if row[0] != "sqlite_sequence"
    }


def columns(connection: sqlite3.Connection, table: str) -> list[str]:
    quoted = '"' + table.replace('"', '""') + '"'
    return [row[1] for row in connection.execute(f"PRAGMA table_info({quoted})").fetchall()]


def row_count(connection: sqlite3.Connection, table: str) -> int:
    quoted = '"' + table.replace('"', '""') + '"'
    return int(connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])


def validate_source(connection: sqlite3.Connection) -> dict[str, int]:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if not integrity or integrity[0] != "ok":
        raise ValueError("Decrypted source database failed PRAGMA integrity_check.")
    tables = table_names(connection)
    required_tables = {"auth_users", "employees", "tasks", "attendance", "holidays"}
    missing = sorted(required_tables - tables)
    if missing:
        raise ValueError("Source is missing required tables: " + ", ".join(missing))

    account_columns = set(columns(connection, "auth_users"))
    missing_columns = sorted(REQUIRED_ACCOUNT_COLUMNS - account_columns)
    if missing_columns:
        raise ValueError("auth_users is missing required fields: " + ", ".join(missing_columns))

    account_rows = {}
    for username in ("Admin", "admin"):
        rows = connection.execute(
            "SELECT username, role, active, password_salt, password_hash, "
            "security_question, answer_salt, answer_hash, created_at, updated_at "
            "FROM auth_users WHERE username = ? COLLATE BINARY",
            (username,),
        ).fetchall()
        if len(rows) != 1 or rows[0][0] != username:
            raise ValueError(f"Source must contain exactly one case-sensitive {username} account.")
        row = rows[0]
        if row[1] not in VALID_ROLES:
            raise ValueError(f"{username} has an unsupported role value.")
        if row[2] not in (0, 1):
            raise ValueError(f"{username} has an invalid active flag.")
        if any(value is None or str(value) == "" for value in row[3:]):
            raise ValueError(f"{username} is missing password/security metadata.")
        account_rows[username] = {"role": row[1], "active": int(row[2])}

    fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if fk_errors:
        raise ValueError(f"Source has {len(fk_errors)} foreign-key integrity violation(s).")

    counts = {table: row_count(connection, table) for table in sorted(tables)}
    print("SOURCE SQLITE INTEGRITY: PASS")
    print("CASE-SENSITIVE ACCOUNTS: Admin=1, admin=1")
    for username, values in account_rows.items():
        print(f"ACCOUNT {username}: role={values['role']}, active={values['active']} (hashes preserved; not displayed)")
    for table, count in counts.items():
        print(f"SOURCE ROWS {table}: {count}")
    return counts


def validate_target(source: sqlite3.Connection, export_path: Path) -> None:
    with tempfile.NamedTemporaryFile(prefix="rsc_d1_export_", suffix=".db", delete=False) as handle:
        target_path = Path(handle.name)
    target = None
    try:
        target = sqlite3.connect(str(target_path))
        target.executescript(export_path.read_text(encoding="utf-8"))
        integrity = target.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise ValueError("D1 pre-migration export failed local SQLite integrity validation.")

        source_tables = table_names(source)
        target_tables = table_names(target)
        missing = sorted(source_tables - target_tables)
        if missing:
            raise ValueError("D1 is missing source tables: " + ", ".join(missing))
        for table in sorted(source_tables):
            source_columns = columns(source, table)
            target_columns = columns(target, table)
            if source_columns != target_columns:
                raise ValueError(
                    f"Schema mismatch for {table}: source columns {source_columns}; D1 columns {target_columns}"
                )

        unexpected_rows = []
        for table in sorted(target_tables):
            count = row_count(target, table)
            if table == "settings":
                rows = target.execute("SELECT key, value FROM settings").fetchall()
                if any(row != ("working_weekdays", "0,1,2,3,4,6") for row in rows) or len(rows) > 1:
                    unexpected_rows.append(f"settings={count} (not just the seeded default)")
            elif table != "_cf_KV" and count:
                unexpected_rows.append(f"{table}={count}")
        if unexpected_rows:
            raise ValueError(
                "D1 is not an empty migration target; refusing to overwrite existing records: "
                + ", ".join(unexpected_rows)
            )
        print("D1 TARGET SCHEMA COMPATIBILITY: PASS")
        print("D1 TARGET DATA STATE: EMPTY (only the seeded working_weekdays setting is permitted)")
    finally:
        if target is not None:
            target.close()
        target_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--d1-export", required=True, type=Path)
    parser.add_argument("--encrypted-d1-backup", required=True, type=Path)
    args = parser.parse_args()

    secret = os.environ.get("DB_SYNC_ENCRYPTION_SECRET", "").strip()
    if not secret:
        raise SystemExit("DB_SYNC_ENCRYPTION_SECRET is missing from the protected Actions environment.")

    database_bytes = decrypt_snapshot(args.source, secret)
    with tempfile.NamedTemporaryFile(prefix="rsc_source_", suffix=".db", delete=False) as handle:
        source_path = Path(handle.name)
        handle.write(database_bytes)
    source = None
    try:
        source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
        validate_source(source)
        validate_target(source, args.d1_export)
    finally:
        if source is not None:
            source.close()
        source_path.unlink(missing_ok=True)

    args.encrypted_d1_backup.parent.mkdir(parents=True, exist_ok=True)
    args.encrypted_d1_backup.write_bytes(encrypt_bytes(args.d1_export.read_bytes(), secret))
    print("D1 PRE-MIGRATION EXPORT: encrypted successfully for separate backup storage.")
    print("NO CUSTOMER DATA WAS IMPORTED OR MODIFIED.")


if __name__ == "__main__":
    main()
