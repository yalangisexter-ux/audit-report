"""Credential-preserving provisioning for the two explicitly configured web admins.

Passwords are supplied only through deployment environment secrets. They are never
stored in source control or logged. Existing account IDs and unrelated accounts remain
untouched; the two named accounts receive the requested roles and credentials.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path


def ensure_admin_accounts(db_path, customer_password: str, developer_password: str) -> int:
    """Ensure exact-case Admin and admin accounts exist with supplied credentials."""
    if not customer_password or not developer_password:
        raise RuntimeError("Both web administrator password secrets must be configured")

    import app as desktop_app
    import web_db_migrations

    path = Path(db_path)
    if not path.is_file():
        raise RuntimeError(f"Authentication database does not exist: {path}")

    # The desktop DB may use NOCASE uniqueness. Convert only the web DB copy while
    # preserving every existing row and credential before inserting case-distinct names.
    web_db_migrations.ensure_case_sensitive_auth_users(path)

    conn = sqlite3.connect(str(path), timeout=30)
    try:
        conn.row_factory = sqlite3.Row
        columns = {row[1] for row in conn.execute("PRAGMA table_info(auth_users)")}
        required = {
            "id", "username", "display_name", "role", "password_salt",
            "password_hash", "active", "created_at", "updated_at",
        }
        if not required.issubset(columns):
            raise RuntimeError("auth_users schema is incomplete; refusing to modify accounts")

        now = desktop_app.now_text()
        desired = (
            ("Admin", "Customer Administrator", "Admin", customer_password),
            ("admin", "Developer Administrator", "Developer", developer_password),
        )
        for username, display_name, role, password in desired:
            salt, digest = desktop_app.hash_pin(password)
            existing = conn.execute(
                """SELECT id, password_salt, password_hash, role, display_name, active
                   FROM auth_users WHERE username = ? COLLATE BINARY""",
                (username,),
            ).fetchone()
            if existing:
                # Do not rotate salts/hashes on every status poll once the requested
                # credential is already valid. Preserve the stable account ID.
                stored_salt = existing["password_salt"] or ""
                stored_hash = existing["password_hash"] or ""
                try:
                    _, verified_hash = desktop_app.hash_pin(password, stored_salt)
                    password_matches = bool(stored_salt and secrets.compare_digest(
                        str(verified_hash), str(stored_hash)
                    ))
                except Exception:
                    password_matches = False
                if password_matches:
                    salt, digest = stored_salt, stored_hash
                conn.execute(
                    """UPDATE auth_users SET display_name=?, role=?, password_salt=?,
                       password_hash=?, active=1, updated_at=? WHERE id=?""",
                    (display_name, role, salt, digest, now, existing["id"]),
                )
            else:
                # Older schemas may have optional security-answer fields.
                values = {
                    "username": username, "display_name": display_name, "role": role,
                    "password_salt": salt, "password_hash": digest, "active": 1,
                    "created_at": now, "updated_at": now,
                    "security_question": "", "answer_salt": "", "answer_hash": "",
                }
                insert_columns = [name for name in values if name in columns]
                conn.execute(
                    "INSERT INTO auth_users (" + ",".join(insert_columns) + ") VALUES (" +
                    ",".join("?" for _ in insert_columns) + ")",
                    tuple(values[name] for name in insert_columns),
                )
        conn.commit()
        count = conn.execute(
            """SELECT COUNT(*) FROM auth_users
               WHERE active=1 AND username IN ('Admin','admin') COLLATE BINARY"""
        ).fetchone()[0]
        if count != 2:
            raise RuntimeError("Both exact-case administrator accounts were not verified")
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_admin_login_heal() -> None:
    try:
        import web_auth_shim as shim
        import app as desktop_app
    except Exception as exc:
        print(f"[Auth] Safe auth adapter could not load: {exc}")
        return

    def ensure(db_path) -> None:
        customer_password = os.environ.get("WEB_CUSTOMER_ADMIN_PASSWORD", "")
        developer_password = os.environ.get("WEB_DEVELOPER_ADMIN_PASSWORD", "")
        if not customer_password or not developer_password:
            print("[Auth] Admin provisioning skipped: both deployment password secrets are required")
            return
        try:
            count = ensure_admin_accounts(db_path, customer_password, developer_password)
            print(f"[Auth] Verified {count} exact-case administrator accounts")
        except Exception as exc:
            print(f"[Auth] Administrator provisioning failed safely: {exc}")
            raise

    def find(conn, username: str, password: str):
        row = conn.execute(
            "SELECT * FROM auth_users WHERE username = ? COLLATE BINARY AND active = 1",
            (username,),
        ).fetchone()
        if row is None:
            candidates = conn.execute(
                "SELECT * FROM auth_users WHERE username = ? COLLATE NOCASE AND active = 1",
                (username,),
            ).fetchall()
            row = candidates[0] if len(candidates) == 1 else None
        if not row:
            return None
        salt, stored = row["password_salt"], row["password_hash"]
        if not salt or not stored:
            return None
        try:
            _, digest = desktop_app.hash_pin(password, salt)
            return row if secrets.compare_digest(str(digest), str(stored)) else None
        except Exception as exc:
            print(f"[Auth] Password verification failed safely: {exc}")
            return None

    shim._ensure_bootstrap_admin = ensure
    shim._find_active_login_user = find
    print("[Auth] Credential-preserving dual-admin provisioning installed")


apply_admin_login_heal()
