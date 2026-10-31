"""Extra operational read APIs for web parity (business, prospects, print summary)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import Depends, Query
import sqlite3

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
            OR IFNULL(contact_name,'') LIKE ?
            OR IFNULL(phone,'') LIKE ?
        )"""
        params.extend([term, term, term, term])
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return _rows(conn, sql, tuple(params))


@api.app.get("/api/customers/summary")
def customers_summary(conn: sqlite3.Connection = Depends(api.get_db)):
    return {
        "prospects": _count(conn, "SELECT COUNT(*) FROM customer_prospects"),
        "by_state": _rows(
            conn,
            """SELECT IFNULL(state,'') AS state, COUNT(*) AS count
               FROM customer_prospects GROUP BY IFNULL(state,'')
               ORDER BY count DESC LIMIT 50""",
        ),
    }


@api.app.get("/api/print-center/summary")
def print_center_summary(conn: sqlite3.Connection = Depends(api.get_db)):
    today = date.today().isoformat()
    return {
        "employees": _count(conn, "SELECT COUNT(*) FROM employees WHERE active=1"),
        "tasks_open": _count(
            conn,
            """SELECT COUNT(*) FROM tasks
               WHERE lower(IFNULL(status,'')) NOT IN ('done','completed','closed')""",
        ),
        "attendance_today": _count(
            conn,
            "SELECT COUNT(*) FROM attendance WHERE date = ?",
            (today,),
        ),
        "orders": _count(conn, "SELECT COUNT(*) FROM bt_orders"),
        "members": _count(conn, "SELECT COUNT(*) FROM bt_members"),
    }
