"""Web parity routes for customer discovery, archive, and operational CRUD."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import threading
import uuid

from fastapi import Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response

import customer_prospects as prospect_store
import api_server as api

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="web-parity")
_jobs = {}
_jobs_lock = threading.Lock()


def _admin(user):
    if str(user.get("role", "")).casefold() not in {"admin", "developer"}:
        raise HTTPException(status_code=403, detail="Admin or Developer permission required")


def _rows(conn, sql, params=()):
    cur = conn.execute(sql, params)
    names = [x[0] for x in cur.description or []]
    return [dict(r) if isinstance(r, sqlite3.Row) else dict(zip(names, r)) for r in cur.fetchall()]


@api.app.get("/api/archive")
def list_archive(conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    return _rows(conn, """SELECT d.id,d.employee_id,COALESCE(e.name,'Unassigned / All') AS employee_name,
        d.report_date,d.file_name,d.mime_type,d.notes,d.uploaded_at,length(d.content) AS size_bytes
        FROM archived_documents d LEFT JOIN employees e ON e.id=d.employee_id ORDER BY d.uploaded_at DESC,d.id DESC""")

@api.app.post("/api/archive")
async def upload_archive(file: UploadFile = File(...), employee_id: int | None = Form(None),
                         report_date: str = Form(""), notes: str = Form(""),
                         conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    filename = Path(file.filename or "archive.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be archived.")
    if report_date:
        try: date.fromisoformat(report_date)
        except ValueError: raise HTTPException(status_code=400, detail="Report date must use YYYY-MM-DD.")
    content = await file.read(25 * 1024 * 1024 + 1)
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF exceeds the 25 MB upload limit.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")
    if employee_id is not None and not conn.execute("SELECT 1 FROM employees WHERE id=?", (employee_id,)).fetchone():
        raise HTTPException(status_code=400, detail="Selected employee was not found.")
    cur = conn.execute("""INSERT INTO archived_documents(employee_id,report_date,file_name,mime_type,content,notes,uploaded_at)
        VALUES(?,?,?,?,?,?,?)""", (employee_id, report_date, filename, "application/pdf", sqlite3.Binary(content),
        notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    return {"success": True, "id": cur.lastrowid}

def _archive_pdf_response(document_id: int, disposition: str, conn):
    row = conn.execute(
        "SELECT file_name,mime_type,content FROM archived_documents WHERE id=?",
        (document_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Archived document not found.")
    filename = Path(row["file_name"] or f"archive-{document_id}.pdf").name
    filename = "".join(
        char for char in filename
        if ord(char) >= 32 and char not in {'"', chr(92), chr(13), chr(10)}
    ).strip()
    if not filename:
        filename = f"archive-{document_id}.pdf"
    return Response(
        content=bytes(row["content"]),
        media_type=row["mime_type"] or "application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@api.app.get("/api/archive/{document_id}/view")
def view_archive(document_id: int, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    return _archive_pdf_response(document_id, "inline", conn)


@api.app.get("/api/archive/{document_id}/download")
def download_archive(document_id: int, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    return _archive_pdf_response(document_id, "attachment", conn)

@api.app.delete("/api/archive/{document_id}")
def delete_archive(document_id: int, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _admin(user)
    cur = conn.execute("DELETE FROM archived_documents WHERE id=?", (document_id,))
    conn.commit()
    if not cur.rowcount: raise HTTPException(status_code=404, detail="Archived document not found.")
    return {"success": True}


def _run_scrape(job_id, state, query, max_results, deep_scrape):
    try:
        import customer_prospects as cp
        records = cp.crawl_search_engine_results(
            category="Pure Product Selling Stores", state=state, query_term=query,
            max_results=max_results, deep_scrape=deep_scrape
        )
        conn = sqlite3.connect(str(api.desktop_app.DB_PATH), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            db = SimpleNamespace(conn=conn)
            result = cp.persist_prospect_records(
                db, records, source_name="Deep Web Scraper",
                source_checked_at=date.today().isoformat()
            )
        finally:
            conn.close()
        with _jobs_lock:
            _jobs[job_id].update({"status":"completed","found":len(records),"result":result,"error":""})
    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id].update({"status":"failed","error":str(exc)[:500]})


@api.app.post("/api/customers/scrape")
def start_customer_scrape(payload: dict, user=Depends(api.get_current_user)):
    state = str(payload.get("state") or "").strip()
    query = str(payload.get("query") or "").strip()
    try: max_results = max(1, min(30, int(payload.get("max_results", 10))))
    except (TypeError, ValueError): max_results = 10
    deep = bool(payload.get("deep_scrape", True))
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {"id":job_id,"status":"running","state":state,"query":query,"found":0,"error":""}
    _pool.submit(_run_scrape, job_id, state, query, max_results, deep)
    return {"job_id":job_id,"status":"running"}

@api.app.get("/api/customers/scrape/{job_id}")
def customer_scrape_status(job_id: str, user=Depends(api.get_current_user)):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job: raise HTTPException(status_code=404, detail="Scrape job not found or expired.")
        return dict(job)


@api.app.patch("/api/customers/prospects/{prospect_id}")
def update_prospect(prospect_id: int, payload: dict, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _admin(user)
    allowed = {"business_name","business_category","kind","state","city","area","contact_person","phone","email",
               "address","website","maps","followup_date","call_time","connection","verified","response",
               "notes","source_status","verification_status","last_verified"}
    changes = {k:v for k,v in payload.items() if k in allowed}
    if not changes:
        raise HTTPException(status_code=400, detail="No editable prospect fields supplied.")

    columns = {r["name"] for r in conn.execute("PRAGMA table_info(customer_prospects)").fetchall()}
    changes = {k:v for k,v in changes.items() if k in columns}
    if not changes:
        raise HTTPException(status_code=400, detail="No supported prospect fields supplied.")
    if "dedupe_key" not in columns:
        raise HTTPException(status_code=500, detail="Store Directory deduplication schema is unavailable.")

    existing = conn.execute("SELECT * FROM customer_prospects WHERE id=?", (prospect_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Prospect not found.")

    record = dict(existing)
    record.update(changes)
    record["business_name"] = str(record.get("business_name") or "").strip()
    record["kind"] = str(record.get("kind") or "Store").strip()
    record["state"] = prospect_store.normalise_state(record.get("state"))
    record["city"] = str(record.get("city") or "").strip()
    record["address"] = str(record.get("address") or "").strip()
    record["maps"] = str(record.get("maps") or "").strip()
    if not record["business_name"]:
        raise HTTPException(status_code=422, detail="Business / store name is required.")
    if not record["state"] or not record["city"]:
        raise HTTPException(status_code=422, detail="City and state are required to identify a unique store branch.")

    if not record["maps"] and record["address"]:
        record["maps"] = prospect_store.google_maps_search_url(record)

    new_dedupe_key = prospect_store.prospect_dedupe_key(record)
    other_rows = conn.execute(
        "SELECT id,business_name,state,city FROM customer_prospects WHERE id<>?",
        (prospect_id,),
    ).fetchall()
    for other in other_rows:
        if prospect_store.prospect_dedupe_key(dict(other)) == new_dedupe_key:
            raise HTTPException(
                status_code=409,
                detail="A store with the same business name, city and state already exists.",
            )

    for field in ("business_name", "kind", "state", "city", "address"):
        if field in changes:
            changes[field] = record[field]
    if "maps" in changes or (not str(existing["maps"] or "").strip() and record["maps"]):
        changes["maps"] = record["maps"]
    changes["dedupe_key"] = new_dedupe_key
    if "updated_at" in columns:
        changes["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changes = {k:v for k,v in changes.items() if k in columns}

    assignments = ", ".join(f'"{key}"=?' for key in changes)
    try:
        cur = conn.execute(
            f"UPDATE customer_prospects SET {assignments} WHERE id=?",
            (*changes.values(), prospect_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    if not cur.rowcount:
        raise HTTPException(status_code=404, detail="Prospect not found.")
    return {"success": True, "dedupe_key": new_dedupe_key}

@api.app.delete("/api/customers/prospects/{prospect_id}")
def delete_prospect(prospect_id: int, conn=Depends(api.get_db), user=Depends(api.get_current_user)):
    _admin(user)
    cur=conn.execute("DELETE FROM customer_prospects WHERE id=?", (prospect_id,))
    conn.commit()
    if not cur.rowcount: raise HTTPException(status_code=404, detail="Prospect not found.")
    return {"success":True}
