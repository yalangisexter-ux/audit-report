"""Tests for the Business Tracking module. Uses a disposable database."""
import sqlite3
import tempfile
import os

def test_business_tables_created_without_touching_employees():
    import business_tracking
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # Pre-existing employee
    conn.execute("CREATE TABLE employees(id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Existing Employee')")
    conn.commit()
    business_tracking.setup_business_tables(conn)
    # Employee still exists
    row = conn.execute("SELECT name FROM employees WHERE id=1").fetchone()
    assert row["name"] == "Existing Employee"
    # Business tables exist
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "bt_products" in tables
    assert "bt_orders" in tables
    assert "bt_activities" in tables
    conn.close()
    os.unlink(path)

def test_available_stock_calculation():
    import business_tracking
    class Row(dict):
        def __getitem__(self, k):
            return dict.__getitem__(self, k)
    p = Row(opening_stock=100, received_qty=50, reserved_qty=10, dispatched_qty=20,
            free_qty=5, returned_qty=3, damaged_qty=2, expired_qty=1, quarantined_qty=0)
    avail = business_tracking.available_stock(p)
    assert avail == 100 + 50 - 10 - 20 - 5 + 3 - 2 - 1 - 0
