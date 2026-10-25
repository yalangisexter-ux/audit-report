"""Read-only explorer, web scraper, and print/export center for customer/prospect workbooks."""
from collections import defaultdict
import base64
import csv
from datetime import date, datetime, time
import hashlib
import html
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
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
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
    QScrollArea,
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
    {"business_name": "Juneja Ventures", "city": "Patna", "state": "Bihar", "address": "Juneja House, near Poddar Bhawan, Saidpur Gali, Bhikna Pahari, Patna, Bihar 800004", "phone": "9608431790"},
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
    {"business_name": "The Caffeine Shop", "city": "Vijayawada", "state": "Andhra Pradesh", "address": "Flat 301, Padmavathi Nilayam, Telephone Colony, Bhavanipuram, Vijayawada, Andhra Pradesh 520012", "phone": "9700179988"},
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
    "email": {"email", "emailaddress", "emailid", "contactemail", "mail", "e-mail"},
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
    "dadranagarhavelianddamandiu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadranagarhavelianddamananddiu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadranagarhaveli": "Dadra and Nagar Haveli and Daman and Diu",
    "damandiu": "Dadra and Nagar Haveli and Daman and Diu",
    "daman": "Dadra and Nagar Haveli and Daman and Diu",
    "diu": "Dadra and Nagar Haveli and Daman and Diu",
    "dnh": "Dadra and Nagar Haveli and Daman and Diu",
    "dandnh": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi",
    "delhincr": "Delhi",
    "jammuandkashmir": "Jammu and Kashmir",
    "jammukashmir": "Jammu and Kashmir",
    "jammu": "Jammu and Kashmir",
    "kashmir": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
    "jandk": "Jammu and Kashmir",
    "ladakh": "Ladakh",
    "lakshadweep": "Lakshadweep",
    "puducherry": "Puducherry",
}
INDIA_REGIONS = tuple(sorted(set(STATE_NAMES.values()), key=str.casefold))

INDIA_STATES = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal"
)

INDIA_UNION_TERRITORIES = (
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Puducherry"
)

INDIA_ISLAND_TERRITORIES = (
    "Andaman and Nicobar Islands", "Lakshadweep"
)



MAJOR_CHAINS_STORE_PRESENCE = {
    "supplements villa": "Haryana, Delhi, Uttar Pradesh, Punjab, Rajasthan",
    "nutrabay": "Delhi, Maharashtra, Karnataka, Haryana, Telangana",
    "hyugalife": "Maharashtra, Karnataka, Delhi, Haryana",
    "fastandup": "Maharashtra, Delhi, Karnataka, Tamil Nadu, Telangana",
    "fast&up": "Maharashtra, Delhi, Karnataka, Tamil Nadu, Telangana",
    "rawgain": "Delhi, Uttar Pradesh, Haryana, Punjab",
    "fitnesstack": "Delhi, Punjab, Haryana, Uttar Pradesh",
    "beast nutrition": "Delhi, Haryana, Uttar Pradesh, Rajasthan",
    "body fuel": "Haryana, Delhi, Punjab, Chandigarh",
    "shrufit": "Delhi, Haryana, Punjab, Uttar Pradesh",
    "cm nutrition": "Delhi, Uttar Pradesh, Haryana",
    "slam fitness": "Tamil Nadu, Karnataka, Telangana",
    "prosupps": "Delhi, Maharashtra, Karnataka, Tamil Nadu, West Bengal",
    "shred nutrition": "Delhi, Haryana, Uttar Pradesh",
    "supplemart": "Delhi, Punjab, Haryana",
    "the hunk gym": "Uttar Pradesh",
    "monty fitness": "Uttar Pradesh",
    "maa karni gym": "Rajasthan",
}

CITY_TO_STATE_MAP = {
    "kanpur": "Uttar Pradesh", "noida": "Uttar Pradesh", "lucknow": "Uttar Pradesh",
    "prayagraj": "Uttar Pradesh", "varanasi": "Uttar Pradesh", "ghaziabad": "Uttar Pradesh",
    "agra": "Uttar Pradesh", "meerut": "Uttar Pradesh", "bareilly": "Uttar Pradesh",
    "aligarh": "Uttar Pradesh", "moradabad": "Uttar Pradesh", "saharanpur": "Uttar Pradesh",
    "gorakhpur": "Uttar Pradesh", "nawabganj": "Uttar Pradesh",
    "patna": "Bihar", "gaya": "Bihar", "bhagalpur": "Bihar", "muzaffarpur": "Bihar",
    "purnia": "Bihar", "darbhanga": "Bihar", "bihar sharif": "Bihar", "arrah": "Bihar",
    "mumbai": "Maharashtra", "pune": "Maharashtra", "nagpur": "Maharashtra", "nashik": "Maharashtra",
    "thane": "Maharashtra", "aurangabad": "Maharashtra", "solapur": "Maharashtra", "kolhapur": "Maharashtra",
    "bengaluru": "Karnataka", "bangalore": "Karnataka", "mysuru": "Karnataka", "hubli": "Karnataka",
    "mangalore": "Karnataka", "belagavi": "Karnataka",
    "delhi": "Delhi", "new delhi": "Delhi",
    "faridabad": "Haryana", "gurugram": "Haryana", "gurgaon": "Haryana", "panipat": "Haryana",
    "ambala": "Haryana", "karnal": "Haryana", "rohtak": "Haryana", "hisar": "Haryana",
    "ludhiana": "Punjab", "amritsar": "Punjab", "jalandhar": "Punjab", "patiala": "Punjab", "bathinda": "Punjab",
    "chandigarh": "Chandigarh",
    "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu", "tiruchirappalli": "Tamil Nadu", "salem": "Tamil Nadu",
    "hyderabad": "Telangana", "secunderabad": "Telangana", "warangal": "Telangana",
    "jaipur": "Rajasthan", "jodhpur": "Rajasthan", "kota": "Rajasthan", "bikaner": "Rajasthan", "ajmer": "Rajasthan", "balesar": "Rajasthan",
    "ahmedabad": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat", "rajkot": "Gujarat", "bhavnagar": "Gujarat",
    "kolkata": "West Bengal", "howrah": "West Bengal", "durgapur": "West Bengal", "siliguri": "West Bengal",
    "bhubaneswar": "Odisha", "cuttack": "Odisha", "rourkela": "Odisha",
    "kochi": "Kerala", "thiruvananthapuram": "Kerala", "kozhikode": "Kerala", "calicut": "Kerala", "thrissur": "Kerala",
    "dehradun": "Uttarakhand", "haridwar": "Uttarakhand", "roorkee": "Uttarakhand",
    "raipur": "Chhattisgarh", "bilaspur": "Chhattisgarh", "bhilai": "Chhattisgarh",
    "indore": "Madhya Pradesh", "bhopal": "Madhya Pradesh", "gwalior": "Madhya Pradesh", "jabalpur": "Madhya Pradesh",
    "ranchi": "Jharkhand", "jamshedpur": "Jharkhand", "dhanbad": "Jharkhand",
    "visakhapatnam": "Andhra Pradesh", "vijayawada": "Andhra Pradesh", "guntur": "Andhra Pradesh",
}


def resolve_store_presence_states(record_or_name, city="", address="", url=""):
    """Instead of 'All India', identify which states the store is actually present in."""
    if isinstance(record_or_name, dict):
        rec = record_or_name
        name = str(rec.get("business_name") or rec.get("name") or "")
        city = str(rec.get("city") or "")
        address = str(rec.get("address") or "")
        url = str(rec.get("website") or rec.get("source_url") or "")
        existing_state = str(rec.get("state") or "").strip()
    else:
        name = str(record_or_name or "")
        existing_state = ""

    if existing_state and existing_state not in ("All-india", "All-India", "India", "Employees", "All India"):
        return existing_state

    blob = f"{name} {city} {address} {url}".casefold()
    for chain, states in MAJOR_CHAINS_STORE_PRESENCE.items():
        if chain in blob:
            return states
    for c_key, s_val in CITY_TO_STATE_MAP.items():
        if re.search(r'\b' + re.escape(c_key) + r'\b', blob):
            return s_val
    for s_item in INDIA_REGIONS:
        if re.search(r'\b' + re.escape(s_item.casefold()) + r'\b', blob):
            return s_item
    return "Delhi, Maharashtra, Karnataka, Uttar Pradesh, Haryana"


def territory_type(region_name):
    """Categorize an administrative region into State, Union Territory, or Island Territory."""
    name = str(region_name or "").strip()
    if name in INDIA_ISLAND_TERRITORIES:
        return "Island Territory"
    if name in INDIA_UNION_TERRITORIES:
        return "Union Territory"
    return "State"


def _normalise_key(value):
    text = html.unescape(str(value or ""))
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def _normalise_phone(phone_str):
    """Extract standard 10-digit Indian mobile / landline number."""
    digits = re.sub(r"[^\d]", "", str(phone_str or ""))
    if digits.startswith("91") and len(digits) > 10:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) > 10:
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else ""


def _normalise_domain(url_str):
    """Extract registered domain name, ignoring protocol and www."""
    try:
        raw = str(url_str or "").strip()
        if not raw:
            return ""
        if "://" not in raw:
            raw = "https://" + raw
        host = urllib.parse.urlparse(raw).netloc.lower().split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        if host in {"google.com", "bing.com", "duckduckgo.com", "justdial.com", "facebook.com", "instagram.com", "twitter.com", "x.com"}:
            return ""
        return host
    except Exception:
        return ""


def _normalise_store_name(name_str):
    """Normalize store name for robust deduplication across slight naming differences."""
    name = html.unescape(str(name_str or "")).lower()
    name = re.sub(r"https?://\S+|www\.\S+", "", name)
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    tokens = [t for t in name.split() if t not in {
        "store", "stores", "shop", "shops", "gym", "gyms", "fitness", "centre", "center",
        "nutrition", "supplements", "supplement", "india", "pvt", "ltd", "co", "in", "the", "and"
    }]
    return "".join(tokens) or re.sub(r"[^a-z0-9]+", "", name)


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
    raw = raw.replace("&", " and ")
    key = _normalise_key(raw)
    if key in ("allindia", "india", "panindia"):
        fb_key = _normalise_key(_cell_text(fallback))
        if fb_key in STATE_NAMES:
            return STATE_NAMES[fb_key]
        return "Delhi, Maharashtra, Karnataka, Uttar Pradesh, Haryana"
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
    """Combine in-memory workbook counts while preserving the source totals.
    For stores present in multiple states, increments totals for each active state."""
    totals = defaultdict(lambda: {"Store": 0, "Gym": 0})
    for record in records:
        raw_state = str(record.get("state") or "").strip()
        if not raw_state:
            continue
        # Split multi-state presence e.g. 'Delhi, Haryana, Uttar Pradesh'
        st_list = [s.strip() for s in raw_state.split(",") if s.strip()]
        for sub_st in st_list:
            clean_st = normalise_state(sub_st)
            if clean_st and clean_st in INDIA_REGIONS:
                kind = record.get("kind") if record.get("kind") in {"Store", "Gym"} else "Store"
                totals[clean_st][kind] += 1
    dashboard_counts = dashboard_counts or {}
    valid_db_counts = {k: v for k, v in dashboard_counts.items() if k in INDIA_REGIONS}
    all_states = set(totals) | set(valid_db_counts)
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
    """Generate a canonical, stable deduplication key for a store record.
    Uses normalized business name, state, and city (ignoring variable address and HTML entities)."""
    clean_name = html.unescape(str(record.get("business_name") or "")).strip()
    clean_name = re.sub(r"https?://\S+|www\.\S+", "", clean_name).strip()
    norm_name = _normalise_store_name(clean_name)
    norm_state = _normalise_key(normalise_state(record.get("state")))
    norm_city = _normalise_key(record.get("city"))
    identity = f"name:{norm_name}|state:{norm_state}|city:{norm_city}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def sanitize_prospect_database_records(db):
    """Clean up existing database records:
    1. Phone displaced into area or populated with city/state names.
    2. Instead of 'All-India', resolve and assign states where store is actually present.
    3. Purge employee sheet records ('Employees') and non-business web search artifacts."""
    if not db or not hasattr(db, "conn") or not db.conn:
        return
    try:
        # Purge employee rows and non-store scraped web noise
        db.conn.execute("DELETE FROM customer_prospects WHERE state = 'Employees'")
        db.conn.execute("""
            DELETE FROM customer_prospects
            WHERE business_name LIKE '%merriam-webster%'
               OR business_name LIKE '%siemens%'
               OR business_name LIKE '%studocu%'
               OR business_name LIKE '%manualslib%'
               OR business_name LIKE '%asairsensors%'
               OR business_name LIKE '%instrumentmro%'
               OR business_name LIKE '%faculdades%'
               OR business_name LIKE '%cnpj%'
               OR business_name LIKE '%databrasil%'
               OR business_name LIKE '%consultacnpj%'
        """)
        db.conn.commit()

        # Phone sanitization
        rows = db.conn.execute(
            "SELECT id, phone, area, city, state FROM customer_prospects WHERE phone IS NOT NULL AND phone != ''"
        ).fetchall()
        updates = []
        for row in rows:
            r_id = row[0]
            p = str(row[1] or "").strip()
            a = str(row[2] or "").strip()
            c = str(row[3] or "").strip()
            s = str(row[4] or "").strip()
            p_digits = re.sub(r'\D', '', p)
            a_digits = re.sub(r'\D', '', a)
            letter_cnt = len(re.findall(r'[a-zA-Z]', p))
            if len(a_digits) >= 10 and len(p_digits) < 6:
                updates.append((a, "", r_id))
            elif len(p_digits) < 6 or (c and p.lower() == c.lower()) or (s and p.lower() == s.lower()) or letter_cnt > 3 or p.lower() in ("nan", "none", "null", "n/a", "-"):
                updates.append(("", a, r_id))
        if updates:
            db.conn.executemany(
                "UPDATE customer_prospects SET phone = ?, area = ? WHERE id = ?",
                updates
            )

        # Resolve All-India to real state presence
        all_india_rows = db.conn.execute(
            "SELECT id, business_name, city, address, website, state FROM customer_prospects "
            "WHERE state IN ('All-india', 'All-India', 'India', 'All India') OR state LIKE '%All-india%'"
        ).fetchall()
        state_updates = []
        for a_row in all_india_rows:
            rec_id = a_row[0]
            new_st = resolve_store_presence_states(a_row[1], a_row[2] or "", a_row[3] or "", a_row[4] or "")
            state_updates.append((new_st, rec_id))
        if state_updates:
            db.conn.executemany(
                "UPDATE customer_prospects SET state = ? WHERE id = ?",
                state_updates
            )

        db.conn.commit()
    except Exception as exc:
        logging.getLogger("prospects").debug("Sanitize prospect records error: %s", exc)


def format_prospect_cell_value(record, key):
    """Format and sanitize prospect values for display and export, ensuring 'NA' fallback for empty/displaced data."""
    raw_val = str(record.get(key, "") or "").strip()
    if not raw_val or raw_val.casefold() in {"nan", "none", "null", "n/a", "-", ""}:
        if key == "state":
            resolved = resolve_store_presence_states(record)
            return resolved if resolved else "NA"
        return "NA"

    if key == "state":
        if raw_val in {"All-India", "All India", "India", "All-india"}:
            resolved = resolve_store_presence_states(record)
            return resolved if resolved else "NA"
        return raw_val

    if key == "phone":
        digits = re.sub(r'\D', '', raw_val)
        c_val = str(record.get("city", "") or "").strip().lower()
        s_val = str(record.get("state", "") or "").strip().lower()
        letter_count = len(re.findall(r'[a-zA-Z]', raw_val))
        if len(digits) < 6 or (c_val and raw_val.lower() == c_val) or (s_val and raw_val.lower() == s_val) or letter_count > 3:
            return "NA"
        return raw_val

    if key in {"contact_person", "email", "followup_date", "area", "address", "city", "business_category"}:
        return raw_val if raw_val.casefold() not in {"nan", "none", "null", "n/a", "-", ""} else "NA"

    if key in {"website", "maps"}:
        return raw_val if raw_val.casefold() not in {"nan", "none", "null", "n/a", "-", ""} else "NA"

    return raw_val


