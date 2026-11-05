from types import SimpleNamespace

import app


def test_customer_first_login_pushes_initial_snapshot_to_its_installation(monkeypatch):
    calls = {}
    installation_id = "c4cf201d3c68e2fcaf60aa05fd423d9a"

    class FakeSync:
        is_configured = True
        is_busy = False
        is_dirty = False
        installation_id = installation_id

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
