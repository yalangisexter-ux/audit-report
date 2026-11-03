"""Regression tests for dashboard query indexes and refresh coalescing."""
from pathlib import Path

import app


def test_dashboard_query_indexes_are_created_for_existing_database(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "dashboard-indexes.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    try:
        task_indexes = {row["name"] for row in db.conn.execute("PRAGMA index_list(tasks)")}
        attendance_indexes = {row["name"] for row in db.conn.execute("PRAGMA index_list(attendance)")}
        assert "idx_tasks_employee_date" in task_indexes
        assert "idx_tasks_date_employee" in task_indexes
        assert "idx_attendance_date_employee" in attendance_indexes
    finally:
        db.conn.close()


def test_refresh_queue_coalesces_dashboard_refresh_requests():
    source = Path(app.__file__).read_text(encoding="utf-8")
    assert 'self._dashboard_refresh_pending = True' in source
    assert 'QTimer.singleShot(0, self.refresh_dashboard)' in source
    assert 'self.refresh_attendance_summary,' not in source


def test_dashboard_indexes_are_created_after_legacy_column_migrations():
    source = Path(app.__file__).read_text(encoding="utf-8")
    task_migration = source.index('apply_column_migrations("tasks", task_migrations)')
    attendance_migration = source.index('apply_column_migrations("attendance", attendance_migrations)')
    task_index = source.index("idx_tasks_employee_date")
    attendance_index = source.index("idx_attendance_date_employee")
    assert task_migration < task_index
    assert attendance_migration < attendance_index


def test_refresh_dashboard_runs_when_selected_as_queue_job():
    source = Path(app.__file__).read_text(encoding="utf-8")
    assert "def refresh_dashboard(self, force=False)" in source
    assert "job(force=True)" in source
    assert 'getattr(job, "__name__", "") == "refresh_dashboard"' in source
    assert "Bound methods are not identity-stable" in source
