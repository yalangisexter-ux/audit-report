"""Operational APIs for web parity — EXE untouched."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
import sqlite3
import secrets

import api_server as api


def _rows(conn, sql, params=()):
    try:
        cur = conn.execute(sql, params)
        cols = [c[0] for c in cur.description] if cur.description else []
        out = []
        for r in cur.fetchall():
            if isinstance(r, sqlite3.Row):
                out.append(dict(r))
            else:
                out.append({cols[i]: r[i] for i in range(len(cols))})
        return out
    except Exception:
        return []


def _count(conn, sql, params=()):
    try:
        return int(conn.execute(sql, params).fetchone()[0] or 0)
    except Exception:
        return 0


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@api.app.get("/api/business/orders")
def list_business_orders(conn: sqlite3.Connection = Depends(api.get_db)):
    return _rows(conn, "SELECT id,external_order_id AS order_code,order_date,sales_channel AS channel,customer_name,contact,payment_mode,order_status AS status,discount,order_value,invoice_number,shipment_id,assigned_employee_id,updated_by,updated_at,remarks FROM bt_orders ORDER BY id DESC LIMIT 300")


@api.app.get("/api/business/members")
def list_business_members(conn: sqlite3.Connection = Depends(api.get_db)):
    return _rows(conn, """SELECT m.id,m.name AS full_name,m.contact AS phone,m.service_id,s.name AS plan_name,m.training_mode,m.registration_date AS start_date,m.expiry_date AS end_date,m.sessions_purchased,m.sessions_completed,m.status,m.payment_status,m.invoice_ref,m.remarks FROM bt_members m LEFT JOIN bt_services s ON s.id=m.service_id ORDER BY m.id DESC LIMIT 300""")


@api.app.get("/api/business/activities")
def list_business_activities(conn: sqlite3.Connection = Depends(api.get_db)):
    return _rows(conn, "SELECT * FROM bt_activities ORDER BY id DESC LIMIT 300")


@api.app.get("/api/business/overview")
def business_overview(conn: sqlite3.Connection = Depends(api.get_db)):
    return {
        "products": _count(conn, "SELECT COUNT(*) FROM bt_products"),
        "orders": _count(conn, "SELECT COUNT(*) FROM bt_orders"),
        "services": _count(conn, "SELECT COUNT(*) FROM bt_services"),
        "members": _count(conn, "SELECT COUNT(*) FROM bt_members"),
        "activities": _count(conn, "SELECT COUNT(*) FROM bt_activities"),
        "open_orders": _count(
            conn,
            "SELECT COUNT(*) FROM bt_orders WHERE lower(IFNULL(status,'')) NOT IN ('completed','cancelled','delivered','closed')",
        ),
        "active_members": _count(
            conn,
            "SELECT COUNT(*) FROM bt_members WHERE lower(IFNULL(status,'')) IN ('active','current','ongoing') OR IFNULL(status,'') = ''",
        ),
    }


class OrderIn(BaseModel):
    customer_name: str = ""
    order_code: Optional[str] = None
    status: str = "Open"
    order_date: Optional[str] = None
    order_value: float = 0.0
    channel: str = ""
    notes: str = ""


@api.app.post("/api/business/orders")
def create_order(body: OrderIn, conn: sqlite3.Connection = Depends(api.get_db), user: dict = Depends(api.get_current_user)):
    now = _now()
    code = (body.order_code or "").strip() or ("WEB-" + secrets.token_hex(3).upper())
    odate = body.order_date or date.today().isoformat()
    try:
        cur = conn.execute(
            """INSERT INTO bt_orders(external_order_id,order_date,sales_channel,customer_name,contact,order_status,order_value,updated_by,updated_at,remarks)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (code,odate,body.channel,body.customer_name.strip(),"",body.status,body.order_value,user.get("username",""),now,body.notes),
        )
        conn.commit()
        return {"success":True,"id":cur.lastrowid,"order_code":code}
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=400,detail=f"Create order failed: {exc}") from exc


class MemberIn(BaseModel):
    full_name: str
    status: str = "Active"
    plan_name: str = ""
    service_id: Optional[int] = None
    phone: str = ""
    training_mode: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    sessions_purchased: int = 0
    payment_status: str = "Pending"
    invoice_ref: str = ""
    notes: str = ""


