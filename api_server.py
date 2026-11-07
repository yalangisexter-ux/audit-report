"""FastAPI REST API server for Raw Strength Calisthenics Employee Audit & Operations OS.
Exposes complete REST endpoints while preserving 100% of underlying SQLite business logic.
"""
import os
import sys
import json
import sqlite3
import secrets
import csv
import io
import re
from pathlib import Path
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

# Ensure repo root is in python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app as desktop_app

# Web-only isolation: the browser service owns its database and never reuses the
# desktop LocalAppData database or the desktop GitHub/Worker synchronization path.
if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
    _web_data_dir = Path(os.environ.get("AUDIT_DATA_DIR") or (ROOT_DIR / "web-data")).expanduser().resolve()
    _web_data_dir.mkdir(parents=True, exist_ok=True)
    desktop_app.APP_DIR = _web_data_dir
    desktop_app.DB_PATH = _web_data_dir / "web_employee_audit.db"
    desktop_app.BACKUP_DIR = _web_data_dir / "backups"
    desktop_app.EXPORT_DIR = _web_data_dir / "exports"
    desktop_app.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    desktop_app.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    class _WebOnlySyncDisabled:
        is_configured = False
        is_dirty = False
        _on_dirty_callback = None
        def __init__(self, *args, **kwargs): pass
        def mark_pending(self, *args, **kwargs): return False
        def request_sync(self, *args, **kwargs): return False
        def schedule_sync(self, *args, **kwargs): return False
        def set_status(self, *args, **kwargs): return False
        def close(self, *args, **kwargs): return None
        def download_latest_snapshot(self, *args, **kwargs): return None
    desktop_app.GitHubDatabaseSync = _WebOnlySyncDisabled

from build_info import APP_VERSION

app = FastAPI(
    title="Raw Strength Calisthenics REST API",
    version=APP_VERSION,
    description="High-performance REST API backend for Raw Strength Calisthenics Employee Audit & Operations OS",
)

# Enable CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_DB_INITIALIZED = False
WEB_SYNC_MANAGER = None


def ensure_database():
    """Initialize the persistent web DB, then restore its installation snapshot."""
    global _DB_INITIALIZED, WEB_SYNC_MANAGER
    if _DB_INITIALIZED:
        return

    db = None
    try:
        db = desktop_app.Database()
        try:
            import business_tracking
            business_tracking.setup_business_tables(db.conn)
        except Exception as exc:
            print(f"[Web DB] Business-table setup note: {exc}")

        standalone = os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes")
        if standalone:
            from web_db_migrations import ensure_case_sensitive_auth_users
            if ensure_case_sensitive_auth_users(desktop_app.DB_PATH):
                print("[Web DB] Migrated auth_users to exact case-sensitive usernames; credentials preserved")
            db.conn.execute(
                """CREATE TABLE IF NOT EXISTS web_auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES auth_users(id) ON DELETE CASCADE
                )"""
            )
            db.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_web_auth_sessions_expiry ON web_auth_sessions(expires_at)"
            )
            db.conn.commit()
    except Exception as exc:
        print(f"[Web DB] Initialization/migration failed: {exc}")
        raise
    finally:
        if db is not None:
            try:
                if hasattr(db, "close_github_sync"):
                    db.close_github_sync(timeout=0)
            except Exception as exc:
                print(f"[Web DB] Desktop sync shutdown note: {exc}")
            try:
                if getattr(db, "conn", None):
                    db.conn.close()
            except Exception:
                pass

    _DB_INITIALIZED = True
    if standalone:
        try:
            from web_sync import WebDatabaseSync
            WEB_SYNC_MANAGER = WebDatabaseSync(desktop_app.DB_PATH)
            restored = WEB_SYNC_MANAGER.bootstrap()
            print(
                "[Web Sync] Initial snapshot restore "
                + ("verified" if restored else "not verified")
                + f"; status={WEB_SYNC_MANAGER.status}; counts={WEB_SYNC_MANAGER.last_pull}"
            )
            WEB_SYNC_MANAGER.start_polling()
        except Exception as exc:
            print(f"[Web Sync] Initialization failed: {exc}")
            WEB_SYNC_MANAGER = None


