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


def test_absent_status_is_committed_to_selected_working_date(monkeypatch, tmp_path):
    qt_app, db, window, employee_id, today = make_attendance_window(monkeypatch, tmp_path)
    try:
        db.upsert_attendance(employee_id, today, check_in="09:00", check_out="18:00", status="Present")
        window.set_attendance_status("Absent")
        saved = db.conn.execute(
            "SELECT work_date, attendance_status, check_in, check_out FROM attendance WHERE employee_id=? AND work_date=?",
            (employee_id, today),
        ).fetchone()
        assert tuple(saved) == (today, "Absent", "", "")
        window.refresh_attendance()
        qt_app.processEvents()
        assert window.att_table.cellWidget(0, 2).findChild(app.QComboBox).currentText() == "Absent"
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


def test_present_absent_leave_dropdown_updates_persist_and_refresh_monthly_summary(monkeypatch, tmp_path):
    import sqlite3

    qt_app, db, window, employee_id, today_text = make_attendance_window(monkeypatch, tmp_path)
    try:
        today = date.fromisoformat(today_text)
        month_start = today.replace(day=1)
        db.conn.execute(
            "UPDATE employees SET joining_date=? WHERE id=?",
            (month_start.isoformat(), employee_id),
        )
        weekdays = []
        current = month_start
        while current <= today:
            if current.weekday() in db.working_weekdays():
                weekdays.append(current.isoformat())
            current = date.fromordinal(current.toordinal() + 1)
        assert len(weekdays) >= 3

        # Drive the real QComboBox signal wired by refresh_attendance(), rather
        # than calling the persistence helper directly.
        for work_date, status in zip(weekdays[:3], ("Present", "Absent", "Leave")):
            work_day = date.fromisoformat(work_date)
            window.att_date.setDate(app.QDate(work_day.year, work_day.month, work_day.day))
            window.refresh_attendance()
            combo = window.att_table.cellWidget(0, 2).findChild(app.QComboBox)
            assert combo is not None
            combo.setCurrentText(status)
            qt_app.processEvents()
            saved = db.conn.execute(
                "SELECT attendance_status, check_in, check_out FROM attendance "
                "WHERE employee_id=? AND work_date=?",
                (employee_id, work_date),
            ).fetchone()
            assert saved is not None
            assert saved["attendance_status"] == status
            if status in ("Absent", "Leave"):
                assert saved["check_in"] == ""
                assert saved["check_out"] == ""

        # Re-check Present with times after the other two statuses were written.
        first_day = date.fromisoformat(weekdays[0])
        window.att_date.setDate(app.QDate(first_day.year, first_day.month, first_day.day))
        window.refresh_attendance()
        window.save_attendance_inline(employee_id, weekdays[0], "check_in", "09:00")
        window.save_attendance_inline(employee_id, weekdays[0], "check_out", "17:00")

        window.att_date.setDate(app.QDate(today.year, today.month, today.day))
        window.refresh_attendance_summary()
        qt_app.processEvents()

        summary = window.attendance_summary_table
        assert summary.rowCount() == 1
        assert int(summary.item(0, 3).text()) == 1  # Present
        assert int(summary.item(0, 4).text()) == 1  # Absent
        assert int(summary.item(0, 5).text()) == 1  # Leave
        assert int(summary.item(0, 7).text()) == 1  # Total present

        window.close()
        db.conn.close()
        reopened = sqlite3.connect(tmp_path / "attendance.db")
        try:
            saved = reopened.execute(
                "SELECT work_date, attendance_status, check_in, check_out "
                "FROM attendance WHERE employee_id=? ORDER BY work_date",
                (employee_id,),
            ).fetchall()
            assert saved == [
                (weekdays[0], "Present", "09:00", "17:00"),
                (weekdays[1], "Absent", "", ""),
                (weekdays[2], "Leave", "", ""),
            ]
        finally:
            reopened.close()
    finally:
        try:
            window.close()
        except Exception:
            pass
        try:
            db.conn.close()
        except Exception:
            pass


