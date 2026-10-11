import sqlite3

def migrate_employee_names(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(employees)").fetchall()
    }
    if "name" not in columns:
        conn.execute("ALTER TABLE employees ADD COLUMN name TEXT NOT NULL DEFAULT ''")
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(employees)").fetchall()
    }
    if "employee_name" in columns:
        conn.execute("""
            UPDATE employees
            SET name = employee_name
            WHERE COALESCE(name, '') = ''
              AND COALESCE(employee_name, '') <> ''
        """)
    if "full_name" in columns:
        conn.execute("""
            UPDATE employees
            SET name = full_name
            WHERE COALESCE(name, '') = ''
              AND COALESCE(full_name, '') <> ''
        """)

def test_legacy_employee_name_is_preserved():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            employee_name TEXT
        )
    """)
    conn.execute("INSERT INTO employees VALUES (?, ?)", (1, "Test Employee"))
    migrate_employee_names(conn)
    result = conn.execute("SELECT name FROM employees WHERE id = 1").fetchone()
    assert result["name"] == "Test Employee"
    conn.close()

def test_legacy_full_name_is_preserved():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            full_name TEXT
        )
    """)
    conn.execute("INSERT INTO employees VALUES (?, ?)", (1, "Test Employee"))
    migrate_employee_names(conn)
    result = conn.execute("SELECT name FROM employees WHERE id = 1").fetchone()
    assert result["name"] == "Test Employee"
    conn.close()