def get_db():
    """Create a thread-safe connection and mark committed web changes for encrypted sync."""
    ensure_database()
    db_path = desktop_app.DB_PATH
    factory = sqlite3.Connection
    if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
        try:
            from database_sync import SyncableSQLiteConnection
            factory = SyncableSQLiteConnection
        except Exception as exc:
            print(f"[Web Sync] Commit callback unavailable: {exc}")
    conn = sqlite3.connect(
        str(db_path), check_same_thread=False, timeout=30, factory=factory
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    manager = WEB_SYNC_MANAGER
    if manager is not None and getattr(manager, "configured", False) and hasattr(conn, "set_commit_callback"):
        conn.set_commit_callback(manager.mark_pending)
    try:
        yield conn
    finally:
        conn.close()

# Token memory store for lightweight session management
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_current_user(authorization: Optional[str] = Header(None), conn: sqlite3.Connection = Depends(get_db)):
    token = ""
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = value.strip()
    standalone = os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes")
    if token and standalone:
        token_hash = __import__("hashlib").sha256(token.encode("utf-8")).hexdigest()
        session = conn.execute(
            """SELECT u.id, u.username, u.display_name, u.role
               FROM web_auth_sessions s
               JOIN auth_users u ON u.id=s.user_id
               WHERE s.token_hash=? AND s.expires_at>? AND u.active=1""",
            (token_hash, datetime.now().isoformat(timespec="seconds")),
        ).fetchone()
        if session:
            return dict(session)
    elif token and token in ACTIVE_SESSIONS:
        return ACTIVE_SESSIONS[token]
    if os.environ.get("WEB_REQUIRE_LOGIN", "0").strip().lower() in ("1", "true", "yes"):
        raise HTTPException(status_code=401, detail="Login required")
    row = conn.execute("SELECT id, username, display_name, role FROM auth_users WHERE active=1 ORDER BY id ASC LIMIT 1").fetchone()
    if row:
        return dict(row)
    raise HTTPException(status_code=401, detail="Login required")


# ----------------- Models ----------------- #
class LoginRequest(BaseModel):
    username: str
    password: str

class SetupRequest(BaseModel):
    username: str
    display_name: str
    password: str
    security_question: str
    security_answer: str


class RegistrationRequest(BaseModel):
    username: str
    display_name: str
    password: str
    security_question: str
    security_answer: str

class RecoveryQuestionRequest(BaseModel):
    username: str

class PasswordResetRequest(BaseModel):
    username: str
    security_answer: str
    new_password: str

class PasswordChangeRequest(BaseModel):
    username: str
    current_password: str
    new_password: str

class AccountActiveRequest(BaseModel):
    active: bool

class AccountCreateRequest(BaseModel):
    username: str
    display_name: str
    role: str
    password: str
    security_question: str
    security_answer: str

class AccountRoleRequest(BaseModel):
    role: str

class AccountPasswordResetRequest(BaseModel):
    new_password: str

class EmployeeModel(BaseModel):
    name: str
    employee_code: Optional[str] = ""
    department: Optional[str] = ""
    designation: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    joining_date: Optional[str] = ""
    notes: Optional[str] = ""
    active: Optional[int] = 1

class TaskModel(BaseModel):
    employee_id: Optional[int] = 1
    task_date: Optional[str] = None
    title: str
    department: Optional[str] = ""
    details: Optional[str] = ""
    due_time: Optional[str] = ""
    priority: Optional[str] = "Normal"
    status: Optional[str] = "Not started"
    progress: Optional[int] = 0
    target_qty: Optional[str] = ""
    actual_qty: Optional[str] = ""
    next_action: Optional[str] = ""
    proof_url: Optional[str] = ""
    proof_note: Optional[str] = ""
    manager_note: Optional[str] = ""
    expose_link: Optional[int] = 0
    custom_values: Optional[Any] = None
    custom_fields: Optional[Any] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class TaskBulkEditModel(BaseModel):
    task_ids: List[int]
    updates: Dict[str, Any]

class AttendanceMarkModel(BaseModel):
    employee_id: int
    work_date: Optional[str] = None
    attendance_status: Optional[str] = "Present"
    status: Optional[str] = None  # alias for convenience
    check_in: Optional[str] = ""
    check_out: Optional[str] = ""
    break_minutes: Optional[int] = 0
    attendance_note: Optional[str] = ""
    notes: Optional[str] = None  # alias for convenience

class HolidayModel(BaseModel):
    holiday_date: str
    holiday_name: str

class ProductModel(BaseModel):
    name: str
    sku: Optional[str] = ""
    category: Optional[str] = "General"
    brand: Optional[str] = ""
    package_type: Optional[str] = ""
    base_unit: Optional[str] = "PCS"
    opening_stock: Optional[float] = 0.0
    received_qty: Optional[float] = 0.0
    reserved_qty: Optional[float] = 0.0
    dispatched_qty: Optional[float] = 0.0
    free_qty: Optional[float] = 0.0
    returned_qty: Optional[float] = 0.0
    damaged_qty: Optional[float] = 0.0
    expired_qty: Optional[float] = 0.0
    quarantined_qty: Optional[float] = 0.0
    purchase_cost: Optional[float] = 0.0
    selling_price: Optional[float] = 0.0
    reorder_level: Optional[float] = 0.0
    batch_number: Optional[str] = ""
    expiry_date: Optional[str] = ""
    storage_location: Optional[str] = ""

class ServiceModel(BaseModel):
    name: str
    category: Optional[str] = "Training"
    description: Optional[str] = ""
    training_mode: Optional[str] = "Offline"
    service_unit: Optional[str] = "Session"
    session_duration: Optional[int] = 0
    num_sessions: Optional[int] = 0
    plan_validity: Optional[int] = 0
    standard_price: Optional[float] = 0.0
    active: Optional[int] = 1

class ChatMessageModel(BaseModel):
    channel: Optional[str] = "general"
    content: str
    sender_name: Optional[str] = ""

class ReportOptionsModel(BaseModel):
    date: str
    employee_id: Optional[int] = None
    exclude_employee_id: Optional[int] = None
    report_type: Optional[str] = "Audit / EOD"
    options: Optional[Dict[str, bool]] = None
    output_format: Optional[str] = "pdf"


class ReportOptionPreferencesModel(BaseModel):
    options: Dict[str, bool]


# ----------------- Endpoints ----------------- #

@app.get("/api/health")
def health_check(conn: sqlite3.Connection = Depends(get_db)):
    emp_count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    return {
        "status": "healthy",
        "app_name": desktop_app.APP_NAME,
        "version": APP_VERSION,
        "database_connected": True,
        "total_employees": emp_count,
        "total_tasks": task_count,
        "timestamp": datetime.now().isoformat(),
    }


# --- Authentication ---
@app.post("/api/auth/login")
def login(req: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    username = req.username.strip()
    row = conn.execute("SELECT * FROM auth_users WHERE username=? COLLATE BINARY AND active=1", (username,)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    _, digest = desktop_app.hash_pin(req.password, row["password_salt"])
    if not secrets.compare_digest(digest, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = secrets.token_hex(24)
    user_info = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
        "role": row["role"],
    }
    ACTIVE_SESSIONS[token] = user_info
    return {"token": token, "user": user_info}

@app.get("/api/auth/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    return {"user": user}

@app.post("/api/auth/setup")
def initial_setup(req: SetupRequest, conn: sqlite3.Connection = Depends(get_db)):
    standalone = os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes")
    if standalone:
        manager = WEB_SYNC_MANAGER
        verified_empty_snapshot = bool(
            manager is not None
            and getattr(manager, "configured", False)
            and bool(getattr(manager, "last_pull", {}).get("ok"))
            and int(getattr(manager, "last_pull", {}).get("auth_users") or 0) == 0
        )
        explicitly_allowed = os.environ.get("WEB_ALLOW_FIRST_ADMIN_SETUP", "0").strip().lower() in ("1", "true", "yes")
        if not (verified_empty_snapshot and explicitly_allowed):
            raise HTTPException(
                status_code=403,
                detail="First-admin setup is disabled until an empty customer snapshot is verified and WEB_ALLOW_FIRST_ADMIN_SETUP is explicitly enabled.",
            )
    count = conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
    if count > 0:
        raise HTTPException(status_code=400, detail="Setup has already been completed.")
    
    ps, ph = desktop_app.hash_pin(req.password)
    ans_salt, ans_hash = desktop_app.hash_pin(req.security_answer)
    now = desktop_app.now_text()
    
    conn.execute(
        """INSERT INTO auth_users(username, display_name, role, password_salt, password_hash,
                                security_question, answer_salt, answer_hash, active, created_at, updated_at)
           VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
        (req.username.strip(), req.display_name.strip(), "Admin", ps, ph, req.security_question, ans_salt, ans_hash, now, now)
    )
    conn.commit()
    return {"success": True, "message": "Admin account created successfully"}


# --- Account registration, recovery and administration ---
def _require_account_admin(user: Dict[str, Any]):
    if str(user.get("role") or "").strip().casefold() not in {"admin", "developer"}:
        raise HTTPException(status_code=403, detail="Only an Admin or Developer can manage accounts")


def _invalidate_account_sessions(user_id: int, conn: sqlite3.Connection) -> None:
    """Invalidate both in-memory and persistent browser sessions for one account."""
    for token, session in list(ACTIVE_SESSIONS.items()):
        try:
            if int(session.get("id") or 0) == int(user_id):
                ACTIVE_SESSIONS.pop(token, None)
        except (TypeError, ValueError):
            continue
    has_sessions = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='web_auth_sessions'"
    ).fetchone()
    if has_sessions:
        conn.execute("DELETE FROM web_auth_sessions WHERE user_id=?", (int(user_id),))


def _record_account_audit(conn: sqlite3.Connection, action: str, details: str) -> None:
    has_audit = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit_log'"
    ).fetchone()
    if has_audit:
        conn.execute(
            "INSERT INTO audit_log(timestamp,action,details) VALUES(?,?,?)",
            (desktop_app.now_text(), action, details),
        )


@app.post("/api/auth/change-password")
def change_account_password(req: PasswordChangeRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Change an active account password using the same PBKDF2 scheme as the Windows login dialog."""
    username = str(req.username or "").strip()
    row = conn.execute(
        "SELECT * FROM auth_users WHERE username=? COLLATE BINARY AND active=1",
        (username,),
    ).fetchone()
    if row is None:
        matches = conn.execute(
            "SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1",
            (username,),
        ).fetchall()
        row = matches[0] if len(matches) == 1 else None
    if row is None:
        raise HTTPException(status_code=400, detail="No active account found for that username.")

    _, current_digest = desktop_app.hash_pin(req.current_password, row["password_salt"])
    if not secrets.compare_digest(str(current_digest), str(row["password_hash"])):
        raise HTTPException(status_code=403, detail="Current password is incorrect.")
    if not desktop_app.password_is_strong(req.new_password or ""):
        raise HTTPException(status_code=422, detail="Use at least 8 characters, including a letter and a number.")

    salt, digest = desktop_app.hash_pin(req.new_password)
    conn.execute(
        "UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?",
        (salt, digest, desktop_app.now_text(), row["id"]),
    )
    _invalidate_account_sessions(int(row["id"]), conn)
    _record_account_audit(conn, "Password changed", str(row["username"]))
    conn.commit()
    return {"success": True, "message": "Password changed successfully. Sign in with your new password."}


@app.post("/api/auth/register")
def register_account(req: RegistrationRequest, conn: sqlite3.Connection = Depends(get_db)):
    username = str(req.username or "").strip()
    display_name = str(req.display_name or "").strip()
    answer = desktop_app.normalized_answer(str(req.security_answer or ""))
    if not username or len(username) > 64 or not display_name or len(display_name) > 100:
        raise HTTPException(status_code=422, detail="Enter a valid username and display name")
    if not desktop_app.password_is_strong(req.password or ""):
        raise HTTPException(status_code=422, detail="Use at least 8 characters with a letter and a number")
    if len(answer) < 2 or req.security_question not in desktop_app.SECURITY_QUESTIONS:
        raise HTTPException(status_code=422, detail="Choose a recovery question and enter a recovery answer")
    if not conn.execute("SELECT 1 FROM auth_users WHERE active=1 AND role IN ('Admin','Developer') LIMIT 1").fetchone():
        raise HTTPException(status_code=403, detail="An active Admin must complete initial setup before new account registration")
    if conn.execute("SELECT 1 FROM auth_users WHERE username=? COLLATE BINARY", (username,)).fetchone():
        raise HTTPException(status_code=409, detail="That username already exists")
    password_salt, password_hash = desktop_app.hash_pin(req.password)
    answer_salt, answer_hash = desktop_app.hash_pin(answer)
    now = desktop_app.now_text()
    try:
        conn.execute(
            """INSERT INTO auth_users(username,display_name,role,password_salt,password_hash,
               security_question,answer_salt,answer_hash,active,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,0,?,?)""",
            (username, display_name, "Staff", password_salt, password_hash,
             req.security_question, answer_salt, answer_hash, now, now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That username already exists")
    return {"success": True, "pending_approval": True,
            "message": "Account request submitted. An Admin must activate the account before sign-in."}


@app.post("/api/auth/recovery-question")
def get_recovery_question(req: RecoveryQuestionRequest, conn: sqlite3.Connection = Depends(get_db)):
    username = str(req.username or "").strip()
    row = conn.execute(
        "SELECT security_question, answer_salt, answer_hash FROM auth_users WHERE username=? COLLATE BINARY AND active=1",
        (username,),
    ).fetchone()
    if row is None:
        matches = conn.execute(
            "SELECT security_question, answer_salt, answer_hash FROM auth_users WHERE username=? COLLATE NOCASE AND active=1",
            (username,),
        ).fetchall()
        row = matches[0] if len(matches) == 1 else None
    if not row or not row["security_question"] or not row["answer_salt"] or not row["answer_hash"]:
        raise HTTPException(status_code=404, detail="No password-recovery question is configured for this active account. Contact an Admin.")
    return {"security_question": row["security_question"]}


@app.post("/api/auth/password-reset")
def reset_account_password(req: PasswordResetRequest, conn: sqlite3.Connection = Depends(get_db)):
    username = str(req.username or "").strip()
    answer = desktop_app.normalized_answer(str(req.security_answer or ""))
    row = conn.execute(
        "SELECT * FROM auth_users WHERE username=? COLLATE BINARY AND active=1", (username,)
    ).fetchone()
    if row is None:
        matches = conn.execute(
            "SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1", (username,)
        ).fetchall()
        row = matches[0] if len(matches) == 1 else None
    if not row or not row["answer_salt"] or not row["answer_hash"]:
        raise HTTPException(status_code=400, detail="Password recovery is unavailable for this account. Contact an Admin.")
    _, answer_hash = desktop_app.hash_pin(answer, row["answer_salt"])
    if not secrets.compare_digest(str(answer_hash), str(row["answer_hash"])):
        raise HTTPException(status_code=403, detail="Recovery answer is incorrect")
    if not desktop_app.password_is_strong(req.new_password or ""):
        raise HTTPException(status_code=422, detail="Use at least 8 characters with a letter and a number")
    salt, digest = desktop_app.hash_pin(req.new_password)
    conn.execute(
        "UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?",
        (salt, digest, desktop_app.now_text(), row["id"]),
    )
    if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
        conn.execute("DELETE FROM web_auth_sessions WHERE user_id=?", (row["id"],))
    else:
        for token, user in list(ACTIVE_SESSIONS.items()):
            if int(user.get("id") or 0) == int(row["id"]):
                ACTIVE_SESSIONS.pop(token, None)
    conn.commit()
    return {"success": True, "message": "Password reset successfully. Sign in with your new password."}


@app.get("/api/auth/users")
def list_auth_users(user: Dict[str, Any] = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    _require_account_admin(user)
    rows = conn.execute(
        "SELECT id,username,display_name,role,active,created_at,updated_at FROM auth_users ORDER BY username COLLATE NOCASE"
    ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/auth/users")
def create_managed_account(
    item: AccountCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    _require_account_admin(user)
    username = str(item.username or "").strip()
    display_name = str(item.display_name or "").strip()
    role = str(item.role or "").strip()
    answer = desktop_app.normalized_answer(str(item.security_answer or ""))
    allowed_roles = {"Staff", "HR", "Admin", "Developer"}
    if not username or len(username) > 64 or not display_name or len(display_name) > 100:
        raise HTTPException(status_code=422, detail="Enter a valid username and display name")
    if role not in allowed_roles:
        raise HTTPException(status_code=422, detail="Select a valid account role")
    caller_role = str(user.get("role") or "").casefold()
    if role == "Developer" and caller_role != "developer":
        raise HTTPException(status_code=403, detail="Only a Developer can create a Developer account")
    if not desktop_app.password_is_strong(item.password or ""):
        raise HTTPException(status_code=422, detail="Use at least 8 characters with a letter and a number")
    if item.security_question not in desktop_app.SECURITY_QUESTIONS or len(answer) < 2:
        raise HTTPException(status_code=422, detail="Select a recovery question and enter a valid recovery answer")
    if conn.execute(
        "SELECT 1 FROM auth_users WHERE username=? COLLATE BINARY",
        (username,),
    ).fetchone():
        raise HTTPException(status_code=409, detail="That username already exists.")
    password_salt, password_hash = desktop_app.hash_pin(item.password)
    answer_salt, answer_hash = desktop_app.hash_pin(answer)
    now = desktop_app.now_text()
    cursor = conn.execute(
        """INSERT INTO auth_users(
               username,display_name,role,password_salt,password_hash,
               security_question,answer_salt,answer_hash,active,created_at,updated_at
           ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
        (username, display_name, role, password_salt, password_hash,
         item.security_question, answer_salt, answer_hash, now, now),
    )
    _record_account_audit(conn, "User account created", f"{username} ({role})")
    conn.commit()
    return {"success": True, "user_id": int(cursor.lastrowid), "username": username, "role": role, "active": True}


@app.patch("/api/auth/users/{user_id}/active")
def set_auth_user_active(
    user_id: int,
    item: AccountActiveRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    _require_account_admin(user)
    if int(user.get("id") or 0) == int(user_id) and not item.active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    target = conn.execute("SELECT id,username,role,active FROM auth_users WHERE id=?", (user_id,)).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="Account not found")
    caller_role = str(user.get("role") or "").casefold()
    if str(target["role"]).casefold() == "developer" and caller_role != "developer":
        raise HTTPException(status_code=403, detail="Only a Developer can change a Developer account")
    if not item.active and str(target["role"]).casefold() == "admin":
        remaining = conn.execute(
            "SELECT COUNT(*) FROM auth_users WHERE active=1 AND role='Admin' AND id<>?", (user_id,)
        ).fetchone()[0]
        if remaining < 1:
            raise HTTPException(status_code=409, detail="The last active Admin account cannot be deactivated")
    conn.execute(
        "UPDATE auth_users SET active=?,updated_at=? WHERE id=?",
        (1 if item.active else 0, desktop_app.now_text(), user_id),
    )
    if not item.active:
        _invalidate_account_sessions(user_id, conn)
    _record_account_audit(
        conn,
        "User status changed",
        f"{target['username']}: {'Active' if item.active else 'Disabled'}",
    )
    conn.commit()
    return {"success": True, "user_id": user_id, "active": item.active}


@app.patch("/api/auth/users/{user_id}/role")
def set_auth_user_role(
    user_id: int,
    item: AccountRoleRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    _require_account_admin(user)
    new_role = str(item.role or "").strip()
    allowed_roles = {"Staff", "HR", "Admin", "Developer"}
    if new_role not in allowed_roles:
        raise HTTPException(status_code=422, detail="Select a valid account role")
    target = conn.execute("SELECT id,username,role,active FROM auth_users WHERE id=?", (user_id,)).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="Account not found")
    caller_role = str(user.get("role") or "").casefold()
    if (str(target["role"]).casefold() == "developer" or new_role == "Developer") and caller_role != "developer":
        raise HTTPException(status_code=403, detail="Only a Developer can change or assign a Developer account")
    if str(target["role"]).casefold() == "admin" and new_role != "Admin" and int(target["active"] or 0):
        remaining = conn.execute(
            "SELECT COUNT(*) FROM auth_users WHERE active=1 AND role='Admin' AND id<>?",
            (user_id,),
        ).fetchone()[0]
        if remaining < 1:
            raise HTTPException(status_code=409, detail="The last active Admin cannot be changed to a non-Admin role")
    if str(target["role"]) == new_role:
        return {"success": True, "user_id": user_id, "role": new_role, "unchanged": True}
    conn.execute(
        "UPDATE auth_users SET role=?,updated_at=? WHERE id=?",
        (new_role, desktop_app.now_text(), user_id),
    )
    _record_account_audit(conn, "User role changed", f"{target['username']} -> {new_role}")
    _invalidate_account_sessions(user_id, conn)
    conn.commit()
    return {"success": True, "user_id": user_id, "role": new_role}


@app.post("/api/auth/users/{user_id}/password-reset")
def reset_managed_account_password(
    user_id: int,
    item: AccountPasswordResetRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    _require_account_admin(user)
    target = conn.execute("SELECT id,username,role FROM auth_users WHERE id=?", (user_id,)).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="Account not found")
    caller_role = str(user.get("role") or "").casefold()
    if str(target["role"]).casefold() == "developer" and caller_role != "developer":
        raise HTTPException(status_code=403, detail="Only a Developer can reset a Developer account password")
    if not desktop_app.password_is_strong(item.new_password or ""):
        raise HTTPException(status_code=422, detail="Use at least 8 characters with a letter and a number")
    salt, digest = desktop_app.hash_pin(item.new_password)
    conn.execute(
        "UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?",
        (salt, digest, desktop_app.now_text(), user_id),
    )
    _record_account_audit(conn, "User password reset by admin", target["username"])
    _invalidate_account_sessions(user_id, conn)
    conn.commit()
    return {"success": True, "user_id": user_id, "message": "Password reset successfully. The account must sign in again."}


# --- Home workspace business snapshot ---
@app.get("/api/home/business-snapshot")
def get_home_business_snapshot(
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Return the business counters shown on the desktop Home workspace."""
    from business_tracking import available_stock

    products = conn.execute("SELECT * FROM bt_products ORDER BY name COLLATE NOCASE ASC").fetchall()
    low_stock = 0
    for product in products:
        reorder_level = float(product["reorder_level"] or 0)
        if reorder_level > 0 and available_stock(product) <= reorder_level:
            low_stock += 1

    orders = conn.execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(order_value), 0) AS sales FROM bt_orders"
    ).fetchone()
    active_members = conn.execute(
        "SELECT COUNT(*) FROM bt_members WHERE status='Active'"
    ).fetchone()[0]
    activities = conn.execute("SELECT COUNT(*) FROM bt_activities").fetchone()[0]

    return {
        "version": APP_VERSION,
        "products": len(products),
        "low_stock": low_stock,
        "orders": int(orders["total"] or 0),
        "members": int(active_members or 0),
        "activities": int(activities or 0),
        "total_sales": float(orders["sales"] or 0),
    }


# --- Dashboard Analytics ---
@app.get("/api/dashboard")
def get_dashboard(conn: sqlite3.Connection = Depends(get_db), user: Dict[str, Any] = Depends(get_current_user)):
    """Return the desktop dashboard's active roster, daily telemetry, and productivity metrics."""
    from datetime import timedelta

    today = date.today()
    today_str = today.isoformat()
    employees = [
        dict(row)
        for row in conn.execute(
            """SELECT id, employee_code, name, department, designation, joining_date,
                      active, display_order
               FROM employees
               WHERE active=1
               ORDER BY display_order ASC, name COLLATE NOCASE"""
        ).fetchall()
    ]
    employee_ids = [int(employee["id"]) for employee in employees]
    placeholders = ",".join("?" for _ in employee_ids)

    attendance_by_id = {}
    if employee_ids:
        for row in conn.execute(
            f"""SELECT employee_id, attendance_status, check_in, check_out
                FROM attendance
                WHERE work_date=? AND employee_id IN ({placeholders})""",
            (today_str, *employee_ids),
        ).fetchall():
            attendance_by_id[int(row["employee_id"])] = dict(row)

    present_today = absent_today = leave_today = checkins_today = 0
    attendance_roster = []
    for employee in employees:
        record = attendance_by_id.get(int(employee["id"]))
        status = str((record or {}).get("attendance_status") or "Unmarked").strip()
        check_in = str((record or {}).get("check_in") or "").strip()
        check_out = str((record or {}).get("check_out") or "").strip()
        normalized_status = status.casefold()
        has_check_in = bool(check_in)
        if desktop_app.is_present_attendance_status(status) or (
            normalized_status == "unmarked" and has_check_in
        ):
            if normalized_status == "unmarked":
                status = "Present"
            present_today += 1
            if has_check_in:
                checkins_today += 1
        elif normalized_status == "absent":
            status = "Absent"
            absent_today += 1
        elif normalized_status == "leave":
            status = "Leave"
            leave_today += 1
        elif normalized_status in {"unmarked", "", "not checked"}:
            status = "Not checked"
        else:
            status = desktop_app.task_status_label(status)
        attendance_roster.append(
            {
                "employee_id": employee["id"],
                "name": employee["name"],
                "status": status,
                "check_in": check_in or "—",
                "check_out": check_out or "—",
            }
        )

    # Match Database.tasks(report_date): all statuses, employee ordering, and the
    # first twelve visible rows. KPI counts are computed from the complete day.
    today_tasks_all = [
        dict(row)
        for row in conn.execute(
            """SELECT t.id, t.employee_id, t.title, t.status, t.progress, t.due_time,
                      t.priority, t.task_date, e.name AS employee_name, e.employee_code,
                      COALESCE(NULLIF(t.department, ''), e.department, '') AS department
               FROM tasks t
               JOIN employees e ON e.id=t.employee_id
               WHERE t.task_date=?
               ORDER BY e.display_order ASC, e.name COLLATE NOCASE, t.id DESC""",
            (today_str,),
        ).fetchall()
    ]
    open_tasks = sum(
        1 for task in today_tasks_all
        if not desktop_app.is_explicitly_completed_task_status(task["status"])
        and not desktop_app.is_cancelled_task_status(task["status"])
    )
    completed_tasks = sum(
        1 for task in today_tasks_all
        if desktop_app.is_explicitly_completed_task_status(task["status"])
    )

    # Resolve each employee's desktop tracking start in one batched query. A valid
    # joining date wins; otherwise use the first task/attendance record, then today.
    start_by_id = {}
    activity_by_id = {}
    if employee_ids:
        activity_rows = conn.execute(
            f"""SELECT employee_id, MIN(activity_date) AS first_date
                FROM (
                    SELECT employee_id, task_date AS activity_date
                    FROM tasks
                    WHERE employee_id IN ({placeholders}) AND task_date<=?
                    UNION ALL
                    SELECT employee_id, work_date AS activity_date
                    FROM attendance
                    WHERE employee_id IN ({placeholders}) AND work_date<=?
                )
                GROUP BY employee_id""",
            (*employee_ids, today_str, *employee_ids, today_str),
        ).fetchall()
        activity_by_id = {
            int(row["employee_id"]): row["first_date"] for row in activity_rows
        }

        for employee in employees:
            employee_id = int(employee["id"])
            start = None
            if employee.get("joining_date"):
                try:
                    start = date.fromisoformat(str(employee["joining_date"]))
                except (TypeError, ValueError):
                    start = None
            if start is None and activity_by_id.get(employee_id):
                try:
                    start = date.fromisoformat(str(activity_by_id[employee_id]))
                except (TypeError, ValueError):
                    start = None
            start_by_id[employee_id] = start or today

    productivity = []
    avg_productivity = 0.0
    if employee_ids:
        earliest_start = min(start_by_id.values()).isoformat()
        task_history = conn.execute(
            f"""SELECT employee_id, task_date, progress, status
                FROM tasks
                WHERE employee_id IN ({placeholders})
                  AND task_date BETWEEN ? AND ?""",
            (*employee_ids, earliest_start, today_str),
        ).fetchall()
        attendance_history = conn.execute(
            f"""SELECT employee_id, work_date, attendance_status, check_in
                FROM attendance
                WHERE employee_id IN ({placeholders})
                  AND work_date BETWEEN ? AND ?""",
            (*employee_ids, earliest_start, today_str),
        ).fetchall()
        holiday_rows = conn.execute(
            "SELECT holiday_date FROM holidays WHERE holiday_date BETWEEN ? AND ?",
            (earliest_start, today_str),
        ).fetchall()
        holidays = {str(row["holiday_date"]) for row in holiday_rows}
        weekdays = desktop_app.working_weekdays_from_connection(conn)

        tasks_by_employee = {employee_id: [] for employee_id in employee_ids}
        attendance_by_employee = {employee_id: [] for employee_id in employee_ids}
        for row in task_history:
            tasks_by_employee[int(row["employee_id"])].append(row)
        for row in attendance_history:
            attendance_by_employee[int(row["employee_id"])].append(row)

        scores = []
        for employee in employees:
            employee_id = int(employee["id"])
            start = start_by_id[employee_id]
            start_text = start.isoformat()
            employee_tasks = [
                row for row in tasks_by_employee[employee_id]
                if start_text <= str(row["task_date"] or "") <= today_str
            ]
            task_progress_total = 0
            for task in employee_tasks:
                if not desktop_app.is_known_task_status(task["status"]):
                    continue
                try:
                    progress = int(float(task["progress"] or 0))
                except (TypeError, ValueError, OverflowError):
                    progress = 0
                task_progress_total += max(0, min(100, progress))
            # Match the desktop denominator: every task row is counted, while
            # unknown/unselected statuses contribute zero progress.
            task_score = (
                task_progress_total / len(employee_tasks) if employee_tasks else None
            )

            employee_attendance = [
                row for row in attendance_by_employee[employee_id]
                if start_text <= str(row["work_date"] or "") <= today_str
            ]

            def is_scheduled_workday(day_text):
                try:
                    work_day = date.fromisoformat(str(day_text))
                except (TypeError, ValueError):
                    return False
                return work_day.weekday() in weekdays and str(day_text) not in holidays

            working_days = 0
            current_day = start
            while current_day <= today:
                day_text = current_day.isoformat()
                if current_day.weekday() in weekdays and day_text not in holidays:
                    working_days += 1
                current_day += timedelta(days=1)

            leave_days = sum(
                1 for row in employee_attendance
                if str(row["attendance_status"] or "").strip().casefold() == "leave"
                and is_scheduled_workday(row["work_date"])
            )
            attendance_eligible_days = max(0, working_days - leave_days)
            present_count = sum(
                1 for row in employee_attendance
                if is_scheduled_workday(row["work_date"])
                and (
                    desktop_app.is_present_attendance_status(row["attendance_status"])
                    or (
                        str(row["attendance_status"] or "").strip().casefold() in {"unmarked", ""}
                        and bool(str(row["check_in"] or "").strip())
                    )
                )
            )
            attendance_score = (
                present_count / attendance_eligible_days * 100
                if attendance_eligible_days else None
            )

            if task_score is not None and attendance_score is not None:
                score = round(task_score * 0.7 + attendance_score * 0.3)
            elif task_score is not None:
                score = round(task_score)
            elif attendance_score is not None:
                score = round(attendance_score)
            else:
                score = 0
            completed = sum(
                1 for task in employee_tasks
                if desktop_app.is_explicitly_completed_task_status(task["status"])
            )
            scores.append(score)
            productivity.append(
                {
                    "employee_id": employee_id,
                    "name": employee["name"],
                    "active": bool(employee["active"]),
                    "score": score,
                    "working_days": working_days,
                    "attendance_eligible_days": attendance_eligible_days,
                    "present_count": present_count,
                    "task_count": len(employee_tasks),
                    "completed": completed,
                    "tracking_start": start_text,
                    "task_score": round(task_score, 1) if task_score is not None else None,
                    "attendance_score": round(attendance_score, 1) if attendance_score is not None else None,
                }
            )
        avg_productivity = round(sum(scores) / len(scores), 1) if scores else 0.0

    total_employees = len(employees)
    not_checked_today = max(
        0, total_employees - present_today - absent_today - leave_today
    )
    attendance_rate = round(present_today / total_employees * 100) if total_employees else 0
    recent_employees = list(reversed(employees[-8:]))

    return {
        "today": today_str,
        "kpis": {
            "total_employees": total_employees,
            "present_today": present_today,
            "absent_today": absent_today,
            "leave_today": leave_today,
            "not_checked_today": not_checked_today,
            "open_tasks": open_tasks,
            "completed_tasks": completed_tasks,
            "checkins_today": checkins_today,
            "attendance_rate": attendance_rate,
            "avg_productivity": avg_productivity,
        },
        "recent_employees": recent_employees,
        "today_tasks": today_tasks_all[:12],
        "attendance_roster": attendance_roster[:8],
        "productivity": productivity,
        "attendance_summary": (
            f"{attendance_rate}% checked in\n"
            f"{present_today} Present  ·  {absent_today} Absent  ·  "
            f"{leave_today} Leave  ·  {not_checked_today} Not checked"
        ),
    }


# --- Employees ---
def _require_employee_roles(user, allowed_roles):
    role = str((user or {}).get("role", "")).strip().casefold()
    allowed = {str(value).strip().casefold() for value in allowed_roles}
    if role not in allowed:
        raise HTTPException(status_code=403, detail="You do not have permission to modify employee records.")


def _ensure_employee_group(conn, department, timestamp):
    name = str(department or "").strip()
    if not name:
        return
    existing = conn.execute("SELECT 1 FROM employee_groups WHERE name=? COLLATE NOCASE", (name,)).fetchone()
    if not existing:
        maximum = conn.execute("SELECT COALESCE(MAX(display_order), 0) AS value FROM employee_groups").fetchone()
        next_order = int((maximum["value"] if maximum else 0) or 0) + 10
        conn.execute("INSERT INTO employee_groups(name, display_order, created_at) VALUES(?,?,?)", (name, next_order, timestamp))


@app.get("/api/employees")
def list_employees(search: Optional[str] = None, department: Optional[str] = None, active_only: bool = True, conn: sqlite3.Connection = Depends(get_db), user: Dict[str, Any] = Depends(get_current_user)):
    query = "SELECT * FROM employees WHERE 1=1"
    params = []
    if active_only:
        query += " AND active=1"
    if department:
        query += " AND department=?"
        params.append(department)
    if search:
        query += " AND (name LIKE ? OR employee_code LIKE ? OR designation LIKE ? OR department LIKE ? OR phone LIKE ? OR email LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term, term, term, term, term])
    query += " ORDER BY active DESC, display_order ASC, name COLLATE NOCASE, id ASC"
    return [dict(row) for row in conn.execute(query, params).fetchall()]


@app.get("/api/employees/export.csv")
def export_employees_csv(
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Export every employee, including inactive records, in the Windows CSV format."""
    rows = conn.execute(
        "SELECT * FROM employees ORDER BY active DESC, display_order ASC, name COLLATE NOCASE"
    ).fetchall()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "Record ID", "Employee ID", "Name", "Department", "Role",
        "Phone", "Email", "Joining date", "Status", "Notes",
    ])
    for employee in rows:
        writer.writerow([
            employee["id"],
            employee["employee_code"],
            employee["name"],
            employee["department"],
            employee["designation"],
            employee["phone"],
            employee["email"],
            employee["joining_date"],
            "Active" if employee["active"] else "Inactive",
            employee["notes"],
        ])
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="employees.csv"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/api/employees")
def create_employee(emp: EmployeeModel, conn: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    _require_employee_roles(user, {"HR", "Admin", "Developer"})
    name = (emp.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Employee name is required.")
    email = (emp.email or "").strip()
    if email and ("@" not in email or "." not in email.split("@")[-1]):
        raise HTTPException(status_code=400, detail="Enter a valid email address or leave it blank.")
    now = desktop_app.now_text()
    code = (emp.employee_code or "").strip() or f"EMP{secrets.token_hex(2).upper()}"
    department = (emp.department or "").strip()
    active = 1 if emp.active is None or bool(emp.active) else 0
    try:
        cursor = conn.execute(
            """INSERT INTO employees(name, employee_code, department, designation, phone, email, joining_date, notes, active, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (name, code, department, (emp.designation or "").strip(), (emp.phone or "").strip(), email,
             (emp.joining_date or "").strip(), (emp.notes or "").strip(), active, now)
        )
        _ensure_employee_group(conn, department, now)
        conn.commit()
        return {"id": cursor.lastrowid, "success": True, "employee_code": code}
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Employee code '{code}' already exists")


@app.put("/api/employees/{emp_id}")
def update_employee(emp_id: int, emp: EmployeeModel, conn: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    _require_employee_roles(user, {"HR", "Admin", "Developer"})
    existing = conn.execute("SELECT employee_code FROM employees WHERE id=?", (emp_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")
    name = (emp.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Employee name is required.")
    email = (emp.email or "").strip()
    if email and ("@" not in email or "." not in email.split("@")[-1]):
        raise HTTPException(status_code=400, detail="Enter a valid email address or leave it blank.")
    code = (emp.employee_code or "").strip() or existing["employee_code"]
    department = (emp.department or "").strip()
    active = 1 if emp.active is None or bool(emp.active) else 0
    try:
        conn.execute(
            """UPDATE employees SET name=?, employee_code=?, department=?, designation=?, phone=?, email=?,
                                   joining_date=?, notes=?, active=? WHERE id=?""",
            (name, code, department, (emp.designation or "").strip(), (emp.phone or "").strip(), email,
             (emp.joining_date or "").strip(), (emp.notes or "").strip(), active, emp_id)
        )
        _ensure_employee_group(conn, department, desktop_app.now_text())
        conn.commit()
        return {"success": True}
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Employee code '{code}' already exists")


@app.delete("/api/employees/{emp_id}")
def delete_employee(emp_id: int, conn: sqlite3.Connection = Depends(get_db), user=Depends(get_current_user)):
    # Preserve the legacy soft-toggle contract for existing clients.
    _require_employee_roles(user, {"HR", "Admin", "Developer"})
    row = conn.execute("SELECT active FROM employees WHERE id=?", (emp_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    new_active = 0 if row["active"] == 1 else 1
    conn.execute("UPDATE employees SET active=? WHERE id=?", (new_active, emp_id))
    conn.commit()
    return {"success": True, "active": new_active}


# --- Tasks ---
def _task_custom_values(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _validate_task_fields(task):
    title = str(task.title or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Task title is required.")
    task_date = str(task.task_date or date.today().isoformat()).strip()
    try:
        task_date = date.fromisoformat(task_date).isoformat()
    except ValueError:
        raise HTTPException(status_code=422, detail="Task date must use YYYY-MM-DD format.")
    due_time = str(task.due_time or "").strip()
    if due_time:
        try:
            datetime.strptime(due_time, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=422, detail="Due time must use HH:MM format.")
    progress = int(task.progress or 0)
    if progress < 0 or progress > 100:
        raise HTTPException(status_code=422, detail="Task progress must be between 0 and 100.")
    status = "Not started" if task.status is None else str(task.status).strip()
    if status == "Completed":
        progress = 100
    next_action = str(task.next_action or task.manager_note or "").strip()
    manager_note = str(task.manager_note or task.next_action or "").strip()
    custom_source = task.custom_values if task.custom_values is not None else task.custom_fields
    return {
        "employee_id": int(task.employee_id or 1),
        "task_date": task_date,
        "title": title,
        "department": str(task.department or task.category or "").strip(),
        "details": str(task.details or task.notes or "").strip(),
        "due_time": due_time,
        "priority": str(task.priority or "Normal").strip(),
        "status": status,
        "progress": progress,
        "target_qty": str(task.target_qty or "").strip(),
        "actual_qty": str(task.actual_qty or "").strip(),
        "next_action": next_action,
        "proof_url": str(task.proof_url or "").strip(),
        "proof_note": str(task.proof_note or "").strip(),
        "manager_note": manager_note,
        "expose_link": 1 if bool(task.expose_link) else 0,
        "custom_values": _task_custom_values(custom_source),
    }


def _sync_employee_target_from_task(conn, task, values, now):
    """Keep the desktop's per-employee/per-day target record in sync with task edits."""
    fields_set = set(
        getattr(task, "model_fields_set", getattr(task, "__fields_set__", set())) or ()
    )
    if not fields_set.intersection({"target_qty", "actual_qty"}):
        return
    employee_id = int(values["employee_id"])
    target_date = str(values["task_date"])
    existing = conn.execute(
        "SELECT target,target_status FROM employee_targets WHERE employee_id=? AND target_date=?",
        (employee_id, target_date),
    ).fetchone()
    target = values["target_qty"] if "target_qty" in fields_set else (existing["target"] if existing else "")
    target_status = values["actual_qty"] if "actual_qty" in fields_set else (existing["target_status"] if existing else "")
    conn.execute(
        """INSERT INTO employee_targets(employee_id,target_date,target,target_status,updated_at)
           VALUES(?,?,?,?,?)
           ON CONFLICT(employee_id,target_date) DO UPDATE SET
             target=excluded.target,
             target_status=excluded.target_status,
             updated_at=excluded.updated_at""",
        (employee_id, target_date, str(target or "").strip(), str(target_status or "").strip(), now),
    )

@app.get("/api/tasks")
def list_tasks(
    employee_id: Optional[int] = None,
    task_date: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    department: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = """
        SELECT t.*, e.name as employee_name, e.employee_code
        FROM tasks t
        LEFT JOIN employees e ON t.employee_id = e.id
        WHERE 1=1
    """
    params = []
    if employee_id:
        query += " AND t.employee_id=?"
        params.append(employee_id)
    if task_date:
        try:
            task_date = date.fromisoformat(str(task_date)).isoformat()
        except ValueError:
            raise HTTPException(status_code=422, detail="task_date must use YYYY-MM-DD format.")
        query += " AND t.task_date=?"
        params.append(task_date)
    if status is not None:
        query += " AND t.status=?"
        params.append(status)
    if priority:
        query += " AND t.priority=?"
        params.append(priority)
    if department:
        query += " AND t.department=?"
        params.append(department)

    query += " ORDER BY t.task_date DESC, t.id DESC"
    rows = conn.execute(query, params).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        raw = item.get("custom_values") or ""
        parsed = []
        if raw:
            try:
                decoded = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(decoded, list):
                    parsed = decoded
                else:
                    parsed = [{"key": key, "value": value} for key, value in desktop_app.parse_custom_values(decoded)]
            except Exception:
                parsed = [{"key": key, "value": value} for key, value in desktop_app.parse_custom_values(raw)]
        item["custom_fields"] = parsed
        result.append(item)
    return result


@app.get("/api/employee-targets")
def get_employee_target(
    employee_id: int,
    target_date: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        selected_date = date.fromisoformat(str(target_date)).isoformat()
    except ValueError:
        raise HTTPException(status_code=422, detail="target_date must use YYYY-MM-DD format.")
    if not conn.execute("SELECT 1 FROM employees WHERE id=?", (employee_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Employee not found.")
    row = conn.execute(
        "SELECT target,target_status FROM employee_targets WHERE employee_id=? AND target_date=?",
        (employee_id, selected_date),
    ).fetchone()
    return {
        "employee_id": employee_id,
        "target_date": selected_date,
        "target": (row["target"] if row else "") or "",
        "target_status": (row["target_status"] if row else "") or "",
    }

@app.post("/api/tasks")
def create_task(
    task: TaskModel,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    now = desktop_app.now_text()
    values = _validate_task_fields(task)
    submitted_at = now if values["status"] in ("Submitted", "Completed") else ""
    cursor = conn.execute(
        """INSERT INTO tasks(
               employee_id, task_date, title, department, details, due_time, priority, status,
               progress, target_qty, actual_qty, next_action, proof_url, proof_note,
               submitted_at, manager_note, expose_link, custom_values, created_at, updated_at
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            values["employee_id"], values["task_date"], values["title"], values["department"],
            values["details"], values["due_time"], values["priority"], values["status"],
            values["progress"], values["target_qty"], values["actual_qty"], values["next_action"],
            values["proof_url"], values["proof_note"], submitted_at, values["manager_note"],
            values["expose_link"], values["custom_values"], now, now,
        ),
    )
    _sync_employee_target_from_task(conn, task, values, now)
    conn.commit()
    return {
        "id": cursor.lastrowid,
        "success": True,
        "status": values["status"],
        "progress": values["progress"],
        "submitted_at": submitted_at,
    }


@app.put("/api/tasks/{task_id}")
def update_task(
    task_id: int,
    task: TaskModel,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    existing = conn.execute("SELECT submitted_at,target_qty,actual_qty FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found.")
    now = desktop_app.now_text()
    values = _validate_task_fields(task)
    fields_set = set(getattr(task, "model_fields_set", getattr(task, "__fields_set__", set())) or ())
    if "target_qty" not in fields_set:
        values["target_qty"] = existing["target_qty"] or ""
    if "actual_qty" not in fields_set:
        values["actual_qty"] = existing["actual_qty"] or ""
    submitted_at = (existing["submitted_at"] or "").strip()
    if not submitted_at and values["status"] in ("Submitted", "Completed"):
        submitted_at = now
    conn.execute(
        """UPDATE tasks SET
               employee_id=?, task_date=?, title=?, department=?, details=?, due_time=?, priority=?,
               status=?, progress=?, target_qty=?, actual_qty=?, next_action=?, proof_url=?, proof_note=?,
               submitted_at=?, manager_note=?, expose_link=?, custom_values=?, updated_at=?
           WHERE id=?""",
        (
            values["employee_id"], values["task_date"], values["title"], values["department"],
            values["details"], values["due_time"], values["priority"], values["status"],
            values["progress"], values["target_qty"], values["actual_qty"], values["next_action"],
            values["proof_url"], values["proof_note"], submitted_at, values["manager_note"],
            values["expose_link"], values["custom_values"], now, task_id,
        ),
    )
    _sync_employee_target_from_task(conn, task, values, now)
    conn.commit()
    return {
        "id": task_id,
        "success": True,
        "status": values["status"],
        "progress": values["progress"],
        "submitted_at": submitted_at,
    }


@app.post("/api/tasks/bulk-edit")
def bulk_edit_tasks(
    payload: TaskBulkEditModel,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    task_ids = list(dict.fromkeys(int(value) for value in payload.task_ids))
    if not task_ids:
        raise HTTPException(status_code=422, detail="Select at least one task.")
    if len(task_ids) > 500:
        raise HTTPException(status_code=422, detail="A bulk edit can update at most 500 tasks.")
    updates = dict(payload.updates or {})
    allowed = {
        "title", "department", "details", "due_time", "priority", "status", "progress",
        "target_qty", "actual_qty", "next_action", "proof_url", "proof_note",
        "manager_note", "expose_link", "custom_values",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail="Unsupported bulk task field(s): " + ", ".join(sorted(unknown)))
    if not updates:
        raise HTTPException(status_code=422, detail="Choose at least one field to update.")
    if "title" in updates and not str(updates["title"] or "").strip():
        raise HTTPException(status_code=422, detail="Task title cannot be blank.")
    if "progress" in updates:
        try:
            updates["progress"] = int(updates["progress"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Task progress must be a whole number.")
        if updates["progress"] < 0 or updates["progress"] > 100:
            raise HTTPException(status_code=422, detail="Task progress must be between 0 and 100.")
    if "expose_link" in updates:
        updates["expose_link"] = 1 if bool(updates["expose_link"]) else 0
    if "custom_values" in updates:
        updates["custom_values"] = _task_custom_values(updates["custom_values"])
    if "next_action" in updates and "manager_note" not in updates:
        updates["manager_note"] = updates["next_action"]
    elif "manager_note" in updates and "next_action" not in updates:
        updates["next_action"] = updates["manager_note"]
    if updates.get("status") == "Completed":
        updates["progress"] = 100

    marks = ",".join("?" for _ in task_ids)
    rows = conn.execute(
        f"SELECT id, submitted_at FROM tasks WHERE id IN ({marks})",
        task_ids,
    ).fetchall()
    if len(rows) != len(task_ids):
        raise HTTPException(status_code=404, detail="One or more selected tasks no longer exist.")

    now = desktop_app.now_text()
    conn.execute("SAVEPOINT task_bulk_edit")
    try:
        for row in rows:
            per_task = dict(updates)
            existing_submitted = (row["submitted_at"] or "").strip()
            if "status" in per_task and per_task["status"] in ("Submitted", "Completed") and not existing_submitted:
                per_task["submitted_at"] = now
            else:
                per_task["submitted_at"] = existing_submitted
            per_task["updated_at"] = now
            columns = list(per_task)
            assignments = ", ".join(column + "=?" for column in columns)
            conn.execute(
                f"UPDATE tasks SET {assignments} WHERE id=?",
                [per_task[column] for column in columns] + [int(row["id"])],
            )
        conn.execute("RELEASE SAVEPOINT task_bulk_edit")
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT task_bulk_edit")
        conn.execute("RELEASE SAVEPOINT task_bulk_edit")
        conn.commit()
        raise
    return {"success": True, "updated": len(rows)}


@app.delete("/api/tasks/{task_id}")
def delete_task(
    task_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    role = str((user or {}).get("role", "")).strip().casefold()
    if role not in {"admin", "developer"}:
        raise HTTPException(status_code=403, detail="Only an Admin or Developer account can delete tasks.")
    cursor = conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found.")
    conn.commit()
    return {"success": True}


# --- Attendance & Working Calendar ---
@app.get("/api/attendance")
def get_attendance(work_date: Optional[str] = None, conn: sqlite3.Connection = Depends(get_db), user: dict = Depends(get_current_user)):
    selected_date = work_date or date.today().isoformat()
    try:
        selected_date = date.fromisoformat(str(selected_date)).isoformat()
    except ValueError:
        raise HTTPException(status_code=422, detail="work_date must use YYYY-MM-DD format")
    
    # Retrieve all active employees merged with attendance for selected_date
    rows = conn.execute(
        """SELECT e.id as employee_id, e.name, e.employee_code, e.department, e.designation,
                  COALESCE(a.attendance_status, 'Unmarked') as attendance_status,
                  COALESCE(a.check_in, '') as check_in,
                  COALESCE(a.check_out, '') as check_out,
                  COALESCE(a.break_minutes, 0) as break_minutes,
                  COALESCE(a.attendance_note, '') as attendance_note,
                  a.updated_at
           FROM employees e
           LEFT JOIN attendance a ON e.id = a.employee_id AND a.work_date=?
           WHERE e.active=1
           ORDER BY e.display_order ASC, e.name COLLATE NOCASE""",
        (selected_date,)
    ).fetchall()
    
    return {
        "date": selected_date,
        "roster": [dict(r) for r in rows],
        "remarks_options": list(desktop_app.ATTENDANCE_REMARK_OPTIONS),
    }

@app.post("/api/attendance/mark")
def mark_attendance(item: AttendanceMarkModel, conn: sqlite3.Connection = Depends(get_db), user: dict = Depends(get_current_user)):
    """Persist one employee's attendance while serializing against holiday declarations."""
    now = desktop_app.now_text()
    work_date = str(item.work_date or date.today().isoformat()).strip()
    try:
        work_date = date.fromisoformat(work_date).isoformat()
    except ValueError:
        raise HTTPException(status_code=422, detail="work_date must use YYYY-MM-DD format")

    try:
        # Acquire SQLite's write reservation before checking the holiday table.
        # A concurrent holiday declaration can therefore happen either before
        # this write (and be observed here) or after this attendance commit,
        # but never between the check and the attendance upsert.
        conn.execute("BEGIN IMMEDIATE")
        holiday = conn.execute(
            "SELECT holiday_name FROM holidays WHERE holiday_date=?",
            (work_date,),
        ).fetchone()
        if holiday:
            raise HTTPException(
                status_code=409,
                detail="This date is declared as a holiday. Remove the holiday declaration before recording attendance.",
            )

        employee = conn.execute(
            "SELECT id FROM employees WHERE id=?",
            (item.employee_id,),
        ).fetchone()
        if employee is None:
            raise HTTPException(status_code=404, detail="Employee not found")

        fields_set = getattr(item, "model_fields_set", None)
        if fields_set is None:
            fields_set = getattr(item, "__fields_set__", set())
        old = conn.execute(
            "SELECT * FROM attendance WHERE employee_id=? AND work_date=?",
            (item.employee_id, work_date),
        ).fetchone()

        status = str(item.status or item.attendance_status or "Present").strip()
        allowed_statuses = {
            "present": "Present",
            "absent": "Absent",
            "leave": "Leave",
            "unmarked": "Unmarked",
        }
        if status.casefold() in allowed_statuses:
            status = allowed_statuses[status.casefold()]
        elif not desktop_app.is_present_attendance_status(status):
            raise HTTPException(
                status_code=422,
                detail="Attendance status must be Present, Absent, Leave, Unmarked or a recognized worked-day detail status.",
            )
        note = (
            item.notes if "notes" in fields_set else
            item.attendance_note if "attendance_note" in fields_set else
            (old["attendance_note"] if old else "")
        ) or ""
        check_in = (
            str(item.check_in or "").strip() if "check_in" in fields_set
            else str(old["check_in"] or "").strip() if old else ""
        )
        check_out = (
            str(item.check_out or "").strip() if "check_out" in fields_set
            else str(old["check_out"] or "").strip() if old else ""
        )
        break_minutes = (
            max(0, int(item.break_minutes or 0)) if "break_minutes" in fields_set
            else int(old["break_minutes"] or 0) if old else 0
        )

        if check_in and not desktop_app.valid_hhmm(check_in):
            raise HTTPException(status_code=422, detail="Check-in must use 24-hour HH:MM format.")
        if check_out and not desktop_app.valid_hhmm(check_out):
            raise HTTPException(status_code=422, detail="Check-out must use 24-hour HH:MM format.")
        if status.casefold() in {"absent", "leave", "unmarked"}:
            check_in = check_out = ""
        elif (check_in or check_out) and not desktop_app.is_present_attendance_status(status):
            status = "Present"
        if check_out and not check_in:
            raise HTTPException(status_code=422, detail="Check-out requires a check-in")

        conn.execute(
            """INSERT INTO attendance(
                   employee_id, work_date, attendance_status, check_in, check_out,
                   break_minutes, attendance_note, updated_at
               ) VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(employee_id, work_date) DO UPDATE SET
                   attendance_status=excluded.attendance_status,
                   check_in=excluded.check_in,
                   check_out=excluded.check_out,
                   break_minutes=excluded.break_minutes,
                   attendance_note=excluded.attendance_note,
                   updated_at=excluded.updated_at""",
            (item.employee_id, work_date, status, check_in, check_out, break_minutes, str(note), now)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    saved = conn.execute(
        "SELECT * FROM attendance WHERE employee_id=? AND work_date=?",
        (item.employee_id, work_date),
    ).fetchone()
    return {"success": True, "attendance": dict(saved)}

@app.post("/api/attendance/bulk")
def bulk_attendance(
    work_date: str = Query(...),
    status: str = Query("Present"),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Legacy all-active-employees action with serialized holiday and roster checks."""
    try:
        work_date = date.fromisoformat(str(work_date or "").strip()).isoformat()
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="work_date must use YYYY-MM-DD format")

    allowed_statuses = {
        value.casefold(): value
        for value in (
            "Present", "Absent", "Leave", "Unmarked",
            *getattr(desktop_app, "ATTENDANCE_DETAIL_STATUSES", ()),
        )
    }
    selected_status = allowed_statuses.get(str(status or "").strip().casefold())
    if selected_status is None:
        raise HTTPException(
            status_code=422,
            detail="Attendance status must be Present, Absent, Leave, Unmarked or a recognized worked-day detail status.",
        )

    try:
        # Lock before both the holiday check and active-roster read so those
        # decisions remain consistent for the entire bulk update.
        conn.execute("BEGIN IMMEDIATE")
        holiday = conn.execute(
            "SELECT holiday_name FROM holidays WHERE holiday_date=?",
            (work_date,),
        ).fetchone()
        if holiday:
            raise HTTPException(
                status_code=409,
                detail="This date is declared as a holiday. Remove the holiday declaration before recording attendance.",
            )

        employees = conn.execute(
            "SELECT id FROM employees WHERE active=1"
        ).fetchall()
        now = desktop_app.now_text()
        for emp in employees:
            conn.execute(
                """INSERT INTO attendance(employee_id, work_date, attendance_status, updated_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT(employee_id, work_date) DO UPDATE SET
                       attendance_status=excluded.attendance_status,
                       check_in=CASE WHEN excluded.attendance_status IN ('Absent','Leave','Unmarked') THEN '' ELSE attendance.check_in END,
                       check_out=CASE WHEN excluded.attendance_status IN ('Absent','Leave','Unmarked') THEN '' ELSE attendance.check_out END,
                       updated_at=excluded.updated_at""",
                (emp["id"], work_date, selected_status, now)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"success": True, "count": len(employees)}

@app.get("/api/holidays")
def list_holidays(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    rows = conn.execute("SELECT holiday_date, holiday_name, created_at FROM holidays ORDER BY holiday_date ASC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/holidays")
def add_holiday(
    h: HolidayModel,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_employee_roles(user, {"admin", "developer"})
    try:
        holiday_date = date.fromisoformat(str(h.holiday_date)).isoformat()
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Holiday date must use YYYY-MM-DD.")
    holiday_name = str(h.holiday_name or "").strip()
    if not holiday_name:
        raise HTTPException(status_code=422, detail="Holiday name is required.")
    existing = conn.execute(
        "SELECT holiday_name FROM holidays WHERE holiday_date=?",
        (holiday_date,),
    ).fetchone()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Holiday already declared: {existing['holiday_name'] or 'Holiday'}",
        )
    now = desktop_app.now_text()
    conn.execute(
        "INSERT INTO holidays(holiday_date, holiday_name, created_at) VALUES(?,?,?)",
        (holiday_date, holiday_name, now),
    )
    _record_account_audit(conn, "Holiday declared", f"{holiday_date}: {holiday_name}")
    conn.commit()
    return {"success": True}


@app.delete("/api/holidays/{holiday_date}")
def delete_holiday(
    holiday_date: str,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_employee_roles(user, {"admin", "developer"})
    try:
        holiday_date = date.fromisoformat(str(holiday_date)).isoformat()
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Holiday date must use YYYY-MM-DD.")
    existing = conn.execute(
        "SELECT holiday_name FROM holidays WHERE holiday_date=?",
        (holiday_date,),
    ).fetchone()
    if existing is None:
        return {"success": True, "removed": False}
    conn.execute("DELETE FROM holidays WHERE holiday_date=?", (holiday_date,))
    _record_account_audit(
        conn,
        "Holiday removed",
        f"{holiday_date}: {existing['holiday_name'] or 'Holiday'}",
    )
    conn.commit()
    return {"success": True, "removed": True}


# --- Business Tracking (Products & Services) ---
_BUSINESS_PRODUCT_NUMBERS = (
    "opening_stock", "received_qty", "reserved_qty", "dispatched_qty",
    "free_qty", "returned_qty", "damaged_qty", "expired_qty",
    "quarantined_qty", "purchase_cost", "selling_price", "reorder_level",
)


def _validate_business_amounts(model, field_names):
    for field_name in field_names:
        value = getattr(model, field_name, 0) or 0
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"{field_name} must be a non-negative number.")
        if number < 0 or number != number or number in (float("inf"), float("-inf")):
            raise HTTPException(status_code=422, detail=f"{field_name} must be a finite non-negative number.")


@app.get("/api/business/products")
def list_products(
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    rows = conn.execute("SELECT * FROM bt_products ORDER BY name COLLATE NOCASE ASC").fetchall()
    result = []
    from business_tracking import available_stock
    for row in rows:
        item = dict(row)
        item["available_stock"] = available_stock(item)
        result.append(item)
    return result


@app.post("/api/business/products")
def create_product(
    p: ProductModel,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    name = str(p.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Product name is required.")
    _validate_business_amounts(p, _BUSINESS_PRODUCT_NUMBERS)
    now = desktop_app.now_text()
    try:
        cur = conn.execute(
            """INSERT INTO bt_products(
                name,sku,category,brand,package_type,base_unit,opening_stock,received_qty,
                reserved_qty,dispatched_qty,free_qty,returned_qty,damaged_qty,expired_qty,
                quarantined_qty,purchase_cost,selling_price,reorder_level,batch_number,
                expiry_date,storage_location,updated_by,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                name, str(p.sku or "").strip() or None, p.category or "", p.brand or "",
                p.package_type or "", p.base_unit or "PCS", p.opening_stock or 0,
                p.received_qty or 0, p.reserved_qty or 0, p.dispatched_qty or 0,
                p.free_qty or 0, p.returned_qty or 0, p.damaged_qty or 0,
                p.expired_qty or 0, p.quarantined_qty or 0, p.purchase_cost or 0,
                p.selling_price or 0, p.reorder_level or 0, p.batch_number or "",
                p.expiry_date or "", p.storage_location or "", user.get("username", ""), now,
            ),
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid}
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="A product with that SKU already exists.") from exc
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Create product failed: {exc}") from exc


@app.get("/api/business/services")
def list_services(
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    rows = conn.execute("SELECT * FROM bt_services ORDER BY name COLLATE NOCASE ASC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/business/services")
def create_service(
    s: ServiceModel,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    name = str(s.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Service name is required.")
    if int(s.session_duration or 0) < 0 or int(s.num_sessions or 0) < 0 or int(s.plan_validity or 0) < 0:
        raise HTTPException(status_code=422, detail="Service duration, sessions and validity cannot be negative.")
    _validate_business_amounts(s, ("standard_price",))
    now = desktop_app.now_text()
    cur = conn.execute(
        """INSERT INTO bt_services(
            name,category,description,training_mode,service_unit,session_duration,
            num_sessions,plan_validity,standard_price,active,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            name, s.category or "", s.description or "", s.training_mode or "Offline",
            s.service_unit or "Session", s.session_duration or 0, s.num_sessions or 0,
            s.plan_validity or 0, s.standard_price or 0, int(s.active if s.active is not None else 1), now,
        ),
    )
    conn.commit()
    return {"success": True, "id": cur.lastrowid}


# --- Reports & Print Center ---
_REPORT_OPTION_DEFAULTS = {
    "summary": True, "identity": True, "target": True, "contact": False,
    "work_status": True, "late_links": True, "missing_proof": True,
    "target_status": True, "tasks": True, "target_qty": True,
    "actual_qty": True, "completion_pct": True, "priority": True,
    "details": True, "due_time": True, "proof": True, "proof_notes": False,
    "custom_values": True, "next_action": True, "remarks": True,
    "expose_link": False, "pending": True, "attendance": False,
    "attendance_identity": True, "attendance_status": True,
    "attendance_times": True, "attendance_remarks": True,
    "attendance_summary": True, "details_identity": True,
    "details_contact": True, "details_joining": True, "details_status": True,
    "details_notes": True, "productivity_identity": True,
    "productivity_metrics": True, "productivity_explanation": True,
    "productivity_tracking": True, "productivity_tasks": True,
    "business_products": False, "business_services": False,
}

# These are the report checkboxes persisted by the desktop EXE as report_opt_*.
# Business catalog toggles remain per-report choices in both clients.
_REPORT_PERSISTED_OPTION_KEYS = frozenset(
    key for key in _REPORT_OPTION_DEFAULTS
    if key not in {"attendance", "business_products", "business_services"}
)


def _report_is_completed(status):
    helper = getattr(desktop_app, "is_explicitly_completed_task_status", None)
    if callable(helper):
        return bool(helper(status))
    return str(status or "").strip().lower() in {"completed", "done", "closed", "submitted"}


def _report_is_cancelled(status):
    helper = getattr(desktop_app, "is_cancelled_task_status", None)
    if callable(helper):
        return bool(helper(status))
    return str(status or "").strip().lower() in {"cancelled", "canceled"}


def _report_is_present(status, check_in=""):
    helper = getattr(desktop_app, "is_present_attendance_status", None)
    if callable(helper):
        return bool(helper(status))
    return str(status or "").strip().lower() in {"present", "late", "checked in", "on time"} or (
        str(status or "").strip().lower() == "unmarked" and bool(check_in)
    )


def _report_net_hours(check_in, check_out, break_minutes=0):
    if not check_in or not check_out:
        return ""
    try:
        start = datetime.strptime(str(check_in), "%H:%M")
        end = datetime.strptime(str(check_out), "%H:%M")
        minutes = int((end - start).total_seconds() // 60)
        if minutes < 0:
            minutes += 24 * 60
        minutes = max(0, minutes - int(break_minutes or 0))
        return f"{minutes / 60:.2f}"
    except (TypeError, ValueError, OverflowError):
        return ""


def _report_scope_clause(req, alias="e"):
    if req.employee_id is not None:
        return f" AND {alias}.id=?", [int(req.employee_id)]
    if req.exclude_employee_id is not None:
        return f" AND {alias}.id<>?", [int(req.exclude_employee_id)]
    return "", []


def _build_report_preview(req, conn):
    try:
        report_day = date.fromisoformat(req.date)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Report date must use YYYY-MM-DD.")
    if report_day > date.today():
        raise HTTPException(status_code=400, detail="Report date cannot be in the future.")

    report_type = (req.report_type or "Audit / EOD").strip()
    allowed_types = {"Audit / EOD", "Employee Attendance", "Employee Details", "Employee Productivity"}
    if report_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported report type.")

    opts = dict(_REPORT_OPTION_DEFAULTS)
    if req.options:
        opts.update({key: bool(value) for key, value in req.options.items() if key in opts})
    scope_sql, scope_params = _report_scope_clause(req)

    if report_type == "Employee Attendance":
        try:
            holiday = conn.execute(
                "SELECT holiday_name FROM holidays WHERE holiday_date=?",
                (req.date,),
            ).fetchone()
        except sqlite3.OperationalError:
            holiday = None
        holiday_declared = holiday is not None
        holiday_name = str(holiday["holiday_name"] or "").strip() if holiday_declared else ""

        rows = conn.execute(
            """SELECT e.name,e.employee_code,e.department,
                      COALESCE(a.attendance_status,'Unmarked') AS status,
                      COALESCE(a.check_in,'') AS check_in,
                      COALESCE(a.check_out,'') AS check_out,
                      COALESCE(a.break_minutes,0) AS break_minutes,
                      COALESCE(a.attendance_note,'') AS notes
               FROM employees e
               LEFT JOIN attendance a ON a.employee_id=e.id AND a.work_date=?
               WHERE e.active=1""" + scope_sql + " ORDER BY e.name",
            [req.date, *scope_params],
        ).fetchall()
        lines = ["RAW STRENGTH CALISTHENICS — EMPLOYEE ATTENDANCE", f"Date: {req.date}", ""]
        if holiday_name:
            lines.extend([f"Declared holiday: {holiday_name}", ""])

        def attendance_report_status(row):
            # Match the desktop EXE: a declared holiday overrides any stale
            # attendance mark that may exist from before the holiday was added.
            return "Holiday" if holiday_declared else str(row["status"] or "Unmarked")

        if opts["attendance_summary"]:
            present = sum(
                1 for row in rows
                if _report_is_present(attendance_report_status(row), row["check_in"])
            )
            absent = sum(1 for row in rows if attendance_report_status(row).casefold() == "absent")
            leave = sum(1 for row in rows if attendance_report_status(row).casefold() == "leave")
            lines.append(f"SUMMARY: Present {present} | Absent {absent} | Leave {leave} | Employees {len(rows)}")
            lines.append("")
        for row in rows:
            parts = [str(row["name"] or "")]
            if opts["attendance_identity"]:
                parts.extend([row["employee_code"] or "N/A", row["department"] or "General"])
            if opts["attendance_status"]:
                parts.append(attendance_report_status(row))
            if opts["attendance_times"]:
                net = _report_net_hours(row["check_in"], row["check_out"], row["break_minutes"])
                parts.extend([
                    f"In: {row['check_in'] or '—'}",
                    f"Out: {row['check_out'] or '—'}",
                    f"Break: {int(row['break_minutes'] or 0)} min",
                    f"Net hours: {net or '—'}",
                ])
            if opts["attendance_remarks"]:
                parts.append(f"Remarks: {row['notes'] or '—'}")
            lines.append(" | ".join(str(part) for part in parts))
        return {"preview_text": "\n".join(lines), "report_type": report_type, "record_count": len(rows)}

    if report_type == "Employee Details":
        rows = conn.execute(
            """SELECT e.* FROM employees e WHERE 1=1""" + scope_sql + " ORDER BY e.name",
            scope_params,
        ).fetchall()
        lines = [
            "RAW STRENGTH CALISTHENICS — EMPLOYEE DETAILS",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "",
        ]
        for row in rows:
            parts = [str(row["name"] or "")]
            if opts["details_identity"]:
                parts.extend([
                    f"Employee ID: {row['employee_code'] or 'N/A'}",
                    f"Department: {row['department'] or 'N/A'}",
                    f"Role: {row['designation'] or 'N/A'}",
                ])
            if opts["details_contact"]:
                parts.extend([f"Phone: {row['phone'] or 'N/A'}", f"Email: {row['email'] or 'N/A'}"])
            if opts["details_joining"]:
                parts.append(f"Joining date: {row['joining_date'] or 'N/A'}")
            if opts["details_status"]:
                parts.append("Status: Active" if row["active"] else "Status: Inactive")
            if opts["details_notes"]:
                parts.append(f"Notes: {row['notes'] or 'N/A'}")
            lines.append(" | ".join(parts))
        return {"preview_text": "\n".join(lines), "report_type": report_type, "record_count": len(rows)}

    if report_type == "Employee Productivity":
        rows = conn.execute(
            """SELECT e.* FROM employees e WHERE e.active=1""" + scope_sql + " ORDER BY e.name",
            scope_params,
        ).fetchall()
        weekdays = desktop_app.working_weekdays_from_connection(conn)
        lines = ["RAW STRENGTH CALISTHENICS — EMPLOYEE PRODUCTIVITY", f"Date: {req.date}", ""]
        for employee in rows:
            employee_id = int(employee["id"])
            start_day = None
            if employee["joining_date"]:
                try:
                    start_day = date.fromisoformat(employee["joining_date"])
                except (TypeError, ValueError):
                    start_day = None
            if start_day is None:
                first = conn.execute(
                    """SELECT MIN(work_day) AS first_day FROM (
                           SELECT task_date AS work_day FROM tasks WHERE employee_id=?
                           UNION ALL
                           SELECT work_date AS work_day FROM attendance WHERE employee_id=?
                       ) WHERE work_day IS NOT NULL AND work_day<>''""",
                    (employee_id, employee_id),
                ).fetchone()
                try:
                    start_day = date.fromisoformat(first["first_day"]) if first and first["first_day"] else date.today()
                except (TypeError, ValueError):
                    start_day = date.today()
            as_of = min(report_day, date.today())
            task_rows = conn.execute(
                "SELECT progress,status FROM tasks WHERE employee_id=? AND task_date BETWEEN ? AND ?",
                (employee_id, start_day.isoformat(), as_of.isoformat()),
            ).fetchall()
            def task_progress(task):
                known = getattr(desktop_app, "is_known_task_status", None)
                if callable(known) and not known(task["status"]):
                    return 0
                try:
                    return max(0, min(100, int(float(task["progress"] or 0))))
                except (TypeError, ValueError, OverflowError):
                    return 0
            task_score = (sum(task_progress(task) for task in task_rows) / len(task_rows)) if task_rows else None
            attendance_rows = conn.execute(
                """SELECT work_date,attendance_status,check_in FROM attendance
                   WHERE employee_id=? AND work_date BETWEEN ? AND ?""",
                (employee_id, start_day.isoformat(), as_of.isoformat()),
            ).fetchall()
            holiday_rows = conn.execute(
                "SELECT holiday_date FROM holidays WHERE holiday_date BETWEEN ? AND ?",
                (start_day.isoformat(), as_of.isoformat()),
            ).fetchall()
            holidays = {row["holiday_date"] for row in holiday_rows}
            scheduled = []
            current = start_day
            from datetime import timedelta
            while current <= as_of:
                if current.weekday() in weekdays and current.isoformat() not in holidays:
                    scheduled.append(current.isoformat())
                current += timedelta(days=1)
            leave_days = {
                row["work_date"] for row in attendance_rows
                if row["attendance_status"] == "Leave" and row["work_date"] in scheduled
            }
            eligible_days = max(0, len(scheduled) - len(leave_days))
            present_days = sum(
                1 for row in attendance_rows
                if row["work_date"] in scheduled and _report_is_present(row["attendance_status"], row["check_in"])
            )
            attendance_score = (present_days / eligible_days * 100) if eligible_days else None
            if task_score is not None and attendance_score is not None:
                score = round(task_score * 0.7 + attendance_score * 0.3)
            elif task_score is not None:
                score = round(task_score)
            elif attendance_score is not None:
                score = round(attendance_score)
            else:
                score = 0
            daily_tasks = conn.execute(
                """SELECT title,status,progress FROM tasks
                   WHERE employee_id=? AND task_date=? ORDER BY id""",
                (employee_id, req.date),
            ).fetchall()
            completed = sum(1 for task in task_rows if _report_is_completed(task["status"]))
            lines.append(str(employee["name"] or ""))
            if opts["productivity_identity"]:
                lines.append(f"Employee ID: {employee['employee_code'] or 'N/A'} | Department: {employee['department'] or 'N/A'}")
            if opts["productivity_metrics"]:
                lines.extend([
                    f"Overall score: {score}%",
                    f"Task progress component: {round(task_score)}%" if task_score is not None else "Task progress component: N/A",
                    f"Attendance component: {round(attendance_score)}%" if attendance_score is not None else "Attendance component: N/A",
                ])
            if opts["productivity_explanation"]:
                lines.append("Scoring: Task progress contributes 70% and attendance 30% when both are available; otherwise the available component is used. Attendance counts scheduled working days, excluding declared holidays and recorded leave.")
            if opts["productivity_tracking"]:
                lines.append(
                    f"Tracking start: {start_day.isoformat()} | Working days: {len(scheduled)} | "
                    f"Attendance-eligible days: {eligible_days} | Present days: {present_days} | "
                    f"Tasks counted: {len(task_rows)} | Completed/submitted tasks: {completed}"
                )
            if opts["productivity_tasks"]:
                if daily_tasks:
                    lines.extend(
                        f"• {task['title']}: {task['status'] or 'Not selected'} — {task['progress'] or 0}%"
                        for task in daily_tasks
                    )
                else:
                    lines.append("No tasks recorded for the selected date.")
            lines.append("")
        return {"preview_text": "\n".join(lines), "report_type": report_type, "record_count": len(rows)}

    employees = conn.execute(
        "SELECT e.* FROM employees e WHERE e.active=1" + scope_sql + " ORDER BY e.name",
        scope_params,
    ).fetchall()
    all_tasks = []
    employee_records = []
    for employee in employees:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE employee_id=? AND task_date=? ORDER BY id",
            (employee["id"], req.date),
        ).fetchall()
        attendance = conn.execute(
            "SELECT * FROM attendance WHERE employee_id=? AND work_date=?",
            (employee["id"], req.date),
        ).fetchone()
        employee_records.append((employee, tasks, attendance))
        all_tasks.extend(tasks)

    completed_count = sum(1 for task in all_tasks if _report_is_completed(task["status"]))
    pending_count = sum(1 for task in all_tasks if not _report_is_completed(task["status"]) and not _report_is_cancelled(task["status"]))
    missing_proof_count = sum(
        1 for _employee, tasks, _attendance in employee_records
        if any(_report_is_completed(task["status"]) and not str(task["proof_url"] or "").strip() for task in tasks)
    )
    lines = [
        "RAW STRENGTH CALISTHENICS — EMPLOYEE AUDIT / EOD",
        f"Report date: {req.date}",
        f"Scope: {'Individual employee' if req.employee_id else ('Consolidated, excluding employee ' + str(req.exclude_employee_id) if req.exclude_employee_id else 'All employees')}",
        "",
    ]
    if opts["summary"]:
        lines.extend([
            "DAILY SUMMARY",
            f"Employees: {len(employee_records)}",
            f"Tasks recorded: {len(all_tasks)}",
            f"Completed / submitted tasks: {completed_count}",
            f"Pending / other tasks: {pending_count}",
            f"Employees flagged for missing proof: {missing_proof_count}",
            "",
        ])

    expose_global = False
    try:
        setting = conn.execute("SELECT value FROM settings WHERE key='global_expose_link'").fetchone()
        expose_global = bool(setting and str(setting["value"]) == "1")
    except sqlite3.OperationalError:
        pass

    for employee, tasks, attendance in employee_records:
        name = str(employee["name"] or "")
        lines.append(f"EMPLOYEE: {name}")
        if opts["identity"]:
            lines.append(
                f"Employee ID: {employee['employee_code'] or 'N/A'} | "
                f"Department: {employee['department'] or 'N/A'} | Role: {employee['designation'] or 'N/A'}"
            )
        if opts["contact"]:
            lines.append(f"Phone: {employee['phone'] or 'N/A'} | Email: {employee['email'] or 'N/A'}")
        if opts["target"] or opts["target_status"]:
            try:
                target = conn.execute(
                    "SELECT target,target_status FROM employee_targets WHERE employee_id=? AND target_date=?",
                    (employee["id"], req.date),
                ).fetchone()
            except sqlite3.OperationalError:
                target = None
            if opts["target"]:
                lines.append(f"Target: {(target['target'] if target else '') or 'N/A'}")
            if opts["target_status"]:
                lines.append(f"Target status: {(target['target_status'] if target else '') or 'N/A'}")
        if opts["work_status"]:
            statuses = [str(task["status"] or "") for task in tasks]
            work_status = (
                "Submitted" if statuses and all(_report_is_completed(status) for status in statuses)
                else "In progress / Partial" if statuses else "No tasks recorded"
            )
            if req.date == "2026-10-09":
                notes = str(employee["notes"] or "").lower()
                if "work: submitted" in notes or "work: submitted in time" in notes:
                    work_status = "Submitted (source audit)"
            lines.append(f"WORK / EOD STATUS: {work_status}")
        if opts["late_links"]:
            notes = str(employee["notes"] or "").lower()
            late = "No (source audit)" if req.date == "2026-10-09" and "late: no" in notes else "Review required"
            links = "Open (source audit; not rechecked)" if req.date == "2026-10-09" and ("links: open" in notes or "links open: yes" in notes) else "Not independently checked"
            lines.append(f"LATE: {late} | LINKS: {links}")
        if opts["missing_proof"]:
            missing = any(_report_is_completed(task["status"]) and not str(task["proof_url"] or "").strip() for task in tasks)
            lines.append(f"MISSING PROOF: {'Yes' if missing else 'No'}")
        if opts["attendance"] and attendance:
            lines.append(
                f"Attendance: {attendance['attendance_status'] or 'Unmarked'} | "
                f"In: {attendance['check_in'] or '—'} | Out: {attendance['check_out'] or '—'}"
            )
        if opts["tasks"]:
            lines.append("TASKS / WORK ITEMS")
            if not tasks:
                lines.append("No tasks recorded for this date.")
            for index, task in enumerate(tasks, 1):
                lines.append(f"{index}. {task['title']} — Status: {task['status'] or 'Not selected'}")
                if opts["target_qty"] and task["target_qty"]:
                    lines.append(f"Target Qty: {task['target_qty']}")
                if opts["actual_qty"] and task["actual_qty"]:
                    lines.append(f"Actual Qty: {task['actual_qty']}")
                if opts["completion_pct"]:
                    lines.append(f"Completion %: {task['progress'] or 0}%")
                if opts["priority"]:
                    lines.append(f"Priority: {task['priority'] or 'Normal'}")
                if opts["details"] and task["details"]:
                    lines.append(f"Details: {task['details']}")
                if opts["due_time"] and task["due_time"]:
                    lines.append(f"Due time: {task['due_time']}")
                if opts["proof"] and task["proof_url"]:
                    expose = opts["expose_link"] or expose_global or bool(task["expose_link"])
                    lines.append(f"Proof link: {task['proof_url'] if expose else 'Tap here to view content'}")
                if opts["proof_notes"] and task["proof_note"]:
                    lines.append(f"Proof notes: {task['proof_note']}")
                if opts["custom_values"] and task["custom_values"]:
                    lines.append(f"Custom values: {task['custom_values']}")
                if opts["next_action"] and task["next_action"]:
                    lines.append(f"Next action: {task['next_action']}")
                if opts["remarks"] and task["manager_note"]:
                    lines.append(f"Manager remarks: {task['manager_note']}")
        if opts["pending"]:
            pending = [
                str(task["title"] or "") for task in tasks
                if not _report_is_completed(task["status"]) and not _report_is_cancelled(task["status"])
            ]
            lines.append("PENDING: " + ("; ".join(pending) if pending else "No"))
        lines.append("")

    if opts["business_products"]:
        try:
            products = conn.execute("SELECT * FROM bt_products ORDER BY name").fetchall()
        except sqlite3.OperationalError:
            products = []
        lines.extend(["PRODUCT CATALOG & STOCK", "Product | SKU | Category | Brand | Unit | Available stock | Reorder level | Selling price"])
        for product in products:
            from business_tracking import available_stock
            available = available_stock(product)
            lines.append(
                f"{product['name']} | {product['sku'] or '—'} | {product['category'] or '—'} | "
                f"{product['brand'] or '—'} | {product['base_unit'] or '—'} | {available:g} | "
                f"{float(product['reorder_level'] or 0):g} | {float(product['selling_price'] or 0):.2f}"
            )
    if opts["business_services"]:
        try:
            services = conn.execute("SELECT * FROM bt_services ORDER BY name").fetchall()
        except sqlite3.OperationalError:
            services = []
        lines.extend(["SERVICE CATALOG", "Service | Category | Description | Training mode | Unit | Duration | Sessions | Validity | Price | Status"])
        for service in services:
            lines.append(
                f"{service['name']} | {service['category'] or '—'} | {service['description'] or '—'} | "
                f"{service['training_mode'] or '—'} | {service['service_unit'] or '—'} | "
                f"{service['session_duration'] or 0} | {service['num_sessions'] or 0} | "
                f"{service['plan_validity'] or 0} | {float(service['standard_price'] or 0):.2f} | "
                f"{'Active' if service['active'] else 'Inactive'}"
            )

    return {"preview_text": "\n".join(lines), "report_type": report_type, "record_count": len(employee_records)}


@app.get("/api/reports/options")
def get_report_option_preferences(
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Return the shared Print Center checkbox preferences used by the desktop EXE."""
    options = {
        key: bool(_REPORT_OPTION_DEFAULTS[key])
        for key in _REPORT_PERSISTED_OPTION_KEYS
    }
    rows = conn.execute(
        "SELECT key, value FROM settings WHERE key LIKE 'report_opt_%'"
    ).fetchall()
    for row in rows:
        key = str(row["key"])[len("report_opt_"):]
        value = str(row["value"])
        if key in _REPORT_PERSISTED_OPTION_KEYS and value in {"0", "1"}:
            options[key] = value == "1"
    return {"options": options}


@app.put("/api/reports/options")
def save_report_option_preferences(
    data: ReportOptionPreferencesModel,
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Persist only known desktop report checkboxes; any authenticated role may use Print Center."""
    unknown = sorted(set(data.options) - _REPORT_PERSISTED_OPTION_KEYS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail="Unsupported report option(s): " + ", ".join(unknown),
        )
    for key, enabled in data.options.items():
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (f"report_opt_{key}", "1" if enabled else "0"),
        )
    conn.commit()
    return {"success": True, "options": data.options}


@app.post("/api/reports/preview")
def generate_report_preview(
    req: ReportOptionsModel,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user),
):
    return _build_report_preview(req, conn)


@app.post("/api/reports/export")
def export_report(
    req: ReportOptionsModel,
    conn: sqlite3.Connection = Depends(get_db),
    user=Depends(get_current_user),
):
    output_format = str(req.output_format or "pdf").lower().lstrip(".")
    if output_format not in {"pdf", "docx", "csv"}:
        raise HTTPException(status_code=400, detail="Output format must be PDF, DOCX, or CSV.")
    report = _build_report_preview(req, conn)
    report_text = report["preview_text"]
    slug = re.sub(r"[^a-z0-9]+", "-", str(req.report_type or "report").lower()).strip("-") or "report"
    filename = f"raw-strength-{slug}-{req.date}.{output_format}"

    if output_format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["Section", "Field", "Value"])
        section = str(req.report_type or "Report")
        for raw_line in report_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.isupper() or line.startswith("EMPLOYEE:") or line.startswith("DAILY SUMMARY"):
                section = line
                writer.writerow([section, "", ""])
            elif ":" in line:
                field, value = line.split(":", 1)
                writer.writerow([section, field.strip(), value.strip()])
            else:
                writer.writerow([section, "Detail", line])
        content = ("\ufeff" + stream.getvalue()).encode("utf-8")
        media_type = "text/csv; charset=utf-8"
    elif output_format == "docx":
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.opc.constants import RELATIONSHIP_TYPE as RT

        document = Document()
        section = document.sections[0]
        section.top_margin = Inches(0.65)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)
        document.styles["Normal"].font.name = "Aptos"
        document.styles["Normal"].font.size = Pt(9)
        title = document.add_paragraph()
        title.alignment = 1
        title_run = title.add_run("RAW STRENGTH CALISTHENICS")
        title_run.bold = True
        title_run.font.size = Pt(16)
        subtitle = document.add_paragraph()
        subtitle.alignment = 1
        subtitle.add_run(f"{req.report_type or 'Report'} — {req.date}").bold = True

        def add_line_with_links(line):
            paragraph = document.add_paragraph()
            for part in re.split(r"(https?://[^\s]+)", line):
                if part.startswith(("http://", "https://")):
                    relation = paragraph.part.relate_to(part, RT.HYPERLINK, is_external=True)
                    hyperlink = OxmlElement("w:hyperlink")
                    hyperlink.set(qn("r:id"), relation)
                    run = OxmlElement("w:r")
                    properties = OxmlElement("w:rPr")
                    color = OxmlElement("w:color")
                    color.set(qn("w:val"), "0563C1")
                    underline = OxmlElement("w:u")
                    underline.set(qn("w:val"), "single")
                    properties.append(color)
                    properties.append(underline)
                    run.append(properties)
                    text_node = OxmlElement("w:t")
                    text_node.text = part
                    run.append(text_node)
                    hyperlink.append(run)
                    paragraph._p.append(hyperlink)
                elif part:
                    paragraph.add_run(part)

        for line in report_text.splitlines():
            if not line.strip():
                document.add_paragraph()
            elif line.isupper() or line.startswith("EMPLOYEE:") or line.startswith("DAILY SUMMARY"):
                document.add_heading(line, level=2)
            else:
                add_line_with_links(line)
        output = io.BytesIO()
        document.save(output)
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image as RLImage
        from xml.sax.saxutils import escape

        output = io.BytesIO()
        regular_name, bold_name = "Helvetica", "Helvetica-Bold"
        regular_font = ROOT_DIR / "assets" / "DejaVuSans.ttf"
        bold_font = ROOT_DIR / "assets" / "DejaVuSans-Bold.ttf"
        try:
            if regular_font.is_file() and bold_font.is_file():
                if "RawStrengthSans" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("RawStrengthSans", str(regular_font)))
                    pdfmetrics.registerFont(TTFont("RawStrengthSans-Bold", str(bold_font)))
                regular_name, bold_name = "RawStrengthSans", "RawStrengthSans-Bold"
        except Exception:
            regular_name, bold_name = "Helvetica", "Helvetica-Bold"

        navy = colors.HexColor("#102B42")
        cyan = colors.HexColor("#00AEEA")
        muted = colors.HexColor("#526579")
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="RSWebTitle", fontName=bold_name, fontSize=13, leading=17,
            alignment=TA_CENTER, textColor=cyan, spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="RSWebSubtitle", fontName=regular_name, fontSize=8.5, leading=12,
            alignment=TA_CENTER, textColor=muted, spaceAfter=12,
        ))
        styles.add(ParagraphStyle(
            name="RSWebName", fontName=regular_name, fontSize=8.5, leading=12,
            textColor=navy, spaceBefore=8, spaceAfter=5, keepWithNext=True,
        ))
        styles.add(ParagraphStyle(
            name="RSWebSection", fontName=bold_name, fontSize=9.2, leading=12,
            textColor=navy, spaceBefore=5, spaceAfter=3, keepWithNext=True,
        ))
        styles.add(ParagraphStyle(
            name="RSWebBody", fontName=regular_name, fontSize=8.5, leading=12,
            textColor=colors.HexColor("#1F2937"), spaceAfter=3, wordWrap="LTR",
        ))
        styles.add(ParagraphStyle(
            name="RSWebBullet", parent=styles["RSWebBody"], leftIndent=13,
            firstLineIndent=-8, bulletIndent=1, spaceAfter=3,
        ))

        story = []
        logo_path = ROOT_DIR / "assets" / "raw_strength_brand.png"
        if logo_path.is_file():
            try:
                logo = RLImage(str(logo_path), width=38 * mm, height=38 * mm)
                logo.hAlign = "CENTER"
                story.extend([logo, Spacer(1, 3.5 * mm)])
            except Exception:
                pass

        report_titles = {
            "Audit / EOD": "EMPLOYEE AUDIT / END-OF-DAY REPORT",
            "Employee Attendance": "EMPLOYEE ATTENDANCE REPORT",
            "Employee Details": "EMPLOYEE DETAILS REGISTER",
            "Employee Productivity": "EMPLOYEE PRODUCTIVITY REPORT",
        }
        if req.employee_id:
            scope_row = conn.execute("SELECT name FROM employees WHERE id=?", (req.employee_id,)).fetchone()
            scope_label = str(scope_row["name"] or "Selected employee") if scope_row else "Selected employee"
        elif req.exclude_employee_id:
            excluded_row = conn.execute("SELECT name FROM employees WHERE id=?", (req.exclude_employee_id,)).fetchone()
            excluded_name = str(excluded_row["name"] or req.exclude_employee_id) if excluded_row else str(req.exclude_employee_id)
            scope_label = "All employees except " + excluded_name
        else:
            scope_label = "All employees"

        story.extend([
            Paragraph(escape(report_titles.get(req.report_type or "", "EMPLOYEE AUDIT / END-OF-DAY REPORT")), styles["RSWebTitle"]),
            Paragraph(
                f"Report date: {escape(str(req.date))} &nbsp;&nbsp; | &nbsp;&nbsp; Scope: {escape(scope_label)}",
                styles["RSWebSubtitle"],
            ),
            HRFlowable(width="100%", thickness=1.2, color=cyan, spaceAfter=9),
        ])
        if req.report_type == "Employee Details":
            story.append(Paragraph(
                f"<b>TOTAL EMPLOYEES:</b> {int(report.get('record_count') or 0)}",
                styles["RSWebSection"],
            ))

        url_pattern = re.compile(r"https?://[^\s]+", re.IGNORECASE)

        def linked_markup(value):
            clean = str(value).replace("■ ", "EMPLOYEE: ").replace("—", "-")
            parts = []
            cursor = 0
            for match in url_pattern.finditer(clean):
                parts.append(escape(clean[cursor:match.start()]))
                raw_url = match.group(0)
                url = raw_url.rstrip(".,;:!?)]}")
                suffix = raw_url[len(url):]
                safe_url = escape(url, {"'": "&#39;", '"': "&quot;"})
                parts.append(
                    '<link href="' + safe_url + '" color="#0563C1">'
                    + escape(url) + "</link>"
                )
                parts.append(escape(suffix))
                cursor = match.end()
            parts.append(escape(clean[cursor:]))
            return "".join(parts)

        for raw_line in report_text.splitlines():
            line = raw_line.strip()
            if not line:
                story.append(Spacer(1, 2 * mm))
                continue
            if line.startswith("RAW STRENGTH CALISTHENICS"):
                continue
            if line.startswith(("Report date:", "Scope:", "Date:", "Generated:")):
                continue
            if line.startswith("EMPLOYEE:"):
                name = line.partition(":")[2].strip()
                story.append(Paragraph("<b>Name :</b> " + linked_markup(name), styles["RSWebName"]))
            elif line.startswith("SUMMARY:"):
                story.append(Paragraph(linked_markup(line), styles["RSWebSection"]))
            elif req.report_type in {"Employee Attendance", "Employee Details"} and "|" in line:
                parts = [part.strip() for part in line.split("|")]
                story.append(Paragraph("<b>Name :</b> " + linked_markup(parts[0]), styles["RSWebName"]))
                for part in parts[1:]:
                    if part:
                        story.append(Paragraph("&#8226;&nbsp; " + linked_markup(part), styles["RSWebBullet"]))
            elif req.report_type in {"Employee Attendance", "Employee Details"} and not line.startswith(("No records",)):
                story.append(Paragraph("<b>Name :</b> " + linked_markup(line), styles["RSWebName"]))
            elif req.report_type == "Employee Productivity" and ":" not in line and "|" not in line and line != "No tasks recorded for the selected date." and not line.startswith(("•", "▪", "■")):
                story.append(Paragraph("<b>Name :</b> " + linked_markup(line), styles["RSWebName"]))
            elif line.isupper() or line.startswith("DAILY SUMMARY") or line.startswith("TASKS / WORK ITEMS"):
                story.append(Paragraph(linked_markup(line), styles["RSWebSection"]))
            else:
                story.append(Paragraph("&#8226;&nbsp; " + linked_markup(line.lstrip("•▪■ ")), styles["RSWebBullet"]))

        def draw_page(canvas, doc_obj):
            canvas.saveState()
            page_width, _page_height = A4
            canvas.setStrokeColor(cyan)
            canvas.setLineWidth(.6)
            canvas.line(15 * mm, 13 * mm, page_width - 15 * mm, 13 * mm)
            canvas.setFont(regular_name, 7)
            canvas.setFillColor(muted)
            canvas.drawString(15 * mm, 7.5 * mm, "Raw Strength Calisthenics | Confidential internal report")
            canvas.drawRightString(page_width - 15 * mm, 7.5 * mm, f"Page {doc_obj.page}")
            canvas.restoreState()

        pdf = SimpleDocTemplate(
            output, pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm,
            topMargin=16 * mm, bottomMargin=18 * mm,
            title=str(req.report_type or "Report"),
            author="Raw Strength Calisthenics",
            subject=f"{req.report_type or 'Report'} - {req.date}",
        )
        pdf.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
        content = output.getvalue()
        media_type = "application/pdf"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


# --- Live Chat ---
@app.get("/api/chat/messages")
def get_chat_messages(channel: str = "general", conn: sqlite3.Connection = Depends(get_db), user: Dict[str, Any] = Depends(get_current_user)):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS local_chat_messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT DEFAULT 'general',
            sender TEXT NOT NULL,
            role TEXT DEFAULT 'Staff',
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    rows = conn.execute(
        "SELECT * FROM local_chat_messages WHERE channel=? ORDER BY id ASC LIMIT 100", (channel,)
    ).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/chat/messages")
def send_chat_message(
    msg: ChatMessageModel,
    user: Dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db)
):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS local_chat_messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT DEFAULT 'general',
            sender TEXT NOT NULL,
            role TEXT DEFAULT 'Staff',
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    now = desktop_app.now_text()
    sender = msg.sender_name or user.get("display_name") or user.get("username", "User")
    role = user.get("role", "Staff")
    cursor = conn.execute(
        "INSERT INTO local_chat_messages(channel, sender, role, content, created_at) VALUES(?,?,?,?,?)",
        (msg.channel, sender, role, msg.content, now)
    )
    conn.commit()
    return {"id": cursor.lastrowid, "sender": sender, "role": role, "content": msg.content, "created_at": now}


@app.post("/api/settings/expose-all-links")
def enable_global_expose_links(
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Match the desktop action: expose every task proof URL and default report URLs."""
    task_count = int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] or 0)
    timestamp = desktop_app.now_text()
    conn.execute("UPDATE tasks SET expose_link=1, updated_at=?", (timestamp,))
    for key in ("global_expose_link", "report_opt_expose_link"):
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, "1"),
        )
    _record_account_audit(conn, "Global expose links enabled", f"Updated {task_count} tasks")
    # Keep this on the normal connection commit path so encrypted snapshot sync
    # receives the same dirty notification as other web writes.
    conn.commit()
    return {"success": True, "enabled": True, "updated": task_count}


# --- Settings ---
@app.get("/api/settings")
def get_settings(
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    _require_account_admin(user)
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings_dict = {r["key"]: r["value"] for r in rows}
    return {
        "settings": settings_dict,
        "app_version": APP_VERSION,
        "app_name": desktop_app.APP_NAME,
    }

@app.post("/api/settings")
def update_settings(
    data: Dict[str, str],
    conn: sqlite3.Connection = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user),
):
    _require_account_admin(user)
    for k, v in data.items():
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (k, str(v))
        )
    conn.commit()
    return {"success": True}


# --- System Updates & Releases ---
@app.get("/api/system/check-updates")
def check_updates():
    """Queries GitHub Releases API for the latest published application release."""
    import urllib.request
    try:
        url = f"https://api.github.com/repos/{desktop_app.GITHUB_REPOSITORY}/releases?per_page=15"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "RawStrengthEmployeeAuditManager",
                "Accept": "application/vnd.github+json",
            }
        )
        ssl_ctx = desktop_app.get_ssl_context() if hasattr(desktop_app, "get_ssl_context") else None
        try:
            if ssl_ctx:
                with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as resp:
                    releases = json.loads(resp.read().decode("utf-8"))
            else:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    releases = json.loads(resp.read().decode("utf-8"))
        except TypeError:
            with urllib.request.urlopen(req, timeout=12) as resp:
                releases = json.loads(resp.read().decode("utf-8"))

        if not isinstance(releases, list) or not releases:
            return {
                "current_version": APP_VERSION,
                "latest_version": APP_VERSION,
                "has_update": False,
                "message": "No releases currently found on GitHub.",
                "github_releases_url": f"https://github.com/{desktop_app.GITHUB_REPOSITORY}/releases/latest",
                "repository": desktop_app.GITHUB_REPOSITORY
            }

        latest_rel = None
        for r in releases:
            if not r.get("draft") and not r.get("prerelease") and r.get("published_at"):
                latest_rel = r
                break
        if not latest_rel:
            latest_rel = releases[0]

        tag = latest_rel.get("tag_name", "").lstrip("vV")
        installer_asset = next(
            (a for a in latest_rel.get("assets", []) if a.get("name") == "RawStrengthEmployeeAuditManager-Setup.exe"),
            None
        )

        has_update = desktop_app.release_version_tuple(tag) > desktop_app.release_version_tuple(APP_VERSION)

        return {
            "current_version": APP_VERSION,
            "latest_version": tag,
            "has_update": has_update,
            "published_at": latest_rel.get("published_at"),
            "release_name": latest_rel.get("name"),
            "release_notes": latest_rel.get("body", ""),
            "installer_url": installer_asset.get("browser_download_url") if installer_asset else f"https://github.com/{desktop_app.GITHUB_REPOSITORY}/releases/latest",
            "installer_name": "RawStrengthEmployeeAuditManager-Setup.exe",
            "installer_size": installer_asset.get("size") if installer_asset else 0,
            "github_releases_url": f"https://github.com/{desktop_app.GITHUB_REPOSITORY}/releases/latest",
            "repository": desktop_app.GITHUB_REPOSITORY,
        }
    except Exception as exc:
        # A failed GitHub request is not evidence that the installed version is
        # current. Return an explicit service error so clients cannot suppress an
        # available update by treating a network/API failure as has_update=False.
        return JSONResponse(
            status_code=503,
            content={
                "current_version": APP_VERSION,
                "latest_version": None,
                "has_update": None,
                "error": f"Unable to check GitHub releases: {exc}",
                "github_releases_url": f"https://github.com/{desktop_app.GITHUB_REPOSITORY}/releases/latest",
                "repository": desktop_app.GITHUB_REPOSITORY,
            },
        )


# Register operational routes after the API app and dependencies are fully defined.
import web_ops_routes  # noqa: E402,F401
import web_parity_routes  # noqa: E402,F401
import web_employee_routes  # noqa: E402,F401
import web_standalone_routes  # noqa: E402,F401

# --- Serve Built React Frontend (SPA Fallback) ---
DIST_DIR = ROOT_DIR / "frontend" / "dist"

@app.head("/")
def render_root_health_probe():
    """Return 200 for Render's default HEAD / probe; the configured API check remains /api/health."""
    return Response(status_code=200, headers={"Cache-Control": "no-store"})

if (ROOT_DIR / "assets").is_dir():
    app.mount("/brand-assets", StaticFiles(directory=str(ROOT_DIR / "assets")), name="brand-assets")

@app.get("/brand-logo.png")
def serve_brand_logo():
    logo_path = ROOT_DIR / "assets" / "raw_strength_brand_hud.png"
    if not logo_path.is_file():
        raise HTTPException(status_code=404, detail="Brand logo asset is unavailable")
    return FileResponse(logo_path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/")
    def serve_react_root():
        return FileResponse(DIST_DIR / "index.html", headers={"Cache-Control": "no-store, max-age=0, must-revalidate"})

    @app.get("/{full_path:path}")
    def serve_react_spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
else:
    @app.get("/")
    def index_placeholder():
        return {
            "message": "Raw Strength Calisthenics REST API is running! Frontend is building or accessible via Vite dev server at http://localhost:5173",
            "docs": "/docs",
            "version": APP_VERSION
        }

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Raw Strength Calisthenics REST API Server on http://localhost:8000 ...")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
