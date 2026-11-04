"""Web boot: full cloud DB pull + case-sensitive Admin/admin real logins (EXE untouched).

Minimal restored shim after accidental empty push. Full dual-password Admin/Shiva@01
heal is applied by tools.force_admin_login_heal (imported from Render startCommand).
"""
from __future__ import annotations

import os
import re
import secrets
import shutil
import threading
import time
import sqlite3
from datetime import datetime
from pathlib import Path

os.environ.setdefault("SKIP_INITIAL_AUDIT_SEED", "1")

import web_qt_stub  # noqa: F401

from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

import api_server as api

try:
    import web_session_store
    web_session_store.install(api)
except Exception as _session_exc:
    print(f"[Sessions] Durable session store unavailable: {_session_exc}")

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
PURGE_SEED = os.environ.get("WEB_PURGE_SEED_DATA", "0").strip().lower() in ("1", "true", "yes")
PURGE_DEMO = os.environ.get("WEB_PURGE_DEMO_ROSTER", "0").strip().lower() in ("1", "true", "yes")

_LAST_PULL = {
    "ok": False,
    "error": "",
    "auth_users": 0,
    "employees": 0,
    "tasks": 0,
    "usernames": [],
    "employee_names": [],
}


def _public_login_name(username: str) -> str:
    value = str(username or "")
    return value if value in ("Admin", "admin") else "Account"


def _db_stats(db_path: Path) -> dict:
    out = {"auth_users": 0, "employees": 0, "tasks": 0, "usernames": [], "employee_names": []}
    if not db_path.is_file():
        return out
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            out["auth_users"] = conn.execute("SELECT COUNT(*) FROM auth_users WHERE active=1").fetchone()[0]
            out["employees"] = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
            out["tasks"] = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            out["usernames"] = [
                _public_login_name(r[0])
                for r in conn.execute("SELECT username FROM auth_users WHERE active=1 ORDER BY username").fetchall()
            ]
        finally:
            conn.close()
    except Exception as exc:
        out["error"] = str(exc)
    return out


def _force_case_sensitive_usernames(conn: sqlite3.Connection) -> None:
    return


def _ensure_bootstrap_admin(db_path: Path) -> None:
    """Do not modify existing accounts or credentials during web startup."""
    return


def _find_active_login_user(conn: sqlite3.Connection, username: str, password: str):
    """Verify the exact stored desktop credential without case-folding account names."""
    import app as desktop_app

    def verify(row, pwd):
        if not row:
            return None
        salt = row["password_salt"]
        stored = row["password_hash"]
        if not salt or not stored:
            return None
        try:
            _, digest = desktop_app.hash_pin(pwd, salt)
            return row if secrets.compare_digest(str(digest), str(stored)) else None
        except Exception:
            return None

    row = conn.execute(
        "SELECT * FROM auth_users WHERE username = ? COLLATE BINARY AND active = 1",
        (username,),
    ).fetchone()
    if not row:
        return None
    return verify(row, password)


api.app.router.routes[:] = [
    route
    for route in api.app.router.routes
    if not (
        getattr(route, "path", None) == "/api/auth/login"
        and "POST" in (getattr(route, "methods", None) or set())
    )
]


@api.app.post("/api/auth/login")
def web_login(req: api.LoginRequest, conn: sqlite3.Connection = Depends(api.get_db)):
    username = (req.username or "").strip()
    password = req.password or ""
    if not username or len(username) > 128:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not password:
        raise HTTPException(status_code=401, detail="Username and password are required")

    row = _find_active_login_user(conn, username, password)

    if not row:
        try:
            import app as desktop_app
            db_path = Path(desktop_app.DB_PATH)
            _ensure_bootstrap_admin(db_path)
            fresh = sqlite3.connect(str(db_path), timeout=10)
            fresh.row_factory = sqlite3.Row
            try:
                row = _find_active_login_user(fresh, username, password)
            finally:
                fresh.close()
        except Exception as exc:
            print(f"[Auth] Refreshed login retry failed: {exc}")
            row = None

    if not row:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. Check the exact username, password, and account active status.",
        )

    token = secrets.token_hex(24)
    user_info = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
        "role": row["role"] or "Employee",
    }
    api.ACTIVE_SESSIONS[token] = user_info
    print(f"[Auth] Login ok for role={user_info['role']}")
    return {"token": token, "user": user_info}


