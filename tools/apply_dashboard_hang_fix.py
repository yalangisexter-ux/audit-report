#!/usr/bin/env python3
"""Minimal Dashboard hang fix for app.py. No feature changes."""
from pathlib import Path
import sys

path = Path(__file__).resolve().parents[1] / "app.py"
text = path.read_text(encoding="utf-8")
if "lookback_days = 90" in text and "attendance_by_id" in text:
    print("already applied")
    sys.exit(0)

old = """    def animate_tab_transition(self, index):
        page = self.tabs.widget(index)
        if page is None:
            return
        if self._tab_animation:
            self._tab_animation.stop()
        if self._animated_page:
            self._animated_page.setGraphicsEffect(None)
        effect = QGraphicsOpacityEffect(page)"""
new = """    def animate_tab_transition(self, index):
        page = self.tabs.widget(index)
        if page is None:
            return
        # Dashboard has large tables/charts; opacity effects freeze the UI on Windows.
        if index == 1:
            if self._tab_animation:
                self._tab_animation.stop()
            if self._animated_page:
                try:
                    self._animated_page.setGraphicsEffect(None)
                except Exception:
                    pass
            try:
                page.setGraphicsEffect(None)
            except Exception:
                pass
            return
        if self._tab_animation:
            self._tab_animation.stop()
        if self._animated_page:
            self._animated_page.setGraphicsEffect(None)
        effect = QGraphicsOpacityEffect(page)"""
if old not in text:
    print("FAIL: animate_tab_transition pattern", file=sys.stderr)
    sys.exit(1)
text = text.replace(old, new, 1)

old = """        attendance_rows = []
        for employee in employees:
            record = self.db.conn.execute(
                \"SELECT attendance_status, check_in FROM attendance WHERE employee_id=? AND work_date=?\",
                (employee[\"id\"], report_date),
            ).fetchone()"""
new = """        attendance_rows = []
        attendance_by_id = {}
        if employees:
            ids = [int(e[\"id\"]) for e in employees]
            marks = \",\".join(\"?\" for _ in ids)
            for record in self.db.conn.execute(
                f\"SELECT employee_id, attendance_status, check_in FROM attendance WHERE work_date=? AND employee_id IN ({marks})\",
                (report_date, *ids),
            ).fetchall():
                attendance_by_id[int(record[\"employee_id\"])] = record
        for employee in employees:
            record = attendance_by_id.get(int(employee[\"id\"]))"""
if old not in text:
    print("FAIL: attendance N+1 pattern", file=sys.stderr)
    sys.exit(1)
text = text.replace(old, new, 1)

old = """                starts = {}
                for employee in employees:
                    starts[employee[\"id\"]] = self.tracking_start_date(employee)
                earliest = min(starts.values())
                start_text = earliest.isoformat()
                end_text = today.isoformat()"""
new = """                lookback_days = 90
                range_start = today.fromordinal(max(1, today.toordinal() - lookback_days))
                starts = {}
                for employee in employees:
                    start = None
                    if employee[\"joining_date\"]:
                        try:
                            start = date.fromisoformat(employee[\"joining_date\"])
                        except ValueError:
                            start = None
                    if start is None:
                        start = range_start
                    starts[employee[\"id\"]] = max(start, range_start)
                start_text = min(starts.values()).isoformat()
                end_text = today.isoformat()"""
if old not in text:
    print("FAIL: tracking_start_date pattern", file=sys.stderr)
    sys.exit(1)
text = text.replace(old, new, 1)

old = """                    task_score = (task_progress_total / len(employee_tasks)) if employee_tasks else None
                    attendance_score = present_count / eligible * 100 if eligible else None"""
new = """                    task_score = (task_progress_total / len(employee_tasks)) if employee_tasks else None
                    present_count = 0
                    for row in attendance_by_employee.get(employee[\"id\"], attendance_by_employee.get(int(employee[\"id\"]), [])):
                        status = str(row[\"attendance_status\"] or \"\").strip()
                        has_check_in = bool(str(row[\"check_in\"] or \"\").strip())
                        if is_present_attendance_status(status) or (status.casefold() in {\"unmarked\", \"\"} and has_check_in):
                            present_count += 1
                    working_days = self.count_working_days(start, today)
                    eligible = max(1, working_days)
                    attendance_score = present_count / eligible * 100 if eligible else None"""
if old not in text:
    print("FAIL: score block pattern", file=sys.stderr)
    sys.exit(1)
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("applied ok")
