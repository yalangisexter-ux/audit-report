"""Standalone web database backup and migration endpoints.

The browser edition owns its SQLite database. Imports are validated before an
atomic replacement and the previous web database is retained as a rollback copy.
The Windows EXE and its LocalAppData database are not touched.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

import api_server as api
import app as desktop_app

MAX_IMPORT_BYTES = 256 * 1024 * 1024
REQUIRED_TABLES = {"auth_users", "employees", "tasks"}


def _require_admin(user: dict) -> None:
    if str(user.get("role", "")).casefold() not in {"admin", "developer"}:
        raise HTTPException(status_code=403, detail="Admin or Developer permission required")


def _database_path() -> Path:
    return Path(desktop_app.DB_PATH)


def _rollback_import(current: Path, backup_path: Path) -> None:
    """Restore the pre-import database after a failure occurring post-replacement."""
    rollback_path = current.with_name(current.name + ".restore-rollback")
    try:
        if backup_path.is_file():
            shutil.copy2(backup_path, rollback_path)
            os.replace(rollback_path, current)
        else:
            current.unlink(missing_ok=True)
    finally:
        rollback_path.unlink(missing_ok=True)


def _validate_database(path: Path) -> dict:
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            integrity = db.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError("SQLite integrity check failed.")
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            missing = REQUIRED_TABLES - tables
            if missing:
                raise ValueError("This file is not a compatible Employee Audit Manager database.")
            users = int(db.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0])
            employees = int(db.execute("SELECT COUNT(*) FROM employees").fetchone()[0])
            tasks = int(db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
            if users < 1:
                raise ValueError("The imported database has no login accounts.")
            return {"auth_users": users, "employees": employees, "tasks": tasks}
        finally:
            db.close()
    except sqlite3.Error as exc:
        raise ValueError(f"Invalid SQLite database: {exc}") from exc


@api.app.get("/api/web-database/export")
def export_web_database(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    path = _database_path()
    export_dir = Path(desktop_app.EXPORT_DIR) / "web-database"
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = export_dir / f"RawStrength-Web-Database-{stamp}.db"
    destination = sqlite3.connect(str(target))
    try:
        conn.backup(destination)
        destination.execute("PRAGMA integrity_check")
    finally:
        destination.close()
    return FileResponse(
        str(target),
        media_type="application/vnd.sqlite3",
        filename=target.name,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@api.app.post("/api/web-database/import")
async def import_web_database(
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    _require_admin(user)
    manager = getattr(api, "WEB_SYNC_MANAGER", None)
    active_sync = getattr(manager, "sync", None) if manager is not None else None
    if active_sync is not None and getattr(active_sync, "is_busy", False):
        raise HTTPException(status_code=409, detail="Encrypted database sync is running. Wait for it to finish before restoring a backup.")
    filename = (file.filename or "").lower()
    if not filename.endswith((".db", ".sqlite", ".sqlite3")):
        raise HTTPException(status_code=400, detail="Upload a .db, .sqlite, or .sqlite3 database file.")
    data = await file.read(MAX_IMPORT_BYTES + 1)
    if not data or len(data) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Database file is empty or exceeds the 256 MB limit.")

    current = _database_path()
    current.parent.mkdir(parents=True, exist_ok=True)
    temp_path = current.with_name(current.name + ".import-check")
    backup_path = current.with_name(
        current.stem + ".before-import-" + datetime.now().strftime("%Y%m%d-%H%M%S") + current.suffix
    )
    replaced = False
    try:
        temp_path.write_bytes(data)
        # Migrate the uploaded copy before it can replace the customer's live DB.
        # This is the same web-only compatibility migration used at startup and
        # preserves IDs, salts, hashes, recovery data, and all account rows.
        try:
            from web_db_migrations import ensure_case_sensitive_auth_users
            ensure_case_sensitive_auth_users(temp_path)
        except Exception as exc:
            raise ValueError("The imported account schema could not be migrated safely.") from exc
        stats = _validate_database(temp_path)
        if current.exists():
            # Retain the exact current web database before replacing it.
            source = sqlite3.connect(str(current))
            backup = sqlite3.connect(str(backup_path))
            try:
                source.backup(backup)
            finally:
                backup.close()
                source.close()
        # Close this request's connection before the atomic file replacement.
        conn.close()
        os.replace(temp_path, current)
        replaced = True

        # Re-open and verify the replacement before reporting success. If this
        # critical local step fails, the exception handler restores the safety copy.
        restored = sqlite3.connect(str(current), timeout=15)
        try:
            integrity = restored.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise sqlite3.DatabaseError("Restored database failed SQLite integrity_check.")
            restored_tables = {
                row[0] for row in restored.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "web_auth_sessions" in restored_tables:
                restored.execute("DELETE FROM web_auth_sessions")
                restored.commit()
        finally:
            restored.close()

        # Invalidate browser sessions without changing imported account identities
        # or password hashes.
        api.ACTIVE_SESSIONS.clear()

        # Local restore is successful even if the remote sync queue is temporarily
        # unavailable. Report that condition explicitly instead of returning a
        # misleading 500 after the database has already been replaced.
        sync_warning = ""
        if manager is not None:
            try:
                manager.mark_pending()
                if manager.sync is not None:
                    manager.sync.schedule_sync(1.0)
            except Exception as sync_exc:
                sync_warning = (
                    "Local restore succeeded, but encrypted synchronization "
                    f"could not be queued: {str(sync_exc)[:180]}"
                )
        return {
            "success": True,
            "message": "Database imported. Sign in again using an account from the imported database.",
            "backup_file": backup_path.name if backup_path.exists() else None,
            "counts": stats,
            "sync_warning": sync_warning,
        }
    except ValueError as exc:
        temp_path.unlink(missing_ok=True)
        if replaced:
            try:
                _rollback_import(current, backup_path)
            except Exception as rollback_exc:
                raise HTTPException(
                    status_code=500,
                    detail="Database import failed and automatic rollback failed; retain the pre-import backup for recovery.",
                ) from rollback_exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        if replaced:
            try:
                _rollback_import(current, backup_path)
                detail = f"Database import failed; the previous database was restored: {str(exc)[:180]}"
            except Exception as rollback_exc:
                detail = (
                    "Database import failed and automatic rollback failed; "
                    f"the pre-import backup is {backup_path.name}. "
                    f"Rollback error: {str(rollback_exc)[:120]}"
                )
        else:
            detail = f"Database import failed; the existing database was not replaced: {str(exc)[:180]}"
        raise HTTPException(status_code=500, detail=detail) from exc
    finally:
        await file.close()



@api.app.get("/api/system/db-info")
def web_database_info(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    """Return safe database health/count metadata without exposing filesystem paths or credentials."""
    path = _database_path()
    table_names = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    table_counts = {}
    for table in (
        "auth_users", "employees", "tasks", "attendance", "customer_prospects",
        "archived_documents", "bt_products", "bt_orders", "bt_members", "bt_activities",
    ):
        if table in table_names:
            table_counts[table] = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    integrity_row = conn.execute("PRAGMA quick_check").fetchone()
    integrity = str(integrity_row[0]) if integrity_row else "unknown"
    try:
        stat = path.stat()
        size_bytes = int(stat.st_size)
        modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    except OSError:
        size_bytes = 0
        modified_at = ""
    backup_dir = Path(desktop_app.BACKUP_DIR)
    backup_count = len(list(backup_dir.glob("*.db"))) if backup_dir.is_dir() else 0
    manager = getattr(api, "WEB_SYNC_MANAGER", None)
    sync = {
        "configured": False,
        "status": "Encrypted web sync manager is unavailable",
        "dirty": False,
        "busy": False,
        "last_sync": "",
        "last_error": "",
        "installation_id": None,
    }
    if manager is not None:
        try:
            raw = manager.public_status()
            sync = {
                key: raw.get(key)
                for key in ("configured", "status", "dirty", "busy", "last_sync", "last_error", "installation_id")
            }
            sync["last_error"] = str(sync.get("last_error") or "")[:240]
        except Exception as exc:
            sync["status"] = "Unable to read encrypted sync status"
            sync["last_error"] = str(exc)[:240]
    return {
        "database_connected": True,
        "database_name": path.name,
        "database_size_bytes": size_bytes,
        "database_modified_at": modified_at,
        "database_integrity": integrity,
        "counts": table_counts,
        "backup_count": backup_count,
        "app_version": api.APP_VERSION,
        "sync": sync,
    }


@api.app.post("/api/system/sync-now")
def sync_web_database_now(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    """Run the existing encrypted installation-scoped sync without changing its key or transport."""
    manager = getattr(api, "WEB_SYNC_MANAGER", None)
    if manager is None:
        return {
            "success": False,
            "status": "Encrypted web sync manager is unavailable",
            "error": "Web database synchronization has not been initialized.",
        }
    try:
        return manager.sync_now(conn)
    except Exception as exc:
        return {
            "success": False,
            "status": "Encrypted sync failed",
            "error": str(exc)[:240],
        }