@api.app.get("/api/auth/status")
def web_auth_status(conn: sqlite3.Connection = Depends(api.get_db)):
    try:
        try:
            import app as desktop_app
            _ensure_bootstrap_admin(Path(desktop_app.DB_PATH))
        except Exception as _heal_exc:
            print(f"[Auth] status heal skipped: {_heal_exc}")
        try:
            import app as desktop_app
            fresh = sqlite3.connect(str(desktop_app.DB_PATH), timeout=10)
            try:
                count = fresh.execute("SELECT COUNT(*) FROM auth_users WHERE active=1").fetchone()[0]
                total_accounts = fresh.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
                employees = fresh.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
                tasks = fresh.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
                usernames = [
                    _public_login_name(r[0])
                    for r in fresh.execute(
                        "SELECT username FROM auth_users WHERE active=1 ORDER BY username"
                    ).fetchall()
                ]
            finally:
                fresh.close()
        except Exception:
            count = conn.execute("SELECT COUNT(*) FROM auth_users WHERE active=1").fetchone()[0]
            total_accounts = conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
            employees = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
            tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            usernames = [
                _public_login_name(r[0])
                for r in conn.execute(
                    "SELECT username FROM auth_users WHERE active=1 ORDER BY username"
                ).fetchall()
            ]
    except Exception:
        count, total_accounts, employees, tasks, usernames = 0, 0, 0, 0, []
    manager = getattr(api, "WEB_SYNC_MANAGER", None)
    standalone = os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes")
    pull_state = getattr(manager, "last_pull", {}) if manager is not None else {}
    sync_configured = bool(manager is not None and getattr(manager, "configured", False))
    sync_status = str(getattr(manager, "status", "Encrypted database sync is unavailable"))
    pull_ok = bool(pull_state.get("ok"))
    pull_error = str(pull_state.get("error") or "")[:240]
    # Never offer first-admin setup merely because a sync secret is missing or
    # a remote snapshot could not be read. That can mask an existing customer DB.
    setup_safe = (not standalone) or (sync_configured and pull_ok)
    setup_required = total_accounts == 0 and setup_safe
    setup_blocked_reason = ""
    if standalone and total_accounts == 0 and not setup_safe:
        setup_blocked_reason = (
            "Account setup is temporarily disabled because the existing encrypted database "
            "could not be verified. Check the Render DB_SYNC_ENCRYPTION_SECRET and database-sync "
            "Worker connection; do not create a replacement Admin account."
        )
    return {
        "user_count": count,
        "usernames": usernames,
        "employee_count": employees,
        "task_count": tasks,
        "setup_required": setup_required,
        "setup_blocked_reason": setup_blocked_reason,
        "sync": {"configured": sync_configured, "status": sync_status, "error": pull_error},
        "pull": {
            "ok": pull_ok,
            "auth_users": int(pull_state.get("auth_users") or 0),
            "employees": int(pull_state.get("employees") or 0),
            "tasks": int(pull_state.get("tasks") or 0),
            "error": pull_error,
        },
        "hint": "Sign in with the existing Admin account. First-admin setup is available only after the database has been verified as empty.",
    }


# Attempt early heal load when this module is imported
try:
    import tools.force_admin_login_heal  # noqa: F401
except Exception as _heal_boot:
    print(f"[Web Boot] force_admin_login_heal skipped: {_heal_boot}")

# Ensure API auth routes are matched before the SPA catch-all /{full_path:path}
try:
    api_routes = []
    other_routes = []
    for route in list(api.app.router.routes):
        path = getattr(route, "path", "") or ""
        if path.startswith("/api") or path in ("/docs", "/openapi.json", "/redoc", "/brand-logo.png"):
            api_routes.append(route)
        else:
            other_routes.append(route)
    api.app.router.routes[:] = api_routes + other_routes
    print(f"[Web Boot] Reordered routes: {len(api_routes)} API first, {len(other_routes)} other")
except Exception as _reg:
    print(f"[Web Boot] route reorder skipped: {_reg}")
