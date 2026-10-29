"""Web-only boot shim: shared cloud DB pull + optional login gate (does not change the Windows EXE)."""
from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path

# Must run before api_server -> app imports PySide6
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

# Until the React login screen is deployed, GET APIs stay open so the UI does not crash.
# Set WEB_REQUIRE_LOGIN=1 on Render to enforce Bearer tokens on all non-public API routes.
REQUIRE_LOGIN = os.environ.get("WEB_REQUIRE_LOGIN", "0").strip().lower() in ("1", "true", "yes")


def _pull_shared_database_if_configured():
    try:
        from database_sync import GitHubDatabaseSync, FALLBACK_DB_SYNC_WORKER_URL
        import app as desktop_app
    except Exception as exc:
        print(f"[DB Sync] Import skipped: {exc}")
        return

    worker_url = (os.environ.get("DB_SYNC_WORKER_URL") or FALLBACK_DB_SYNC_WORKER_URL or "").strip().rstrip("/")
    encryption_secret = (os.environ.get("DB_SYNC_ENCRYPTION_SECRET") or "").strip()
    if not encryption_secret and os.environ.get("DB_SYNC_USE_DESKTOP_DEFAULT", "").strip().lower() in ("1", "true", "yes"):
        encryption_secret = "Devlopershouse@1996#"
    if not worker_url or not encryption_secret:
        print("[DB Sync] Shared DB pull skipped (set DB_SYNC_ENCRYPTION_SECRET or DB_SYNC_USE_DESKTOP_DEFAULT=1).")
        return

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
            return
        tmp = db_path.with_suffix(".pull.tmp")
        tmp.write_bytes(payload)
        check = sqlite3.connect(str(tmp))
        integrity = check.execute("PRAGMA integrity_check").fetchone()
        user_count = check.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
        check.close()
        if not integrity or integrity[0] != "ok":
            tmp.unlink(missing_ok=True)
            print("[DB Sync] Pulled snapshot failed integrity check.")
            return
        os.replace(tmp, db_path)
        print(f"[DB Sync] Restored shared database ({user_count} auth users) from cloud snapshot.")
    except Exception as exc:
        print(f"[DB Sync] Pull failed: {exc}")


@api.app.middleware("http")
async def require_api_login(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    if path in PUBLIC_PATHS or path.startswith("/api/auth/login") or path.startswith("/api/auth/setup"):
        return await call_next(request)

    # Default: allow GET so the current React UI (no login form yet) does not crash.
    if not REQUIRE_LOGIN and request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    if not REQUIRE_LOGIN and request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    auth = request.headers.get("authorization") or ""
    token = auth.replace("Bearer ", "").strip()
    if REQUIRE_LOGIN and (not token or token not in api.ACTIVE_SESSIONS):
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    if token and token not in api.ACTIVE_SESSIONS and REQUIRE_LOGIN:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    return await call_next(request)


_pull_shared_database_if_configured()
if REQUIRE_LOGIN:
    print("[Web Auth] Strict login enabled (WEB_REQUIRE_LOGIN=1).")
else:
    print("[Web Auth] Read APIs open (set WEB_REQUIRE_LOGIN=1 after login UI is deployed).")
