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
