"""FastAPI REST API server for Raw Strength Calisthenics Employee Audit & Operations OS.
Exposes complete REST endpoints while preserving 100% of underlying SQLite business logic.
"""
import os
import sys
import json
import sqlite3
import secrets
import csv
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

# Render uses a persistent web working copy; encrypted synchronization is
# managed by web_sync.py, not by the desktop application's local sync worker.
if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
    _web_data_dir = Path(os.environ.get("AUDIT_DATA_DIR") or ("/var/data" if Path("/var/data").is_dir() else (ROOT_DIR / "web-data"))).expanduser().resolve()
    _web_data_dir.mkdir(parents=True, exist_ok=True)
    desktop_app.APP_DIR = _web_data_dir
    desktop_app.DB_PATH = _web_data_dir / "audit_manager.db"
    _legacy_web_db = _web_data_dir / "web_employee_audit.db"
    if not desktop_app.DB_PATH.exists() and _legacy_web_db.is_file():
        _src = sqlite3.connect(str(_legacy_web_db), timeout=30)
        _dst = sqlite3.connect(str(desktop_app.DB_PATH), timeout=30)
        try:
            _src.backup(_dst)
        finally:
            _dst.close()
            _src.close()
    desktop_app.BACKUP_DIR = _web_data_dir / "backups"
    desktop_app.EXPORT_DIR = _web_data_dir / "exports"
    desktop_app.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    desktop_app.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    class _WebOnlyDesktopSyncDisabled:
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
    desktop_app.GitHubDatabaseSync = _WebOnlyDesktopSyncDisabled

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
    global _DB_INITIALIZED, WEB_SYNC_MANAGER
    if not _DB_INITIALIZED:
        try:
            db = desktop_app.Database()
            try:
                import business_tracking
                business_tracking.setup_business_tables(db.conn)
            except Exception:
                pass
            if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
                from web_db_migrations import ensure_case_sensitive_auth_users
                if ensure_case_sensitive_auth_users(desktop_app.DB_PATH):
                    print("[Web DB] Migrated auth_users to exact case-sensitive usernames; all credentials preserved")
            if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
                db.conn.execute("""
                    CREATE TABLE IF NOT EXISTS web_auth_sessions (
                        token_hash TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES auth_users(id) ON DELETE CASCADE
                    )
                """)
                db.conn.execute("CREATE INDEX IF NOT EXISTS idx_web_auth_sessions_expiry ON web_auth_sessions(expires_at)")
                db.conn.commit()
            if hasattr(db, "close_github_sync"):
                db.close_github_sync(timeout=0)
            if hasattr(db, "conn") and db.conn:
                db.conn.close()
        except Exception as exc:
            print(f"[Web DB] Initialization/migration failed: {exc}")
            raise
        _DB_INITIALIZED = True
        if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
            try:
                from web_sync import WebDatabaseSync
                WEB_SYNC_MANAGER = WebDatabaseSync(desktop_app.DB_PATH)
                WEB_SYNC_MANAGER.bootstrap()
                WEB_SYNC_MANAGER.start_polling()
            except Exception as exc:
                print(f"[Web Sync] Initialization skipped: {exc}")

def get_db():
    """Create a thread-safe connection and mark committed web changes for sync."""
    ensure_database()
    db_path = desktop_app.DB_PATH
    factory = sqlite3.Connection
    if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
        try:
            from database_sync import SyncableSQLiteConnection
            factory = SyncableSQLiteConnection
        except Exception:
            factory = sqlite3.Connection
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30, factory=factory)
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
    if token and os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
        token_hash = __import__("hashlib").sha256(token.encode("utf-8")).hexdigest()
        session = conn.execute(
            """SELECT u.id, u.username, u.display_name, u.role
               FROM web_auth_sessions s JOIN auth_users u ON u.id=s.user_id
               WHERE s.token_hash=? AND s.expires_at>? AND u.active=1""",
            (token_hash, datetime.now().isoformat(timespec="seconds")),
        ).fetchone()
        if session:
            return dict(session)
    elif token and token in ACTIVE_SESSIONS:
        return ACTIVE_SESSIONS[token]
    if os.environ.get("WEB_REQUIRE_LOGIN", "0").strip().lower() in ("1", "true", "yes"):
        raise HTTPException(status_code=401, detail="Login required")
    # Non-web local development may use the first account; production web boot requires a token.
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


class StockTransactionModel(BaseModel):
    txn_type: str
    quantity: float
    unit: Optional[str] = ""
    reference: Optional[str] = ""
    notes: Optional[str] = ""


class ServiceModel(BaseModel):
    name: str
    category: Optional[str] = "Training"
    description: Optional[str] = ""
    training_mode: Optional[str] = "In-Person"
    service_unit: Optional[str] = "Session"
    session_duration: Optional[int] = 60
    num_sessions: Optional[int] = 1
    plan_validity: Optional[int] = 30
    standard_price: Optional[float] = 0.0
    active: Optional[int] = 1

class ChatMessageModel(BaseModel):
    channel: Optional[str] = "general"
    content: str
    sender_name: Optional[str] = ""

