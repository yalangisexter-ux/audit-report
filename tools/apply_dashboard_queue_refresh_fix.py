#!/usr/bin/env python3
from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

old_rd = '''    def refresh_dashboard(self):
        if getattr(self, "_is_closing", False):
            return
        # Coalesce dashboard refresh requests raised by child refreshes in refresh_all.
        if getattr(self, "_refresh_queue_active", False):
            self._dashboard_refresh_pending = True
            return
'''

new_rd = '''    def refresh_dashboard(self):
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

if "_allow_dashboard_refresh_in_queue" in text and "Coalesce concurrent dashboard refresh requests" in text:
    print("refresh_dashboard already patched")
elif old_rd in text:
    text = text.replace(old_rd, new_rd, 1)
    print("patched refresh_dashboard")
else:
    raise SystemExit("refresh_dashboard header not found")

old_step = '''        queue = getattr(self, "_refresh_queue", [])
        if queue:
            job = queue.pop(0)
            try:
                job()
            except Exception:
                logging.getLogger("app").exception("Deferred UI refresh failed: %s", getattr(job, "__name__", repr(job)))
            QTimer.singleShot(15, self._run_refresh_queue_step)
            return
'''

new_step = '''        queue = getattr(self, "_refresh_queue", [])
        if queue:
            job = queue.pop(0)
            try:
                # refresh_dashboard coalesces concurrent calls while the queue is
                # active. Allow the queued dashboard step itself to run fully.
                if job is getattr(self, "refresh_dashboard", None) or getattr(job, "__name__", "") == "refresh_dashboard":
                    self._allow_dashboard_refresh_in_queue = True
                    try:
                        job()
                    finally:
                        self._allow_dashboard_refresh_in_queue = False
                else:
                    job()
            except Exception:
                logging.getLogger("app").exception("Deferred UI refresh failed: %s", getattr(job, "__name__", repr(job)))
            QTimer.singleShot(15, self._run_refresh_queue_step)
            return
'''

if "Allow the queued dashboard step itself to run fully" in text:
    print("queue step already patched")
elif old_step in text:
    text = text.replace(old_step, new_step, 1)
    print("patched queue step")
else:
    raise SystemExit("queue step not found")

path.write_text(text, encoding="utf-8")

test_path = Path("tests/test_dashboard_refresh_performance.py")
t = test_path.read_text(encoding="utf-8")
extra = '''

def test_refresh_dashboard_runs_when_selected_as_queue_job():
    source = Path(app.__file__).read_text(encoding="utf-8")
    assert "_allow_dashboard_refresh_in_queue" in source
    assert "Coalesce concurrent dashboard refresh requests" in source
    assert 'getattr(job, "__name__", "") == "refresh_dashboard"' in source or "job is getattr(self, \"refresh_dashboard\"" in source
'''
if "test_refresh_dashboard_runs_when_selected_as_queue_job" not in t:
    test_path.write_text(t.rstrip() + "\n" + extra, encoding="utf-8")
    print("test added")
else:
    print("test already present")
print("done")
