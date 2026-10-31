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
    return _rows(conn, "SELECT * FROM bt_orders ORDER BY id DESC LIMIT 300")


@api.app.get("/api/business/members")
def list_business_members(conn: sqlite3.Connection = Depends(api.get_db)):
    return _rows(conn, "SELECT * FROM bt_members ORDER BY id DESC LIMIT 300")


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
            "INSERT INTO bt_orders(order_code, customer_name, status, order_date, order_value, channel, notes, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (code, body.customer_name, body.status, odate, body.order_value, body.channel, body.notes, now, now),
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid, "order_code": code}
    except Exception:
        try:
            cur = conn.execute(
                "INSERT INTO bt_orders(customer_name, status, order_date, order_value) VALUES(?,?,?,?)",
                (body.customer_name, body.status, odate, body.order_value),
            )
            conn.commit()
            return {"success": True, "id": cur.lastrowid}
        except Exception as exc2:
            raise HTTPException(status_code=400, detail=f"Create order failed: {exc2}")


class MemberIn(BaseModel):
    full_name: str
    status: str = "Active"
    plan_name: str = ""
    phone: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: str = ""


@api.app.post("/api/business/members")
def create_member(body: MemberIn, conn: sqlite3.Connection = Depends(api.get_db), user: dict = Depends(api.get_current_user)):
    now = _now()
    try:
        cur = conn.execute(
            "INSERT INTO bt_members(full_name, name, status, plan_name, phone, start_date, end_date, notes, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (body.full_name, body.full_name, body.status, body.plan_name, body.phone, body.start_date or date.today().isoformat(), body.end_date or "", body.notes, now, now),
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid}
    except Exception:
        try:
            cur = conn.execute(
                "INSERT INTO bt_members(full_name, status, plan_name, phone) VALUES(?,?,?,?)",
                (body.full_name, body.status, body.plan_name, body.phone),
            )
            conn.commit()
            return {"success": True, "id": cur.lastrowid}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Create member failed: {exc}")


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