class ReportOptionsModel(BaseModel):
    date: str
    employee_id: Optional[int] = None
    report_type: Optional[str] = "Audit / EOD"
    options: Optional[Dict[str, bool]] = None


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
    if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
        import hashlib
        from datetime import timedelta
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        created_at = datetime.now()
        conn.execute(
            "INSERT INTO web_auth_sessions(token_hash, user_id, created_at, expires_at) VALUES(?,?,?,?)",
            (token_hash, row["id"], created_at.isoformat(timespec="seconds"),
             (created_at + timedelta(days=30)).isoformat(timespec="seconds")),
        )
        conn.commit()
    else:
        ACTIVE_SESSIONS[token] = user_info
    return {"token": token, "user": user_info}

@app.get("/api/auth/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    return {"user": user}

@app.post("/api/auth/setup")
def initial_setup(req: SetupRequest, conn: sqlite3.Connection = Depends(get_db)):
    count = conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
    if count > 0:
        raise HTTPException(status_code=400, detail="Setup has already been completed.")
    if os.environ.get("WEB_STANDALONE", "0").strip().lower() in ("1", "true", "yes"):
        manager = WEB_SYNC_MANAGER
        if manager is None or not getattr(manager, "configured", False) or not bool(getattr(manager, "last_pull", {}).get("ok")):
            raise HTTPException(
                status_code=503,
                detail="Admin setup is disabled until the existing encrypted customer database is verified. Check database sync configuration.",
            )
    
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


# --- Dashboard Analytics ---
@app.get("/api/dashboard")
def get_dashboard(conn: sqlite3.Connection = Depends(get_db)):
    """KPI + productivity scores matching desktop refresh_dashboard / worker formulas."""
    from datetime import timedelta

    today = date.today()
    today_str = today.isoformat()
    range_start = date.fromordinal(max(1, today.toordinal() - 90))

    employees = [
        dict(r)
        for r in conn.execute(
            "SELECT id, name, joining_date, active FROM employees WHERE active=1 ORDER BY name ASC"
        ).fetchall()
    ]
    total_employees = len(employees)

    att_by_id = {}
    if employees:
        ids = [int(e["id"]) for e in employees]
        marks = ",".join("?" for _ in ids)
        for record in conn.execute(
            f"SELECT employee_id, attendance_status, check_in, check_out FROM attendance "
            f"WHERE work_date=? AND employee_id IN ({marks})",
            (today_str, *ids),
        ).fetchall():
            att_by_id[int(record["employee_id"])] = dict(record)

    present_today = absent_today = leave_today = checkins_today = 0
    attendance_roster = []
    for emp in employees:
        rec = att_by_id.get(int(emp["id"]))
        status = str((rec or {}).get("attendance_status") or "Unmarked").strip()
        check_in = str((rec or {}).get("check_in") or "").strip()
        check_out = str((rec or {}).get("check_out") or "").strip()
        has_check_in = bool(check_in)
        normalized = status.casefold()
        if desktop_app.is_present_attendance_status(status) or (
            normalized in {"unmarked", ""} and has_check_in
        ):
            if normalized == "unmarked":
                status = "Present"
            present_today += 1
            if has_check_in:
                checkins_today += 1
        elif normalized == "absent":
            status = "Absent"
            absent_today += 1
        elif normalized == "leave":
            status = "Leave"
            leave_today += 1
        else:
            status = "Not checked" if normalized in {"unmarked", "", "not checked"} else status
        attendance_roster.append(
            {
                "employee_id": emp["id"],
                "name": emp["name"],
                "status": status,
                "check_in": check_in or "—",
                "check_out": check_out or "—",
            }
        )
    not_checked_today = max(0, total_employees - present_today - absent_today - leave_today)

    tasks_today = [
        dict(r)
        for r in conn.execute(
            """SELECT t.id, t.title, t.status, t.progress, t.due_time, t.priority, e.name as employee_name
               FROM tasks t LEFT JOIN employees e ON t.employee_id = e.id
               WHERE t.task_date=? ORDER BY t.id DESC LIMIT 12""",
            (today_str,),
        ).fetchall()
    ]
    day_statuses = [r["status"] for r in conn.execute("SELECT status FROM tasks WHERE task_date=?", (today_str,)).fetchall()]
    open_tasks = sum(
        1 for st in day_statuses
        if not desktop_app.is_explicitly_completed_task_status(st)
        and not desktop_app.is_cancelled_task_status(st)
    )
    completed_tasks = sum(1 for st in day_statuses if desktop_app.is_explicitly_completed_task_status(st))

    productivity = []
    avg_productivity = 0.0
    if employees:
        ids = [int(e["id"]) for e in employees]
        marks = ",".join("?" for _ in ids)
        starts = {}
        for emp in employees:
            start = None
            if emp.get("joining_date"):
                try:
                    start = date.fromisoformat(str(emp["joining_date"]))
                except (TypeError, ValueError):
                    start = None
            starts[int(emp["id"])] = max(start or range_start, range_start)
        start_text = min(starts.values()).isoformat()
        end_text = today_str
        task_rows = conn.execute(
            f"SELECT employee_id, task_date, progress, status FROM tasks "
            f"WHERE employee_id IN ({marks}) AND task_date BETWEEN ? AND ?",
            (*ids, start_text, end_text),
        ).fetchall()
        attendance_rows = conn.execute(
            f"SELECT employee_id, work_date, attendance_status, check_in FROM attendance "
            f"WHERE employee_id IN ({marks}) AND work_date BETWEEN ? AND ?",
            (*ids, start_text, end_text),
        ).fetchall()
        holiday_rows = conn.execute(
            "SELECT holiday_date FROM holidays WHERE holiday_date BETWEEN ? AND ?",
            (start_text, end_text),
        ).fetchall()
        setting = conn.execute("SELECT value FROM settings WHERE key='working_weekdays'").fetchone()
        try:
            weekdays = {
                int(v)
                for v in ((setting["value"] if setting else "0,1,2,3,4") or "0,1,2,3,4").split(",")
                if str(v).strip()
            }
        except (TypeError, ValueError):
            weekdays = {0, 1, 2, 3, 4}
        holidays = {row["holiday_date"] for row in holiday_rows}
        tasks_by = {i: [] for i in ids}
        att_by = {i: [] for i in ids}
        for item in task_rows:
            tasks_by[int(item["employee_id"])].append(item)
        for item in attendance_rows:
            att_by[int(item["employee_id"])].append(item)
        scores = []
        for emp in employees:
            eid = int(emp["id"])
            start = starts[eid]
            start_emp = start.isoformat()
            emp_tasks = [t for t in tasks_by[eid] if start_emp <= str(t["task_date"]) <= end_text]
            task_progress_total = 0
            known = 0
            for task in emp_tasks:
                if not desktop_app.is_known_task_status(task["status"]):
                    continue
                known += 1
                try:
                    task_progress_total += max(0, min(100, int(float(task["progress"] or 0))))
                except (TypeError, ValueError, OverflowError):
                    continue
            task_score = (task_progress_total / known) if known else None
            present_count = 0
            for attendance in att_by[eid]:
                st = str(attendance["attendance_status"] or "").strip()
                has_ci = bool(str(attendance["check_in"] or "").strip())
                if desktop_app.is_present_attendance_status(st) or (
                    st.casefold() in {"unmarked", ""} and has_ci
                ):
                    present_count += 1
            working_days = 0
            current_day = start
            while current_day <= today:
                day_text = current_day.isoformat()
                if current_day.weekday() in weekdays and day_text not in holidays:
                    working_days += 1
                current_day += timedelta(days=1)
            eligible = max(1, working_days)
            attendance_score = present_count / eligible * 100 if eligible else None
            if task_score is not None and attendance_score is not None:
                score = round(task_score * 0.7 + attendance_score * 0.3)
            elif task_score is not None:
                score = round(task_score)
            elif attendance_score is not None:
                score = round(attendance_score)
            else:
                score = 0
            completed = sum(
                1 for task in emp_tasks if desktop_app.is_explicitly_completed_task_status(task["status"])
            )
            scores.append(score)
            productivity.append(
                {
                    "employee_id": eid,
                    "name": emp["name"],
                    "score": score,
                    "working_days": working_days,
                    "present_count": present_count,
                    "task_count": len(emp_tasks),
                    "completed": completed,
                    "tracking_start": start_emp,
                }
            )
        avg_productivity = round(sum(scores) / len(scores), 1) if scores else 0.0

    att_rate = round((present_today / total_employees * 100), 1) if total_employees else 0.0
    recent_employees = [
        dict(r)
        for r in conn.execute(
            "SELECT id, employee_code, name, department, designation, active FROM employees ORDER BY id DESC LIMIT 8"
        ).fetchall()
    ]

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
            "attendance_rate": att_rate,
            "avg_productivity": avg_productivity,
        },
        "recent_employees": recent_employees,
        "today_tasks": tasks_today,
        "attendance_roster": attendance_roster[:12],
        "productivity": productivity,
        "attendance_summary": (
            f"{att_rate}% checked in\n"
            f"{present_today} Present  ·  {absent_today} Absent  ·  "
            f"{leave_today} Leave  ·  {not_checked_today} Not checked"
        ),
    }

