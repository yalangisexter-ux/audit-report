import sqlite3
import app

def create_legacy_database(db_path, legacy_column, employee_name):
    conn = sqlite3.connect(db_path)
    conn.execute(
        f"CREATE TABLE employees "
        f"(id INTEGER PRIMARY KEY, {legacy_column} TEXT)"
    )
    conn.execute(
        f"INSERT INTO employees (id, {legacy_column}) VALUES (?, ?)",
        (1, employee_name),
    )
    conn.commit()
    conn.close()

def test_database_setup_preserves_legacy_employee_name(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_employee_name.sqlite3"
    create_legacy_database(db_path, "employee_name", "Test Employee")
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        result = database.conn.execute(
            "SELECT name FROM employees WHERE id = 1"
        ).fetchone()
        assert result["name"] == "Test Employee"
    finally:
        database.conn.close()

def test_database_setup_preserves_legacy_full_name(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_full_name.sqlite3"
    create_legacy_database(db_path, "full_name", "Test Employee")
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        result = database.conn.execute(
            "SELECT name FROM employees WHERE id = 1"
        ).fetchone()
        assert result["name"] == "Test Employee"
    finally:
        database.conn.close()
