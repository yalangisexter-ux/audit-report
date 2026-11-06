from types import SimpleNamespace

import app


def test_customer_first_login_pushes_initial_snapshot_to_its_installation(monkeypatch):
    calls = {}
    installation_id = "c4cf201d3c68e2fcaf60aa05fd423d9a"

    class FakeSync:
        is_configured = True
        is_busy = False
        is_dirty = False
        installation_id = "c4cf201d3c68e2fcaf60aa05fd423d9a"

        def download_latest_snapshot(self, **kwargs):
            calls["pull"] = kwargs
            raise RuntimeError("No remote snapshot exists for this installation yet.")

        def request_sync(self):
            calls["push"] = True
            return True

    class InlineThread:
        def __init__(self, target, name=None, daemon=None):
            self.target = target

        def start(self):
            self.target()

    sync = FakeSync()
    fake_window = SimpleNamespace(
        current_user={"username": "Admin", "role": "Admin"},
        db=SimpleNamespace(github_sync=sync),
        _auto_sync_running=False,
    )
    monkeypatch.setattr(app.threading, "Thread", InlineThread)

    app.MainWindow._background_auto_sync(fake_window)

    assert calls["pull"] == {
        "target_installation_id": installation_id,
        "prefer_latest": False,
    }
    assert calls["push"] is True
    assert fake_window._auto_sync_running is False

def test_customer_login_marks_pending_but_waits_for_remote_pull_before_upload():
    calls = []

    class FakeSync:
        is_configured = True

        def mark_pending(self):
            calls.append("mark_pending")

        def schedule_sync(self, delay):
            calls.append(("unsafe_direct_upload", delay))

    fake_db = SimpleNamespace(github_sync=FakeSync())
    app.Database.set_active_user(
        fake_db,
        {"username": "Admin", "role": "Admin"},
    )

    assert calls == ["mark_pending"]

def test_failed_customer_pull_does_not_upload_stale_local_snapshot(monkeypatch):
    calls = []

    class FakeSync:
        is_configured = True
        is_busy = False
        is_dirty = True
        installation_id = "customer-installation"

        def download_latest_snapshot(self, **kwargs):
            calls.append(("pull", kwargs))
            raise OSError("temporary network failure")

        def request_sync(self):
            calls.append(("push",))
            return True

    class InlineThread:
        def __init__(self, target, name=None, daemon=None):
            self.target = target

        def start(self):
            self.target()

    fake_window = SimpleNamespace(
        current_user={"username": "Admin", "role": "Admin"},
        db=SimpleNamespace(github_sync=FakeSync()),
        _auto_sync_running=False,
    )
    monkeypatch.setattr(app.threading, "Thread", InlineThread)

    app.MainWindow._background_auto_sync(fake_window)

    assert calls == [("pull", {
        "target_installation_id": "customer-installation",
        "prefer_latest": False,
    })]
    assert fake_window._auto_sync_running is False

def test_first_run_setup_is_allowed_only_when_exact_installation_snapshot_is_confirmed_missing():
    calls = {}
    installation_id = "c4cf201d3c68e2fcaf60aa05fd423d9a"

    class MissingSnapshotSync:
        is_configured = True
        installation_id = "c4cf201d3c68e2fcaf60aa05fd423d9a"

        def download_latest_snapshot(self, **kwargs):
            calls["pull"] = kwargs
            raise RuntimeError("No remote snapshot exists for this installation yet.")

    allowed, reason = app.restore_first_run_cloud_snapshot(
        SimpleNamespace(github_sync=MissingSnapshotSync())
    )

    assert calls["pull"] == {
        "target_installation_id": installation_id,
        "prefer_latest": False,
    }
    assert allowed is True
    assert "No remote customer snapshot exists" in reason


def test_first_run_setup_is_blocked_when_remote_snapshot_pull_fails():
    class UnreachableSync:
        is_configured = True
        installation_id = "c4cf201d3c68e2fcaf60aa05fd423d9a"

        def download_latest_snapshot(self, **kwargs):
            raise RuntimeError("Could not reach the secure database-sync service: timeout")

    allowed, reason = app.restore_first_run_cloud_snapshot(
        SimpleNamespace(github_sync=UnreachableSync())
    )

    assert allowed is False
    assert "could not be downloaded" in reason


def test_first_run_setup_is_blocked_when_restored_snapshot_has_no_active_account(monkeypatch):
    class ExistingSnapshotSync:
        is_configured = True
        installation_id = "c4cf201d3c68e2fcaf60aa05fd423d9a"

        def download_latest_snapshot(self, **kwargs):
            return b"verified snapshot bytes"

    class Cursor:
        def fetchone(self):
            return (0,)

    class Connection:
        def execute(self, statement):
            assert "auth_users" in statement
            return Cursor()

    monkeypatch.setattr(app, "merge_remote_database_snapshot", lambda conn, path: {})
    allowed, reason = app.restore_first_run_cloud_snapshot(
        SimpleNamespace(github_sync=ExistingSnapshotSync(), conn=Connection())
    )

    assert allowed is False
    assert "no active login account" in reason



def test_first_run_restore_refuses_global_snapshot_discovery_without_installation_id():
    class UnidentifiedSync:
        is_configured = True

        def download_latest_snapshot(self, **kwargs):
            raise AssertionError("Global snapshot discovery must never be attempted.")

    allowed, reason = app.restore_first_run_cloud_snapshot(
        SimpleNamespace(github_sync=UnidentifiedSync())
    )

    assert allowed is False
    assert "installation ID is unavailable" in reason
