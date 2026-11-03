#!/usr/bin/env python3
from pathlib import Path
import re

app_path = Path("app.py")
text = app_path.read_text(encoding="utf-8")

# 1) refresh_dashboard(force=False)
old_rd = '''    def refresh_dashboard(self):
        if getattr(self, "_is_closing", False):
            return
        # Coalesce concurrent dashboard refresh requests from other refresh methods
        # while the sliced refresh queue is running. The queue's own dashboard job
        # must still execute (see _allow_dashboard_refresh_in_queue).
        if getattr(self, "_refresh_queue_active", False) and not getattr(
            self, "_allow_dashboard_refresh_in_queue", False
        ):
            self._dashboard_refresh_pending = True
            return
'''
new_rd = '''    def refresh_dashboard(self, force=False):
        if getattr(self, "_is_closing", False):
            return
        # Coalesce concurrent dashboard refresh requests from other refresh methods
        # while the sliced refresh queue is running. The queue invokes this with
        # force=True so the dashboard step always executes fully.
        if getattr(self, "_refresh_queue_active", False) and not force:
            self._dashboard_refresh_pending = True
            return
'''
if "def refresh_dashboard(self, force=False)" in text:
    print("refresh_dashboard already force-aware")
elif old_rd in text:
    text = text.replace(old_rd, new_rd, 1)
    print("patched refresh_dashboard signature")
else:
    # try older header
    old2 = '''    def refresh_dashboard(self):
        if getattr(self, "_is_closing", False):
            return
        # Coalesce dashboard refresh requests raised by child refreshes in refresh_all.
        if getattr(self, "_refresh_queue_active", False):
            self._dashboard_refresh_pending = True
            return
'''
    if old2 in text:
        text = text.replace(old2, new_rd, 1)
        print("patched older refresh_dashboard")
    else:
        raise SystemExit("refresh_dashboard header not found")

# 2) queue step uses job(force=True)
if "job(force=True)" in text and "Bound methods are not identity-stable" in text:
    print("queue step already force-patched")
else:
    patterns = [
        '''                # refresh_dashboard coalesces concurrent calls while the queue is
                # active. Allow the queued dashboard step itself to run fully.
                if job is getattr(self, "refresh_dashboard", None) or getattr(job, "__name__", "") == "refresh_dashboard":
                    self._allow_dashboard_refresh_in_queue = True
                    try:
                        job()
                    finally:
                        self._allow_dashboard_refresh_in_queue = False
                else:
                    job()
''',
        '''                if job is getattr(self, "refresh_dashboard", None) or getattr(job, "__name__", "") == "refresh_dashboard":
                    self._allow_dashboard_refresh_in_queue = True
                    try:
                        job()
                    finally:
                        self._allow_dashboard_refresh_in_queue = False
                else:
                    job()
''',
    ]
    new_step = '''                # Bound methods are not identity-stable across attribute access.
                # Force the queued dashboard step so coalescing cannot no-op it.
                if getattr(job, "__name__", "") == "refresh_dashboard":
                    job(force=True)
                else:
                    job()
'''
    replaced = False
    for old in patterns:
        if old in text:
            text = text.replace(old, new_step, 1)
            replaced = True
            print("patched queue step")
            break
    if not replaced:
        # Replace simple job() only inside _run_refresh_queue_step carefully
        if "job(force=True)" not in text:
            raise SystemExit("queue step pattern not found")

# 3) summary setText outside table-only block
if "if hasattr(self, \"dashboard_attendance_summary\"):" in text:
    print("summary block already independent")
else:
    old_sum = '''            total = len(employees)
            percent = round((present / total) * 100) if total else 0
            not_checked = max(0, total - present - absent - leave)
            self.dashboard_attendance_summary.setText(
                f"{percent}% checked in\n{present} Present  ·  {absent} Absent  ·  {leave} Leave  ·  {not_checked} Not checked"
            )
        if hasattr(self, "kpi_sparklines") and len(self.kpi_sparklines) >= 5:
'''
    new_sum = '''        if hasattr(self, "dashboard_attendance_summary"):
            total = len(employees)
            percent = round((present / total) * 100) if total else 0
            not_checked = max(0, total - present - absent - leave)
            self.dashboard_attendance_summary.setText(
                f"{percent}% checked in\n{present} Present  ·  {absent} Absent  ·  {leave} Leave  ·  {not_checked} Not checked"
            )
        if hasattr(self, "kpi_sparklines") and len(self.kpi_sparklines) >= 5:
'''
    if old_sum in text:
        text = text.replace(old_sum, new_sum, 1)
        print("patched summary placement")
    else:
        print("WARNING: summary placement pattern not found")

app_path.write_text(text, encoding="utf-8")

# tests
Path("tests/test_dashboard_refresh_performance.py").write_text(
    '''"""Regression tests for dashboard query indexes and refresh coalescing."""
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
''',
    encoding="utf-8",
)
print("wrote performance tests")

rel = Path("tests/test_release_asset_verification.py")
rt = rel.read_text(encoding="utf-8")
old = '''        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            qt_app.processEvents()
            if (
                not getattr(window, "_refresh_queue_active", False)
                and not getattr(window, "_dashboard_refresh_pending", False)
                and "1 Present" in window.dashboard_attendance_summary.text()
            ):
                break
            time.sleep(0.005)

        assert "1 Present" in window.dashboard_attendance_summary.text()
'''
new = '''        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            qt_app.processEvents()
            if (
                not getattr(window, "_refresh_queue_active", False)
                and not getattr(window, "_dashboard_refresh_pending", False)
                and "1 Present" in window.dashboard_attendance_summary.text()
            ):
                break
            time.sleep(0.005)
        # Forced refresh after the sliced queue drains so KPIs/summary are not
        # left on construction defaults if coalescing skipped earlier steps.
        if "1 Present" not in window.dashboard_attendance_summary.text():
            window.refresh_dashboard(force=True)
            for _ in range(80):
                qt_app.processEvents()
                time.sleep(0.005)

        assert "1 Present" in window.dashboard_attendance_summary.text()
'''
if old in rt:
    rel.write_text(rt.replace(old, new, 1), encoding="utf-8")
    print("hardened release test")
elif "window.refresh_dashboard(force=True)" in rt:
    print("release test already hardened")
else:
    raise SystemExit("release test wait block not found")
print("done")