def test_changing_attendance_date_saves_each_status_to_the_selected_date(monkeypatch, tmp_path):
    import sqlite3

    qt_app, db, window, employee_id, today_text = make_attendance_window(monkeypatch, tmp_path)
    try:
        today = date.fromisoformat(today_text)
        selected_dates = [
            date.fromordinal(today.toordinal() - 3),
            date.fromordinal(today.toordinal() - 2),
            date.fromordinal(today.toordinal() - 1),
        ]
        statuses = ("Present", "Absent", "Leave")

        for selected_day, status in zip(selected_dates, statuses):
            qdate = app.QDate(selected_day.year, selected_day.month, selected_day.day)
            window.att_date.setDate(qdate)
            qt_app.processEvents()

            assert window.att_date.date().toString("yyyy-MM-dd") == selected_day.isoformat()
            assert window.att_table.item(0, 1).text() == selected_day.isoformat()

            status_cell = window.att_table.cellWidget(0, 2)
            status_combo = status_cell.findChild(app.QComboBox)
            assert status_combo is not None
            status_combo.setCurrentText(status)
            qt_app.processEvents()

            saved = db.conn.execute(
                "SELECT work_date, attendance_status FROM attendance "
                "WHERE employee_id=? AND work_date=?",
                (employee_id, selected_day.isoformat()),
            ).fetchone()
            assert saved is not None
            assert tuple(saved) == (selected_day.isoformat(), status)

        window.close()
        db.conn.close()
        reopened = sqlite3.connect(tmp_path / "attendance.db")
        try:
            records = reopened.execute(
                "SELECT work_date, attendance_status FROM attendance "
                "WHERE employee_id=? ORDER BY work_date",
                (employee_id,),
            ).fetchall()
            assert records == sorted(
                [(day.isoformat(), status) for day, status in zip(selected_dates, statuses)]
            )
        finally:
            reopened.close()
    finally:
        try:
            window.close()
        except Exception:
            pass
        try:
            db.conn.close()
        except Exception:
            pass


def test_legacy_required_date_and_status_columns_accept_new_attendance(monkeypatch, tmp_path):
    import sqlite3

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "legacy-attendance.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))

    # Reproduce customer DBs from releases that used NOT NULL date/status columns.
    legacy = sqlite3.connect(tmp_path / "legacy-attendance.db")
    legacy.execute("""
        CREATE TABLE attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            check_in TEXT NOT NULL DEFAULT '',
            check_out TEXT NOT NULL DEFAULT '',
            remarks TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
    """)
    legacy.commit()
    legacy.close()

    qt_app = app.QApplication.instance() or app.QApplication([])
    db = app.Database()
    window = None
    try:
        today = date.today()
        work_dates = []
        current = today.replace(day=1)
        while current <= today:
            if current.weekday() in db.working_weekdays():
                work_dates.append(current.isoformat())
            current = date.fromordinal(current.toordinal() + 1)
        assert len(work_dates) >= 3

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        employee_id = db.conn.execute(
            "INSERT INTO employees(name,joining_date,active,created_at) VALUES(?,?,?,?)",
            ("Legacy Attendance", today.replace(day=1).isoformat(), 1, timestamp),
        ).lastrowid

        db.upsert_attendance(employee_id, work_dates[0], status="Present")
        db.upsert_attendance(employee_id, work_dates[1], status="Absent")
        db.upsert_attendance(employee_id, work_dates[2], status="Leave")

        rows = db.conn.execute(
            "SELECT date, work_date, status, attendance_status "
            "FROM attendance WHERE employee_id=? ORDER BY work_date",
            (employee_id,),
        ).fetchall()
        assert [tuple(row) for row in rows] == [
            (work_dates[0], work_dates[0], "Present", "Present"),
            (work_dates[1], work_dates[1], "Absent", "Absent"),
            (work_dates[2], work_dates[2], "Leave", "Leave"),
        ]

        # Updating an existing row must keep both schema generations aligned.
        db.upsert_attendance(employee_id, work_dates[1], status="Present", check_in="09:00")
        updated = db.conn.execute(
            "SELECT date, work_date, status, attendance_status, check_in "
            "FROM attendance WHERE employee_id=? AND work_date=?",
            (employee_id, work_dates[1]),
        ).fetchone()
        assert tuple(updated) == (
            work_dates[1], work_dates[1], "Present", "Present", "09:00"
        )

        # The monthly UI summary must read those same legacy-backed rows.
        window = app.MainWindow(db, {"username": "Preview", "role": "Admin"})
        window.att_date.setDate(app.QDate(today.year, today.month, today.day))
        window.refresh_attendance_summary()
        qt_app.processEvents()
        summary = window.attendance_summary_table
        assert summary.rowCount() == 1
        assert int(summary.item(0, 3).text()) == 2
        assert int(summary.item(0, 4).text()) == 0
        assert int(summary.item(0, 5).text()) == 1
        assert int(summary.item(0, 7).text()) == 2
    finally:
        if window is not None:
            window.close()
        db.conn.close()