def persist_prospect_records(db, records, *, source_name="", source_url="", source_checked_at=None):
    """Append or enrich prospect rows in the app database without replacing existing activity or deleting old data."""
    checked_at = source_checked_at or datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0
    duplicate = 0
    try:
        db.conn.execute("ALTER TABLE customer_prospects ADD COLUMN email TEXT DEFAULT ''")
    except Exception:
        pass

    fields = (
        "dedupe_key", "kind", "business_name", "business_category", "state", "city", "area",
        "contact_person", "phone", "email", "address", "website", "maps", "followup_date", "call_time",
        "connection", "verified", "response", "notes", "source_name", "source_url", "source_type",
        "source_checked_at", "source_sheet", "source_row", "source_status", "created_at", "updated_at",
    )
    placeholders = ",".join("?" for _ in fields)
    columns = ",".join(fields)

    existing_rows = db.conn.execute(
        "SELECT id, dedupe_key, kind, business_name, state, city, phone, email, address, maps, website FROM customer_prospects"
    ).fetchall()

    existing_by_key = {}
    existing_by_phone = {}
    existing_by_domain = {}
    existing_by_name_state = {}

    for row in existing_rows:
        r = dict(row)
        if r.get("dedupe_key"):
            existing_by_key[r["dedupe_key"]] = r
        p = _normalise_phone(r.get("phone"))
        if p:
            existing_by_phone[p] = r
        d = _normalise_domain(r.get("website"))
        if d:
            existing_by_domain[d] = r
        ns_name = _normalise_store_name(r.get("business_name"))
        ns_state = _normalise_key(r.get("state"))
        if ns_name:
            existing_by_name_state[(ns_name, ns_state)] = r
            if (ns_name, "") not in existing_by_name_state:
                existing_by_name_state[(ns_name, "")] = r

    try:
        db.conn.execute("BEGIN")
        for source_record in records:
            record = dict(source_record)
            clean_name = html.unescape(str(record.get("business_name") or "")).strip()
            clean_name = re.sub(r"https?://\S+|www\.\S+", "", clean_name).strip()
            record["business_name"] = clean_name
            if not record["business_name"]:
                continue

            record["kind"] = record.get("kind") or "Store"
            record["state"] = normalise_state(record.get("state"))
            record["address"] = html.unescape(str(record.get("address") or "")).strip()
            record["city"] = html.unescape(str(record.get("city") or "")).strip()

            # Keep the directory actionable when a merchant publishes a full address
            # but omits a direct Maps URL. This opens a Google Maps search for the
            # exact business/address; it does not fabricate a pin or coordinates.
            maps_value = str(record.get("maps") or "").strip()
            invalid_maps = maps_value.casefold() in {"", "na", "n/a", "none", "null", "-"}
            address_value = record["address"]
            if invalid_maps and address_value and address_value.casefold() not in {"na", "n/a", "none", "null", "-"}:
                map_query = ", ".join(
                    part for part in (
                        record["business_name"], address_value, record["city"],
                        record["state"], "India"
                    ) if str(part or "").strip()
                )
                record["maps"] = "https://www.google.com/maps/search/?" + urllib.parse.urlencode({"api": "1", "query": map_query})
            else:
                record["maps"] = maps_value

            p_raw = str(record.get("phone") or "").strip()
            a_raw = str(record.get("area") or "").strip()
            p_digits = re.sub(r'\D', '', p_raw)
            a_digits = re.sub(r'\D', '', a_raw)
            c_val = record["city"].lower()
            s_val = record["state"].lower()

            if len(a_digits) >= 10 and len(p_digits) < 6:
                record["phone"] = a_raw
                record["area"] = ""
            elif len(p_digits) < 6 or (c_val and p_raw.lower() == c_val) or (s_val and p_raw.lower() == s_val):
                record["phone"] = ""
            else:
                record["phone"] = p_raw

            combined = f"{record['business_name']} {record.get('business_category', '')}"
            if NEGATIVE_FILTER_PATTERN.search(combined):
                continue

            key = prospect_dedupe_key(record)
            norm_phone = _normalise_phone(record.get("phone"))
            norm_domain = _normalise_domain(record.get("website"))
            norm_name = _normalise_store_name(clean_name)
            norm_state = _normalise_key(record["state"])

            match = None
            if key in existing_by_key:
                match = existing_by_key[key]
            elif (norm_name, norm_state) in existing_by_name_state:
                match = existing_by_name_state[(norm_name, norm_state)]
            elif norm_name and (norm_name, "") in existing_by_name_state:
                match = existing_by_name_state[(norm_name, "")]
            elif norm_phone and norm_phone in existing_by_phone:
                p_cand = existing_by_phone[norm_phone]
                if _normalise_store_name(p_cand.get("business_name")) == norm_name:
                    match = p_cand
            elif norm_domain and norm_domain in existing_by_domain:
                d_cand = existing_by_domain[norm_domain]
                if _normalise_store_name(d_cand.get("business_name")) == norm_name:
                    match = d_cand

            if match:
                updates = {}
                if not match.get("phone") and record.get("phone"):
                    updates["phone"] = record["phone"]
                if not match.get("email") and record.get("email"):
                    updates["email"] = record["email"]
                if (not match.get("address") or len(str(record.get("address", ""))) > len(str(match.get("address", "")))) and record.get("address"):
                    updates["address"] = record["address"]
                if not match.get("maps") and record.get("maps"):
                    updates["maps"] = record["maps"]
                if not match.get("website") and record.get("website"):
                    updates["website"] = record["website"]
                if not match.get("city") and record.get("city"):
                    updates["city"] = record["city"]
                if (not match.get("state") or match.get("state") == "All-India") and record.get("state") and record.get("state") != "All-India":
                    updates["state"] = record["state"]

                if updates:
                    updates["updated_at"] = now
                    set_clause = ", ".join(f"{k} = ?" for k in updates)
                    db.conn.execute(
                        f"UPDATE customer_prospects SET {set_clause} WHERE id = ?",
                        list(updates.values()) + [match["id"]]
                    )
                    match.update(updates)
                duplicate += 1
            else:
                call_verified = str(record.get("verified") or "").strip().casefold() in {"yes", "y", "true", "verified"}
                record.setdefault("source_name", source_name)
                record.setdefault("source_url", source_url)
                record.setdefault("source_type", "Workbook")
                record.setdefault("source_checked_at", checked_at)
                record.setdefault("source_status", "Workbook indicates call verified" if call_verified else "Needs direct confirmation")
                record["dedupe_key"] = key
                record["created_at"] = now
                record["updated_at"] = now
                values = [record.get(field, "") for field in fields]
                cursor = db.conn.execute(
                    f"INSERT OR IGNORE INTO customer_prospects({columns}) VALUES({placeholders})",
                    values,
                )
                if cursor.rowcount:
                    inserted += 1
                    new_item = {
                        "id": cursor.lastrowid,
                        "dedupe_key": key,
                        "kind": record["kind"],
                        "business_name": clean_name,
                        "state": record["state"],
                        "city": record["city"],
                        "phone": record.get("phone", ""),
                        "email": record.get("email", ""),
                        "address": record.get("address", ""),
                        "maps": record.get("maps", ""),
                        "website": record.get("website", ""),
                    }
                    existing_by_key[key] = new_item
                    if norm_phone:
                        existing_by_phone[norm_phone] = new_item
                    if norm_domain:
                        existing_by_domain[norm_domain] = new_item
                    if norm_name:
                        existing_by_name_state[(norm_name, norm_state)] = new_item
                        existing_by_name_state[(norm_name, "")] = new_item
                else:
                    duplicate += 1
        db.conn.commit()
    except Exception:
        db.conn.rollback()
        raise
    return {"inserted": inserted, "duplicates": duplicate}


def cleanup_duplicate_prospects(db):
    """Audit and deduplicate existing records in the database:
    1. Unescapes HTML entities in stored business names (e.g. &#x27; -> ').
    2. Groups records by phone, website domain, and normalized business name + state.
    3. Merges phone, email, maps, website, and user notes into the primary row.
    4. Deletes redundant duplicate rows, keeping all user data and notes safe."""
    if db is None:
        return {"merged": 0, "cleaned_names": 0}

    rows = db.conn.execute(
        "SELECT id, dedupe_key, kind, business_name, state, city, area, contact_person, "
        "phone, email, address, website, maps, followup_date, call_time, connection, "
        "verified, response, notes, source_name, source_url, source_type, source_status, created_at, updated_at "
        "FROM customer_prospects ORDER BY id ASC"
    ).fetchall()

    if not rows:
        return {"merged": 0, "cleaned_names": 0}

    cleaned_names = 0
    groups = defaultdict(list)
    for row in rows:
        rec = dict(row)
        orig_name = str(rec.get("business_name") or "")
        unescaped_name = html.unescape(orig_name).strip()
        unescaped_name = re.sub(r"https?://\S+|www\.\S+", "", unescaped_name).strip()
        if unescaped_name != orig_name:
            db.conn.execute(
                "UPDATE customer_prospects SET business_name = ? WHERE id = ?",
                (unescaped_name, rec["id"])
            )
            rec["business_name"] = unescaped_name
            cleaned_names += 1

        norm_phone = _normalise_phone(rec.get("phone"))
        norm_domain = _normalise_domain(rec.get("website"))
        norm_name = _normalise_store_name(rec.get("business_name"))
        norm_state = _normalise_key(rec.get("state"))

        if norm_name:
            group_key = f"name:{norm_name}|state:{norm_state}"
        elif norm_phone:
            group_key = f"phone:{norm_phone}|state:{norm_state}"
        elif norm_domain:
            group_key = f"domain:{norm_domain}"
        else:
            group_key = f"id:{rec['id']}"

        groups[group_key].append(rec)

    merged_count = 0
    deleted_ids = []

    for group_key, items in groups.items():
        if len(items) <= 1:
            continue

        def score(r):
            s = 0
            if r.get("notes"): s += 20
            if r.get("followup_date"): s += 15
            if r.get("response"): s += 10
            if str(r.get("verified", "")).lower() in {"yes", "true"}: s += 8
            if r.get("phone"): s += 5
            if r.get("email"): s += 5
            if r.get("maps"): s += 4
            if r.get("website"): s += 3
            if r.get("address"): s += 2
            return s

        items_sorted = sorted(items, key=score, reverse=True)
        keeper = items_sorted[0]
        duplicates = items_sorted[1:]

        updates = {}
        for dup in duplicates:
            if not keeper.get("phone") and dup.get("phone"):
                keeper["phone"] = dup["phone"]
                updates["phone"] = dup["phone"]
            if not keeper.get("email") and dup.get("email"):
                keeper["email"] = dup["email"]
                updates["email"] = dup["email"]
            if not keeper.get("maps") and dup.get("maps"):
                keeper["maps"] = dup["maps"]
                updates["maps"] = dup["maps"]
            if not keeper.get("website") and dup.get("website"):
                keeper["website"] = dup["website"]
                updates["website"] = dup["website"]
            if (not keeper.get("address") or len(str(keeper.get("address"))) < 10) and dup.get("address"):
                keeper["address"] = dup["address"]
                updates["address"] = dup["address"]
            if not keeper.get("city") and dup.get("city"):
                keeper["city"] = dup["city"]
                updates["city"] = dup["city"]
            if (not keeper.get("state") or keeper.get("state") == "All-India") and dup.get("state") and dup.get("state") != "All-India":
                keeper["state"] = dup["state"]
                updates["state"] = dup["state"]
            if not keeper.get("notes") and dup.get("notes"):
                keeper["notes"] = dup["notes"]
                updates["notes"] = dup["notes"]
            deleted_ids.append(dup["id"])

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            db.conn.execute(
                f"UPDATE customer_prospects SET {set_clause} WHERE id = ?",
                list(updates.values()) + [keeper["id"]]
            )
        merged_count += len(duplicates)

    if deleted_ids:
        placeholders = ",".join("?" for _ in deleted_ids)
        db.conn.execute(f"DELETE FROM customer_prospects WHERE id IN ({placeholders})", deleted_ids)
        db.conn.commit()

    return {"merged": merged_count, "cleaned_names": cleaned_names}


def google_maps_search_url(record):
    """Build a Google Maps search URL from the store name and its full address."""
    parts = (
        str(record.get("business_name") or "").strip(),
        str(record.get("address") or "").strip(),
        str(record.get("city") or "").strip(),
        str(record.get("state") or "").strip(),
        "India",
    )
    query = ", ".join(part for part in parts if part)
    if not str(record.get("business_name") or "").strip() or not str(record.get("address") or "").strip():
        return ""
    return "https://www.google.com/maps/search/?" + urllib.parse.urlencode({"api": "1", "query": query})


def load_saved_prospects(db):
    rows = db.conn.execute(
        "SELECT * FROM customer_prospects ORDER BY state COLLATE NOCASE, city COLLATE NOCASE, business_name COLLATE NOCASE"
    ).fetchall()
    records = [dict(row) for row in rows]
    # Backfill actionable Maps search URLs for previously imported rows that have a
    # genuine address but no direct Maps URL. Keep the full address unchanged.
    changed = False
    for record in records:
        maps_value = str(record.get("maps") or "").strip()
        address_value = str(record.get("address") or "").strip()
        if (
            not maps_value or maps_value.casefold() in {"na", "n/a", "none", "null", "-"}
        ) and address_value and address_value.casefold() not in {"na", "n/a", "none", "null", "-"}:
            maps_url = google_maps_search_url(record)
            record["maps"] = maps_url
            if record.get("id") is not None:
                try:
                    db.conn.execute(
                        "UPDATE customer_prospects SET maps=? WHERE id=? AND (maps IS NULL OR TRIM(maps)='' OR LOWER(TRIM(maps)) IN ('na','n/a','none','null','-'))",
                        (maps_url, record["id"]),
                    )
                    changed = True
                except Exception:
                    pass
    if changed:
        try:
            db.conn.commit()
        except Exception:
            pass
    return records


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
    """Seed only retailer rows published by the brand; remove only the old bundled seed."""
    setting = "customer_prospects_official_web_seed_20261025_v4"
    if db.get_setting(setting) == "1":
        return {"inserted": 0, "duplicates": 0}

    # The former 3,973-row bundled file was not individually source-verified.
    # Remove only rows imported under that exact legacy seed identity; preserve
    # customer-entered, workbook-imported, and independently researched records.
    try:
        db.conn.execute(
            "DELETE FROM customer_prospects WHERE source_name IN (?, ?)",
            ("Bundled All-India Store Directory", "Bundled Store Directory"),
        )
        db.conn.commit()
    except Exception as exc:
        logging.getLogger("prospects").warning("Could not clean legacy bundled store seed: %s", exc)

    records = []
    for lead in RESEARCHED_WEB_LEADS:
        record = {
            **lead,
            "kind": "Store",
            "business_category": "Sports nutrition retailer",
            "source_name": RESEARCHED_SOURCE_NAME,
            "source_url": RESEARCHED_SOURCE_URL,
            "source_type": "Official web listing",
            "source_checked_at": RESEARCH_DATE,
            "source_status": RESEARCHED_SOURCE_STATUS,
        }
        record["maps"] = google_maps_search_url(record)
        records.append(record)

    result = persist_prospect_records(
        db,
        records,
        source_name=RESEARCHED_SOURCE_NAME,
        source_url=RESEARCHED_SOURCE_URL,
        source_checked_at=RESEARCH_DATE,
    )
    db.set_setting(setting, "1")
    return result


