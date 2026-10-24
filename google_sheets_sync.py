"""Google Sheets Cloud Database Sync for Raw Strength Employee Audit Manager.

Synchronizes the application's local SQLite database with the central Google Spreadsheet:
https://docs.google.com/spreadsheets/d/1edK9BASSDPOcJZ94WcaCkWAoQHr-AkgTmy6axWv0r-o/edit
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import io
import logging
from pathlib import Path
import sqlite3
import urllib.request
import openpyxl

GOOGLE_SHEET_ID = "1edK9BASSDPOcJZ94WcaCkWAoQHr-AkgTmy6axWv0r-o"
GOOGLE_SHEET_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx"

log = logging.getLogger("google_sheets_sync")


def fetch_google_sheet_bytes(url: str = GOOGLE_SHEET_EXPORT_URL, timeout: int = 20) -> bytes:
    """Download the current live spreadsheet as Excel bytes directly from Google."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RawStrengthSync/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Google Sheets returned HTTP {resp.status}")
        return resp.read()


def sync_database_from_workbook_bytes(db, xlsx_bytes: bytes) -> dict:
    """Parse all sheets from the workbook bytes and upsert into the SQLite database.
    
    Additive & safe: Does NOT delete any local records; merges and updates records by key.
    """
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    stats = {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Sync Employees
    if "Employees" in wb.sheetnames:
        sheet = wb["Employees"]
        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) > 1:
            header = [str(h or '').strip().lower() for h in rows[0]]
            col_idx = {h: idx for idx, h in enumerate(header)}
            upserted = 0
            for r in rows[1:]:
                if not any(r):
                    continue
                emp_id = r[col_idx.get("id", 0)]
                emp_code = r[col_idx.get("employee_code", 1)] if "employee_code" in col_idx else f"EMP{emp_id}"
                name = r[col_idx.get("name", 2)] if "name" in col_idx else ""
                if not name:
                    continue
                dept = r[col_idx.get("department", 3)] if "department" in col_idx else "General"
                desig = r[col_idx.get("designation", 4)] if "designation" in col_idx else ""
                phone = r[col_idx.get("phone", 5)] if "phone" in col_idx else ""
                email = r[col_idx.get("email", 6)] if "email" in col_idx else ""
                join_date = str(r[col_idx.get("joining_date", 7)] or "") if "joining_date" in col_idx else ""
                active = int(r[col_idx.get("active", 8)] or 1) if "active" in col_idx else 1
                notes = str(r[col_idx.get("notes", 9)] or "") if "notes" in col_idx else ""
                display_order = int(r[col_idx.get("display_order", 11)] or 0) if "display_order" in col_idx else 0

                db.conn.execute("""
                    INSERT INTO employees(id, employee_code, name, department, designation, phone, email, joining_date, active, notes, created_at, display_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      name=excluded.name, department=excluded.department, designation=excluded.designation,
                      phone=excluded.phone, email=excluded.email, active=excluded.active, notes=excluded.notes,
                      display_order=excluded.display_order
                """, (emp_id, emp_code, name, dept, desig, phone, email, join_date, active, notes, now, display_order))
                upserted += 1
            stats["employees"] = upserted

    # 2. Sync Tasks
    if "Tasks" in wb.sheetnames:
        sheet = wb["Tasks"]
        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) > 1:
            header = [str(h or '').strip().lower() for h in rows[0]]
            col_idx = {h: idx for idx, h in enumerate(header)}
            upserted = 0
            for r in rows[1:]:
                if not any(r):
                    continue
                task_id = r[col_idx.get("id", 0)]
                emp_id = r[col_idx.get("employee_id", 1)]
                task_date = str(r[col_idx.get("task_date", 2)] or "")
                title = str(r[col_idx.get("title", 3)] or "")
                if not title or not emp_id:
                    continue
                details = str(r[col_idx.get("details", 4)] or "")
                due_time = str(r[col_idx.get("due_time", 5)] or "18:00")
                priority = str(r[col_idx.get("priority", 6)] or "Medium")
                status = str(r[col_idx.get("status", 7)] or "Pending")
                progress = int(r[col_idx.get("progress", 8)] or 0)
                proof_url = str(r[col_idx.get("proof_url", 9)] or "")
                proof_note = str(r[col_idx.get("proof_note", 10)] or "")
                dept = str(r[col_idx.get("department", 20)] or "") if "department" in col_idx else ""

                db.conn.execute("""
                    INSERT INTO tasks(id, employee_id, task_date, title, details, due_time, priority, status, progress, proof_url, proof_note, department, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      title=excluded.title, details=excluded.details, due_time=excluded.due_time,
                      priority=excluded.priority, status=excluded.status, progress=excluded.progress,
                      proof_url=excluded.proof_url, proof_note=excluded.proof_note, department=excluded.department,
                      updated_at=excluded.updated_at
                """, (task_id, emp_id, task_date, title, details, due_time, priority, status, progress, proof_url, proof_note, dept, now, now))
                upserted += 1
            stats["tasks"] = upserted

    # 3. Sync Attendance
    if "Attendance" in wb.sheetnames:
        sheet = wb["Attendance"]
        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) > 1:
            header = [str(h or '').strip().lower() for h in rows[0]]
            col_idx = {h: idx for idx, h in enumerate(header)}
            upserted = 0
            for r in rows[1:]:
                if not any(r):
                    continue
                att_id = r[col_idx.get("id", 0)]
                emp_id = r[col_idx.get("employee_id", 1)]
                work_date = str(r[col_idx.get("work_date", 2)] or "")
                if not emp_id or not work_date:
                    continue
                check_in = str(r[col_idx.get("check_in", 3)] or "")
                check_out = str(r[col_idx.get("check_out", 4)] or "")
                break_mins = int(r[col_idx.get("break_minutes", 5)] or 0)
                att_status = str(r[col_idx.get("attendance_status", 6)] or "Present")
                att_note = str(r[col_idx.get("attendance_note", 7)] or "")

                db.conn.execute("""
                    INSERT INTO attendance(id, employee_id, work_date, check_in, check_out, break_minutes, attendance_status, attendance_note, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(employee_id, work_date) DO UPDATE SET
                      check_in=excluded.check_in, check_out=excluded.check_out, break_minutes=excluded.break_minutes,
                      attendance_status=excluded.attendance_status, attendance_note=excluded.attendance_note,
                      updated_at=excluded.updated_at
                """, (att_id, emp_id, work_date, check_in, check_out, break_mins, att_status, att_note, now))
                upserted += 1
            stats["attendance"] = upserted

    # 4. Sync StoresData / Customer Prospects
    if "StoresData" in wb.sheetnames:
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customer_prospects'")
        if cursor.fetchone():
            sheet = wb["StoresData"]
            rows = list(sheet.iter_rows(values_only=True))
            if len(rows) > 1:
                upserted = 0
                for r in rows[1:]:
                    if not any(r):
                        continue
                    state = str(r[0] or '').strip()
                    city = str(r[1] or '').strip()
                    area = str(r[2] or '').strip()
                    cat = str(r[3] or 'Supplement Store').strip()
                    name = str(r[4] or '').strip()
                    if not name:
                        continue
                    phone = str(r[5] or '').strip()
                    addr = str(r[6] or '').strip()
                    maps = str(r[7] or '').strip()
                    web = str(r[8] or '').strip()
                    dedupe = hashlib.sha256(f"{name}|{city}|{state}|{phone}".encode()).hexdigest()

                    db.conn.execute("""
                        INSERT OR IGNORE INTO customer_prospects(
                            dedupe_key, kind, business_name, business_category, state, city, area,
                            phone, address, website, maps, source_name, source_type, source_status,
                            created_at, updated_at
                        ) VALUES (?, 'Store', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Google Sheets Master', 'Central Sheet', 'Active Lead', ?, ?)
                    """, (dedupe, name, cat, state, city, area, phone, addr, web, maps, now, now))
                    upserted += 1
                stats["stores"] = upserted

    db.conn.commit()
    wb.close()
    return stats


