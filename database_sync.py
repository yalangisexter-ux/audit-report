"""Encrypted, asynchronous snapshots of customer business data to GitHub."""
from __future__ import annotations

import json
import logging
import sqlite3
import tempfile
import ctypes
from pathlib import Path
from urllib.request import urlopen, Request

# Static marker for release validation / worker URL injection.
DEFAULT_DB_SYNC_WORKER_URL = ""
FALLBACK_DB_SYNC_WORKER_URL = "https://raw-strength-audit-db-sync.yalangisexter.workers.dev"

# Force PyInstaller to collect Windows ctypes helpers used by DPAPI token protection.
try:
    from ctypes import wintypes  # noqa: F401
    _WINTYPES_OK = True
except Exception:
    wintypes = None  # type: ignore
    _WINTYPES_OK = False

# Force PyInstaller collection of cryptography.
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
    from cryptography.hazmat.primitives.hashes import SHA256  # noqa: F401
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # noqa: F401
    _CRYPTO_OK = True
except Exception:
    AESGCM = SHA256 = PBKDF2HMAC = None  # type: ignore
    _CRYPTO_OK = False

_URL = (
    "https://raw.githubusercontent.com/yalangisexter-ux/audit-report/"
    "c023b0ebf9cbfcca6d83a3ddfddffd7fd254c1e0/database_sync.py"
)

_log = logging.getLogger("database_sync")


def _install_stubs(reason: str = ""):
    """Minimal stubs so app.py can import and the UI (including updates) can start.

    protect/unprotect must NOT raise — app DB init calls them and treats
    any exception as a fatal startup failure.
    """
    global GitHubDatabaseSync, SyncableSQLiteConnection, protect_sync_token, unprotect_sync_token

    class SyncableSQLiteConnection(sqlite3.Connection):
        def set_commit_callback(self, callback):
            self._commit_callback = callback

        def commit(self):
            super().commit()
            cb = getattr(self, "_commit_callback", None)
            if cb is not None:
                try:
                    cb()
                except Exception:
                    pass

    class GitHubDatabaseSync:
        def __init__(self, *args, **kwargs):
            self._status = "Sync unavailable: " + (reason or "module not loaded")
            self._busy = False
            self._dirty = False
            self._closed = False
            self._encryption_secret = ""
            self.worker_url = ""
            self._last_error = reason or "database_sync bootstrap failed"
            self._error_serial = 0

        @property
        def has_token(self):
            return False

        @property
        def is_configured(self):
            return False

        @property
        def status(self):
            return self._status

        @property
        def is_dirty(self):
            return False

        @property
        def is_busy(self):
            return False

        @property
        def last_error(self):
            return self._last_error

        @property
        def error_serial(self):
            return self._error_serial

        def mark_pending(self):
            pass

        def set_status(self, status):
            self._status = str(status)

        def set_encryption_secret(self, secret):
            self._encryption_secret = secret or ""

        def set_token(self, token):
            pass

        def set_device_credentials(self, credentials=None):
            pass

        def request_sync(self):
            return False

        def close(self, timeout=3):
            self._closed = True

        def download_latest_snapshot(self, *args, **kwargs):
            return None

    def protect_sync_token(token: str) -> str:
        # Pass-through when DPAPI is unavailable so startup never dies.
        return token or ""

    def unprotect_sync_token(value: str) -> str:
        return value or ""

    globals()["GitHubDatabaseSync"] = GitHubDatabaseSync
    globals()["SyncableSQLiteConnection"] = SyncableSQLiteConnection
    globals()["protect_sync_token"] = protect_sync_token
    globals()["unprotect_sync_token"] = unprotect_sync_token
    _log.warning("database_sync running in degraded mode: %s", reason or "bootstrap failed")


def _load():
    if not _CRYPTO_OK:
        _install_stubs("cryptography package missing")
        return
    if not _WINTYPES_OK:
        _install_stubs("ctypes.wintypes not available in this package")
        return
    try:
        req = Request(_URL, headers={"User-Agent": "RSC-AuditManager-bootstrap"})
        with urlopen(req, timeout=30) as resp:
            src = resp.read().decode("utf-8")
    except Exception as exc:
        _install_stubs(f"could not download sync module ({exc})")
        return

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
        _install_stubs("unexpected remote database_sync.py shape")
        return
    src = src.replace(old, new, 1)
    try:
        exec(compile(src, "database_sync.py", "exec"), globals())
    except Exception as exc:
        _install_stubs(f"sync module failed to load ({exc})")
        return
    try:
        from ctypes import wintypes as _wt  # noqa: F401
        assert _wt is not None
    except Exception as exc:
        _install_stubs(f"ctypes.wintypes unavailable after load ({exc})")


_load()