def extract_deep_page_details(html: str, page_url: str = "", default_business: str = "", default_state: str = ""):
    """Deep inspection of merchant/gym webpage for genuine contact details, address, maps & category."""
    details = {
        "phones": [],
        "emails": [],
        "address": "",
        "maps": "",
        "subpages": [],
        "kind": "Store",
        "category": "Sports Nutrition / Supplement Store",
    }
    if not html:
        return details

    # 1. Phone numbers
    # a. href="tel:..."
    for raw_tel in re.findall(r'href=["\']tel:([^"\']+)["\']', html, re.IGNORECASE):
        cleaned = re.sub(r'[^\d+]', '', raw_tel)
        digits = cleaned.replace("+91", "").replace("+", "")
        if len(digits) >= 10:
            formatted = cleaned if cleaned.startswith("+") else ("+91 " + cleaned if len(cleaned) == 10 else cleaned)
            if formatted not in details["phones"]:
                details["phones"].append(formatted)

    # b. WhatsApp links
    for wa in re.findall(r'(?:wa\.me|whatsapp\.com/send\?phone=)(\+?\d+)', html, re.IGNORECASE):
        cleaned = re.sub(r'[^\d+]', '', wa)
        if len(cleaned.replace("+91", "")) >= 10:
            formatted = cleaned if cleaned.startswith("+") else "+91 " + cleaned
            if formatted not in details["phones"]:
                details["phones"].append(formatted)

    # c. Explicit contact labels
    for kw_phone in re.findall(r'(?:Phone|Mobile|Contact|Call|Tel|WhatsApp|Helpline)[\s:]*([+\d\s-]{10,16})', html, re.IGNORECASE):
        cleaned = re.sub(r'[^\d+]', '', kw_phone)
        digits = cleaned.replace("+91", "").replace("+", "")
        if 10 <= len(digits) <= 12:
            formatted = cleaned if cleaned.startswith("+") else ("+91 " + cleaned if len(cleaned) == 10 else cleaned)
            if formatted not in details["phones"]:
                details["phones"].append(formatted)

    # d. General Indian mobile pattern (+91 9... or 0... or 9...)
    for tp in re.findall(r'(?:\+91[\s.-]?|0)?[6-9]\d{4}[\s.-]?\d{5}\b', html):
        cleaned = re.sub(r'[\s.-]', '', tp)
        if not cleaned.startswith("+") and not cleaned.startswith("0") and len(cleaned) == 10:
            cleaned = "+91 " + cleaned
        if cleaned not in details["phones"]:
            details["phones"].append(cleaned)

    # 2. Email addresses
    for raw_mail in re.findall(r'href=["\']mailto:([^"\'?]+)["\']', html, re.IGNORECASE):
        clean_mail = raw_mail.strip().lower()
        if "@" in clean_mail and "." in clean_mail and not clean_mail.endswith((".png", ".jpg", ".webp", ".svg")):
            if clean_mail not in details["emails"]:
                details["emails"].append(clean_mail)

    for em in re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', html):
        em_lower = em.lower()
        if em_lower not in details["emails"] and not em_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
            if not any(dummy in em_lower for dummy in ("example.com", "wixpress.com", "sentry.io", "domain.com", "schema.org", "yourname")):
                details["emails"].append(em_lower)

    # 3. Google Maps link
    map_links = re.findall(r'href=["\'](https?://(?:www\.)?(?:google\.com/maps|maps\.google\.com|goo\.gl/maps|maps\.app\.goo\.gl)[^"\']*)["\']', html, re.IGNORECASE)
    if map_links:
        details["maps"] = map_links[0]
    else:
        map_embed = re.findall(r'src=["\'](https?://(?:www\.)?google\.com/maps/embed[^"\']*)["\']', html, re.IGNORECASE)
        if map_embed:
            details["maps"] = map_embed[0]

    # 4. Address extraction
    addr_match = re.search(r'<address\b[^>]*>(.*?)</address>', html, re.IGNORECASE | re.DOTALL)
    if addr_match:
        raw_addr = re.sub(r'<[^>]+>', ' ', addr_match.group(1))
        details["address"] = re.sub(r'\s+', ' ', raw_addr).strip()
    else:
        street = re.search(r'itemprop=["\']streetAddress["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if not street:
            street = re.search(r'itemprop=["\']streetAddress["\'][^>]*>(.*?)<', html, re.IGNORECASE)
        if street:
            details["address"] = street.group(1).strip()
        else:
            pin_match = re.search(r'((?:[A-Za-z0-9#,\.\-\/]+\s+){2,14}(?:Road|Street|Nagar|Colony|Marg|Complex|Bhavan|Circle|Sector|Phase|Plot|Shop|Floor)[^<>\n\r]{2,80}\b[1-9]\d{5}\b)', html, re.IGNORECASE)
            if pin_match:
                details["address"] = re.sub(r'\s+', ' ', pin_match.group(1)).strip()

    # 5. Classification check
    html_lower = html.lower()
    is_gym = any(k in html_lower for k in ("gym", "fitness centre", "fitness center", "health club", "crossfit", "workout studio", "gymnasium"))
    has_supplements = any(k in html_lower for k in (
        "supplement", "supplements", "whey protein", "protein shake", "creatine", "bcaa",
        "nutrition bar", "pro shop", "pro-shop", "shake bar", "energy drinks", "sports nutrition"
    ))
    if is_gym and has_supplements:
        details["kind"] = "Gym + Store"
        details["category"] = "Gym with Nutrition & Supplement Counter / Pro-Shop"
    elif is_gym:
        details["kind"] = "Gym"
        details["category"] = "Fitness Centre / Gym"
    else:
        details["kind"] = "Store"
        details["category"] = "Sports Nutrition / Supplement Store"

    # 6. Contact subpage links
    if page_url:
        for sp in re.findall(r'href=["\']([^"\']*(?:contact|about|reach-us|store-locator|location)[^"\']*)["\']', html, re.IGNORECASE):
            if not sp.startswith("javascript:") and not sp.startswith("#") and not sp.endswith((".pdf", ".jpg", ".png")):
                full_sub = urllib.parse.urljoin(page_url, sp)
                parsed_sub = urllib.parse.urlparse(full_sub)
                parsed_main = urllib.parse.urlparse(page_url)
                if parsed_sub.netloc == parsed_main.netloc and full_sub not in details["subpages"]:
                    details["subpages"].append(full_sub)

    return details


def crawl_search_engine_results(
    category: str = "All Categories",
    state: str = "",
    query_term: str = "",
    max_results: int = 30,
    deep_scrape: bool = True,
    progress_cb=None
) -> list:
    """Discover real merchant pages, deeply inspect them, and keep only evidence-backed records.

    Search results are leads, not proof of call verification. No synthetic businesses,
    addresses, phone numbers, email addresses, or verification flags are generated.
    """
    from html.parser import HTMLParser
    from urllib.parse import urljoin, urlparse, parse_qs, unquote
    from urllib.request import Request, urlopen
    import json
    import re
    import time

    negative = NEGATIVE_FILTER_PATTERN
    product_terms = re.compile(
        r"\b(supplement|sports nutrition|whey protein|protein powder|creatine|pre[- ]workout|"
        r"amino acid|bcaa|mass gainer|nutrition store|protein store|fitness supplement)\b",
        re.IGNORECASE,
    )
    gym_terms = re.compile(r"\b(gym|fitness centre|fitness center|crossfit|personal training)\b", re.I)
    retail_terms = re.compile(r"\b(buy now|add to cart|shop now|order online|store locator|retailer|supplement store|nutrition store|products|product catalogue|product catalog)\b", re.I)
    phone_pattern = re.compile(r"(?<!\w)(?:\+?91[\s().-]*)?(?:\d[\s().-]*){10,13}(?!\w)")
    email_pattern = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
    }

    class PageParser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.title_parts = []
            self.text_parts = []
            self.links = []
            self.in_title = False
            self.skip_depth = 0
            self.address_depth = 0
            self.address_parts = []
            self.jsonld_parts = []
            self.in_jsonld = False

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "title":
                self.in_title = True
            if tag in {"script", "style", "noscript", "svg"}:
                self.skip_depth += 1
                if tag == "script" and "ld+json" in str(attrs.get("type", "")).casefold():
                    self.in_jsonld = True
            if tag == "address":
                self.address_depth += 1
            if tag == "a" and attrs.get("href"):
                self.links.append((attrs.get("href", ""), attrs.get("aria-label", "")))
            if tag == "meta":
                key = str(attrs.get("property") or attrs.get("name") or "").casefold()
                value = str(attrs.get("content") or "").strip()
                if value and key in {"og:title", "og:site_name", "description"}:
                    self.text_parts.append(value)

        def handle_endtag(self, tag):
            if tag == "title":
                self.in_title = False
            if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
                self.skip_depth -= 1
                if tag == "script":
                    self.in_jsonld = False
            if tag == "address" and self.address_depth:
                self.address_depth -= 1

        def handle_data(self, data):
            value = " ".join(str(data or "").split())
            if not value:
                return
            if self.in_title:
                self.title_parts.append(value)
            if self.in_jsonld:
                self.jsonld_parts.append(value)
            elif not self.skip_depth:
                self.text_parts.append(value)
            if self.address_depth:
                self.address_parts.append(value)

    def report(message, percent):
        if progress_cb:
            try:
                progress_cb(message, percent)
            except Exception:
                pass

    def get_html(url, timeout=8):
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type.casefold() and "application/xhtml" not in content_type.casefold():
                    return ""
                raw = response.read(2_500_000)
                charset = response.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except Exception:
            return ""

    def parse_search_results(page_html, engine):
        parser = PageParser()
        try:
            parser.feed(page_html)
        except Exception:
            return []
        links = []
        # Search engine anchors are filtered to external result destinations only.
        for href, label in parser.links:
            href = unquote(href).strip()
            parsed = urlparse(href)
            host_before_decode = parsed.netloc.casefold()
            if engine == "duckduckgo" and (
                href.startswith("/l/?") or
                (host_before_decode.endswith("duckduckgo.com") and parsed.path == "/l/")
            ):
                query = parse_qs(parsed.query)
                href = (query.get("uddg") or [""])[0]
            elif engine == "bing" and (
                href.startswith("/ck/a") or
                (host_before_decode.endswith("bing.com") and parsed.path.startswith("/ck/a"))
            ):
                query = parse_qs(parsed.query)
                href = (query.get("u") or [""])[0]
                if href.startswith("a1"):
                    import base64
                    try:
                        href = base64.urlsafe_b64decode(href[2:] + "==").decode("utf-8", errors="ignore")
                    except Exception:
                        href = ""
            parsed = urlparse(href)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            host = parsed.netloc.casefold()
            if any(x in host for x in ("duckduckgo.com", "bing.com", "google.com", "microsoft.com")):
                continue
            if any(href.rstrip("/") == existing[0].rstrip("/") for existing in links):
                continue
            links.append((href, label))
        return links

    # This directory is specifically for product-selling stores, not gyms.
    # Keep existing category choices in the UI, but only store leads can enter this directory.
    cat = (category or "Pure Product Selling Stores").casefold()
    store_only = True
    base_query = query_term.strip() or "sports nutrition supplement store whey protein creatine"
    kind, default_category = "Store", "Sports nutrition / supplement retailer"

    region = str(state or "").strip()
    if region.casefold() in {"all states / uts", "all states", "all india"}:
        region = ""
    location = region or "India"
    base_terms = [
        base_query,
        "sports nutrition retailer " + location,
        "whey protein creatine supplement shop " + location,
        "sports supplements store full address " + location,
        "authorized sports nutrition retailer " + location,
    ]
    if query_term.strip():
        base_terms.insert(0, query_term.strip() + " " + location)
    # Keep the query set bounded while still using multiple independent result pages.
    queries = list(dict.fromkeys(" ".join(q.split()) for q in base_terms))[:6]
    result_links = []
    seen_urls = set()
    for index, query in enumerate(queries):
        report(f"Searching independent web index {index + 1}/{len(queries)}...", 10 + int(index * 35 / max(1, len(queries))))
        encoded = urllib.parse.quote_plus(query)
        for engine, url in (
            ("duckduckgo", f"https://html.duckduckgo.com/html/?q={encoded}"),
            ("bing", f"https://www.bing.com/search?q={encoded}&count=20"),
        ):
            html_doc = get_html(url)
            if not html_doc:
                continue
            for href, _label in parse_search_results(html_doc, engine):
                canonical = href.split("#", 1)[0].rstrip("/")
                if canonical not in seen_urls:
                    seen_urls.add(canonical)
                    result_links.append(canonical)
        # Be courteous to public search endpoints.
        time.sleep(0.25)

    found = []
    seen_names = set()
    crawl_limit = max(60, min(180, max_results * 4))
    for index, url in enumerate(result_links[:crawl_limit]):
        if len(found) >= max_results:
            break
        report(f"Inspecting merchant page {index + 1}/{min(len(result_links), crawl_limit)}...", 45 + int(index * 50 / max(1, min(len(result_links), crawl_limit))))
        page_html = get_html(url) if deep_scrape else ""
        if not page_html:
            continue
        parser = PageParser()
        try:
            parser.feed(page_html)
        except Exception:
            continue
        title = " ".join(parser.title_parts).strip()
        text_blob = " ".join(parser.text_parts)
        address_text = " ".join(parser.address_parts).strip()
        if not text_blob or negative.search(title + " " + text_blob[:12000]):
            continue
        page_evidence = title + " " + text_blob[:20000]
        if not product_terms.search(page_evidence):
            continue
        if not retail_terms.search(page_evidence):
            continue
        # Exclude gyms and training studios even if they mention supplements in blogs.
        if gym_terms.search(title) or gym_terms.search(text_blob[:1800]):
            if not re.search(r"\b(supplement store|nutrition store|retailer|shop supplements|buy supplements|protein store)\b", page_evidence, re.I):
                continue

        business_name = title.split("|")[0].split(" - ")[0].split(" — ")[0].strip()
        business_name = re.sub(r"\s+", " ", business_name).strip(" -|•")
        if not business_name or len(business_name) < 3:
            business_name = urlparse(url).netloc.removeprefix("www.")
        name_key = business_name.casefold()
        if name_key in seen_names:
            continue

        address = address_text
        # Parse schema.org JSON-LD to extract real PostalAddress values when available.
        for raw_json in parser.jsonld_parts:
            try:
                payload = json.loads(raw_json)
            except Exception:
                continue
            stack = payload if isinstance(payload, list) else [payload]
            while stack:
                obj = stack.pop()
                if isinstance(obj, list):
                    stack.extend(obj)
                elif isinstance(obj, dict):
                    typ = obj.get("@type", "")
                    if isinstance(typ, list):
                        typ = " ".join(typ)
                    if any(t in str(typ).casefold() for t in ("localbusiness", "store", "organization", "sportsactivitylocation")):
                        candidate = obj.get("address")
                        if isinstance(candidate, dict):
                            address = ", ".join(str(candidate.get(k) or "").strip() for k in (
                                "streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry"
                            ) if str(candidate.get(k) or "").strip())
                        elif isinstance(candidate, str):
                            address = candidate.strip()
                    stack.extend(v for v in obj.values() if isinstance(v, (dict, list)))
        if not address:
            # Accept explicit street address-like text, not merely a city or state.
            match = re.search(r"(?i)(?:address\s*[:\-]?\s*)([^\n]{12,220}(?:\b\d{6}\b))", text_blob)
            if match:
                address = " ".join(match.group(1).split())
        if len(address) < 12 or not re.search(r"\b\d{6}\b", address):
            continue
        if negative.search(address):
            continue

        parsed_url = urlparse(url)
        city = ""
        state_name = region
        if not city:
            for token in ("Mumbai", "Delhi", "Bengaluru", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Visakhapatnam", "Vijayawada", "Gurugram", "Faridabad", "Dehradun", "Patna", "Indore", "Bhopal", "Cuttack", "Bhubaneswar", "Kanpur", "Chandigarh"):
                if re.search(r"\b" + re.escape(token) + r"\b", address, re.I):
                    city = token
                    break
        phone_match = phone_pattern.search(text_blob)
        phone = phone_match.group(0).strip() if phone_match else ""
        email_match = email_pattern.search(text_blob)
        email = email_match.group(0).strip() if email_match else ""
        maps_link = ""
        for href, _label in parser.links:
            absolute = urljoin(url, href)
            if "google." in urlparse(absolute).netloc.casefold() and "maps" in absolute.casefold():
                maps_link = absolute
                break
        if not maps_link:
            query = ", ".join(x for x in (business_name, address, "India") if x)
            maps_link = "https://www.google.com/maps/search/?" + urllib.parse.urlencode({"api": "1", "query": query})
        seen_names.add(name_key)
        found.append({
            "kind": kind,
            "business_name": business_name,
            "business_category": default_category,
            "state": state_name,
            "city": city,
            "area": "",
            "phone": phone,
            "email": email,
            "address": address,
            "maps": maps_link,
            "website": url,
            "source_name": "Deep Web Scraper",
            "source_url": url,
            "source_type": "Public merchant page",
            "source_checked_at": date.today().isoformat(),
            "source_status": "Public product listing; not call-verified",
            "verified": "No",
            "notes": "Product-selling evidence and a full postal address found on the linked public page.",
        })
    report(f"Deep search complete: {len(found)} evidence-backed records; no synthetic records added.", 100)
    return found


class WebScraperWorker(QThread):
    """Background worker to deeply scrape verified gyms and supplement stores across India."""
    progress = Signal(str, int)
    finished = Signal(list, str)

    def __init__(self, region="", query_term="", category_type="Pure Product Selling Stores", deep_scrape=True, parent=None):
        super().__init__(parent)
        self.region = region
        self.category_type = category_type or "Pure Product Selling Stores"
        self.query_term = query_term or ""
        self.deep_scrape = deep_scrape

    def run(self):
        """Execute deep search across public search engines and merchant websites."""
        try:
            found = crawl_search_engine_results(
                category=self.category_type,
                state=self.region,
                query_term=self.query_term,
                max_results=40,
                deep_scrape=self.deep_scrape,
                progress_cb=self.progress.emit
            )
            self.finished.emit(found, "")
        except Exception as exc:
            self.finished.emit([], str(exc))


class WebScraperDialog(QDialog):
    """Deep multi-engine web scraper for Gyms, Pure Product Selling Stores, and Gyms Selling Products."""
    def __init__(self, parent=None, default_state="All States / UTs"):
        super().__init__(parent)
        self.setWindowTitle("🌐 Deep Web Scraper — Gyms & Supplement Stores")
        self.setMinimumSize(720, 520)
        self.results = []

        root = QVBoxLayout(self)
        root.setSpacing(8)
        self.tabs = QTabWidget()
        search_page = QWidget()
        layout = QVBoxLayout(search_page)
        layout.setSpacing(10)

        info = QLabel(
            "<b>Evidence-Based Deep Web Search for Product-Selling Stores</b><br>"
            "<span style='color: #64748B;'>Select business type (Gym, Pure Supplement Store, or Gym Selling Products). "
            "Deep crawler visits merchant and gym web domains, extracts authentic contact phone numbers, "
            "verified email addresses, physical postal addresses, and Google Maps location links.<br>"
            "<b>Strict Exclusions:</b> Automatically filters out pharmacies, chemists, medical stores, ayurvedic/herbal shops, and HealthKart.</span>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Category and Region selection
        form_grid = QVBoxLayout()
        form_grid.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Business Type:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Pure Product Selling Stores",
            "Gym",
            "Gyms which sell products also",
            "All Categories"
        ])
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        row1.addWidget(self.category_combo, 2)

        row1.addWidget(QLabel("Region:"))
        self.state_combo = QComboBox()
        self.state_combo.addItem("All States / UTs")
        self.state_combo.addItems(INDIA_REGIONS)
        if default_state in INDIA_REGIONS:
            self.state_combo.setCurrentText(default_state)
        row1.addWidget(self.state_combo, 2)
        form_grid.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Keywords:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Search query terms (e.g. supplement store sports nutrition)")
        self.keyword_input.setText("supplement store sports nutrition whey protein")
        self.keyword_input.returnPressed.connect(self._start_scraping)
        row2.addWidget(self.keyword_input, 1)
        form_grid.addLayout(row2)

        # Deep Scraping Option
        self.deep_scrape_cb = QPushButton("🔍 Deep Scraping Enabled (Extracts Phones, Emails, Full Address & Maps)")
        self.deep_scrape_cb.setCheckable(True)
        self.deep_scrape_cb.setChecked(True)
        self.deep_scrape_cb.setStyleSheet("font-weight: 700; color: #0D9488; text-align: left; background: transparent; border: none; padding: 2px;")
        form_grid.addWidget(self.deep_scrape_cb)

        layout.addLayout(form_grid)

        self.engine_status = QLabel("Engines: DuckDuckGo · Bing · Deep Merchant Web Crawler")
        self.engine_status.setStyleSheet("font-weight: 700; color: #0D9488; font-size: 8.5pt;")
        layout.addWidget(self.engine_status)

        self.btn_start = QPushButton("🚀 Run Deep Web Scraping")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet("font-weight: 800; font-size: 10pt; background: #2563EB; color: white; border-radius: 6px;")
        self.btn_start.clicked.connect(self._start_scraping)
        layout.addWidget(self.btn_start)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Deep web scraping logs with phone, email, and map extraction will appear here in real-time...")
        layout.addWidget(self.log_view, 1)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("💾 Save Discovered Leads to App DB")
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("font-weight: 700; background: #059669; color: white; border-radius: 6px; min-height: 34px;")
        self.btn_save.clicked.connect(self.accept)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_save, 2)
        btn_row.addWidget(self.btn_close, 1)
        layout.addLayout(btn_row)

        self.tabs.addTab(search_page, "Deep Web Scraper")
        root.addWidget(self.tabs)

    def _on_category_changed(self, cat):
        cat_lower = cat.casefold()
        if "pure" in cat_lower:
            self.keyword_input.setText("supplement store sports nutrition whey protein")
        elif "also" in cat_lower or "hybrid" in cat_lower:
            self.keyword_input.setText("gym supplement counter protein bar pro shop")
        elif "gym" in cat_lower:
            self.keyword_input.setText("gym fitness centre health club")
        else:
            self.keyword_input.setText("supplement store gym nutrition protein")

    def _start_scraping(self):
        region = self.state_combo.currentText()
        cat = self.category_combo.currentText()
        query = self.keyword_input.text().strip()
        deep = self.deep_scrape_cb.isChecked()
        self.btn_start.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_view.append(f"Starting deep scraping for {cat} in {region} ({query})...")
        self.worker = WebScraperWorker(region=region, query_term=query, category_type=cat, deep_scrape=deep)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, msg, pct):
        self.progress_bar.setValue(pct)
        self.log_view.append(msg)

    def _on_finished(self, records, error):
        self.btn_start.setEnabled(True)
        if error:
            self.log_view.append(f"⚠️ Search finished with notes: {error}")
        self.results = records
        self.log_view.append(
            f"\n✅ Scraping finished: {len(records)} unique genuine business leads found with contact details."
        )
        for record in records[:10]:
            p = record.get('phone') or 'No phone'
            e = record.get('email') or 'No email'
            k = record.get('kind') or 'Store'
            self.log_view.append(f"  • [{k}] {record['business_name']} | 📞 {p} | ✉️ {e} | 📍 {record['address'][:45]}")
        if len(records) > 10:
            self.log_view.append(f"  ... and {len(records) - 10} more.")
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
        ("Email", "email"),
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
        ("State / UT / Island", "state"),
        ("Territory Type", "territory_type"),
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
        if db is not None:
            try:
                sanitize_prospect_database_records(db)
                cleanup_duplicate_prospects(db)
            except Exception:
                pass
        self.records = load_saved_prospects(db) if db is not None else []
        self.preview_records = []
        self.dashboard_counts = {}
        self.dashboard_total = None
        self.database_filename = ""
        self.dashboard_filename = ""

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        outer_scroll = QScrollArea()
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        outer_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        container = QWidget()
        container.setObjectName("customerProspectsContainer")
        root = QVBoxLayout(container)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Header Title & Subtitle
        heading = QVBoxLayout()
        title = QLabel("Store Directory & Market Coverage")
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

        # Prominent View Switcher Dropdown (Store Directory vs Regional Dashboard)
        view_nav_card = QFrame()
        view_nav_card.setObjectName("prospectViewNavCard")
        view_nav_card.setStyleSheet(
            "QFrame#prospectViewNavCard {"
            "  background: rgba(30, 41, 59, 0.85);"
            "  border: 1.5px solid rgba(59, 130, 246, 0.4);"
            "  border-radius: 8px;"
            "  padding: 6px 12px;"
            "}"
        )
        view_nav_layout = QHBoxLayout(view_nav_card)
        view_nav_layout.setContentsMargins(10, 6, 10, 6)
        view_nav_layout.setSpacing(12)

        view_icon_label = QLabel("👁️ Select View:")
        view_icon_label.setObjectName("prospectViewLabel")
        view_icon_label.setStyleSheet("font-size: 10pt; font-weight: 800; color: #38BDF8;")
        view_nav_layout.addWidget(view_icon_label)

        self.view_selector = QComboBox()
        self.view_selector.setObjectName("prospectViewSelector")
        self.view_selector.addItems([
            "🏪 Store Directory (Central Stores & Retail Directory)",
            "🗺️ Regional Dashboard (36 States, UTs & Island Coverage)"
        ])
        self.view_selector.setMinimumHeight(36)
        self.view_selector.setToolTip("Switch active view between Store Directory and Regional Dashboard")
        self.view_selector.setStyleSheet(
            "QComboBox { font-size: 9.5pt; font-weight: 700; color: #FFFFFF; background: #2563EB; "
            "border: 1.5px solid #60A5FA; border-radius: 6px; padding: 4px 14px; min-width: 320px; } "
            "QComboBox:hover { background: #1D4ED8; border-color: #93C5FD; } "
            "QComboBox QAbstractItemView { background: #0F172A; color: #FFFFFF; selection-background-color: #2563EB; selection-color: #FFFFFF; font-size: 9.5pt; font-weight: 600; padding: 4px; }"
        )
        self.view_selector.currentIndexChanged.connect(self._on_view_selector_changed)
        view_nav_layout.addWidget(self.view_selector, 0)

        view_nav_hint = QLabel("Use dropdown to switch views. All print and export options are at the bottom.")
        view_nav_hint.setStyleSheet("font-size: 8.5pt; color: #CBD5E1; font-style: italic;")
        view_nav_layout.addWidget(view_nav_hint, 1)

        root.addWidget(view_nav_card)

        # Single Unified Action Card: 1-Tap Deep Web Scraping & Continuous Master Sync
        action_card = QFrame()
        action_card.setObjectName("prospectActionCard")
        action_card.setStyleSheet(
            "QFrame#prospectActionCard {"
            "  background: rgba(30, 41, 59, 0.7);"
            "  border: 1px solid rgba(255, 255, 255, 0.08);"
            "  border-radius: 8px;"
            "  padding: 6px 12px;"
            "}"
        )
        action_layout = QHBoxLayout(action_card)
        action_layout.setContentsMargins(10, 8, 10, 8)
        action_layout.setSpacing(12)

        self.btn_one_tap_scrape_and_update = QPushButton("⚡ 1-Tap Deep Web Scraping & Master Update")
        self.btn_one_tap_scrape_and_update.setMinimumHeight(40)
        self.btn_one_tap_scrape_and_update.setStyleSheet(
            "QPushButton {"
            "  font-size: 10.5pt; font-weight: 800; color: #FFFFFF;"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #7C3AED);"
            "  border: none; border-radius: 6px; padding: 0 18px;"
            "}"
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #6D28D9); }"
        )
        self.btn_one_tap_scrape_and_update.setToolTip(
            "1-Tap action: Deep scrapes genuine supplement stores and gyms across India, "
            "resolves conflicts and appends to local database without deleting data, "
            "auto-saves a fresh master Excel snapshot to Downloads, and continuously syncs to Google Sheets."
        )
        self.btn_one_tap_scrape_and_update.clicked.connect(self.one_tap_scrape_and_master_update)
        action_layout.addWidget(self.btn_one_tap_scrape_and_update)

        self.sync_status_badge = QLabel("🟢 Continuous Sync: Active (Conflict-Free)")
        self.sync_status_badge.setStyleSheet(
            "font-size: 9pt; font-weight: 700; color: #34D399; background: rgba(16, 185, 129, 0.15); "
            "border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 4px; padding: 6px 12px;"
        )
        action_layout.addWidget(self.sync_status_badge)

        self.snapshot_badge = QLabel("💾 Master Backup: Downloads/Google_Sheets_Master_Database.xlsx")
        self.snapshot_badge.setStyleSheet("font-size: 8.5pt; color: #94A3B8;")
        action_layout.addWidget(self.snapshot_badge, 1)

        # Retain density_combo on self for API/test compatibility (hidden from UI per user request)
        self.density_combo = QComboBox()
        self.density_combo.addItems(["Compact", "Comfortable", "Dense"])
        self.density_combo.setVisible(False)
        self.density_combo.currentTextChanged.connect(self._on_density_changed)

        root.addWidget(action_card)

        # Retain internal compatibility references
        self.load_database_button = QPushButton("Load Local Workbook")
        self.load_database_button.clicked.connect(self.choose_database_workbook)
        self.load_dashboard_button = QPushButton("Load Store Dashboard")
        self.load_dashboard_button.clicked.connect(self.choose_dashboard_workbook)
        self.scrape_web_button = QPushButton("Scrape Web Stores")
        self.scrape_web_button.clicked.connect(self.open_web_scrape_dialog)
        self.load_master_india_button = QPushButton("Load Store Directory (All States)")
        self.load_master_india_button.clicked.connect(self.load_master_india_stores)
        self.sync_google_sheets_button = QPushButton("Sync Google Sheets")
        self.sync_google_sheets_button.clicked.connect(self.sync_google_sheets)
        self.import_workbook_button = QPushButton("Save Workbook Rows")
        self.import_workbook_button.clicked.connect(self.import_workbook_to_app_db)
        self.database_source_label = QLabel("Database: not loaded")
        self.dashboard_source_label = QLabel("Dashboard: not loaded")
        self.saved_status_label = QLabel("App DB: 0 saved leads")

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

        # Tabs: Store Directory & Regional Dashboard
        self.pages = QTabWidget()
        self.pages.addTab(self._build_leads_page(), "🏪 Store Directory")
        self.pages.addTab(self._build_regional_page(), "🗺️ Regional Dashboard (States / UTs / Islands)")
        self.pages.currentChanged.connect(self._on_pages_tab_changed)
        root.addWidget(self.pages, 1)

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(160)
        self._filter_timer.timeout.connect(self.apply_filters)

        # Continuous background sync timer (every 60s, silent, conflict-free)
        self._auto_sync_timer = QTimer(self)
        self._auto_sync_timer.setInterval(60000)
        self._auto_sync_timer.timeout.connect(self._run_silent_continuous_sync)
        self._auto_sync_timer.start()

        outer_scroll.setWidget(container)
        main_layout.addWidget(outer_scroll)
        self.outer_scroll_area = outer_scroll

        self.apply_theme("night")
        self._refresh_views()

    def _on_view_selector_changed(self, index):
        if hasattr(self, "pages") and 0 <= index < self.pages.count():
            self.pages.blockSignals(True)
            self.pages.setCurrentIndex(index)
            self.pages.blockSignals(False)

    def _on_pages_tab_changed(self, index):
        if hasattr(self, "view_selector") and 0 <= index < self.view_selector.count():
            self.view_selector.blockSignals(True)
            self.view_selector.setCurrentIndex(index)
            self.view_selector.blockSignals(False)

    def _on_print_export_changed(self, index):
        if index <= 0:
            return
        self.print_export_combo.blockSignals(True)
        self.print_export_combo.setCurrentIndex(0)
        self.print_export_combo.blockSignals(False)

        if index == 1:
            self.open_print_preview()
        elif index == 2:
            self.open_store_details_preview()
        elif index == 3:
            self.open_regional_print_preview()
        elif index == 4:
            self.print_leads()
        elif index == 5:
            self.export_xlsx()
        elif index == 6:
            self.export_pdf()
        elif index == 7:
            self.export_csv()
        elif index == 8:
            self.export_doc()
        elif index == 9:
            self.open_export_folder()

    def _on_more_filters_changed(self, text):
        if text == "Has Phone / Email":
            self.contact_filter.setCurrentText("Has phone/email")
            self.website_filter.setCurrentText("All websites")
            self.verification_filter.setCurrentText("All verification")
        elif text == "Missing Contact":
            self.contact_filter.setCurrentText("Missing contact")
            self.website_filter.setCurrentText("All websites")
            self.verification_filter.setCurrentText("All verification")
        elif text == "Has Website":
            self.contact_filter.setCurrentText("All contacts")
            self.website_filter.setCurrentText("Has website")
            self.verification_filter.setCurrentText("All verification")
        elif text == "Missing Website":
            self.contact_filter.setCurrentText("All contacts")
            self.website_filter.setCurrentText("Missing website")
            self.verification_filter.setCurrentText("All verification")
        elif text == "Verified Only":
            self.contact_filter.setCurrentText("All contacts")
            self.website_filter.setCurrentText("All websites")
            self.verification_filter.setCurrentText("Verified")
        elif text == "Unverified Only":
            self.contact_filter.setCurrentText("All contacts")
            self.website_filter.setCurrentText("All websites")
            self.verification_filter.setCurrentText("Unverified")
        else:
            self.contact_filter.setCurrentText("All contacts")
            self.website_filter.setCurrentText("All websites")
            self.verification_filter.setCurrentText("All verification")
        self.apply_filters()

    def _build_leads_page(self):
        page = QWidget()
        self.leads_page = page
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Print & Export Actions (Dropdown and fallback buttons)
        self.print_export_combo = QComboBox()
        self.print_export_combo.addItem("🖨️ Print & Export ▾")
        self.print_export_combo.addItem("👁️ Full Print Preview")
        self.print_export_combo.addItem("🏢 Print Store Details")
        self.print_export_combo.addItem("📊 Print Regional Dashboard")
        self.print_export_combo.addItem("🖨️ Direct Print / PDF")
        self.print_export_combo.addItem("📗 Export to Excel (.xlsx)")
        self.print_export_combo.addItem("📄 Export to PDF (.pdf)")
        self.print_export_combo.addItem("📊 Export to CSV (.csv)")
        self.print_export_combo.addItem("📝 Export to Word (.doc)")
        self.print_export_combo.addItem("📂 Open Export Folder")
        self.print_export_combo.setToolTip("Print Center: Print preview, direct print, and exports in Excel, PDF, CSV, Word")
        self.print_export_combo.currentIndexChanged.connect(self._on_print_export_changed)
        self.print_export_combo.setStyleSheet(
            "QComboBox { font-size: 8.5pt; font-weight: 700; color: #FFFFFF; background: #2563EB; "
            "border: 1px solid #3B82F6; border-radius: 6px; padding: 4px 10px; min-width: 140px; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { background: #1E293B; color: #F8FAFC; selection-background-color: #2563EB; }"
        )

        # Retain explicit QPushButton instances for backward compatibility & direct invocation
        self.btn_print_preview = QPushButton("🖨️ Print Preview")
        self.btn_print_preview.clicked.connect(self.open_print_preview)
        self.btn_print = QPushButton("🖨️ Print")
        self.btn_print.clicked.connect(self.print_leads)
        self.btn_pdf = QPushButton("📄 PDF")
        self.btn_pdf.clicked.connect(self.export_pdf)
        self.btn_csv = QPushButton("📊 CSV")
        self.btn_csv.clicked.connect(self.export_csv)
        self.btn_xlsx = QPushButton("📗 Excel")
        self.btn_xlsx.clicked.connect(self.export_xlsx)
        self.btn_doc = QPushButton("📝 Word")
        self.btn_doc.clicked.connect(self.export_doc)
        self.btn_store_details = QPushButton("🏢 Store Details")
        self.btn_store_details.setToolTip("Print or preview detailed dossier for the selected store")
        self.btn_store_details.clicked.connect(self.open_store_details_preview)
        self.btn_dashboard_print = QPushButton("📊 Dashboard")
        self.btn_dashboard_print.setToolTip("Print or preview the Regional Dashboard directly")
        self.btn_dashboard_print.clicked.connect(self.open_regional_print_preview)
        self.btn_folder = QPushButton("📂 Open Folder")
        self.btn_folder.clicked.connect(self.open_export_folder)

        # Row 1: Primary Search, Category, State, More Filters
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search business name, phone, address, city…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(lambda _text: self._filter_timer.start())
        toolbar.addWidget(self.search_input, 2)

        self.kind_filter = QComboBox()
        self.kind_filter.addItems(["All types", "Pure Product Selling Stores", "Gym", "Gyms which sell products also"])
        # Store Directory opens on product-selling stores by default. Existing filter
        # choices are preserved so users can still inspect other record types.
        self.kind_filter.setCurrentText("Pure Product Selling Stores")
        self.kind_filter.setToolTip("Filter by store / gym category")
        self.kind_filter.currentTextChanged.connect(lambda _text: self.apply_filters())
        toolbar.addWidget(self.kind_filter, 1)

        self.state_filter = QComboBox()
        self.state_filter.addItem("All States / UTs")
        self.state_filter.setToolTip("Filter by State, UT, or Island")
        self.state_filter.currentTextChanged.connect(lambda _text: self.apply_filters())
        toolbar.addWidget(self.state_filter, 1)

        # More Filters (Contacts, Websites, Verification status)
        self.more_filters = QComboBox()
        self.more_filters.addItems([
            "Filter: All Records",
            "Has Phone / Email",
            "Missing Contact",
            "Has Website",
            "Missing Website",
            "Verified Only",
            "Unverified Only",
        ])
        self.more_filters.setToolTip("Filter by Contact, Website, or Verification status")
        self.more_filters.currentTextChanged.connect(self._on_more_filters_changed)
        toolbar.addWidget(self.more_filters, 1)

        self.btn_top_print = QPushButton("🖨️ Print")
        self.btn_top_print.setToolTip("Print current store directory list")
        self.btn_top_print.setStyleSheet(
            "QPushButton { font-size: 9pt; font-weight: 700; color: #FFFFFF; background: #2563EB; "
            "border: 1px solid #3B82F6; border-radius: 6px; padding: 4px 14px; min-height: 32px; } "
            "QPushButton:hover { background: #1D4ED8; }"
        )
        self.btn_top_print.clicked.connect(self.print_leads)
        toolbar.addWidget(self.btn_top_print, 0)

        layout.addLayout(toolbar)

        # Retain underlying contact, website, verification filters for compatibility
        self.contact_filter = QComboBox()
        self.contact_filter.addItems(["All contacts", "Has phone/email", "Missing contact"])
        self.contact_filter.currentTextChanged.connect(lambda _text: self.apply_filters())

        self.website_filter = QComboBox()
        self.website_filter.addItems(["All websites", "Has website", "Missing website"])
        self.website_filter.currentTextChanged.connect(lambda _text: self.apply_filters())

        self.verification_filter = QComboBox()
        self.verification_filter.addItems(["All verification", "Verified", "Unverified"])
        self.verification_filter.currentTextChanged.connect(lambda _text: self.apply_filters())

        # Row 2: Consolidated Exclude Dropdown + Keyword Search + Clear Button + Results Counter
        exclude_bar = QHBoxLayout()
        exclude_bar.setSpacing(8)

        self.exclude_dropdown = QComboBox()
        self.exclude_dropdown.addItem("🚫 Exclude Target: None (Show All)")
        self.exclude_dropdown.addItem("Exclude Category: Pure Product Selling Stores")
        self.exclude_dropdown.addItem("Exclude Category: Gym")
        self.exclude_dropdown.addItem("Exclude Category: Gyms which sell products also")
        self.exclude_dropdown.addItem("🚫 Exclude: Gym + Wellness Centers + Herbal + HealthKart")
        self.exclude_dropdown.addItem("Exclude: Missing Phone / Email")
        self.exclude_dropdown.addItem("Exclude: Missing Website")
        self.exclude_dropdown.addItem("Exclude: Unverified Leads")
        self.exclude_dropdown.setToolTip("Select any category, territory, or condition to exclude from the directory")
        self.exclude_dropdown.currentTextChanged.connect(lambda _text: self.apply_filters())
        self.exclude_dropdown.setStyleSheet(
            "QComboBox { font-size: 8.5pt; font-weight: 600; color: #FCA5A5; background: rgba(239, 68, 68, 0.12); "
            "border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 6px; padding: 4px 10px; min-width: 220px; }"
        )
        exclude_bar.addWidget(self.exclude_dropdown, 0)

        self.exclude_keyword = QLineEdit()
        self.exclude_keyword.setPlaceholderText("🚫 Exclude keyword, name, district, or city…")
        self.exclude_keyword.setClearButtonEnabled(True)
        self.exclude_keyword.textChanged.connect(lambda _text: self._filter_timer.start())
        self.exclude_keyword.setStyleSheet(
            "QLineEdit { font-size: 8.5pt; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 4px 8px; }"
        )
        exclude_bar.addWidget(self.exclude_keyword, 1)

        self.btn_clear_excludes = QPushButton("✖ Clear Exclude")
        self.btn_clear_excludes.setToolTip("Clear all negative / exclude filters")
        self.btn_clear_excludes.clicked.connect(self.clear_exclude_filters)
        self.btn_clear_excludes.setStyleSheet(
            "QPushButton { font-size: 8.5pt; font-weight: 600; background: rgba(239, 68, 68, 0.18); "
            "border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 6px; padding: 4px 10px; color: #FCA5A5; } "
            "QPushButton:hover { background: rgba(239, 68, 68, 0.3); color: #FFFFFF; }"
        )
        exclude_bar.addWidget(self.btn_clear_excludes)

        # Backward compatibility exclude widgets
        self.exclude_state = QComboBox()
        self.exclude_state.addItem("Exclude State: None")
        self.exclude_state.currentTextChanged.connect(lambda _text: self.apply_filters())

        self.exclude_kind = QComboBox()
        self.exclude_kind.addItems(["Exclude Category: None", "Pure Product Selling Stores", "Gym", "Gyms which sell products also"])
        self.exclude_kind.currentTextChanged.connect(lambda _text: self.apply_filters())

        self.exclude_name = QLineEdit()
        self.exclude_name.textChanged.connect(lambda _text: self._filter_timer.start())

        self.exclude_district = QLineEdit()
        self.exclude_district.textChanged.connect(lambda _text: self._filter_timer.start())

        self.exclude_custom = QLineEdit()
        self.exclude_custom.textChanged.connect(lambda _text: self._filter_timer.start())

        exclude_bar.addSpacing(12)
        self.results_label = QLabel("Showing 0 stores")
        self.results_label.setStyleSheet("font-size: 8.5pt; font-weight: 600; color: #94A3B8;")
        exclude_bar.addWidget(self.results_label, 0)
        exclude_bar.addStretch(1)

        layout.addLayout(exclude_bar)

        # Data Table
        self.leads_table = QTableWidget(0, len(self.LEAD_COLUMNS))
        self.leads_table.setHorizontalHeaderLabels([label for label, _key in self.LEAD_COLUMNS])
        self.leads_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.leads_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.leads_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.leads_table.setWordWrap(True)
        self.leads_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.leads_table.verticalHeader().setVisible(False)
        self.leads_table.setAlternatingRowColors(True)
        self.leads_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.leads_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.leads_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.leads_table.setSortingEnabled(False)
        self.leads_table.setMinimumHeight(420)
        self.leads_table.verticalHeader().setDefaultSectionSize(38)
        self.leads_table.cellDoubleClicked.connect(self.open_source_link)
        for index, width in enumerate((85, 210, 160, 150, 130, 140, 135, 320, 320, 150, 95, 175, 180, 240, 170, 110, 130, 320, 320, 160)):
            self.leads_table.setColumnWidth(index, width)
        layout.addWidget(self.leads_table, 1)

        # Dedicated Print Center & Export Section (at the very bottom / last)
        print_card = QFrame()
        print_card.setObjectName("storeDirectoryPrintCard")
        print_card.setStyleSheet(
            "QFrame#storeDirectoryPrintCard { "
            "  background: rgba(15, 23, 42, 0.90); "
            "  border: 1.5px solid rgba(59, 130, 246, 0.50); "
            "  border-radius: 8px; padding: 8px 14px; "
            "}"
        )
        print_layout = QHBoxLayout(print_card)
        print_layout.setContentsMargins(10, 8, 10, 8)
        print_layout.setSpacing(10)

        print_title = QLabel("🖨️ Print Center & Export:")
        print_title.setStyleSheet("font-size: 9.5pt; font-weight: 800; color: #38BDF8;")
        print_layout.addWidget(print_title)

        print_layout.addWidget(self.print_export_combo, 0)

        for btn in (
            self.btn_print_preview, self.btn_print, self.btn_store_details, self.btn_dashboard_print,
            self.btn_pdf, self.btn_csv, self.btn_xlsx, self.btn_doc, self.btn_folder
        ):
            btn.setStyleSheet(
                "QPushButton { font-size: 8.5pt; font-weight: 700; background: #1E293B; "
                "border: 1px solid #3B82F6; border-radius: 6px; padding: 5px 10px; color: #F8FAFC; min-height: 28px; } "
                "QPushButton:hover { background: #2563EB; color: #FFFFFF; border-color: #60A5FA; }"
            )
            print_layout.addWidget(btn)

        print_note = QLabel("Official Raw Strength Calisthenics Print Center")
        print_note.setStyleSheet("font-size: 8.5pt; color: #CBD5E1; font-style: italic;")
        print_layout.addWidget(print_note, 1)

        layout.addWidget(print_card)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidget(page)
        self.leads_scroll_area = scroll_area
        return scroll_area

    def clear_exclude_filters(self):
        """Reset all negative / exclude filters to show all unexcluded records."""
        if hasattr(self, "exclude_dropdown"):
            self.exclude_dropdown.blockSignals(True)
            self.exclude_dropdown.setCurrentIndex(0)
            self.exclude_dropdown.blockSignals(False)
        if hasattr(self, "exclude_keyword"):
            self.exclude_keyword.blockSignals(True)
            self.exclude_keyword.clear()
            self.exclude_keyword.blockSignals(False)
        if hasattr(self, "exclude_state"):
            self.exclude_state.blockSignals(True)
            self.exclude_state.setCurrentIndex(0)
            self.exclude_state.blockSignals(False)
        if hasattr(self, "exclude_kind"):
            self.exclude_kind.blockSignals(True)
            self.exclude_kind.setCurrentIndex(0)
            self.exclude_kind.blockSignals(False)
        if hasattr(self, "exclude_name"):
            self.exclude_name.blockSignals(True)
            self.exclude_name.clear()
            self.exclude_name.blockSignals(False)
        if hasattr(self, "exclude_district"):
            self.exclude_district.blockSignals(True)
            self.exclude_district.clear()
            self.exclude_district.blockSignals(False)
        if hasattr(self, "exclude_custom"):
            self.exclude_custom.blockSignals(True)
            self.exclude_custom.clear()
            self.exclude_custom.blockSignals(False)
        self.apply_filters()

    def _build_regional_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Territory KPI Cards: clearly separating 28 States, 6 UTs, 2 Island Territories
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        # 1. 28 States Card
        card_states = QFrame()
        card_states.setStyleSheet("background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 8px; padding: 6px 12px;")
        l_s = QVBoxLayout(card_states)
        l_s.setContentsMargins(4, 4, 4, 4)
        l_s.setSpacing(2)
        lbl_s_title = QLabel("🏛️ 28 Indian States")
        lbl_s_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #93C5FD;")
        self.card_states_val = QLabel("28 States (Calculating...)")
        self.card_states_val.setStyleSheet("font-size: 10pt; font-weight: 800; color: #FFFFFF;")
        l_s.addWidget(lbl_s_title)
        l_s.addWidget(self.card_states_val)
        kpi_row.addWidget(card_states, 1)

        # 2. 6 Union Territories Card
        card_ut = QFrame()
        card_ut.setStyleSheet("background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 8px; padding: 6px 12px;")
        l_u = QVBoxLayout(card_ut)
        l_u.setContentsMargins(4, 4, 4, 4)
        l_u.setSpacing(2)
        lbl_u_title = QLabel("🏢 6 Union Territories")
        lbl_u_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #FCD34D;")
        self.card_ut_val = QLabel("6 UTs (Calculating...)")
        self.card_ut_val.setStyleSheet("font-size: 10pt; font-weight: 800; color: #FFFFFF;")
        l_u.addWidget(lbl_u_title)
        l_u.addWidget(self.card_ut_val)
        kpi_row.addWidget(card_ut, 1)

        # 3. 2 Island Territories Card
        card_islands = QFrame()
        card_islands.setStyleSheet("background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 8px; padding: 6px 12px;")
        l_i = QVBoxLayout(card_islands)
        l_i.setContentsMargins(4, 4, 4, 4)
        l_i.setSpacing(2)
        lbl_i_title = QLabel("🏝️ 2 Island Territories")
        lbl_i_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #6EE7B7;")
        self.card_islands_val = QLabel("2 Island UTs (Calculating...)")
        self.card_islands_val.setStyleSheet("font-size: 10pt; font-weight: 800; color: #FFFFFF;")
        l_i.addWidget(lbl_i_title)
        l_i.addWidget(self.card_islands_val)
        kpi_row.addWidget(card_islands, 1)
        layout.addLayout(kpi_row)

        # Filter bar for territory separation
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        filter_lbl = QLabel("Filter Territory:")
        filter_lbl.setStyleSheet("font-weight: 700; color: #E2E8F0; font-size: 9pt;")
        filter_bar.addWidget(filter_lbl)

        self.territory_filter = QComboBox()
        self.territory_filter.addItems([
            "All 36 Regions (Separated by Category)",
            "🏛️ 28 States",
            "🏢 6 Union Territories",
            "🏝️ 2 Island Territories"
        ])
        self.territory_filter.currentTextChanged.connect(lambda _text: self._fill_regional_table())
        filter_bar.addWidget(self.territory_filter, 1)

        self.reconciliation_label = QLabel(
            "Coverage uses saved app database leads. Stores across all 36 States and UTs are tracked against target counts."
        )
        self.reconciliation_label.setWordWrap(True)
        self.reconciliation_label.setObjectName("prospectReconciliation")
        self.reconciliation_label.setStyleSheet("font-size: 8.5pt; font-weight: 600; color: #94A3B8;")
        filter_bar.addWidget(self.reconciliation_label, 2)
        layout.addLayout(filter_bar)

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

        # Dedicated Regional Print Center & Export Section
        regional_print_card = QFrame()
        regional_print_card.setObjectName("regionalDashboardPrintCard")
        regional_print_card.setStyleSheet(
            "QFrame#regionalDashboardPrintCard { "
            "  background: rgba(15, 23, 42, 0.75); "
            "  border: 1px solid rgba(59, 130, 246, 0.35); "
            "  border-radius: 8px; padding: 6px 12px; "
            "}"
        )
        reg_print_layout = QHBoxLayout(regional_print_card)
        reg_print_layout.setContentsMargins(10, 8, 10, 8)
        reg_print_layout.setSpacing(10)

        reg_print_title = QLabel("🖨️ Regional Print Center & Export:")
        reg_print_title.setStyleSheet("font-size: 9pt; font-weight: 700; color: #93C5FD;")
        reg_print_layout.addWidget(reg_print_title)

        self.regional_print_combo = QComboBox()
        self.regional_print_combo.addItem("🖨️ Regional Print & Export ▾")
        self.regional_print_combo.addItem("👁️ Regional Print Preview")
        self.regional_print_combo.addItem("🖨️ Direct Print / PDF")
        self.regional_print_combo.addItem("📗 Export Regional to Excel (.xlsx)")
        self.regional_print_combo.addItem("📄 Export Regional to PDF (.pdf)")
        self.regional_print_combo.addItem("📊 Export Regional to CSV (.csv)")
        self.regional_print_combo.addItem("📂 Open Export Folder")
        self.regional_print_combo.currentIndexChanged.connect(self._on_regional_print_export_changed)
        self.regional_print_combo.setStyleSheet(
            "QComboBox { font-size: 8.5pt; font-weight: 700; color: #FFFFFF; background: #2563EB; "
            "border: 1px solid #3B82F6; border-radius: 6px; padding: 4px 10px; min-width: 140px; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { background: #1E293B; color: #F8FAFC; selection-background-color: #2563EB; }"
        )
        reg_print_layout.addWidget(self.regional_print_combo, 0)

        self.btn_regional_preview = QPushButton("🖨️ Print Preview")
        self.btn_regional_preview.clicked.connect(self.open_regional_print_preview)
        self.btn_regional_print = QPushButton("🖨️ Print")
        self.btn_regional_print.clicked.connect(self.print_regional_dashboard)
        self.btn_regional_folder = QPushButton("📂 Open Folder")
        self.btn_regional_folder.clicked.connect(self.open_export_folder)

        for btn in (self.btn_regional_preview, self.btn_regional_print, self.btn_regional_folder):
            btn.setStyleSheet(
                "QPushButton { font-size: 8.5pt; font-weight: 600; background: rgba(37, 99, 235, 0.2); "
                "border: 1px solid #3B82F6; border-radius: 6px; padding: 4px 10px; color: #93C5FD; } "
                "QPushButton:hover { background: #2563EB; color: #FFFFFF; }"
            )
            reg_print_layout.addWidget(btn)

        reg_print_note = QLabel("Replicates official Raw Strength Calisthenics Print Center")
        reg_print_note.setStyleSheet("font-size: 8pt; color: #64748B; font-style: italic;")
        reg_print_layout.addWidget(reg_print_note, 1)

        layout.addWidget(regional_print_card)

        self.region_table.verticalHeader().setDefaultSectionSize(38)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidget(page)
        self.regional_scroll_area = scroll_area
        return scroll_area

    def _get_visible_regional_rows(self):
        """Retrieve current rows displayed in the regional summary table."""
        if hasattr(self, "last_regional_display_rows") and self.last_regional_display_rows:
            return list(self.last_regional_display_rows)
        rows = build_regional_summary(self.records, self.dashboard_counts, include_all_regions=True)
        source_counts = defaultdict(lambda: {"web": 0, "workbook": 0})
        for record in self.records:
            raw_state = str(record.get("state") or "").strip()
            if not raw_state:
                continue
            is_web = str(record.get("source_type") or "").casefold().startswith("official web")
            st_list = [s.strip() for s in raw_state.split(",") if s.strip()]
            for sub_st in st_list:
                clean_st = normalise_state(sub_st)
                if clean_st and clean_st in INDIA_REGIONS:
                    if is_web:
                        source_counts[clean_st]["web"] += 1
                    else:
                        source_counts[clean_st]["workbook"] += 1
        for row in rows:
            row["web_leads"] = source_counts[row["state"]]["web"]
            row["workbook_leads"] = source_counts[row["state"]]["workbook"]
            row["territory_type"] = territory_type(row["state"])
        return rows

    def _on_regional_print_export_changed(self, index):
        if index <= 0:
            return
        self.regional_print_combo.blockSignals(True)
        self.regional_print_combo.setCurrentIndex(0)
        self.regional_print_combo.blockSignals(False)

        if index == 1:
            self.open_regional_print_preview()
        elif index == 2:
            self.print_regional_dashboard()
        elif index == 3:
            self.export_regional_xlsx()
        elif index == 4:
            self.export_regional_pdf()
        elif index == 5:
            self.export_regional_csv()
        elif index == 6:
            self.open_export_folder()

    def open_regional_print_preview(self):
        """Open full-page print preview dialog for Regional Dashboard replicating Print Center."""
        rows = self._get_visible_regional_rows()
        if not rows:
            QMessageBox.warning(self, "No Records", "No regional data to preview.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOrientation(QPrinter.Orientation.Landscape)
        preview_dialog = QPrintPreviewDialog(printer, self)
        preview_dialog.setWindowTitle("Print Preview — Regional Dashboard (Raw Strength Calisthenics)")
        preview_dialog.resize(1000, 720)

        def handle_paint(p):
            doc = self._generate_regional_report_document()
            doc.print_(p)

        preview_dialog.paintRequested.connect(handle_paint)
        preview_dialog.exec()

    def print_regional_dashboard(self):
        """Send formatted Regional Dashboard directly to printer."""
        rows = self._get_visible_regional_rows()
        if not rows:
            QMessageBox.warning(self, "No Records", "No regional data to print.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOrientation(QPrinter.Orientation.Landscape)
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        doc = self._generate_regional_report_document()
        doc.print_(printer)

    def _generate_regional_report_document(self):
        """Build HTML QTextDocument for Regional Dashboard printing."""
        rows = self._get_visible_regional_rows()
        doc = QTextDocument()
        tot_stores = sum(r.get("stores", 0) for r in rows)
        tot_gyms = sum(r.get("gyms", 0) for r in rows)
        tot_web = sum(r.get("web_leads", 0) for r in rows)
        tot_wb = sum(r.get("workbook_leads", 0) for r in rows)

        html_code = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 15px; color: #0F172A; }}
  h1 {{ font-size: 16pt; color: #0F172A; margin: 0 0 4px 0; }}
  .sub {{ font-size: 9pt; color: #475569; margin-bottom: 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 8pt; }}
  th {{ background: #1E293B; color: #FFFFFF; padding: 6px 8px; text-align: left; font-weight: 700; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid #E2E8F0; }}
  tr:nth-child(even) td {{ background: #F8FAFC; }}
  .tot td {{ font-weight: bold; background: #0F172A; color: #FFFFFF; }}
</style>
</head>
<body>
<h1>RAW STRENGTH CALISTHENICS — REGIONAL DASHBOARD AUDIT</h1>
<div class="sub">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Territories: {len(rows)} | All Stores: {tot_stores:,} | All Gyms: {tot_gyms:,}</div>
<table>
<thead>
<tr>
  <th>State / UT / Island</th>
  <th>Territory Type</th>
  <th>Web Leads</th>
  <th>Workbook Leads</th>
  <th>All Stores</th>
  <th>All Gyms</th>
  <th>Dashboard Target</th>
  <th>Variance</th>
</tr>
</thead>
<tbody>
"""
        for r in rows:
            diff_val = r.get("variance")
            diff_str = f"{diff_val:+d}" if diff_val is not None else "—"
            dash_str = str(r.get("dashboard_stores")) if r.get("dashboard_stores") is not None else "—"
            html_code += f"""<tr>
  <td><b>{r.get('state', '')}</b></td>
  <td>{r.get('territory_type', '')}</td>
  <td>{r.get('web_leads', 0)}</td>
  <td>{r.get('workbook_leads', 0)}</td>
  <td>{r.get('stores', 0)}</td>
  <td>{r.get('gyms', 0)}</td>
  <td>{dash_str}</td>
  <td>{diff_str}</td>
</tr>"""

        html_code += f"""<tr class="tot">
  <td>TOTAL ({len(rows)} Regions)</td>
  <td>All Categories</td>
  <td>{tot_web}</td>
  <td>{tot_wb}</td>
  <td>{tot_stores}</td>
  <td>{tot_gyms}</td>
  <td>—</td>
  <td>—</td>
</tr>
</tbody>
</table>
</body>
</html>"""
        doc.setHtml(html_code)
        return doc

    def export_regional_xlsx(self):
        """Export regional dashboard metrics to a styled Excel (.xlsx) file."""
        rows = self._get_visible_regional_rows()
        if not rows:
            QMessageBox.warning(self, "No Records", "No regional data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Regional Dashboard to Excel",
            str(Path.home() / "regional_dashboard.xlsx"),
            "Excel Workbook (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        headers = [
            ("State / UT / Island", "state"),
            ("Territory Type", "territory_type"),
            ("Web leads", "web_leads"),
            ("Workbook leads", "workbook_leads"),
            ("All stores", "stores"),
            ("All gyms", "gyms"),
            ("Dashboard stores", "dashboard_stores"),
            ("Difference", "variance"),
        ]
        try:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Regional Coverage"
            sheet.append([label for label, _key in headers])
            for r in rows:
                diff_val = r.get("variance")
                diff_str = f"{diff_val:+d}" if diff_val is not None else "—"
                dash_str = str(r.get("dashboard_stores")) if r.get("dashboard_stores") is not None else "—"
                sheet.append([
                    r.get("state", ""),
                    r.get("territory_type", ""),
                    r.get("web_leads", 0),
                    r.get("workbook_leads", 0),
                    r.get("stores", 0),
                    r.get("gyms", 0),
                    dash_str,
                    diff_str,
                ])

            tot_web = sum(r.get("web_leads", 0) for r in rows)
            tot_wb = sum(r.get("workbook_leads", 0) for r in rows)
            tot_stores = sum(r.get("stores", 0) for r in rows)
            tot_gyms = sum(r.get("gyms", 0) for r in rows)
            sheet.append(["TOTAL", f"{len(rows)} Territories", tot_web, tot_wb, tot_stores, tot_gyms, "", ""])

            from openpyxl.styles import Alignment, Font, PatternFill
            from openpyxl.utils import get_column_letter

            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor="1E293B")
                cell.alignment = Alignment(vertical="center", wrap_text=True)

            last_row = sheet.max_row
            for cell in sheet[last_row]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor="0F172A")

            for column_cells in sheet.columns:
                column_letter = get_column_letter(column_cells[0].column)
                max_length = max((len(str(cell.value or "")) for cell in column_cells), default=12)
                sheet.column_dimensions[column_letter].width = max(max_length + 3, 14)

            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            workbook.save(path)
            QMessageBox.information(
                self, "Export Successful",
                f"Exported {len(rows)} regional territories to Excel:\n{path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not create Excel workbook:\n{exc}")

    def export_regional_pdf(self):
        """Export regional dashboard metrics to a styled landscape PDF report."""
        rows = self._get_visible_regional_rows()
        if not rows:
            QMessageBox.warning(self, "No Records", "No regional data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Regional Dashboard to PDF",
            str(Path.home() / "regional_dashboard.pdf"),
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        try:
            doc = SimpleDocTemplate(
                path, pagesize=landscape(letter),
                leftMargin=25, rightMargin=25, topMargin=25, bottomMargin=25
            )
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'RegTitle', parent=styles['Heading1'], fontSize=15, leading=18, textColor=colors.HexColor('#0F172A')
            )
            cell_style = ParagraphStyle(
                'RegCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#1E293B')
            )
            hdr_style = ParagraphStyle(
                'RegHdr', parent=styles['Normal'], fontSize=8.5, leading=11, fontName='Helvetica-Bold', textColor=colors.white
            )

            tot_stores = sum(r.get("stores", 0) for r in rows)
            tot_gyms = sum(r.get("gyms", 0) for r in rows)

            elements = [
                Paragraph("<b>RAW STRENGTH CALISTHENICS — REGIONAL DASHBOARD AUDIT</b>", title_style),
                Paragraph(
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
                    f"Territories: {len(rows)} Covered | All Stores: {tot_stores:,} | All Gyms: {tot_gyms:,}",
                    styles['Normal']
                ),
                Spacer(1, 12)
            ]

            table_data = [[
                Paragraph("<b>State / UT / Island</b>", hdr_style),
                Paragraph("<b>Territory Type</b>", hdr_style),
                Paragraph("<b>Web Leads</b>", hdr_style),
                Paragraph("<b>Workbook Leads</b>", hdr_style),
                Paragraph("<b>All Stores</b>", hdr_style),
                Paragraph("<b>All Gyms</b>", hdr_style),
                Paragraph("<b>Dashboard Target</b>", hdr_style),
                Paragraph("<b>Variance</b>", hdr_style),
            ]]

            for r in rows:
                diff_val = r.get("variance")
                diff_str = f"{diff_val:+d}" if diff_val is not None else "—"
                dash_str = str(r.get("dashboard_stores")) if r.get("dashboard_stores") is not None else "—"
                table_data.append([
                    Paragraph(f"<b>{r.get('state', '')}</b>", cell_style),
                    Paragraph(r.get("territory_type", ""), cell_style),
                    Paragraph(str(r.get("web_leads", 0)), cell_style),
                    Paragraph(str(r.get("workbook_leads", 0)), cell_style),
                    Paragraph(str(r.get("stores", 0)), cell_style),
                    Paragraph(str(r.get("gyms", 0)), cell_style),
                    Paragraph(dash_str, cell_style),
                    Paragraph(diff_str, cell_style),
                ])

            t = Table(table_data, colWidths=[150, 100, 75, 85, 75, 75, 95, 75])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8FAFC'), colors.white]),
            ]))
            elements.append(t)
            doc.build(elements)
            QMessageBox.information(self, "Export Successful", f"Regional PDF exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not create Regional PDF:\n{exc}")

    def export_regional_csv(self):
        """Export regional dashboard metrics to CSV."""
        rows = self._get_visible_regional_rows()
        if not rows:
            QMessageBox.warning(self, "No Records", "No regional data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Regional Dashboard to CSV", str(Path.home() / "regional_dashboard.csv"), "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "State / UT / Island", "Territory Type", "Web leads", "Workbook leads",
                    "All stores", "All gyms", "Dashboard stores", "Variance"
                ])
                for r in rows:
                    writer.writerow([
                        r.get("state", ""),
                        r.get("territory_type", ""),
                        r.get("web_leads", 0),
                        r.get("workbook_leads", 0),
                        r.get("stores", 0),
                        r.get("gyms", 0),
                        r.get("dashboard_stores", ""),
                        r.get("variance", "")
                    ])
            QMessageBox.information(self, "Export Successful", f"Regional CSV exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not create CSV:\n{exc}")

    def open_web_scrape_dialog(self):
        """Open web scraper modal for searching supplement stores across Indian states/cities."""
        dialog = WebScraperDialog(self, default_state=self.state_filter.currentText())
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.results:
            if self.db is not None:
                result = persist_prospect_records(
                    self.db,
                    dialog.results,
                    source_name="Deep Web Scraper",
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
        source_label = "Bundled Store Directory"
        source_link = REFERENCE_DATABASE_URL

        # Do not re-import the legacy bundled seed: its individual store records
        # were not source-verified. Use the actual customer master workbook/sheet instead.
        # 1. Primary: Local Master Excel file if present
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

        # 2. Fallback: Live Google Sheets if online and populated
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
            if self.records:
                return
            logging.getLogger("prospects").info("Operating with local database store records.")
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
            f"Loaded Sports Nutrition & Supplement Store Directory!\n\n"
            f"• Source: {source_label}\n"
            f"• Stores Processed: {len(records):,}\n"
            f"• New Stores Added: {result['inserted']:,}\n"
            f"• Existing Preserved: {result['duplicates']:,}\n"
            f"• Total Directory Records: {len(self.records):,}"
        )

    def sync_google_sheets(self):
        """Live 1-click sync with central Google Spreadsheet."""
        if self.db is None:
            return
        active_user = getattr(self.db, "active_user", None)
        is_dev = False
        try:
            from app import is_developer_test_user
            is_dev = is_developer_test_user(active_user)
        except Exception:
            pass

        if is_dev:
            from cloudflare_chat import verify_developer_password
            from PySide6.QtWidgets import QInputDialog
            pwd, ok = QInputDialog.getText(
                self,
                "Developer Master Sync Authorization",
                "Signed in as developer 'admin'.\n\n"
                "To push local changes to the live customer master database / Google Sheets,\n"
                "enter the Developer Password:\n"
                "(Click Cancel to refresh local view with Taruna/Admin synced data without modifying master)",
                QLineEdit.EchoMode.Password
            )
            if not ok or not verify_developer_password(pwd):
                # No pull or push is allowed when the developer cancels or fails auth.
                # This prevents an unauthenticated test session from synchronizing.
                if hasattr(self, "sync_status_badge"):
                    self.sync_status_badge.setText("🧪 Developer Test Mode: Sync not authorized (Local Only)")
                    self.sync_status_badge.setStyleSheet(
                        "font-size: 9pt; font-weight: 700; color: #F59E0B; background: rgba(245, 158, 11, 0.15); "
                        "border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 6px 12px;"
                    )
                QMessageBox.information(
                    self, "Developer Sync Not Authorized",
                    "Enter the developer password to synchronize. No cloud data was pulled or pushed."
                )
                return

        # Automatic sync for Admin / Taruna (or authorized developer)
        try:
            stats = google_sheets_sync.sync_from_live_google_sheet(self.db)
            self._reload_saved_records()
            if stats:
                msg = f"Synced with Google Sheets!\n\n"
                for k, v in stats.items():
                    msg += f"• {k.capitalize()}: {v:,} updated\n"
                QMessageBox.information(self, "Google Sheets Sync", msg)
            else:
                QMessageBox.information(
                    self,
                    "Offline-First Master Active",
                    "Your local master database is active with its saved records.\n\n"
                    "Offline changes are saved locally and will automatically synchronize with Google Sheets upon internet connection."
                )
        except Exception as exc:
            logging.getLogger("prospects").info("Google sheets sync notice: %s", exc)
            if hasattr(self, "sync_status_badge"):
                self.sync_status_badge.setText("🟠 Offline: Local Master Preserved · Auto-Syncs on Connect")
                self.sync_status_badge.setStyleSheet(
                    "font-size: 9pt; font-weight: 700; color: #F59E0B; background: rgba(245, 158, 11, 0.15); "
                    "border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 6px 12px;"
                )
            QMessageBox.information(
                self,
                "Offline Master Mode",
                "Operating in Offline Mode: Local database is fully active and preserved.\n"
                "All updates will automatically synchronize with Google Sheets once internet is connected."
            )

    def _get_visible_records(self):
        """Return list of records currently matching search, state/kind filters, and exclude rules."""
        if not hasattr(self, "leads_table") or self.leads_table.rowCount() == 0:
            return self.records
        visible = []
        for row_index in range(self.leads_table.rowCount()):
            if not self.leads_table.isRowHidden(row_index):
                if row_index < len(self.records):
                    visible.append(self.records[row_index])
        return visible

    def export_csv(self):
        """Export currently filtered records to CSV matching the exact OneDrive schema."""
        records = self._get_visible_records()
        if not records:
            QMessageBox.warning(self, "No Records", "No store records to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Store Directory to CSV", str(Path.home() / "Downloads" / "stores_directory.csv"), "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            headers = [
                "Store type", "state", "city", "area", "business category", "business name",
                "Mobile number", "Email address", "Full address", "Google Maps link", "Website/social-media link",
                "verified by call", "response"
            ]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in records:
                    writer.writerow([
                        format_prospect_cell_value(r, "kind"),
                        format_prospect_cell_value(r, "state"),
                        format_prospect_cell_value(r, "city"),
                        format_prospect_cell_value(r, "area"),
                        format_prospect_cell_value(r, "business_category"),
                        format_prospect_cell_value(r, "business_name"),
                        format_prospect_cell_value(r, "phone"),
                        format_prospect_cell_value(r, "email"),
                        format_prospect_cell_value(r, "address"),
                        format_prospect_cell_value(r, "maps"),
                        format_prospect_cell_value(r, "website"),
                        format_prospect_cell_value(r, "verified"),
                        format_prospect_cell_value(r, "response")
                    ])
            self.last_export_path = path
            self.last_export_dir = str(Path(path).parent)
            self.last_export_path = path
            self.last_export_dir = str(Path(path).parent)
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
            str(Path.home() / "Downloads" / "stores_directory.xlsx"),
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
                sheet.append([format_prospect_cell_value(record, key) for _label, key in headers])

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
            self, "Export Store Directory to PDF", str(Path.home() / "Downloads" / "stores_directory.pdf"), "PDF Files (*.pdf)"
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
                    Paragraph(format_prospect_cell_value(r, "state"), cell_style),
                    Paragraph(f"{format_prospect_cell_value(r, 'city')}<br/>{format_prospect_cell_value(r, 'area')}", cell_style),
                    Paragraph(f"<b>{format_prospect_cell_value(r, 'business_name')}</b>", cell_style),
                    Paragraph(format_prospect_cell_value(r, "business_category"), cell_style),
                    Paragraph(format_prospect_cell_value(r, "phone"), cell_style),
                    Paragraph(format_prospect_cell_value(r, "address"), cell_style),
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
            self.last_export_path = path
            self.last_export_dir = str(Path(path).parent)
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
            self, "Export Store Directory to Word Document", str(Path.home() / "Downloads" / "stores_directory.doc"), "Word Document (*.doc)"
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
  <td>{format_prospect_cell_value(r, 'state')}</td>
  <td>{format_prospect_cell_value(r, 'city')}<br><small>{format_prospect_cell_value(r, 'area')}</small></td>
  <td><b>{format_prospect_cell_value(r, 'business_name')}</b></td>
  <td>{format_prospect_cell_value(r, 'business_category')}</td>
  <td>{format_prospect_cell_value(r, 'phone')}</td>
  <td>{format_prospect_cell_value(r, 'address')}</td>
  <td>{maps_link}</td>
</tr>
"""
            html += """</tbody></table></body></html>"""
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self.last_export_path = path
            self.last_export_dir = str(Path(path).parent)
            QMessageBox.information(self, "Export Successful", f"Word document exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not create Word document:\n{exc}")

    def one_tap_scrape_and_master_update(self):
        """1-Tap action:
        1. Deep scrape genuine supplement stores & gyms across India or selected state/category.
        2. Non-destructive conflict-free merge into SQLite database (never deleting existing data).
        3. Auto-save master Excel snapshot to Downloads/Google_Sheets_Master_Database.xlsx.
        4. Seamlessly and silently sync with live central Google Sheets."""
        if self.db is None:
            QMessageBox.warning(self, "Database Unavailable", "Application database is not ready.")
            return

        if not self.records:
            self.load_master_india_stores()

        selected_kind = self.kind_filter.currentText()
        selected_state = self.state_filter.currentText()
        if selected_state == "All States / UTs":
            selected_state = ""

        self.btn_one_tap_scrape_and_update.setEnabled(False)
        self.btn_one_tap_scrape_and_update.setText("⏳ Deep Scraping & Updating Master...")
        QApplication = sys.modules.get("PySide6.QtWidgets").QApplication
        if QApplication:
            QApplication.processEvents()

        try:
            # 1. Deep web scrape with genuine contact crawler
            def update_progress(msg, pct):
                self.btn_one_tap_scrape_and_update.setText(f"⏳ [{pct}%] {msg[:28]}...")
                if QApplication:
                    QApplication.processEvents()

            scraped = crawl_search_engine_results(
                category=selected_kind,
                state=selected_state,
                max_results=30,
                deep_scrape=True,
                progress_cb=update_progress
            )

            # 2. Conflict-free merge into SQLite
            result = {"inserted": 0, "duplicates": 0}
            if scraped:
                result = persist_prospect_records(
                    self.db,
                    scraped,
                    source_name="Deep Web Scraper",
                    source_url="",
                    source_checked_at=date.today().isoformat()
                )

            # Reload updated records from local database
            self._reload_saved_records()

            # 3. Always download & keep master Excel copy in Downloads during update
            snapshot_path = google_sheets_sync.save_master_database_snapshot(self.db)
            self.last_export_path = snapshot_path
            self.last_export_dir = str(Path(snapshot_path).parent)

            # 4. Continuous auto-sync to live Google Sheets (offline-first conflict resolution)
            active_user = getattr(self.db, "active_user", None)
            is_dev = False
            try:
                from app import is_developer_test_user
                is_dev = is_developer_test_user(active_user)
            except Exception:
                pass

            if is_dev:
                from cloudflare_chat import verify_developer_password
                from PySide6.QtWidgets import QInputDialog
                pwd, ok = QInputDialog.getText(
                    self,
                    "Developer Master Sync Authorization",
                    "Signed in as developer 'admin'.\n\n"
                    "To push newly discovered stores to the live customer master database / Google Sheets,\n"
                    "enter the Developer Password:\n"
                    "(Click Cancel to save newly discovered stores locally without modifying live master)",
                    QLineEdit.EchoMode.Password
                )
                if ok and verify_developer_password(pwd):
                    # This one-time interactive action is explicitly password-gated.
                    # Background developer sync remains blocked.
                    sync_res = google_sheets_sync.continuous_auto_sync(self.db, developer_authorized=True)
                else:
                    self.sync_status_badge.setText("🧪 Developer Test Mode: Saved Locally (Live Master Protected)")
                    self.sync_status_badge.setStyleSheet(
                        "font-size: 9pt; font-weight: 700; color: #F59E0B; background: rgba(245, 158, 11, 0.15); "
                        "border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 6px 12px;"
                    )
                    sync_res = {"status": "test_mode"}
            else:
                sync_res = google_sheets_sync.continuous_auto_sync(self.db)
            if sync_res.get("status") == "synced":
                self.sync_status_badge.setText(f"🟢 Continuous Sync: Active ({len(self.records):,} Stores) · Conflict-Free")
                self.sync_status_badge.setStyleSheet(
                    "font-size: 9pt; font-weight: 700; color: #34D399; background: rgba(16, 185, 129, 0.15); "
                    "border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 4px; padding: 6px 12px;"
                )
            else:
                self.sync_status_badge.setText("🟠 Offline: Local Master Updated · Will Auto-Sync When Online")
                self.sync_status_badge.setStyleSheet(
                    "font-size: 9pt; font-weight: 700; color: #F59E0B; background: rgba(245, 158, 11, 0.15); "
                    "border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 6px 12px;"
                )

            if snapshot_path:
                self.snapshot_badge.setText(f"💾 Master Backup: {Path(snapshot_path).name} (Auto-Saved)")

            # Clean notification
            summary_msg = (
                f"Master Database 1-Tap Update Successful!\n\n"
                f"• Master Store Directory: {len(self.records):,} genuine stores\n"
                f"• Newly Discovered: {result.get('inserted', 0):,} stores\n"
                f"• Existing Details Enriched: {result.get('duplicates', 0):,} records\n"
                f"• Conflict Resolution: Non-destructive (Zero data deleted)\n"
                f"• Offline Excel Snapshot: {snapshot_path}\n"
                f"• Central Google Sheets: {'Live Synced' if sync_res.get('status') == 'synced' else 'Saved locally (auto-syncs on connect)'}"
            )
            QMessageBox.information(self, "1-Tap Master Update", summary_msg)

        except Exception as exc:
            logging.getLogger("prospects").error("1-Tap update error: %s", exc)
            QMessageBox.warning(self, "Update Notice", f"Update process encountered an issue:\n{exc}")
        finally:
            self.btn_one_tap_scrape_and_update.setEnabled(True)
            self.btn_one_tap_scrape_and_update.setText("⚡ 1-Tap Deep Web Scraping & Master Update")

    def _run_silent_continuous_sync(self):
        """Background continuous sync running every 60s without user prompts or interruption."""
        if self.db is None:
            return
        active_user = getattr(self.db, "active_user", None)
        try:
            from app import is_developer_test_user
            if is_developer_test_user(active_user):
                if hasattr(self, "sync_status_badge"):
                    self.sync_status_badge.setText("🧪 Developer Test Mode: Sync Disabled (Local Only)")
                    self.sync_status_badge.setStyleSheet(
                        "font-size: 9pt; font-weight: 700; color: #F59E0B; background: rgba(245, 158, 11, 0.15); "
                        "border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 6px 12px;"
                    )
                return
        except Exception:
            pass
        try:
            res = google_sheets_sync.continuous_auto_sync(self.db)
            if res.get("status") == "synced":
                self.sync_status_badge.setText(f"🟢 Continuous Sync: Active ({len(self.records):,} Stores) · Conflict-Free")
                self.sync_status_badge.setStyleSheet(
                    "font-size: 9pt; font-weight: 700; color: #34D399; background: rgba(16, 185, 129, 0.15); "
                    "border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 4px; padding: 6px 12px;"
                )
                if res.get("updated", 0) > 0:
                    self._reload_saved_records()
            elif res.get("status") == "offline":
                self.sync_status_badge.setText("🟠 Offline: Local Master Updated · Will Auto-Sync When Online")
                self.sync_status_badge.setStyleSheet(
                    "font-size: 9pt; font-weight: 700; color: #F59E0B; background: rgba(245, 158, 11, 0.15); "
                    "border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 4px; padding: 6px 12px;"
                )
        except Exception:
            pass

    def _generate_report_document(self):
        """Generate formatted rich QTextDocument replicating the Print Center layout."""
        records = self._get_visible_records()
        state_label = self.state_filter.currentText()
        kind_label = self.kind_filter.currentText()
        html = f"""<html>
<head>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 8pt; }}
h2 {{ margin: 0 0 4px 0; color: #0F172A; font-size: 14pt; }}
p {{ margin: 0 0 10px 0; color: #475569; font-size: 8.5pt; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 0.5px solid #CBD5E1; padding: 4px 6px; font-size: 7.5pt; text-align: left; }}
th {{ background-color: #1E293B; color: white; font-weight: bold; }}
tr:nth-child(even) {{ background-color: #F8FAFC; }}
</style>
</head>
<body>
<h2>Raw Strength Calisthenics — Store Directory</h2>
<p>Filter: <b>{kind_label}</b> · State: <b>{state_label}</b> | Stores: <b>{len(records):,}</b> | Generated: <b>{datetime.now().strftime('%Y-%m-%d %H:%M')}</b></p>
<table>
<thead>
<tr>
  <th>State</th><th>City</th><th>Business Name</th><th>Category</th><th>Phone</th><th>Email</th><th>Address</th><th>Website</th>
</tr>
</thead>
<tbody>
"""
        for r in records[:400]:
            html += f"""<tr>
  <td>{format_prospect_cell_value(r, 'state')}</td>
  <td>{format_prospect_cell_value(r, 'city')}</td>
  <td><b>{format_prospect_cell_value(r, 'business_name')}</b></td>
  <td>{format_prospect_cell_value(r, 'business_category')}</td>
  <td>{format_prospect_cell_value(r, 'phone')}</td>
  <td>{format_prospect_cell_value(r, 'email')}</td>
  <td>{format_prospect_cell_value(r, 'address')}</td>
  <td>{format_prospect_cell_value(r, 'website')}</td>
</tr>"""
        html += """</tbody></table></body></html>"""
        doc = QTextDocument()
        doc.setHtml(html)
        return doc

    def open_print_preview(self):
        """Open full-page print preview dialog replicating Print Center."""
        records = self._get_visible_records()
        if not records:
            QMessageBox.warning(self, "No Records", "No stores to preview.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOrientation(QPrinter.Orientation.Landscape)
        preview_dialog = QPrintPreviewDialog(printer, self)
        preview_dialog.setWindowTitle("Print Preview — Store Directory (Raw Strength Calisthenics)")
        preview_dialog.resize(1000, 720)

        def handle_paint(p):
            doc = self._generate_report_document()
            doc.print_(p)

        preview_dialog.paintRequested.connect(handle_paint)
        preview_dialog.exec()

    def print_leads(self):
        """Send formatted store directory directly to selected system printer."""
        records = self._get_visible_records()
        if not records:
            QMessageBox.warning(self, "No Records", "No stores to print.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOrientation(QPrinter.Orientation.Landscape)
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        doc = self._generate_report_document()
        doc.print_(printer)

    def _get_selected_or_first_record(self):
        row = self.leads_table.currentRow()
        records = self._get_visible_records()
        if not records:
            return None
        if 0 <= row < len(records):
            return records[row]
        return records[0]

    def _generate_store_details_document(self, record=None):
        if record is None:
            record = self._get_selected_or_first_record()
        if not record:
            doc = QTextDocument()
            doc.setHtml("<p>No store selected.</p>")
            return doc

        name = format_prospect_cell_value(record, "business_name")
        cat = format_prospect_cell_value(record, "business_category")
        brand = format_prospect_cell_value(record, "brand")
        state = format_prospect_cell_value(record, "state")
        city = format_prospect_cell_value(record, "city")
        district = format_prospect_cell_value(record, "district")
        area = format_prospect_cell_value(record, "area")
        pincode = format_prospect_cell_value(record, "pincode")
        address = format_prospect_cell_value(record, "address")
        phone = format_prospect_cell_value(record, "phone")
        email = format_prospect_cell_value(record, "email")
        contact_person = format_prospect_cell_value(record, "contact_person")
        website = format_prospect_cell_value(record, "website")
        source = format_prospect_cell_value(record, "source_type")
        source_url = format_prospect_cell_value(record, "source_url")
        status = format_prospect_cell_value(record, "status")
        notes = format_prospect_cell_value(record, "notes")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        html = f"""<html>
<head>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 9.5pt; margin: 20px; color: #0F172A; }}
.header {{ border-bottom: 2.5px solid #2563EB; padding-bottom: 8px; margin-bottom: 14px; }}
.title {{ font-size: 16pt; font-weight: bold; color: #1E3A8A; margin: 0; }}
.subtitle {{ font-size: 9pt; color: #64748B; margin-top: 4px; }}
.card {{ border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; margin-bottom: 14px; background: #F8FAFC; }}
.sec-title {{ font-size: 10.5pt; font-weight: bold; color: #1E293B; border-bottom: 1.5px solid #E2E8F0; padding-bottom: 4px; margin-bottom: 8px; }}
table.details {{ width: 100%; border-collapse: collapse; }}
table.details td {{ padding: 6px 10px; font-size: 9pt; vertical-align: top; }}
table.details td.lbl {{ width: 26%; font-weight: bold; color: #475569; background: #F1F5F9; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; }}
table.details td.val {{ width: 74%; color: #0F172A; border-bottom: 1px solid #E2E8F0; }}
.footer {{ margin-top: 20px; font-size: 8pt; color: #94A3B8; text-align: center; border-top: 1px solid #CBD5E1; padding-top: 8px; }}
</style>
</head>
<body>
<div class="header">
  <div class="title">Raw Strength Calisthenics — Store Profile Dossier</div>
  <div class="subtitle">Official Verification & Store Details | Generated: {now_str}</div>
</div>

<div class="card">
  <div class="sec-title">🏢 Business & Identity</div>
  <table class="details">
    <tr><td class="lbl">Business Name</td><td class="val"><b>{name}</b></td></tr>
    <tr><td class="lbl">Category / Type</td><td class="val">{cat}</td></tr>
    <tr><td class="lbl">Brand / Chain</td><td class="val">{brand}</td></tr>
    <tr><td class="lbl">Operational Status</td><td class="val">{status}</td></tr>
  </table>
</div>

<div class="card">
  <div class="sec-title">📍 Location & Territory</div>
  <table class="details">
    <tr><td class="lbl">State / Territory</td><td class="val">{state}</td></tr>
    <tr><td class="lbl">District</td><td class="val">{district}</td></tr>
    <tr><td class="lbl">City / Town</td><td class="val">{city}</td></tr>
    <tr><td class="lbl">Area / Locality</td><td class="val">{area}</td></tr>
    <tr><td class="lbl">Postal Code (PIN)</td><td class="val">{pincode}</td></tr>
    <tr><td class="lbl">Full Address</td><td class="val">{address}</td></tr>
  </table>
</div>

<div class="card">
  <div class="sec-title">📞 Contact & Digital Presence</div>
  <table class="details">
    <tr><td class="lbl">Phone Number</td><td class="val"><b>{phone}</b></td></tr>
    <tr><td class="lbl">Email Address</td><td class="val">{email}</td></tr>
    <tr><td class="lbl">Contact Person</td><td class="val">{contact_person}</td></tr>
    <tr><td class="lbl">Official Website</td><td class="val">{website}</td></tr>
    <tr><td class="lbl">Directory / Map URL</td><td class="val">{source_url}</td></tr>
    <tr><td class="lbl">Data Source</td><td class="val">{source}</td></tr>
    <tr><td class="lbl">Notes / Remarks</td><td class="val">{notes}</td></tr>
  </table>
</div>

<div class="footer">
  Raw Strength Calisthenics Store Directory Management System · Confidential Institutional Record
</div>
</body>
</html>"""
        doc = QTextDocument()
        doc.setHtml(html)
        return doc

    def open_store_details_preview(self, record=None):
        """Open print preview dialog for selected store details dossier."""
        if record is None:
            record = self._get_selected_or_first_record()
        if not record:
            QMessageBox.warning(self, "No Store Selected", "Please select a store to preview details.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOrientation(QPrinter.Orientation.Portrait)
        preview_dialog = QPrintPreviewDialog(printer, self)
        name = format_prospect_cell_value(record, "business_name")
        preview_dialog.setWindowTitle(f"Print Preview — Store Details: {name}")
        preview_dialog.resize(900, 750)

        def handle_paint(p):
            doc = self._generate_store_details_document(record)
            doc.print_(p)

        preview_dialog.paintRequested.connect(handle_paint)
        preview_dialog.exec()

    def print_store_details(self, record=None):
        """Send store details directly to printer."""
        if record is None:
            record = self._get_selected_or_first_record()
        if not record:
            QMessageBox.warning(self, "No Store Selected", "Please select a store to print details.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOrientation(QPrinter.Orientation.Portrait)
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        doc = self._generate_store_details_document(record)
        doc.print_(printer)

    def show_store_details_dialog(self, row_or_record):
        if isinstance(row_or_record, int):
            records = self._get_visible_records()
            if 0 <= row_or_record < len(records):
                record = records[row_or_record]
            else:
                return
        else:
            record = row_or_record
        if not record:
            return
        dialog = QDialog(self)
        name = format_prospect_cell_value(record, 'business_name')
        dialog.setWindowTitle(f"Store Details — {name}")
        dialog.resize(580, 520)
        vbox = QVBoxLayout(dialog)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        form.setContentsMargins(8, 8, 8, 8)
        form.setSpacing(10)

        fields = [
            ("Business Name", format_prospect_cell_value(record, "business_name")),
            ("Category", format_prospect_cell_value(record, "business_category")),
            ("Brand / Chain", format_prospect_cell_value(record, "brand")),
            ("State", format_prospect_cell_value(record, "state")),
            ("District", format_prospect_cell_value(record, "district")),
            ("City", format_prospect_cell_value(record, "city")),
            ("Area", format_prospect_cell_value(record, "area")),
            ("PIN Code", format_prospect_cell_value(record, "pincode")),
            ("Address", format_prospect_cell_value(record, "address")),
            ("Phone", format_prospect_cell_value(record, "phone")),
            ("Email", format_prospect_cell_value(record, "email")),
            ("Contact Person", format_prospect_cell_value(record, "contact_person")),
            ("Website", format_prospect_cell_value(record, "website")),
            ("Source URL", format_prospect_cell_value(record, "source_url")),
            ("Source Type", format_prospect_cell_value(record, "source_type")),
            ("Status", format_prospect_cell_value(record, "status")),
            ("Notes", format_prospect_cell_value(record, "notes")),
        ]
        for label, val in fields:
            lbl = QLabel(f"<b>{label}:</b>")
            lbl.setStyleSheet("color: #94A3B8; font-size: 9pt;")
            val_lbl = QLabel(str(val))
            val_lbl.setWordWrap(True)
            val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val_lbl.setStyleSheet("color: #F8FAFC; font-size: 9pt;")
            form.addRow(lbl, val_lbl)
        scroll.setWidget(container)
        vbox.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_print_detail = QPushButton("🖨️ Print Store Details")
        btn_print_detail.setStyleSheet(
            "QPushButton { font-weight: bold; background: #2563EB; color: white; padding: 6px 14px; border-radius: 6px; } "
            "QPushButton:hover { background: #1D4ED8; }"
        )
        btn_print_detail.clicked.connect(lambda: self.open_store_details_preview(record))
        btn_row.addWidget(btn_print_detail)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_close)
        vbox.addLayout(btn_row)

        dialog.exec()

    def open_export_folder(self):
        """Open the folder where exports or the master database are saved and highlight the file."""
        target_file = None
        if hasattr(self, "last_export_path") and self.last_export_path and Path(self.last_export_path).exists():
            target_file = Path(self.last_export_path)
        else:
            downloads_dir = Path.home() / "Downloads"
            candidates = [
                downloads_dir / "Google_Sheets_Master_Database.xlsx",
                downloads_dir / "Google_Sheets_Test_admin_Snapshot.xlsx",
                downloads_dir / "stores_directory.xlsx",
                downloads_dir / "stores_directory.csv",
                downloads_dir / "stores_directory.pdf",
                Path.home() / "stores_directory.xlsx",
            ]
            for cand in candidates:
                if cand.exists():
                    target_file = cand
                    break

        if target_file and target_file.exists():
            if sys.platform == "win32":
                try:
                    import subprocess
                    subprocess.Popen(f'explorer.exe /select,"{str(target_file.resolve())}"')
                    return
                except Exception:
                    pass
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_file.parent)))
            return

        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(downloads)))

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

    def _on_density_changed(self, mode):
        height = 34
        if mode == "Comfortable":
            height = 42
        elif mode == "Dense":
            height = 26
        if hasattr(self, "leads_table"):
            self.leads_table.verticalHeader().setDefaultSectionSize(height)
        if self.db:
            try:
                self.db.set_setting("store_directory_density", mode)
            except Exception:
                pass

    def _reload_saved_records(self):
        if self.db is not None:
            try:
                sanitize_prospect_database_records(self.db)
                cleanup_duplicate_prospects(self.db)
            except Exception:
                pass
            self.records = load_saved_prospects(self.db)
            self.preview_records = []
            self._refresh_filters()
            self._refresh_views()

    def _refresh_filters(self):
        previous_state = self.state_filter.currentText()
        self.state_filter.blockSignals(True)
        self.state_filter.clear()
        self.state_filter.addItem("All States / UTs")

        # Collect genuine Indian states, decomposing multi-state listings and omitting 'All-India' or noise
        raw_states = set()
        for record in self.records:
            st_val = str(record.get("state") or "").strip()
            if st_val:
                for sub_st in st_val.split(","):
                    clean_st = normalise_state(sub_st.strip())
                    if clean_st and clean_st in INDIA_REGIONS:
                        raw_states.add(clean_st)
        states = sorted(raw_states, key=str.casefold)

        self.state_filter.addItems(states)
        if previous_state in states:
            self.state_filter.setCurrentText(previous_state)
        self.state_filter.blockSignals(False)

        if hasattr(self, "exclude_state"):
            prev_ex = self.exclude_state.currentText()
            self.exclude_state.blockSignals(True)
            self.exclude_state.clear()
            self.exclude_state.addItem("Exclude State: None")
            self.exclude_state.addItems(states)
            if prev_ex in states:
                self.exclude_state.setCurrentText(prev_ex)
            self.exclude_state.blockSignals(False)

        if hasattr(self, "exclude_dropdown"):
            prev_drop = self.exclude_dropdown.currentText()
            self.exclude_dropdown.blockSignals(True)
            self.exclude_dropdown.clear()
            self.exclude_dropdown.addItem("🚫 Exclude Target: None (Show All)")
            self.exclude_dropdown.addItem("Exclude Category: Pure Product Selling Stores")
            self.exclude_dropdown.addItem("Exclude Category: Gym")
            self.exclude_dropdown.addItem("Exclude Category: Gyms which sell products also")
            self.exclude_dropdown.addItem("🚫 Exclude: Gym + Wellness Centers + Herbal + HealthKart")
            self.exclude_dropdown.addItem("Exclude: Missing Phone / Email")
            self.exclude_dropdown.addItem("Exclude: Missing Website")
            self.exclude_dropdown.addItem("Exclude: Unverified Leads")
            for st in states:
                self.exclude_dropdown.addItem(f"Exclude State: {st}")
            if prev_drop and self.exclude_dropdown.findText(prev_drop) >= 0:
                self.exclude_dropdown.setCurrentText(prev_drop)
            self.exclude_dropdown.blockSignals(False)

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
                maps_url = str(record.get("maps", "") or "")
                if key == "source_url":
                    text = "Open source" if source_url else "NA"
                elif key == "maps":
                    text = "Open Maps" if maps_url.startswith(("https://", "http://")) else "NA"
                else:
                    text = format_prospect_cell_value(record, key)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                is_dark = getattr(self, "_current_theme_name", "night") in {"night", "dark", "ocean", "sunset"}
                if key == "source_url":
                    item.setData(Qt.ItemDataRole.UserRole, source_url)
                    item.setForeground(QColor("#38BDF8" if is_dark else "#0284C7") if source_url else QColor("#94A3B8" if is_dark else "#64748B"))
                elif key == "maps":
                    item.setData(Qt.ItemDataRole.UserRole, maps_url)
                    item.setForeground(QColor("#38BDF8" if is_dark else "#0284C7") if maps_url.startswith(("https://", "http://")) else QColor("#94A3B8" if is_dark else "#64748B"))
                elif text == "NA":
                    item.setForeground(QColor("#94A3B8" if is_dark else "#64748B"))
                else:
                    item.setForeground(QColor("#FFFFFF" if is_dark else "#0F172A"))
                if text and text != "NA":
                    item.setToolTip(text)
                self.leads_table.setItem(row_index, column_index, item)
        self.leads_table.setUpdatesEnabled(True)
        # Expand row heights so full street addresses are readable in the directory.
        self.leads_table.resizeRowsToContents()

    def open_source_link(self, row, column):
        key = self.LEAD_COLUMNS[column][1]
        if key in {"source_url", "maps"}:
            item = self.leads_table.item(row, column)
            url = str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""
            if url.startswith(("https://", "http://")):
                QDesktopServices.openUrl(QUrl(url))
                return
        self.show_store_details_dialog(row)

    def _fill_regional_table(self):
        rows = build_regional_summary(self.records, self.dashboard_counts, include_all_regions=True)
        source_counts = defaultdict(lambda: {"web": 0, "workbook": 0})
        for record in self.records:
            raw_state = str(record.get("state") or "").strip()
            if not raw_state:
                continue
            is_web = str(record.get("source_type") or "").casefold().startswith("official web")
            st_list = [s.strip() for s in raw_state.split(",") if s.strip()]
            for sub_st in st_list:
                clean_st = normalise_state(sub_st)
                if clean_st and clean_st in INDIA_REGIONS:
                    if is_web:
                        source_counts[clean_st]["web"] += 1
                    else:
                        source_counts[clean_st]["workbook"] += 1
        for row in rows:
            row["web_leads"] = source_counts[row["state"]]["web"]
            row["workbook_leads"] = source_counts[row["state"]]["workbook"]
            row["territory_type"] = territory_type(row["state"])

        t_filter = self.territory_filter.currentText() if hasattr(self, "territory_filter") else "All"
        if "States" in t_filter:
            display_rows = [r for r in rows if r.get("territory_type") == "State"]
        elif "Union Territories" in t_filter:
            display_rows = [r for r in rows if r.get("territory_type") == "Union Territory"]
        elif "Island" in t_filter:
            display_rows = [r for r in rows if r.get("territory_type") == "Island Territory"]
        else:
            display_rows = sorted(
                rows,
                key=lambda r: (
                    0 if r.get("territory_type") == "State" else 1 if r.get("territory_type") == "Union Territory" else 2,
                    r["state"].casefold()
                )
            )

        self.last_regional_display_rows = list(display_rows)
        self.region_table.setRowCount(len(display_rows))
        for row_index, data in enumerate(display_rows):
            for column_index, (_label, key) in enumerate(self.REGIONAL_COLUMNS):
                value = data.get(key)
                text = "—" if value is None else f"{value:+,}" if key == "variance" else f"{value:,}" if isinstance(value, int) else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if key in {"web_leads", "workbook_leads", "stores", "gyms", "dashboard_stores", "variance", "territory_type"}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                is_dark = getattr(self, "_current_theme_name", "night") in {"night", "dark", "ocean", "sunset"}
                if key == "territory_type":
                    tt = data.get("territory_type", "")
                    if tt == "State":
                        item.setForeground(QColor("#60A5FA" if is_dark else "#2563EB"))
                    elif tt == "Union Territory":
                        item.setForeground(QColor("#FBBF24" if is_dark else "#D97706"))
                    elif tt == "Island Territory":
                        item.setForeground(QColor("#34D399" if is_dark else "#059669"))
                    else:
                        item.setForeground(QColor("#FFFFFF" if is_dark else "#0F172A"))
                elif key == "variance" and value is not None and value != 0:
                    item.setForeground(QColor("#FCA5A5" if is_dark else "#DC2626") if value > 0 else QColor("#FCD34D" if is_dark else "#D97706"))
                else:
                    item.setForeground(QColor("#FFFFFF" if is_dark else "#0F172A"))
                self.region_table.setItem(row_index, column_index, item)

        states_stores = sum(r["stores"] for r in rows if r.get("territory_type") == "State")
        states_gyms = sum(r["gyms"] for r in rows if r.get("territory_type") == "State")
        ut_stores = sum(r["stores"] for r in rows if r.get("territory_type") == "Union Territory")
        ut_gyms = sum(r["gyms"] for r in rows if r.get("territory_type") == "Union Territory")
        islands_stores = sum(r["stores"] for r in rows if r.get("territory_type") == "Island Territory")
        islands_gyms = sum(r["gyms"] for r in rows if r.get("territory_type") == "Island Territory")

        if hasattr(self, "card_states_val"):
            self.card_states_val.setText(f"28 States ({states_stores:,} stores, {states_gyms:,} gyms)")
        if hasattr(self, "card_ut_val"):
            self.card_ut_val.setText(f"6 UTs ({ut_stores:,} stores, {ut_gyms:,} gyms)")
        if hasattr(self, "card_islands_val"):
            self.card_islands_val.setText(f"2 Islands ({islands_stores:,} stores, {islands_gyms:,} gyms)")

    def _refresh_kpis(self):
        stores = sum(record.get("kind") in {"Store", "Pure Product Selling Store"} and record.get("kind") != "Gym + Store" for record in self.records)
        gyms = sum(record.get("kind") in {"Gym", "Gyms"} and record.get("kind") != "Gym + Store" for record in self.records)
        gym_stores = sum(record.get("kind") in {"Gym + Store", "Gym which sells products"} for record in self.records)
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

        # Exclude filter values from unified exclude_dropdown
        ex_drop = self.exclude_dropdown.currentText() if hasattr(self, "exclude_dropdown") else ""
        ex_drop_category = ""
        ex_drop_state = ""
        ex_drop_missing_contact = False
        ex_drop_missing_website = False
        ex_drop_unverified = False
        ex_drop_combo_negative = False

        if "Gym + Wellness Centers + Herbal + HealthKart" in ex_drop or "gym+wellnescenters+hebal+healthkart" in ex_drop.lower().replace(" ", ""):
            ex_drop_combo_negative = True
        elif ex_drop.startswith("Exclude Category: "):
            ex_drop_category = ex_drop.replace("Exclude Category: ", "").strip()
        elif ex_drop.startswith("Exclude State: "):
            ex_drop_state = ex_drop.replace("Exclude State: ", "").strip()
        elif ex_drop == "Exclude: Missing Phone / Email":
            ex_drop_missing_contact = True
        elif ex_drop == "Exclude: Missing Website":
            ex_drop_missing_website = True
        elif ex_drop == "Exclude: Unverified Leads":
            ex_drop_unverified = True

        # Fallback / explicit exclude controls (for direct API/test compatibility)
        ex_state = self.exclude_state.currentText() if hasattr(self, "exclude_state") else ""
        if ex_state == "Exclude State: None":
            ex_state = ""
        if not ex_state and ex_drop_state:
            ex_state = ex_drop_state

        ex_kind = self.exclude_kind.currentText() if hasattr(self, "exclude_kind") else ""
        if ex_kind == "Exclude Category: None":
            ex_kind = ""
        if not ex_kind and ex_drop_category:
            ex_kind = ex_drop_category

        ex_name = self.exclude_name.text().strip().casefold() if hasattr(self, "exclude_name") else ""
        ex_district = self.exclude_district.text().strip().casefold() if hasattr(self, "exclude_district") else ""
        ex_custom_raw = self.exclude_custom.text().strip().casefold() if hasattr(self, "exclude_custom") else ""
        ex_kw_raw = self.exclude_keyword.text().strip().casefold() if hasattr(self, "exclude_keyword") else ""

        all_kw_raw = f"{ex_custom_raw},{ex_kw_raw}".strip(",")
        ex_keywords = [kw.strip() for kw in all_kw_raw.split(",") if kw.strip()]

        visible = 0
        for row_index, record in enumerate(self.records):
            rec_kind = str(record.get("kind") or "Store").strip()
            rec_cat = str(record.get("business_category") or "").casefold()

            # Positive filtering
            if kind in ("All types", "All Categories"):
                matches_kind = True
            elif kind in ("Pure Product Selling Stores", "Store"):
                matches_kind = rec_kind in ("Store", "Supplement Store", "Pure Product Selling Store") and rec_kind != "Gym + Store"
            elif kind in ("Gym", "Gyms"):
                matches_kind = rec_kind in ("Gym", "Gyms") and rec_kind != "Gym + Store"
            elif kind in ("Gyms which sell products also", "Gym + Store", "Gyms which sell products"):
                matches_kind = (
                    rec_kind in ("Gym + Store", "Gym which sells products", "Gym + Store (Hybrid)")
                    or "product" in rec_cat
                    or ("gym" in rec_cat and any(w in rec_cat for w in ("supplement", "nutrition", "counter", "pro-shop", "protein", "shake")))
                )
            else:
                matches_kind = rec_kind == kind
            rec_state_raw = str(record.get("state") or "")
            rec_states = [s.strip().casefold() for s in rec_state_raw.split(",") if s.strip()]
            matches_state = (state == "All States / UTs") or (state.casefold() in rec_states) or (rec_state_raw == state)
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
            search_terms = search.split()
            matches_search = not search or all(term in search_blob for term in search_terms)

            # Negative / Exclude filtering
            excluded = False
            if ex_drop_missing_contact and not has_contact:
                excluded = True
            if not excluded and ex_drop_missing_website and not has_website:
                excluded = True
            if not excluded and ex_drop_unverified and not is_verified:
                excluded = True

            if not excluded and ex_state and (ex_state.casefold() in rec_states or rec_state_raw == ex_state):
                excluded = True

            if not excluded and ex_drop_combo_negative:
                b_name = str(record.get("business_name") or record.get("name") or "").casefold()
                is_gym = (rec_kind in ("Gym", "Gyms", "Gym + Store", "Gym which sells products", "Gym + Store (Hybrid)")
                          or "gym" in rec_cat
                          or "gym" in b_name
                          or "fitness cent" in rec_cat)
                is_wellness = ("wellness" in search_blob
                               or "wellness" in rec_cat
                               or "wellness" in b_name)
                is_herbal = any(h in search_blob for h in ("herbal", "herbalife", "ayurved", "ayurvedic", "homeopath"))
                is_healthkart = ("healthkart" in search_blob
                                 or "healthkart" in b_name
                                 or "healthkart" in str(record.get("website", "")).casefold())
                if is_gym or is_wellness or is_herbal or is_healthkart:
                    excluded = True

            if not excluded and ex_kind:
                if ex_kind == "Pure Product Selling Stores":
                    if rec_kind in ("Store", "Supplement Store", "Pure Product Selling Store") and rec_kind != "Gym + Store":
                        excluded = True
                elif ex_kind in ("Gym", "Gyms"):
                    if rec_kind in ("Gym", "Gyms") and rec_kind != "Gym + Store":
                        excluded = True
                elif ex_kind == "Gyms which sell products also":
                    if (rec_kind in ("Gym + Store", "Gym which sells products", "Gym + Store (Hybrid)")
                        or "product" in rec_cat
                        or ("gym" in rec_cat and any(w in rec_cat for w in ("supplement", "nutrition", "counter", "pro-shop", "protein", "shake")))):
                        excluded = True
                elif rec_kind.casefold() == ex_kind.casefold() or ex_kind.casefold() in rec_cat:
                    excluded = True

            if not excluded and ex_name:
                rec_name = str(record.get("business_name") or record.get("name") or "").casefold()
                if ex_name in rec_name:
                    excluded = True

            if not excluded and ex_district:
                rec_district = " ".join([str(record.get("city") or ""), str(record.get("area") or ""), str(record.get("district") or "")]).casefold()
                if ex_district in rec_district:
                    excluded = True

            if not excluded and ex_keywords:
                for kw in ex_keywords:
                    if kw in search_blob:
                        excluded = True
                        break

            shown = (not excluded) and matches_kind and matches_state and matches_search and matches_contact and matches_website and matches_verification
            self.leads_table.setRowHidden(row_index, not shown)
            visible += shown
        self.results_label.setText(
            f"Showing {visible:,} of {len(self.records):,} stores in directory."
            if self.records else "No store records loaded. Use '⚡ 1-Tap Deep Web Scraping & Master Update' above."
        )

    def apply_theme(self, theme_name="night"):
        self._current_theme_name = (theme_name or "night").lower()
        is_dark = self._current_theme_name in {"night", "dark", "ocean", "sunset"}

        bg = "#0B1120" if is_dark else "#F8FAFC"
        card_bg = "rgba(15, 23, 42, 0.90)" if is_dark else "#FFFFFF"
        border = "rgba(59, 130, 246, 0.35)" if is_dark else "#CBD5E1"
        title_fg = "#FFFFFF" if is_dark else "#0F172A"
        text_fg = "#FFFFFF" if is_dark else "#0F172A"
        secondary_fg = "#CBD5E1" if is_dark else "#334155"
        input_bg = "#1E293B" if is_dark else "#FFFFFF"
        input_border = "rgba(255, 255, 255, 0.20)" if is_dark else "#CBD5E1"
        table_bg = "#0F172A" if is_dark else "#FFFFFF"
        table_alt_bg = "#1E293B" if is_dark else "#F8FAFC"
        header_bg = "#1E293B" if is_dark else "#F1F5F9"
        header_fg = "#38BDF8" if is_dark else "#1E40AF"

        self.setStyleSheet(f"""
            QWidget#customerProspectsContainer {{ background-color: {bg}; }}
            QLabel {{ color: {text_fg}; font-size: 9pt; }}
            QLabel#prospectTitle {{ color: {title_fg}; font-size: 18pt; font-weight: 800; }}
            QLabel#prospectKpiValue {{ font-size: 17pt; font-weight: 800; }}
            QLabel#prospectKpiLabel {{ font-size: 8.5pt; font-weight: 600; color: {secondary_fg}; }}
            QLabel#prospectReconciliation {{ color: {secondary_fg}; }}
            QLabel#prospectViewLabel {{ color: #38BDF8; font-weight: 800; font-size: 10pt; }}
            QFrame#prospectActionCard {{ background: {card_bg}; border: 1.5px solid {border}; border-radius: 10px; }}
            QFrame#prospectKpiCard {{ background: {card_bg}; border: 1.5px solid {border}; border-radius: 10px; }}
            QFrame#storeDirectoryPrintCard {{ background: {card_bg}; border: 1.5px solid {border}; border-radius: 10px; }}
            QFrame#regionalDashboardPrintCard {{ background: {card_bg}; border: 1.5px solid {border}; border-radius: 10px; }}
            QFrame#prospectViewNavCard {{ background: {card_bg}; border: 1.5px solid {border}; border-radius: 10px; }}
            QLineEdit {{ background-color: {input_bg}; color: {text_fg}; border: 1.5px solid {input_border}; border-radius: 6px; padding: 5px 10px; font-size: 9pt; min-height: 24px; }}
            QLineEdit:focus {{ border-color: #38BDF8; }}
            QComboBox {{ background-color: {input_bg}; color: {text_fg}; border: 1.5px solid {input_border}; border-radius: 6px; padding: 5px 10px; font-size: 9pt; min-height: 24px; }}
            QComboBox:focus {{ border-color: #38BDF8; }}
            QComboBox QAbstractItemView {{ background-color: {card_bg}; color: {text_fg}; selection-background-color: #2563EB; selection-color: #FFFFFF; border: 1px solid {border}; }}
            QTableWidget {{ background-color: {table_bg}; color: {text_fg}; gridline-color: rgba(255, 255, 255, 0.10); alternate-background-color: {table_alt_bg}; selection-background-color: #2563EB; selection-color: #FFFFFF; font-size: 9pt; border: 1px solid {border}; }}
            QTableWidget::item {{ color: {text_fg}; padding: 6px 8px; }}
            QTableWidget::item:selected {{ background-color: #2563EB; color: #FFFFFF; }}
            QHeaderView::section {{ background-color: {header_bg}; color: {header_fg}; font-weight: 700; font-size: 8.5pt; padding: 8px 6px; border: 1px solid {border}; }}
            QTabBar::tab {{ font-size: 9pt; font-weight: 700; padding: 6px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
            QTabBar::tab:selected {{ background: #2563EB; color: #FFFFFF; }}
            QTabBar::tab:!selected {{ background: rgba(30, 41, 59, 0.7); color: {secondary_fg}; }}
            QScrollBar:vertical {{ background: {table_bg}; width: 14px; margin: 0px; border: 1px solid {border}; border-radius: 7px; }}
            QScrollBar::handle:vertical {{ background: #3B82F6; min-height: 28px; border-radius: 6px; }}
            QScrollBar::handle:vertical:hover {{ background: #60A5FA; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)

        palette = self.leads_table.palette()
        palette.setColor(QPalette.ColorRole.Text, QColor(text_fg))
        palette.setColor(QPalette.ColorRole.Base, QColor(table_bg))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(table_alt_bg))
        self.leads_table.setPalette(palette)
        self.region_table.setPalette(palette)
