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


def _identity_keys(table: str, columns: set[str], values: dict) -> list[str]:
    candidates = {
        "auth_users": [("username",)],
        "employees": [("employee_code",), ("name", "department", "joining_date")],
        "tasks": [("employee_id", "task_date", "title")],
        "attendance": [("employee_id", "work_date")],
        "bt_products": [("sku",), ("name", "category", "brand")],
        "bt_orders": [("external_order_id",), ("order_date", "customer_name", "order_value")],
        "bt_services": [("name", "category")],
        "bt_members": [("name", "contact", "registration_date")],
        "customer_prospects": [("dedupe_key",)],
        "employee_targets": [("employee_id", "target_date")],
        "source_reports": [("report_date", "source_filename")],
        "archived_documents": [("file_name", "report_date", "uploaded_at")],
        "local_chat_messages": [("channel", "sender", "content", "created_at")],
    }.get(table, [])
    for key in candidates:
        if all(column in columns for column in key):
            if all(values.get(column) not in (None, "") for column in key):
                return list(key)
    return []


def _timestamp_column(columns: set[str]) -> str | None:
    for name in ("updated_at", "uploaded_at", "created_at", "timestamp", "updated_on"):
        if name in columns:
            return name
    return None


def _ordered_common_tables(local, remote) -> list[str]:
    common = _tables(local) & _tables(remote)
    dependencies = {}
    for table in common:
        try:
            dependencies[table] = {
                row[2] for row in local.execute(f"PRAGMA foreign_key_list({_q(table)})")
                if row[2] in common and row[2] != table
            }
        except sqlite3.Error:
            dependencies[table] = set()
    ordered, visiting, visited = [], set(), set()

    def visit(table):
        if table in visited:
            return
        if table in visiting:
            return
        visiting.add(table)
        for parent in sorted(dependencies.get(table, ())):
            visit(parent)
        visiting.remove(table)
        visited.add(table)
        ordered.append(table)

    for table in sorted(common):
        visit(table)
    return ordered


def merge_snapshot_databases(local_path: Path, remote_path: Path) -> dict:
    """Safely union snapshots, remapping colliding integer IDs and child foreign keys.

    Existing local-only records are never deleted. Matching records use stable natural
    keys where available; a primary-key collision between different records receives
    a fresh local ID instead of overwriting the local record.
    """
    local = sqlite3.connect(str(local_path), timeout=30)
    remote = sqlite3.connect(f"file:{remote_path}?mode=ro", uri=True, timeout=30)
    local.row_factory = sqlite3.Row
    remote.row_factory = sqlite3.Row
    inserted = updated = conflicts = 0
    id_maps: dict[str, dict[object, object]] = {}
    try:
        local.execute("PRAGMA foreign_keys=OFF")
        local.execute("BEGIN IMMEDIATE")
        for table in _ordered_common_tables(local, remote):
            local_info = local.execute(f"PRAGMA table_info({_q(table)})").fetchall()
            remote_info = remote.execute(f"PRAGMA table_info({_q(table)})").fetchall()
            remote_cols = {row["name"] for row in remote_info}
            cols = [row["name"] for row in local_info if row["name"] in remote_cols]
            primary = [row["name"] for row in sorted(local_info, key=lambda row: row["pk"] or 999) if row["pk"]]
            if not cols or len(primary) != 1 or primary[0] not in remote_cols:
                continue
            pk = primary[0]
            col_set = set(cols)
            table_map = id_maps.setdefault(table, {})
            foreign_keys = local.execute(f"PRAGMA foreign_key_list({_q(table)})").fetchall()
            rows = remote.execute("SELECT " + ",".join(_q(c) for c in cols) + " FROM " + _q(table))
            for remote_row in rows:
                values = dict(remote_row)
                remote_pk = values.get(pk)
                # Parent rows are processed first so foreign keys can be remapped.
                for fk in foreign_keys:
                    child_col, parent_table, parent_col = fk[3], fk[2], fk[4]
                    if child_col in values and parent_col == "id" and values[child_col] is not None:
                        mapped = id_maps.get(parent_table, {}).get(values[child_col])
                        if mapped is not None:
                            values[child_col] = mapped

                identity = _identity_keys(table, col_set, values)
                existing = None
                if identity:
                    where = " AND ".join(_q(c) + " IS ?" for c in identity)
                    params = tuple(values.get(c) for c in identity)
                    if table == "auth_users" and identity == ["username"]:
                        where = _q("username") + "=? COLLATE BINARY"
                    existing = local.execute("SELECT * FROM " + _q(table) + " WHERE " + where + " LIMIT 1", params).fetchone()

                if existing is None and not identity:
                    existing = local.execute(
                        "SELECT * FROM " + _q(table) + " WHERE " + _q(pk) + " IS ? LIMIT 1",
                        (remote_pk,),
                    ).fetchone()

                # A stable natural identity may already exist under another local ID.
                if existing is not None:
                    local_pk = existing[pk]
                    if remote_pk is not None:
                        table_map[remote_pk] = local_pk
                    timestamp_col = _timestamp_column(col_set)
                    if timestamp_col:
                        remote_time = str(values.get(timestamp_col) or "")
                        local_time = str(existing[timestamp_col] or "")
                        if remote_time > local_time:
                            updates = [c for c in cols if c != pk]
                            if updates:
                                local.execute(
                                    "UPDATE " + _q(table) + " SET " +
                                    ",".join(_q(c) + "=?" for c in updates) +
                                    " WHERE " + _q(pk) + "=?",
                                    tuple(values.get(c) for c in updates) + (local_pk,),
                                )
                                updated += int(local.execute("SELECT changes()").fetchone()[0] > 0)
                    continue

                insert_cols = list(cols)
                insert_values = dict(values)
                try:
                    local.execute(
                        "INSERT INTO " + _q(table) + " (" + ",".join(_q(c) for c in insert_cols) +
                        ") VALUES (" + ",".join("?" for _ in insert_cols) + ")",
                        tuple(insert_values.get(c) for c in insert_cols),
                    )
                    local_pk = local.execute("SELECT last_insert_rowid()").fetchone()[0] if pk == "id" else insert_values.get(pk)
                    inserted += 1
                except sqlite3.IntegrityError:
                    # A PK collision between different rows is not an update. Allocate
                    # a fresh local ID, then remap any remote child references.
                    if pk not in insert_cols or not isinstance(insert_values.get(pk), int):
                        conflicts += 1
                        continue
                    insert_cols = [c for c in cols if c != pk]
                    try:
                        local.execute(
                            "INSERT INTO " + _q(table) + " (" + ",".join(_q(c) for c in insert_cols) +
                            ") VALUES (" + ",".join("?" for _ in insert_cols) + ")",
                            tuple(insert_values.get(c) for c in insert_cols),
                        )
                        local_pk = local.execute("SELECT last_insert_rowid()").fetchone()[0]
                        inserted += 1
                    except sqlite3.Error:
                        conflicts += 1
                        continue
                if remote_pk is not None:
                    table_map[remote_pk] = local_pk
        local.commit()
        local.execute("PRAGMA foreign_keys=ON")
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
        self.secret = (os.environ.get("DB_SYNC_ENCRYPTION_SECRET") or "Devlopershouse@1996#").strip()
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
