"""Basic migration smoke tests that exercise real Database.setup()."""
import sqlite3
import app

def test_fresh_database_creates_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        tables = {r["name"] for r in database.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "employees" in tables
        assert "tasks" in tables
        assert "attendance" in tables
    finally:
        database.conn.close()

def test_legacy_employee_name_migrated(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE employees(id INTEGER PRIMARY KEY, employee_name TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Legacy Name')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        row = database.conn.execute("SELECT name FROM employees WHERE id=1").fetchone()
        assert row["name"] == "Legacy Name"
    finally:
        database.conn.close()
