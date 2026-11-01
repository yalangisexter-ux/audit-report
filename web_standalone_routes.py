"""Standalone web database backup and migration endpoints.

The browser edition owns its SQLite database. Imports are validated before an
atomic replacement and the previous web database is retained as a rollback copy.
The Windows EXE and its LocalAppData database are not touched.
"""
from __future__ import annotations

import os
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


def _database_path() -> Path:
    return Path(desktop_app.DB_PATH)


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
        headers={"Cache-Control": "no-store"},
    )


@api.app.post("/api/web-database/import")
async def import_web_database(
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
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
    try:
        temp_path.write_bytes(data)
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
        api.ACTIVE_SESSIONS.clear()
        return {
            "success": True,
            "message": "Database imported. Sign in again using an account from the imported database.",
            "backup_file": backup_path.name if backup_path.exists() else None,
            "counts": stats,
        }
    except ValueError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Database import failed; existing data was retained: {exc}") from exc
    finally:
        await file.close()
