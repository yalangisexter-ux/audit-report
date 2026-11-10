"""Regression for quoted IF NOT EXISTS legacy auth_users schemas.

This schema form was present in customer databases from older installers and
must migrate without raising the startup popup about preparing the case-sensitive
migration. Existing account IDs and password hashes must remain unchanged.
"""
import sqlite3

import app


def test_auth_migration_handles_if_not_exists_quoted_table_and_preserves_credentials(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "legacy_if_not_exists_quoted_auth.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS "auth_users" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            security_question TEXT NOT NULL DEFAULT '',
            answer_salt TEXT NOT NULL DEFAULT '',
            answer_hash TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        '''
    )
    conn.execute(
        '''
        INSERT INTO auth_users (
            id, username, display_name, role, password_salt, password_hash,
            security_question, answer_salt, answer_hash, active, created_at, updated_at
        ) VALUES (901, 'Admin', 'Customer Administrator', 'Admin',
                  'existing-salt', 'existing-password-hash',
                  'existing-question', 'existing-answer-salt',
                  'existing-answer-hash', 1, 'created', 'updated')
        '''
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    database = app.Database()
    try:
        customer = database.conn.execute(
            "SELECT id, username, role, password_salt, password_hash, "
            "security_question, answer_salt, answer_hash "
            "FROM auth_users WHERE username=? COLLATE BINARY",
            ("Admin",),
        ).fetchone()
        assert customer is not None
        assert customer["id"] == 901
        assert customer["username"] == "Admin"
        assert customer["role"] == "Admin"
        assert customer["password_salt"] == "existing-salt"
        assert customer["password_hash"] == "existing-password-hash"
        assert customer["security_question"] == "existing-question"
        assert customer["answer_salt"] == "existing-answer-salt"
        assert customer["answer_hash"] == "existing-answer-hash"

        developer = database.conn.execute(
            "SELECT username, role FROM auth_users "
            "WHERE username=? COLLATE BINARY",
            ("admin",),
        ).fetchone()
        assert developer is not None
        assert developer["username"] == "admin"
        assert developer["role"] == "Developer"

        schema = database.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_users'"
        ).fetchone()[0]
        assert "COLLATE BINARY" in schema.upper()
        assert "COLLATE NOCASE" not in schema.upper()
        assert database.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        database.conn.close()
