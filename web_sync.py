"""Encrypted bidirectional snapshot sync for the Render web working copy.

The desktop EXE remains unchanged. Render uses a persistent SQLite working copy
and the existing installation-scoped Cloudflare Worker transport.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from database_sync import GitHubDatabaseSync

DEFAULT_WORKER = "https://raw-strength-audit-db-sync.yalangisexter.workers.dev"
DEFAULT_INSTALLATION = "c4cf201d3c68e2fcaf60aa05fd423d9a"
REQUIRED_TABLES = {"auth_users", "employees", "tasks"}


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}


def validate_snapshot(path: Path) -> dict:
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=20)
    try:
        check = db.execute("PRAGMA integrity_check").fetchone()
        if not check or check[0] != "ok":
            raise ValueError("Remote database failed SQLite integrity validation")
        missing = REQUIRED_TABLES - _tables(db)
        if missing:
            raise ValueError("Remote database is missing required tables: " + ", ".join(sorted(missing)))
        return {
            "auth_users": db.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0],
            "employees": db.execute("SELECT COUNT(*) FROM employees").fetchone()[0],
            "tasks": db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
        }
    finally:
        db.close()


def merge_snapshot_databases(local_path: Path, remote_path: Path) -> dict:
    """Union remote records into the local DB; newer updated_at rows win.

    Local-only rows are never deleted. Tables without primary keys are skipped.
    This deliberately favors preservation over destructive snapshot replacement.
    """
    local = sqlite3.connect(str(local_path), timeout=30)
    remote = sqlite3.connect(f"file:{remote_path}?mode=ro", uri=True, timeout=30)
    local.row_factory = sqlite3.Row
    remote.row_factory = sqlite3.Row
    inserted = updated = conflicts = 0
    try:
        local.execute("PRAGMA foreign_keys=OFF")
        local.execute("BEGIN IMMEDIATE")
        for table in sorted(_tables(local) & _tables(remote)):
            li = local.execute(f"PRAGMA table_info({_q(table)})").fetchall()
            ri = remote.execute(f"PRAGMA table_info({_q(table)})").fetchall()
            remote_cols = {r["name"] for r in ri}
            cols = [r["name"] for r in li if r["name"] in remote_cols]
            pks = [r["name"] for r in sorted(li, key=lambda x: x["pk"] or 999) if r["pk"] and r["name"] in remote_cols]
            if not cols or not pks:
                continue
            col_sql = ",".join(_q(c) for c in cols)
            marks = ",".join("?" for _ in cols)
            for row in remote.execute(f"SELECT {col_sql} FROM {_q(table)}"):
                values = dict(row)
                if table == "auth_users" and "username" in cols:
                    existing = local.execute(
                        f"SELECT * FROM {_q(table)} WHERE username=? COLLATE BINARY LIMIT 1",
                        (values.get("username"),),
                    ).fetchone()
                else:
                    where = " AND ".join(f"{_q(c)} IS ?" for c in pks)
                    existing = local.execute(
                        f"SELECT * FROM {_q(table)} WHERE {where}",
                        tuple(values.get(c) for c in pks),
                    ).fetchone()
                if existing is None:
                    try:
                        local.execute(
                            f"INSERT OR IGNORE INTO {_q(table)} ({col_sql}) VALUES ({marks})",
                            tuple(values.get(c) for c in cols),
                        )
                        inserted += int(local.execute("SELECT changes()").fetchone()[0] > 0)
                    except sqlite3.Error:
                        conflicts += 1
                    continue
                if "updated_at" not in cols:
                    continue
                if str(values.get("updated_at") or "") <= str(existing["updated_at"] or ""):
                    continue
                updates = [c for c in cols if c not in pks]
                if table == "auth_users":
                    updates = [c for c in updates if c != "id"]
                    where = "username=? COLLATE BINARY"
                    keys = (values.get("username"),)
                else:
                    where = " AND ".join(f"{_q(c)} IS ?" for c in pks)
                    keys = tuple(values.get(c) for c in pks)
                if updates:
                    local.execute(
                        f"UPDATE {_q(table)} SET " + ",".join(f"{_q(c)}=?" for c in updates) + f" WHERE {where}",
                        tuple(values.get(c) for c in updates) + keys,
                    )
                    updated += int(local.execute("SELECT changes()").fetchone()[0] > 0)
        local.commit()
        return {"inserted": inserted, "updated": updated, "conflicts": conflicts}
    except Exception:
        local.rollback()
        raise
    finally:
        remote.close()
        local.close()


class WebDatabaseSync:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.worker_url = (os.environ.get("DB_SYNC_WORKER_URL") or DEFAULT_WORKER).strip().rstrip("/")
        self.installation_id = (os.environ.get("DB_SYNC_INSTALLATION_ID") or DEFAULT_INSTALLATION).strip().lower()
        self.secret = (os.environ.get("DB_SYNC_ENCRYPTION_SECRET") or "").strip()
        self.credentials_path = self.db_path.parent / "web_sync_device.json"
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.poll_thread = None
        self.remote_digest = ""
        self.last_pull = {"ok": False, "error": "Sync has not run", "auth_users": 0, "employees": 0, "tasks": 0}
        self.status = "Encrypted sync is not configured"
        self.sync = None
        self.configured = bool(self.secret and re.fullmatch(r"[0-9a-f]{32}", self.installation_id) and self.worker_url.startswith("https://"))
        if self.configured:
            try:
                credentials = json.loads(self.credentials_path.read_text(encoding="utf-8"))
                if not isinstance(credentials, dict):
                    credentials = {}
            except Exception:
                credentials = {}
            self.sync = GitHubDatabaseSync(
                self.db_path, "yalangisexter-ux/audit-report", self.installation_id,
                worker_url=self.worker_url, encryption_secret=self.secret,
                device_credentials=credentials, credential_store=self._save_credentials,
            )
            self.sync._on_dirty_callback = lambda: self.sync.schedule_sync(2.0)
            self.push_impl = self.sync._sync_once
            self.sync._sync_once = self._sync_once

    def _save_credentials(self, credentials):
        temp = self.credentials_path.with_suffix(".tmp")
        temp.write_text(json.dumps(credentials, separators=(",", ":")), encoding="utf-8")
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass
        os.replace(temp, self.credentials_path)

    def _download(self) -> bytes:
        if not self.sync:
            raise RuntimeError("Set DB_SYNC_ENCRYPTION_SECRET in Render to enable encrypted sync.")
        payload = self.sync.download_latest_snapshot(
            target_installation_id=self.installation_id,
            candidate_secret=self.secret, prefer_latest=False,
        )
        if not payload.startswith(b"SQLite format 3\x00"):
            raise ValueError("Worker snapshot is not a SQLite database")
        return payload

    def _merge_payload(self, payload: bytes) -> dict:
        temp = self.db_path.with_name(self.db_path.name + ".remote-check")
        try:
            temp.write_bytes(payload)
            stats = validate_snapshot(temp)
            backup_dir = self.db_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            if self.db_path.is_file():
                backup_path = backup_dir / ("pre-sync-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".db")
                source = sqlite3.connect(str(self.db_path), timeout=30)
                backup = sqlite3.connect(str(backup_path), timeout=30)
                try:
                    source.backup(backup)
                finally:
                    backup.close()
                    source.close()
            result = merge_snapshot_databases(self.db_path, temp)
            self.last_pull = {"ok": True, "error": "", **stats, **result}
            return result
        finally:
            temp.unlink(missing_ok=True)

    def _pull_merge(self) -> dict:
        payload = self._download()
        digest = hashlib.sha256(payload).hexdigest()
        if digest == self.remote_digest:
            return {"changed": False, "inserted": 0, "updated": 0, "conflicts": 0}
        merged = self._merge_payload(payload)
        self.remote_digest = digest
        return {"changed": bool(merged["inserted"] or merged["updated"]), **merged}

    def _sync_once(self):
        # Merge the newest remote snapshot before publishing local commits.
        try:
            self._pull_merge()
        except RuntimeError as exc:
            if "No remote snapshot exists" not in str(exc):
                raise
        self.push_impl()
        self.status = "Synced"

    def bootstrap(self) -> bool:
        if not self.configured:
            self.status = "Sync disabled: DB_SYNC_ENCRYPTION_SECRET is missing"
            self.last_pull["error"] = "Set Render DB_SYNC_ENCRYPTION_SECRET to the same encryption secret used by the desktop sync."
            return False
        try:
            result = self._pull_merge()
            self.status = "Connected to encrypted installation snapshot"
            if result["changed"]:
                self.sync.mark_pending()
                self.sync.schedule_sync(3.0)
            return True
        except RuntimeError as exc:
            if "No remote snapshot exists" in str(exc):
                self.status = "Connected; no remote snapshot exists yet"
                self.last_pull = {"ok": True, "error": "No remote snapshot yet; the first web account or data save will publish it.", "auth_users": 0, "employees": 0, "tasks": 0}
                return False
            self.status = "Initial pull failed"
            self.last_pull["error"] = str(exc)[:240]
            return False
        except Exception as exc:
            self.status = "Initial pull failed"
            self.last_pull["error"] = str(exc)[:240]
            return False

    def start_polling(self, interval_seconds: int = 60):
        if not self.configured or self.poll_thread is not None:
            return
        def poll():
            while not self.stop_event.wait(max(30, interval_seconds)):
                try:
                    if self.sync.is_dirty or self.sync.is_busy:
                        continue
                    result = self._pull_merge()
                    if result["changed"]:
                        self.sync.mark_pending()
                        self.sync.schedule_sync(2.0)
                        self.status = "Desktop changes merged; publishing combined snapshot"
                    else:
                        self.status = "Synced"
                except RuntimeError as exc:
                    if "No remote snapshot exists" not in str(exc):
                        self.status = "Sync poll failed: " + str(exc)[:180]
                except Exception as exc:
                    self.status = "Sync poll failed: " + str(exc)[:180]
        self.poll_thread = threading.Thread(target=poll, name="web-db-sync-poll", daemon=True)
        self.poll_thread.start()

    def sync_now(self, conn: sqlite3.Connection) -> dict:
        if not self.configured:
            return {"success": False, "status": self.status, "error": self.last_pull.get("error", "")}
        try:
            if self.sync.is_dirty:
                self.sync.request_sync()
                return {"success": True, "queued": True, "status": "Local changes queued for encrypted push"}
            result = self._pull_merge()
            if result["changed"]:
                self.sync.mark_pending()
                self.sync.request_sync()
            else:
                self.status = "Synced"
            return {"success": True, **result, "status": self.status}
        except RuntimeError as exc:
            if "No remote snapshot exists" in str(exc):
                self.sync.request_sync()
                return {"success": True, "queued": True, "status": "Publishing first encrypted snapshot"}
            return {"success": False, "status": self.status, "error": str(exc)[:240]}

    def mark_pending(self):
        if self.sync:
            self.sync.mark_pending()

    def public_status(self):
        return {
            "configured": self.configured,
            "status": self.status,
            "installation_id": self.installation_id if self.configured else None,
            "dirty": bool(self.sync.is_dirty) if self.sync else False,
            "busy": bool(self.sync.is_busy) if self.sync else False,
            "last_sync": self.sync._last_sync if self.sync else "",
            "last_error": self.sync.last_error if self.sync else "",
            "last_pull": dict(self.last_pull),
            "device_registered": bool(self.sync._device_credentials.get("token")) if self.sync else False,
        }
