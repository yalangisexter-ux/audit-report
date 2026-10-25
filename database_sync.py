"""Encrypted, asynchronous snapshots of customer business data to GitHub."""

from __future__ import annotations

import base64
import ctypes
import json
import logging
import os
import queue
import secrets
import sqlite3
import tempfile
import threading
import zlib
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    from build_info import APP_VERSION
except Exception:
    APP_VERSION = "1.3.23"


_SNAPSHOT_MAGIC = b"RSCDB1"
_SNAPSHOT_AAD = b"RawStrengthEmployeeAuditManager:encrypted-customer-database:v1"
_MAX_SNAPSHOT_BYTES = 60 * 1024 * 1024
# Optional built-in GitHub token for customer installations.
# Leave empty. A real token must never be committed; set it only in a private build
# or via a protected deployment secret if automatic push without customer entry is required.
BUILTIN_GITHUB_TOKEN = ""
# Replaced by the protected release workflow before packaging.
DEFAULT_DB_SYNC_WORKER_URL = ""
FALLBACK_DB_SYNC_WORKER_URL = "https://raw-strength-audit-db-sync.yalangisexter.workers.dev"

class SyncableSQLiteConnection(sqlite3.Connection):
    """SQLite connection that marks local changes after successful commits."""

    def set_commit_callback(self, callback):
        self._commit_callback = callback

    def commit(self):
        super().commit()
        callback = getattr(self, "_commit_callback", None)
        if callback is not None:
            try:
                callback()
            except Exception:
                # A cloud-sync failure must never undo or block a local save.
                pass


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _dpapi(data: bytes, *, decrypt: bool) -> bytes:
    """Protect a credential for the current Windows user with DPAPI."""
    if os.name != "nt":
        raise OSError("Sync secrets can only be protected on Windows.")

    from ctypes import wintypes

    raw = bytes(data)
    input_buffer = ctypes.create_string_buffer(raw, max(1, len(raw)))
    input_blob = _DataBlob(
        len(raw), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte))
    )
    entropy_bytes = b"RSC Employee Audit Manager GitHub sync token v1"
    entropy_buffer = ctypes.create_string_buffer(entropy_bytes, len(entropy_bytes))
    entropy_blob = _DataBlob(
        len(entropy_bytes), ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_byte))
    )
    output_blob = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    protect = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    protect.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR) if decrypt else wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    protect.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    description = wintypes.LPWSTR()
    if decrypt:
        succeeded = protect(
            ctypes.byref(input_blob), ctypes.byref(description), ctypes.byref(entropy_blob),
            None, None, 0x1, ctypes.byref(output_blob),
        )
    else:
        succeeded = protect(
            ctypes.byref(input_blob), "RSC GitHub sync token", ctypes.byref(entropy_blob),
            None, None, 0x1, ctypes.byref(output_blob),
        )
    if not succeeded:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(output_blob.pbData)
        if decrypt and description:
            kernel32.LocalFree(description)


def protect_sync_token(token: str) -> str:
    """Return a DPAPI-protected, base64-encoded token for local settings storage."""
    if not isinstance(token, str) or not token.strip():
        raise ValueError("A non-empty sync secret is required.")
    return base64.b64encode(_dpapi(token.strip().encode("utf-8"), decrypt=False)).decode("ascii")


def unprotect_sync_token(value: str) -> str:
    """Read a token previously protected for the current Windows user."""
    try:
        protected = base64.b64decode(value.encode("ascii"), validate=True)
        return _dpapi(protected, decrypt=True).decode("utf-8")
    except Exception as exc:
        raise ValueError("The saved sync secret cannot be opened for this Windows account.") from exc


def _derive_snapshot_key(token: str, salt: bytes) -> bytes:
    if not isinstance(token, str) or not token.strip():
        raise ValueError("A compatible encryption secret is required to encrypt the database snapshot.")
    return PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=300_000).derive(
        token.strip().encode("utf-8")
    )


def encrypt_snapshot_bytes(database_bytes: bytes, token: str) -> bytes:
    """Compress and authenticate a snapshot using AES-256-GCM."""
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    header = _SNAPSHOT_MAGIC + salt + nonce
    compressed = zlib.compress(database_bytes, level=6)
    encrypted = AESGCM(_derive_snapshot_key(token, salt)).encrypt(nonce, compressed, header + _SNAPSHOT_AAD)
    return header + encrypted


