"""Regression tests for non-blocking dashboard productivity preparation."""
from datetime import date, datetime

import app


def test_dashboard_productivity_worker_preserves_existing_score(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "dashboard-worker.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    try:
        today = date.today().isoformat()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.set_setting("working_weekdays", "0,1,2,3,4,5,6")
        employee_id = db.conn.execute(
            "INSERT INTO employees(name,joining_date,active,created_at) VALUES(?,?,?,?)",
            ("Dashboard Worker", today, 1, timestamp),
        ).lastrowid
        db.conn.execute(
            "INSERT INTO tasks(employee_id,task_date,title,status,progress,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (employee_id, today, "Daily task", "In progress", 50, timestamp, timestamp),
        )
        db.conn.execute(
            "INSERT INTO attendance(employee_id,work_date,check_in,attendance_status,updated_at) "
            "VALUES(?,?,?,?,?)",
            (employee_id, today, "09:00", "Present", timestamp),
        )
        db.conn.commit()

        worker = app.DashboardProductivityWorker(17, db.employees(False))
        worker.start()
        assert worker.wait(5000), "Dashboard productivity worker did not finish"
        assert worker.error_text == ""
        assert worker.result_data is not None
        start, working_days, present, task_count, completed, score = worker.result_data[employee_id]
        assert start == date.today()
        assert working_days == 1
        assert present == 1
        assert task_count == 1
        assert completed == 0
        # Existing dashboard formula: 70% task score + 30% attendance score.
        assert score == 65
    finally:
        db.conn.close()


def test_dashboard_productivity_render_batch_has_no_database_queries():
    import inspect

    source = inspect.getsource(app.MainWindow._refresh_dashboard_productivity_batch)
    assert "self.db" not in source
    assert "execute(" not in source
    assert "count_working_days" not in source
    assert "QTimer.singleShot" in source
