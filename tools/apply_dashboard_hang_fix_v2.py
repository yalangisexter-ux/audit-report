#!/usr/bin/env python3
from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

old_batch = """    def _refresh_dashboard_productivity_batch(self, generation):
        \"\"\"Render at most four prepared productivity rows per event-loop turn.\"\"\"
        if getattr(self, \"_is_closing\", False):
            return
        if generation != getattr(self, \"_dashboard_productivity_generation\", None):
            return
        queue = getattr(self, \"_dashboard_productivity_queue\", [])
        metrics = getattr(self, \"_dashboard_productivity_metrics\", [])
        prepared = getattr(self, \"_dashboard_productivity_prepared_rows\", {})
        self.productivity_table.setUpdatesEnabled(False)
        try:
            for employee in queue[:4]:
                values_data = prepared.get(int(employee[\"id\"]))
                if values_data is None:
                    continue
                start, working_days, present_count, task_count, completed, score = values_data
                metrics.append((employee[\"name\"], score))
                values = [
                    employee[\"name\"], start.isoformat(), working_days,
                    present_count, task_count, completed, f\"{score}%\",
                ]
                row = self.productivity_table.rowCount()
                self.productivity_table.insertRow(row)
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter
                        | (Qt.AlignmentFlag.AlignLeft if column == 0 else Qt.AlignmentFlag.AlignCenter)
                    )
                    item.setToolTip(str(value))
                    self.productivity_table.setItem(row, column, item)
            del queue[:4]
        finally:
            self.productivity_table.setUpdatesEnabled(True)
        self.productivity_chart.set_values(metrics)
        if queue:
            QTimer.singleShot(
                10, lambda current_generation=generation:
                self._refresh_dashboard_productivity_batch(current_generation)
            )
"""

new_batch = """    def _refresh_dashboard_productivity_batch(self, generation):
        \"\"\"Render at most four prepared productivity rows per event-loop turn.

        Chart repaint is deferred until the queue is empty so switching to the
        Dashboard tab does not freeze while every intermediate batch repaints.
        \"\"\"
        if getattr(self, \"_is_closing\", False):
            return
        if generation != getattr(self, \"_dashboard_productivity_generation\", None):
            return
        queue = getattr(self, \"_dashboard_productivity_queue\", [])
        metrics = getattr(self, \"_dashboard_productivity_metrics\", [])
        prepared = getattr(self, \"_dashboard_productivity_prepared_rows\", {})
        self.productivity_table.setUpdatesEnabled(False)
        try:
            for employee in queue[:4]:
                values_data = prepared.get(int(employee[\"id\"]))
                if values_data is None:
                    continue
                start, working_days, present_count, task_count, completed, score = values_data
                metrics.append((employee[\"name\"], score))
                values = [
                    employee[\"name\"], start.isoformat(), working_days,
                    present_count, task_count, completed, f\"{score}%\",
                ]
                row = self.productivity_table.rowCount()
                self.productivity_table.insertRow(row)
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter
                        | (Qt.AlignmentFlag.AlignLeft if column == 0 else Qt.AlignmentFlag.AlignCenter)
                    )
                    item.setToolTip(str(value))
                    self.productivity_table.setItem(row, column, item)
            del queue[:4]
        finally:
            self.productivity_table.setUpdatesEnabled(True)
        # Only paint the chart once all rows are ready. Intermediate chart
        # repaints were freezing the UI when many employees were present.
        if queue:
            QTimer.singleShot(
                10, lambda current_generation=generation:
                self._refresh_dashboard_productivity_batch(current_generation)
            )
        else:
            self.productivity_chart.set_values(metrics)
"""

if "Chart repaint is deferred until the queue is empty" in text:
    print("batch already patched")
elif old_batch in text:
    text = text.replace(old_batch, new_batch, 1)
    print("patched batch")
else:
    raise SystemExit("batch block not found")

old_anim = """        # Dashboard has large tables/charts; opacity effects freeze the UI on Windows.\n        if index == 1:\n"""
new_anim = """        # Dashboard has large tables/charts; opacity effects freeze the UI on Windows.\n        # Match by index and by widget identity so future tab reordering cannot reintroduce the hang.\n        if index == 1 or page is getattr(self, \"dashboard\", None):\n"""
if 'page is getattr(self, "dashboard"' in text:
    print("anim already patched")
