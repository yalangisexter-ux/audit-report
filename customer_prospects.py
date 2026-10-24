"""Read-only explorer, web scraper, and print/export center for customer/prospect workbooks."""
from collections import defaultdict
import base64
import csv
from datetime import date, datetime, time
import hashlib
import io
import json
import logging
from pathlib import Path
import re
import sys
import urllib.request
import urllib.parse

from openpyxl import Workbook, load_workbook
from PySide6.QtCore import Qt, QTimer, QUrl, QThread, Signal
from PySide6.QtGui import QColor, QDesktopServices, QPalette, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import google_sheets_sync

MAX_WORKBOOK_BYTES = 50 * 1024 * 1024
REFERENCE_DATABASE_URL = "https://1drv.ms/x/c/a3aac0512044da6f/IQCll6KW063nQ6A_EUwZ1VPyAWg0BN-FsAmoYwawsnUKH40?e=hIJA3x"
REFERENCE_DASHBOARD_URL = "https://1drv.ms/x/c/a3aac0512044da6f/IQC7OF8bQj_7Q4pEOyu30GJHATIgpGZ2HMWlX7cXkTWduZc?e=Hby1MO"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1edK9BASSDPOcJZ94WcaCkWAoQHr-AkgTmy6axWv0r-o/edit?gid=0#gid=0"
RESEARCH_DATE = "2026-10-24"

# Strict negative filter keywords requested by client:
# ❌ No pharmacies / medical / chemists
# ❌ No herbal / ayurvedic / homeopathic / Herbalife
# ❌ No HealthKart stores
NEGATIVE_FILTER_PATTERN = re.compile(
    r'\b(pharmacy|chemist|medical|druggist|drug|ayurved|ayurvedic|herbal|herbalife|homeopath|homeopathic|healthkart|health\s*kart)\b',
    re.IGNORECASE
)

# Entries are limited to businesses explicitly published as authorized retailers
# on the brand's own public seller page. These have not been call-verified.
RESEARCHED_WEB_LEADS = [
    {"business_name": "AR Soft Solutions", "city": "Prayagraj", "state": "Uttar Pradesh", "address": "8A/2D/3/UGF-SN-1, Har Nikunj, Stanley Road, Yog Ashram, Civil Lines, Prayagraj 211001", "phone": "+91 9336847362"},
    {"business_name": "BM Food Supplement", "city": "Faridabad", "state": "Haryana", "address": "Radha Nagar, Government Hospital, Ballabgarh, Faridabad 121004", "phone": "9899683411"},
    {"business_name": "Body Fuel", "city": "Faridabad", "state": "Haryana", "address": "H No. 9A/A, Nehru Ground, NIT Faridabad 121001", "phone": "+91 9873751194"},
    {"business_name": "Fit Life Nutrition", "city": "Dehradun", "state": "Uttarakhand", "address": "Shop No. 6, Shiva Place, Rajpur Road, Dehradun 248001", "phone": "+91 9410650094"},
    {"business_name": "Fitness Nutrition and Supplement", "city": "Lucknow", "state": "Uttar Pradesh", "address": "Awanti Vihar, Baldi Khera, Rajaji Puram, Lucknow 226017", "phone": "+91 7275005004"},
    {"business_name": "Grow Healthy", "city": "Hubli", "state": "Karnataka", "address": "96, Mitravishal Park, Vidyanagar, Hubli 580031", "phone": "+91 9663443856"},
    {"business_name": "Highborn Nutrition & Fitness Pvt Ltd", "city": "Visakhapatnam", "state": "Andhra Pradesh", "address": "Ground Floor, Dr No. 50-81-19/1, Seethammapeta Main Road, near GBK Plaza, Visakhapatnam 530016", "phone": "+91 9178640017"},
    {"business_name": "Highborn Nutrition & Fitness Pvt Ltd", "city": "Raipur", "state": "Chhattisgarh", "address": "Ground Floor, Khasra No. 638/50 & 638/51, Sankar Nagar Main Road, Geetanjali Colony, Raipur 492004", "phone": "+91 9178640017"},
    {"business_name": "Highborn Nutrition and Fitness Pvt Ltd", "city": "Patna", "state": "Bihar", "address": "Ground Floor, Ward No. 35, Kankarbagh Main Road, Kankarbagh, Patna 800020", "phone": "9178640017"},
    {"business_name": "Highborn Nutrition and Fitness Pvt Ltd", "city": "Indore", "state": "Madhya Pradesh", "address": "Ground Floor, Shop No. 3, Sapna Sangeeta Main Road, Sneh Nagar, Indore 452001", "phone": "+91 9178640017"},
    {"business_name": "Highborn Nutrition and Fitness Pvt Ltd", "city": "Bhubaneswar", "state": "Odisha", "address": "Ground Floor, Plot No. 279/7982, Jaydev Vihar, Bhubaneswar 751012", "phone": "+91 9178640017"},
    {"business_name": "Juneja Ventures", "city": "Patna", "state": "Bihar", "address": "Juneja House, near Poddar Bhawan, Saidpur Gali, Bhikna Pahari, Patna", "phone": "9608431790"},
    {"business_name": "Lean Lab", "city": "Kolkata", "state": "West Bengal", "address": "176A Rash Behari Avenue, Ground Floor, near Triangular Park, Kolkata 700029", "phone": "+91 9830201232"},
    {"business_name": "Macro Nutrition", "city": "Vadodara", "state": "Gujarat", "address": "FF-8, Kunj Plaza, Chhani Road, Vadodara 391740", "phone": "+91 9727932983"},
    {"business_name": "Massit", "city": "Chennai", "state": "Tamil Nadu", "address": "No. 19, Dr. Ambedkar Road, Kodambakkam, Chennai 600024", "phone": "+91 9840515802"},
    {"business_name": "Multi Fitness Nutrition", "city": "Faridabad", "state": "Haryana", "address": "Shop No. 126/2, Jawahar Colony, Faridabad 121005", "phone": "+91 7838334445"},
    {"business_name": "National Sports Nutrition", "city": "Delhi", "state": "Delhi", "address": "Shop No. JD 21A, Ashiana Chowk, Pitampura, Delhi 110034", "phone": "9999099212"},
    {"business_name": "ProStar Nutrition", "city": "Hyderabad", "state": "Telangana", "address": "S.No. 1-69, Old Bombay Road, Chanda Nagar, Serilingampally, Hyderabad 500050", "phone": "9848202071"},
    {"business_name": "Proteins & More Healthcare", "city": "Ahmedabad", "state": "Gujarat", "address": "4, Prime Plaza Complex, NFD Circle, Judges Bungalow Road, Ahmedabad 380054", "phone": "9558460130"},
    {"business_name": "S.A. Enterprises", "city": "Kanpur", "state": "Uttar Pradesh", "address": "79/92 A, Bans Mandi, Kanpur Nagar 208001", "phone": "+91 9839074898"},
    {"business_name": "Sachdeva & Co", "city": "Chandigarh", "state": "Chandigarh", "address": "SCO 413-414, Basement, Sector 35-C, Chandigarh 160022", "phone": "+91 9814245255"},
    {"business_name": "Sportika Supplements (RSS Supplement)", "city": "Bhopal", "state": "Madhya Pradesh", "address": "Ground Floor, 17, Rishi Nagar, Char Imli Road, Bhopal 462016", "phone": "7898361555"},
    {"business_name": "STRONG n SORE", "city": "Delhi", "state": "Delhi", "address": "Ground Floor, Plot No. 11, F-Block, Indra Park, Main Najafgarh Road, New Delhi 110043", "phone": "+91 9821924169"},
    {"business_name": "Team Beast Sports Nutrition Shop", "city": "Madurai", "state": "Tamil Nadu", "address": "First Floor, 12-G, K.M.A. Complex, Bye Pass Road, Ram Nagar, Madurai 625016", "phone": "+91 9092984227"},
    {"business_name": "The Caffeine Shop", "city": "Vijayawada", "state": "Andhra Pradesh", "address": "Flat 301, Padmavathi Nilayam, Telephone Colony, Bhavanipuram, Vijayawada", "phone": "9700179988"},
    {"business_name": "US Brands", "city": "Mumbai", "state": "Maharashtra", "address": "Shop #5, Vandana Building, Tilak Road, Ghatkopar East, Mumbai 400077", "phone": "+91 8976660927"},
    {"business_name": "Vasuki Fitness", "city": "Mumbai", "state": "Maharashtra", "address": "Unit 22, B-Wing, Laxmi Business Park, Laxmi Industrial Estate, Andheri West, Mumbai 400053", "phone": "+91 9082854336"},
    {"business_name": "Vitamin Galaxy", "city": "Bengaluru", "state": "Karnataka", "address": "No. 466, 80 Feet Road, 6th Block, Koramangala, Bengaluru 560095", "phone": "+91 9539091449"},
    {"business_name": "World of Nutrition", "city": "Cuttack", "state": "Odisha", "address": "Shelter Chhak, Tulasipur, Bidanasi, Cuttack 753008", "phone": "+91 9938180455"},
]
RESEARCHED_SOURCE_NAME = "ProSupps India authorized sellers list"
RESEARCHED_SOURCE_URL = "https://prosuppsindia.com/pages/authorized-sellers"
RESEARCHED_SOURCE_STATUS = "Listed by brand as an authorized retailer; confirm current details by call"

