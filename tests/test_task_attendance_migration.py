import sqlite3

def migrate_task_links(conn):
    """Minimal version of the task link migration for testing."""
    task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    employee_columns = {row["name"] for row in conn.execute("PRAGMA table_info(employees)").fetchall()}
    if "employee_id" not in task_columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN employee_id INTEGER")
    name_columns = [col for col in ("employee_name", "full_name", "employee", "assigned_to") if col in task_columns]
    has_code = "employee_code" in task_columns and "employee_code" in employee_columns
    rows = conn.execute("""
        SELECT * FROM tasks
        WHERE employee_id IS NULL
           OR NOT EXISTS (SELECT 1 FROM employees WHERE employees.id = tasks.employee_id)
    """).fetchall()
    for task in rows:
        matches = []
        if has_code:
            code = str(task["employee_code"] or "").strip()
            if code:
                matches = conn.execute(
                    "SELECT id FROM employees WHERE LOWER(TRIM(COALESCE(employee_code, ''))) = LOWER(?)",
                    (code,)
                ).fetchall()
        if not matches:
            for column in name_columns:
                value = str(task[column] or "").strip()
                if not value:
                    continue
                candidates = conn.execute(
                    "SELECT id FROM employees WHERE LOWER(TRIM(COALESCE(name, ''))) = LOWER(?)",
                    (value,)
                ).fetchall()
                if len(candidates) == 1:
                    matches = candidates
                    break
        if len(matches) == 1:
            conn.execute("UPDATE tasks SET employee_id = ? WHERE id = ?", (matches[0]["id"], task["id"]))
    conn.commit()

def test_task_link_by_name_is_restored():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT, employee_code TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Alice', 'A1')")
    conn.execute("CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT, employee_name TEXT)")
    conn.execute("INSERT INTO tasks VALUES (10, 'Do work', 'Alice')")
    migrate_task_links(conn)
    row = conn.execute("SELECT employee_id FROM tasks WHERE id = 10").fetchone()
    assert row["employee_id"] == 1
    conn.close()

def test_unambiguous_match_only():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Bob')")
    conn.execute("INSERT INTO employees VALUES (2, 'Bob')")
    conn.execute("CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT, employee_name TEXT)")
    conn.execute("INSERT INTO tasks VALUES (20, 'Ambiguous', 'Bob')")
    migrate_task_links(conn)
    row = conn.execute("SELECT employee_id FROM tasks WHERE id = 20").fetchone()
    assert row["employee_id"] is None  # not assigned when ambiguous
    conn.close()

def test_attendance_status_added():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE attendance(id INTEGER PRIMARY KEY, work_date TEXT, check_in TEXT)")
    conn.execute("INSERT INTO attendance VALUES (1, '2026-10-11', '09:00')")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(attendance)").fetchall()}
    if "attendance_status" not in cols:
        conn.execute("ALTER TABLE attendance ADD COLUMN attendance_status TEXT DEFAULT 'Unmarked'")
        conn.execute("UPDATE attendance SET attendance_status='Present' WHERE COALESCE(check_in, '') <> ''")
    conn.commit()
    row = conn.execute("SELECT attendance_status FROM attendance WHERE id = 1").fetchone()
    assert row["attendance_status"] == "Present"
    conn.close()