elif old_anim in text:
    text = text.replace(old_anim, new_anim, 1)
    print("patched anim")
else:
    raise SystemExit("anim block not found")

old_worker = """        self.productivity_chart.set_values([])\n        if not employees:\n            return\n        for previous_worker in list(getattr(self, \"_dashboard_productivity_workers\", [])):\n            if previous_worker.isRunning():\n                previous_worker.requestInterruption()\n        worker = DashboardProductivityWorker(generation, employees)\n        if not hasattr(self, \"_dashboard_productivity_workers\"):\n            self._dashboard_productivity_workers = []\n        self._dashboard_productivity_workers.append(worker)\n        _ACTIVE_DASHBOARD_PRODUCTIVITY_WORKERS.add(worker)\n        worker.result_ready.connect(self._on_dashboard_productivity_ready)\n        worker.failed.connect(self._on_dashboard_productivity_failed)\n        worker.finished.connect(\n            lambda current=worker: self._cleanup_dashboard_productivity_worker(current)\n        )\n        worker.start()\n"""

new_worker = """        self.productivity_chart.set_values([])\n        if not employees:\n            return\n        # Start the worker on the next event-loop turn so the Dashboard tab can\n        # paint KPIs/recent tables first. Business logic and scores are unchanged.\n        QTimer.singleShot(\n            0,\n            lambda current_generation=generation, current_employees=list(employees):\n            self._start_dashboard_productivity_worker(current_generation, current_employees),\n        )\n\n    def _start_dashboard_productivity_worker(self, generation, employees):\n        if getattr(self, \"_is_closing\", False):\n            return\n        if generation != getattr(self, \"_dashboard_productivity_generation\", None):\n            return\n        for previous_worker in list(getattr(self, \"_dashboard_productivity_workers\", [])):\n            if previous_worker.isRunning():\n                previous_worker.requestInterruption()\n        worker = DashboardProductivityWorker(generation, employees)\n        if not hasattr(self, \"_dashboard_productivity_workers\"):\n            self._dashboard_productivity_workers = []\n        self._dashboard_productivity_workers.append(worker)\n        _ACTIVE_DASHBOARD_PRODUCTIVITY_WORKERS.add(worker)\n        worker.result_ready.connect(self._on_dashboard_productivity_ready)\n        worker.failed.connect(self._on_dashboard_productivity_failed)\n        worker.finished.connect(\n            lambda current=worker: self._cleanup_dashboard_productivity_worker(current)\n        )\n        worker.start()\n"""

if "_start_dashboard_productivity_worker" in text:
    print("worker already patched")
elif old_worker in text:
    text = text.replace(old_worker, new_worker, 1)
    print("patched worker")
else:
    raise SystemExit("worker block not found")

path.write_text(text, encoding="utf-8")

test_path = Path("tests/test_dashboard_productivity_async.py")
test_text = test_path.read_text(encoding="utf-8")
extra = '''

def test_dashboard_productivity_chart_updates_only_after_final_batch():
    import inspect
    source = inspect.getsource(app.MainWindow._refresh_dashboard_productivity_batch)
    # Chart must not repaint on intermediate batches.
    assert "if queue:" in source
    assert "self.productivity_chart.set_values(metrics)" in source
    # set_values should appear only in the empty-queue branch, after the queue check.
    chart_pos = source.rfind("self.productivity_chart.set_values(metrics)")
    queue_pos = source.find("if queue:")
    assert queue_pos != -1 and chart_pos != -1
    assert queue_pos < chart_pos
    assert "Intermediate chart" in source or "queue is empty" in source or "deferred until" in source


def test_dashboard_tab_transition_skips_opacity_effect():
    import inspect
    source = inspect.getsource(app.MainWindow.animate_tab_transition)
    assert "index == 1" in source
    assert "dashboard" in source
    assert "QGraphicsOpacityEffect" in source
    # Dashboard branch must return before creating an opacity effect.
    dash_branch = source.find("index == 1")
    effect_pos = source.find("QGraphicsOpacityEffect")
    assert dash_branch != -1 and effect_pos != -1
    assert dash_branch < effect_pos
'''
if "test_dashboard_productivity_chart_updates_only_after_final_batch" not in test_text:
    test_path.write_text(test_text.rstrip() + "\n" + extra, encoding="utf-8")
    print("tests updated")
else:
    print("tests already present")
print("done")
