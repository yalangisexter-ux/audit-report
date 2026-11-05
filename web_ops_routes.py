"""Operational APIs for web parity — EXE untouched."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
import sqlite3
import secrets
import math
from types import SimpleNamespace

import customer_prospects as prospect_store
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


def _read_working_weekdays(conn):
    return sorted(api.desktop_app.working_weekdays_from_connection(conn))


@api.app.get("/api/business/orders")
def list_business_orders(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    return _rows(conn, "SELECT id,external_order_id AS order_code,order_date,sales_channel AS channel,customer_name,contact,payment_mode,order_status AS status,discount,order_value,invoice_number,shipment_id,assigned_employee_id,updated_by,updated_at,remarks FROM bt_orders ORDER BY id DESC LIMIT 300")


@api.app.get("/api/business/members")
def list_business_members(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    return _rows(conn, """SELECT m.id,m.name AS full_name,m.contact AS phone,m.service_id,s.name AS plan_name,m.training_mode,m.registration_date,m.start_date,m.expiry_date AS end_date,m.sessions_purchased,m.sessions_completed,m.assigned_trainer_id,m.status,m.payment_status,m.invoice_ref,m.remarks FROM bt_members m LEFT JOIN bt_services s ON s.id=m.service_id ORDER BY m.id DESC LIMIT 300""")


@api.app.get("/api/business/activities")
def list_business_activities(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    return _rows(conn, """SELECT a.*,e.name AS employee_name,o.external_order_id AS order_code,
        s.name AS service_name,p.name AS product_name
        FROM bt_activities a
        LEFT JOIN employees e ON e.id=a.employee_id
        LEFT JOIN bt_orders o ON o.id=a.related_order_id
        LEFT JOIN bt_services s ON s.id=a.related_service_id
        LEFT JOIN bt_products p ON p.id=a.product_id
        ORDER BY a.id DESC LIMIT 300""")


@api.app.get("/api/business/overview")
def business_overview(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    return {
        "products": _count(conn, "SELECT COUNT(*) FROM bt_products"),
        "low_stock": _count(conn, """SELECT COUNT(*) FROM bt_products WHERE
            (COALESCE(opening_stock,0)+COALESCE(received_qty,0)-COALESCE(reserved_qty,0)
             -COALESCE(dispatched_qty,0)-COALESCE(free_qty,0)-COALESCE(damaged_qty,0)
             -COALESCE(expired_qty,0)-COALESCE(quarantined_qty,0)+COALESCE(returned_qty,0))
            <= COALESCE(reorder_level,0)"""),
        "orders": _count(conn, "SELECT COUNT(*) FROM bt_orders"),
        "services": _count(conn, "SELECT COUNT(*) FROM bt_services"),
        "members": _count(conn, "SELECT COUNT(*) FROM bt_members"),
        "activities": _count(conn, "SELECT COUNT(*) FROM bt_activities"),
        "open_orders": _count(
            conn,
            "SELECT COUNT(*) FROM bt_orders WHERE lower(IFNULL(order_status,'')) NOT IN ('completed','cancelled','delivered','closed','returned')",
        ),
        "active_members": _count(
            conn,
            "SELECT COUNT(*) FROM bt_members WHERE lower(IFNULL(status,'')) IN ('active','current','ongoing') OR IFNULL(status,'') = ''",
        ),
        "completed_activities": _count(
            conn, "SELECT COUNT(*) FROM bt_activities WHERE lower(IFNULL(task_status,''))='completed'"
        ),
    }


class OrderIn(BaseModel):
    customer_name: str = ""
    order_code: Optional[str] = None
    status: str = "Pending"
    order_date: Optional[str] = None
    order_value: float = 0.0
    channel: str = ""
    contact: str = ""
    payment_mode: str = ""
    discount: float = 0.0
    invoice_number: str = ""
    shipment_id: str = ""
    assigned_employee_id: Optional[int] = None
    notes: str = ""


@api.app.post("/api/business/orders")
def create_order(
    body: OrderIn,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    now = _now()
    code = (body.order_code or "").strip() or ("WEB-" + secrets.token_hex(3).upper())
    try:
        odate = date.fromisoformat(str(body.order_date or date.today().isoformat())).isoformat()
    except ValueError:
        raise HTTPException(status_code=422, detail="Order date must use YYYY-MM-DD.")
    if body.status not in {"Pending", "Confirmed", "Packed", "Dispatched", "Delivered", "Completed", "Cancelled", "Returned"}:
        raise HTTPException(status_code=422, detail="Invalid order status.")
    if not math.isfinite(float(body.order_value)) or body.order_value < 0:
        raise HTTPException(status_code=422, detail="Order value must be a finite non-negative number.")
    if not math.isfinite(float(body.discount)) or body.discount < 0:
        raise HTTPException(status_code=422, detail="Discount must be a finite non-negative number.")
    if body.assigned_employee_id is not None and not conn.execute(
        "SELECT 1 FROM employees WHERE id=? AND active=1", (body.assigned_employee_id,)
    ).fetchone():
        raise HTTPException(status_code=400, detail="Assigned employee was not found or is inactive.")
    try:
        cur = conn.execute(
            """INSERT INTO bt_orders(
                external_order_id,order_date,sales_channel,customer_name,contact,payment_mode,
                order_status,discount,order_value,invoice_number,shipment_id,assigned_employee_id,
                updated_by,updated_at,remarks
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                code, odate, body.channel, body.customer_name.strip(), body.contact,
                body.payment_mode, body.status, body.discount, body.order_value,
                body.invoice_number, body.shipment_id, body.assigned_employee_id,
                user.get("username", ""), now, body.notes,
            ),
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid, "order_code": code}
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Create order failed: {exc}") from exc


