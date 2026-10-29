"""Web boot: pull full cloud SQLite snapshot, optional admin bootstrap (EXE untouched)."""
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
    "/api/system/db-info",
    "/docs",
    "/openapi.json",
    "/redoc",
}

REQUIRE_LOGIN = os.environ.get("WEB_REQUIRE_LOGIN", "1").strip().lower() in ("1", "true", "yes")
PURGE_SEED = os.environ.get("WEB_PURGE_SEED_DATA", "1").strip().lower() in ("1", "true", "yes")
PURGE_DEMO = os.environ.get("WEB_PURGE_DEMO_ROSTER", "1").strip().lower() in ("1", "true", "yes")

_LAST_PULL = {
    "ok": False,
    "error": "",
    "auth_users": 0,
    "employees": 0,
    "tasks": 0,
    "usernames": [],
    "employee_names": [],
}


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
                r[0]
                for r in conn.execute(
                    "SELECT username FROM auth_users WHERE active=1 ORDER BY username COLLATE NOCASE"
                ).fetchall()
            ]
            out["employee_names"] = [
                r[0] for r in conn.execute("SELECT name FROM employees ORDER BY id LIMIT 20").fetchall()
            ]
        finally:
            conn.close()
    except Exception as exc:
        out["error"] = str(exc)
    return out


def _purge_junk_rows(db_path: Path) -> None:
    if not db_path.is_file():
        return
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        if PURGE_SEED:
            conn.execute(
                """DELETE FROM tasks WHERE employee_id IN (
                     SELECT id FROM employees WHERE IFNULL(notes,'') LIKE '%historical audit%'
                   )"""
            )
            conn.execute("DELETE FROM employees WHERE IFNULL(notes,'') LIKE '%historical audit%'")
            conn.execute("DELETE FROM settings WHERE key LIKE 'initial_audit%'")
        if PURGE_DEMO:
            demo_names = ("Present Person", "Absent Person", "On Leave", "Unmarked Person")
            q = ",".join("?" for _ in demo_names)
            conn.execute(
                f"""DELETE FROM tasks WHERE employee_id IN (
                      SELECT id FROM employees WHERE name IN ({q})
                    )""",
                demo_names,
            )
            conn.execute(f"DELETE FROM employees WHERE name IN ({q})", demo_names)
        conn.commit()
        conn.close()
        print("[DB] Junk/demo row purge complete")
    except Exception as exc:
        print(f"[DB] Purge skipped: {exc}")