def test_bulk_attendance_transaction_uses_legacy_safe_schema_and_commits_once(monkeypatch, tmp_path):
    import sqlite3

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "legacy-bulk-attendance.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))

    legacy = sqlite3.connect(tmp_path / "legacy-bulk-attendance.db")
    legacy.execute("""
        CREATE TABLE attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            check_in TEXT NOT NULL DEFAULT '',
            check_out TEXT NOT NULL DEFAULT '',
            remarks TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
    """)
    legacy.commit()
    legacy.close()

    db = app.Database()
    try:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        employee_ids = [
            db.conn.execute(
                "INSERT INTO employees(name,joining_date,active,created_at) VALUES(?,?,?,?)",
                (f"Bulk Legacy {index}", date.today().isoformat(), 1, stamp),
            ).lastrowid
            for index in range(2)
        ]

        # Commit fixture employee creation before starting the attendance-only transaction.
        db.conn.commit()
        db.conn.execute("BEGIN")
        for employee_id, status in zip(employee_ids, ("Present", "Leave")):
            db.upsert_attendance(
                employee_id,
                date.today().isoformat(),
                status=status,
                commit=False,
            )
        assert db.conn.in_transaction
        db.conn.commit()
        assert not db.conn.in_transaction

        saved = db.conn.execute(
            "SELECT employee_id,date,work_date,status,attendance_status "
            "FROM attendance ORDER BY employee_id"
        ).fetchall()
        assert [tuple(row) for row in saved] == [
            (employee_ids[0], date.today().isoformat(), date.today().isoformat(), "Present", "Present"),
            (employee_ids[1], date.today().isoformat(), date.today().isoformat(), "Leave", "Leave"),
        ]
    finally:
        db.conn.close()


def test_remote_attendance_merge_populates_legacy_required_columns(monkeypatch, tmp_path):
    import sqlite3

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "legacy-merge.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))

    local_legacy = sqlite3.connect(tmp_path / "legacy-merge.db")
    local_legacy.execute("""
        CREATE TABLE attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            check_in TEXT NOT NULL DEFAULT '',
            check_out TEXT NOT NULL DEFAULT '',
            remarks TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
    """)
    local_legacy.commit()
    local_legacy.close()

    db = app.Database()
    remote_path = tmp_path / "remote.db"
    remote = sqlite3.connect(remote_path)
    remote.executescript("""
        CREATE TABLE employees(
            id INTEGER PRIMARY KEY, employee_code TEXT, name TEXT, department TEXT,
            designation TEXT, phone TEXT, email TEXT, joining_date TEXT,
            active INTEGER, notes TEXT, created_at TEXT
        );
        CREATE TABLE attendance(
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, work_date TEXT NOT NULL,
            date TEXT NOT NULL, status TEXT NOT NULL, check_in TEXT NOT NULL DEFAULT '',
            check_out TEXT NOT NULL DEFAULT '', break_minutes INTEGER NOT NULL DEFAULT 0,
            attendance_status TEXT NOT NULL, attendance_note TEXT NOT NULL DEFAULT '',
            remarks TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL
        );
    """)
    work_date = date.today().isoformat()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    remote.execute(
        "INSERT INTO employees VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (9, "SYNC-LEGACY-01", "Legacy Sync Employee", "Ops", "", "", "",
         work_date, 1, "", stamp),
    )
    remote.execute(
        "INSERT INTO attendance VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (17, 9, work_date, work_date, "Present", "09:00", "18:00", 0,
         "Present", "Remote attendance", "Remote attendance", stamp),
    )
    remote.commit()
    remote.close()

    try:
        db.conn.execute(
            "INSERT INTO employees(employee_code,name,joining_date,active,created_at) VALUES(?,?,?,?,?)",
            ("SYNC-LEGACY-01", "Legacy Sync Employee", work_date, 1, stamp),
        )
        db.conn.commit()

        app.merge_remote_database_snapshot(db.conn, remote_path)

        saved = db.conn.execute(
            "SELECT date,work_date,status,attendance_status,check_in,check_out,remarks "
            "FROM attendance WHERE employee_id=(SELECT id FROM employees WHERE employee_code=?)",
            ("SYNC-LEGACY-01",),
        ).fetchone()
        assert tuple(saved) == (
            work_date, work_date, "Present", "Present", "09:00", "18:00", "Remote attendance"
        )
    finally:
        db.conn.close()