@app.get("/api/employees")
def list_employees(
    search: Optional[str] = None,
    department: Optional[str] = None,
    active_only: bool = True,
    conn: sqlite3.Connection = Depends(get_db)
):
    query = "SELECT * FROM employees WHERE 1=1"
    params = []
    if active_only:
        query += " AND active=1"
    if department:
        query += " AND department=?"
        params.append(department)
    if search:
        query += " AND (name LIKE ? OR employee_code LIKE ? OR designation LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term, term])
    
    query += " ORDER BY name ASC"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/employees")
def create_employee(emp: EmployeeModel, conn: sqlite3.Connection = Depends(get_db)):
    now = desktop_app.now_text()
    code = emp.employee_code.strip() if emp.employee_code else f"EMP{secrets.token_hex(2).upper()}"
    try:
        cursor = conn.execute(
            """INSERT INTO employees(name, employee_code, department, designation, phone, email, joining_date, notes, active, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (emp.name.strip(), code, emp.department, emp.designation, emp.phone, emp.email, emp.joining_date, emp.notes, emp.active, now)
        )
        conn.commit()
        new_id = cursor.lastrowid
        return {"id": new_id, "success": True, "employee_code": code}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Employee code '{code}' already exists")

@app.put("/api/employees/{emp_id}")
def update_employee(emp_id: int, emp: EmployeeModel, conn: sqlite3.Connection = Depends(get_db)):
    existing = conn.execute("SELECT employee_code FROM employees WHERE id=?", (emp_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")
    code = emp.employee_code.strip() if emp.employee_code and emp.employee_code.strip() else existing["employee_code"]
    try:
        conn.execute(
            """UPDATE employees SET name=?, employee_code=?, department=?, designation=?, phone=?, email=?,
                                   joining_date=?, notes=?, active=?
               WHERE id=?""",
            (emp.name.strip(), code, emp.department, emp.designation, emp.phone, emp.email,
             emp.joining_date, emp.notes, emp.active, emp_id)
        )
        conn.commit()
        return {"success": True}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Employee code '{code}' already exists")

@app.delete("/api/employees/{emp_id}")
def delete_employee(emp_id: int, conn: sqlite3.Connection = Depends(get_db)):
    # Toggle active status to prevent cascading delete data loss
    row = conn.execute("SELECT active FROM employees WHERE id=?", (emp_id,)).fetchone()
    if row:
        new_active = 0 if row["active"] == 1 else 1
        conn.execute("UPDATE employees SET active=? WHERE id=?", (new_active, emp_id))
        conn.commit()
    return {"success": True, "active": new_active if row else 0}


# --- Tasks ---
@app.get("/api/tasks")
def list_tasks(
    employee_id: Optional[int] = None,
    task_date: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    department: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db)
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
        query += " AND t.task_date=?"
        params.append(task_date)
    if status:
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
    for r in rows:
        d = dict(r)
        # Parse custom values JSON or string
        cv = d.get("custom_values") or ""
        parsed_cv = []
        if cv:
            try:
                parsed_cv = json.loads(cv)
                if not isinstance(parsed_cv, list):
                    parsed_cv = [{"key": k, "value": v} for k, v in desktop_app.parse_custom_values(cv)]
            except Exception:
                parsed_cv = [{"key": k, "value": v} for k, v in desktop_app.parse_custom_values(cv)]
        d["custom_fields"] = parsed_cv
        result.append(d)
        
    return result

@app.post("/api/tasks")
def create_task(task: TaskModel, conn: sqlite3.Connection = Depends(get_db)):
    now = desktop_app.now_text()
    t_date = task.task_date or date.today().isoformat()
    t_dept = task.department or task.category or ""
    t_details = task.details or task.notes or ""
    cv_source = task.custom_values if task.custom_values is not None else task.custom_fields
    
    # Format custom_values as JSON string
    custom_val_str = ""
    if cv_source:
        if isinstance(cv_source, (list, dict)):
            custom_val_str = json.dumps(cv_source)
        elif isinstance(cv_source, str):
            custom_val_str = cv_source
            
    emp_id = task.employee_id or 1
    cursor = conn.execute(
        """INSERT INTO tasks(employee_id, task_date, title, department, details, due_time, priority, status,
                             progress, target_qty, actual_qty, next_action, proof_url, proof_note,
                             manager_note, expose_link, custom_values, created_at, updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (emp_id, t_date, task.title.strip(), t_dept, t_details, task.due_time or "",
         task.priority or "Normal", task.status or "Not started", task.progress or 0,
         task.target_qty or "", task.actual_qty or "", task.next_action or "",
         task.proof_url or "", task.proof_note or "", task.manager_note or "",
         task.expose_link or 0, custom_val_str, now, now)
    )
    conn.commit()
    return {"id": cursor.lastrowid, "success": True, "status": task.status or "Not started", "progress": task.progress or 0}

@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, task: TaskModel, conn: sqlite3.Connection = Depends(get_db)):
    now = desktop_app.now_text()
    t_date = task.task_date or date.today().isoformat()
    t_dept = task.department or task.category or ""
    t_details = task.details or task.notes or ""
    cv_source = task.custom_values if task.custom_values is not None else task.custom_fields

    custom_val_str = ""
    if cv_source:
        if isinstance(cv_source, (list, dict)):
            custom_val_str = json.dumps(cv_source)
        elif isinstance(cv_source, str):
            custom_val_str = cv_source

    emp_id = task.employee_id or 1
    conn.execute(
        """UPDATE tasks SET employee_id=?, task_date=?, title=?, department=?, details=?, due_time=?,
                           priority=?, status=?, progress=?, target_qty=?, actual_qty=?, next_action=?,
                           proof_url=?, proof_note=?, manager_note=?, expose_link=?, custom_values=?,
                           updated_at=?
           WHERE id=?""",
        (emp_id, t_date, task.title.strip(), t_dept, t_details, task.due_time or "",
         task.priority or "Normal", task.status or "Not started", task.progress or 0,
         task.target_qty or "", task.actual_qty or "", task.next_action or "",
         task.proof_url or "", task.proof_note or "", task.manager_note or "",
         task.expose_link or 0, custom_val_str, now, task_id)
    )
    conn.commit()
    return {"id": task_id, "success": True, "status": task.status, "progress": task.progress}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    return {"success": True}


