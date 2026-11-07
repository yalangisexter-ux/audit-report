from pathlib import Path
import sqlite3

MIGRATION = Path(__file__).resolve().parents[1] / "cloudflare" / "d1" / "migrations" / "0001_initial.sql"


def test_cloudflare_d1_baseline_schema_matches_required_application_tables(tmp_path):
    connection = sqlite3.connect(tmp_path / "d1-schema-check.sqlite3")
    try:
        connection.executescript(MIGRATION.read_text(encoding="utf-8"))
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        required = {
            "settings", "auth_users", "employees", "tasks", "attendance", "holidays",
            "employee_groups", "archived_documents", "audit_log", "source_reports",
            "employee_targets", "customer_prospects", "bt_products", "bt_stock_ledger",
            "bt_orders", "bt_order_items", "bt_services", "bt_members", "bt_activities",
            "web_auth_sessions", "local_chat_messages",
        }
        assert required <= tables
        assert connection.execute(
            "SELECT value FROM settings WHERE key='working_weekdays'"
        ).fetchone()[0] == "0,1,2,3,4,6"
        attendance_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(attendance)")
        }
        assert {"work_date", "attendance_status", "check_in", "check_out", "break_minutes"} <= attendance_columns
        task_columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
        assert {"target_qty", "actual_qty", "next_action", "custom_values", "updated_at"} <= task_columns
        employee_columns = {row[1] for row in connection.execute("PRAGMA table_info(employees)")}
        assert {"employee_code", "display_order", "joining_date"} <= employee_columns
        # Exact-case account names must remain distinct; this creates test rows only
        # in a temporary SQLite file and never touches customer accounts.
        account_columns = (
            "username, display_name, role, password_salt, password_hash, "
            "security_question, answer_salt, answer_hash, created_at, updated_at"
        )
        values = (
            ("Admin", "Customer Admin", "Admin", "s", "h", "q", "s", "h", "now", "now"),
            ("admin", "Developer", "Developer", "s", "h", "q", "s", "h", "now", "now"),
        )
        connection.executemany(
            f"INSERT INTO auth_users({account_columns}) VALUES(?,?,?,?,?,?,?,?,?,?)",
            values,
        )
        assert connection.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] == 2
    finally:
        connection.close()
