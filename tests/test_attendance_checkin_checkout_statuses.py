from datetime import date, datetime

import app


def make_attendance_window(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = app.QApplication.instance() or app.QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "attendance.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    today = date.today().isoformat()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.set_setting("working_weekdays", "0,1,2,3,4,5,6")
    cursor = db.conn.execute(
        "INSERT INTO employees(employee_code,name,joining_date,active,created_at) VALUES(?,?,?,?,?)",
        ("EMP-ATT", "Attendance Check", today, 1, timestamp),
    )
    db.conn.commit()
    window = app.MainWindow(db, {"username": "Preview", "role": "Admin"})
    window.att_date.setDate(app.QDate.currentDate())
    window.refresh_attendance()
    window.att_table.selectRow(0)
    return qt_app, db, window, cursor.lastrowid, today


def test_inline_checkout_saves_visible_unsaved_checkin(monkeypatch, tmp_path):
    qt_app, db, window, employee_id, today = make_attendance_window(monkeypatch, tmp_path)
    try:
        check_in_cell = window.att_table.cellWidget(0, 3)
        check_out_cell = window.att_table.cellWidget(0, 4)
        check_in_editor = check_in_cell.findChild(app.QLineEdit)
        check_out_editor = check_out_cell.findChild(app.QLineEdit)
        check_in_editor.setText("09:55")
        check_out_editor.setText("18:00")

        window.save_attendance_inline(employee_id, today, "check_out", "18:00")

        saved = db.conn.execute(
            "SELECT check_in, check_out, attendance_status FROM attendance WHERE employee_id=? AND work_date=?",
            (employee_id, today),
        ).fetchone()
        assert tuple(saved) == ("09:55", "18:00", "Present")
        assert window.att_table.item(0, 5).text() == "8.08"
        qt_app.processEvents()
    finally:
        window.close()
        db.conn.close()


def test_toolbar_checkout_uses_visible_checkin_and_extended_statuses(monkeypatch, tmp_path):
    qt_app, db, window, employee_id, today = make_attendance_window(monkeypatch, tmp_path)
    try:
        check_in_editor = window.att_table.cellWidget(0, 3).findChild(app.QLineEdit)
        check_in_editor.setText("09:55")
        monkeypatch.setattr(app.QInputDialog, "getText", lambda *args, **kwargs: ("18:00", True))

        window.check_out()

        # Status combo only contains attendance statuses: Present, Absent, Leave, Unmarked
        status_cell = window.att_table.cellWidget(0, 2)
        status_combo = status_cell.findChild(app.QComboBox)
        for opt in ("Present", "Absent", "Leave", "Unmarked"):
            assert status_combo.findText(opt) >= 0
        # Dedicated remarks combo contains presets: Late Check-in, Late Check-out, Overtime, etc.
        remarks_cell = window.att_table.cellWidget(0, 6)
        remarks_combo = remarks_cell.findChild(app.QComboBox)
        assert all(remarks_combo.findText(option) >= 0 for option in app.ATTENDANCE_DETAIL_STATUSES)
        remarks_combo.setCurrentText("Overtime")
        window.save_attendance_inline(employee_id, today, "remarks", "Overtime")
        qt_app.processEvents()

        saved = db.conn.execute(
            "SELECT check_in, check_out, attendance_status, attendance_note FROM attendance WHERE employee_id=? AND work_date=?",
            (employee_id, today),
        ).fetchone()
        assert tuple(saved[:3]) == ("09:55", "18:00", "Present")
        assert saved[3] == "Overtime"
        assert app.is_present_attendance_status(saved["attendance_status"])
        assert window.employee_productivity(db.employee(employee_id), date.today())["present"] == 1
        assert window.attendance_summary_table.item(0, 3).text() == "1"
        assert window._attendance_report_rows(today)[0]["status"] == "Present"
        assert window._attendance_report_rows(today)[0]["note"] == "Overtime"
    finally:
        window.close()
        db.conn.close()


def test_attendance_select_all_keeps_multi_selection_after_table_polish(monkeypatch, tmp_path):
    qt_app, db, window, employee_id, today = make_attendance_window(monkeypatch, tmp_path)
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.conn.execute(
            "INSERT INTO employees(employee_code,name,joining_date,active,created_at) VALUES(?,?,?,?,?)",
            ("EMP-ATT-2", "Second Attendance Check", today, 1, timestamp),
        )
        db.conn.commit()
        window.refresh_attendance()

        assert window.att_table.selectionMode() == app.QAbstractItemView.ExtendedSelection
        assert window.task_table.selectionMode() == app.QAbstractItemView.ExtendedSelection
        window.att_table.selectAll()
        assert len(window.att_table.selectionModel().selectedRows()) == 2
        qt_app.processEvents()
    finally:
        window.close()
        db.conn.close()
