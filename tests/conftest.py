"""Shared pytest cleanup for application-owned background services."""

import pytest


@pytest.fixture(autouse=True)
def close_database_sync_workers_after_each_test():
    """Prevent database-sync daemon threads leaking across Qt/PySide test cases."""
    yield
    from database_sync import close_all_sync_workers

    close_all_sync_workers(timeout=2.0)