@api.app.post("/api/business/members")
def create_member(body: MemberIn, conn: sqlite3.Connection = Depends(api.get_db), user: dict = Depends(api.get_current_user)):
    service_id=body.service_id
    if service_id is None and body.plan_name.strip():
        found=conn.execute("SELECT id FROM bt_services WHERE name=? COLLATE NOCASE LIMIT 1",(body.plan_name.strip(),)).fetchone()
        service_id=found[0] if found else None
    start=body.start_date or date.today().isoformat()
    try:
        cur=conn.execute(
            """INSERT INTO bt_members(name,contact,service_id,training_mode,registration_date,start_date,expiry_date,
               sessions_purchased,status,payment_status,invoice_ref,remarks) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (body.full_name.strip(),body.phone,service_id,body.training_mode,start,start,body.end_date or "",
             body.sessions_purchased,body.status,body.payment_status,body.invoice_ref,body.notes),
        )
        conn.commit()
        return {"success":True,"id":cur.lastrowid}
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=400,detail=f"Create member failed: {exc}") from exc


class OrderStatusIn(BaseModel):
    status: str


@api.app.patch("/api/business/orders/{order_id}")
def update_order_status(order_id: int, body: OrderStatusIn, conn: sqlite3.Connection = Depends(api.get_db), user: dict = Depends(api.get_current_user)):
    allowed={"Pending","Confirmed","Packed","Dispatched","Delivered","Completed","Cancelled","Returned"}
    if body.status not in allowed:
        raise HTTPException(status_code=400,detail="Invalid order status.")
    cur=conn.execute("UPDATE bt_orders SET order_status=?,updated_by=?,updated_at=? WHERE id=?",
        (body.status,user.get("username",""),_now(),order_id))
    conn.commit()
    if not cur.rowcount: raise HTTPException(status_code=404,detail="Order not found.")
    return {"success":True}


class ActivityIn(BaseModel):
    employee_id: int
    related_order_id: Optional[int] = None
    related_service_id: Optional[int] = None
    task_type: str = ""
    product_id: Optional[int] = None
    quantity: float = 0
    unit: str = ""
    start_time: str = ""
    completion_time: str = ""
    task_status: str = "Pending"
    proof_ref: str = ""
    remarks: str = ""


@api.app.post("/api/business/activities")
def create_business_activity(body: ActivityIn, conn: sqlite3.Connection = Depends(api.get_db), user: dict = Depends(api.get_current_user)):
    if not conn.execute("SELECT 1 FROM employees WHERE id=? AND active=1",(body.employee_id,)).fetchone():
        raise HTTPException(status_code=400,detail="Select an active employee.")
    cur=conn.execute(
        """INSERT INTO bt_activities(employee_id,related_order_id,related_service_id,task_type,product_id,quantity,
           unit,assigned_by,start_time,completion_time,task_status,proof_ref,remarks,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (body.employee_id,body.related_order_id,body.related_service_id,body.task_type,body.product_id,body.quantity,
         body.unit,user.get("username",""),body.start_time,body.completion_time,body.task_status,body.proof_ref,body.remarks,_now()),
    )
    conn.commit()
    return {"success":True,"id":cur.lastrowid}


@api.app.get("/api/customers/prospects")
def list_customer_prospects(
    state: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(api.get_db),
):
    sql = "SELECT * FROM customer_prospects WHERE 1=1"
    params = []
    if state:
        sql += " AND state = ?"
        params.append(state)
    if q:
        term = f"%{q.strip()}%"
        sql += " AND (IFNULL(business_name,'') LIKE ? OR IFNULL(city,'') LIKE ? OR IFNULL(contact_person,'') LIKE ? OR IFNULL(phone,'') LIKE ?)"
        params.extend([term, term, term, term])
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return _rows(conn, sql, tuple(params))


@api.app.get("/api/customers/summary")
def customers_summary(conn: sqlite3.Connection = Depends(api.get_db)):
    return {
        "prospects": _count(conn, "SELECT COUNT(*) FROM customer_prospects"),
        "total": _count(conn, "SELECT COUNT(*) FROM customer_prospects"),
        "states": _rows(conn, "SELECT IFNULL(state,'') AS name, COUNT(*) AS count FROM customer_prospects GROUP BY IFNULL(state,'') ORDER BY count DESC LIMIT 50"),
        "by_state": _rows(conn, "SELECT IFNULL(state,'') AS state, COUNT(*) AS count FROM customer_prospects GROUP BY IFNULL(state,'') ORDER BY count DESC LIMIT 50"),
    }


class ProspectIn(BaseModel):
    business_name: str
    state: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    contact_person: str = ""
    notes: str = ""
    kind: str = "Store"


@api.app.post("/api/customers/prospects")
def create_prospect(body: ProspectIn, conn: sqlite3.Connection = Depends(api.get_db), user: dict = Depends(api.get_current_user)):
    now = _now()
    dedupe = f"web:{body.business_name.strip().lower()}:{body.city.strip().lower()}:{secrets.token_hex(3)}"
    try:
        cur = conn.execute(
            """INSERT INTO customer_prospects(
                   dedupe_key, kind, business_name, state, city, contact_person, phone, email, notes,
                   source_name, source_type, source_status, created_at, updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (dedupe, body.kind, body.business_name.strip(), body.state, body.city, body.contact_person,
             body.phone, body.email, body.notes, "Web App", "Web", "Active", now, now),
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Create prospect failed: {exc}")


@api.app.get("/api/print-center/summary")
def print_center_summary(report_date: Optional[str] = None, conn: sqlite3.Connection = Depends(api.get_db)):
    day = report_date or date.today().isoformat()
    tasks = _rows(
        conn,
        """SELECT t.*, e.name AS employee_name FROM tasks t
           LEFT JOIN employees e ON e.id = t.employee_id
           WHERE t.task_date = ? ORDER BY t.id DESC LIMIT 200""",
        (day,),
    )
    attendance = _rows(
        conn,
        """SELECT e.name, e.department,
                  COALESCE(a.attendance_status,'Unmarked') AS attendance_status,
                  a.check_in, a.check_out
           FROM employees e
           LEFT JOIN attendance a ON a.employee_id = e.id AND a.work_date = ?
           WHERE e.active = 1 ORDER BY e.name""",
        (day,),
    )
    return {
        "report_date": day,
        "employee_count": _count(conn, "SELECT COUNT(*) FROM employees WHERE active=1"),
        "employees": _count(conn, "SELECT COUNT(*) FROM employees WHERE active=1"),
        "tasks_open": _count(conn, "SELECT COUNT(*) FROM tasks WHERE lower(IFNULL(status,'')) NOT IN ('done','completed','closed')"),
        "attendance_today": _count(conn, "SELECT COUNT(*) FROM attendance WHERE work_date = ?", (day,)),
        "orders": _count(conn, "SELECT COUNT(*) FROM bt_orders"),
        "members": _count(conn, "SELECT COUNT(*) FROM bt_members"),
        "tasks": tasks,
        "attendance": attendance,
        "note": "Live web summary from the shared database.",
    }


class AttendanceBulkEditModel(BaseModel):
    work_date: str
    employee_ids: list[int]
    apply_status: bool = False
    status: str = "Present"
    apply_check_in: bool = False
    check_in: str = ""
    apply_check_out: bool = False
    check_out: str = ""
    apply_remarks: bool = False
    remarks: str = ""


@api.app.post("/api/attendance/bulk-edit")
def bulk_edit_attendance(
    body: AttendanceBulkEditModel,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    try:
        work_date = date.fromisoformat(str(body.work_date).strip()).isoformat()
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="work_date must use YYYY-MM-DD format")

    employee_ids = list(dict.fromkeys(int(value) for value in body.employee_ids if int(value) > 0))
    if not employee_ids:
        raise HTTPException(status_code=422, detail="Select at least one employee.")
    if len(employee_ids) > 1000:
        raise HTTPException(status_code=422, detail="Bulk attendance is limited to 1000 employees.")
    if not any((body.apply_status, body.apply_check_in, body.apply_check_out, body.apply_remarks)):
        raise HTTPException(status_code=422, detail="Select at least one field to apply.")

    holiday = conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?", (work_date,)).fetchone()
    if holiday:
        raise HTTPException(status_code=409, detail="This date is declared as a holiday. Remove the holiday declaration before editing attendance.")

    allowed_statuses = {"present": "Present", "absent": "Absent", "leave": "Leave", "unmarked": "Unmarked"}
    selected_status = str(body.status or "").strip()
    if body.apply_status and selected_status.casefold() not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Attendance status must be Present, Absent, Leave or Unmarked.")
    if body.apply_check_in and body.check_in and not api.desktop_app.valid_hhmm(body.check_in):
        raise HTTPException(status_code=422, detail="Check-in must use 24-hour HH:MM format.")
    if body.apply_check_out and body.check_out and not api.desktop_app.valid_hhmm(body.check_out):
        raise HTTPException(status_code=422, detail="Check-out must use 24-hour HH:MM format.")

    now = api.desktop_app.now_text()
    updated = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for employee_id in employee_ids:
            employee = conn.execute(
                "SELECT id FROM employees WHERE id=? AND active=1", (employee_id,)
            ).fetchone()
            if employee is None:
                raise HTTPException(status_code=404, detail=f"Active employee {employee_id} was not found.")

            old = conn.execute(
                "SELECT * FROM attendance WHERE employee_id=? AND work_date=?",
                (employee_id, work_date),
            ).fetchone()
            status = (
                allowed_statuses[selected_status.casefold()]
                if body.apply_status
                else str(old["attendance_status"] or "Unmarked") if old else "Unmarked"
            )
            check_in = (
                str(body.check_in or "").strip()
                if body.apply_check_in
                else str(old["check_in"] or "").strip() if old else ""
            )
            check_out = (
                str(body.check_out or "").strip()
                if body.apply_check_out
                else str(old["check_out"] or "").strip() if old else ""
            )
            remarks = (
                str(body.remarks or "").strip()
                if body.apply_remarks
                else str(old["attendance_note"] or "") if old else ""
            )
            break_minutes = int(old["break_minutes"] or 0) if old else 0

            if status.casefold() in {"absent", "leave", "unmarked"}:
                check_in = check_out = ""
            elif (check_in or check_out) and not api.desktop_app.is_present_attendance_status(status):
                status = "Present"
            if check_out and not check_in:
                raise HTTPException(
                    status_code=422,
                    detail=f"Employee {employee_id}: check-out requires a check-in.",
                )

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
                (employee_id, work_date, status, check_in, check_out, break_minutes, remarks, now),
            )
            updated += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return {"success": True, "updated": updated, "work_date": work_date}


@api.app.get("/api/attendance/summary")
def attendance_summary(
    work_date: Optional[str] = None,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    try:
        selected = date.fromisoformat(str(work_date or date.today().isoformat())).replace()
    except ValueError:
        raise HTTPException(status_code=422, detail="work_date must use YYYY-MM-DD format")

    month_start = selected.replace(day=1)
    end = min(selected, date.today())
    employees = _rows(
        conn,
        "SELECT id, name, joining_date FROM employees WHERE active=1 ORDER BY name COLLATE NOCASE",
    )
    if not employees:
        return {"date": selected.isoformat(), "month_start": month_start.isoformat(), "through_date": end.isoformat(), "rows": []}

    employee_ids = [int(employee["id"]) for employee in employees]
    starts = {}
    missing_join_dates = []
    for employee in employees:
        try:
            starts[int(employee["id"])] = date.fromisoformat(str(employee.get("joining_date") or ""))
        except (TypeError, ValueError):
            missing_join_dates.append(int(employee["id"]))

    if missing_join_dates:
        marks = ",".join("?" for _ in missing_join_dates)
        first_rows = conn.execute(
            f"""SELECT employee_id, MIN(work_day) AS first_day FROM (
                    SELECT employee_id, task_date AS work_day FROM tasks
                    WHERE employee_id IN ({marks}) AND task_date IS NOT NULL AND task_date<>''
                    UNION ALL
                    SELECT employee_id, work_date AS work_day FROM attendance
                    WHERE employee_id IN ({marks}) AND work_date IS NOT NULL AND work_date<>''
                ) GROUP BY employee_id""",
            (*missing_join_dates, *missing_join_dates),
        ).fetchall()
        first_by_employee = {int(row["employee_id"]): row["first_day"] for row in first_rows}
        for employee_id in missing_join_dates:
            try:
                starts[employee_id] = date.fromisoformat(
                    first_by_employee.get(employee_id) or date.today().isoformat()
                )
            except (TypeError, ValueError):
                starts[employee_id] = date.today()

    raw_weekdays = conn.execute(
        "SELECT value FROM settings WHERE key=?", ("working_weekdays",)
    ).fetchone()
    try:
        weekdays = {int(value) for value in str(raw_weekdays["value"] if raw_weekdays else "0,1,2,3,4").split(",") if value.strip()}
        if not weekdays or any(value < 0 or value > 6 for value in weekdays):
            raise ValueError("invalid working weekdays")
    except (TypeError, ValueError):
        weekdays = {0, 1, 2, 3, 4}

    earliest_start = min(starts.values())
    holiday_rows = _rows(
        conn,
        "SELECT holiday_date FROM holidays WHERE holiday_date BETWEEN ? AND ?",
        (earliest_start.isoformat(), end.isoformat()),
    )
    holiday_dates = {str(row["holiday_date"]) for row in holiday_rows}
    marks = ",".join("?" for _ in employee_ids)
    attendance_rows = _rows(
        conn,
        f"""SELECT employee_id, work_date, attendance_status, check_in
            FROM attendance WHERE employee_id IN ({marks}) AND work_date BETWEEN ? AND ?
            ORDER BY employee_id, work_date""",
        (*employee_ids, earliest_start.isoformat(), end.isoformat()),
    )
    attendance_by_employee = {employee_id: [] for employee_id in employee_ids}
    for row in attendance_rows:
        attendance_by_employee[int(row["employee_id"])].append(row)

    summary_rows = []
    for employee in employees:
        employee_id = int(employee["id"])
        start_day = starts[employee_id]
        effective_start = max(start_day, month_start)
        if effective_start <= end:
            working = sum(
                1 for offset in range((end - effective_start).days + 1)
                if (effective_start + __import__("datetime").timedelta(days=offset)).weekday() in weekdays
                and (effective_start + __import__("datetime").timedelta(days=offset)).isoformat() not in holiday_dates
            )
            monthly_rows = []
            for row in attendance_by_employee[employee_id]:
                try:
                    row_day = date.fromisoformat(str(row["work_date"]))
                except (TypeError, ValueError):
                    continue
                if effective_start <= row_day <= end and row_day.isoformat() not in holiday_dates and row_day.weekday() in weekdays:
                    monthly_rows.append(row)
            holiday_count = sum(
                1 for holiday in holiday_dates
                if effective_start.isoformat() <= holiday <= end.isoformat()
                and date.fromisoformat(holiday).weekday() in weekdays
            )
        else:
            working = 0
            monthly_rows = []
            holiday_count = 0

        def is_present(row):
            status = str(row.get("attendance_status") or "").strip()
            return api.desktop_app.is_present_attendance_status(status) or (
                status.casefold() in {"unmarked", ""}
                and bool(str(row.get("check_in") or "").strip())
            )

        present = sum(1 for row in monthly_rows if is_present(row))
        absent = sum(1 for row in monthly_rows if str(row.get("attendance_status") or "").strip().casefold() == "absent")
        leave = sum(1 for row in monthly_rows if str(row.get("attendance_status") or "").strip().casefold() == "leave")
        total_present = 0
        for row in attendance_by_employee[employee_id]:
            try:
                row_day = date.fromisoformat(str(row["work_date"]))
            except (TypeError, ValueError):
                continue
            if start_day <= row_day <= end and row_day.isoformat() not in holiday_dates and row_day.weekday() in weekdays and is_present(row):
                total_present += 1

        summary_rows.append({
            "employee_id": employee_id,
            "employee_name": employee["name"],
            "start_date": start_day.isoformat(),
            "work_days": working,
            "present": present,
            "absent": absent,
            "leave": leave,
            "holidays": holiday_count,
            "total_present": total_present,
        })

    return {
        "date": selected.isoformat(),
        "month_start": month_start.isoformat(),
        "through_date": end.isoformat(),
        "rows": summary_rows,
    }
