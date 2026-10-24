"""Read-only explorer for locally downloaded customer/prospect workbooks."""
from collections import defaultdict
from datetime import date, datetime, time
import hashlib
from pathlib import Path
import re

from openpyxl import load_workbook
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


MAX_WORKBOOK_BYTES = 50 * 1024 * 1024
REFERENCE_DATABASE_URL = "https://1drv.ms/x/c/a3aac0512044da6f/IQCll6KW063nQ6A_EUwZ1VPyAWg0BN-FsAmoYwawsnUKH40?e=hIJA3x"
REFERENCE_DASHBOARD_URL = "https://1drv.ms/x/c/a3aac0512044da6f/IQC7OF8bQj_7Q4pEOyu30GJHATIgpGZ2HMWlX7cXkTWduZc?e=Hby1MO"
RESEARCH_DATE = "2026-10-24"

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
    # Some sheets use names such as "Delhi NCR" or include a category suffix.
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
                # Repeated follow-up columns are common in these sheets; keep the
                # rightmost non-empty value for those fields and first value for identity.
                for field, value in zip(fields, values):
                    if not field:
                        continue
                    text = _cell_text(value)
                    if text and (not record[field] or field in {"followup_date", "call_time", "connection", "verified", "response"}):
                        record[field] = text
                if not any(record[field] for field in ("business_name", "phone", "address")):
                    skipped_unidentified += 1
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


def seed_official_web_prospects(db):
    """One-time, idempotent local seed of brand-listed retailer leads."""
    setting = "customer_prospects_official_web_seed_20261024"
    if db.get_setting(setting) == "1":
        return {"inserted": 0, "duplicates": 0}
    records = [
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
    ]
    result = persist_prospect_records(
        db,
        records,
        source_name=RESEARCHED_SOURCE_NAME,
        source_url=RESEARCHED_SOURCE_URL,
        source_checked_at=RESEARCH_DATE,
    )
    db.set_setting(setting, "1")
    return result


class CustomerProspectsTab(QWidget):
    """Prospect explorer backed by the app database; source workbooks stay read-only."""

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

        heading = QVBoxLayout()
        title = QLabel("Customer & Prospect Explorer")
        title.setObjectName("prospectTitle")
        title.setStyleSheet("font-size: 18pt; font-weight: 800;")
        subtitle = QLabel(
            "Keep store and gym prospects in the app database with a source link and review date. "
            "The shared OneDrive workbooks are only read during import; this tab never edits them."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 9pt; color: #94A3B8;")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        root.addLayout(heading)

        source_card = QFrame()
        source_card.setObjectName("prospectSourceCard")
        source_layout = QHBoxLayout(source_card)
        source_layout.setContentsMargins(12, 10, 12, 10)
        source_layout.setSpacing(10)
        self.load_database_button = QPushButton("Load Prospect Database")
        self.load_database_button.setMinimumHeight(36)
        self.load_database_button.clicked.connect(self.choose_database_workbook)
        self.load_dashboard_button = QPushButton("Load Store Dashboard")
        self.load_dashboard_button.setMinimumHeight(36)
        self.load_dashboard_button.clicked.connect(self.choose_dashboard_workbook)
        self.database_source_label = QLabel("Database: not loaded")
        self.dashboard_source_label = QLabel("Dashboard: not loaded")
        self.database_source_label.setToolTip("No workbook is stored by this tab.")
        self.dashboard_source_label.setToolTip("No workbook is stored by this tab.")
        source_layout.addWidget(self.load_database_button)
        source_layout.addWidget(self.database_source_label, 1)
        source_layout.addWidget(self.load_dashboard_button)
        source_layout.addWidget(self.dashboard_source_label, 1)
        root.addWidget(source_card)

        import_row = QHBoxLayout()
        self.import_workbook_button = QPushButton("Save Loaded Workbook Rows to App DB")
        self.import_workbook_button.setMinimumHeight(36)
        self.import_workbook_button.setEnabled(False)
        self.import_workbook_button.clicked.connect(self.import_workbook_to_app_db)
        self.import_web_button = QPushButton("Add Official Retailer Leads to App DB")
        self.import_web_button.setMinimumHeight(36)
        self.import_web_button.clicked.connect(self.import_researched_web_leads)
        self.saved_status_label = QLabel("App DB: 0 saved leads")
        self.saved_status_label.setWordWrap(True)
        import_row.addWidget(self.import_workbook_button)
        import_row.addWidget(self.import_web_button)
        import_row.addWidget(self.saved_status_label, 1)
        root.addLayout(import_row)

        self.kpi_values = {}
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)
        for key, caption, accent in (
            ("prospects", "Lead rows", "#00E5FF"),
            ("stores", "Store leads", "#34D399"),
            ("gyms", "Gym leads", "#A78BFA"),
            ("regions", "Regions", "#FBBF24"),
            ("dashboard", "Reference stores", "#60A5FA"),
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

        self.pages = QTabWidget()
        self.pages.addTab(self._build_leads_page(), "Prospect List")
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

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search business, phone, category, city…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(lambda _text: self._filter_timer.start())
        self.kind_filter = QComboBox()
        self.kind_filter.addItems(["All types", "Store", "Gym"])
        self.kind_filter.currentTextChanged.connect(lambda _text: self.apply_filters())
        self.state_filter = QComboBox()
        self.state_filter.addItem("All States / UTs")
        self.state_filter.currentTextChanged.connect(lambda _text: self.apply_filters())
        filters.addWidget(self.search_input, 2)
        filters.addWidget(self.kind_filter)
        filters.addWidget(self.state_filter, 1)
        layout.addLayout(filters)

        self.results_label = QLabel("Load the prospect database workbook to view records.")
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
            "Coverage uses saved app database leads. Online retailer listings still need a direct call before outreach."
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
            "Counts stay separated by source. Official website listings are not treated as call-verified."
        )
        privacy.setWordWrap(True)
        privacy.setStyleSheet("font-size: 8pt; color: #94A3B8;")
        layout.addWidget(privacy)
        return page

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
        visible = 0
        for row_index, record in enumerate(self.records):
            matches_kind = kind == "All types" or record.get("kind") == kind
            matches_state = state == "All States / UTs" or record.get("state") == state
            search_blob = " ".join(str(value or "") for value in record.values()).casefold()
            matches_search = not search or search in search_blob
            shown = matches_kind and matches_state and matches_search
            self.leads_table.setRowHidden(row_index, not shown)
            visible += shown
        self.results_label.setText(
            f"Showing {visible:,} of {len(self.records):,} prospect rows · double-check the source workbook before acting on contact details."
            if self.records else "Load the prospect database workbook to view records."
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
