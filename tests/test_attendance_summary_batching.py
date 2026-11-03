"""Regression tests for batched attendance-summary database access."""
from datetime import date, datetime
from types import SimpleNamespace

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QDateEdit, QTableWidget

import app


def test_attendance_summary_batches_employee_and_holiday_queries(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "attendance-summary.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    try:
        today = date.today()
        today_text = today.isoformat()
        yesterday_text = date.fromordinal(max(1, today.toordinal() - 1)).isoformat()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.set_setting("working_weekdays", "0,1,2,3,4,5,6")
        first_id = db.conn.execute(
            "INSERT INTO employees(name,joining_date,active,created_at) VALUES(?,?,?,?)",
            ("Joined Employee", today_text, 1, timestamp),
        ).lastrowid
        second_id = db.conn.execute(
            "INSERT INTO employees(name,joining_date,active,created_at) VALUES(?,?,?,?)",
            ("Tracked Employee", "", 1, timestamp),
        ).lastrowid
        db.conn.execute(
            "INSERT INTO tasks(employee_id,task_date,title,status,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?)",
            (second_id, yesterday_text, "Earlier task", "In progress", timestamp, timestamp),
        )
        db.conn.execute(
            "INSERT INTO attendance(employee_id,work_date,check_in,attendance_status,updated_at) "
            "VALUES(?,?,?,?,?)",
            (first_id, today_text, "09:00", "Present", timestamp),
        )
        db.conn.execute(
            "INSERT INTO attendance(employee_id,work_date,check_in,attendance_status,updated_at) "
            "VALUES(?,?,?,?,?)",
            (second_id, today_text, "09:15", "Present", timestamp),
        )
        db.conn.commit()

        date_edit = QDateEdit()
        date_edit.setDate(QDate(today.year, today.month, today.day))
        table = QTableWidget(0, 8)
        fake_window = SimpleNamespace(
            attendance_summary_table=table, att_date=date_edit, db=db
        )
        statements = []
        db.conn.set_trace_callback(statements.append)
        app.MainWindow.refresh_attendance_summary(fake_window)
        db.conn.set_trace_callback(None)

        assert table.rowCount() == 2
        assert table.item(0, 0).text() == "Joined Employee"
        assert table.item(0, 3).text() == "1"
        assert table.item(1, 0).text() == "Tracked Employee"
        assert table.item(1, 1).text() == yesterday_text
        assert sum("FROM holidays WHERE holiday_date BETWEEN" in sql for sql in statements) == 1
        assert sum("FROM attendance WHERE employee_id IN" in sql for sql in statements) == 1
        assert sum("MIN(work_day)" in sql for sql in statements) == 1
    finally:
        db.conn.close()