class MemberIn(BaseModel):
    full_name: str
    status: str = "Active"
    plan_name: str = ""
    service_id: Optional[int] = None
    phone: str = ""
    training_mode: str = ""
    registration_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    sessions_purchased: int = 0
    sessions_completed: int = 0
    assigned_trainer_id: Optional[int] = None
    payment_status: str = "Pending"
    invoice_ref: str = ""
    notes: str = ""


@api.app.post("/api/business/members")
def create_member(
    body: MemberIn,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    if not body.full_name.strip():
        raise HTTPException(status_code=422, detail="Member name is required.")
    if body.sessions_purchased < 0 or body.sessions_completed < 0:
        raise HTTPException(status_code=422, detail="Session counts cannot be negative.")
    service_id = body.service_id
    if service_id is None and body.plan_name.strip():
        found = conn.execute(
            "SELECT id FROM bt_services WHERE name=? COLLATE NOCASE LIMIT 1",
            (body.plan_name.strip(),),
        ).fetchone()
        service_id = found[0] if found else None
    if service_id is not None and not conn.execute(
        "SELECT 1 FROM bt_services WHERE id=?", (service_id,)
    ).fetchone():
        raise HTTPException(status_code=400, detail="Selected service was not found.")
    if body.assigned_trainer_id is not None and not conn.execute(
        "SELECT 1 FROM employees WHERE id=? AND active=1", (body.assigned_trainer_id,)
    ).fetchone():
        raise HTTPException(status_code=400, detail="Assigned trainer was not found or is inactive.")
    registration = body.registration_date or body.start_date or date.today().isoformat()
    start = body.start_date or registration
    try:
        registration = date.fromisoformat(str(registration)).isoformat()
        start = date.fromisoformat(str(start)).isoformat()
        expiry = date.fromisoformat(str(body.end_date)).isoformat() if body.end_date else ""
    except ValueError:
        raise HTTPException(status_code=422, detail="Membership dates must use YYYY-MM-DD.")
    if body.status not in {"Active", "Expired", "Inactive", "Cancelled", "Suspended"}:
        raise HTTPException(status_code=422, detail="Invalid membership status.")
    if body.payment_status not in {"Pending", "Paid", "Partial", "Overdue", "Refunded"}:
        raise HTTPException(status_code=422, detail="Invalid payment status.")
    try:
        cur = conn.execute(
            """INSERT INTO bt_members(
                name,contact,service_id,training_mode,registration_date,start_date,expiry_date,
                sessions_purchased,sessions_completed,assigned_trainer_id,status,payment_status,
                invoice_ref,remarks
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                body.full_name.strip(), body.phone, service_id, body.training_mode, registration,
                start, expiry, body.sessions_purchased, body.sessions_completed,
                body.assigned_trainer_id, body.status, body.payment_status,
                body.invoice_ref, body.notes,
            ),
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid}
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Create member failed: {exc}") from exc


class MemberUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    sessions_purchased: Optional[int] = None
    sessions_completed: Optional[int] = None
    end_date: Optional[str] = None
    invoice_ref: Optional[str] = None
    notes: Optional[str] = None


@api.app.patch("/api/business/members/{member_id}")
def update_business_member(
    member_id: int,
    body: MemberUpdate,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    allowed = {
        "status": "status", "payment_status": "payment_status",
        "sessions_purchased": "sessions_purchased", "sessions_completed": "sessions_completed",
        "end_date": "expiry_date", "invoice_ref": "invoice_ref", "notes": "remarks",
    }
    values = body.dict(exclude_unset=True)
    if not values:
        raise HTTPException(status_code=422, detail="No membership changes were supplied.")
    if "status" in values and values["status"] not in {"Active", "Expired", "Inactive", "Cancelled", "Suspended"}:
        raise HTTPException(status_code=422, detail="Invalid membership status.")
    if "payment_status" in values and values["payment_status"] not in {"Pending", "Paid", "Partial", "Overdue", "Refunded"}:
        raise HTTPException(status_code=422, detail="Invalid payment status.")
    for key in ("sessions_purchased", "sessions_completed"):
        if key in values and (values[key] is None or int(values[key]) < 0):
            raise HTTPException(status_code=422, detail="Session counts cannot be negative.")
    if "end_date" in values and values["end_date"]:
        try:
            values["end_date"] = date.fromisoformat(str(values["end_date"])).isoformat()
        except ValueError:
            raise HTTPException(status_code=422, detail="End date must use YYYY-MM-DD.")
    assignments = [f"{allowed[key]}=?" for key in values]
    params = [values[key] for key in values]
    cur = conn.execute(
        "UPDATE bt_members SET " + ",".join(assignments) + " WHERE id=?",
        (*params, member_id),
    )
    conn.commit()
    if not cur.rowcount:
        raise HTTPException(status_code=404, detail="Member not found.")
    return {"success": True}


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


_ACTIVITY_STATUSES = {"Pending", "In Progress", "Completed", "Blocked", "Cancelled"}


@api.app.post("/api/business/activities")
def create_business_activity(
    body: ActivityIn,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    if not conn.execute("SELECT 1 FROM employees WHERE id=? AND active=1", (body.employee_id,)).fetchone():
        raise HTTPException(status_code=400, detail="Select an active employee.")
    if not math.isfinite(float(body.quantity)) or body.quantity < 0:
        raise HTTPException(status_code=422, detail="Activity quantity must be a finite non-negative number.")
    if body.task_status not in _ACTIVITY_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid activity status.")
    for table, value, label in (
        ("bt_orders", body.related_order_id, "order"),
        ("bt_services", body.related_service_id, "service"),
        ("bt_products", body.product_id, "product"),
    ):
        if value is not None and not conn.execute(f"SELECT 1 FROM {table} WHERE id=?", (value,)).fetchone():
            raise HTTPException(status_code=400, detail=f"Selected {label} was not found.")
    cur = conn.execute(
        """INSERT INTO bt_activities(
            employee_id,related_order_id,related_service_id,task_type,product_id,quantity,
            unit,assigned_by,start_time,completion_time,task_status,proof_ref,remarks,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            body.employee_id, body.related_order_id, body.related_service_id, body.task_type,
            body.product_id, body.quantity, body.unit, user.get("username", ""),
            body.start_time, body.completion_time, body.task_status, body.proof_ref,
            body.remarks, _now(),
        ),
    )
    conn.commit()
    return {"success": True, "id": cur.lastrowid}


class ActivityUpdate(BaseModel):
    task_status: Optional[str] = None
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    verified_by: Optional[str] = None
    proof_ref: Optional[str] = None
    remarks: Optional[str] = None


@api.app.patch("/api/business/activities/{activity_id}")
def update_business_activity(
    activity_id: int,
    body: ActivityUpdate,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    values = body.dict(exclude_unset=True)
    if not values:
        raise HTTPException(status_code=422, detail="No activity changes were supplied.")
    if "task_status" in values and values["task_status"] not in _ACTIVITY_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid activity status.")
    current = conn.execute("SELECT task_status,start_time,completion_time FROM bt_activities WHERE id=?", (activity_id,)).fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="Activity not found.")
    if values.get("task_status") == "In Progress" and not values.get("start_time", current["start_time"]):
        values["start_time"] = _now()
    if values.get("task_status") == "Completed" and not values.get("completion_time", current["completion_time"]):
        values["completion_time"] = _now()
    allowed = {"task_status", "start_time", "completion_time", "verified_by", "proof_ref", "remarks"}
    assignments = [f"{key}=?" for key in values if key in allowed]
    params = [values[key] for key in values if key in allowed]
    cur = conn.execute(
        "UPDATE bt_activities SET " + ",".join(assignments) + " WHERE id=?",
        (*params, activity_id),
    )
    conn.commit()
    if not cur.rowcount:
        raise HTTPException(status_code=404, detail="Activity not found.")
    return {"success": True}


class StockMovementIn(BaseModel):
    product_id: int
    txn_type: str
    quantity: float
    unit: str = ""
    reference: str = ""
    notes: str = ""


_STOCK_MOVEMENTS = {
    "receive": ("received_qty", 1, False),
    "reserve": ("reserved_qty", 1, True),
    "release": ("reserved_qty", -1, False),
    "dispatch": ("dispatched_qty", 1, True),
    "free": ("free_qty", 1, True),
    "return": ("returned_qty", 1, False),
    "damage": ("damaged_qty", 1, True),
    "expire": ("expired_qty", 1, True),
    "quarantine": ("quarantined_qty", 1, True),
    "unquarantine": ("quarantined_qty", -1, False),
}


@api.app.get("/api/business/stock-ledger")
def list_business_stock_ledger(
    product_id: Optional[int] = None,
    limit: int = Query(300, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    sql = """SELECT l.*,p.name AS product_name,p.sku FROM bt_stock_ledger l
             LEFT JOIN bt_products p ON p.id=l.product_id"""
    params = []
    if product_id is not None:
        sql += " WHERE l.product_id=?"
        params.append(product_id)
    sql += " ORDER BY l.id DESC LIMIT ?"
    params.append(limit)
    return _rows(conn, sql, tuple(params))


@api.app.post("/api/business/stock-ledger")
def create_business_stock_movement(
    body: StockMovementIn,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    movement = str(body.txn_type or "").strip().casefold()
    if movement not in _STOCK_MOVEMENTS:
        raise HTTPException(status_code=422, detail="Unsupported stock movement type.")
    quantity = float(body.quantity)
    if not math.isfinite(quantity) or quantity <= 0:
        raise HTTPException(status_code=422, detail="Movement quantity must be a finite positive number.")
    field, direction, consumes_available = _STOCK_MOVEMENTS[movement]
    try:
        conn.execute("BEGIN IMMEDIATE")
        product = conn.execute("SELECT * FROM bt_products WHERE id=?", (body.product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")
        if consumes_available:
            from business_tracking import available_stock
            if quantity > max(0.0, available_stock(product)):
                raise HTTPException(status_code=409, detail="Movement exceeds available stock.")
        if direction < 0 and quantity > float(product[field] or 0):
            raise HTTPException(status_code=409, detail="Movement exceeds the quantity currently held in that stock state.")
        conn.execute(
            f"UPDATE bt_products SET {field}=COALESCE({field},0)+?,updated_by=?,updated_at=? WHERE id=?",
            (quantity * direction, user.get("username", ""), _now(), body.product_id),
        )
        cur = conn.execute(
            """INSERT INTO bt_stock_ledger(
                product_id,txn_type,quantity,unit,reference,notes,created_by,created_at
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (
                body.product_id, movement, quantity, body.unit, body.reference,
                body.notes, user.get("username", ""), _now(),
            ),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM bt_products WHERE id=?", (body.product_id,)).fetchone()
        from business_tracking import available_stock
        return {"success": True, "id": cur.lastrowid, "available_stock": available_stock(updated)}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Stock movement failed: {exc}") from exc


@api.app.get("/api/customers/prospects")
def list_customer_prospects(
    state: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    sql = "SELECT * FROM customer_prospects WHERE 1=1"
    params = []
    if state:
        sql += " AND state = ?"
        params.append(state)
    if q:
        term = f"%{q.strip()}%"
        search_fields = (
            "business_name", "business_category", "kind", "area", "city", "state",
            "contact_person", "phone", "email", "address", "website", "maps",
            "followup_date", "connection", "verified", "response", "source_status",
        )
        sql += " AND (" + " OR ".join(
            f"IFNULL({field},'') LIKE ?" for field in search_fields
        ) + ")"
        params.extend([term] * len(search_fields))
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return _rows(conn, sql, tuple(params))


@api.app.get("/api/customers/summary")
def customers_summary(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    return {
        "prospects": _count(conn, "SELECT COUNT(*) FROM customer_prospects"),
        "total": _count(conn, "SELECT COUNT(*) FROM customer_prospects"),
        "states": _rows(conn, "SELECT IFNULL(state,'') AS name, COUNT(*) AS count FROM customer_prospects GROUP BY IFNULL(state,'') ORDER BY count DESC LIMIT 50"),
        "by_state": _rows(conn, "SELECT IFNULL(state,'') AS state, COUNT(*) AS count FROM customer_prospects GROUP BY IFNULL(state,'') ORDER BY count DESC LIMIT 50"),
    }


class ProspectIn(BaseModel):
    business_name: str
    business_category: str = ""
    kind: str = "Store"
    state: str = ""
    city: str = ""
    area: str = ""
    contact_person: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    website: str = ""
    maps: str = ""
    followup_date: str = ""
    call_time: str = ""
    connection: str = ""
    verified: str = ""
    response: str = ""
    notes: str = ""


@api.app.post("/api/customers/prospects")
def create_prospect(
    body: ProspectIn,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    record = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    record["business_name"] = str(record.get("business_name") or "").strip()
    record["state"] = str(record.get("state") or "").strip()
    record["city"] = str(record.get("city") or "").strip()
    if not record["business_name"]:
        raise HTTPException(status_code=422, detail="Business / store name is required.")
    if not record["state"] or not record["city"]:
        raise HTTPException(status_code=422, detail="City and state are required to identify a unique store branch.")

    record["kind"] = str(record.get("kind") or "Store").strip()
    record["source_name"] = "Web App"
    record["source_type"] = "Web"
    record["source_url"] = str(record.get("website") or "").strip()
    try:
        result = prospect_store.persist_prospect_records(
            SimpleNamespace(conn=conn),
            [record],
            source_name="Web App",
            source_checked_at=date.today().isoformat(),
        )
        if not result.get("inserted") and not result.get("duplicates"):
            raise HTTPException(
                status_code=422,
                detail="This record did not pass the Store Directory quality filters.",
            )
        dedupe_key = prospect_store.prospect_dedupe_key(record)
        saved = conn.execute(
            "SELECT id FROM customer_prospects WHERE dedupe_key=?",
            (dedupe_key,),
        ).fetchone()
        if not saved:
            raise HTTPException(status_code=500, detail="Saved prospect could not be resolved after deduplication.")
        saved_id = int(saved["id"] if isinstance(saved, sqlite3.Row) else saved[0])
        return {
            "success": True,
            "id": saved_id,
            "inserted": int(result.get("inserted", 0)),
            "duplicates": int(result.get("duplicates", 0)),
            "duplicate": bool(result.get("duplicates", 0)),
        }
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Create prospect failed: {exc}") from exc


@api.app.get("/api/print-center/summary")
def print_center_summary(report_date: Optional[str] = None, conn: sqlite3.Connection = Depends(api.get_db), user: dict = Depends(api.get_current_user)):
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


class WorkingWeekdaysModel(BaseModel):
    weekdays: list[int]


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


@api.app.get("/api/settings/working-weekdays")
def get_working_weekdays(
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    api._require_employee_roles(user, {"admin", "developer"})
    return {"weekdays": _read_working_weekdays(conn), "sunday_required": True}


@api.app.put("/api/settings/working-weekdays")
def save_working_weekdays(
    body: WorkingWeekdaysModel,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    api._require_employee_roles(user, {"admin", "developer"})
    if not body.weekdays or any(value < 0 or value > 6 for value in body.weekdays):
        raise HTTPException(status_code=422, detail="Choose valid weekdays from Monday through Sunday.")
    weekdays = sorted(set(body.weekdays) | {6})
    serialized = ",".join(str(value) for value in weekdays)
    conn.execute(
        "INSERT INTO settings(key, value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        ("working_weekdays", serialized),
    )
    api._record_account_audit(conn, "Working week changed", serialized)
    conn.commit()
    return {"success": True, "weekdays": weekdays, "sunday_required": True}


@api.app.get("/api/attendance/summary")
def attendance_summary(
    work_date: Optional[str] = None,
    conn: sqlite3.Connection = Depends(api.get_db),
    user: dict = Depends(api.get_current_user),
):
    try:
        selected = date.fromisoformat(str(work_date or date.today().isoformat()))
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

    weekdays = set(_read_working_weekdays(conn))

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
                if (effective_start + timedelta(days=offset)).weekday() in weekdays
                and (effective_start + timedelta(days=offset)).isoformat() not in holiday_dates
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
