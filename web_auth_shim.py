"""Web-only boot shim: cloud DB first, never keep historical seed roster (EXE untouched)."""
from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path

os.environ.setdefault("SKIP_INITIAL_AUDIT_SEED", "1")

import web_qt_stub  # noqa: F401

from fastapi.responses import JSONResponse
from starlette.requests import Request

import api_server as api

PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/setup",
    "/docs",
    "/openapi.json",
    "/redoc",
}

REQUIRE_LOGIN = os.environ.get("WEB_REQUIRE_LOGIN", "1").strip().lower() in ("1", "true", "yes")
PURGE_SEED = os.environ.get("WEB_PURGE_SEED_DATA", "1").strip().lower() in ("1", "true", "yes")


def _purge_historical_seed(db_path: Path) -> None:
    """Remove embedded historical audit demo employees/tasks if present."""
    if not db_path.is_file():
        return
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        before_e = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        conn.execute(
            """DELETE FROM tasks WHERE employee_id IN (
                 SELECT id FROM employees WHERE IFNULL(notes,'') LIKE '%historical audit%'
               )"""
        )
        conn.execute(
            "DELETE FROM employees WHERE IFNULL(notes,'') LIKE '%historical audit%'"
        )
        conn.execute(
            "DELETE FROM settings WHERE key LIKE 'initial_audit%'"
        )
        conn.commit()
        after_e = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        after_t = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        names = [r[0] for r in conn.execute("SELECT name FROM employees ORDER BY id LIMIT 12").fetchall()]
        conn.close()
        print(f"[DB] Purge seed: employees {before_e}->{after_e}, tasks now {after_t}, names={names}")
    except Exception as exc:
        print(f"[DB] Purge seed skipped: {exc}")


def _pull_shared_database_if_configured():
    try:
        from database_sync import GitHubDatabaseSync, FALLBACK_DB_SYNC_WORKER_URL
        import app as desktop_app
    except Exception as exc:
        print(f"[DB Sync] Import skipped: {exc}")
        return False

    worker_url = (os.environ.get("DB_SYNC_WORKER_URL") or FALLBACK_DB_SYNC_WORKER_URL or "").strip().rstrip("/")
    encryption_secret = (os.environ.get("DB_SYNC_ENCRYPTION_SECRET") or "").strip()
    if not encryption_secret and os.environ.get("DB_SYNC_USE_DESKTOP_DEFAULT", "").strip().lower() in ("1", "true", "yes"):
        encryption_secret = "Devlopershouse@1996#"
    if not worker_url or not encryption_secret:
        print("[DB Sync] Shared DB pull skipped (set DB_SYNC_ENCRYPTION_SECRET or DB_SYNC_USE_DESKTOP_DEFAULT=1).")
        return False

    install_id = (os.environ.get("DB_SYNC_INSTALLATION_ID") or secrets.token_hex(16)).strip()
    db_path = Path(desktop_app.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        sync = GitHubDatabaseSync(
            db_path,
            getattr(desktop_app, "GITHUB_REPOSITORY", "yalangisexter-ux/audit-report"),
            install_id,
            worker_url=worker_url,
            encryption_secret=encryption_secret,
        )
        payload = sync.download_latest_snapshot(prefer_latest=True)
        if not payload:
            print("[DB Sync] No remote snapshot available yet.")
            return False
        tmp = db_path.with_suffix(".pull.tmp")
        tmp.write_bytes(payload)
        check = sqlite3.connect(str(tmp))
        integrity = check.execute("PRAGMA integrity_check").fetchone()
        user_count = check.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
        emp_count = check.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        task_count = check.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        names = [r[0] for r in check.execute("SELECT name FROM employees ORDER BY id LIMIT 12").fetchall()]
        check.close()
        if not integrity or integrity[0] != "ok":
            tmp.unlink(missing_ok=True)
            print("[DB Sync] Pulled snapshot failed integrity check.")
            return False
        os.replace(tmp, db_path)
        print(f"[DB Sync] Restored cloud DB: auth_users={user_count}, employees={emp_count}, tasks={task_count}, names={names}")
        return True
    except Exception as exc:
        print(f"[DB Sync] Pull failed: {exc}")
        return False


@api.app.middleware("http")
async def require_api_login(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    if path in PUBLIC_PATHS or path.startswith("/api/auth/login") or path.startswith("/api/auth/setup"):
        return await call_next(request)
    if not REQUIRE_LOGIN:
        return await call_next(request)
    auth = request.headers.get("authorization") or ""
    token = auth.replace("Bearer ", "").strip()
    if not token or token not in api.ACTIVE_SESSIONS:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    return await call_next(request)


pulled = _pull_shared_database_if_configured()
if PURGE_SEED:
    try:
        import app as desktop_app
        _purge_historical_seed(Path(desktop_app.DB_PATH))
    except Exception as exc:
        print(f"[DB] Post-boot purge failed: {exc}")
print(f"[Web Boot] cloud_pull={'ok' if pulled else 'no'}; login_required={REQUIRE_LOGIN}; purge_seed={PURGE_SEED}")