def _pull_full_database() -> bool:
    global _LAST_PULL
    try:
        from database_sync import GitHubDatabaseSync, FALLBACK_DB_SYNC_WORKER_URL
        import app as desktop_app
    except Exception as exc:
        _LAST_PULL = {"ok": False, "error": f"import: {exc}"}
        print(f"[DB Sync] Import skipped: {exc}")
        return False

    worker_url = (os.environ.get("DB_SYNC_WORKER_URL") or FALLBACK_DB_SYNC_WORKER_URL or "").strip().rstrip("/")
    secrets_to_try = []
    primary = (os.environ.get("DB_SYNC_ENCRYPTION_SECRET") or "").strip()
    if primary:
        secrets_to_try.append(primary)
    if os.environ.get("DB_SYNC_USE_DESKTOP_DEFAULT", "1").strip().lower() in ("1", "true", "yes"):
        secrets_to_try.append("Devlopershouse@1996#")
    seen = set()
    secrets_to_try = [s for s in secrets_to_try if s and not (s in seen or seen.add(s))]
    if not worker_url or not secrets_to_try:
        _LAST_PULL = {"ok": False, "error": "missing worker url or encryption secret"}
        print("[DB Sync] Missing worker URL or encryption secret")
        return False

    target_id = (os.environ.get("DB_SYNC_INSTALLATION_ID") or "").strip()
    install_id = target_id if len(target_id) == 32 else secrets.token_hex(16)
    db_path = Path(desktop_app.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    last_err = ""
    for secret in secrets_to_try:
        try:
            sync = GitHubDatabaseSync(
                db_path,
                getattr(desktop_app, "GITHUB_REPOSITORY", "yalangisexter-ux/audit-report"),
                install_id,
                worker_url=worker_url,
                encryption_secret=secret,
            )
            prefer_latest = not (target_id and len(target_id) == 32)
            payload = sync.download_latest_snapshot(
                target_installation_id=target_id if len(target_id) == 32 else "",
                prefer_latest=prefer_latest,
                candidate_secret=secret,
            )
            if not payload:
                last_err = "empty payload"
                continue
            if not payload.startswith(b"SQLite format 3"):
                last_err = "payload is not a SQLite database"
                continue
            tmp = db_path.with_suffix(".pull.tmp")
            tmp.write_bytes(payload)
            check = sqlite3.connect(str(tmp))
            integrity = check.execute("PRAGMA integrity_check").fetchone()
            stats = {
                "auth_users": check.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0],
                "employees": check.execute("SELECT COUNT(*) FROM employees").fetchone()[0],
                "tasks": check.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
                "usernames": [r[0] for r in check.execute("SELECT username FROM auth_users").fetchall()],
                "employee_names": [r[0] for r in check.execute("SELECT name FROM employees ORDER BY id LIMIT 20").fetchall()],
            }
            check.close()
            if not integrity or integrity[0] != "ok":
                tmp.unlink(missing_ok=True)
                last_err = "integrity_check failed"
                continue
            os.replace(tmp, db_path)
            _LAST_PULL = {"ok": True, "error": "", **stats}
            print(
                f"[DB Sync] FULL DB restored: auth={stats['auth_users']} users={stats['usernames']} "
                f"employees={stats['employees']} tasks={stats['tasks']} names={stats['employee_names']}"
            )
            if stats["auth_users"] == 0:
                print(
                    "[DB Sync] WARNING: cloud snapshot has ZERO login accounts. "
                    "Run Cloud Sync from the desktop EXE that has your real admin user, "
                    "or set WEB_BOOTSTRAP_ADMIN_PASSWORD on Render."
                )
            return True
        except Exception as exc:
            last_err = str(exc)
            print(f"[DB Sync] Attempt failed: {exc}")
            continue

    _LAST_PULL = {"ok": False, "error": last_err or "pull failed"}
    print(f"[DB Sync] Pull failed: {last_err}")
    return False


def _ensure_bootstrap_admin(db_path: Path) -> None:
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
            print("[Auth] Bootstrap: updated admin password from WEB_BOOTSTRAP_ADMIN_PASSWORD")
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
        "pull": _LAST_PULL,
        "hint": "Username is often admin or taruna. If user_count is 0, set WEB_BOOTSTRAP_ADMIN_PASSWORD or sync desktop DB.",
    }


@api.app.get("/api/system/db-info")
def web_db_info():
    try:
        import app as desktop_app

        stats = _db_stats(Path(desktop_app.DB_PATH))
    except Exception as exc:
        stats = {"error": str(exc)}
    return {"pull": _LAST_PULL, "local": stats}


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
            detail=(
                "No login accounts in the web database. "
                "1) On desktop: run Cloud Sync successfully. "
                "2) On Render: set WEB_BOOTSTRAP_ADMIN_PASSWORD to your password and redeploy."
            ),
        )

    row = conn.execute(
        "SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1",
        (username,),
    ).fetchone()
    if not row:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. Use desktop Username (admin / taruna), not display name.",
        )

    import app as desktop_app

    _, digest = desktop_app.hash_pin(password, row["password_salt"])
    if not secrets.compare_digest(digest, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_hex(24)
    user_info = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
        "role": row["role"],
    }
    api.ACTIVE_SESSIONS[token] = user_info
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


print("[Web Boot] Pulling full cloud database snapshot…")
pulled = _pull_full_database()
try:
    import app as desktop_app

    db_path = Path(desktop_app.DB_PATH)
    if PURGE_SEED or PURGE_DEMO:
        _purge_junk_rows(db_path)
    _ensure_bootstrap_admin(db_path)
    stats = _db_stats(db_path)
    print(f"[Web Boot] Local DB after pull/bootstrap: {stats}")
except Exception as exc:
    print(f"[Web Boot] post-pull failed: {exc}")
print(f"[Web Boot] cloud_pull={'ok' if pulled else 'FAILED'}; login_required={REQUIRE_LOGIN}")