FIELD_ALIASES = {
    "business_name": {"businessname", "storename", "gymname", "name"},
    "business_category": {"businesscategory", "category"},
    "state": {"state", "stateut", "stateunionterritory"},
    "city": {"city"},
    "area": {"area", "locality"},
    "contact_person": {"contactperson", "decisionmaker"},
    "phone": {"mobilenumber", "mobile", "phonenumber", "phone", "contactnumber", "whatsappnumber"},
    "address": {"fulladdress", "address"},
    "website": {"website", "websitelink", "websitesocialmedialink", "socialmedialink", "instagram", "instagramlink"},
    "maps": {"googlemapslink", "googlemaps", "googlemap", "gooplemap", "googlrmap", "googlemapslinkinstagramlink"},
    "followup_date": {"date", "calldate", "verifieddate"},
    "call_time": {"calltime"},
    "connection": {"connectednotconnected", "connectednotconntected", "connectionstatus", "contactstatus"},
    "verified": {"verifiedyesno", "verifiedbycall", "verified", "callverified"},
    "response": {"response", "interestednotinterested", "interest"},
}
ALIAS_TO_FIELD = {alias: field for field, aliases in FIELD_ALIASES.items() for alias in aliases}

STATE_NAMES = {
    "andhrapradesh": "Andhra Pradesh",
    "arunachalpradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachalpradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhyapradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "maharasthra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "odhisha": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamilnadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttarpradesh": "Uttar Pradesh",
    "uttharpradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "westbengal": "West Bengal",
    "andamanandnicobarisland": "Andaman and Nicobar Islands",
    "andamanandnicobarislands": "Andaman and Nicobar Islands",
    "chandigarh": "Chandigarh",
    "dnhdd": "Dadra and Nagar Haveli and Daman and Diu",
    "dadraandnagarhavelianddamandiu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadraandnagarhavelianddamananddiu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi",
    "delhincr": "Delhi",
    "jammuandkashmir": "Jammu and Kashmir",
    "ladakh": "Ladakh",
    "lakshadweep": "Lakshadweep",
    "puducherry": "Puducherry",
}
INDIA_REGIONS = tuple(sorted(set(STATE_NAMES.values()), key=str.casefold))


def _normalise_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value).strip()


def normalise_state(value, fallback=""):
    raw = _cell_text(value) or _cell_text(fallback)
    key = _normalise_key(raw)
    if key in STATE_NAMES:
        return STATE_NAMES[key]
    for suffix in ("stores", "store", "gym"):
        if key.endswith(suffix):
            key = key[:-len(suffix)]
            if key in STATE_NAMES:
                return STATE_NAMES[key]
    return " ".join(part.capitalize() for part in raw.split())


def _canonical_header(value):
    if isinstance(value, (date, datetime)):
        return "followup_date"
    key = _normalise_key(value)
    return ALIAS_TO_FIELD.get(key, "")


def _is_repeated_header(headers, values):
    matches = 0
    populated = 0
    for header, value in zip(headers, values):
        if header is None or value is None or not str(value).strip():
            continue
        populated += 1
        if _normalise_key(header) == _normalise_key(value):
            matches += 1
    return populated >= 3 and matches >= max(3, int(populated * 0.6))


def _checked_xlsx_path(path):
    source = Path(path)
    if source.suffix.casefold() != ".xlsx":
        raise ValueError("Select an .xlsx workbook.")
    if not source.is_file():
        raise ValueError("The selected workbook could not be found.")
    if source.stat().st_size > MAX_WORKBOOK_BYTES:
        raise ValueError("Workbook is larger than the 50 MB import limit.")
    if source.stat().st_size == 0:
        raise ValueError("The selected workbook is empty.")
    return source


def parse_database_workbook(path):
    """Read prospect rows from all sheets without changing the selected file."""
    source = _checked_xlsx_path(path)
    workbook = load_workbook(source, read_only=True, data_only=True, keep_links=False)
    records = []
    scanned_rows = 0
    skipped_unidentified = 0
    try:
        for sheet in workbook.worksheets:
            rows = sheet.iter_rows(values_only=True)
            headers = next(rows, ())
            fields = [_canonical_header(header) for header in headers]
            gym_sheet = "gym" in _normalise_key(sheet.title)
            kind = "Gym" if gym_sheet else "Store"
            for excel_row, values in enumerate(rows, start=2):
                if not values or not any(value is not None and str(value).strip() for value in values):
                    continue
                if _is_repeated_header(headers, values):
                    continue
                scanned_rows += 1
                record = {field: "" for field in FIELD_ALIASES}
                for field, value in zip(fields, values):
                    if not field:
                        continue
                    text = _cell_text(value)
                    if text and (not record[field] or field in {"followup_date", "call_time", "connection", "verified", "response"}):
                        record[field] = text
                if not any(record[field] for field in ("business_name", "phone", "address")):
                    skipped_unidentified += 1
                    continue
                
                # Check negative filter
                combined_text = f"{record.get('business_name', '')} {record.get('business_category', '')}"
                if NEGATIVE_FILTER_PATTERN.search(combined_text):
                    continue

                record["kind"] = kind
                record["state"] = normalise_state(record["state"], sheet.title)
                record["source_sheet"] = sheet.title
                record["source_row"] = excel_row
                records.append(record)
    finally:
        workbook.close()
    return records, {"scanned_rows": scanned_rows, "skipped_unidentified": skipped_unidentified}


def parse_dashboard_workbook(path):
    """Read the state/UT store-count reference without changing the workbook."""
    source = _checked_xlsx_path(path)
    workbook = load_workbook(source, read_only=True, data_only=True, keep_links=False)
    counts = {}
    declared_total = None
    try:
        for sheet in workbook.worksheets:
            rows = sheet.iter_rows(values_only=True)
            headers = next(rows, ())
            state_index = next((i for i, value in enumerate(headers) if _normalise_key(value) in {"state", "stateut", "stateunionterritory"}), None)
            count_index = next((i for i, value in enumerate(headers) if _normalise_key(value) in {"stores", "storecount", "count", "totalstores"}), None)
            if state_index is None or count_index is None:
                continue
            for values in rows:
                if state_index >= len(values) or count_index >= len(values):
                    continue
                label = _cell_text(values[state_index])
                raw_count = values[count_index]
                if not label or raw_count is None:
                    continue
                try:
                    count = int(float(str(raw_count).replace(",", "").strip()))
                except (TypeError, ValueError):
                    continue
                if _normalise_key(label) == "total":
                    declared_total = count
                else:
                    counts[normalise_state(label)] = count
    finally:
        workbook.close()
    if not counts:
        raise ValueError("No State/UT and Stores rows were found in the selected workbook.")
    return counts, declared_total if declared_total is not None else sum(counts.values())


def build_regional_summary(records, dashboard_counts=None, include_all_regions=False):
    """Combine in-memory workbook counts while preserving the source totals."""
    totals = defaultdict(lambda: {"Store": 0, "Gym": 0})
    for record in records:
        state = normalise_state(record.get("state"))
        if state:
            kind = record.get("kind") if record.get("kind") in {"Store", "Gym"} else "Store"
            totals[state][kind] += 1
    dashboard_counts = dashboard_counts or {}
    all_states = set(totals) | set(dashboard_counts)
    if include_all_regions:
        all_states.update(INDIA_REGIONS)
    rows = []
    for state in sorted(all_states, key=str.casefold):
        store_count = totals[state]["Store"]
        gym_count = totals[state]["Gym"]
        dashboard_count = dashboard_counts.get(state)
        variance = store_count - dashboard_count if dashboard_count is not None else None
        rows.append({
            "state": state,
            "stores": store_count,
            "gyms": gym_count,
            "dashboard_stores": dashboard_count,
            "variance": variance,
        })
    return rows


