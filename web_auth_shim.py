"""Web boot: full cloud DB pull + case-sensitive Admin/admin real logins (EXE untouched)."""
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
                    "SELECT username FROM auth_users WHERE active=1 ORDER BY username"
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

    default_installation_id = "c4cf201d3c68e2fcaf60aa05fd423d9a"
    target_id = (os.environ.get("DB_SYNC_INSTALLATION_ID") or default_installation_id).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}", target_id):
        _LAST_PULL = {"ok": False, "error": "DB_SYNC_INSTALLATION_ID must be 32-char hex"}
        return False
    install_id = target_id
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
            payload = sync.download_latest_snapshot(
                target_installation_id=target_id,
                prefer_latest=False,
                candidate_secret=secret,
            )
            if not payload or not payload.startswith(b"SQLite format 3"):
                last_err = "empty or non-sqlite payload"
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

            demo = {"Present Person", "Absent Person", "On Leave", "Unmarked Person"}
            incoming_names = set(stats.get("employee_names") or [])
            demo_only = bool(incoming_names) and incoming_names.issubset(demo)
            if stats.get("auth_users", 0) < 1 or stats.get("employees", 0) < 1 or demo_only:
                tmp.unlink(missing_ok=True)
                last_err = "snapshot missing accounts or demo-only; preserving existing web DB"
                continue

            current = _db_stats(db_path)
            current_names = set(current.get("employee_names") or [])
            current_is_real = bool(current.get("auth_users", 0)) and bool(current.get("employees", 0)) and not (
                current_names and current_names.issubset(demo)
            )
            if current_is_real and (
                stats.get("auth_users", 0) < current.get("auth_users", 0)
                or stats.get("employees", 0) < current.get("employees", 0)
                or stats.get("tasks", 0) < current.get("tasks", 0)
            ):
                tmp.unlink(missing_ok=True)
                last_err = "incoming snapshot smaller than existing customer DB; preserved"
                continue

            if db_path.is_file():
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = db_path.with_name(f"{db_path.stem}.pre-sync-{stamp}.db")
                shutil.copy2(db_path, backup_path)
            os.replace(tmp, db_path)
            _LAST_PULL = {"ok": True, "error": "", **stats}
            print(f"[DB Sync] Snapshot OK: auth={stats['auth_users']} emp={stats['employees']} tasks={stats['tasks']}")
            return True
        except Exception as exc:
            last_err = str(exc)
            print(f"[DB Sync] Attempt failed: {exc}")
            continue

    _LAST_PULL = {"ok": False, "error": last_err or "pull failed"}
    print(f"[DB Sync] Pull failed: {last_err}")
    return False


def _force_case_sensitive_usernames(conn: sqlite3.Connection) -> None:
    """Ensure auth_users.username can hold both Admin and admin (BINARY)."""
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS auth_users_bin (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL COLLATE BINARY,
                display_name TEXT,
                role TEXT,
                password_salt TEXT,
                password_hash TEXT,
                security_question TEXT,
                answer_salt TEXT,
                answer_hash TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        conn.execute("DELETE FROM auth_users_bin")
        conn.execute(
            """INSERT INTO auth_users_bin(
                   id, username, display_name, role, password_salt, password_hash,
                   security_question, answer_salt, answer_hash, active, created_at, updated_at)
               SELECT id, username, display_name, role, password_salt, password_hash,
                      security_question, answer_salt, answer_hash, active, created_at, updated_at
               FROM auth_users"""
        )
        conn.execute("DROP TABLE auth_users")
        conn.execute("ALTER TABLE auth_users_bin RENAME TO auth_users")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_username_bin ON auth_users(username)"
        )
        conn.execute("PRAGMA foreign_keys=ON")
        print("[Auth] auth_users username collation forced to BINARY")
    except Exception as exc:
        print(f"[Auth] BINARY username migration skipped: {exc}")


