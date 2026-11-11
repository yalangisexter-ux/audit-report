import json
import sqlite3

from tools.cloudflare_d1_import import build_import, ordered_tables, sql_value


def test_sql_value_quotes_text_and_preserves_blobs():
    assert sql_value("O'Reilly") == "'O''Reilly'"
    assert sql_value(b"\\x00\\xff") == "X'00ff'"
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
    assert manifest["total_rows"] == 2
    assert manifest["excluded_ephemeral_tables"] == ["web_auth_sessions"]

    chunks = sorted(tmp_path.glob("chunk-*.json"))
    statements = [statement for path in chunks for statement in json.loads(path.read_text())]
    assert any("O''Reilly" in statement for statement in statements)
    assert any('INSERT OR REPLACE INTO "tasks"' in statement for statement in statements)
    source.close()
