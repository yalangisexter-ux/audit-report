"""Encrypted, asynchronous snapshots of customer business data to GitHub."""

from __future__ import annotations

import base64
import ctypes
import json
import os
import queue
import secrets
import sqlite3
import tempfile
import threading
import time
import zlib
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


_SNAPSHOT_MAGIC = b"RSCDB1"
_SNAPSHOT_AAD = b"RawStrengthEmployeeAuditManager:encrypted-customer-database:v1"
_MAX_SNAPSHOT_BYTES = 60 * 1024 * 1024
_SYNC_DEBOUNCE_SECONDS = 2.0


class _SyncPaused(RuntimeError):
    """Raised when Developer Mode pauses an upload before it updates main."""


class SyncableSQLiteConnection(sqlite3.Connection):
    """SQLite connection that notifies the sync queue after successful commits."""

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
        raise OSError("GitHub sync credentials can only be protected on Windows.")

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
        raise ValueError("Enter a GitHub token first.")
    return base64.b64encode(_dpapi(token.strip().encode("utf-8"), decrypt=False)).decode("ascii")


def unprotect_sync_token(value: str) -> str:
    """Read a token previously protected for the current Windows user."""
    try:
        protected = base64.b64decode(value.encode("ascii"), validate=True)
        return _dpapi(protected, decrypt=True).decode("utf-8")
    except Exception as exc:
        raise ValueError("The saved GitHub token cannot be opened for this Windows account.") from exc


