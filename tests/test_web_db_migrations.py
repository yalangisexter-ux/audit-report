import sqlite3

from web_db_migrations import ensure_case_sensitive_auth_users


def test_web_auth_migration_preserves_rows_and_allows_case_distinct_names(tmp_path):
    path = tmp_path / "web.db"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE auth_users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
            password_salt TEXT NOT NULL, password_hash TEXT NOT NULL,
            security_question TEXT NOT NULL, answer_salt TEXT NOT NULL,
            answer_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        INSERT INTO auth_users VALUES
        (1,'admin','Developer','Developer','salt1','hash1','','','','1','now','now');
    """)
    db.commit()
    db.close()

    assert ensure_case_sensitive_auth_users(path) is True
    db = sqlite3.connect(path)
    try:
        db.execute(
            "INSERT INTO auth_users VALUES(2,'Admin','Customer','Admin','salt2','hash2','','','','1','now','now')"
        )
        rows = db.execute("SELECT username, password_hash FROM auth_users ORDER BY id").fetchall()
        assert rows == [('admin', 'hash1'), ('Admin', 'hash2')]
    finally:
        db.close()


def test_web_auth_migration_is_idempotent(tmp_path):
    path = tmp_path / "web.db"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE auth_users(
            id INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE BINARY UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
            password_salt TEXT NOT NULL, password_hash TEXT NOT NULL,
            security_question TEXT NOT NULL, answer_salt TEXT NOT NULL,
            answer_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
    """)
    db.commit()
    db.close()
    assert ensure_case_sensitive_auth_users(path) is False
