"""FastAPI REST API server for Raw Strength Calisthenics Employee Audit & Operations OS.
Exposes complete REST endpoints while preserving 100% of underlying SQLite business logic.
"""
import os
import sys
import json
import sqlite3
import secrets
from pathlib import Path
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

# Ensure repo root is in python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app as desktop_app
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

def ensure_database():
    global _DB_INITIALIZED
    if not _DB_INITIALIZED:
        try:
            db = desktop_app.Database()
            try:
                import business_tracking
                business_tracking.setup_business_tables(db.conn)
            except Exception:
                pass
            if hasattr(db, "close_github_sync"):
                db.close_github_sync(timeout=0)
            if hasattr(db, "conn") and db.conn:
                db.conn.close()
        except Exception:
            pass
        _DB_INITIALIZED = True

def get_db():
    """Create a thread-safe connection to the exact same database."""
    ensure_database()
    db_path = desktop_app.DB_PATH
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

# Token memory store for lightweight session management
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_current_user(authorization: Optional[str] = Header(None), conn: sqlite3.Connection = Depends(get_db)):
    if not authorization:
        # Default fallback to first active admin/user for seamless local development
        row = conn.execute("SELECT id, username, display_name, role FROM auth_users WHERE active=1 ORDER BY id ASC LIMIT 1").fetchone()
        if row:
            return dict(row)
        return {"id": 1, "username": "Admin", "display_name": "Administrator", "role": "Admin"}
    
    token = authorization.replace("Bearer ", "").strip()
    if token in ACTIVE_SESSIONS:
        return ACTIVE_SESSIONS[token]
    
    # Check if token matches a username directly for testing
    row = conn.execute("SELECT id, username, display_name, role FROM auth_users WHERE username=? COLLATE NOCASE AND active=1", (token,)).fetchone()
    if row:
        return dict(row)
    
    # Fallback to first user
    row = conn.execute("SELECT id, username, display_name, role FROM auth_users WHERE active=1 ORDER BY id ASC LIMIT 1").fetchone()
    if row:
        return dict(row)
    return {"id": 1, "username": "Admin", "display_name": "Administrator", "role": "Admin"}


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
    base_unit: Optional[str] = "PCS"
    opening_stock: Optional[float] = 0.0
    received_qty: Optional[float] = 0.0
    reserved_qty: Optional[float] = 0.0
    reorder_level: Optional[float] = 0.0
    selling_price: Optional[float] = 0.0

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
    row = conn.execute("SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1", (username,)).fetchone()
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


# --- Dashboard Analytics ---
@app.get("/api/dashboard")
def get_dashboard(conn: sqlite3.Connection = Depends(get_db)):
    today_str = date.today().isoformat()
    
    total_employees = conn.execute("SELECT COUNT(*) FROM employees WHERE active=1").fetchone()[0]
    present_today = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE work_date=? AND attendance_status='Present'", (today_str,)
    ).fetchone()[0]
    absent_today = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE work_date=? AND attendance_status='Absent'", (today_str,)
    ).fetchone()[0]
    leave_today = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE work_date=? AND attendance_status='Leave'", (today_str,)
    ).fetchone()[0]
    checkins_today = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE work_date=? AND check_in != ''", (today_str,)
    ).fetchone()[0]
    open_tasks = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE task_date=? AND status IN ('Not started', 'In progress')", (today_str,)
    ).fetchone()[0]
    completed_tasks = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE task_date=? AND status='Completed'", (today_str,)
    ).fetchone()[0]

    # Attendance percentage
    att_rate = round((present_today / total_employees * 100), 1) if total_employees > 0 else 0.0

    # Recent employees
    recent_employees = [
        dict(r) for r in conn.execute(
            "SELECT id, employee_code, name, department, designation, active FROM employees ORDER BY id DESC LIMIT 5"
        ).fetchall()
    ]

    # Today's tasks with employee names
    today_tasks = [
        dict(r) for r in conn.execute(
            """SELECT t.id, t.title, t.status, t.progress, t.due_time, t.priority, e.name as employee_name
               FROM tasks t
               LEFT JOIN employees e ON t.employee_id = e.id
               WHERE t.task_date=?
               ORDER BY t.id DESC LIMIT 6""",
            (today_str,)
        ).fetchall()
    ]

    # Attendance roster summary
    attendance_roster = [
        dict(r) for r in conn.execute(
            """SELECT e.id as employee_id, e.name, e.employee_code, e.department,
                      COALESCE(a.attendance_status, 'Unmarked') as status,
                      COALESCE(a.check_in, '') as check_in,
                      COALESCE(a.check_out, '') as check_out
               FROM employees e
               LEFT JOIN attendance a ON e.id = a.employee_id AND a.work_date=?
               WHERE e.active=1
               ORDER BY e.name ASC LIMIT 6""",
            (today_str,)
        ).fetchall()
    ]

    return {
        "today": today_str,
        "kpis": {
            "total_employees": total_employees,
            "present_today": present_today,
            "absent_today": absent_today,
            "leave_today": leave_today,
            "open_tasks": open_tasks,
            "completed_tasks": completed_tasks,
            "checkins_today": checkins_today,
            "attendance_rate": att_rate,
        },
        "recent_employees": recent_employees,
        "today_tasks": today_tasks,
        "attendance_roster": attendance_roster,
    }


# --- Employees ---
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
    status = item.status or item.attendance_status or "Present"
    note = item.notes or item.attendance_note or ""
    conn.execute(
        """INSERT INTO attendance(employee_id, work_date, attendance_status, check_in, check_out, break_minutes, attendance_note, updated_at)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(employee_id, work_date) DO UPDATE SET
               attendance_status=excluded.attendance_status,
               check_in=CASE WHEN excluded.check_in != '' THEN excluded.check_in ELSE attendance.check_in END,
               check_out=CASE WHEN excluded.check_out != '' THEN excluded.check_out ELSE attendance.check_out END,
               break_minutes=excluded.break_minutes,
               attendance_note=excluded.attendance_note,
               updated_at=excluded.updated_at""",
        (item.employee_id, work_date, status, item.check_in or "", item.check_out or "", item.break_minutes or 0, note, now)
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
    rows = conn.execute("SELECT * FROM bt_products ORDER BY name ASC").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["available_stock"] = (d.get("opening_stock", 0) or 0) + (d.get("received_qty", 0) or 0) - (d.get("reserved_qty", 0) or 0)
        result.append(d)
    return result

@app.post("/api/business/products")
def create_product(p: ProductModel, conn: sqlite3.Connection = Depends(get_db)):
    now = desktop_app.now_text()
    conn.execute(
        """INSERT INTO bt_products(name, sku, category, brand, base_unit, opening_stock, received_qty, reserved_qty, reorder_level, selling_price, updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (p.name, p.sku, p.category, p.brand, p.base_unit, p.opening_stock, p.received_qty, p.reserved_qty, p.reorder_level, p.selling_price, now)
    )
    conn.commit()
    return {"success": True}

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

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/")
    def serve_react_root():
        return FileResponse(DIST_DIR / "index.html")

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