# --- Attendance & Working Calendar ---
@app.get("/api/tracker")
def employee_tracker(target_date: Optional[str] = None, conn: sqlite3.Connection = Depends(get_db)):
    day = target_date or date.today().isoformat()
    rows = conn.execute(
        """SELECT e.id,e.name,e.employee_code,e.department,e.designation,
                  COALESCE(a.attendance_status,'Unmarked') AS attendance_status,
                  COALESCE(a.check_in,'') AS check_in,COALESCE(a.check_out,'') AS check_out,
                  COUNT(t.id) AS assigned_tasks,
                  SUM(CASE WHEN lower(COALESCE(t.status,'')) IN ('completed','done','closed') THEN 1 ELSE 0 END) AS completed_tasks,
                  SUM(CASE WHEN t.id IS NOT NULL AND lower(COALESCE(t.status,'')) NOT IN ('completed','done','closed') THEN 1 ELSE 0 END) AS open_tasks,
                  COALESCE(g.target,'') AS target,COALESCE(g.target_status,'') AS target_status
           FROM employees e
           LEFT JOIN attendance a ON a.employee_id=e.id AND a.work_date=?
           LEFT JOIN tasks t ON t.employee_id=e.id AND t.task_date=?
           LEFT JOIN employee_targets g ON g.employee_id=e.id AND g.target_date=?
           WHERE e.active=1
           GROUP BY e.id,a.attendance_status,a.check_in,a.check_out,g.target,g.target_status
           ORDER BY e.name COLLATE NOCASE""",(day,day,day)).fetchall()
    return {"date":day,"employees":[dict(r) for r in rows]}


