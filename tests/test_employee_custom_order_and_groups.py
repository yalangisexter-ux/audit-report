import os, sqlite3, pytest
from pathlib import Path
import app

@pytest.fixture
def qapp():
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    if app.QApplication.instance() is None:
        return app.QApplication([])
    return app.QApplication.instance()

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_employee_audit.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    db = app.Database()
    yield db
    try:
        db.conn.close()
    except Exception:
        pass

def test_database_display_order_and_groups_migration(temp_db):
    cols = {r["name"] for r in temp_db.conn.execute("PRAGMA table_info(employees)").fetchall()}
    assert "display_order" in cols
    
    group_tables = temp_db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='employee_groups'"
    ).fetchall()
    assert len(group_tables) == 1

def test_employee_groups_crud(temp_db):
    # Add groups
    assert temp_db.add_employee_group("Technical") is True
    assert temp_db.add_employee_group("House Keeping") is True
    assert temp_db.add_employee_group("Sales") is True
    # Duplicate returns False
    assert temp_db.add_employee_group("Technical") is False

    groups = temp_db.employee_groups()
    names = [g["name"] for g in groups]
    assert "Technical" in names
    assert "House Keeping" in names
    assert "Sales" in names

    # Add employee in House Keeping
    temp_db.conn.execute(
        "INSERT INTO employees(employee_code, name, department, created_at) VALUES('E01', 'John Cleaner', 'House Keeping', ?)",
        (app.now_text(),)
    )
    temp_db.conn.commit()

    # Rename group
    assert temp_db.rename_employee_group("House Keeping", "Housekeeping") is True
    groups = temp_db.employee_groups()
    names = [g["name"] for g in groups]
    assert "Housekeeping" in names
    assert "House Keeping" not in names

    # Employee department should be updated
    emp = temp_db.conn.execute("SELECT * FROM employees WHERE employee_code='E01'").fetchone()
    assert emp["department"] == "Housekeeping"

    # Reorder groups
    temp_db.reorder_employee_groups(["Sales", "Technical", "Housekeeping"])
    reordered = temp_db.employee_groups()
    reordered_names = [g["name"] for g in reordered]
    assert reordered_names == ["Sales", "Technical", "Housekeeping"]

    # Delete group
    assert temp_db.delete_employee_group("Housekeeping") is True
    emp_after_del = temp_db.conn.execute("SELECT * FROM employees WHERE employee_code='E01'").fetchone()
    assert emp_after_del["department"] == ""

def test_employee_custom_order_persistence(temp_db):
    # Add employees
    now = app.now_text()
    temp_db.conn.execute("INSERT INTO employees(employee_code, name, department, display_order, created_at) VALUES('E1', 'Charlie', 'General', 0, ?)", (now,))
    temp_db.conn.execute("INSERT INTO employees(employee_code, name, department, display_order, created_at) VALUES('E2', 'Alice', 'General', 0, ?)", (now,))
    temp_db.conn.execute("INSERT INTO employees(employee_code, name, department, display_order, created_at) VALUES('E3', 'Bob', 'General', 0, ?)", (now,))
    temp_db.conn.commit()

    # When all display_order are 0, secondary sort is name
    emps_init = temp_db.employees()
    assert [e["name"] for e in emps_init] == ["Alice", "Bob", "Charlie"]

    # Custom reorder: Bob first, then Charlie, then Alice
    e_map = {e["name"]: e["id"] for e in emps_init}
    temp_db.update_employees_order([
        (e_map["Bob"], 10, "General"),
        (e_map["Charlie"], 20, "General"),
        (e_map["Alice"], 30, "General"),
    ])

    emps_ordered = temp_db.employees()
    assert [e["name"] for e in emps_ordered] == ["Bob", "Charlie", "Alice"]

    # Tasks and attendance also reflect custom display order
    temp_db.conn.execute(
        "INSERT INTO tasks(employee_id, task_date, title, created_at) VALUES(?, '2026-10-24', 'Task 1', ?)",
        (e_map["Alice"], now)
    )
    temp_db.conn.execute(
        "INSERT INTO tasks(employee_id, task_date, title, created_at) VALUES(?, '2026-10-24', 'Task 2', ?)",
        (e_map["Bob"], now)
    )
    temp_db.conn.commit()

    tasks = temp_db.tasks('2026-10-24')
    # Bob (order 10) must appear before Alice (order 30)
    assert tasks[0]["employee_name"] == "Bob"
    assert tasks[1]["employee_name"] == "Alice"

    # Attendance also follows custom display order
    temp_db.conn.execute("INSERT INTO attendance(employee_id, work_date, check_in, updated_at) VALUES(?, '2026-10-24', '09:00', ?)", (e_map["Alice"], now))
    temp_db.conn.execute("INSERT INTO attendance(employee_id, work_date, check_in, updated_at) VALUES(?, '2026-10-24', '09:00', ?)", (e_map["Bob"], now))
    temp_db.conn.commit()

    att = temp_db.attendance('2026-10-24')
    assert att[0]["employee_name"] == "Bob"
    assert att[1]["employee_name"] == "Alice"


