"""Safe web authentication adapter.

Never rename users or reset existing desktop credentials during web startup.
An Admin account is created only when the database has no accounts and an
operator explicitly supplies WEB_BOOTSTRAP_ADMIN_PASSWORD.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path


def apply_admin_login_heal() -> None:
    try:
        import web_auth_shim as shim
        import app as desktop_app
    except Exception as exc:
        print(f"[Auth] Safe auth adapter could not load: {exc}")
        return

    def ensure(db_path) -> None:
        password = (os.environ.get("WEB_BOOTSTRAP_ADMIN_PASSWORD") or "").strip()
        if not password:
            return
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=30)
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS auth_users (
                    id INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE BINARY,
                    display_name TEXT, role TEXT, password_salt TEXT, password_hash TEXT,
                    security_question TEXT, answer_salt TEXT, answer_hash TEXT,
                    active INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT
                )"""
            )
            count = conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
            if count:
                return
            salt, digest = desktop_app.hash_pin(password)
            now = desktop_app.now_text()
            conn.execute(
                """INSERT INTO auth_users(
                    username, display_name, role, password_salt, password_hash,
                    security_question, answer_salt, answer_hash, active, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
                ("Admin", "Administrator", "Admin", salt, digest, "", "", "", now, now),
            )
            conn.commit()
            print("[Auth] Created first Admin account from explicit bootstrap configuration")
        finally:
            conn.close()

    def find(conn, username: str, password: str):
        # Prefer exact casing; permit a case variant only when it identifies one account.
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
        salt = row["password_salt"]
        stored = row["password_hash"]
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
    print("[Auth] Credential-preserving login verification installed")


apply_admin_login_heal()