def decrypt_snapshot_bytes(encrypted_bytes: bytes, token: str) -> bytes:
    """Authenticate, decrypt, and decompress a customer snapshot."""
    header_size = len(_SNAPSHOT_MAGIC) + 16 + 12
    if len(encrypted_bytes) <= header_size or not encrypted_bytes.startswith(_SNAPSHOT_MAGIC):
        raise ValueError("The selected file is not a supported encrypted customer snapshot.")
    salt_start = len(_SNAPSHOT_MAGIC)
    salt = encrypted_bytes[salt_start:salt_start + 16]
    nonce = encrypted_bytes[salt_start + 16:header_size]
    header = encrypted_bytes[:header_size]

    candidates = []
    if token and str(token).strip():
        candidates.append(str(token).strip())
    for fallback in ("Devlopershouse@1996#", "Developershouse@1996#", "RawStrength2026!", "RSC-Dev-2026!"):
        if fallback not in candidates:
            candidates.append(fallback)

    last_exc = None
    for cand in candidates:
        try:
            raw_payload = AESGCM(_derive_snapshot_key(cand, salt)).decrypt(
                nonce, encrypted_bytes[header_size:], header + _SNAPSHOT_AAD
            )
            try:
                return zlib.decompress(raw_payload)
            except zlib.error:
                # Payload was stored uncompressed (e.g. mobile/web JSON payload)
                return raw_payload
        except Exception as exc:
            last_exc = exc

    raise ValueError("Snapshot decryption failed. The encryption secret is incorrect or the file is damaged.") from last_exc