def test_employee_table_section_header_selected_id(temp_db, qapp):
    from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
    from PySide6.QtCore import Qt

    # Test selected_id helper logic
    table = app.EmployeeTableWidget(2, 8)
    
    # Row 0: Section header
    hdr = QTableWidgetItem("   📁  TECHNICAL   (1 employee)")
    hdr.setData(Qt.ItemDataRole.UserRole, "__section_header__")
    table.setItem(0, 0, hdr)

    # Row 1: Employee
    emp_item = QTableWidgetItem("42")
    emp_item.setData(Qt.ItemDataRole.UserRole, 42)
    table.setItem(1, 0, emp_item)

    # Fake window with selected_id method
    class DummyWindow:
        selected_id = app.MainWindow.selected_id

    win = DummyWindow()
    table.selectRow(0)
    assert win.selected_id(table) is None

    table.selectRow(1)
    assert win.selected_id(table) == 42


def test_handle_employee_dropped_reorders_and_moves_group(temp_db, qapp):
    now = app.now_text()
    temp_db.add_employee_group("Technical")
    temp_db.add_employee_group("Housekeeping")

    # Add employees in groups
    temp_db.conn.execute("INSERT INTO employees(employee_code, name, department, display_order, created_at) VALUES('E1', 'Tech Lead', 'Technical', 10, ?)", (now,))
    temp_db.conn.execute("INSERT INTO employees(employee_code, name, department, display_order, created_at) VALUES('E2', 'Tech Junior', 'Technical', 20, ?)", (now,))
    temp_db.conn.execute("INSERT INTO employees(employee_code, name, department, display_order, created_at) VALUES('E3', 'Cleaner', 'Housekeeping', 10, ?)", (now,))
    temp_db.conn.commit()

    # Create dummy window with database and permissions
    class DummyMainWindow:
        def __init__(self, db):
            self.db = db
            self.is_admin_or_dev = True
            self.emp_table = app.EmployeeTableWidget(0, 8, self)
            self.emp_search = app.QLineEdit()
            self.refreshed = False
        handle_employee_dropped = app.MainWindow.handle_employee_dropped
        refresh_employees = app.MainWindow.refresh_employees
        set_row_items = app.MainWindow.set_row_items
        status_item = app.MainWindow.status_item
        current_theme = lambda self: "night"
        refresh_task_filter = lambda self: None
        refresh_report_employees = lambda self: None
        refresh_all = lambda self: None
        selected_id = app.MainWindow.selected_id

    win = DummyMainWindow(temp_db)
    win.refresh_employees()

    # Check rows: should have Technical header, 2 tech employees, Housekeeping header, 1 cleaner employee
    assert win.emp_table.rowCount() == 5  # 2 headers + 3 employees

    # Move Tech Junior (E2) into Housekeeping
    e2 = temp_db.conn.execute("SELECT id FROM employees WHERE employee_code='E2'").fetchone()["id"]
    # Target row is Housekeeping section header (row 3)
    win.handle_employee_dropped(e2, 2, 3)

    # Check database
    e2_updated = temp_db.conn.execute("SELECT * FROM employees WHERE id=?", (e2,)).fetchone()
    assert e2_updated["department"] == "Housekeeping"


def test_employees_sorted_by_serial_number_and_drag_drop_disabled(temp_db, qapp):
    table = app.EmployeeTableWidget()
    assert table.dragEnabled() is False
    assert table.acceptDrops() is False

    now = app.now_text()
    temp_db.conn.execute("DELETE FROM employees")
    temp_db.conn.execute("INSERT INTO employees(id, employee_code, name, department, created_at) VALUES(1, 'E01', 'Zoe Senior', 'General', ?)", (now,))
    temp_db.conn.execute("INSERT INTO employees(id, employee_code, name, department, created_at) VALUES(2, 'E02', 'Adam Junior', 'General', ?)", (now,))
    temp_db.conn.execute("INSERT INTO employees(id, employee_code, name, department, created_at) VALUES(3, 'E03', 'Ben Mid', 'General', ?)", (now,))
    temp_db.conn.commit()

    class DummyMainWindow:
        def __init__(self, db):
            self.db = db
            self.is_admin_or_dev = True
            self.emp_table = app.EmployeeTableWidget(0, 8, self)
            self.emp_search = app.QLineEdit()
        handle_employee_dropped = app.MainWindow.handle_employee_dropped
        refresh_employees = app.MainWindow.refresh_employees
        set_row_items = app.MainWindow.set_row_items
        status_item = app.MainWindow.status_item
        current_theme = lambda self: "night"
        refresh_task_filter = lambda self: None
        refresh_report_employees = lambda self: None
        refresh_all = lambda self: None
        selected_id = app.MainWindow.selected_id

    win = DummyMainWindow(temp_db)
    win.refresh_employees()

    # The rows under General header must be ordered by serial number (1, 2, 3), not alphabetical (Adam, Ben, Zoe)
    assert win.emp_table.rowCount() == 4  # 1 header + 3 employees
    assert win.emp_table.item(1, 0).text() == "1"
    assert win.emp_table.item(1, 2).text() == "Zoe Senior"
    assert win.emp_table.item(2, 0).text() == "2"
    assert win.emp_table.item(2, 2).text() == "Adam Junior"
    assert win.emp_table.item(3, 0).text() == "3"
    assert win.emp_table.item(3, 2).text() == "Ben Mid"
