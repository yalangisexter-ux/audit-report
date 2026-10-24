import sqlite3
from pathlib import Path

import pytest

from cloudflare_chat import normalize_api_base, websocket_url


def test_normalize_cloudflare_worker_url():
    assert normalize_api_base(" https://chat.example.workers.dev/ ") == "https://chat.example.workers.dev"


def test_local_http_is_allowed_for_development_only():
    assert normalize_api_base("http://127.0.0.1:8787/") == "http://127.0.0.1:8787"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "chat.example.workers.dev",
        "http://chat.example.workers.dev",
        "https://user:password@chat.example.workers.dev",
        "https://chat.example.workers.dev/api",
        "https://chat.example.workers.dev/?token=secret",
    ],
)
def test_reject_unsafe_or_malformed_worker_urls(value):
    with pytest.raises(ValueError):
        normalize_api_base(value)


def test_websocket_url_uses_wss_and_encodes_ticket():
    result = websocket_url("https://chat.example.workers.dev/", "one-time/+ticket")
    assert result == "wss://chat.example.workers.dev/api/chat/ws?ticket=one-time%2F%2Bticket"


def test_chat_migration_creates_private_group_and_message_tables():
    migration_path = Path(__file__).resolve().parent.parent / "cloudflare-chat" / "migrations" / "0001_initial.sql"
    migration = migration_path.read_text(encoding="utf-8")
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(migration)
    table_names = {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {
        "chat_users",
        "conversations",
        "conversation_members",
        "messages",
        "socket_tickets",
        "login_attempts",
        "bootstrap_guard",
    }.issubset(table_names)
    connection.close()
