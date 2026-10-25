"""Regression tests for case-sensitive customer/developer sync roles."""

import app


def test_customer_admin_and_developer_admin_are_distinct_accounts():
    customer = {"username": "taruna", "display_name": "Taruna", "role": "Admin"}
    developer = {"username": "admin", "display_name": "Developer", "role": "Admin"}

    assert app.is_developer_test_user(customer) is False
    assert app.is_master_customer_user(customer) is True
    assert app.is_developer_test_user(developer) is True
    assert app.is_master_customer_user(developer) is False


def test_developer_role_still_requires_developer_sync_authorization():
    assert app.is_developer_test_user({"username": "qa-user", "role": "Developer"}) is True
    assert app.is_developer_test_user({"username": "taruna", "display_name": "Taruna", "role": "Developer"}) is False


def test_developer_background_sync_is_blocked_but_password_authorized_sync_can_run(monkeypatch):
    from types import SimpleNamespace
    import google_sheets_sync

    db = SimpleNamespace(active_user={"username": "admin", "role": "Admin"})
    blocked = google_sheets_sync.continuous_auto_sync(db)
    assert blocked["status"] == "test_mode"

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"x" * 1200

    monkeypatch.setattr(google_sheets_sync.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    monkeypatch.setattr(google_sheets_sync, "sync_database_from_workbook_bytes", lambda *_args, **_kwargs: {"stores": 1})
    monkeypatch.setattr(google_sheets_sync, "save_master_database_snapshot", lambda *_args, **_kwargs: "snapshot.xlsx")

    authorized = google_sheets_sync.continuous_auto_sync(db, developer_authorized=True)
    assert authorized["status"] == "synced"
    assert authorized["updated"] == 1
