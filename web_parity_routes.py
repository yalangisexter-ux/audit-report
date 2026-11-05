"""Web parity routes for customer discovery, archive, and operational CRUD."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
import csv
import io
import sqlite3
import tempfile
import threading
import uuid

from fastapi import Depends, HTTPException, UploadFile, File, Form, Query
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
        result = {"inserted": 0, "duplicates": 0}
        if records:
            # Use the same managed connection as ordinary API writes. In standalone
            # production this installs the encrypted-sync commit callback, so a
            # background scrape cannot silently update only the local SQLite file.
            db_context = api.get_db()
            try:
                conn = next(db_context)
                db = SimpleNamespace(conn=conn)
                result = cp.persist_prospect_records(
                    db, records, source_name="Deep Web Scraper",
                    source_checked_at=date.today().isoformat()
                )
            finally:
                db_context.close()
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


# Store Directory import, regional coverage, and desktop-compatible export actions.
# Imports always use the desktop's non-destructive merge routine; existing customer
# activity, notes, identifiers, and account records are never replaced.
_STORE_IMPORT_MAX_BYTES = 50 * 1024 * 1024

_STORE_XLSX_FIELDS = (
    ("Store type", "kind"),
    ("Business name", "business_name"),
    ("Category", "business_category"),
    ("State / UT", "state"),
    ("District", "district"),
    ("City", "city"),
    ("Area", "area"),
    ("Contact person", "contact_person"),
    ("Phone numbers", "phone"),
    ("Email addresses", "email"),
    ("Full address", "address"),
    ("Website", "website"),
    ("Google Maps", "maps"),
    ("Verified by call", "verified"),
    ("Verification status", "source_status"),
    ("Source", "source_name"),
    ("Source type", "source_type"),
    ("Source URL", "source_url"),
    ("Last checked", "source_checked_at"),
    ("Response", "response"),
)

_STORE_CSV_FIELDS = (
    ("Store type", "kind"),
    ("state", "state"),
    ("city", "city"),
    ("area", "area"),
    ("business category", "business_category"),
    ("business name", "business_name"),
    ("Mobile number", "phone"),
    ("Email address", "email"),
    ("Full address", "address"),
    ("Google Maps link", "maps"),
    ("Website/social-media link", "website"),
    ("verified by call", "verified"),
    ("response", "response"),
)


def _store_directory_rows(conn, *, state="", query="", kind="", website="", verification=""):
    sql = "SELECT * FROM customer_prospects WHERE 1=1"
    params = []
    if state:
        sql += " AND lower(trim(IFNULL(state,'')))=lower(trim(?))"
        params.append(state)
    if kind:
        sql += " AND lower(trim(IFNULL(kind,'Store')))=lower(trim(?))"
        params.append(kind)
    if website == "has":
        sql += " AND trim(IFNULL(website,''))<>''"
    elif website == "missing":
        sql += " AND trim(IFNULL(website,''))=''"
    verified_expr = (
        "lower(trim(IFNULL(verified,''))) IN ('yes','y','true','verified') "
        "OR lower(IFNULL(source_status,'')) LIKE '%verified%'"
    )
    if verification == "verified":
        sql += " AND (" + verified_expr + ")"
    elif verification == "pending":
        sql += " AND NOT (" + verified_expr + ")"
    if query:
        term = "%" + query.strip() + "%"
        fields = (
            "business_name", "business_category", "kind", "area", "city", "state",
            "contact_person", "phone", "email", "address", "website", "maps",
            "followup_date", "call_time", "connection", "verified", "response",
            "source_status", "notes",
        )
        sql += " AND (" + " OR ".join("IFNULL(" + field + ",'') LIKE ?" for field in fields) + ")"
        params.extend([term] * len(fields))
    sql += " ORDER BY id DESC"
    return _rows(conn, sql, tuple(params))


def _regional_dashboard_rows(conn):
    records = _rows(conn, "SELECT * FROM customer_prospects ORDER BY id")
    dashboard_counts = {}
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='web_customer_dashboard_counts'"
    ).fetchone()
    if table_exists:
        dashboard_counts = {
            str(row["state"]): int(row["store_count"])
            for row in _rows(conn, "SELECT state,store_count FROM web_customer_dashboard_counts")
        }

    rows = prospect_store.build_regional_summary(
        records, dashboard_counts=dashboard_counts, include_all_regions=True
    )
    source_counts = {}
    for record in records:
        raw_state = str(record.get("state") or "").strip()
        if not raw_state:
            continue
        is_web = str(record.get("source_type") or "").casefold().startswith("official web")
        source_key = "web_leads" if is_web else "workbook_leads"
        for part in (value.strip() for value in raw_state.split(",") if value.strip()):
            region = prospect_store.normalise_state(part)
            if region in prospect_store.INDIA_REGIONS:
                source_counts.setdefault(region, {"web_leads": 0, "workbook_leads": 0})
                source_counts[region][source_key] += 1

    for row in rows:
        row["territory_type"] = prospect_store.territory_type(row["state"])
        row.update(source_counts.get(row["state"], {"web_leads": 0, "workbook_leads": 0}))

    totals = {
        "territories": len(rows),
        "web_leads": sum(row["web_leads"] for row in rows),
        "workbook_leads": sum(row["workbook_leads"] for row in rows),
        "stores": sum(row["stores"] for row in rows),
        "gyms": sum(row["gyms"] for row in rows),
        "dashboard_stores": sum(dashboard_counts.values()) if dashboard_counts else None,
        "dashboard_loaded": bool(dashboard_counts),
        "customer_records": len(records),
    }
    return rows, totals


def _attachment(content, media_type, filename):
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": 'attachment; filename="' + filename + '"'},
    )


def _export_xlsx(title, headers, rows, filename, totals_row=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title[:31]
    sheet.append([label for label, _key in headers])
    for record in rows:
        values = [record.get(key, "") for _label, key in headers]
        sheet.append(values)
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(fill_type="solid", fgColor="1E293B")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    if totals_row:
        sheet.append(totals_row)
        for cell in sheet[sheet.max_row]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(fill_type="solid", fgColor="0F172A")
    for column_cells in sheet.columns:
        letter = get_column_letter(column_cells[0].column)
        max_length = max((len(str(cell.value or "")) for cell in column_cells[:1001]), default=12)
        sheet.column_dimensions[letter].width = min(max(max_length + 2, 12), 42)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return _attachment(
        output.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename,
    )


def _export_pdf(title, subtitle, header_labels, rows, filename, column_widths, totals_row=None):
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    output = io.BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=landscape(letter),
        leftMargin=20, rightMargin=20, topMargin=24, bottomMargin=24,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "StoreReportTitle", parent=styles["Heading1"], fontSize=14, leading=17,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_style = ParagraphStyle(
        "StoreReportCell", parent=styles["Normal"], fontSize=7, leading=8.5,
        textColor=colors.HexColor("#1E293B"),
    )
    header_style = ParagraphStyle(
        "StoreReportHeader", parent=styles["Normal"], fontSize=7, leading=8.5,
        fontName="Helvetica-Bold", textColor=colors.white,
    )
    def safe_text(value):
        # ReportLab's built-in Helvetica is WinAnsi; replace unsupported glyphs
        # rather than allowing one unusual customer name to abort an export.
        return escape(str(value if value is not None else "").encode("latin-1", "replace").decode("latin-1"))

    table_data = [[Paragraph("<b>" + safe_text(label) + "</b>", header_style) for label in header_labels]]
    for record in rows:
        table_data.append([Paragraph(safe_text(value), cell_style) for value in record])
    if totals_row:
        table_data.append([Paragraph("<b>" + safe_text(value) + "</b>", header_style) for value in totals_row])

    table = LongTable(table_data, colWidths=column_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    document.build([
        Paragraph("<b>" + safe_text(title) + "</b>", title_style),
        Paragraph(safe_text(subtitle), styles["Normal"]),
        Spacer(1, 8),
        table,
    ])
    return _attachment(output.getvalue(), "application/pdf", filename)


@api.app.post("/api/customers/import")
async def import_customer_workbook(
    file: UploadFile = File(...),
    conn=Depends(api.get_db),
    user=Depends(api.get_current_user),
):
    _admin(user)
    filename = Path(file.filename or "store_directory.xlsx").name
    if Path(filename).suffix.casefold() != ".xlsx":
        raise HTTPException(status_code=400, detail="Upload an Excel .xlsx workbook.")
    content = await file.read(_STORE_IMPORT_MAX_BYTES + 1)
    if len(content) > _STORE_IMPORT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Workbook exceeds the 50 MB import limit.")
    if not content:
        raise HTTPException(status_code=400, detail="The selected workbook is empty.")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="rsc-store-import-", suffix=".xlsx", delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        records, parse_stats = prospect_store.parse_database_workbook(temporary_path)
        if not records:
            raise HTTPException(status_code=422, detail="No identifiable store or gym rows were found in the workbook.")
        result = prospect_store.persist_prospect_records(
            SimpleNamespace(conn=conn),
            records,
            source_name="Web Workbook Import: " + filename,
            source_checked_at=date.today().isoformat(),
        )
        return {
            "success": True,
            "filename": filename,
            "scanned_rows": int(parse_stats.get("scanned_rows", 0)),
            "skipped_unidentified": int(parse_stats.get("skipped_unidentified", 0)),
            "processed": len(records),
            "inserted": int(result.get("inserted", 0)),
            "duplicates_enriched_or_matched": int(result.get("duplicates", 0)),
            "message": "Workbook merged without deleting or replacing existing customer records.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Workbook import failed: " + str(exc)[:400]) from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


@api.app.post("/api/customers/dashboard-import")
async def import_customer_dashboard_workbook(
    file: UploadFile = File(...),
    conn=Depends(api.get_db),
    user=Depends(api.get_current_user),
):
    _admin(user)
    filename = Path(file.filename or "regional_dashboard.xlsx").name
    if Path(filename).suffix.casefold() != ".xlsx":
        raise HTTPException(status_code=400, detail="Upload an Excel .xlsx dashboard workbook.")
    content = await file.read(_STORE_IMPORT_MAX_BYTES + 1)
    if len(content) > _STORE_IMPORT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Dashboard workbook exceeds the 50 MB import limit.")
    if not content:
        raise HTTPException(status_code=400, detail="The selected dashboard workbook is empty.")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="rsc-dashboard-import-", suffix=".xlsx", delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        counts, declared_total = prospect_store.parse_dashboard_workbook(temporary_path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS web_customer_dashboard_counts (
                state TEXT PRIMARY KEY,
                store_count INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        conn.execute("DELETE FROM web_customer_dashboard_counts")
        checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.executemany(
            "INSERT INTO web_customer_dashboard_counts(state,store_count,updated_at) VALUES(?,?,?)",
            [(state, int(count), checked_at) for state, count in counts.items()],
        )
        conn.commit()
        return {
            "success": True,
            "filename": filename,
            "territories": len(counts),
            "dashboard_total": int(declared_total),
            "message": "Regional benchmark counts imported. Existing Store Directory records were not changed.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Dashboard import failed: " + str(exc)[:400]) from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


@api.app.get("/api/customers/regional-summary")
def customer_regional_summary(
    conn=Depends(api.get_db),
    user=Depends(api.get_current_user),
):
    rows, totals = _regional_dashboard_rows(conn)
    return {"rows": rows, "totals": totals}


@api.app.get("/api/customers/export")
def export_customer_directory(
    export_format: str = Query("xlsx", alias="format"),
    state: str = "",
    q: str = "",
    kind: str = "",
    website: str = "",
    verification: str = "",
    conn=Depends(api.get_db),
    user=Depends(api.get_current_user),
):
    if export_format not in {"csv", "xlsx", "pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Supported Store Directory formats are CSV, XLSX, PDF and DOCX.")
    records = _store_directory_rows(
        conn, state=state, query=q, kind=kind, website=website, verification=verification
    )
    if not records:
        raise HTTPException(status_code=404, detail="No Store Directory records match the selected filters.")
    stamp = date.today().strftime("%Y%m%d")

    if export_format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow([label for label, _key in _STORE_CSV_FIELDS])
        for record in records:
            writer.writerow([prospect_store.format_prospect_cell_value(record, key) for _label, key in _STORE_CSV_FIELDS])
        return _attachment(
            output.getvalue().encode("utf-8-sig"),
            "text/csv; charset=utf-8",
            "stores_directory_" + stamp + ".csv",
        )

    if export_format == "xlsx":
        return _export_xlsx(
            "Store Directory", _STORE_XLSX_FIELDS,
            [{key: prospect_store.format_prospect_cell_value(record, key) for _label, key in _STORE_XLSX_FIELDS} for record in records],
            "stores_directory_" + stamp + ".xlsx",
        )

    if export_format == "docx":
        from docx import Document
        from docx.enum.section import WD_ORIENT
        from docx.shared import Inches

        document = Document()
        section = document.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = section.page_height, section.page_width
        document.add_heading("Raw Strength Calisthenics — Store Directory", level=1)
        document.add_paragraph("Generated " + datetime.now().strftime("%Y-%m-%d %H:%M") + " · " + str(len(records)) + " records")
        fields = (("State", "state"), ("City / Area", "city"), ("Business name", "business_name"),
                  ("Category", "business_category"), ("Phone", "phone"), ("Full address", "address"), ("Google Maps", "maps"))
        table = document.add_table(rows=1, cols=len(fields))
        table.style = "Table Grid"
        for index, (label, _key) in enumerate(fields):
            table.rows[0].cells[index].text = label
        for record in records:
            cells = table.add_row().cells
            for index, (_label, key) in enumerate(fields):
                cells[index].text = prospect_store.format_prospect_cell_value(record, key)
        output = io.BytesIO()
        document.save(output)
        return _attachment(
            output.getvalue(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "stores_directory_" + stamp + ".docx",
        )

    fields = (("State", "state"), ("City / Area", "city"), ("Business name", "business_name"),
              ("Category", "business_category"), ("Phone", "phone"), ("Full address", "address"), ("Google Maps", "maps"))
    pdf_rows = [
        [prospect_store.format_prospect_cell_value(record, key) for _label, key in fields]
        for record in records
    ]
    return _export_pdf(
        "RAW STRENGTH CALISTHENICS — STORE AUDIT & CUSTOMER PROSPECTS",
        "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M") + " | Filtered records: " + str(len(records)),
        [label for label, _key in fields],
        pdf_rows,
        "stores_directory_" + stamp + ".pdf",
        [58, 72, 126, 78, 72, 190, 125],
    )


@api.app.get("/api/customers/regional-export")
def export_customer_regional_dashboard(
    export_format: str = Query("xlsx", alias="format"),
    territory_type: str = "",
    conn=Depends(api.get_db),
    user=Depends(api.get_current_user),
):
    if export_format not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(status_code=400, detail="Supported regional formats are CSV, XLSX and PDF.")
    rows, totals = _regional_dashboard_rows(conn)
    if territory_type:
        allowed_types = {"State", "Union Territory", "Island Territory"}
        if territory_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid territory type filter.")
        rows = [row for row in rows if row["territory_type"] == territory_type]
    if not rows:
        raise HTTPException(status_code=404, detail="No regional dashboard rows are available.")
    stamp = date.today().strftime("%Y%m%d")
    fields = (
        ("State / UT / Island", "state"),
        ("Territory Type", "territory_type"),
        ("Web leads", "web_leads"),
        ("Workbook leads", "workbook_leads"),
        ("All stores", "stores"),
        ("All gyms", "gyms"),
        ("Dashboard stores", "dashboard_stores"),
        ("Difference", "variance"),
    )

    if export_format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow([label for label, _key in fields])
        for row in rows:
            writer.writerow([row.get(key, "") if row.get(key) is not None else "" for _label, key in fields])
        return _attachment(
            output.getvalue().encode("utf-8-sig"),
            "text/csv; charset=utf-8",
            "regional_dashboard_" + stamp + ".csv",
        )

    if export_format == "xlsx":
        export_rows = []
        for row in rows:
            export_rows.append({
                "state": row["state"],
                "territory_type": row["territory_type"],
                "web_leads": row["web_leads"],
                "workbook_leads": row["workbook_leads"],
                "stores": row["stores"],
                "gyms": row["gyms"],
                "dashboard_stores": row["dashboard_stores"] if row["dashboard_stores"] is not None else "—",
                "variance": (f'{row["variance"]:+d}' if row["variance"] is not None else "—"),
            })
        total_row = [
            "TOTAL", str(len(rows)) + " Territories",
            sum(row["web_leads"] for row in rows),
            sum(row["workbook_leads"] for row in rows),
            sum(row["stores"] for row in rows),
            sum(row["gyms"] for row in rows),
            "", "",
        ]
        return _export_xlsx(
            "Regional Coverage", fields, export_rows,
            "regional_dashboard_" + stamp + ".xlsx", totals_row=total_row,
        )

    pdf_rows = []
    for row in rows:
        pdf_rows.append([
            row["state"], row["territory_type"], row["web_leads"], row["workbook_leads"],
            row["stores"], row["gyms"],
            row["dashboard_stores"] if row["dashboard_stores"] is not None else "—",
            (f'{row["variance"]:+d}' if row["variance"] is not None else "—"),
        ])
    total_row = [
        "TOTAL", str(len(rows)) + " Territories",
        sum(row["web_leads"] for row in rows),
        sum(row["workbook_leads"] for row in rows),
        sum(row["stores"] for row in rows),
        sum(row["gyms"] for row in rows),
        "—", "—",
    ]
    return _export_pdf(
        "RAW STRENGTH CALISTHENICS — REGIONAL DASHBOARD AUDIT",
        "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M") + " | Territories: " + str(len(rows)),
        [label for label, _key in fields],
        pdf_rows,
        "regional_dashboard_" + stamp + ".pdf",
        [126, 102, 70, 80, 70, 70, 100, 70],
        totals_row=total_row,
    )
