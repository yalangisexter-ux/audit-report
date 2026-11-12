import json
import sqlite3

from pathlib import Path

import pytest

from tools.cloudflare_d1_import import (
    build_import,
    ensure_empty_target,
    expected_migration_schema,
    ordered_tables,
    sql_value,
)


def test_sql_value_quotes_text_and_preserves_blobs():
    assert sql_value("O'Reilly") == "'O''Reilly'"
    assert sql_value(bytes([0, 255])) == "X'00ff'"
    assert sql_value(None) == "NULL"
    assert sql_value(12) == "12"


def test_import_is_bounded_and_orders_parent_rows_first(tmp_path):
    schema = __import__("pathlib").Path("cloudflare/d1/migrations/0001_initial.sql")
    source = sqlite3.connect(":memory:")
    source.executescript(schema.read_text(encoding="utf-8"))
    source.execute(
        "INSERT INTO employees(id, name, created_at) VALUES(1, ?, ?)",
        ("O'Reilly", "2026-11-11T00:00:00Z"),
    )
    source.execute(
        "INSERT INTO tasks(id, employee_id, task_date, title) VALUES(1, 1, '2026-11-11', 'Audit')"
    )
    source.commit()

    order = ordered_tables(source)
    assert order.index("employees") < order.index("tasks")

    manifest = build_import(source, schema, tmp_path)
    assert manifest["tables"]["employees"] == 1
    assert manifest["tables"]["tasks"] == 1
    assert manifest["total_rows"] == 3  # employees + tasks + schema-seeded working-weekdays setting
    assert manifest["excluded_ephemeral_tables"] == ["web_auth_sessions"]

    chunks = sorted(tmp_path.glob("chunk-*.json"))
    statements = [statement for path in chunks for statement in json.loads(path.read_text())]
    assert any("O''Reilly" in statement for statement in statements)
    assert any('INSERT OR REPLACE INTO "tasks"' in statement for statement in statements)
    source.close()



def test_expected_migration_schema_applies_all_additive_migrations():
    schema = expected_migration_schema(Path("cloudflare/d1/migrations"))

    assert {
        "store_orders",
        "store_order_items",
        "sales_channels",
        "marketplace_orders",
        "marketplace_order_items",
        "marketplace_events",
        "sales_sync_jobs",
        "sales_notifications",
        "channel_product_mappings",
    } <= set(schema)
    assert {"employee_id", "permissions"} <= schema["auth_users"]
    assert "approval_status" in schema["tasks"]
    assert {"department", "employee_ids"} <= schema["holidays"]


def test_empty_target_guard_allows_only_seeded_settings():
    ensure_empty_target({
        "settings": 1,
        "employees": 0,
        "tasks": 0,
        "attendance": 0,
        "web_auth_sessions": 0,
    })


def test_empty_target_guard_refuses_existing_customer_rows():
    with pytest.raises(ValueError, match="refusing to import or reconcile"):
        ensure_empty_target({
            "settings": 1,
            "employees": 9,
            "tasks": 49,
            "attendance": 20,
        })


def test_empty_target_guard_does_not_ignore_existing_web_sessions():
    with pytest.raises(ValueError, match="web_auth_sessions=1"):
        ensure_empty_target({"settings": 1, "web_auth_sessions": 1})
