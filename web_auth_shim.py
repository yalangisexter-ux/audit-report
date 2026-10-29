"""Web-only boot shim: cloud DB first, login diagnostics, no historical seed (EXE untouched)."""
from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path

os.environ.setdefault("SKIP_INITIAL_AUDIT_SEED", "1")

import web_qt_stub  # noqa: F401

from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

import api_server as api

PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/setup",
    "/api/auth/status",
    "/docs",
    "/openapi.json",
    "/redoc",
}

REQUIRE_LOGIN = os.environ.get("WEB_REQUIRE_LOGIN", "1").strip().lower() in ("1", "true", "yes")
PURGE_SEED = os.environ.get("WEB_PURGE_SEED_DATA", "1").strip().lower() in ("1", "true", "yes")


def _purge_historical_seed(db_path: Path) -> None:
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
        conn.execute("DELETE FROM employees WHERE IFNULL(notes,'') LIKE '%historical audit%'")
        conn.execute("DELETE FROM settings WHERE key LIKE 'initial_audit%'")
        conn.commit()
        after_e = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        after_t = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        names = [r[0] for r in conn.execute("SELECT name FROM employees ORDER BY id LIMIT 12").fetchall()]
        users = [r[0] for r in conn.execute("SELECT username FROM auth_users WHERE active=1 ORDER BY username").fetchall()]
        conn.close()
        print(f"[DB] Purge seed: employees {before_e}->{after_e}, tasks={after_t}, names={names}, auth_users={users}")
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
        print("[DB Sync] Shared DB pull skipped.")
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
        users = [r[0] for r in check.execute("SELECT username FROM auth_users WHERE active=1").fetchall()]
        check.close()
        if not integrity or integrity[0] != "ok":
            tmp.unlink(missing_ok=True)
            print("[DB Sync] Pulled snapshot failed integrity check.")
            return False
        os.replace(tmp, db_path)
        print(f"[DB Sync] Restored cloud DB: auth={user_count} users={users}, employees={emp_count}, tasks={task_count}, names={names}")
        return True
    except Exception as exc:
        print(f"[DB Sync] Pull failed: {exc}")
        return False


@api.app.get("/api/auth/status")
def web_auth_status(conn: sqlite3.Connection = Depends(api.get_db)):
    try:
        count = conn.execute("SELECT COUNT(*) FROM auth_users WHERE active=1").fetchone()[0]
        usernames = [
            r[0]
            for r in conn.execute(
                "SELECT username FROM auth_users WHERE active=1 ORDER BY username COLLATE NOCASE"
            ).fetchall()
        ]
    except Exception:
        count, usernames = 0, []
    return {
        "user_count": count,
        "usernames": usernames,
        "setup_required": count == 0,
        "hint": "Use the exact Username from the desktop app (e.g. admin or taruna), not the display name.",
    }


@api.app.post("/api/auth/login")
def web_login(req: api.LoginRequest, conn: sqlite3.Connection = Depends(api.get_db)):
    username = (req.username or "").strip()
    password = req.password or ""
    if not username or not password:
        raise HTTPException(status_code=401, detail="Username and password are required")

    try:
        total_users = conn.execute("SELECT COUNT(*) FROM auth_users WHERE active=1").fetchone()[0]
    except Exception:
        total_users = 0

    if total_users == 0:
        raise HTTPException(
            status_code=401,
            detail="No login accounts on this web server yet. Set WEB_BOOTSTRAP_ADMIN_PASSWORD on Render, or sync the desktop cloud DB and redeploy.",
        )

    row = conn.execute(
        "SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1",
        (username,),
    ).fetchone()
    if not row:
        print(f"[Auth] unknown username={username!r} active_users={total_users}")
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. Use the desktop Username field (often admin or taruna), not the display name.",
        )

    import app as desktop_app

    _, digest = desktop_app.hash_pin(password, row["password_salt"])
    if not secrets.compare_digest(digest, row["password_hash"]):
        print(f"[Auth] bad password for username={row['username']!r}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_hex(24)
    user_info = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
        "role": row["role"],
    }
    api.ACTIVE_SESSIONS[token] = user_info
    print(f"[Auth] Login ok: {user_info['username']} ({user_info['role']})")
    return {"token": token, "user": user_info}


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


def _ensure_bootstrap_admin(db_path: Path) -> None:
    """Optional: set WEB_BOOTSTRAP_ADMIN_PASSWORD on Render to force-sync admin password (web only)."""
    pwd = (os.environ.get("WEB_BOOTSTRAP_ADMIN_PASSWORD") or "").strip()
    if not pwd:
        return
    try:
        import app as desktop_app
        db = desktop_app.Database()
        if hasattr(db, "close_github_sync"):
            try:
                db.close_github_sync(timeout=0)
            except Exception:
                pass
        conn = db.conn
        salt, digest = desktop_app.hash_pin(pwd)
        now = desktop_app.now_text()
        row = conn.execute("SELECT id FROM auth_users WHERE username='admin' COLLATE NOCASE").fetchone()
        if row:
            conn.execute(
                "UPDATE auth_users SET password_salt=?, password_hash=?, active=1, updated_at=? WHERE id=?",
                (salt, digest, now, row[0]),
            )
            print("[Auth] Bootstrap: updated password for admin from WEB_BOOTSTRAP_ADMIN_PASSWORD")
        else:
            conn.execute(
                """INSERT INTO auth_users(username, display_name, role, password_salt, password_hash,
                   security_question, answer_salt, answer_hash, active, created_at, updated_at)
                   VALUES('admin', 'Administrator', 'Admin', ?, ?, '', '', '', 1, ?, ?)""",
                (salt, digest, now, now),
            )
            print("[Auth] Bootstrap: created admin from WEB_BOOTSTRAP_ADMIN_PASSWORD")
        conn.commit()
        try:
            db.conn.close()
        except Exception:
            pass
    except Exception as exc:
        print(f"[Auth] Bootstrap admin failed: {exc}")


pulled = _pull_shared_database_if_configured()
if PURGE_SEED:
    try:
        import app as desktop_app
        _purge_historical_seed(Path(desktop_app.DB_PATH))
    except Exception as exc:
        print(f"[DB] Post-boot purge failed: {exc}")
try:
    import app as desktop_app
    _ensure_bootstrap_admin(Path(desktop_app.DB_PATH))
except Exception as exc:
    print(f"[Auth] Bootstrap call failed: {exc}")
print(f"[Web Boot] cloud_pull={'ok' if pulled else 'no'}; login_required={REQUIRE_LOGIN}; purge_seed={PURGE_SEED}")