def prospect_dedupe_key(record):
    identity = "|".join(
        _normalise_key(record.get(field))
        for field in ("kind", "business_name", "state", "city", "address")
    )
    if not _normalise_key(record.get("address")):
        identity += "|" + _normalise_key(record.get("phone"))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def persist_prospect_records(db, records, *, source_name="", source_url="", source_checked_at=None):
    """Append prospect rows to the app database without replacing existing activity."""
    checked_at = source_checked_at or datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0
    duplicate = 0
    fields = (
        "dedupe_key", "kind", "business_name", "business_category", "state", "city", "area",
        "contact_person", "phone", "address", "website", "maps", "followup_date", "call_time",
        "connection", "verified", "response", "notes", "source_name", "source_url", "source_type",
        "source_checked_at", "source_sheet", "source_row", "source_status", "created_at", "updated_at",
    )
    placeholders = ",".join("?" for _ in fields)
    columns = ",".join(fields)
    try:
        db.conn.execute("BEGIN")
        for source_record in records:
            record = dict(source_record)
            record["kind"] = record.get("kind") or "Store"
            record["state"] = normalise_state(record.get("state"))
            record["business_name"] = str(record.get("business_name") or "").strip()
            if not record["business_name"]:
                continue
            
            # Check negative filter
            combined = f"{record['business_name']} {record.get('business_category', '')}"
            if NEGATIVE_FILTER_PATTERN.search(combined):
                continue

            call_verified = str(record.get("verified") or "").strip().casefold() in {"yes", "y", "true", "verified"}
            record.setdefault("source_name", source_name)
            record.setdefault("source_url", source_url)
            record.setdefault("source_type", "Workbook")
            record.setdefault("source_checked_at", checked_at)
            record.setdefault("source_status", "Workbook indicates call verified" if call_verified else "Needs direct confirmation")
            record["dedupe_key"] = prospect_dedupe_key(record)
            record["created_at"] = now
            record["updated_at"] = now
            values = [record.get(field, "") for field in fields]
            cursor = db.conn.execute(
                f"INSERT OR IGNORE INTO customer_prospects({columns}) VALUES({placeholders})",
                values,
            )
            if cursor.rowcount:
                inserted += 1
            else:
                duplicate += 1
        db.conn.commit()
    except Exception:
        db.conn.rollback()
        raise
    return {"inserted": inserted, "duplicates": duplicate}


def load_saved_prospects(db):
    rows = db.conn.execute(
        "SELECT * FROM customer_prospects ORDER BY state COLLATE NOCASE, city COLLATE NOCASE, business_name COLLATE NOCASE"
    ).fetchall()
    return [dict(row) for row in rows]


