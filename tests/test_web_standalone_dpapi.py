"""Regression coverage for Linux web-mode database initialization."""

import app


def test_web_standalone_skips_windows_dpapi_sync_initialization(monkeypatch):
    """The web database must not initialize the desktop DPAPI credential store."""
    monkeypatch.setenv("WEB_STANDALONE", "1")

    def fail_if_dpapi_is_used(*args, **kwargs):
        raise AssertionError("Windows DPAPI must not be called in web standalone mode")

    monkeypatch.setattr(app, "protect_sync_token", fail_if_dpapi_is_used)
    database = object.__new__(app.Database)

    database._initialize_github_sync()

    assert database.github_sync is None