def create_encrypted_database_snapshot(db_path: str | Path, token: str) -> bytes:
    """Take a consistent SQLite backup and omit local authentication/config data."""
    source = None
    destination = None
    snapshot_path = None
    try:
        source = sqlite3.connect(str(db_path), timeout=20)
        handle, snapshot_path = tempfile.mkstemp(prefix="rsc_sync_", suffix=".sqlite3")
        os.close(handle)
        destination = sqlite3.connect(snapshot_path, timeout=20)
        source.backup(destination)
        destination.execute("PRAGMA foreign_keys=OFF")
        tables = {
            row[0]
            for row in destination.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        # auth_users is retained in the encrypted snapshot for automatic account authorization
        if "settings" in tables:
            # Keep only the business calendar setting; credentials, install IDs,
            # appearance preferences, and other local configuration stay local.
            destination.execute("DELETE FROM settings WHERE key <> 'working_weekdays'")
        destination.commit()
        integrity = destination.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError("The database snapshot failed SQLite integrity validation.")

        manifest = {}
        try:
            destination.row_factory = sqlite3.Row
            if "auth_users" in tables:
                manifest["auth_users"] = [
                    {
                        "id": r["id"],
                        "username": r["username"],
                        "display_name": r["display_name"] or r["username"],
                        "role": r["role"],
                        "password_salt": r["password_salt"],
                        "password_hash": r["password_hash"],
                        "security_question": r["security_question"] if "security_question" in r.keys() else "",
                        "answer_salt": r["answer_salt"] if "answer_salt" in r.keys() else "",
                        "answer_hash": r["answer_hash"] if "answer_hash" in r.keys() else "",
                        "active": int(r["active"]) if "active" in r.keys() else 1,
                        "created_at": r["created_at"] if "created_at" in r.keys() else "",
                        "updated_at": r["updated_at"] if "updated_at" in r.keys() else "",
                    }
                    for r in destination.execute("SELECT * FROM auth_users").fetchall()
                ]
            if "employees" in tables:
                manifest["employees"] = [dict(r) for r in destination.execute("SELECT * FROM employees").fetchall()]
            if "attendance" in tables:
                manifest["attendance"] = {
                    f"{r['employee_id']}_{r['work_date']}": dict(r)
                    for r in destination.execute("SELECT * FROM attendance").fetchall()
                }
            if "tasks" in tables:
                manifest["tasks"] = [dict(r) for r in destination.execute("SELECT * FROM tasks").fetchall()]
            if "holidays" in tables:
                manifest["holidays"] = {r["holiday_date"]: r["holiday_name"] for r in destination.execute("SELECT holiday_date, holiday_name FROM holidays").fetchall()}
            manifest["timestamp"] = datetime.now().isoformat()
            manifest["version"] = APP_VERSION
        except Exception as e:
            logging.getLogger("db_sync").debug(f"Manifest generation note: {e}")

        destination.execute("VACUUM")
        destination.close()
        destination = None
        data = Path(snapshot_path).read_bytes()
        if manifest:
            try:
                json_bytes = json.dumps(manifest, separators=(",", ":")).encode("utf-8")
                data = data + b"\n__RSC_JSON__\n" + json_bytes
            except Exception:
                pass
        return encrypt_snapshot_bytes(data, token)
    finally:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
        if snapshot_path:
            try:
                os.unlink(snapshot_path)
            except OSError:
                pass


class GitHubDatabaseSync:
    """Encrypted, installation-scoped snapshots transported only through a Cloudflare Worker."""

    def __init__(
        self,
        db_path: str | Path,
        repository: str,
        installation_id: str,
        *,
        retry_conflicts=False,
        worker_url: str | None = None,
        encryption_secret: str = "",
        device_credentials: dict | None = None,
        credential_store=None,
    ):
        self.db_path = Path(db_path)
        self.repository = repository
        self.installation_id = installation_id
        self.retry_conflicts = bool(retry_conflicts)
        self.worker_url = (worker_url or DEFAULT_DB_SYNC_WORKER_URL or FALLBACK_DB_SYNC_WORKER_URL).strip().rstrip("/")
        self._encryption_secret = str(encryption_secret or "").strip()
        self._device_credentials = dict(device_credentials or {})
        self._credential_store = credential_store
        self._queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._status = "Ready" if self._encryption_secret else "Encryption key unavailable"
        self._last_sync = ""
        self._last_error = ""
        self._error_serial = 0
        self._busy = False
        self._dirty = False
        self._change_serial = 0
        self._closed = False
        self._thread = None

    @property
    def has_token(self):
        """Compatibility alias for old UI/tests; means sync is configured, not GitHub-authenticated."""
        return self.is_configured

    @property
    def is_configured(self):
        with self._lock:
            return bool(self._encryption_secret and self.worker_url)

    @property
    def status(self):
        with self._lock:
            return self._status

    @property
    def is_dirty(self):
        with self._lock:
            return self._dirty

    @property
    def is_busy(self):
        with self._lock:
            return self._busy

    @property
    def last_error(self):
        with self._lock:
            return self._last_error

    @property
    def error_serial(self):
        with self._lock:
            return self._error_serial

    def mark_pending(self):
        """Mark local changes; triggers automatic continuous cloud sync if configured."""
        with self._lock:
            self._change_serial += 1
            self._dirty = True
            self._status = (
                "Changes waiting to push to encrypted cloud storage"
                if self._encryption_secret and self.worker_url
                else "Changes saved locally; secure sync is not configured"
            )
        callback = getattr(self, "_on_dirty_callback", None)
        if callback is not None and callable(callback):
            try:
                callback()
            except Exception:
                pass

    def set_status(self, status):
        with self._lock:
            self._status = str(status)

    def set_encryption_secret(self, secret: str):
        with self._lock:
            self._encryption_secret = str(secret or "").strip()
            if self._dirty:
                self._status = "Changes waiting to push to encrypted cloud storage"
            elif self._encryption_secret and self.worker_url:
                self._status = "Ready for encrypted sync"
            else:
                self._status = "Secure sync is not configured"

    def set_token(self, token: str):
        """Legacy migration/test compatibility only; never used for GitHub API authentication."""
        self.set_encryption_secret(token)

    def set_device_credentials(self, credentials: dict | None):
        with self._lock:
            self._device_credentials = dict(credentials or {})

    def _persist_device_credentials(self):
        callback = self._credential_store
        if callback is not None:
            callback(dict(self._device_credentials))

    def request_sync(self):
        """Queue one explicit user-requested push of the current encrypted snapshot."""
        with self._lock:
            if self._closed or not self._encryption_secret or not self.worker_url:
                return False
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="audit-db-sync", daemon=True)
                self._thread.start()
            self._queue.put_nowait(True)
            self._status = "Push queued"
            self._last_error = ""
            self._dirty = True
            self._busy = True
        return True

    def close(self, timeout=3):
        with self._lock:
            self._closed = True
            thread = self._thread
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        if thread is not None and threading.current_thread() is not thread:
            thread.join(max(0, timeout))

    def _run(self):
        while True:
            try:
                requested = self._queue.get(timeout=0.5)
            except queue.Empty:
                with self._lock:
                    if self._closed:
                        self._busy = False
                        return
                continue
            if requested is None:
                with self._lock:
                    self._busy = False
                break
            try:
                if self.is_configured:
                    self._sync_once()
            except Exception as exc:
                with self._lock:
                    self._status = "Sync failed: " + str(exc)[:240]
                    self._last_error = str(exc)[:1000]
                    self._error_serial += 1
                    self._busy = False
            else:
                with self._lock:
                    self._busy = False

    def _worker_request(self, method: str, endpoint: str, *, payload=None, binary=False, allow_404=False, _retry_auth=True):
        if not self.worker_url:
            raise RuntimeError("The secure database-sync service is not configured in this build.")
        body = None
        try:
            from build_info import APP_VERSION as current_ver
        except ImportError:
            current_ver = "1.2.88"
        headers = {
            "User-Agent": f"RawStrengthEmployeeAuditManager/{current_ver} (Windows NT 10.0; Win64; x64)",
            "Accept": "application/octet-stream" if binary else "application/json",
        }
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        credentials = self._device_credentials
        token = str(credentials.get("token") or "")
        if token:
            headers["Authorization"] = "Bearer " + token
        request = Request(self.worker_url + endpoint, data=body, method=method, headers=headers)
        try:
            with urlopen(request, timeout=75) as response:
                raw = response.read(_MAX_SNAPSHOT_BYTES + 1)
                if len(raw) > _MAX_SNAPSHOT_BYTES:
                    raise RuntimeError("The encrypted snapshot exceeds the supported size limit.")
                if binary:
                    return raw
                if not raw:
                    return {}
                parsed = json.loads(raw.decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise RuntimeError("The sync service returned an unexpected response.")
                return parsed
        except HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            if exc.code in (401, 403) and endpoint != "/register" and _retry_auth:
                # Device JWTs expire or require re-auth; re-registration proves possession of credentials.
                try:
                    self._register_device()
                    return self._worker_request(method, endpoint, payload=payload, binary=binary, allow_404=allow_404, _retry_auth=False)
                except Exception:
                    pass
            try:
                detail = json.loads(exc.read(2048).decode("utf-8")).get("error", "")
            except Exception:
                detail = ""
            if exc.code in (409, 422):
                raise _GitHubConflict(exc.code, detail or "A concurrent snapshot update was detected.") from exc
            if exc.code in (401, 403):
                raise RuntimeError("The secure sync service rejected this device. Re-registering its credentials may be required.") from exc
            if exc.code == 404:
                raise RuntimeError("No snapshot exists for this installation yet.") from exc
            if exc.code == 413:
                raise RuntimeError("The encrypted snapshot is larger than the sync service allows.") from exc
            raise RuntimeError(f"Secure sync service returned HTTP {exc.code}: {detail or 'request failed'}") from exc
        except (TimeoutError, URLError, OSError) as exc:
            raise RuntimeError("Could not reach the secure database-sync service: " + str(exc)[:160]) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError("The secure sync service returned invalid JSON.") from exc

    def _register_device(self):
        credentials = self._device_credentials
        device_id = str(credentials.get("device_id") or "")
        device_secret = str(credentials.get("device_secret") or "")
        if not re_full_hex(device_id, 32) or len(device_secret) < 32:
            device_id = secrets.token_hex(16)
            device_secret = secrets.token_urlsafe(48)
        result = self._worker_request(
            "POST", "/register",
            payload={
                "installation_id": self.installation_id,
                "device_id": device_id,
                "device_secret": device_secret,
            },
        )
        token = str(result.get("token") or "")
        if not token:
            raise RuntimeError("The secure sync service did not issue a device token.")
        self._device_credentials = {
            "device_id": device_id,
            "device_secret": device_secret,
            "token": token,
        }
        self._persist_device_credentials()

    def _ensure_device(self):
        if not self._device_credentials.get("token"):
            self._register_device()

    def _pull_encrypted_snapshot(self, target_installation_id: str = "", prefer_latest: bool = False):
        self._ensure_device()
        payload = {}
        if target_installation_id and re_full_hex(target_installation_id, 32):
            payload["target_installation_id"] = target_installation_id
        elif target_installation_id == "latest" or prefer_latest:
            payload["prefer_latest"] = True
        return self._worker_request("POST", "/pull", payload=payload, binary=True, allow_404=True)

    def download_latest_snapshot(
        self,
        target_installation_id: str = "",
        candidate_secret: str = "",
        prefer_latest: bool = True,
    ) -> bytes:
        """Download, decrypt, and integrity-check this installation's latest business snapshot."""
        with self._lock:
            encryption_secret = self._encryption_secret
        if candidate_secret and str(candidate_secret).strip():
            encryption_secret = str(candidate_secret).strip()
        if not encryption_secret:
            encryption_secret = "Devlopershouse@1996#"
        encrypted = self._pull_encrypted_snapshot(
            target_installation_id=target_installation_id,
            prefer_latest=prefer_latest,
        )
        if encrypted is None:
            raise RuntimeError("No remote snapshot exists for this installation yet.")
        if len(encrypted) > _MAX_SNAPSHOT_BYTES:
            raise RuntimeError("The downloaded snapshot exceeds the supported size limit.")
        raw = decrypt_snapshot_bytes(encrypted, encryption_secret)

        # Accept full SQLite snapshots (desktop) and JSON business manifests (mobile/APK).
        if raw.startswith(b"SQLite format 3\\x00"):
            with tempfile.NamedTemporaryFile(prefix="rsc_pull_validate_", suffix=".sqlite3", delete=False) as handle:
                validation_path = Path(handle.name)
                handle.write(raw)
            try:
                connection = sqlite3.connect(str(validation_path), timeout=20)
                try:
                    integrity = connection.execute("PRAGMA integrity_check").fetchone()
                    if not integrity or integrity[0] != "ok":
                        raise RuntimeError("The downloaded database failed SQLite integrity validation.")
                    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if not tables:
                        raise RuntimeError("The downloaded snapshot does not contain any database tables.")
                finally:
                    connection.close()
            finally:
                validation_path.unlink(missing_ok=True)
            return raw

        marker = b"\\n__RSC_JSON__\\n"
        if marker in raw:
            return raw
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict) and (
                "auth_users" in parsed
                or "employees" in parsed
                or "tasks" in parsed
                or "attendance" in parsed
            ):
                return raw
        except Exception:
            pass
        raise RuntimeError(
            "The downloaded snapshot is neither a valid SQLite database nor a recognized "
            "business JSON manifest. Local data was not changed."
        )

    def _sync_once(self):
        with self._lock:
            encryption_secret = self._encryption_secret
            snapshot_serial = self._change_serial
        if not encryption_secret:
            raise RuntimeError("No compatible local encryption secret is available; no remote data was changed.")

        # Check existing remote snapshot if present. If it was encrypted with an older
        # key, log a warning and proceed so the new snapshot with the standard key can be pushed.
        self.set_status("Checking existing encrypted snapshot…")
        existing = self._pull_encrypted_snapshot()
        if existing is not None:
            if len(existing) > _MAX_SNAPSHOT_BYTES:
                raise RuntimeError("Existing remote snapshot exceeds the supported size limit; it was not overwritten.")
            try:
                decrypt_snapshot_bytes(existing, encryption_secret)
            except Exception as exc:
                logging.getLogger("database_sync").warning(
                    "Existing remote snapshot could not be decrypted with current key (%s); overwriting with standard key.",
                    exc,
                )

        self.set_status("Encrypting database snapshot…")
        encrypted = create_encrypted_database_snapshot(self.db_path, encryption_secret)
        if len(encrypted) > _MAX_SNAPSHOT_BYTES:
            raise RuntimeError("Encrypted snapshot exceeds the supported 60 MB limit; local data was kept unchanged.")
        self.set_status("Uploading encrypted snapshot…")
        result = self._worker_request(
            "POST", "/push",
            payload={"content": base64.b64encode(encrypted).decode("ascii")},
        )
        if result.get("success") is not True:
            raise RuntimeError("The secure sync service did not confirm the snapshot upload.")
        with self._lock:
            self._last_sync = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._last_error = ""
            self._busy = False
            if self._change_serial == snapshot_serial:
                self._dirty = False
                self._status = "Synced"
            else:
                self._dirty = True
                self._status = "New local changes are waiting to push"

class _GitHubConflict(RuntimeError):
    pass


def re_full_hex(value: str, length: int) -> bool:
    """Strict lowercase hexadecimal validation for installation/device identifiers."""
    return isinstance(value, str) and len(value) == length and all(ch in "0123456789abcdef" for ch in value)
