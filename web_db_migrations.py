"""Web-only SQLite compatibility migrations.

These migrations apply only to the Render database copy. The Windows desktop
application and its on-disk database schema are not modified.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def ensure_case_sensitive_auth_users(db_path: str | Path) -> bool:
    """Rebuild auth_users with BINARY username uniqueness while preserving every row.

    The desktop schema historically used NOCASE UNIQUE, which prevents the web
    client from retaining distinct legacy usernames such as "admin" and "Admin".
    The web copy needs exact username matching to preserve both credentials.
    """
    path = Path(db_path)
    if not path.is_file():
        return False
    conn = sqlite3.connect(str(path), timeout=30)
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_users'"
        ).fetchone()
        if not row or not row[0]:
            return False
        sql = str(row[0]).upper()
        if "COLLATE NOCASE" not in sql:
            return False
        columns = [r[1] for r in conn.execute("PRAGMA table_info(auth_users)")]
        required = [
            "id", "username", "display_name", "role", "password_salt",
            "password_hash", "security_question", "answer_salt", "answer_hash",
            "active", "created_at", "updated_at",
        ]
        if not all(name in columns for name in required):
            raise RuntimeError("auth_users schema is not recognized; web migration stopped without changing data")
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DROP TABLE IF EXISTS auth_users_web_migration")
        conn.execute("""
            CREATE TABLE auth_users_web_migration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE BINARY UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                security_question TEXT NOT NULL,
                answer_salt TEXT NOT NULL,
                answer_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO auth_users_web_migration (" + ",".join(required) + ") "
            "SELECT " + ",".join(required) + " FROM auth_users ORDER BY id"
        )
        conn.execute("DROP TABLE auth_users")
        conn.execute("ALTER TABLE auth_users_web_migration RENAME TO auth_users")
        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