def _upsert_user_exact(conn, desktop_app, username: str, display_name: str, role: str, password: str) -> None:
    salt, digest = desktop_app.hash_pin(password)
    now = desktop_app.now_text()
    row = conn.execute(
        "SELECT id FROM auth_users WHERE username = ? COLLATE BINARY",
        (username,),
    ).fetchone()
    if row:
        conn.execute(
            """UPDATE auth_users
               SET display_name=?, role=?, password_salt=?, password_hash=?, active=1, updated_at=?
               WHERE id=?""",
            (display_name, role, salt, digest, now, row[0]),
        )
        print(f"[Auth] Bootstrap: updated {username!r}")
    else:
        conn.execute(
            """INSERT INTO auth_users(
                   username, display_name, role, password_salt, password_hash,
                   security_question, answer_salt, answer_hash, active, created_at, updated_at
               ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
            (username, display_name, role, salt, digest, "", "", "", now, now),
        )
        print(f"[Auth] Bootstrap: created {username!r}")


def _ensure_bootstrap_admin(db_path: Path) -> None:
    """Force case-sensitive Admin (customer) and admin (developer) web passwords."""
    try:
        import app as desktop_app

        # Avoid desktop_app.Database() on Linux/Render — it can raise
        # "Sync secrets can only be protected on Windows" and abort bootstrap.
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS auth_users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    role TEXT,
                    password_salt TEXT,
                    password_hash TEXT,
                    security_question TEXT,
                    answer_salt TEXT,
                    answer_hash TEXT,
                    active INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )"""
            )
        except Exception:
            pass
        _force_case_sensitive_usernames(conn)

        customer_pwd = (
            os.environ.get("WEB_BOOTSTRAP_CUSTOMER_PASSWORD")
            or os.environ.get("WEB_BOOTSTRAP_TARUNA_PASSWORD")
            or ""
        ).strip() or "Shiva@01"
        dev_pwd = (os.environ.get("WEB_BOOTSTRAP_ADMIN_PASSWORD") or "").strip() or "kiran123"

        try:
            conn.execute("PRAGMA case_sensitive_like = ON")
        except Exception:
            pass
        try:
            rows = conn.execute("SELECT id, username, display_name, role FROM auth_users").fetchall()
            for r in rows:
                uname = r[1] if not isinstance(r, sqlite3.Row) else r["username"]
                if str(uname) in ("admin", "Admin"):
                    continue
                elif str(uname).casefold() == "admin":
                    rid = r[0] if not isinstance(r, sqlite3.Row) else r["id"]
                    conn.execute(
                        "UPDATE auth_users SET username=?, display_name=?, role=? WHERE id=?",
                        ("admin", "admin (Developer - Test Mode)", "Developer", rid),
                    )
            conn.execute(
                """DELETE FROM auth_users
                   WHERE lower(username) IN ('admin', 'taruna')
                     AND username NOT IN ('admin', 'Admin', 'taruna')"""
            )
        except Exception as exc:
            print(f"[Auth] Case-split normalize skipped: {exc}")

        _upsert_user_exact(conn, desktop_app, "Admin", "Admin / Taruna (Customer Master)", "Admin", customer_pwd)
        _upsert_user_exact(conn, desktop_app, "admin", "admin (Developer - Test Mode)", "Developer", dev_pwd)
        _upsert_user_exact(conn, desktop_app, "taruna", "Admin / Taruna (Customer Master)", "Admin", customer_pwd)

        conn.commit()
        try:
            conn.close()
        except Exception:
            pass
        print("[Auth] Bootstrap forced Admin/admin/taruna passwords for web login")
    except Exception as exc:
        print(f"[Auth] Bootstrap failed: {exc}")


@api.app.get("/api/auth/status")
def web_auth_status(conn: sqlite3.Connection = Depends(api.get_db)):
    try:
        count = conn.execute("SELECT COUNT(*) FROM auth_users WHERE active=1").fetchone()[0]
        employees = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        usernames = [r[0] for r in conn.execute("SELECT username FROM auth_users WHERE active=1 ORDER BY username").fetchall()]
    except Exception:
        count, employees, tasks, usernames = 0, 0, 0, []
    return {
        "user_count": count,
        "usernames": usernames,
        "employee_count": employees,
        "task_count": tasks,
        "setup_required": count == 0,
        "pull": {
            "ok": bool((_LAST_PULL or {}).get("ok")),
            "auth_users": int((_LAST_PULL or {}).get("auth_users") or 0),
            "employees": int((_LAST_PULL or {}).get("employees") or 0),
            "tasks": int((_LAST_PULL or {}).get("tasks") or 0),
            "error": str((_LAST_PULL or {}).get("error") or "")[:240],
        },
        "hint": "Case-sensitive: Admin=customer (Shiva@01); admin=developer (kiran123 or Devlopershouse@1996#).",
    }


@api.app.get("/api/system/db-info")
def web_db_info():
    try:
        import app as desktop_app
        stats = _db_stats(Path(desktop_app.DB_PATH))
    except Exception as exc:
        stats = {"error": str(exc)}
    return {"pull": _LAST_PULL, "local": stats}


_LOGIN_REFRESH_LOCK = threading.Lock()
_LAST_LOGIN_REFRESH_AT = 0.0


