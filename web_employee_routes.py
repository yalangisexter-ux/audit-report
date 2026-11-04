"""Authenticated employee directory parity routes."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import sqlite3
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
import api_server as api

class EmployeeGroupPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)

class EmployeeGroupRenamePayload(BaseModel):
    old_name: str = Field(min_length=1, max_length=80)
    new_name: str = Field(min_length=1, max_length=80)

class EmployeeGroupOrderPayload(BaseModel):
    group_names: List[str] = Field(default_factory=list)

class EmployeeOrderItem(BaseModel):
    id: int
    display_order: int
    department: Optional[str] = None

class EmployeeOrderPayload(BaseModel):
    items: List[EmployeeOrderItem] = Field(default_factory=list)

class EmployeeStatusPayload(BaseModel):
    active: bool

def _require_roles(user, allowed_roles):
    role = str((user or {}).get("role", "")).strip().casefold()
    allowed = {str(value).strip().casefold() for value in allowed_roles}
    if role not in allowed:
        raise HTTPException(status_code=403, detail="You do not have permission to perform this employee directory action.")

def _group_rows(conn):
    groups = conn.execute("SELECT id, name, display_order FROM employee_groups ORDER BY display_order ASC, name COLLATE NOCASE").fetchall()
    counts = conn.execute(
        """SELECT TRIM(department) AS group_name, COUNT(*) AS employee_count
           FROM employees WHERE department IS NOT NULL AND TRIM(department) <> ''
           GROUP BY TRIM(department)"""
    ).fetchall()
    count_map = {str(row["group_name"] or "").strip().casefold(): int(row["employee_count"] or 0) for row in counts}
    result = {}
    for row in groups:
        name = str(row["name"] or "").strip()
        if name:
            result[name.casefold()] = {"id": row["id"], "name": name, "display_order": int(row["display_order"] or 0), "employee_count": count_map.get(name.casefold(), 0)}
    for row in counts:
        name = str(row["group_name"] or "").strip()
        if name and name.casefold() not in result:
            result[name.casefold()] = {"id": None, "name": name, "display_order": 9999, "employee_count": int(row["employee_count"] or 0)}
    return sorted(result.values(), key=lambda item: (item["display_order"], item["name"].casefold()))

@api.app.get("/api/employee-groups")
def list_employee_groups(conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    return _group_rows(conn)

@api.app.post("/api/employee-groups")
def create_employee_group(payload: EmployeeGroupPayload, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _require_roles(user, {"Admin", "Developer"})
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Section name is required.")
    if any(item["name"].casefold() == name.casefold() for item in _group_rows(conn)):
        raise HTTPException(status_code=409, detail="A section with this name already exists.")
    maximum = conn.execute("SELECT COALESCE(MAX(display_order), 0) AS value FROM employee_groups").fetchone()
    next_order = int((maximum["value"] if maximum else 0) or 0) + 10
    conn.execute("INSERT INTO employee_groups(name, display_order, created_at) VALUES(?,?,?)", (name, next_order, api.desktop_app.now_text()))
    conn.commit()
    return {"success": True, "group": next((item for item in _group_rows(conn) if item["name"].casefold() == name.casefold()), None)}

@api.app.patch("/api/employee-groups")
def rename_employee_group(payload: EmployeeGroupRenamePayload, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _require_roles(user, {"Admin", "Developer"})
    old_name, new_name = payload.old_name.strip(), payload.new_name.strip()
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="Both section names are required.")
    current = next((item for item in _group_rows(conn) if item["name"].casefold() == old_name.casefold()), None)
    if not current:
        raise HTTPException(status_code=404, detail="Section not found.")
    collision = next((item for item in _group_rows(conn) if item["name"].casefold() == new_name.casefold() and item["name"].casefold() != old_name.casefold()), None)
    if collision:
        raise HTTPException(status_code=409, detail="A section with the new name already exists.")
    if old_name.casefold() == new_name.casefold():
        return {"success": True, "name": current["name"]}
    try:
        stored = conn.execute("SELECT display_order FROM employee_groups WHERE name=? COLLATE NOCASE", (old_name,)).fetchone()
        if stored:
            conn.execute("UPDATE employee_groups SET name=? WHERE name=? COLLATE NOCASE", (new_name, old_name))
        else:
            conn.execute("INSERT INTO employee_groups(name, display_order, created_at) VALUES(?,?,?)", (new_name, current["display_order"], api.desktop_app.now_text()))
        conn.execute("UPDATE employees SET department=? WHERE department=? COLLATE NOCASE", (new_name, old_name))
        conn.execute("UPDATE tasks SET department=? WHERE department=? COLLATE NOCASE", (new_name, old_name))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="A section with the new name already exists.")
    return {"success": True, "name": new_name}

@api.app.delete("/api/employee-groups")
def delete_employee_group(payload: EmployeeGroupPayload, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _require_roles(user, {"Admin", "Developer"})
    name = payload.name.strip()
    current = next((item for item in _group_rows(conn) if item["name"].casefold() == name.casefold()), None)
    if not current:
        raise HTTPException(status_code=404, detail="Section not found.")
    conn.execute("DELETE FROM employee_groups WHERE name=? COLLATE NOCASE", (name,))
    conn.execute("UPDATE employees SET department='' WHERE department=? COLLATE NOCASE", (name,))
    conn.commit()
    return {"success": True}

@api.app.put("/api/employee-groups/order")
def reorder_employee_groups(payload: EmployeeGroupOrderPayload, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _require_roles(user, {"Admin", "Developer"})
    names = [str(name or "").strip() for name in payload.group_names]
    folded = [name.casefold() for name in names]
    if any(not name for name in names) or len(folded) != len(set(folded)):
        raise HTTPException(status_code=400, detail="Section names must be non-empty and unique.")
    available = {item["name"].casefold() for item in _group_rows(conn)}
    if any(name.casefold() not in available for name in names):
        raise HTTPException(status_code=404, detail="One or more sections no longer exist.")
    try:
        for index, name in enumerate(names):
            conn.execute(
                """INSERT INTO employee_groups(name, display_order, created_at) VALUES(?,?,?)
                   ON CONFLICT(name) DO UPDATE SET display_order=excluded.display_order""",
                (name, (index + 1) * 10, api.desktop_app.now_text()),
            )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Section order could not be saved.")
    return {"success": True, "updated": len(names)}

@api.app.put("/api/employee-directory/reorder")
def reorder_employee_directory(payload: EmployeeOrderPayload, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _require_roles(user, {"Admin", "Developer"})
    items = payload.items
    if not items:
        return {"success": True, "updated": 0}
    ids = [int(item.id) for item in items]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="An employee can appear only once in a reorder request.")
    marks = ",".join("?" for _ in ids)
    found = conn.execute(f"SELECT id FROM employees WHERE id IN ({marks})", ids).fetchall()
    if len(found) != len(ids):
        raise HTTPException(status_code=404, detail="One or more employees no longer exist.")
    try:
        conn.execute("SAVEPOINT employee_directory_reorder")
        for item in items:
            if item.department is None:
                conn.execute("UPDATE employees SET display_order=? WHERE id=?", (int(item.display_order), int(item.id)))
            else:
                department = str(item.department or "").strip()
                if len(department) > 80:
                    raise HTTPException(status_code=400, detail="Section name is too long.")
                conn.execute("UPDATE employees SET display_order=?, department=? WHERE id=?", (int(item.display_order), department, int(item.id)))
        conn.execute("RELEASE SAVEPOINT employee_directory_reorder")
        conn.commit()
    except HTTPException:
        conn.execute("ROLLBACK TO SAVEPOINT employee_directory_reorder")
        conn.execute("RELEASE SAVEPOINT employee_directory_reorder")
        conn.commit()
        raise
    except Exception as exc:
        conn.execute("ROLLBACK TO SAVEPOINT employee_directory_reorder")
        conn.execute("RELEASE SAVEPOINT employee_directory_reorder")
        conn.commit()
        raise HTTPException(status_code=500, detail=f"Employee order could not be saved: {exc}")
    return {"success": True, "updated": len(items)}

@api.app.patch("/api/employees/{emp_id}/status")
def set_employee_status(emp_id: int, payload: EmployeeStatusPayload, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _require_roles(user, {"HR", "Admin", "Developer"})
    row = conn.execute("SELECT id FROM employees WHERE id=?", (emp_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found.")
    active = 1 if payload.active else 0
    conn.execute("UPDATE employees SET active=? WHERE id=?", (active, emp_id))
    conn.commit()
    return {"success": True, "id": emp_id, "active": active}

@api.app.delete("/api/employees/{emp_id}/permanent")
def permanently_delete_employee(emp_id: int, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _require_roles(user, {"Admin", "Developer"})
    employee = conn.execute("SELECT id, name FROM employees WHERE id=?", (emp_id,)).fetchone()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    backup_dir = Path(api.desktop_app.BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_name = f"employee-delete-{emp_id}-{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.db"
    backup_path = backup_dir / backup_name
    backup_conn = None
    try:
        backup_conn = sqlite3.connect(str(backup_path))
        conn.backup(backup_conn)
        backup_conn.commit()
    except Exception as exc:
        try:
            backup_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Safety backup failed; employee was not deleted: {exc}")
    finally:
        if backup_conn is not None:
            backup_conn.close()
    try:
        conn.execute("SAVEPOINT employee_permanent_delete")
        for table_name in ("tasks", "attendance", "bt_activities"):
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
            if exists:
                conn.execute(f"DELETE FROM {table_name} WHERE employee_id=?", (emp_id,))
        conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        conn.execute("INSERT INTO audit_log(timestamp, action, details) VALUES(?,?,?)", (api.desktop_app.now_text(), "Employee deleted", str(employee["name"])))
        conn.execute("RELEASE SAVEPOINT employee_permanent_delete")
        conn.commit()
    except Exception as exc:
        conn.execute("ROLLBACK TO SAVEPOINT employee_permanent_delete")
        conn.execute("RELEASE SAVEPOINT employee_permanent_delete")
        conn.commit()
        raise HTTPException(status_code=500, detail=f"Employee deletion failed; safety backup retained: {exc}")
    return {"success": True, "deleted": True, "backup_file": backup_name}