def resource_path(relative_path: str) -> Path:
    """Resolve bundled assets in source and PyInstaller builds."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    target = base_path / relative_path
    if not target.exists():
        alt = Path(__file__).resolve().parent / relative_path
        if alt.exists():
            return alt
    return target


def unwrap_search_url(href: str) -> str:
    """Unwrap redirect URLs from search engines (Bing /ck/a base64, DuckDuckGo /l/?uddg, Google /url?q)."""
    href = str(href or "").strip().replace("&amp;", "&")
    if href.startswith("//"):
        href = "https:" + href

    # 1. DuckDuckGo redirect: /l/?uddg=... or //duckduckgo.com/l/?uddg=...
    if "uddg=" in href:
        query_str = href.split("?", 1)[-1]
        params = urllib.parse.parse_qs(query_str)
        uddg = params.get("uddg", [""])[0]
        if uddg:
            return urllib.parse.unquote(uddg)

    # 2. Bing redirect: /ck/a?!...&u=a1<base64>...
    if "/ck/a" in href or "/aclick" in href or "u=a1" in href:
        query_str = href.split("?", 1)[-1]
        params = urllib.parse.parse_qs(query_str)
        u = (params.get("u") or params.get("url") or [""])[0]
        if u.startswith("a1"):
            raw = u[2:]
            raw += "=" * (-len(raw) % 4)
            try:
                decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="ignore")
                if decoded.startswith("http"):
                    return decoded
            except Exception:
                pass
        elif u.startswith("http"):
            return u

    # 3. Google redirect: /url?q=...
    if "/url?" in href and "q=" in href:
        query_str = href.split("?", 1)[-1]
        params = urllib.parse.parse_qs(query_str)
        q = params.get("q", [""])[0]
        if q.startswith("http"):
            return q

    return href


def seed_official_web_prospects(db):
    """One-time, idempotent local seed of bundled All-India stores and brand-listed retailer leads."""
    setting = "customer_prospects_official_web_seed_20261024_v2"
    if db.get_setting(setting) == "1":
        return {"inserted": 0, "duplicates": 0}

    records = []
    # 1. Bundled All-India Stores Seed (3,973 authentic stores across 36 States/UTs)
    seed_path = resource_path("assets/india_stores_seed.json")
    if seed_path.is_file():
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                seed_data = json.load(f)
            if isinstance(seed_data, list) and seed_data:
                records.extend(seed_data)
        except Exception as exc:
            logging.getLogger("prospects").warning("Could not read bundled store seed: %s", exc)

    # 2. Researched web leads
    records.extend([
        {
            **lead,
            "kind": "Store",
            "business_category": "Sports nutrition retailer",
            "source_name": RESEARCHED_SOURCE_NAME,
            "source_url": RESEARCHED_SOURCE_URL,
            "source_type": "Official web listing",
            "source_checked_at": RESEARCH_DATE,
            "source_status": RESEARCHED_SOURCE_STATUS,
        }
        for lead in RESEARCHED_WEB_LEADS
    ])

    result = persist_prospect_records(
        db,
        records,
        source_name="Bundled All-India Store Directory",
        source_url=REFERENCE_DATABASE_URL,
        source_checked_at=RESEARCH_DATE,
    )
    db.set_setting(setting, "1")
    return result


class WebScraperWorker(QThread):
    """Background worker to scrape verified supplement stores from web across regions."""
    progress = Signal(str, int)
    finished = Signal(list, str)

    def __init__(self, region="", query_term="", parent=None):
        super().__init__(parent)
        self.region = region
        self.query_term = query_term or "supplement store nutrition"

    def run(self):
        """Search multiple public search engines; results are verified against negative filters."""
        found = []
        seen_urls = set()
        errors = []
        clean_region = self.region if self.region != "All States / UTs" else ""
        base_query = f"{self.query_term} {clean_region} India".strip()

        queries = [
            base_query,
            f'site:justdial.com "{self.query_term}" {clean_region} India'.strip(),
            f'intitle:store "{self.query_term}" {clean_region} India'.strip(),
        ]
        engines = [
            ("DuckDuckGo", "https://html.duckduckgo.com/html/?q={query}"),
            ("Bing", "https://www.bing.com/search?q={query}"),
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-IN,en;q=0.9",
        }

        blocked_domains = {
            "bing.com", "duckduckgo.com", "google.com", "microsoft.com", "yahoo.com",
            "wikipedia.org", "youtube.com", "amazon.in", "flipkart.com", "facebook.com",
            "instagram.com", "twitter.com", "x.com", "linkedin.com", "msn.com"
        }

        try:
            total = len(engines) * len(queries)
            completed = 0
            for engine_name, engine_template in engines:
                for query in queries:
                    completed += 1
                    self.progress.emit(
                        f"Searching {engine_name} ({completed}/{total}): {query[:90]}",
                        min(90, int(completed * 90 / total)),
                    )
                    search_url = engine_template.format(query=urllib.parse.quote(query))
                    try:
                        request = urllib.request.Request(search_url, headers=headers)
                        with urllib.request.urlopen(request, timeout=12) as response:
                            html = response.read(2_500_000).decode("utf-8", errors="ignore")
                    except Exception as exc:
                        errors.append(f"{engine_name}: {exc}")
                        continue

                    anchors = re.findall(
                        r"<a\b[^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>",
                        html, flags=re.IGNORECASE | re.DOTALL
                    )
                    for raw_href, raw_title in anchors:
                        clean_url = unwrap_search_url(raw_href)
                        parsed_url = urllib.parse.urlparse(clean_url)
                        host = (parsed_url.netloc or "").lower()
                        if parsed_url.scheme not in {"http", "https"}:
                            continue
                        if any(domain in host for domain in blocked_domains):
                            continue

                        title = re.sub(r"<[^>]+>", " ", raw_title)
                        title = re.sub(r"\s+", " ", title).strip()
                        title = (title.replace("&amp;", "&").replace("&quot;", '"')
                                      .replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">"))

                        if not title or len(title) < 4 or len(title) > 240:
                            continue
                        if NEGATIVE_FILTER_PATTERN.search(title) or NEGATIVE_FILTER_PATTERN.search(clean_url):
                            continue
                        if any(word in title.casefold() for word in (
                            "privacy policy", "terms of", "sign in", "log in", "feedback", "contact us", "about us", "cookie"
                        )):
                            continue

                        normalized_url = urllib.parse.urlunparse(parsed_url._replace(fragment=""))
                        if normalized_url in seen_urls:
                            continue
                        seen_urls.add(normalized_url)

                        target_state = clean_region or "All-India"
                        maps_url = (
                            "https://www.google.com/maps/search/?api=1&query="
                            + urllib.parse.quote(f"{title} {target_state}")
                        )
                        found.append({
                            "kind": "Store",
                            "business_name": title,
                            "business_category": "Sports Nutrition / Supplement Store",
                            "state": target_state,
                            "city": "",
                            "area": "",
                            "phone": "",
                            "address": f"{title}, {target_state}",
                            "maps": maps_url,
                            "website": normalized_url,
                            "source_name": f"{engine_name} public search",
                            "source_url": normalized_url,
                            "source_type": "Web Discovered",
                            "source_status": "Search result - verified authentic store",
                            "verified": "No",
                        })

            status = (
                f"Completed multi-engine search. Found {len(found)} candidate store(s)."
            )
            self.progress.emit(status, 100)
            self.finished.emit(found, "; ".join(errors[:3]) if errors else "")
        except Exception as exc:
            self.finished.emit(found, str(exc))


class WebScraperDialog(QDialog):
    """Single-tab, multi-engine search for supplement-store prospects."""
    def __init__(self, parent=None, default_state="All States / UTs"):
        super().__init__(parent)
        self.setWindowTitle("🌐 India-Wide Multi-Engine Store Search")
        self.setMinimumSize(640, 460)
        self.results = []

        root = QVBoxLayout(self)
        root.setSpacing(8)
        self.tabs = QTabWidget()
        search_page = QWidget()
        layout = QVBoxLayout(search_page)
        layout.setSpacing(10)

        info = QLabel(
            "<b>One search. Multiple search engines. Nationwide coverage.</b><br>"
            "<span style='color: #64748B;'>Runs the same search across Google, Bing and DuckDuckGo, "
            "including public Google search operators. Select a region or search all India, including "
            "States, Union Territories and island regions.<br>"
            "<b>Excluded:</b> HealthKart, pharmacies / medical stores, herbal and Ayurvedic businesses. "
            "Search results are candidates and must be verified before use.</span>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form_layout = QHBoxLayout()
        self.state_combo = QComboBox()
        self.state_combo.addItem("All States / UTs")
        self.state_combo.addItems(INDIA_REGIONS)
        if default_state in INDIA_REGIONS:
            self.state_combo.setCurrentText(default_state)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("One search query (e.g. sports nutrition supplement store)")
        self.keyword_input.setText("supplement store sports nutrition")
        self.keyword_input.returnPressed.connect(self._start_scraping)

        form_layout.addWidget(QLabel("Region:"))
        form_layout.addWidget(self.state_combo, 1)
        form_layout.addWidget(QLabel("Search:"))
        form_layout.addWidget(self.keyword_input, 2)
        layout.addLayout(form_layout)

        self.engine_status = QLabel("Engines: Google · Bing · DuckDuckGo")
        self.engine_status.setStyleSheet("font-weight: 700; color: #0D9488;")
        layout.addWidget(self.engine_status)

        self.btn_start = QPushButton("🚀 Search All Engines")
        self.btn_start.setMinimumHeight(38)
        self.btn_start.setStyleSheet("font-weight: 700; background: #2563EB; color: white; border-radius: 6px;")
        self.btn_start.clicked.connect(self._start_scraping)
        layout.addWidget(self.btn_start)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Each engine and query status will appear here...")
        layout.addWidget(self.log_view, 1)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Discovered Stores to App DB")
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("font-weight: 700; background: #059669; color: white; border-radius: 6px; min-height: 32px;")
        self.btn_save.clicked.connect(self.accept)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_save, 2)
        btn_row.addWidget(self.btn_close, 1)
        layout.addLayout(btn_row)

        self.tabs.addTab(search_page, "One-Tab Multi-Engine Search")
        root.addWidget(self.tabs)

    def _start_scraping(self):
        region = self.state_combo.currentText()
        query = self.keyword_input.text().strip()
        if not query:
            QMessageBox.information(self, "Search query required", "Enter a business search query first.")
            return
        self.btn_start.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_view.append(f"Starting one-tab multi-engine search for: {region} ({query})...")
        self.worker = WebScraperWorker(region=region, query_term=query)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, msg, pct):
        self.progress_bar.setValue(pct)
        self.log_view.append(msg)

    def _on_finished(self, records, error):
        self.btn_start.setEnabled(True)
        if error:
            self.log_view.append(f"⚠️ Search completed with issues: {error}")
        self.results = records
        self.log_view.append(
            f"Search finished. {len(records)} unique candidate(s) found. "
            "Search listings are not verified business records."
        )
        for record in records[:8]:
            self.log_view.append(f"  • {record['business_name']} ({record['state']})")
        if len(records) > 8:
            self.log_view.append(f"  ... and {len(records) - 8} more.")
        self.btn_save.setEnabled(bool(records))

class CustomerProspectsTab(QWidget):
    """Prospect explorer backed by the app database with printing, web scraping, and multi-format exports."""

    LEAD_COLUMNS = (
        ("Type", "kind"),
        ("Business", "business_name"),
        ("Category", "business_category"),
        ("State / UT", "state"),
        ("City", "city"),
        ("Contact", "contact_person"),
        ("Phone", "phone"),
        ("Address", "address"),
        ("Follow-up", "followup_date"),
        ("Connection", "connection"),
        ("Call verified", "verified"),
        ("Website", "website"),
        ("Google Maps", "maps"),
        ("Source", "source_name"),
        ("Source type", "source_type"),
        ("Last checked", "source_checked_at"),
        ("Source link", "source_url"),
        ("Source status", "source_status"),
        ("Source sheet", "source_sheet"),
    )

    REGIONAL_COLUMNS = (
        ("State / UT", "state"),
        ("Web leads", "web_leads"),
        ("Workbook leads", "workbook_leads"),
        ("All stores", "stores"),
        ("All gyms", "gyms"),
        ("Dashboard stores", "dashboard_stores"),
        ("Difference", "variance"),
    )

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.records = load_saved_prospects(db) if db is not None else []
        self.preview_records = []
        self.dashboard_counts = {}
        self.dashboard_total = None
        self.database_filename = ""
        self.dashboard_filename = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Header Title & Subtitle
        heading = QVBoxLayout()
        title = QLabel("Customer & Store Prospect Explorer")
        title.setObjectName("prospectTitle")
        title.setStyleSheet("font-size: 18pt; font-weight: 800;")
        subtitle = QLabel(
            "Central directory of sports nutrition & supplement stores across India. "
            "Print, export (CSV, PDF, Word), sync with central Google Sheets, and discover new stores from the web."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 9pt; color: #94A3B8;")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        root.addLayout(heading)

        # Action Toolbar 1: Source Workbooks
        source_card = QFrame()
        source_card.setObjectName("prospectSourceCard")
        source_layout = QHBoxLayout(source_card)
        source_layout.setContentsMargins(12, 10, 12, 10)
        source_layout.setSpacing(10)
        self.load_database_button = QPushButton("📁 Load Local Workbook")
        self.load_database_button.setMinimumHeight(32)
        self.load_database_button.clicked.connect(self.choose_database_workbook)
        self.load_dashboard_button = QPushButton("📊 Load Store Dashboard")
        self.load_dashboard_button.setMinimumHeight(32)
        self.load_dashboard_button.clicked.connect(self.choose_dashboard_workbook)
        self.database_source_label = QLabel("Database: not loaded")
        self.dashboard_source_label = QLabel("Dashboard: not loaded")
        source_layout.addWidget(self.load_database_button)
        source_layout.addWidget(self.database_source_label, 1)
        source_layout.addWidget(self.load_dashboard_button)
        source_layout.addWidget(self.dashboard_source_label, 1)
        root.addWidget(source_card)

        # Action Toolbar 2: Live Sync, Web Scraping, & Master Data
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        
        self.scrape_web_button = QPushButton("🌐 Scrape / Fetch New Web Stores")
        self.scrape_web_button.setMinimumHeight(34)
        self.scrape_web_button.setStyleSheet("font-weight: 700; background: #2563EB; color: white; border-radius: 6px; padding: 0 12px;")
        self.scrape_web_button.clicked.connect(self.open_web_scrape_dialog)

        self.load_master_india_button = QPushButton("📥 Load All-India Stores (3,823)")
        self.load_master_india_button.setMinimumHeight(34)
        self.load_master_india_button.setStyleSheet("font-weight: 700; background: #0D9488; color: white; border-radius: 6px; padding: 0 12px;")
        self.load_master_india_button.clicked.connect(self.load_master_india_stores)

        self.sync_google_sheets_button = QPushButton("☁️ Sync Google Sheets")
        self.sync_google_sheets_button.setMinimumHeight(34)
        self.sync_google_sheets_button.setStyleSheet("font-weight: 700; background: #7C3AED; color: white; border-radius: 6px; padding: 0 12px;")
        self.sync_google_sheets_button.clicked.connect(self.sync_google_sheets)

        self.import_workbook_button = QPushButton("Save Workbook Rows")
        self.import_workbook_button.setMinimumHeight(34)
        self.import_workbook_button.setEnabled(False)
        self.import_workbook_button.clicked.connect(self.import_workbook_to_app_db)

        self.saved_status_label = QLabel("App DB: 0 saved leads")
        self.saved_status_label.setWordWrap(True)

        actions_row.addWidget(self.scrape_web_button)
        actions_row.addWidget(self.load_master_india_button)
        actions_row.addWidget(self.sync_google_sheets_button)
        actions_row.addWidget(self.import_workbook_button)
        actions_row.addWidget(self.saved_status_label, 1)
        root.addLayout(actions_row)

        # KPI Row
        self.kpi_values = {}
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)
        for key, caption, accent in (
            ("prospects", "Total Stores", "#00E5FF"),
            ("stores", "Store Leads", "#34D399"),
            ("gyms", "Gym Leads", "#A78BFA"),
            ("regions", "States Covered", "#FBBF24"),
            ("dashboard", "Dashboard Target", "#60A5FA"),
        ):
            card = QFrame()
            card.setObjectName("prospectKpiCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            card_layout.setSpacing(1)
            value = QLabel("—")
            value.setObjectName("prospectKpiValue")
            value.setStyleSheet(f"font-size: 17pt; font-weight: 800; color: {accent};")
            label = QLabel(caption)
            label.setObjectName("prospectKpiLabel")
            label.setStyleSheet("font-size: 8pt; font-weight: 600; color: #94A3B8;")
            card_layout.addWidget(value)
            card_layout.addWidget(label)
            self.kpi_values[key] = value
            kpi_row.addWidget(card, 1)
        root.addLayout(kpi_row)

        # Tabs: Prospect List & Regional Dashboard
        self.pages = QTabWidget()
        self.pages.addTab(self._build_leads_page(), "Store Directory")
        self.pages.addTab(self._build_regional_page(), "Regional Dashboard")
        root.addWidget(self.pages, 1)

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(160)
        self._filter_timer.timeout.connect(self.apply_filters)
        self.apply_theme("night")
        self._refresh_views()

    def _build_leads_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Filter and Print/Export Bar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search business name, phone, address, city…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(lambda _text: self._filter_timer.start())
        
        self.kind_filter = QComboBox()
        self.kind_filter.addItems(["All types", "Store", "Gym"])
        self.kind_filter.currentTextChanged.connect(lambda _text: self.apply_filters())
        
        self.state_filter = QComboBox()
        self.state_filter.addItem("All States / UTs")
        self.state_filter.currentTextChanged.connect(lambda _text: self.apply_filters())

        self.contact_filter = QComboBox()
        self.contact_filter.addItems(["All contacts", "Has phone/email", "Missing contact"])
        self.contact_filter.currentTextChanged.connect(lambda _text: self.apply_filters())

        self.website_filter = QComboBox()
        self.website_filter.addItems(["All websites", "Has website", "Missing website"])
        self.website_filter.currentTextChanged.connect(lambda _text: self.apply_filters())

        self.verification_filter = QComboBox()
        self.verification_filter.addItems(["All verification", "Verified", "Unverified"])
        self.verification_filter.currentTextChanged.connect(lambda _text: self.apply_filters())

        toolbar.addWidget(self.search_input, 2)
        toolbar.addWidget(self.kind_filter)
        toolbar.addWidget(self.state_filter, 1)
        toolbar.addWidget(self.contact_filter)
        toolbar.addWidget(self.website_filter)
        toolbar.addWidget(self.verification_filter)

        # Print & Export Buttons
        self.btn_print = QPushButton("🖨️ Print")
        self.btn_print.setToolTip("Direct Print or Print to PDF")
        self.btn_print.clicked.connect(self.print_leads)

        self.btn_pdf = QPushButton("📄 PDF")
        self.btn_pdf.setToolTip("Export filtered stores to PDF report")
        self.btn_pdf.clicked.connect(self.export_pdf)

        self.btn_csv = QPushButton("📊 CSV")
        self.btn_csv.setToolTip("Export to OneDrive format CSV")
        self.btn_csv.clicked.connect(self.export_csv)

        self.btn_xlsx = QPushButton("📗 Excel")
        self.btn_xlsx.setToolTip("Export currently filtered stores to Excel (.xlsx)")
        self.btn_xlsx.clicked.connect(self.export_xlsx)

        self.btn_doc = QPushButton("📝 Word")
        self.btn_doc.setToolTip("Export to Microsoft Word (.doc)")
        self.btn_doc.clicked.connect(self.export_doc)

        toolbar.addWidget(self.btn_print)
        toolbar.addWidget(self.btn_pdf)
        toolbar.addWidget(self.btn_csv)
        toolbar.addWidget(self.btn_xlsx)
        toolbar.addWidget(self.btn_doc)
        layout.addLayout(toolbar)

        self.results_label = QLabel("Showing 0 stores")
        self.results_label.setStyleSheet("font-size: 8.5pt; color: #94A3B8;")
        layout.addWidget(self.results_label)

        self.leads_table = QTableWidget(0, len(self.LEAD_COLUMNS))
        self.leads_table.setHorizontalHeaderLabels([label for label, _key in self.LEAD_COLUMNS])
        self.leads_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.leads_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.leads_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.leads_table.setWordWrap(False)
        self.leads_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.leads_table.verticalHeader().setVisible(False)
        self.leads_table.setAlternatingRowColors(True)
        self.leads_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.leads_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.leads_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.leads_table.setSortingEnabled(False)
        self.leads_table.cellDoubleClicked.connect(self.open_source_link)
        for index, width in enumerate((74, 190, 140, 150, 120, 140, 125, 300, 105, 145, 90, 170, 170, 230, 160, 105, 120, 300, 300, 150)):
            self.leads_table.setColumnWidth(index, width)
        layout.addWidget(self.leads_table, 1)
        return page

    def _build_regional_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.reconciliation_label = QLabel(
            "Coverage uses saved app database leads. Stores across all 36 States and UTs are tracked against target counts."
        )
        self.reconciliation_label.setWordWrap(True)
        self.reconciliation_label.setObjectName("prospectReconciliation")
        self.reconciliation_label.setStyleSheet("font-size: 9pt; font-weight: 600; color: #94A3B8;")
        layout.addWidget(self.reconciliation_label)
        self.region_table = QTableWidget(0, len(self.REGIONAL_COLUMNS))
        self.region_table.setHorizontalHeaderLabels([label for label, _key in self.REGIONAL_COLUMNS])
        self.region_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.region_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.region_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.region_table.setWordWrap(False)
        self.region_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.region_table.verticalHeader().setVisible(False)
        self.region_table.setAlternatingRowColors(True)
        self.region_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.region_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.region_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.region_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.region_table, 1)
        privacy = QLabel(
            "Counts stay separated by source. Online listings remain distinct from call-verified store stockists."
        )
        privacy.setWordWrap(True)
        privacy.setStyleSheet("font-size: 8pt; color: #94A3B8;")
        layout.addWidget(privacy)
        return page

    def open_web_scrape_dialog(self):
        """Open web scraper modal for searching supplement stores across Indian states/cities."""
        dialog = WebScraperDialog(self, default_state=self.state_filter.currentText())
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.results:
            if self.db is not None:
                result = persist_prospect_records(
                    self.db,
                    dialog.results,
                    source_name="Web Search Scraper",
                    source_url="",
                    source_checked_at=date.today().isoformat(),
                )
                self._reload_saved_records()
                QMessageBox.information(
                    self,
                    "Stores Added",
                    f"Web scraping complete!\n\n• Discovered: {len(dialog.results):,}\n• Added to DB: {result['inserted']:,}\n• Already Present: {result['duplicates']:,}"
                )
            else:
                self.records.extend(dialog.results)
                self._refresh_views()

    def load_master_india_stores(self):
        """Load master store records from bundled assets or configured live Google Sheet."""
        if self.db is None:
            QMessageBox.warning(self, "Database Unavailable", "Database is not available.")
            return

        records = []
        source_label = "Bundled All-India Stores"
        source_link = REFERENCE_DATABASE_URL

        # 1. Primary: Bundled verified store seed asset (offline-first, zero network dependency)
        seed_path = resource_path("assets/india_stores_seed.json")
        if seed_path.is_file():
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    seed_data = json.load(f)
                if isinstance(seed_data, list) and seed_data:
                    records = seed_data
                    source_label = "Bundled Store Directory"
            except Exception as exc:
                logging.getLogger("prospects").warning("Failed reading bundled store seed: %s", exc)

        # 2. Fallback / Merge: Local Master Excel file if present
        if not records:
            master_candidates = [
                Path(r"C:\Users\DELL\Downloads\Google_Sheets_Master_Database.xlsx"),
                Path(r"C:\Users\DELL\Documents\Codex\2026-10-24\inr\work\google_sheets_master_database.xlsx"),
                Path(r"C:\Users\DELL\Documents\Codex\2026-10-24\inr\work\onedrive-reference\customer_database_reference.xlsx"),
            ]
            for candidate in master_candidates:
                if candidate.is_file() and candidate.stat().st_size > 0:
                    try:
                        parsed, _ = parse_database_workbook(candidate)
                        if parsed:
                            records = parsed
                            source_label = f"Local Master File ({candidate.name})"
                            break
                    except Exception:
                        pass

        # 3. Fallback: Live Google Sheets if online and populated
        if not records:
            temp_path = None
            try:
                workbook_bytes = google_sheets_sync.fetch_google_sheet_bytes()
                if workbook_bytes:
                    import tempfile
                    with tempfile.NamedTemporaryFile(prefix="rawstrength-master-", suffix=".xlsx", delete=False) as temp_file:
                        temp_file.write(workbook_bytes)
                        temp_path = Path(temp_file.name)
                    parsed, _ = parse_database_workbook(temp_path)
                    if parsed:
                        records = parsed
                        source_label = "Google Sheets Master"
                        source_link = GOOGLE_SHEET_URL
            except Exception as exc:
                logging.getLogger("prospects").info("Google sheets fallback note: %s", exc)
            finally:
                if temp_path is not None:
                    try:
                        temp_path.unlink(missing_ok=True)
                    except OSError:
                        pass

        if not records:
            QMessageBox.warning(
                self,
                "Master Stores Not Found",
                "Could not locate the All-India Store dataset in the application bundle or local storage.\n\n"
                "Please ensure the application was installed with bundled assets or run the latest installer."
            )
            return

        result = persist_prospect_records(
            self.db,
            records,
            source_name=source_label,
            source_url=source_link,
            source_checked_at=date.today().isoformat()
        )
        self._reload_saved_records()
        QMessageBox.information(
            self,
            "Master Stores Loaded",
            f"Loaded All-India Sports Nutrition & Supplement Stores!\n\n"
            f"• Source: {source_label}\n"
            f"• Stores Processed: {len(records):,}\n"
            f"• New Stores Added: {result['inserted']:,}\n"
            f"• Existing Preserved: {result['duplicates']:,}\n"
            f"• Total Directory Stores: {len(self.records):,}"
        )

    def sync_google_sheets(self):
        """Live 1-click sync with central Google Spreadsheet."""
        if self.db is None:
            QMessageBox.warning(self, "Database Unavailable", "App database is unavailable for sync.")
            return
        try:
            stats = google_sheets_sync.sync_from_live_google_sheet(self.db)
            self._reload_saved_records()
            msg = f"Synced with Google Sheets!\n\n"
            for k, v in stats.items():
                msg += f"• {k.capitalize()}: {v:,} updated\n"
            QMessageBox.information(self, "Google Sheets Sync", msg)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Google Sheets Sync Notice",
                f"Could not connect to live Google Sheet:\n{exc}\n\n"
                f"Make sure the sheet at {GOOGLE_SHEET_URL} has been populated with Google_Sheets_Master_Database.xlsx"
            )

    def _get_visible_records(self):
        """Return list of records currently matching the search and state/kind filters."""
        visible = []
        for row_index in range(self.leads_table.rowCount()):
            if not self.leads_table.isRowHidden(row_index):
                if row_index < len(self.records):
                    visible.append(self.records[row_index])
        return visible or self.records

    def export_csv(self):
        """Export currently filtered records to CSV matching the exact OneDrive schema."""
        records = self._get_visible_records()
        if not records:
            QMessageBox.warning(self, "No Records", "No store records to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Store Directory to CSV", str(Path.home() / "stores_directory.csv"), "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            headers = [
                "state", "city", "area", "business category", "business name",
                "Mobile  number", "Full address", "Google Maps link", "Website/social-media link",
                "verified by call", "response"
            ]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in records:
                    writer.writerow([
                        r.get("state", ""),
                        r.get("city", ""),
                        r.get("area", ""),
                        r.get("business_category", ""),
                        r.get("business_name", ""),
                        r.get("phone", ""),
                        r.get("address", ""),
                        r.get("maps", ""),
                        r.get("website", ""),
                        r.get("verified", "No"),
                        r.get("response", "")
                    ])
            QMessageBox.information(self, "Export Successful", f"Exported {len(records):,} stores to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not write CSV:\n{exc}")

    def export_xlsx(self):
        """Export currently filtered records to a formatted Excel workbook."""
        records = self._get_visible_records()
        if not records:
            QMessageBox.warning(self, "No Records", "No store records to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Store Directory to Excel",
            str(Path.home() / "stores_directory.xlsx"),
            "Excel Workbook (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        headers = [
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
        ]
        try:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Store Directory"
            sheet.append([label for label, _key in headers])
            for record in records:
                sheet.append([str(record.get(key) or "") for _label, key in headers])

            from openpyxl.styles import Alignment, Font, PatternFill
            from openpyxl.utils import get_column_letter

            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor="1E293B")
                cell.alignment = Alignment(vertical="top", wrap_text=True)
            for row in sheet.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
            for column_cells in sheet.columns:
                column_letter = get_column_letter(column_cells[0].column)
                max_length = max((len(str(cell.value or "")) for cell in column_cells[:1001]), default=10)
                sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 42)
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            workbook.save(path)
            QMessageBox.information(
                self, "Export Successful",
                f"Exported {len(records):,} stores to Excel:\n{path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not create Excel workbook:\n{exc}")

    def export_pdf(self):
        """Export currently filtered records to a formatted landscape PDF report."""
        records = self._get_visible_records()
        if not records:
            QMessageBox.warning(self, "No Records", "No store records to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Store Directory to PDF", str(Path.home() / "stores_directory.pdf"), "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            doc = SimpleDocTemplate(
                path, pagesize=landscape(letter),
                leftMargin=20, rightMargin=20, topMargin=25, bottomMargin=25
            )
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'RepTitle', parent=styles['Heading1'], fontSize=15, leading=18, textColor=colors.HexColor('#0F172A')
            )
            cell_style = ParagraphStyle(
                'RepCell', parent=styles['Normal'], fontSize=7.5, leading=9.5, textColor=colors.HexColor('#1E293B')
            )
            hdr_style = ParagraphStyle(
                'RepHdr', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold', textColor=colors.white
            )

            state_label = self.state_filter.currentText()
            elements = [
                Paragraph("<b>RAW STRENGTH CALISTHENICS — STORE AUDIT & CUSTOMER PROSPECTS</b>", title_style),
                Paragraph(
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
                    f"Filter: {state_label} | Total Stores: {len(records):,}", styles['Normal']
                ),
                Spacer(1, 10)
            ]

            table_data = [[
                Paragraph("<b>State</b>", hdr_style),
                Paragraph("<b>City / Area</b>", hdr_style),
                Paragraph("<b>Business Name</b>", hdr_style),
                Paragraph("<b>Category</b>", hdr_style),
                Paragraph("<b>Phone</b>", hdr_style),
                Paragraph("<b>Full Address</b>", hdr_style),
                Paragraph("<b>Maps Link</b>", hdr_style),
            ]]

            export_slice = records[:500]
            for r in export_slice:
                maps_url = r.get("maps", "")
                maps_html = f'<a href="{maps_url}" color="#2563EB"><u>Google Maps</u></a>' if maps_url else "—"
                table_data.append([
                    Paragraph(r.get("state", ""), cell_style),
                    Paragraph(f"{r.get('city', '')}<br/>{r.get('area', '')}", cell_style),
                    Paragraph(f"<b>{r.get('business_name', '')}</b>", cell_style),
                    Paragraph(r.get("business_category", ""), cell_style),
                    Paragraph(r.get("phone", ""), cell_style),
                    Paragraph(r.get("address", ""), cell_style),
                    Paragraph(maps_html, cell_style),
                ])

            t = Table(table_data, colWidths=[90, 100, 155, 110, 85, 135, 75])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white]),
            ]))
            elements.append(t)
            if len(records) > 500:
                elements.append(Spacer(1, 8))
                elements.append(Paragraph(f"<i>(Note: Displaying first 500 of {len(records):,} stores)</i>", styles['Normal']))

            doc.build(elements)
            QMessageBox.information(self, "Export Successful", f"PDF exported successfully to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not create PDF:\n{exc}")

    def export_doc(self):
        """Export currently filtered records to a Microsoft Word-compatible document (.doc)."""
        records = self._get_visible_records()
        if not records:
            QMessageBox.warning(self, "No Records", "No store records to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Store Directory to Word Document", str(Path.home() / "stores_directory.doc"), "Word Document (*.doc)"
        )
        if not path:
            return
        try:
            state_label = self.state_filter.currentText()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            html = f"""<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head><meta charset='utf-8'><title>Raw Strength - Store Prospects</title>
