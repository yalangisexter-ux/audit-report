"""Extra operational read APIs for web parity (business, prospects, print summary)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import Depends, Query
import sqlite3

import api_server as api


def _rows(conn, sql, params=()):
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:
        return []


def _count(conn, sql, params=()):
    try:
        return int(conn.execute(sql, params).fetchone()[0] or 0)
    except Exception:
        return 0


@api.app.get("/api/business/orders")
def list_business_orders(conn: sqlite3.Connection = Depends(api.get_db)):
    return _rows(conn, """SELECT * FROM bt_orders ORDER BY id DESC LIMIT 300""")


@api.app.get("/api/business/members")
def list_business_members(conn: sqlite3.Connection = Depends(api.get_db)):
    return _rows(conn, """SELECT * FROM bt_members ORDER BY id DESC LIMIT 300""")


@api.app.get("/api/business/activities")
def list_business_activities(conn: sqlite3.Connection = Depends(api.get_db)):
    return _rows(conn, """SELECT * FROM bt_activities ORDER BY id DESC LIMIT 300""")


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
            """SELECT COUNT(*) FROM bt_orders
               WHERE lower(IFNULL(status,'')) NOT IN ('completed','cancelled','delivered','closed')""",
        ),
        "active_members": _count(
            conn,
            """SELECT COUNT(*) FROM bt_members
               WHERE lower(IFNULL(status,'')) IN ('active','current','ongoing')
                  OR IFNULL(status,'') = ''""",
        ),
    }


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
        sql += """ AND (
            IFNULL(business_name,'') LIKE ?
            OR IFNULL(city,'') LIKE ?
            OR IFNULL(phone,'') LIKE ?
            OR IFNULL(email,'') LIKE ?
            OR IFNULL(address,'') LIKE ?
        )"""
        params.extend([term, term, term, term, term])
    sql += " ORDER BY state COLLATE NOCASE, city COLLATE NOCASE, business_name COLLATE NOCASE LIMIT ?"
    params.append(limit)
    return _rows(conn, sql, tuple(params))


@api.app.get("/api/customers/summary")
def customer_directory_summary(conn: sqlite3.Connection = Depends(api.get_db)):
    total = _count(conn, "SELECT COUNT(*) FROM customer_prospects")
    states = _rows(
        conn,
        """SELECT state AS name, COUNT(*) AS count
           FROM customer_prospects
           GROUP BY state
           ORDER BY count DESC, state COLLATE NOCASE
           LIMIT 40""",
    )
    return {"total": total, "states": states}


@api.app.get("/api/print-center/summary")
def print_center_summary(
    report_date: Optional[str] = None,
    conn: sqlite3.Connection = Depends(api.get_db),
):
    d = report_date or date.today().isoformat()
    tasks = _rows(
        conn,
        """SELECT t.id, t.title, t.status, t.priority, t.task_date, e.name AS employee_name
           FROM tasks t LEFT JOIN employees e ON e.id = t.employee_id
           WHERE t.task_date = ?
           ORDER BY e.name COLLATE NOCASE, t.id DESC
           LIMIT 100""",
        (d,),
    )
    if not tasks:
        tasks = _rows(
            conn,
            """SELECT t.id, t.title, t.status, t.priority, t.task_date, e.name AS employee_name
               FROM tasks t LEFT JOIN employees e ON e.id = t.employee_id
               ORDER BY t.task_date DESC, t.id DESC
               LIMIT 40""",
        )
    attendance = _rows(
        conn,
        """SELECT e.name, e.department, a.attendance_status, a.check_in, a.check_out
           FROM employees e
           LEFT JOIN attendance a ON a.employee_id = e.id AND a.work_date = ?
           WHERE e.active = 1
           ORDER BY e.name COLLATE NOCASE
           LIMIT 100""",
        (d,),
    )
    return {
        "report_date": d,
        "employee_count": _count(conn, "SELECT COUNT(*) FROM employees"),
        "task_count_for_date": len(tasks),
        "tasks": tasks,
        "attendance": attendance,
        "note": "Web Print Center shows a live summary. Full PDF export/print remains in the desktop EXE.",
    }