@app.get("/api/attendance")
def get_attendance(work_date: Optional[str] = None, conn: sqlite3.Connection = Depends(get_db)):
    selected_date = work_date or date.today().isoformat()
    
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
           ORDER BY e.name ASC""",
        (selected_date,)
    ).fetchall()
    
    return {
        "date": selected_date,
        "roster": [dict(r) for r in rows]
    }

@app.post("/api/attendance/mark")
def mark_attendance(item: AttendanceMarkModel, conn: sqlite3.Connection = Depends(get_db)):
    now = desktop_app.now_text()
    work_date = item.work_date or date.today().isoformat()
    status = str(item.status or item.attendance_status or "Present").strip() or "Present"
    note = item.notes or item.attendance_note or ""
    check_in = (item.check_in or "").strip()
    check_out = (item.check_out or "").strip()
    if check_in and status.casefold() in {"absent", "unmarked", ""}:
        status = "Present"
    if status.casefold() in {"absent", "leave", "unmarked"}:
        check_in, check_out = "", ""
    conn.execute(
        """INSERT INTO attendance(employee_id, work_date, attendance_status, check_in, check_out, break_minutes, attendance_note, updated_at)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(employee_id, work_date) DO UPDATE SET
               attendance_status=excluded.attendance_status,
               check_in=excluded.check_in,
               check_out=excluded.check_out,
               break_minutes=excluded.break_minutes,
               attendance_note=excluded.attendance_note,
               updated_at=excluded.updated_at""",
        (item.employee_id, work_date, status, check_in, check_out, item.break_minutes or 0, note, now)
    )
    conn.commit()
    return {"success": True}

@app.post("/api/attendance/bulk")
def bulk_attendance(
    work_date: str = Query(...),
    status: str = Query("Present"),
    conn: sqlite3.Connection = Depends(get_db)
):
    now = desktop_app.now_text()
    employees = conn.execute("SELECT id FROM employees WHERE active=1").fetchall()
    for emp in employees:
        conn.execute(
            """INSERT INTO attendance(employee_id, work_date, attendance_status, updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(employee_id, work_date) DO UPDATE SET
                   attendance_status=excluded.attendance_status,
                   updated_at=excluded.updated_at""",
            (emp["id"], work_date, status, now)
        )
    conn.commit()
    return {"success": True, "count": len(employees)}

@app.get("/api/holidays")
def list_holidays(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute("SELECT holiday_date, holiday_name, created_at FROM holidays ORDER BY holiday_date ASC").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/holidays")
def add_holiday(h: HolidayModel, conn: sqlite3.Connection = Depends(get_db)):
    now = desktop_app.now_text()
    conn.execute(
        "INSERT INTO holidays(holiday_date, holiday_name, created_at) VALUES(?,?,?) "
        "ON CONFLICT(holiday_date) DO UPDATE SET holiday_name=excluded.holiday_name",
        (h.holiday_date, h.holiday_name, now)
    )
    conn.commit()
    return {"success": True}

@app.delete("/api/holidays/{holiday_date}")
def delete_holiday(holiday_date: str, conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("DELETE FROM holidays WHERE holiday_date=?", (holiday_date,))
    conn.commit()
    return {"success": True}


# --- Business Tracking (Products & Services) ---
@app.get("/api/business/products")
def list_products(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute("SELECT * FROM bt_products ORDER BY name COLLATE NOCASE ASC").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["available_stock"] = (
            float(item.get("opening_stock") or 0) + float(item.get("received_qty") or 0)
            - float(item.get("reserved_qty") or 0) - float(item.get("dispatched_qty") or 0)
            - float(item.get("free_qty") or 0) - float(item.get("damaged_qty") or 0)
            - float(item.get("expired_qty") or 0) - float(item.get("quarantined_qty") or 0)
            + float(item.get("returned_qty") or 0)
        )
        item["low_stock"] = item["available_stock"] <= float(item.get("reorder_level") or 0)
        result.append(item)
    return result


@app.post("/api/business/products")
def create_product(p: ProductModel, user: Dict[str, Any] = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    name = (p.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Product name is required.")
    values = p.dict()
    values["sku"] = (values.get("sku") or "").strip() or None
    columns = ["name","sku","category","brand","package_type","base_unit","opening_stock","received_qty",
               "reserved_qty","dispatched_qty","free_qty","returned_qty","damaged_qty","expired_qty",
               "quarantined_qty","purchase_cost","selling_price","reorder_level","batch_number",
               "expiry_date","storage_location","updated_by","updated_at"]
    now = desktop_app.now_text()
    try:
        cur = conn.execute("INSERT INTO bt_products("+",".join(columns)+") VALUES("+",".join("?" for _ in columns)+")",
            tuple(values.get(c) if c not in ("updated_by","updated_at") else (user.get("username","") if c=="updated_by" else now) for c in columns))
        product_id = cur.lastrowid
        for kind, qty in (("Opening",p.opening_stock or 0),("Received",p.received_qty or 0)):
            if qty:
                conn.execute("INSERT INTO bt_stock_ledger(product_id,txn_type,quantity,unit,reference,created_by,created_at) VALUES(?,?,?,?,?,?,?)",
                    (product_id,kind,qty,p.base_unit or "PCS","Initial stock",user.get("username",""),now))
        conn.commit()
        return {"success": True, "id": product_id}
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="This SKU already exists.") from exc


@app.put("/api/business/products/{product_id}")
def update_product(product_id: int, p: ProductModel, user: Dict[str, Any] = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    if not conn.execute("SELECT 1 FROM bt_products WHERE id=?", (product_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Product not found.")
    values = p.dict()
    values["sku"] = (values.get("sku") or "").strip() or None
    columns = ["name","sku","category","brand","package_type","base_unit","opening_stock","received_qty",
               "reserved_qty","dispatched_qty","free_qty","returned_qty","damaged_qty","expired_qty",
               "quarantined_qty","purchase_cost","selling_price","reorder_level","batch_number","expiry_date","storage_location"]
    try:
        conn.execute("UPDATE bt_products SET "+",".join(c+"=?" for c in columns)+",updated_by=?,updated_at=? WHERE id=?",
            tuple(values.get(c) for c in columns)+(user.get("username",""),desktop_app.now_text(),product_id))
        conn.commit()
        return {"success": True}
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="This SKU already exists.") from exc


@app.get("/api/business/products/{product_id}/ledger")
def product_stock_ledger(product_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if not conn.execute("SELECT 1 FROM bt_products WHERE id=?", (product_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Product not found.")
    return [dict(r) for r in conn.execute("SELECT * FROM bt_stock_ledger WHERE product_id=? ORDER BY id DESC LIMIT 500",(product_id,)).fetchall()]


@app.post("/api/business/products/{product_id}/stock")
def add_stock_transaction(product_id: int, item: StockTransactionModel, user: Dict[str, Any] = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    product = conn.execute("SELECT * FROM bt_products WHERE id=?", (product_id,)).fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    kind = (item.txn_type or "").strip().title()
    qty = float(item.quantity)
    columns = {"Received":"received_qty","Reserved":"reserved_qty","Dispatched":"dispatched_qty","Free":"free_qty",
               "Returned":"returned_qty","Damaged":"damaged_qty","Expired":"expired_qty","Quarantined":"quarantined_qty"}
    if kind not in set(columns)|{"Reserve Released"} or qty <= 0:
        raise HTTPException(status_code=400, detail="Choose a valid stock transaction and a quantity greater than zero.")
    now = desktop_app.now_text()
    if kind == "Reserve Released":
        if qty > float(product["reserved_qty"] or 0):
            raise HTTPException(status_code=400, detail="Released quantity exceeds reserved stock.")
        conn.execute("UPDATE bt_products SET reserved_qty=reserved_qty-?,updated_at=?,updated_by=? WHERE id=?",(qty,now,user.get("username",""),product_id))
    elif kind == "Dispatched":
        release = min(float(product["reserved_qty"] or 0),qty)
        conn.execute("UPDATE bt_products SET dispatched_qty=dispatched_qty+?,reserved_qty=reserved_qty-?,updated_at=?,updated_by=? WHERE id=?",(qty,release,now,user.get("username",""),product_id))
    else:
        col=columns[kind]
        conn.execute(f"UPDATE bt_products SET {col}={col}+?,updated_at=?,updated_by=? WHERE id=?",(qty,now,user.get("username",""),product_id))
    cur=conn.execute("INSERT INTO bt_stock_ledger(product_id,txn_type,quantity,unit,reference,notes,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (product_id,kind,qty,item.unit or product["base_unit"] or "PCS",item.reference or "",item.notes or "",user.get("username",""),now))
    conn.commit()
    return {"success":True,"id":cur.lastrowid}


@app.get("/api/business/services")
def list_services(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute("SELECT * FROM bt_services ORDER BY name ASC").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/business/services")
def create_service(s: ServiceModel, conn: sqlite3.Connection = Depends(get_db)):
    now = desktop_app.now_text()
    conn.execute(
        """INSERT INTO bt_services(name, category, description, training_mode, service_unit, session_duration, num_sessions, plan_validity, standard_price, active, updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (s.name, s.category, s.description, s.training_mode, s.service_unit, s.session_duration, s.num_sessions, s.plan_validity, s.standard_price, s.active, now)
    )
    conn.commit()
    return {"success": True}


# --- Reports & Print Center ---
@app.post("/api/reports/preview")
def generate_report_preview(req: ReportOptionsModel, conn: sqlite3.Connection = Depends(get_db)):
    # Standard EOD options default mapping
    opts = {
        "identity": True, "tasks": True, "details": True, "due_time": True,
        "proof": True, "proof_notes": True, "expose_link": False, "remarks": True,
        "target_qty": True, "actual_qty": True, "completion_pct": True,
        "priority": True, "custom_values": True, "next_action": True,
        "business_products": False, "business_services": False,
        "attendance": True, "summary": True
    }
    if req.options:
        opts.update(req.options)

    # Build rich formatted text preview
    lines = []
    lines.append(f"════════════════════════════════════════════════════════════════════")
    lines.append(f"     RAW STRENGTH CALISTHENICS - EMPLOYEE AUDIT & OPERATIONS REPORT")
    lines.append(f"════════════════════════════════════════════════════════════════════")
    lines.append(f"Report Date : {req.date}")
    lines.append(f"Scope       : {'Specific Employee' if req.employee_id else 'All Employees (Company-Wide)'}")
    lines.append(f"Generated   : {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
    lines.append(f"────────────────────────────────────────────────────────────────────\n")

    emp_query = "SELECT * FROM employees WHERE active=1"
    emp_params = []
    if req.employee_id:
        emp_query += " AND id=?"
        emp_params.append(req.employee_id)
    emp_query += " ORDER BY name ASC"
    
    employees = conn.execute(emp_query, emp_params).fetchall()

    for emp in employees:
        lines.append(f"■ EMPLOYEE: {emp['name']} [{emp['employee_code'] or 'N/A'}]")
        if opts.get("identity"):
            lines.append(f"  Department  : {emp['department'] or 'General'} | Title: {emp['designation'] or 'Staff'}")
            if emp['phone'] or emp['email']:
                lines.append(f"  Contact     : {emp['phone']} {emp['email']}")
        
        # Attendance status for that date
        att = conn.execute(
            "SELECT * FROM attendance WHERE employee_id=? AND work_date=?", (emp["id"], req.date)
        ).fetchone()
        if att:
            in_t = att["check_in"] or "--:--"
            out_t = att["check_out"] or "--:--"
            lines.append(f"  Attendance  : [{att['attendance_status']}] In: {in_t} | Out: {out_t} | Notes: {att['attendance_note'] or 'None'}")
        else:
            lines.append(f"  Attendance  : [Unmarked]")

        # Tasks for that date
        tasks = conn.execute("SELECT * FROM tasks WHERE employee_id=? AND task_date=?", (emp["id"], req.date)).fetchall()
        if tasks:
            lines.append(f"  Assigned Tasks ({len(tasks)}):")
            for t in tasks:
                t_title = t["title"]
                t_stat = t["status"]
                t_prog = f"{t['progress']}%" if opts.get("completion_pct") else ""
                lines.append(f"    • {t_title} - [{t_stat}] {t_prog}")
                if opts.get("target_qty") and t["target_qty"]:
                    lines.append(f"        Target Qty: {t['target_qty']}")
                if opts.get("actual_qty") and t["actual_qty"]:
                    lines.append(f"        Actual Qty: {t['actual_qty']}")
                if opts.get("priority") and t["priority"]:
                    lines.append(f"        Priority: {t['priority']}")
                if opts.get("due_time") and t["due_time"]:
                    lines.append(f"        Due time: {t['due_time']}")
                if opts.get("details") and t["details"]:
                    lines.append(f"        Details: {t['details']}")
                if opts.get("custom_values") and t["custom_values"]:
                    lines.append(f"        Custom Values: {t['custom_values']}")
                if opts.get("proof") and t["proof_url"]:
                    p_disp = t["proof_url"] if opts.get("expose_link") else "Tap here to view content"
                    lines.append(f"        Proof link: {p_disp}")
                if opts.get("next_action") and t["next_action"]:
                    lines.append(f"        Next Action: {t['next_action']}")
        else:
            lines.append(f"  Tasks       : No tasks assigned for this date.")

        lines.append(f"\n" + ("─" * 68) + "\n")

    return {"preview_text": "\n".join(lines)}


@app.post("/api/reports/export")
def export_report(req: ReportOptionsModel, report_format: str = Query("pdf", alias="format"), conn: sqlite3.Connection = Depends(get_db)):
    fmt=(report_format or "pdf").lower()
    if fmt not in {"pdf","docx","csv"}:
        raise HTTPException(status_code=400,detail="Supported formats are PDF, Word and CSV.")
    preview=generate_report_preview(req,conn)["preview_text"]
    out=Path(desktop_app.EXPORT_DIR);out.mkdir(parents=True,exist_ok=True)
    target=out/f"Audit-Report-{req.date}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{fmt}"
    try:
        if fmt=="csv":
            with target.open("w",encoding="utf-8-sig",newline="") as f:
                writer=csv.writer(f);writer.writerow(["Report line"]);writer.writerows([[x] for x in preview.splitlines()])
            media="text/csv"
        elif fmt=="docx":
            from docx import Document
            doc=Document();doc.add_heading("Raw Strength Calisthenics — Employee Audit Report",0)
            for line in preview.splitlines(): doc.add_paragraph(line)
            doc.save(str(target));media="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate,Preformatted
            from reportlab.lib.styles import getSampleStyleSheet
            safe=preview.encode("ascii","replace").decode("ascii")
            doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=32,leftMargin=32,topMargin=32,bottomMargin=32)
            doc.build([Preformatted(safe,getSampleStyleSheet()["Code"])]);media="application/pdf"
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500,detail=f"Report export failed: {exc}") from exc
    return FileResponse(str(target),media_type=media,filename=target.name)