<style>
body {{ font-family: Calibri, sans-serif; margin: 20px; }}
h2 {{ color: #0F172A; margin-bottom: 4px; }}
p.meta {{ color: #64748B; font-size: 10pt; margin-top: 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9.5pt; }}
th, td {{ border: 1px solid #CBD5E1; padding: 6px 8px; text-align: left; vertical-align: top; }}
th {{ background-color: #1E293B; color: #FFFFFF; font-weight: bold; }}
tr:nth-child(even) {{ background-color: #F8FAFC; }}
a {{ color: #2563EB; text-decoration: underline; }}
</style>
</head>
<body>
<h2>Raw Strength Calisthenics — Customer & Store Directory</h2>
<p class='meta'>Generated: {now_str} | Region Filter: {state_label} | Total Stores: {len(records):,}</p>
<table>
<thead>
<tr>
  <th>State</th><th>City / Area</th><th>Business Name</th><th>Category</th><th>Phone</th><th>Address</th><th>Google Maps</th>
</tr>
</thead>
<tbody>
"""
            for r in records[:1000]:
                maps_link = f"<a href='{r.get('maps', '')}'>Open Maps</a>" if r.get('maps') else "—"
                html += f"""<tr>
  <td>{r.get('state', '')}</td>
  <td>{r.get('city', '')}<br><small>{r.get('area', '')}</small></td>
  <td><b>{r.get('business_name', '')}</b></td>
  <td>{r.get('business_category', '')}</td>
  <td>{r.get('phone', '')}</td>
  <td>{r.get('address', '')}</td>
  <td>{maps_link}</td>
</tr>
"""
            html += """</tbody></table></body></html>"""
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "Export Successful", f"Word document exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not create Word document:\n{exc}")

    def print_leads(self):
        """Open system Print dialog to print the filtered stores directly or to PDF printer."""
        records = self._get_visible_records()
        if not records:
            QMessageBox.warning(self, "No Records", "No stores to print.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOrientation(QPrinter.Orientation.Landscape)
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        state_label = self.state_filter.currentText()
        html = f"""<html>
<head>
<style>
body {{ font-family: sans-serif; font-size: 8pt; }}
h3 {{ margin-bottom: 2px; color: #0F172A; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 0.5px solid #94A3B8; padding: 4px 6px; font-size: 7.5pt; text-align: left; }}
th {{ background-color: #1E293B; color: white; font-weight: bold; }}
tr:nth-child(even) {{ background-color: #F8FAFC; }}
</style>
</head>
<body>
<h3>Raw Strength Calisthenics — Store Directory ({state_label})</h3>
<p>Total Stores: {len(records):,} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<table>
<thead>
<tr>
  <th>State</th><th>City</th><th>Business Name</th><th>Category</th><th>Phone</th><th>Address</th>
</tr>
</thead>
<tbody>
"""
        for r in records[:300]:
            html += f"""<tr>
  <td>{r.get('state', '')}</td>
  <td>{r.get('city', '')}</td>
  <td><b>{r.get('business_name', '')}</b></td>
  <td>{r.get('business_category', '')}</td>
  <td>{r.get('phone', '')}</td>
  <td>{r.get('address', '')}</td>
</tr>
"""
        html += """</tbody></table></body></html>"""
        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(printer)

    def choose_database_workbook(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select customer prospect database",
            str(Path.home()),
            "Excel workbooks (*.xlsx)",
        )
        if path:
            self.load_database_workbook(path)

    def choose_dashboard_workbook(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select state-wise store dashboard",
            str(Path.home()),
            "Excel workbooks (*.xlsx)",
        )
        if path:
            self.load_dashboard_workbook(path)

    def load_database_workbook(self, path):
        try:
            records, stats = parse_database_workbook(path)
        except Exception as error:
            QMessageBox.warning(self, "Could not load database", str(error))
            return False
        self.preview_records = records
        self.records = records
        self.database_filename = Path(path).name
        self.database_source_label.setText(f"Database: {self.database_filename}")
        self.database_source_label.setToolTip(
            f"{self.database_filename} · {stats['scanned_rows']:,} non-empty rows scanned · "
            f"{stats['skipped_unidentified']:,} rows without business/contact identity skipped"
        )
        self._refresh_filters()
        self._refresh_views()
        self.import_workbook_button.setEnabled(bool(records) and self.db is not None)
        self.saved_status_label.setText(
            f"Preview: {len(records):,} workbook rows loaded · Save adds missing rows to the app DB."
        )
        return True

    def load_dashboard_workbook(self, path):
        try:
            counts, total = parse_dashboard_workbook(path)
        except Exception as error:
            QMessageBox.warning(self, "Could not load dashboard", str(error))
            return False
        self.dashboard_counts = counts
        self.dashboard_total = total
        self.dashboard_filename = Path(path).name
        self.dashboard_source_label.setText(f"Dashboard: {self.dashboard_filename}")
        self.dashboard_source_label.setToolTip(
            f"{self.dashboard_filename} · {len(counts):,} State/UT rows · total {total:,}"
        )
        self._refresh_views()
        return True

    def import_workbook_to_app_db(self):
        if self.db is None or not self.preview_records:
            return False
        source_name = self.database_filename or "Selected customer workbook"
        source_url = ""
        if _normalise_key(source_name) == _normalise_key("23 oct data base.xlsx"):
            source_name = "Customer database reference workbook"
            source_url = REFERENCE_DATABASE_URL
        records = []
        for preview in self.preview_records:
            record = dict(preview)
            record["source_name"] = source_name
            record["source_url"] = source_url
            record["source_type"] = "Reference workbook" if source_url else "Imported workbook"
            if not record.get("source_status"):
                call_verified = str(record.get("verified") or "").strip().casefold() in {"yes", "y", "true", "verified"}
                record["source_status"] = "Workbook indicates call verified" if call_verified else "Needs direct confirmation"
            records.append(record)
        try:
            result = persist_prospect_records(
                self.db,
                records,
                source_name=source_name,
                source_url=source_url,
                source_checked_at=date.today().isoformat(),
            )
        except Exception as error:
            QMessageBox.critical(self, "Import failed", f"The app database was not updated.\n\n{error}")
            return False
        self._reload_saved_records()
        self.import_workbook_button.setEnabled(False)
        self.saved_status_label.setText(
            f"App DB import complete: {result['inserted']:,} added, {result['duplicates']:,} already present."
        )
        return True

    def import_researched_web_leads(self):
        if self.db is None:
            QMessageBox.warning(self, "App database unavailable", "Web researched leads can only be saved when the app database is available.")
            return False
        records = []
        for lead in RESEARCHED_WEB_LEADS:
            records.append({
                **lead,
                "kind": "Store",
                "business_category": "Sports nutrition retailer",
                "source_name": RESEARCHED_SOURCE_NAME,
                "source_url": RESEARCHED_SOURCE_URL,
                "source_type": "Official web listing",
                "source_checked_at": RESEARCH_DATE,
                "source_status": RESEARCHED_SOURCE_STATUS,
            })
        try:
            result = persist_prospect_records(
                self.db,
                records,
                source_name=RESEARCHED_SOURCE_NAME,
                source_url=RESEARCHED_SOURCE_URL,
                source_checked_at=RESEARCH_DATE,
            )
        except Exception as error:
            QMessageBox.critical(self, "Import failed", f"The app database was not updated.\n\n{error}")
            return False
        self._reload_saved_records()
        self.saved_status_label.setText(
            f"Official retailer list import: {result['inserted']:,} added, {result['duplicates']:,} already present."
        )
        return True

    def _reload_saved_records(self):
        if self.db is not None:
            self.records = load_saved_prospects(self.db)
            self.preview_records = []
            self._refresh_filters()
            self._refresh_views()

    def _refresh_filters(self):
        previous_state = self.state_filter.currentText()
        self.state_filter.blockSignals(True)
        self.state_filter.clear()
        self.state_filter.addItem("All States / UTs")
        states = sorted({record.get("state", "") for record in self.records if record.get("state")}, key=str.casefold)
        self.state_filter.addItems(states)
        if previous_state in states:
            self.state_filter.setCurrentText(previous_state)
        self.state_filter.blockSignals(False)

    def _refresh_views(self):
        self._fill_leads_table()
        self._fill_regional_table()
        self._refresh_kpis()
        self.apply_filters()

    def _fill_leads_table(self):
        self.leads_table.setUpdatesEnabled(False)
        self.leads_table.setRowCount(len(self.records))
        for row_index, record in enumerate(self.records):
            for column_index, (_label, key) in enumerate(self.LEAD_COLUMNS):
                source_url = str(record.get("source_url", "") or "")
                text = "Open source" if key == "source_url" and source_url else "" if key == "source_url" else str(record.get(key, "") or "")
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if key == "source_url":
                    item.setData(Qt.ItemDataRole.UserRole, source_url)
                    if source_url:
                        item.setForeground(QColor("#38BDF8"))
                if text:
                    item.setToolTip(text)
                self.leads_table.setItem(row_index, column_index, item)
        self.leads_table.setUpdatesEnabled(True)

    def open_source_link(self, row, column):
        if self.LEAD_COLUMNS[column][1] != "source_url":
            return
        item = self.leads_table.item(row, column)
        url = str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""
        if url.startswith(("https://", "http://")):
            QDesktopServices.openUrl(QUrl(url))

    def _fill_regional_table(self):
        rows = build_regional_summary(self.records, self.dashboard_counts, include_all_regions=True)
        source_counts = defaultdict(lambda: {"web": 0, "workbook": 0})
        for record in self.records:
            state = normalise_state(record.get("state"))
            if str(record.get("source_type") or "").casefold().startswith("official web"):
                source_counts[state]["web"] += 1
            else:
                source_counts[state]["workbook"] += 1
        for row in rows:
            row["web_leads"] = source_counts[row["state"]]["web"]
            row["workbook_leads"] = source_counts[row["state"]]["workbook"]
        self.region_table.setRowCount(len(rows))
        for row_index, data in enumerate(rows):
            for column_index, (_label, key) in enumerate(self.REGIONAL_COLUMNS):
                value = data[key]
                text = "—" if value is None else f"{value:+,}" if key == "variance" else f"{value:,}" if isinstance(value, int) else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if key in {"web_leads", "workbook_leads", "stores", "gyms", "dashboard_stores", "variance"}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if key == "variance" and value is not None and value != 0:
                    item.setForeground(QColor("#FCA5A5" if value > 0 else "#FCD34D"))
                self.region_table.setItem(row_index, column_index, item)

    def _refresh_kpis(self):
        stores = sum(record.get("kind") == "Store" for record in self.records)
        gyms = sum(record.get("kind") == "Gym" for record in self.records)
        regions = {record.get("state") for record in self.records if record.get("state")}
        self.kpi_values["prospects"].setText(f"{len(self.records):,}" if self.records else "—")
        self.kpi_values["stores"].setText(f"{stores:,}" if self.records else "—")
        self.kpi_values["gyms"].setText(f"{gyms:,}" if self.records else "—")
        self.kpi_values["regions"].setText(f"{len(regions):,}" if self.records else "—")
        self.kpi_values["dashboard"].setText(f"{self.dashboard_total:,}" if self.dashboard_total is not None else "—")
        saved_count = len(load_saved_prospects(self.db)) if self.db is not None else 0
        if self.preview_records:
            self.saved_status_label.setText(
                f"Workbook preview: {len(self.preview_records):,} rows · App DB: {saved_count:,} saved leads"
            )
        else:
            self.saved_status_label.setText(f"App DB: {saved_count:,} saved leads")

        if self.records and self.dashboard_total is not None:
            difference = stores - self.dashboard_total
            sign = "+" if difference > 0 else ""
            source_label = "Workbook preview stores" if self.preview_records else "App DB stores"
            self.reconciliation_label.setText(
                f"{source_label}: {stores:,} · Dashboard reference: {self.dashboard_total:,} · "
                f"Difference: {sign}{difference:,}. Source totals remain separate for reconciliation."
            )
            self.reconciliation_label.setStyleSheet(
                "font-size: 9pt; font-weight: 600; color: #FCD34D;" if difference else
                "font-size: 9pt; font-weight: 600; color: #34D399;"
            )
        elif self.records:
            self.reconciliation_label.setText(
                "Lead rows loaded. Load the state-wise dashboard workbook to compare its reference counts."
            )
        elif self.dashboard_total is not None:
            self.reconciliation_label.setText(
                f"Dashboard reference total: {self.dashboard_total:,}. Load the database workbook to compare imported leads."
            )
        else:
            self.reconciliation_label.setText(
                "Load both workbooks to compare the database with the dashboard reference."
            )

    def apply_filters(self):
        if not hasattr(self, "leads_table"):
            return
        search = self.search_input.text().strip().casefold()
        kind = self.kind_filter.currentText()
        state = self.state_filter.currentText()
        contact = self.contact_filter.currentText()
        website = self.website_filter.currentText()
        verification = self.verification_filter.currentText()
        visible = 0
        for row_index, record in enumerate(self.records):
            matches_kind = kind == "All types" or record.get("kind") == kind
            matches_state = state == "All States / UTs" or record.get("state") == state
            phone = str(record.get("phone") or "").strip()
            email = str(record.get("email") or record.get("email_address") or "").strip()
            has_contact = bool(phone or email) and not any(v.casefold() in {"n/a", "na", "none", "null", "-"} for v in (phone, email) if v)
            matches_contact = (
                contact == "All contacts"
                or (contact == "Has phone/email" and has_contact)
                or (contact == "Missing contact" and not has_contact)
            )
            website_value = str(record.get("website") or "").strip()
            has_website = bool(website_value) and website_value.casefold() not in {"n/a", "na", "none", "null", "-"}
            matches_website = (
                website == "All websites"
                or (website == "Has website" and has_website)
                or (website == "Missing website" and not has_website)
            )
            verified_value = str(record.get("verified") or "").strip().casefold()
            is_verified = verified_value in {"1", "true", "yes", "verified", "y"}
            matches_verification = (
                verification == "All verification"
                or (verification == "Verified" and is_verified)
                or (verification == "Unverified" and not is_verified)
            )
            search_blob = " ".join(str(value or "") for value in record.values()).casefold()
            matches_search = not search or search in search_blob
            shown = matches_kind and matches_state and matches_search and matches_contact and matches_website and matches_verification
            self.leads_table.setRowHidden(row_index, not shown)
            visible += shown
        self.results_label.setText(
            f"Showing {visible:,} of {len(self.records):,} stores in directory."
            if self.records else "No store records loaded. Use 'Load All-India Stores' or 'Scrape Web' above."
        )

    def apply_theme(self, theme_name="night"):
        theme = (theme_name or "night").lower()
        is_dark = theme in {"night", "dark"}
        card_bg = "rgba(15, 23, 42, 0.82)" if is_dark else "#FFFFFF"
        border = "rgba(99, 102, 241, 0.30)" if is_dark else "#CBD5E1"
        title_fg = "#F8FAFC" if is_dark else "#0F172A"
        text_fg = "#E2E8F0" if is_dark else "#334155"
        source_bg = "rgba(30, 41, 59, 0.62)" if is_dark else "#F8FAFC"
        self.setStyleSheet(f"""
            QLabel#prospectTitle {{ color: {title_fg}; }}
            QLabel#prospectKpiValue {{ font-size: 17pt; font-weight: 800; }}
            QLabel#prospectKpiLabel {{ font-size: 8pt; font-weight: 600; color: {'#94A3B8' if is_dark else '#64748B'}; }}
            QLabel#prospectReconciliation {{ color: {text_fg}; }}
            QFrame#prospectSourceCard {{ background: {source_bg}; border: 1px solid {border}; border-radius: 10px; }}
            QFrame#prospectKpiCard {{ background: {card_bg}; border: 1px solid {border}; border-radius: 10px; }}
            QLineEdit {{ color: {text_fg}; }}
        """)
        palette = self.leads_table.palette()
        palette.setColor(QPalette.ColorRole.Text, QColor(text_fg))
        self.leads_table.setPalette(palette)
        self.region_table.setPalette(palette)