def sync_from_live_google_sheet(db) -> dict:
    """Download the live Google Spreadsheet and sync all data into SQLite.
    Gracefully handles offline environments without unhandled exceptions."""
    try:
        xlsx_bytes = fetch_google_sheet_bytes()
        if xlsx_bytes and len(xlsx_bytes) > 500:
            return sync_database_from_workbook_bytes(db, xlsx_bytes)
    except Exception as exc:
        log.info("Live Google Sheet download skipped or offline: %s", exc)
    return {}


def save_master_database_snapshot(db, custom_path=None) -> str:
    """Generate and save an offline Excel snapshot of the master database (Users, Tasks, Attendance, Stores).
    Always keeps a local/Downloads copy preserved during every update."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    
    # Styling
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # 1. Users sheet
    ws_users = wb.active
    ws_users.title = "Users"
    user_headers = ["ID", "Name", "Employee Code", "Email", "Phone", "Role", "Department", "Designation", "Joining Date", "Salary", "Active"]
    ws_users.append(user_headers)
    for col_idx in range(1, len(user_headers) + 1):
        cell = ws_users.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
    
    if db is not None:
        try:
            cursor = db.conn.execute("SELECT id, name, employee_code, email, phone, role, department, designation, joining_date, salary, active FROM employees ORDER BY id")
            for row in cursor.fetchall():
                ws_users.append(list(row))
        except Exception:
            pass

    # 2. Tasks sheet
    ws_tasks = wb.create_sheet(title="Tasks")
    task_headers = ["ID", "Employee ID", "Task Date", "Title", "Details", "Due Time", "Status", "Progress", "Proof URL", "Proof Note", "Manager Note", "Custom Values", "Updated At"]
    ws_tasks.append(task_headers)
    for col_idx in range(1, len(task_headers) + 1):
        cell = ws_tasks.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
    
    if db is not None:
        try:
            # Exclude developer test records if any are tagged
            cursor = db.conn.execute("""
                SELECT id, employee_id, task_date, title, details, due_time, status, progress, proof_url, proof_note, manager_note, custom_values, updated_at
                FROM tasks
                WHERE COALESCE(custom_values, '') NOT LIKE '%created_by%'
                  AND COALESCE(custom_values, '') NOT LIKE '%test_mode%'
                ORDER BY task_date DESC, id DESC
            """)
            for row in cursor.fetchall():
                ws_tasks.append(list(row))
        except Exception:
            pass

    # 3. Attendance sheet
    ws_att = wb.create_sheet(title="Attendance")
    att_headers = ["ID", "Employee ID", "Date", "Status", "Check In", "Check Out", "Total Hours", "Remarks", "Updated At"]
    ws_att.append(att_headers)
    for col_idx in range(1, len(att_headers) + 1):
        cell = ws_att.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font

    if db is not None:
        try:
            cursor = db.conn.execute("SELECT id, employee_id, date, status, check_in, check_out, total_hours, remarks, updated_at FROM attendance ORDER BY date DESC, id DESC")
            for row in cursor.fetchall():
                ws_att.append(list(row))
        except Exception:
            pass

    # 4. StoresData / Customer Prospects sheet
    ws_stores = wb.create_sheet(title="StoresData")
    store_headers = ["State", "City", "Area", "Category", "Store Name", "Phone", "Email", "Address", "Google Maps Link", "Website"]
    ws_stores.append(store_headers)
    for col_idx in range(1, len(store_headers) + 1):
        cell = ws_stores.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font

    if db is not None:
        try:
            # Check if email column exists
            cursor = db.conn.execute("PRAGMA table_info(customer_prospects)")
            cols = {c[1] for c in cursor.fetchall()}
            email_col = "email" if "email" in cols else "'' AS email"
            cursor = db.conn.execute(f"SELECT state, city, area, business_category, business_name, phone, {email_col}, address, maps, website FROM customer_prospects ORDER BY state, city, business_name")
            for row in cursor.fetchall():
                ws_stores.append(list(row))
        except Exception:
            pass

    # Auto-adjust column widths
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

    # Determine target file path
    active_user = getattr(db, "active_user", None)
    is_dev = False
    try:
        from app import is_developer_test_user
        is_dev = is_developer_test_user(active_user)
    except Exception:
        pass

    if custom_path:
        out_path = Path(custom_path)
    else:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        fname = "Google_Sheets_Test_admin_Snapshot.xlsx" if is_dev else "Google_Sheets_Master_Database.xlsx"
        out_path = downloads_dir / fname

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_path))
    wb.close()
    return str(out_path)


def continuous_auto_sync(db) -> dict:
    """Silent background continuous sync with Google Sheets.
    Offline-first: updates local DB immediately; when internet connects,
    silently merges and appends without conflicts and without deleting any data.
    Both Developer (admin) and Customer (Taruna) get the latest synced master data."""
    if db is None:
        return {"status": "error", "message": "Database unavailable"}

    active_user = getattr(db, "active_user", None)
    is_dev = False
    try:
        from app import is_developer_test_user
        is_dev = is_developer_test_user(active_user)
    except Exception:
        pass

    try:
        # Check connectivity by fetching sheet bytes with 5s timeout
        req = urllib.request.Request(
            f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx",
            headers={"User-Agent": "Mozilla/5.0 RawStrengthSync/1.3"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                xlsx_bytes = response.read()
                if len(xlsx_bytes) > 1000:
                    # Developer always gets synced data of Taruna / Admin into local view
                    stats = sync_database_from_workbook_bytes(db, xlsx_bytes=xlsx_bytes)
                    # Keep local master snapshot updated
                    try:
                        save_master_database_snapshot(db)
                    except Exception:
                        pass
                    return {"status": "synced", "updated": sum(stats.values()), "stats": stats, "is_dev": is_dev}
    except Exception as exc:
        logging.getLogger("google_sheets_sync").info("Continuous sync offline notice: %s", exc)

    return {"status": "offline", "message": "Operating offline. Local database preserved."}
