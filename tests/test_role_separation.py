"""Regression tests for case-sensitive customer/developer sync roles."""

import app


def test_customer_admin_and_developer_admin_are_distinct_accounts():
    customer = {"username": "Admin", "display_name": "Taruna", "role": "Admin"}
    developer = {"username": "admin", "display_name": "Developer", "role": "Admin"}

    assert app.is_developer_test_user(customer) is False
    assert app.is_master_customer_user(customer) is True
    assert app.is_developer_test_user(developer) is True
    assert app.is_master_customer_user(developer) is False


def test_developer_role_still_requires_developer_sync_authorization():
    assert app.is_developer_test_user({"username": "qa-user", "role": "Developer"}) is True
    assert app.is_developer_test_user({"username": "Admin", "role": "Developer"}) is False