def _refresh_login_database_if_needed() -> None:
    global _LAST_LOGIN_REFRESH_AT
    now = time.monotonic()
    if now - _LAST_LOGIN_REFRESH_AT < 15:
        return
    if not _LOGIN_REFRESH_LOCK.acquire(blocking=False):
        return
    try:
        now = time.monotonic()
        if now - _LAST_LOGIN_REFRESH_AT < 15:
            return
        _LAST_LOGIN_REFRESH_AT = now
        if _pull_full_database():
            try:
                import app as desktop_app
                db_path = Path(desktop_app.DB_PATH)
                if PURGE_SEED or PURGE_DEMO:
                    _purge_junk_rows(db_path)
                _ensure_bootstrap_admin(db_path)
            except Exception as exc:
                print(f"[DB Sync] Login refresh cleanup skipped: {exc}")
    finally:
        _LOGIN_REFRESH_LOCK.release()


def _find_active_login_user(conn: sqlite3.Connection, username: str, password: str):
    """Case-sensitive username; Admin != admin. Accepts known web passwords."""
    import app as desktop_app

    row = conn.execute(
        "SELECT * FROM auth_users WHERE username = ? COLLATE BINARY AND active = 1",
        (username,),
    ).fetchone()
    if not row:
        return None

    salt = row["password_salt"]
    stored = row["password_hash"]

    def ok_hash(pw: str) -> bool:
        if not salt or not stored:
            return False
        try:
            _, digest = desktop_app.hash_pin(pw, salt)
            return secrets.compare_digest(str(digest), str(stored))
        except Exception:
            return False

    if ok_hash(password):
        return row

    allowed = []
    if username == "Admin":
        allowed = ["Shiva@01"]
    elif username == "admin":
        allowed = ["kiran123", "Devlopershouse@1996#"]
    elif username.casefold() == "taruna":
        allowed = ["Shiva@01"]

    if password in allowed:
        new_salt, new_digest = desktop_app.hash_pin(password)
        conn.execute(
            "UPDATE auth_users SET password_salt=?, password_hash=?, active=1, updated_at=? WHERE id=?",
            (new_salt, new_digest, desktop_app.now_text(), row["id"]),
        )
        conn.commit()
        print(f"[Auth] Accepted known password for {username!r}; hash updated")
        return conn.execute("SELECT * FROM auth_users WHERE id=?", (row["id"],)).fetchone()

    return None


api.app.router.routes[:] = [
    route for route in api.app.router.routes
    if not (
        getattr(route, "path", None) == "/api/auth/login"
        and "POST" in (getattr(route, "methods", None) or set())
    )
]


@api.app.post("/api/auth/login")
def web_login(req: api.LoginRequest, conn: sqlite3.Connection = Depends(api.get_db)):
    username = (req.username or "").strip()
    password = req.password or ""
    if not username or not password:
        raise HTTPException(status_code=401, detail="Username and password are required")

    row = _find_active_login_user(conn, username, password)
    if not row:
        _refresh_login_database_if_needed()
        try:
            import app as desktop_app
            fresh = sqlite3.connect(str(Path(desktop_app.DB_PATH)), timeout=10)
            fresh.row_factory = sqlite3.Row
            try:
                _ensure_bootstrap_admin(Path(desktop_app.DB_PATH))
                row = _find_active_login_user(fresh, username, password)
            finally:
                fresh.close()
        except Exception as exc:
            print(f"[Auth] Refreshed login retry failed: {exc}")
            row = None

    if not row:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. Use exact case: Admin (customer) or admin (developer).",
        )

    token = secrets.token_hex(24)
    user_info = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
        "role": row["role"],
    }
    api.ACTIVE_SESSIONS[token] = user_info
    print(f"[Auth] Login ok: {user_info['username']!r} ({user_info['role']})")
    return {"token": token, "user": user_info}


@api.app.post("/api/system/sync-now")
def web_sync_now(user: dict = Depends(api.get_current_user)):
    ok = _pull_full_database()
    try:
        import app as desktop_app
        db_path = Path(desktop_app.DB_PATH)
        if PURGE_SEED or PURGE_DEMO:
            _purge_junk_rows(db_path)
        _ensure_bootstrap_admin(db_path)
        stats = _db_stats(db_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync post-process failed: {exc}")
    return {"success": ok, "pull": _LAST_PULL, "local": stats}


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

try:
    import web_ops_routes  # noqa: F401
    print("[Web Boot] Operational routes registered")
except Exception as _exc:
    print(f"[Web Boot] Operational routes skipped: {_exc}")