@app.get("/api/archive")
def list_archived_documents(conn: sqlite3.Connection = Depends(get_db)):
    return [dict(r) for r in conn.execute(
        "SELECT id,employee_id,report_date,file_name,mime_type,notes,uploaded_at,length(content) AS size_bytes FROM archived_documents ORDER BY uploaded_at DESC,id DESC LIMIT 500"
    ).fetchall()]


@app.post("/api/archive")
async def upload_archived_document(file: UploadFile = File(...), report_date: str = Form(""), employee_id: Optional[int] = Form(None), notes: str = Form(""), user: Dict[str, Any] = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    filename=Path(file.filename or "archive.bin").name
    content=await file.read(25*1024*1024+1);await file.close()
    if not content or len(content)>25*1024*1024:
        raise HTTPException(status_code=413,detail="Archive file is empty or exceeds 25 MB.")
    cur=conn.execute("INSERT INTO archived_documents(employee_id,report_date,file_name,mime_type,content,notes,uploaded_at) VALUES(?,?,?,?,?,?,?)",
        (employee_id,report_date,filename,file.content_type or "application/octet-stream",content,notes,desktop_app.now_text()))
    conn.commit()
    return {"success":True,"id":cur.lastrowid}


@app.get("/api/archive/{document_id}/download")
def download_archived_document(document_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row=conn.execute("SELECT file_name,mime_type,content FROM archived_documents WHERE id=?",(document_id,)).fetchone()
    if not row: raise HTTPException(status_code=404,detail="Archived document not found.")
    filename=Path(row["file_name"] or "archive.bin").name.replace('"',"")
    return Response(content=bytes(row["content"]),media_type=row["mime_type"] or "application/octet-stream",
        headers={"Content-Disposition":f'attachment; filename="{filename}"',"Cache-Control":"no-store"})


@app.delete("/api/archive/{document_id}")
def delete_archived_document(document_id: int, conn: sqlite3.Connection = Depends(get_db)):
    cur=conn.execute("DELETE FROM archived_documents WHERE id=?",(document_id,));conn.commit()
    if not cur.rowcount: raise HTTPException(status_code=404,detail="Archived document not found.")
    return {"success":True}


# --- Live Chat ---
@app.get("/api/chat/messages")
def get_chat_messages(channel: str = "general", conn: sqlite3.Connection = Depends(get_db)):
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
        "SELECT id,channel,sender AS sender_name,role,content,created_at FROM local_chat_messages WHERE channel=? ORDER BY id ASC LIMIT 100", (channel,)
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


# --- Settings ---
@app.get("/api/settings")
def get_settings(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings_dict = {r["key"]: r["value"] for r in rows}
    return {
        "settings": settings_dict,
        "app_version": APP_VERSION,
        "app_name": desktop_app.APP_NAME,
    }

@app.post("/api/settings")
def update_settings(data: Dict[str, str], conn: sqlite3.Connection = Depends(get_db)):
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


# --- Serve Built React Frontend (SPA Fallback) ---
DIST_DIR = ROOT_DIR / "frontend" / "dist"

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
            # Vite emits content-hashed assets; those may be cached immutably.
            # SPA documents must revalidate so browsers cannot keep an obsolete
            # login bundle after a web-only deployment.
            if file_path.suffix.lower() in {".js", ".css", ".woff", ".woff2", ".png", ".jpg", ".svg"}:
                return FileResponse(file_path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
            return FileResponse(file_path, headers={"Cache-Control": "no-store, max-age=0, must-revalidate"})
        return FileResponse(
            DIST_DIR / "index.html",
            headers={"Cache-Control": "no-store, max-age=0, must-revalidate"},
        )
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
