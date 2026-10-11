import sqlite3
import app

def create_connection():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn

def test_task_link_is_restored_by_production_migration():
    conn = create_connection()
    conn.execute(
        "CREATE TABLE employees ("
        "id INTEGER PRIMARY KEY, "
        "name TEXT, "
        "employee_code TEXT)"
    )
    conn.execute("INSERT INTO employees VALUES (1, 'Alice', 'A1')")
    conn.execute(
        "CREATE TABLE tasks ("
        "id INTEGER PRIMARY KEY, "
        "title TEXT, "
        "employee_name TEXT)"
    )
    conn.execute("INSERT INTO tasks VALUES (10, 'Do work', 'Alice')")
    app.migrate_legacy_task_employee_links(conn)
    result = conn.execute("SELECT employee_id FROM tasks WHERE id = 10").fetchone()
    assert result["employee_id"] == 1
    conn.close()

def test_ambiguous_employee_names_are_not_linked():
    conn = create_connection()
    conn.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT)")
    conn.executemany("INSERT INTO employees VALUES (?, ?)", [(1, "Bob"), (2, "Bob")])
    conn.execute(
        "CREATE TABLE tasks ("
        "id INTEGER PRIMARY KEY, "
        "title TEXT, "
        "employee_name TEXT)"
    )
    conn.execute("INSERT INTO tasks VALUES (20, 'Ambiguous task', 'Bob')")
    app.migrate_legacy_task_employee_links(conn)
    result = conn.execute("SELECT employee_id FROM tasks WHERE id = 20").fetchone()
    assert result["employee_id"] is None
    conn.close()

def test_employee_code_is_used_when_names_are_ambiguous():
    conn = create_connection()
    conn.execute(
        "CREATE TABLE employees ("
        "id INTEGER PRIMARY KEY, "
        "name TEXT, "
        "employee_code TEXT)"
    )
    conn.executemany(
        "INSERT INTO employees VALUES (?, ?, ?)",
        [(1, "Alice", "A1"), (2, "Alice", "A2")],
    )
    conn.execute(
        "CREATE TABLE tasks ("
        "id INTEGER PRIMARY KEY, "
        "title TEXT, "
        "employee_name TEXT, "
        "employee_code TEXT)"
    )
    conn.execute("INSERT INTO tasks VALUES (30, 'Code match', 'Alice', 'A2')")
    app.migrate_legacy_task_employee_links(conn)
    result = conn.execute("SELECT employee_id FROM tasks WHERE id = 30").fetchone()
    assert result["employee_id"] == 2
    conn.close()

def test_existing_valid_employee_link_is_preserved():
    conn = create_connection()
    conn.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Alice')")
    conn.execute("INSERT INTO employees VALUES (2, 'Bob')")
    conn.execute(
        "CREATE TABLE tasks ("
        "id INTEGER PRIMARY KEY, "
        "title TEXT, "
        "employee_id INTEGER, "
        "employee_name TEXT)"
    )
    conn.execute("INSERT INTO tasks VALUES (40, 'Existing task', 2, 'Alice')")
    app.migrate_legacy_task_employee_links(conn)
    result = conn.execute("SELECT employee_id FROM tasks WHERE id = 40").fetchone()
    assert result["employee_id"] == 2
    conn.close()

def test_migration_adds_missing_employee_id_column():
    conn = create_connection()
    conn.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Alice')")
    conn.execute(
        "CREATE TABLE tasks ("
        "id INTEGER PRIMARY KEY, "
        "title TEXT, "
        "employee_name TEXT)"
    )
    conn.execute("INSERT INTO tasks VALUES (50, 'Legacy task', 'Alice')")
    app.migrate_legacy_task_employee_links(conn)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
    result = conn.execute("SELECT employee_id FROM tasks WHERE id = 50").fetchone()
    assert "employee_id" in columns
    assert result["employee_id"] == 1
    conn.close()