def _derive_snapshot_key(token: str, salt: bytes) -> bytes:
    if not isinstance(token, str) or not token.strip():
        raise ValueError("A GitHub token is required to encrypt the database snapshot.")
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
    try:
        compressed = AESGCM(_derive_snapshot_key(token, salt)).decrypt(
            nonce, encrypted_bytes[header_size:], header + _SNAPSHOT_AAD
        )
        return zlib.decompress(compressed)
    except Exception as exc:
        raise ValueError("Snapshot decryption failed. Check the GitHub token and file integrity.") from exc


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
        if "auth_users" in tables:
            destination.execute("DROP TABLE auth_users")
        if "settings" in tables:
            # Keep only the business calendar setting; credentials, install IDs,
            # appearance preferences, and other local configuration stay local.
            destination.execute("DELETE FROM settings WHERE key <> 'working_weekdays'")
        destination.commit()
        integrity = destination.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError("The database snapshot failed SQLite integrity validation.")
        destination.execute("VACUUM")
        destination.close()
        destination = None
        data = Path(snapshot_path).read_bytes()
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
    """Debounced background snapshots, committed to a unique installation path."""

    def __init__(
        self,
        db_path: str | Path,
        repository: str,
        installation_id: str,
        *,
        paused=False,
        auto_retry=True,
        retry_conflicts=True,
        remote_directory="customer-data",
    ):
        self.db_path = Path(db_path)
        self.repository = repository
        self.installation_id = installation_id
        self.auto_retry = bool(auto_retry)
        self.retry_conflicts = bool(retry_conflicts)
        self.remote_directory = str(remote_directory).strip("/") or "customer-data"
        self._api_base = f"https://api.github.com/repos/{repository}"
        self._queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        # Serializes the final ref update against enabling Developer Mode, so
        # once pause is acknowledged, no in-flight upload can advance main.
        self._ref_update_lock = threading.Lock()
        self._token = ""
        self._status = "Not configured"
        self._last_sync = ""
        self._last_error = ""
        self._error_serial = 0
        self._busy = False
        self._developer_paused = bool(paused)
        self._closed = False
        self._thread = None
        self._retry_attempt = 0
        self._retry_timer = None

    @property
    def has_token(self):
        with self._lock:
            return bool(self._token)

    @property
    def status(self):
        with self._lock:
            if self._developer_paused:
                return "Developer Mode is on; GitHub uploads are paused"
            if self._last_sync and self._status == "Synced":
                return f"Last synced {self._last_sync}"
            return self._status

    @property
    def is_paused(self):
        with self._lock:
            return self._developer_paused

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

    def token_for_local_sync(self):
        """Return the configured token to another in-process sync service."""
        with self._lock:
            return self._token

    def set_paused(self, paused):
        """Pause or resume GitHub writes; resuming waits for a future DB edit."""
        retry_timer = None
        with self._ref_update_lock:
            with self._lock:
                self._developer_paused = bool(paused)
                if paused:
                    retry_timer = self._retry_timer
                    self._retry_timer = None
                else:
                    self._status = "Ready to sync" if self._token else "Not configured"
        if retry_timer is not None:
            retry_timer.cancel()

    def set_status(self, status):
        with self._lock:
            if self._developer_paused:
                return
            self._status = str(status)

    def set_token(self, token: str, *, sync_now=False):
        with self._lock:
            self._token = str(token or "").strip()
            if not self._developer_paused:
                self._status = "Ready to sync" if self._token else "Not configured"
        if self._token and sync_now:
            self.request_sync(force=True)

    def request_sync(self, force=False):
        timer = None
        with self._lock:
            if self._closed or self._developer_paused or not self._token:
                return
            timer = self._retry_timer
            self._retry_timer = None
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="github-db-sync", daemon=True)
                self._thread.start()
            self._queue.put_nowait(bool(force))
            self._status = "Sync queued"
            self._last_error = ""
            self._busy = True
        if timer is not None:
            timer.cancel()

    def _schedule_retry(self):
        old_timer = None
        with self._lock:
            if self._closed or self._developer_paused or not self._token:
                return
            self._retry_attempt = min(self._retry_attempt + 1, 5)
            delay = min(15 * (2 ** (self._retry_attempt - 1)), 300)
            old_timer = self._retry_timer
            timer = threading.Timer(delay, self.request_sync, kwargs={"force": True})
            timer.daemon = True
            self._retry_timer = timer
            timer.start()
        if old_timer is not None:
            old_timer.cancel()

    def close(self, timeout=3):
        with self._lock:
            self._closed = True
            retry_timer = self._retry_timer
            self._retry_timer = None
            thread = self._thread
        if retry_timer is not None:
            retry_timer.cancel()
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        if thread is not None and threading.current_thread() is not thread:
            thread.join(max(0, timeout))

    def _run(self):
        stopping = False
        while not stopping:
            try:
                force = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if force is None:
                with self._lock:
                    self._busy = False
                break
            deadline = time.monotonic() if force else time.monotonic() + _SYNC_DEBOUNCE_SECONDS
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    queued = self._queue.get(timeout=remaining)
                    if queued is None:
                        stopping = True
                        break
                    force = force or queued
                    if force:
                        break
                    deadline = time.monotonic() + _SYNC_DEBOUNCE_SECONDS
                except queue.Empty:
                    break
            if stopping:
                with self._lock:
                    self._busy = False
                break
            try:
                if self.has_token:
                    self._sync_once()
            except _SyncPaused:
                # Pausing intentionally drops this snapshot. Turning sync back
                # on must not publish Developer Mode edits by itself.
                with self._lock:
                    self._busy = False
                continue
            except Exception as exc:
                # Never include request headers or token values in status text.
                with self._lock:
                    self._status = "Sync failed: " + str(exc)[:240]
                    self._last_error = str(exc)[:1000]
                    self._error_serial += 1
                    self._busy = False
                if self.auto_retry:
                    self._schedule_retry()
            else:
                # Keep the busy state correct even if a test or alternate
                # implementation returns without updating it itself.
                with self._lock:
                    self._busy = False

    def _request_json(self, method: str, endpoint: str, token: str, payload=None):
        url = self._api_base + endpoint
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "RawStrengthEmployeeAuditManager",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with urlopen(request, timeout=25) as response:
                raw = response.read()
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read(4096).decode("utf-8")).get("message", "")
            except Exception:
                detail = ""
            if exc.code in (409, 422):
                raise _GitHubConflict(exc.code, detail or "GitHub rejected a concurrent update.") from exc
            if exc.code in (401, 403):
                raise RuntimeError("GitHub rejected the token or it lacks repository Contents write access.") from exc
            if exc.code == 404:
                raise RuntimeError("The configured repository or main branch could not be found.") from exc
            raise RuntimeError(f"GitHub returned HTTP {exc.code}: {detail or 'request failed'}") from exc
        except (TimeoutError, URLError, OSError) as exc:
            raise RuntimeError("Could not reach GitHub: " + str(exc)[:160]) from exc
        if not raw:
            return {}
        try:
            result = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("GitHub returned an invalid response.") from exc
        if not isinstance(result, dict):
            raise RuntimeError("GitHub returned an unexpected response.")
        return result

    def _sync_once(self):
        with self._lock:
            if self._developer_paused:
                raise _SyncPaused()
            token = self._token
        if not token:
            return
        self.set_status("Encrypting database snapshot…")
        encrypted = create_encrypted_database_snapshot(self.db_path, token)
        if len(encrypted) > _MAX_SNAPSHOT_BYTES:
            raise RuntimeError("Encrypted snapshot exceeds GitHub's 60 MB sync limit; local data was kept unchanged.")
        content = base64.b64encode(encrypted).decode("ascii")
        path = f"{self.remote_directory}/{self.installation_id}.db.enc"
        for attempt in range(4):
            self.set_status("Uploading encrypted snapshot to GitHub…")
            ref = self._request_json("GET", "/git/ref/heads/main", token)
            head_sha = str(ref.get("object", {}).get("sha") or "")
            if not head_sha:
                raise RuntimeError("GitHub did not return the current main branch commit.")
            head_commit = self._request_json("GET", f"/git/commits/{head_sha}", token)
            base_tree = str(head_commit.get("tree", {}).get("sha") or "")
            if not base_tree:
                raise RuntimeError("GitHub did not return the main branch tree.")
            blob = self._request_json(
                "POST", "/git/blobs", token,
                {"content": content, "encoding": "base64"},
            )
            blob_sha = str(blob.get("sha") or "")
            if not blob_sha:
                raise RuntimeError("GitHub did not create the encrypted snapshot blob.")
            tree = self._request_json(
                "POST", "/git/trees", token,
                {
                    "base_tree": base_tree,
                    "tree": [{"path": path, "mode": "100644", "type": "blob", "sha": blob_sha}],
                },
            )
            tree_sha = str(tree.get("sha") or "")
            if not tree_sha:
                raise RuntimeError("GitHub did not create the snapshot tree.")
            commit = self._request_json(
                "POST", "/git/commits", token,
                {
                    "message": "Update encrypted business database snapshot",
                    "tree": tree_sha,
                    "parents": [head_sha],
                },
            )
            commit_sha = str(commit.get("sha") or "")
            if not commit_sha:
                raise RuntimeError("GitHub did not create the snapshot commit.")
            try:
                with self._ref_update_lock:
                    with self._lock:
                        if self._developer_paused:
                            raise _SyncPaused()
                    self._request_json(
                        "PATCH", "/git/refs/heads/main", token,
                        {"sha": commit_sha, "force": False},
                    )
                    with self._lock:
                        self._status = "Synced"
                        self._last_sync = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self._last_error = ""
                        self._busy = False
                        self._retry_attempt = 0
                        retry_timer = self._retry_timer
                        self._retry_timer = None
                if retry_timer is not None:
                    retry_timer.cancel()
                return
            except _GitHubConflict:
                if not self.retry_conflicts or attempt == 3:
                    raise RuntimeError(
                        "GitHub sync conflict: the main branch changed while the snapshot was being "
                        "uploaded. No local database data was changed. Try syncing again after the "
                        "repository updates settle."
                    )


class _GitHubConflict(RuntimeError):
    pass
