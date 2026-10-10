import os, sys, sqlite3, shutil, webbrowser, hashlib, secrets
from pathlib import Path
from datetime import datetime, date
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QDateEdit, QTimeEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QInputDialog, QDialog, QDialogButtonBox, QHeaderView,
    QGroupBox, QProgressBar, QAbstractItemView, QCheckBox, QScrollArea
)
from PySide6.QtGui import QAction, QPainter, QColor, QPen, QFont, QPixmap
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, HRFlowable
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Embedded historical audit seed data (combined from audit_seed.py).
SOURCE_FILENAME = "EMPLOYEE AUDIT 09-10-2026.docx"
SOURCE_DATE_DISPLAY = "09-10-2026"
SOURCE_DATE_ISO = "2026-10-09"
SOURCE_TEXT = 'EMPLOYEE AUDIT: 09-10-2026\n\n\n\nGOPI:\nWORK : Submitted\nLATE: no\nLinks :  Open\nMissing proof: No\nCompleted: \n   \tUSA comical video for fun and facts\nhttps://drive.google.com/file/d/1suvFWDq6mxPv6xzNZTBYOXn0HV21H79o/view?usp=drive_link\n\nshoot completed for Myusa educational reel\n https://drive.google.com/drive/folders/16RwXdDsl7Yrcgxk-ePf4sHeh9geZvcJW?usp=drive_link\n\neducational reel edit \nhttps://drive.google.com/file/d/1ZxCHlEUmiJwqz75ZERt1TNkHKjihTT_f/view?usp=drive_link\n\nPARTIAL : No\nPENDING : No \n\nVINAY:\nwork : submitted\nLate :no\nLinks : open\nMissing proof: all proofs submitted\nCompleted: \n  \t\tprotein bar story line – 1 carousal (6 slides)\n \t\tcomical carousals-1 (7 slides)\n \t\tvideo static – 1 meme video\n \t\tInstagram stories – 3\n \t\tdussehra creatives- 3\nhttps://drive.google.com/drive/folders/1ryLbi_DMBzg3cm_cUQUSBsjLCInZTPIo?usp=sharing\npending: NO\n\n\nSIRI:\nWORK: submitted\nLATE : no\nLINKS OPEN: yes\nMISSING PROOF : No\nCOMPLETED: \n \t\tNew data collected: jammu and Kashmir=20\n \t\t\t\t        Gujarat=33,Jharkhand =15,Haryana=2,goa=1\n      \t\t\tshe has total stores count=1231\n              \tcalls done : 17 but connected 8  & confirm decision makers names: 5\nDatabase: https://1drv.ms/x/c/42cb0433cf46e2a2/IQBmYm2HAA65RKFmVhyPK4siAY_ozlYUA35h0SMWNOHAvBI?e=OKv1o8\n\nDashboard: https://1drv.ms/x/c/42cb0433cf46e2a2/IQDkko37oqDORb_b5GVbdBFLAe5_LTQh0JQzGV0NqDA-fnw?e=TdKlvg\n\nHaryana Store Calling Sheet: https://1drv.ms/x/c/42cb0433cf46e2a2/IQAj4MUlGYMHTpMpSqQ2d3VIAZNU63tnUY4r8qktC98QaqA?e=iQnwK9\n\nTelangana & Andhra Pradesh Automation Sheet: https://1drv.ms/x/c/42cb0433cf46e2a2/IQD6T_R83XX2QaaqGMj_WsSCAfGivAh1j3CCOpn7ykk-M0k?e=TVPcgu\nPENDING :  No\nshe has done: attached siri and sanjana numbers to automation ,so they can get to know about message sending or not ( received or not to customers/distributors).\n \nSANJANA: \n\nWORK: submitted\nLATE: no\nPROOF : links open\nMISSING PROOF: NO\nCOMPLETED: \n \t\t\tMY operator automation messages sent to AP & telangana\n \t\t\tvijayawada and tirupathi samples sachets –dispatched\n \t\t\thiprocket regarding the return charges. The team advised waiting 10–15 days for an update on the ticket raised.\n \t\t\trecieved siri database  and calls done= 60 but connected 37, 29 from sanjana  and 8 from siri \n \t\t\twarm distributors- sri sai balaji –tirupathi and sent 5 samples \n \t\t\tconnected to nutracore to got confirmation for samples sachets recieved or    not.\n \t\t\tOut for delivery calls: 1 \n \t\t\tpredispatch message sent=3 \nhttps://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=70451726\n\nhttps://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=825994323\n\nPENDING:No\n\n LOHITH:\n\nWORK: Submitted \nLATE : No\nOPEN LINKS: No links but proofs attached in EOD\nMISSING PROOF :NO\nCOMPLETED: All assigned tasks\nPENDING: B2B need to finalise\n\n\nTARUNA:\nWORK: Submitted in time\nLATE:  no\nOPEN LINKS : all links submitted and open\ncompleted:\nStock reconciliation\nstock movement\noutgoing and incoming payment list\ncollected proof links \norder dispatchness\nverified registers and assets and submitted operational requirements in EOD\nproof links:\nFUN AND FACTS TRACKER:\nfun ^L0 facts postings.xlsx\nstock movement.xlsx\nhttps://1drv.ms/x/c/c11b3da91d61d188/IQDclrlPdHLFQ7cUImGfQ9xCAaHY-_xYC5Pjll-TJPSHsM8?e=do2sFs\noutgoing payment list.xlsx\nincoming payment list.xlsx\nMISSING PROOF: No\nPENDING :NO\n\n\nSAILU:\nWORK: Submitted in time\nLATE:  No \nOPEN LINKS : yes\nMISSING PROOF: No\nCOMPLETED: Lillte footprints all 3 activities done\n \t\tmits medha admission script\n \t\tharish sir educational  script:\n \t\tDasara script\n \t\tcoordinated with sai teja and gopi explaining scripts for shoot and also helped in editing .\xa0\n \t\tFun and facts reel caption\nLillte footprints last script:\xa0\n\nhttps://1drv.ms/w/c/e2ee80143bb8aa3f/IQCqK4Js0RMeTZ_ujf9N34CHAS0748iel1v89ppKu1Wbi4c?e=xC4Ubb\xa0\n\nmits medha script:\xa0\n\nhttps://1drv.ms/w/c/e2ee80143bb8aa3f/IQCFXtlMMKBLSq4WPcqo6UMnASlqLgzKvbKQSojjyV3bovM?e=lxc3WP\xa0\n\nharish sir script:\xa0\n\nhttps://1drv.ms/w/c/e2ee80143bb8aa3f/IQCQzkvBuaQpRYXqNLtunt0_AQK0O0xaqgAQO4pZDanLo4M?e=BblsL9\xa0\n\nDasara script:\xa0\n\nhttps://1drv.ms/w/c/e2ee80143bb8aa3f/IQCQzkvBuaQpRYXqNLtunt0_AQK0O0xaqgAQO4pZDanLo4M?e=BblsL9\xa0\n\nTomorrow educational script:\n\nhttps://1drv.ms/w/c/e2ee80143bb8aa3f/IQCQzkvBuaQpRYXqNLtunt0_AQK0O0xaqgAQO4pZDanLo4M?e=BblsL9\xa0\n\n\nPENDING : No\nMissing: Morning comical reel script\n\nSAI TEJA\n\nWORK: Submitted \nLATE : No\nOPEN LINKS: Yes\nMISSING PROOF :NO\nCOMPLETED : All villan world characters modifications done\n \t\t       comical video shoot done  and edited with needed changes and posted in fun and facts\nPENDING: Villan intro animations.\nproof links:\nhttps://drive.google.com/drive/folders/1ns_EPaE3jamFYkq0Y0BRIeKLkROy1Ygs?usp=share_link\n\nhttps://www.instagram.com/reel/DeRhfPdSKvH/?rpxt=enR1bWpyOWc5YWZo\n\nhttps://drive.google.com/drive/folders/1dCMip95NJjrEKQSVAQeW0imH7qYvWFzY?usp=share_link'

EMPLOYEES = [
    {"name": "Gopi", "notes": "Imported from historical audit 09-10-2026. WORK: Submitted. LATE: No. Links: Open. Missing proof: No. PARTIAL: No. PENDING: No."},
    {"name": "Vinay", "notes": "Imported from historical audit 09-10-2026. WORK: Submitted. LATE: No. Links: Open. Missing proof: All proofs submitted. PENDING: No."},
    {"name": "Siri", "notes": "Imported from historical audit 09-10-2026. WORK: Submitted. LATE: No. Links open: Yes. Missing proof: No. PENDING: No."},
    {"name": "Sanjana", "notes": "Imported from historical audit 09-10-2026. WORK: Submitted. LATE: No. Proof links: Open. Missing proof: No. PENDING: No."},
    {"name": "Lohith", "notes": "Imported from historical audit 09-10-2026. WORK: Submitted. LATE: No. No separate links; proofs attached in EOD. Missing proof: No. PENDING: B2B need to finalise."},
    {"name": "Taruna", "notes": "Imported from historical audit 09-10-2026. WORK: Submitted in time. LATE: No. All submitted links reported open. Missing proof: No. PENDING: No."},
    {"name": "Sailu", "notes": "Imported from historical audit 09-10-2026. WORK: Submitted in time. LATE: No. Links open: Yes. Missing proof: No. PENDING: No. Missing: Morning comical reel script."},
    {"name": "Sai Teja", "notes": "Imported from historical audit 09-10-2026. WORK: Submitted. LATE: No. Links open: Yes. Missing proof: No. PENDING: Villain intro animations."},
]

# Each completed source item remains Submitted (not silently converted to Completed),
# with source wording and source status retained. Pending items remain Pending.
TASKS = [
    ("Gopi", "USA comical video for fun and facts", "Completed item in source report. Original WORK status: Submitted.", ["https://drive.google.com/file/d/1suvFWDq6mxPv6xzNZTBYOXn0HV21H79o/view?usp=drive_link"], "", "Submitted", 100),
    ("Gopi", "Shoot completed for Myusa educational reel", "Completed item in source report. Original WORK status: Submitted.", ["https://drive.google.com/drive/folders/16RwXdDsl7Yrcgxk-ePf4sHeh9geZvcJW?usp=drive_link"], "", "Submitted", 100),
    ("Gopi", "Educational reel edit", "Completed item in source report. Original WORK status: Submitted.", ["https://drive.google.com/file/d/1ZxCHlEUmiJwqz75ZERt1TNkHKjihTT_f/view?usp=drive_link"], "", "Submitted", 100),

    ("Vinay", "Protein bar story line — 1 carousel (6 slides)", "Completed item in source report. Shared proof folder supplied for Vinay's completed work.", ["https://drive.google.com/drive/folders/1ryLbi_DMBzg3cm_cUQUSBsjLCInZTPIo?usp=sharing"], "Source: 1 carousel, 6 slides.", "Submitted", 100),
    ("Vinay", "Comical carousals — 1 (7 slides)", "Completed item in source report. Shared proof folder supplied for Vinay's completed work.", ["https://drive.google.com/drive/folders/1ryLbi_DMBzg3cm_cUQUSBsjLCInZTPIo?usp=sharing"], "Source wording preserved: comical carousals-1 (7 slides).", "Submitted", 100),
    ("Vinay", "Video static — 1 meme video", "Completed item in source report. Shared proof folder supplied for Vinay's completed work.", ["https://drive.google.com/drive/folders/1ryLbi_DMBzg3cm_cUQUSBsjLCInZTPIo?usp=sharing"], "", "Submitted", 100),
    ("Vinay", "Instagram stories — 3", "Completed item in source report. Shared proof folder supplied for Vinay's completed work.", ["https://drive.google.com/drive/folders/1ryLbi_DMBzg3cm_cUQUSBsjLCInZTPIo?usp=sharing"], "", "Submitted", 100),
    ("Vinay", "Dussehra creatives — 3", "Completed item in source report. Shared proof folder supplied for Vinay's completed work.", ["https://drive.google.com/drive/folders/1ryLbi_DMBzg3cm_cUQUSBsjLCInZTPIo?usp=sharing"], "", "Submitted", 100),

    ("Siri", "New data collected across states", "Jammu and Kashmir=20; Gujarat=33; Jharkhand=15; Haryana=2; Goa=1. Total stores count=1231.", ["https://1drv.ms/x/c/42cb0433cf46e2a2/IQBmYm2HAA65RKFmVhyPK4siAY_ozlYUA35h0SMWNOHAvBI?e=OKv1o8", "https://1drv.ms/x/c/42cb0433cf46e2a2/IQDkko37oqDORb_b5GVbdBFLAe5_LTQh0JQzGV0NqDA-fnw?e=TdKlvg"], "Source evidence labels: Database; Dashboard.", "Submitted", 100),
    ("Siri", "Store calling activity and decision-maker confirmation", "Calls done: 17; connected: 8; confirmed decision-maker names: 5.", ["https://1drv.ms/x/c/42cb0433cf46e2a2/IQAj4MUlGYMHTpMpSqQ2d3VIAZNU63tnUY4r8qktC98QaqA?e=iQnwK9"], "Source evidence label: Haryana Store Calling Sheet.", "Submitted", 100),
    ("Siri", "Automation message delivery tracking setup", "Attached Siri and Sanjana numbers to automation so message sending/receipt can be checked for customers/distributors.", ["https://1drv.ms/x/c/42cb0433cf46e2a2/IQD6T_R83XX2QaaqGMj_WsSCAfGivAh1j3CCOpn7ykk-M0k?e=TVPcgu"], "Source evidence label: Telangana & Andhra Pradesh Automation Sheet.", "Submitted", 100),

    ("Sanjana", "MY operator automation messages sent to AP & Telangana", "Completed item in source report.", ["https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=70451726"], "Second source sheet: https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=825994323", "Submitted", 100),
    ("Sanjana", "Vijayawada and Tirupati sample sachets dispatched", "Completed item in source report.", ["https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=825994323"], "", "Submitted", 100),
    ("Sanjana", "Hiprocket return-charge ticket follow-up", "Team advised waiting 10–15 days for an update on the ticket raised.", [], "Follow-up is waiting for the team's update; source report still lists PENDING: No.", "Submitted", 100),
    ("Sanjana", "Received Siri database and completed calls", "Total calls: 60; connected: 37; 29 from Sanjana and 8 from Siri.", ["https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=70451726", "https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=825994323"], "Both original spreadsheet links retained.", "Submitted", 100),
    ("Sanjana", "Warm distributor — Sri Sai Balaji, Tirupati; 5 samples sent", "Completed item in source report.", ["https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=825994323"], "", "Submitted", 100),
    ("Sanjana", "Contacted Nutracore to confirm sample sachets receipt", "Connected to Nutracore to get confirmation whether sample sachets were received.", ["https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=70451726", "https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=825994323"], "", "Submitted", 100),
    ("Sanjana", "Out-for-delivery calls and pre-dispatch messages", "Out for delivery calls: 1. Pre-dispatch messages sent: 3.", ["https://docs.google.com/spreadsheets/d/1Dblj5pmjVnNZSXKRSpbqyTf5vOqQXAc8cRXxUbolS58/edit?gid=70451726"], "", "Submitted", 100),

    ("Lohith", "All assigned tasks", "Source report states: All assigned tasks completed.", [], "No separate links; proofs attached in EOD. Source missing proof: No.", "Submitted", 100),
    ("Lohith", "B2B needs to finalise", "Pending item exactly as stated in source report.", [], "Imported as pending work; do not mark completed until manager updates it.", "Pending", 0),

    ("Taruna", "Stock reconciliation", "Completed item in source report.", [], "Source proof references: Fun and Facts Tracker filename: fun ^L0 facts postings.xlsx. No URL supplied for this filename.", "Submitted", 100),
    ("Taruna", "Stock movement", "Completed item in source report.", ["https://1drv.ms/x/c/c11b3da91d61d188/IQDclrlPdHLFQ7cUImGfQ9xCAaHY-_xYC5Pjll-TJPSHsM8?e=do2sFs"], "Source filename: stock movement.xlsx.", "Submitted", 100),
    ("Taruna", "Outgoing and incoming payment lists", "Completed item in source report.", [], "Source filenames: outgoing payment list.xlsx; incoming payment list.xlsx. No URLs supplied for these filenames.", "Submitted", 100),
    ("Taruna", "Collected proof links", "Completed item in source report.", [], "Source report does not specify a separate URL for this item.", "Submitted", 100),
    ("Taruna", "Order dispatchness", "Original wording preserved from source report.", [], "No separate URL supplied for this item.", "Submitted", 100),
    ("Taruna", "Verified registers and assets; submitted operational requirements in EOD", "Completed item in source report.", [], "No separate URL supplied for this item.", "Submitted", 100),

    ("Sailu", "Little footprints — all 3 activities done", "Completed item in source report. Original spelling preserved in source snapshot.", ["https://1drv.ms/w/c/e2ee80143bb8aa3f/IQCqK4Js0RMeTZ_ujf9N34CHAS0748iel1v89ppKu1Wbi4c?e=xC4Ubb"], "Source label: Lillte footprints last script.", "Submitted", 100),
    ("Sailu", "MITs Medha admission script", "Completed item in source report.", ["https://1drv.ms/w/c/e2ee80143bb8aa3f/IQCFXtlMMKBLSq4WPcqo6UMnASlqLgzKvbKQSojjyV3bovM?e=lxc3WP"], "Source label: mits medha script.", "Submitted", 100),
    ("Sailu", "Harish Sir educational script", "Completed item in source report.", ["https://1drv.ms/w/c/e2ee80143bb8aa3f/IQCQzkvBuaQpRYXqNLtunt0_AQK0O0xaqgAQO4pZDanLo4M?e=BblsL9"], "Source label: harish sir script.", "Submitted", 100),
    ("Sailu", "Dasara script", "Completed item in source report.", ["https://1drv.ms/w/c/e2ee80143bb8aa3f/IQCQzkvBuaQpRYXqNLtunt0_AQK0O0xaqgAQO4pZDanLo4M?e=BblsL9"], "Duplicate URL is intentionally preserved exactly as shown in the source.", "Submitted", 100),
    ("Sailu", "Coordinated with Sai Teja and Gopi; explained shoot scripts and helped editing", "Completed item in source report.", ["https://1drv.ms/w/c/e2ee80143bb8aa3f/IQCqK4Js0RMeTZ_ujf9N34CHAS0748iel1v89ppKu1Wbi4c?e=xC4Ubb"], "Shared source evidence retained; no unique link was stated for this item.", "Submitted", 100),
    ("Sailu", "Fun and Facts reel caption / tomorrow educational script", "Fun and Facts reel caption is listed under completed work; source also lists Tomorrow educational script as a proof reference.", ["https://1drv.ms/w/c/e2ee80143bb8aa3f/IQCQzkvBuaQpRYXqNLtunt0_AQK0O0xaqgAQO4pZDanLo4M?e=BblsL9"], "Tomorrow educational script URL duplicated the Harish Sir / Dasara URL in the source; preserved exactly.", "Submitted", 100),
    ("Sailu", "Morning comical reel script", "Missing item noted at the end of Sailu's source section.", [], "Source wording: Missing: Morning comical reel script.", "Pending", 0),

    ("Sai Teja", "All villain world characters modifications done", "Completed item in source report.", ["https://drive.google.com/drive/folders/1ns_EPaE3jamFYkq0Y0BRIeKLkROy1Ygs?usp=share_link"], "", "Submitted", 100),
    ("Sai Teja", "Comical video shoot completed, edited with needed changes, and posted in Fun and Facts", "Completed item in source report.", ["https://www.instagram.com/reel/DeRhfPdSKvH/?rpxt=enR1bWpyOWc5YWZo", "https://drive.google.com/drive/folders/1dCMip95NJjrEKQSVAQeW0imH7qYvWFzY?usp=share_link"], "Both original links are retained.", "Submitted", 100),
    ("Sai Teja", "Villain intro animations", "Pending item exactly as stated in source report.", [], "Do not mark completed until manager updates the task.", "Pending", 0),
]

def seed_initial_audit(db):
    key = "initial_audit_2026_10_09_imported"
    if db.get_setting(key) == "1":
        return
    existing = db.conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    if existing:
        db.set_setting(key, "skipped_existing_data")
        return
    try:
        db.conn.execute("BEGIN")
        db.conn.execute("INSERT OR IGNORE INTO source_reports(report_date, source_filename, raw_text, imported_at) VALUES(?,?,?,?)",
                        (SOURCE_DATE_ISO, SOURCE_FILENAME, SOURCE_TEXT, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        employee_ids = {}
        for e in EMPLOYEES:
            cur = db.conn.execute("INSERT INTO employees(employee_code,name,department,designation,joining_date,active,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                  (None, e["name"], "", "", "", 1, e["notes"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            employee_ids[e["name"]] = cur.lastrowid
        for name, title, details, proof_links, proof_note, status, progress in TASKS:
            proof = "\n".join(proof_links)
            note = proof_note.strip()
            if status == "Submitted":
                note = (note + "\n" if note else "") + "Historical source status: WORK submitted; source item listed under Completed. Imported as Submitted, not automatically converted to Completed."
            db.conn.execute("""INSERT INTO tasks(employee_id,task_date,title,details,due_time,priority,status,progress,proof_url,proof_note,submitted_at,manager_note)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (employee_ids[name], SOURCE_DATE_ISO, title, details, "", "Normal", status, progress, proof, note, "", ""))
        db.conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, "1"))
        db.conn.execute("INSERT INTO audit_log(timestamp,action,details) VALUES(?,?,?)",
                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Initial historical audit imported", f"Imported {len(EMPLOYEES)} employees and {len(TASKS)} task records from {SOURCE_FILENAME} ({SOURCE_DATE_DISPLAY})."))
        db.conn.commit()
    except Exception:
        db.conn.rollback()
        raise


APP_NAME = "Raw Strength Calisthenics — Employee Audit Manager"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "EmployeeAuditManager"
DB_PATH = APP_DIR / "employee_audit.db"
BACKUP_DIR = APP_DIR / "backups"
EXPORT_DIR = Path.home() / "Documents" / "EmployeeAuditReports"
APP_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def hash_pin(pin, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200_000).hex()
    return salt, digest

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.setup()

    def setup(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
          display_name TEXT NOT NULL DEFAULT '',
          role TEXT NOT NULL CHECK(role IN ('Admin','HR')),
          password_salt TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          security_question TEXT NOT NULL,
          answer_salt TEXT NOT NULL,
          answer_hash TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS employees(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_code TEXT UNIQUE,
          name TEXT NOT NULL, department TEXT DEFAULT '', designation TEXT DEFAULT '',
          phone TEXT DEFAULT '', email TEXT DEFAULT '', joining_date TEXT DEFAULT '',
          active INTEGER DEFAULT 1, notes TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
          task_date TEXT NOT NULL, title TEXT NOT NULL, details TEXT DEFAULT '',
          due_time TEXT DEFAULT '', priority TEXT DEFAULT 'Normal',
          status TEXT DEFAULT 'Not started', progress INTEGER DEFAULT 0,
          proof_url TEXT DEFAULT '', proof_note TEXT DEFAULT '', submitted_at TEXT DEFAULT '',
          manager_note TEXT DEFAULT '', FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS attendance(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
          work_date TEXT NOT NULL, check_in TEXT DEFAULT '', check_out TEXT DEFAULT '',
          break_minutes INTEGER DEFAULT 0, attendance_status TEXT DEFAULT 'Unmarked',
          attendance_note TEXT DEFAULT '', updated_at TEXT NOT NULL, UNIQUE(employee_id, work_date),
          FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS holidays(
          holiday_date TEXT PRIMARY KEY, holiday_name TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS archived_documents(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NULL,
          report_date TEXT DEFAULT '', file_name TEXT NOT NULL, mime_type TEXT DEFAULT 'application/pdf',
          content BLOB NOT NULL, notes TEXT DEFAULT '', uploaded_at TEXT NOT NULL,
          FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log(
          id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
          action TEXT NOT NULL, details TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS source_reports(
          id INTEGER PRIMARY KEY AUTOINCREMENT, report_date TEXT NOT NULL,
          source_filename TEXT NOT NULL, raw_text TEXT NOT NULL,
          imported_at TEXT NOT NULL, UNIQUE(report_date, source_filename)
        );
        """)
        # Safe additive migrations for databases created by earlier app versions.
        employee_columns = {r["name"] for r in c.execute("PRAGMA table_info(employees)").fetchall()}
        for column, declaration in (("phone", "TEXT DEFAULT ''"), ("email", "TEXT DEFAULT ''")):
            if column not in employee_columns:
                c.execute(f"ALTER TABLE employees ADD COLUMN {column} {declaration}")
        attendance_columns = {r["name"] for r in c.execute("PRAGMA table_info(attendance)").fetchall()}
        if "attendance_status" not in attendance_columns:
            c.execute("ALTER TABLE attendance ADD COLUMN attendance_status TEXT DEFAULT 'Unmarked'")
            c.execute("UPDATE attendance SET attendance_status='Present' WHERE COALESCE(check_in,'') <> ''")
        if not self.get_setting("working_weekdays"):
            self.set_setting("working_weekdays", "0,1,2,3,4")
        if not self.get_setting("pin_salt"):
            salt, digest = hash_pin("1234")
            self.set_setting("pin_salt", salt)
            self.set_setting("pin_hash", digest)
            self.set_setting("pin_setup_required", "1")
        self.conn.commit()

    def get_setting(self, key, default=""):
        r = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_setting(self, key, value):
        self.conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                          (key, str(value)))
        self.conn.commit()

    def log(self, action, details=""):
        self.conn.execute("INSERT INTO audit_log(timestamp,action,details) VALUES(?,?,?)", (now_text(), action, details))
        self.conn.commit()

    def employees(self, include_inactive=True):
        q = "SELECT * FROM employees"
        if not include_inactive: q += " WHERE active=1"
        return self.conn.execute(q + " ORDER BY active DESC, name COLLATE NOCASE").fetchall()

    def employee(self, emp_id):
        return self.conn.execute("SELECT * FROM employees WHERE id=?", (emp_id,)).fetchone()

    def tasks(self, task_date=None, employee_id=None):
        q = """SELECT t.*, e.name AS employee_name, e.employee_code FROM tasks t
               JOIN employees e ON e.id=t.employee_id WHERE 1=1"""
        args = []
        if task_date: q += " AND t.task_date=?"; args.append(task_date)
        if employee_id: q += " AND t.employee_id=?"; args.append(employee_id)
        return self.conn.execute(q + " ORDER BY e.name, t.id DESC", args).fetchall()

    def attendance(self, work_date=None):
        q = """SELECT a.*, e.name AS employee_name, e.employee_code FROM attendance a
               JOIN employees e ON e.id=a.employee_id WHERE 1=1"""
        args=[]
        if work_date: q += " AND a.work_date=?"; args.append(work_date)
        return self.conn.execute(q + " ORDER BY e.name", args).fetchall()

    def upsert_attendance(self, emp_id, work_date, check_in=None, check_out=None, note=None, status=None):
        old = self.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?", (emp_id, work_date)).fetchone()
        if old:
            ci = check_in if check_in is not None else old["check_in"]
            co = check_out if check_out is not None else old["check_out"]
            nt = note if note is not None else old["attendance_note"]
            st = status if status is not None else ("Present" if ci else old["attendance_status"])
            self.conn.execute("UPDATE attendance SET check_in=?,check_out=?,attendance_note=?,attendance_status=?,updated_at=? WHERE id=?",
                              (ci, co, nt, st, now_text(), old["id"]))
        else:
            st = status or ("Present" if check_in else "Unmarked")
            self.conn.execute("INSERT INTO attendance(employee_id,work_date,check_in,check_out,attendance_status,attendance_note,updated_at) VALUES(?,?,?,?,?,?,?)",
                              (emp_id, work_date, check_in or "", check_out or "", st, note or "", now_text()))
        self.conn.commit()

    def working_weekdays(self):
        raw = self.get_setting("working_weekdays", "0,1,2,3,4")
        try: return {int(x) for x in raw.split(",") if x.strip() != ""}
        except ValueError: return {0,1,2,3,4}

    def is_holiday(self, day_text):
        return self.conn.execute("SELECT 1 FROM holidays WHERE holiday_date=?", (day_text,)).fetchone() is not None

    def holidays_between(self, start_date, end_date):
        return self.conn.execute("SELECT * FROM holidays WHERE holiday_date BETWEEN ? AND ? ORDER BY holiday_date", (start_date, end_date)).fetchall()

    def archive_documents(self):
        return self.conn.execute("""SELECT d.id,d.employee_id,d.report_date,d.file_name,d.mime_type,d.notes,d.uploaded_at,e.name AS employee_name
                                  FROM archived_documents d LEFT JOIN employees e ON e.id=d.employee_id
                                  ORDER BY d.uploaded_at DESC""").fetchall()

def ask(parent, title, message):
    return QMessageBox.question(parent, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

def info(parent, message):
    QMessageBox.information(parent, APP_NAME, message)

def error(parent, message):
    QMessageBox.critical(parent, APP_NAME, message)

SECURITY_QUESTIONS = [
    "What was the name of your first school?",
    "What is the name of the city where you were born?",
    "What was your childhood nickname?",
    "What is the name of your first teacher?",
    "What was the first concert or live event you attended?",
]

def normalized_answer(value):
    return " ".join(value.strip().casefold().split())

def password_is_strong(value):
    return len(value) >= 8 and any(c.isalpha() for c in value) and any(c.isdigit() for c in value)

class AccountSetupDialog(QDialog):
    """First-run setup: create the first administrator and recovery question."""
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Initial HR/Admin Setup")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Set up your administrator account")
        title.setStyleSheet("font-size: 18pt; font-weight: 700; color: #0f172a;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Create a secure account before using Raw Strength Calisthenics — Employee Audit Manager. No default password is used."))
        form = QFormLayout()
        self.username = QLineEdit("admin")
        self.display_name = QLineEdit("Administrator")
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password); self.password.setPlaceholderText("At least 8 characters, including a number")
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.Password)
        self.question = QComboBox(); self.question.addItems(SECURITY_QUESTIONS)
        self.answer = QLineEdit(); self.answer.setEchoMode(QLineEdit.Password); self.answer.setPlaceholderText("Recovery answer (remember it exactly)")
        form.addRow("Admin username", self.username)
        form.addRow("Display name", self.display_name)
        form.addRow("New password", self.password)
        form.addRow("Confirm password", self.confirm)
        form.addRow("Password recovery question", self.question)
        form.addRow("Recovery answer", self.answer)
        layout.addLayout(form)
        note = QLabel("Your recovery answer is stored as a salted hash. Choose an answer you can remember.")
        note.setWordWrap(True); note.setStyleSheet("color:#64748b;")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.create_admin); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def create_admin(self):
        username = self.username.text().strip()
        password = self.password.text()
        answer = normalized_answer(self.answer.text())
        if not username or not self.display_name.text().strip():
            return error(self, "Enter a username and display name.")
        if not password_is_strong(password):
            return error(self, "Use a password of at least 8 characters with at least one letter and one number.")
        if password != self.confirm.text():
            return error(self, "The passwords do not match.")
        if len(answer) < 2:
            return error(self, "Enter a recovery answer you can remember.")
        psalt, phash = hash_pin(password)
        asalt, ahash = hash_pin(answer)
        try:
            self.db.conn.execute("""INSERT INTO auth_users(username,display_name,role,password_salt,password_hash,
                security_question,answer_salt,answer_hash,active,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
                (username, self.display_name.text().strip(), "Admin", psalt, phash,
                 self.question.currentText(), asalt, ahash, now_text(), now_text()))
            self.db.conn.commit()
        except sqlite3.IntegrityError:
            return error(self, "That username already exists. Choose another one.")
        self.db.log("Administrator account created", username)
        self.accept()

class ForgotPasswordDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Forgot password / Reset password")
        self.setMinimumWidth(470)
        self.user_row = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.addWidget(QLabel("Reset your password using your saved security question."))
        form = QFormLayout()
        self.username = QLineEdit(); self.username.setPlaceholderText("Your account username")
        self.question_label = QLabel("Enter your username, then click Find question.")
        self.answer = QLineEdit(); self.answer.setEchoMode(QLineEdit.Password); self.answer.setEnabled(False)
        self.new_password = QLineEdit(); self.new_password.setEchoMode(QLineEdit.Password); self.new_password.setEnabled(False)
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.Password); self.confirm.setEnabled(False)
        form.addRow("Username", self.username)
        form.addRow("Recovery question", self.question_label)
        form.addRow("Recovery answer", self.answer)
        form.addRow("New password", self.new_password)
        form.addRow("Confirm password", self.confirm)
        layout.addLayout(form)
        row = QHBoxLayout()
        find_btn = QPushButton("Find question"); find_btn.clicked.connect(self.find_question)
        reset_btn = QPushButton("Reset password"); reset_btn.clicked.connect(self.reset_password)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        row.addWidget(find_btn); row.addWidget(reset_btn); row.addWidget(cancel_btn)
        layout.addLayout(row)

    def find_question(self):
        username = self.username.text().strip()
        self.user_row = self.db.conn.execute("SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1", (username,)).fetchone()
        if not self.user_row:
            self.username.setEnabled(True)
            self.question_label.setText("No active account found for that username.")
            self.answer.setEnabled(False); self.new_password.setEnabled(False); self.confirm.setEnabled(False)
            return
        self.username.setEnabled(False)
        self.question_label.setText(self.user_row["security_question"])
        self.answer.setEnabled(True); self.new_password.setEnabled(True); self.confirm.setEnabled(True)

    def reset_password(self):
        if not self.user_row:
            return error(self, "Find your security question first.")
        answer = normalized_answer(self.answer.text())
        _, digest = hash_pin(answer, self.user_row["answer_salt"])
        if not secrets.compare_digest(digest, self.user_row["answer_hash"]):
            self.answer.clear()
            return error(self, "The recovery answer is incorrect.")
        password = self.new_password.text()
        if not password_is_strong(password):
            return error(self, "Use a password of at least 8 characters with at least one letter and one number.")
        if password != self.confirm.text():
            return error(self, "The passwords do not match.")
        salt, digest = hash_pin(password)
        self.db.conn.execute("UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?",
                              (salt, digest, now_text(), self.user_row["id"]))
        self.db.conn.commit()
        self.db.log("Password reset using recovery question", self.user_row["username"])
        info(self, "Password reset completed. You can now sign in with your new password.")
        self.accept()

class LoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.user = None
        self.setWindowTitle("HR / Admin Sign In")
        self.setMinimumWidth(440)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(13)
        title = QLabel("Raw Strength Calisthenics")
        title.setStyleSheet("font-size: 20pt; font-weight: 700; color: #0f172a;")
        subtitle = QLabel("HR / Admin workspace • Offline and secure")
        subtitle.setStyleSheet("font-size: 10pt; color: #64748b;")
        layout.addWidget(title); layout.addWidget(subtitle)
        form = QFormLayout()
        self.username = QLineEdit(); self.username.setPlaceholderText("Enter username")
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password); self.password.setPlaceholderText("Enter password")
        form.addRow("Username", self.username); form.addRow("Password", self.password)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.check); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        links = QHBoxLayout()
        forgot = QPushButton("Forgot password?"); forgot.setFlat(True); forgot.clicked.connect(self.forgot_password)
        change = QPushButton("Change password"); change.setFlat(True); change.clicked.connect(self.change_password)
        links.addWidget(forgot); links.addWidget(change)
        layout.addLayout(links)
        self.password.returnPressed.connect(self.check)

    def check(self):
        username = self.username.text().strip()
        row = self.db.conn.execute("SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1", (username,)).fetchone()
        if not row:
            return error(self, "Invalid username or password.")
        _, digest = hash_pin(self.password.text(), row["password_salt"])
        if not secrets.compare_digest(digest, row["password_hash"]):
            self.password.clear()
            return error(self, "Invalid username or password.")
        self.user = dict(row)
        self.db.log("User login", f"{row['username']} ({row['role']})")
        self.accept()

    def forgot_password(self):
        dialog = ForgotPasswordDialog(self.db, self)
        dialog.exec()

    def change_password(self):
        username = self.username.text().strip()
        if not username:
            return error(self, "Enter your username first, then select Change password.")
        row = self.db.conn.execute("SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1", (username,)).fetchone()
        if not row:
            return error(self, "No active account found for that username.")
        current, ok = QInputDialog.getText(self, "Change password", "Current password:", QLineEdit.Password)
        if not ok: return
        _, digest = hash_pin(current, row["password_salt"])
        if not secrets.compare_digest(digest, row["password_hash"]):
            return error(self, "Current password is incorrect.")
        new, ok = QInputDialog.getText(self, "Change password", "New password (8+ characters, letters and numbers):", QLineEdit.Password)
        if not ok: return
        if not password_is_strong(new): return error(self, "Use at least 8 characters, including a letter and a number.")
        confirm, ok = QInputDialog.getText(self, "Change password", "Confirm new password:", QLineEdit.Password)
        if not ok or confirm != new: return error(self, "The passwords do not match.")
        salt, digest = hash_pin(new)
        self.db.conn.execute("UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?", (salt,digest,now_text(),row["id"]))
        self.db.conn.commit(); self.db.log("Password changed", username)
        info(self, "Password changed. Sign in with your new password.")

class EmployeeDialog(QDialog):
    def __init__(self, parent=None, row=None):
        super().__init__(parent); self.setWindowTitle("Employee details"); self.setMinimumWidth(420)
        self.layout=QFormLayout(self)
        self.code=QLineEdit(row["employee_code"] if row else "")
        self.name=QLineEdit(row["name"] if row else "")
        self.department=QLineEdit(row["department"] if row else "")
        self.designation=QLineEdit(row["designation"] if row else "")
        self.phone=QLineEdit(row["phone"] if row and "phone" in row.keys() else "")
        self.email=QLineEdit(row["email"] if row and "email" in row.keys() else "")
        self.phone.setPlaceholderText("Optional")
        self.email.setPlaceholderText("Optional")
        self.join=QDateEdit(); self.join.setCalendarPopup(True); self.join.setDisplayFormat("yyyy-MM-dd")
        self.join.setDate(QDate.fromString(row["joining_date"], "yyyy-MM-dd") if row and row["joining_date"] else QDate.currentDate())
        self.join_known=QCheckBox("Joining date is known")
        self.join_known.setChecked(bool(not row or row["joining_date"]))
        self.join.setEnabled(self.join_known.isChecked())
        self.join_known.toggled.connect(self.join.setEnabled)
        self.notes=QTextEdit(row["notes"] if row else ""); self.notes.setMaximumHeight(75)
        self.layout.addRow("Employee ID / Code", self.code); self.layout.addRow("Full name *", self.name)
        self.layout.addRow("Department", self.department); self.layout.addRow("Role / Designation", self.designation)
        self.layout.addRow("Phone number (optional)", self.phone); self.layout.addRow("Email address (optional)", self.email)
        self.layout.addRow("Joining date", self.join); self.layout.addRow("", self.join_known); self.layout.addRow("Notes", self.notes)
        buttons=QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); self.layout.addRow(buttons)
    def values(self):
        return (self.code.text().strip() or None, self.name.text().strip(), self.department.text().strip(),
                self.designation.text().strip(), self.phone.text().strip(), self.email.text().strip(),
                self.join.date().toString("yyyy-MM-dd") if self.join_known.isChecked() else "", self.notes.toPlainText().strip())

class TaskDialog(QDialog):
    STATUSES=["Not started","In progress","Submitted","Completed","Blocked","Pending review"]
    def __init__(self, db, parent=None, row=None, employee_id=None):
        super().__init__(parent); self.setWindowTitle("Task details"); self.setMinimumWidth(520)
        self.layout=QFormLayout(self); self.db=db; self.row=row
        self.employee=QComboBox()
        for e in db.employees(False): self.employee.addItem(f'{e["name"]} ({e["employee_code"] or e["id"]})', e["id"])
        if employee_id is not None:
            idx=self.employee.findData(employee_id)
            if idx >= 0: self.employee.setCurrentIndex(idx)
        self.date=QDateEdit(); self.date.setCalendarPopup(True); self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setDate(QDate.fromString(row["task_date"],"yyyy-MM-dd") if row else QDate.currentDate())
        self.title=QLineEdit(row["title"] if row else "")
        self.details=QTextEdit(row["details"] if row else ""); self.details.setMaximumHeight(70)
        self.due=QTimeEdit(); self.due.setDisplayFormat("HH:mm"); self.due.setTime(QTime.fromString(row["due_time"],"HH:mm") if row and row["due_time"] else QTime(17,0))
        self.priority=QComboBox(); self.priority.addItems(["Low","Normal","High","Urgent"])
        self.status=QComboBox(); self.status.addItems(self.STATUSES)
        self.progress=QSpinBox(); self.progress.setRange(0,100); self.progress.setSuffix("%")
        self.proof=QTextEdit(row["proof_url"] if row else ""); self.proof.setPlaceholderText("Optional URL or local file path. Use one proof link per line."); self.proof.setMaximumHeight(78)
        self.proof_note=QLineEdit(row["proof_note"] if row else "")
        self.manager_note=QLineEdit(row["manager_note"] if row else "")
        if row:
            idx=self.employee.findData(row["employee_id"])
            if idx>=0: self.employee.setCurrentIndex(idx)
            self.priority.setCurrentText(row["priority"]); self.status.setCurrentText(row["status"]); self.progress.setValue(row["progress"])
        self.layout.addRow("Employee *", self.employee); self.layout.addRow("Task date", self.date)
        self.layout.addRow("Task title *", self.title); self.layout.addRow("Description / deliverable", self.details)
        self.layout.addRow("Due time", self.due); self.layout.addRow("Priority", self.priority)
        self.layout.addRow("Status", self.status); self.layout.addRow("Progress", self.progress)
        self.layout.addRow("Proof link / path", self.proof); self.layout.addRow("Proof notes", self.proof_note)
        self.layout.addRow("Manager remarks", self.manager_note)
        buttons=QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); self.layout.addRow(buttons)
    def values(self):
        if self.employee.count()==0: return None
        status=self.status.currentText(); progress=self.progress.value()
        if status=="Completed": progress=100
        submitted=now_text() if status in ("Submitted","Completed") else (self.row["submitted_at"] if self.row else "")
        return (self.employee.currentData(), self.date.date().toString("yyyy-MM-dd"), self.title.text().strip(),
                self.details.toPlainText().strip(), self.due.time().toString("HH:mm"), self.priority.currentText(),
                status, progress, self.proof.toPlainText().strip(), self.proof_note.text().strip(), submitted,
                self.manager_note.text().strip())

class ProductivityChart(QWidget):
    """Lightweight native Qt bar chart; no charting dependency is required."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.setMinimumHeight(210)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())

    def set_values(self, values):
        self.values = list(values)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setPen(QColor("#64748b"))
        painter.setFont(QFont("Segoe UI", 9))
        if not self.values:
            painter.drawText(self.rect(), Qt.AlignCenter, "No employee productivity data yet")
            return
        left, right, top, bottom = 44, 18, 20, 44
        w = max(1, self.width() - left - right)
        h = max(1, self.height() - top - bottom)
        for tick in (0, 25, 50, 75, 100):
            y = top + h - int(h * tick / 100)
            painter.setPen(QPen(QColor("#e2e8f0"), 1))
            painter.drawLine(left, y, left + w, y)
            painter.setPen(QColor("#64748b"))
            painter.drawText(4, y + 4, f"{tick}%")
        count = len(self.values)
        slot = w / max(count, 1)
        bar_width = max(12, min(42, int(slot * 0.56)))
        for i, (name, score) in enumerate(self.values):
            x = int(left + slot * i + (slot - bar_width) / 2)
            bh = int(h * max(0, min(100, score)) / 100)
            y = top + h - bh
            color = "#16a34a" if score >= 80 else ("#2563eb" if score >= 60 else "#f59e0b")
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(x, y, bar_width, bh, 5, 5)
            painter.setPen(QColor("#0f172a"))
            painter.drawText(x - 8, max(top + 12, y - 5), f"{score}%")
            painter.setPen(QColor("#475569"))
            painter.drawText(int(left + slot * i), top + h + 18, int(slot), 22, Qt.AlignHCenter | Qt.TextSingleLine, name[:13])


class MainWindow(QMainWindow):
    def __init__(self, db, user):
        super().__init__(); self.db=db; self.current_user=user; self.user_role=user.get("role", "HR")
        self.setWindowTitle(APP_NAME); self.resize(1380, 860); self.setMinimumSize(1080, 700)
        self.tabs=QTabWidget(); self.tabs.setTabPosition(QTabWidget.TabPosition.West); self.tabs.setMovable(False); self.setCentralWidget(self.tabs)
        self.dashboard=QWidget(); self.employees_tab=QWidget(); self.tasks_tab=QWidget(); self.tracker_tab=QWidget(); self.attendance_tab=QWidget(); self.reports_tab=QWidget(); self.archive_tab=QWidget(); self.settings_tab=QWidget()
        for widget,title in [(self.dashboard,"Dashboard"),(self.employees_tab,"Employees"),(self.tasks_tab,"Task Manager"),(self.tracker_tab,"Employee Tracker"),(self.attendance_tab,"Attendance"),(self.reports_tab,"Print Center"),(self.archive_tab,"EOD Archive"),(self.settings_tab,"Settings & Backup")]:
            self.tabs.addTab(widget,title)
        self.build_dashboard(); self.build_employees(); self.build_tasks(); self.build_tracker(); self.build_attendance(); self.build_reports(); self.build_archive(); self.build_settings()
        self.polish_tables()
        self.statusBar().showMessage(f"Signed in: {user.get('display_name') or user.get('username')} ({self.user_role})  •  Local database  •  Offline mode")
        self.refresh_all()
        bar=self.menuBar()
        file_menu=bar.addMenu("File")
        backup_action=QAction("Create backup",self); backup_action.triggered.connect(self.backup_db); file_menu.addAction(backup_action)
        password_action=QAction("Change password",self); password_action.triggered.connect(self.change_password); file_menu.addAction(password_action)
        exit_action=QAction("Exit",self); exit_action.triggered.connect(self.close); file_menu.addAction(exit_action)

    def build_dashboard(self):
        l=QVBoxLayout(self.dashboard)
        hero=QHBoxLayout()
        brand=QVBoxLayout()
        logo=QLabel()
        logo_path = resource_path("assets/raw_strength_brand.png")
        if Path(logo_path).exists():
            pix=QPixmap(logo_path)
            logo.setPixmap(pix.scaled(170, 170, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.addWidget(logo)
        brand_title=QLabel("RAW STRENGTH\nCALISTHENICS")
        brand_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_title.setStyleSheet("font-size: 13pt; font-weight: 800; color: #65dcff; letter-spacing: 1px;")
        brand.addWidget(brand_title)
        hero.addLayout(brand, 1)
        heading=QVBoxLayout()
        title=QLabel("Raw Strength Calisthenics — Employee Audit Manager")
        title.setProperty("pageTitle", True)
        heading.addWidget(title)
        subtitle=QLabel("PEOPLE   |   PRODUCTIVITY   |   PROGRESS   |   PERFORMANCE")
        subtitle.setStyleSheet("color:#55d9ff; font-weight:700; letter-spacing:1px;")
        heading.addWidget(subtitle)
        heading.addWidget(QLabel("Offline workforce tracking, attendance, daily tasks and audit reporting."))
        heading.addStretch(1)
        hero.addLayout(heading, 5)
        athlete_panel = QLabel()
        athlete_path = resource_path("assets/raw_strength_athlete.png")
        if Path(athlete_path).exists():
            athlete_pix = QPixmap(athlete_path)
            athlete_panel.setPixmap(athlete_pix.scaled(210, 145, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        athlete_panel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        athlete_panel.setMinimumWidth(150)
        hero.addWidget(athlete_panel, 2)
        l.addLayout(hero)
        self.kpis=QHBoxLayout(); l.addLayout(self.kpis)
        self.kpi_labels=[]
        for title in ["Active employees","Tasks today","Completed today","Pending / blocked","Missing proof"]:
            box=QGroupBox(title); v=QVBoxLayout(box); label=QLabel("0"); label.setStyleSheet("font-size:28px;font-weight:600"); v.addWidget(label); self.kpis.addWidget(box); self.kpi_labels.append(label)
        row=QHBoxLayout(); l.addLayout(row)
        self.dashboard_tasks=QTableWidget(0,6); self.dashboard_tasks.setHorizontalHeaderLabels(["Employee","Task","Status","Progress","Due","Proof"])
        self.dashboard_tasks.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.dashboard_tasks.setEditTriggers(QAbstractItemView.NoEditTriggers)
        row.addWidget(self.dashboard_tasks, 3)
        productivity_box = QGroupBox("Employee productivity score")
        productivity_layout = QVBoxLayout(productivity_box)
        productivity_layout.addWidget(QLabel("Score: task progress 70% + recorded attendance 30%. If one component has no recorded data, the score uses the available component. New employees are measured from joining date; otherwise the first recorded activity is used."))
        self.productivity_chart = ProductivityChart()
        productivity_layout.addWidget(self.productivity_chart)
        row.addWidget(productivity_box, 2)
        self.productivity_table = QTableWidget(0, 7)
        self.productivity_table.setHorizontalHeaderLabels(["Employee", "Joined / tracking start", "Working days", "Present days", "Tasks", "Completed", "Score"])
        self.productivity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.productivity_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.productivity_table)
        buttons=QHBoxLayout(); l.addLayout(buttons)
        for label,slot in [("Add Employee",lambda:self.add_employee()),("Assign Task",lambda:self.add_task()),("Record Attendance",lambda:self.tabs.setCurrentWidget(self.attendance_tab)),("Generate Today's Report",lambda:self.generate_report())]:
            b=QPushButton(label); b.clicked.connect(slot); buttons.addWidget(b)

    def build_employees(self):
        l=QVBoxLayout(self.employees_tab); row=QHBoxLayout(); l.addLayout(row)
        self.emp_search=QLineEdit(); self.emp_search.setPlaceholderText("Search employee name, ID or department"); self.emp_search.textChanged.connect(self.refresh_employees); row.addWidget(self.emp_search)
        for label,slot in [("Add",self.add_employee),("Edit",self.edit_employee),("Activate / Deactivate",self.toggle_employee),("Delete",self.delete_employee)]:
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        self.emp_table=QTableWidget(0,8); self.emp_table.setHorizontalHeaderLabels(["ID","Employee ID","Name","Department","Role","Phone","Email","Status"])
        self.emp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.emp_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.emp_table.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.emp_table)

    def build_tasks(self):
        l=QVBoxLayout(self.tasks_tab); row=QHBoxLayout(); l.addLayout(row)
        self.task_date=QDateEdit(); self.task_date.setCalendarPopup(True); self.task_date.setDisplayFormat("yyyy-MM-dd"); self.task_date.setDate(QDate.currentDate()); self.task_date.dateChanged.connect(self.refresh_tasks)
        row.addWidget(QLabel("Date")); row.addWidget(self.task_date)
        self.task_filter=QComboBox(); self.task_filter.addItem("All employees",None)
        row.addWidget(self.task_filter)
        self.task_filter.currentIndexChanged.connect(self.refresh_tasks)
        for label,slot in [("Add Task",self.add_task),("Edit Selected",self.edit_task),("Delete Selected",self.delete_task),("Open Proof",self.open_proof)]:
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        self.task_table=QTableWidget(0,9); self.task_table.setHorizontalHeaderLabels(["ID","Employee","Task","Priority","Status","Progress","Due","Proof","Manager remarks"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.task_table)

    def build_tracker(self):
        l=QVBoxLayout(self.tracker_tab)
        l.addWidget(QLabel("<h2>Employee Task Tracker</h2><p>Select an employee to review only their tasks, update progress, and maintain evidence links.</p>"))
        filters=QHBoxLayout(); l.addLayout(filters)
        self.tracker_employee=QComboBox(); self.tracker_employee.addItem("Select employee", None)
        self.tracker_employee.currentIndexChanged.connect(self.refresh_tracker)
        self.tracker_date=QDateEdit(); self.tracker_date.setCalendarPopup(True); self.tracker_date.setDisplayFormat("yyyy-MM-dd"); self.tracker_date.setDate(QDate.currentDate()); self.tracker_date.dateChanged.connect(self.refresh_tracker)
        filters.addWidget(QLabel("Employee")); filters.addWidget(self.tracker_employee,2)
        filters.addWidget(QLabel("Task date")); filters.addWidget(self.tracker_date)
        self.tracker_summary=QLabel("Choose an employee to view assigned tasks.")
        self.tracker_summary.setStyleSheet("font-size: 12pt; font-weight: 650; padding: 12px; background: #eff6ff; border: 1px solid #dbeafe; border-radius: 9px;")
        l.addWidget(self.tracker_summary)
        self.tracker_progress=QProgressBar(); self.tracker_progress.setRange(0,100); self.tracker_progress.setValue(0); self.tracker_progress.setFormat("Average task progress: %p%")
        l.addWidget(self.tracker_progress)
        actions=QHBoxLayout(); l.addLayout(actions)
        # Employee Tracker is a read-only employee/date view. Task creation,
        # editing, deletion and proof maintenance remain in Task Manager.
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_tracker)
        actions.addWidget(refresh_button)
        self.tracker_table=QTableWidget(0,8)
        self.tracker_table.setHorizontalHeaderLabels(["Task ID","Task","Priority","Status","Progress","Due time","Proof link","Manager remarks"])
        self.tracker_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tracker_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tracker_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.tracker_table)

    def build_attendance(self):
        l=QVBoxLayout(self.attendance_tab)
        header=QLabel("Attendance & Working Calendar")
        header.setProperty("pageTitle", True)
        l.addWidget(header)
        row=QHBoxLayout(); l.addLayout(row)
        self.att_date=QDateEdit(); self.att_date.setCalendarPopup(True); self.att_date.setDisplayFormat("yyyy-MM-dd"); self.att_date.setDate(QDate.currentDate()); self.att_date.dateChanged.connect(self.refresh_attendance)
        row.addWidget(QLabel("Selected date")); row.addWidget(self.att_date)
        for label,slot in [("Mark Present",lambda:self.set_attendance_status("Present")),("Mark Absent",lambda:self.set_attendance_status("Absent")),("Mark Leave",lambda:self.set_attendance_status("Leave")),("Check In",self.check_in),("Check Out",self.check_out),("Edit Note",self.attendance_note),("Declare Holiday",self.declare_holiday),("Remove Holiday",self.remove_holiday)]:
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        self.holiday_banner=QLabel("")
        self.holiday_banner.setStyleSheet("padding:9px 12px; border-radius:8px; background:#fff7ed; color:#9a3412; font-weight:600;")
        l.addWidget(self.holiday_banner)
        self.att_table=QTableWidget(0,7); self.att_table.setHorizontalHeaderLabels(["Employee","Date","Attendance status","Check-in","Check-out","Net hours","Note"])
        self.att_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.att_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.att_table.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.att_table, 3)
        l.addWidget(QLabel("Monthly and since-joining attendance summary. Declared holidays and configured non-working weekdays are excluded from working-day totals."))
        self.attendance_summary_table=QTableWidget(0,8)
        self.attendance_summary_table.setHorizontalHeaderLabels(["Employee","Join / tracking start","Working days (month)","Present (month)","Absent","Leave","Holidays excluded","Present since start"])
        self.attendance_summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.attendance_summary_table.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.attendance_summary_table, 2)

    def build_reports(self):
        l=QVBoxLayout(self.reports_tab)
        l.addWidget(QLabel("<h2>Print Center</h2><p>Generate employee attendance, employee details, or reference-style Audit/EOD reports. Export to Word, PDF, or CSV.</p>"))
        form=QFormLayout(); l.addLayout(form)
        self.report_type=QComboBox(); self.report_type.addItems(["Audit / EOD", "Employee Attendance", "Employee Details"])
        self.report_date=QDateEdit(); self.report_date.setCalendarPopup(True); self.report_date.setDisplayFormat("yyyy-MM-dd"); self.report_date.setDate(QDate.currentDate())
        self.report_scope=QComboBox(); self.report_scope.addItems(["Consolidated — all employees", "Individual — selected employee"])
        self.report_employee=QComboBox(); self.report_employee.addItem("All employees",None)
        self.report_format=QComboBox(); self.report_format.addItems(["Word (.docx)","PDF (.pdf)","CSV (.csv)"])
        self.archived_report=QComboBox()
        self.archived_report.addItem("Generated report for selected date", None)
        form.addRow("Report type",self.report_type); form.addRow("Report date",self.report_date); form.addRow("Report scope",self.report_scope); form.addRow("Employee",self.report_employee); form.addRow("Output format",self.report_format)
        form.addRow("Historical archived PDF (optional)", self.archived_report)
        self.report_scope.currentIndexChanged.connect(self._report_scope_changed)
        self.archived_report.currentIndexChanged.connect(self._archived_report_changed)
        row=QHBoxLayout(); l.addLayout(row)
        for label,slot in [("Preview Report",self.preview_report),("Generate / Save",self.generate_report),("Print Selected Report",self.print_report),("Open reports folder",self.open_export_folder)]:
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        self.report_summary=QTextEdit(); self.report_summary.setReadOnly(True); self.report_summary.setPlaceholderText("Report preview summary appears here."); l.addWidget(self.report_summary)
        self.report_type.currentTextChanged.connect(lambda _value: self.preview_report())
        self.report_date.dateChanged.connect(lambda _value: self.preview_report())
        self.report_employee.currentIndexChanged.connect(lambda _value: self.preview_report())
        self.refresh_report_employees()
        self.refresh_archived_report_choices()
        self._report_scope_changed()

    def build_archive(self):
        l=QVBoxLayout(self.archive_tab)
        l.addWidget(QLabel("<h2>Historical EOD PDF Archive</h2><p>Upload older employee EOD PDFs and keep their file contents inside the local SQLite database.</p>"))
        row=QHBoxLayout(); l.addLayout(row)
        for label,slot in [("Upload PDF(s)",self.upload_eod_pdfs),("View Selected",self.open_archived_pdf),("Export Selected",self.export_archived_pdf),("Delete Selected",self.delete_archived_pdf),("Refresh",self.refresh_archive)]:
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        self.archive_table=QTableWidget(0,7)
        self.archive_table.setHorizontalHeaderLabels(["ID","File name","Employee","Report date","Uploaded","Notes","Size"])
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.archive_table)
        l.addWidget(QLabel("PDF files are stored as BLOBs in the local database. Back up the database to preserve archived EOD documents."))

    def build_settings(self):
        l=QVBoxLayout(self.settings_tab)
        l.addWidget(QLabel("<h2>Local data & security</h2>"))
        l.addWidget(QLabel(f"Database: {DB_PATH}\nBackups: {BACKUP_DIR}\nReports: {EXPORT_DIR}"))
        row=QHBoxLayout(); l.addLayout(row)
        for label,slot in [("Create Backup",self.backup_db),("Restore Backup",self.restore_backup),("Change Password",self.change_password),("Update Recovery Question",self.update_recovery_question),("Manage HR/Admin Accounts",self.manage_accounts),("Export Employees CSV",self.export_employees_csv)]:
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
            if label == "Manage HR/Admin Accounts" and self.user_role != "Admin":
                b.setEnabled(False); b.setToolTip("Only an Admin account can manage user accounts.")
        l.addWidget(QLabel("Sign in with an HR or Admin account. Use Forgot password on the sign-in screen to reset a password with your saved recovery question. Keep database backups private."))
        days_box=QGroupBox("Working weekdays (used for working-day calculations)")
        days_layout=QHBoxLayout(days_box)
        self.workday_checks=[]
        for day_name in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]:
            cb=QCheckBox(day_name); cb.setChecked(day_name in ["Monday","Tuesday","Wednesday","Thursday","Friday"])
            self.workday_checks.append(cb); days_layout.addWidget(cb)
        saved_days=self.db.working_weekdays()
        for idx,cb in enumerate(self.workday_checks): cb.setChecked(idx in saved_days)
        l.addWidget(days_box)
        save_days=QPushButton("Save Working Week")
        save_days.clicked.connect(self.save_working_week)
        l.addWidget(save_days)
        l.addStretch()

    def polish_tables(self):
        """Apply consistent, readable table behavior across the application."""
        for page in (self.dashboard, self.employees_tab, self.tasks_tab, self.tracker_tab, self.attendance_tab, self.reports_tab, self.archive_tab, self.settings_tab):
            page_layout = page.layout()
            if page_layout:
                page_layout.setContentsMargins(20, 18, 20, 18)
                page_layout.setSpacing(14)
        for table in (self.dashboard_tasks, self.emp_table, self.task_table, self.tracker_table, self.att_table, self.productivity_table, self.attendance_summary_table, self.archive_table):
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.verticalHeader().setVisible(False)
            table.verticalHeader().setDefaultSectionSize(36)
            table.setWordWrap(False)
            table.setCornerButtonEnabled(False)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.setFocusPolicy(Qt.StrongFocus)
            table.horizontalHeader().setMinimumHeight(38)
            table.horizontalHeader().setHighlightSections(False)
            table.horizontalHeader().setStretchLastSection(True)

    def selected_id(self, table, col=0):
        rows=table.selectionModel().selectedRows()
        if not rows: return None
        item=table.item(rows[0].row(),col)
        return int(item.text()) if item else None

    def refresh_all(self):
        self.refresh_employees(); self.refresh_task_filter(); self.refresh_tracker_employees(); self.refresh_tasks(); self.refresh_tracker(); self.refresh_attendance(); self.refresh_report_employees(); self.refresh_dashboard(); self.refresh_archive()

    def refresh_employees(self):
        if not hasattr(self,"emp_table"): return
        text=self.emp_search.text().lower() if hasattr(self,"emp_search") else ""
        rows=[e for e in self.db.employees() if text in " ".join([str(e["employee_code"] or ""),e["name"],e["department"],e["designation"],e["phone"] or "",e["email"] or ""]).lower()]
        self.emp_table.setRowCount(0)
        for e in rows:
            r=self.emp_table.rowCount(); self.emp_table.insertRow(r)
            vals=[e["id"],e["employee_code"] or "",e["name"],e["department"],e["designation"],e["phone"] or "",e["email"] or "","Active" if e["active"] else "Inactive"]
            for c,v in enumerate(vals): self.emp_table.setItem(r,c,QTableWidgetItem(str(v)))
        self.refresh_task_filter(); self.refresh_report_employees()

    def refresh_task_filter(self):
        if not hasattr(self,"task_filter"): return
        current=self.task_filter.currentData()
        self.task_filter.blockSignals(True); self.task_filter.clear(); self.task_filter.addItem("All employees",None)
        for e in self.db.employees(False): self.task_filter.addItem(e["name"],e["id"])
        idx=self.task_filter.findData(current); self.task_filter.setCurrentIndex(max(idx,0)); self.task_filter.blockSignals(False)

    def refresh_tracker_employees(self):
        if not hasattr(self, "tracker_employee"): return
        current=self.tracker_employee.currentData()
        self.tracker_employee.blockSignals(True); self.tracker_employee.clear(); self.tracker_employee.addItem("Select employee", None)
        for e in self.db.employees(False): self.tracker_employee.addItem(f'{e["name"]} ({e["employee_code"] or e["id"]})', e["id"])
        idx=self.tracker_employee.findData(current); self.tracker_employee.setCurrentIndex(max(idx,0)); self.tracker_employee.blockSignals(False)

    def refresh_tracker(self):
        if not hasattr(self, "tracker_table"): return
        eid=self.tracker_employee.currentData(); d=self.tracker_date.date().toString("yyyy-MM-dd")
        self.tracker_table.setRowCount(0)
        if not eid:
            self.tracker_summary.setText("Choose an employee to view assigned tasks.")
            self.tracker_progress.setValue(0)
            return
        rows=self.db.tasks(d,eid)
        completed=sum(1 for t in rows if t["status"]=="Completed")
        avg=round(sum(t["progress"] for t in rows)/len(rows)) if rows else 0
        pending=sum(1 for t in rows if t["status"] not in ("Completed", "Submitted", "Cancelled"))
        blocked=sum(1 for t in rows if t["status"]=="Blocked")
        in_progress=sum(1 for t in rows if t["status"]=="In progress")
        self.tracker_summary.setText(f"{len(rows)} tasks  •  {completed} completed/submitted  •  {in_progress} in progress  •  {pending} pending  •  {blocked} blocked")
        self.tracker_progress.setValue(avg)
        for t in rows:
            r=self.tracker_table.rowCount(); self.tracker_table.insertRow(r)
            vals=[t["id"],t["title"],t["priority"],t["status"],f'{t["progress"]}%',t["due_time"],t["proof_url"],t["manager_note"]]
            for c,v in enumerate(vals): self.tracker_table.setItem(r,c,QTableWidgetItem(str(v or "")))

    def add_tracker_task(self):
        eid=self.tracker_employee.currentData()
        if not eid: return error(self, "Select an employee first.")
        d=TaskDialog(self.db,self,employee_id=eid)
        d.date.setDate(self.tracker_date.date())
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals or not vals[2]: return error(self,"Task title and active employee are required.")
        self.db.conn.execute("""INSERT INTO tasks(employee_id,task_date,title,details,due_time,priority,status,progress,proof_url,proof_note,submitted_at,manager_note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",vals)
        self.db.conn.commit(); self.db.log("Task added from employee tracker",vals[2]); self.refresh_all()

    def edit_tracker_task(self):
        self.edit_task(self.tracker_table)

    def delete_tracker_task(self):
        self.delete_task(self.tracker_table)

    def open_tracker_proof(self):
        self.open_proof(self.tracker_table)

    def _effective_report_employee_id(self):
        """Return an employee ID for individual reports, otherwise None for consolidated reports."""
        if hasattr(self, "report_scope") and self.report_scope.currentIndex() == 0:
            return None
        return self.report_employee.currentData() if hasattr(self, "report_employee") else None

    def refresh_archived_report_choices(self):
        if not hasattr(self, "archived_report"):
            return
        current = self.archived_report.currentData()
        self.archived_report.blockSignals(True)
        self.archived_report.clear()
        self.archived_report.addItem("Generated report for selected date", None)
        for item in self.db.archive_documents():
            label = f'{item["report_date"] or "Unknown date"} — {item["file_name"]} — {item["employee_name"] or "All employees"}'
            self.archived_report.addItem(label, item["id"])
        idx = self.archived_report.findData(current)
        self.archived_report.setCurrentIndex(max(idx, 0))
        self.archived_report.blockSignals(False)

    def _archived_report_changed(self, *_args):
        if not hasattr(self, "archived_report"):
            return
        is_archived = self.archived_report.currentData() is not None
        for widget in (self.report_type, self.report_date, self.report_scope, self.report_employee, self.report_format):
            widget.setEnabled(not is_archived)
        if is_archived:
            self.report_summary.setPlainText("Historical archived PDF selected. Use Print Selected Report to print it, or Generate / Save to export a copy.")
        else:
            self.preview_report()

    def _report_scope_changed(self, *_args):
        if not hasattr(self, "report_scope") or not hasattr(self, "report_employee"):
            return
        individual = self.report_scope.currentIndex() == 1
        self.report_employee.setEnabled(individual)
        if individual and self.report_employee.currentData() is None and self.report_employee.count() > 1:
            self.report_employee.setCurrentIndex(1)
        self.preview_report()

    def refresh_report_employees(self):
        if not hasattr(self,"report_employee"): return
        current=self.report_employee.currentData()
        self.report_employee.blockSignals(True); self.report_employee.clear(); self.report_employee.addItem("All employees",None)
        for e in self.db.employees(): self.report_employee.addItem(f'{e["name"]} ({e["employee_code"] or "No ID"})',e["id"])
        idx=self.report_employee.findData(current); self.report_employee.setCurrentIndex(max(idx,0)); self.report_employee.blockSignals(False)

    def add_employee(self):
        d=EmployeeDialog(self)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals[0]: return error(self,"Employee ID is required.")
        if not vals[1]: return error(self,"Employee name is required.")
        if vals[5] and ("@" not in vals[5] or "." not in vals[5].split("@")[-1]): return error(self,"Enter a valid email address or leave it blank.")
        try:
            self.db.conn.execute("INSERT INTO employees(employee_code,name,department,designation,phone,email,joining_date,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(*vals,now_text()))
            self.db.conn.commit(); self.db.log("Employee added",vals[1]); self.refresh_all()
        except sqlite3.IntegrityError: error(self,"That employee code already exists.")

    def edit_employee(self):
        eid=self.selected_id(self.emp_table)
        if not eid: return error(self,"Select an employee first.")
        row=self.db.employee(eid); d=EmployeeDialog(self,row)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals[1]: return error(self,"Employee name is required.")
        if vals[5] and ("@" not in vals[5] or "." not in vals[5].split("@")[-1]): return error(self,"Enter a valid email address or leave it blank.")
        try:
            self.db.conn.execute("UPDATE employees SET employee_code=?,name=?,department=?,designation=?,phone=?,email=?,joining_date=?,notes=? WHERE id=?",(*vals,eid))
            self.db.conn.commit(); self.db.log("Employee edited",vals[1]); self.refresh_all()
        except sqlite3.IntegrityError: error(self,"That employee code already exists.")

    def toggle_employee(self):
        eid=self.selected_id(self.emp_table)
        if not eid: return error(self,"Select an employee first.")
        e=self.db.employee(eid); active=0 if e["active"] else 1
        self.db.conn.execute("UPDATE employees SET active=? WHERE id=?",(active,eid)); self.db.conn.commit()
        self.db.log("Employee status changed",f'{e["name"]}: {"Active" if active else "Inactive"}'); self.refresh_all()

    def delete_employee(self):
        eid=self.selected_id(self.emp_table)
        if not eid: return error(self,"Select an employee first.")
        e=self.db.employee(eid)
        if not ask(self,"Delete employee",f'Delete {e["name"]} and permanently remove their tasks and attendance? This cannot be undone. Create a backup first if needed.'): return
        self.db.conn.execute("DELETE FROM tasks WHERE employee_id=?",(eid,))
        self.db.conn.execute("DELETE FROM attendance WHERE employee_id=?",(eid,))
        self.db.conn.execute("DELETE FROM employees WHERE id=?",(eid,)); self.db.conn.commit()
        self.db.log("Employee deleted",e["name"]); self.refresh_all()

    def add_task(self):
        d=TaskDialog(self.db,self)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals: return error(self,"Add an active employee before assigning tasks.")
        if not vals[2]: return error(self,"Task title is required.")
        self.db.conn.execute("""INSERT INTO tasks(employee_id,task_date,title,details,due_time,priority,status,progress,proof_url,proof_note,submitted_at,manager_note)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",vals); self.db.conn.commit(); self.db.log("Task added",vals[2]); self.refresh_all()

    def edit_task(self, table=None):
        table=table or self.task_table
        tid=self.selected_id(table)
        if not tid: return error(self,"Select a task first.")
        row=self.db.conn.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
        d=TaskDialog(self.db,self,row)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals or not vals[2]: return error(self,"Task title and active employee are required.")
        self.db.conn.execute("""UPDATE tasks SET employee_id=?,task_date=?,title=?,details=?,due_time=?,priority=?,status=?,progress=?,proof_url=?,proof_note=?,submitted_at=?,manager_note=? WHERE id=?""",(*vals,tid))
        self.db.conn.commit(); self.db.log("Task edited",vals[2]); self.refresh_all()

    def delete_task(self, table=None):
        table=table or self.task_table
        tid=self.selected_id(table)
        if not tid: return error(self,"Select a task first.")
        if ask(self,"Delete task","Permanently delete the selected task?"):
            self.db.conn.execute("DELETE FROM tasks WHERE id=?",(tid,)); self.db.conn.commit(); self.db.log("Task deleted",str(tid)); self.refresh_all()

    def open_proof(self, table=None):
        table=table or self.task_table
        tid=self.selected_id(table)
        if not tid: return error(self,"Select a task first.")
        row=self.db.conn.execute("SELECT proof_url FROM tasks WHERE id=?",(tid,)).fetchone()
        target=row["proof_url"]
        if not target: return info(self,"No proof link or path has been entered.")
        targets=[line.strip() for line in target.splitlines() if line.strip()]
        if len(targets)>1:
            chosen,ok=QInputDialog.getItem(self,"Open proof","Select a proof link:",targets,0,False)
            if not ok: return
            target=chosen
        else:
            target=targets[0] if targets else target.strip()
        if target.startswith(("http://","https://")): webbrowser.open(target)
        elif os.path.exists(target) and sys.platform=="win32": os.startfile(target)
        elif os.path.exists(target): webbrowser.open(Path(target).resolve().as_uri())
        else: info(self,"Proof path does not exist on this computer.")

    def attendance_selected_employee(self):
        rows=self.att_table.selectionModel().selectedRows()
        if not rows: return None
        item=self.att_table.item(rows[0].row(),0)
        return item.data(Qt.UserRole) if item else None

    def set_attendance_status(self, status):
        eid=self.attendance_selected_employee()
        if not eid: return error(self,"Select an employee row first.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        if self.db.is_holiday(d): return error(self,"This date is declared as a holiday. Remove the holiday declaration before recording attendance.")
        if status in ("Absent", "Leave"):
            self.db.conn.execute("UPDATE attendance SET attendance_status=?,check_in='',check_out='',updated_at=? WHERE employee_id=? AND work_date=?",(status,now_text(),eid,d))
            if not self.db.conn.execute("SELECT 1 FROM attendance WHERE employee_id=? AND work_date=?",(eid,d)).fetchone():
                self.db.upsert_attendance(eid,d,status=status)
        else:
            self.db.upsert_attendance(eid,d,status=status)
        e=self.db.employee(eid)
        self.db.log("Attendance status updated",f"{e['name']}: {status} on {d}")
        self.refresh_all()

    def check_in(self):
        eid=self.attendance_selected_employee()
        if not eid: return error(self, "Select an employee row first.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        if self.db.is_holiday(d): return error(self,"This date is declared as a holiday. Remove the holiday declaration before recording attendance.")
        old=self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?",(eid,d)).fetchone()
        if old and old["check_in"]: return info(self,"Check-in is already recorded. Use the existing record or correct it through the attendance note workflow.")
        self.db.upsert_attendance(eid,d,check_in=datetime.now().strftime("%H:%M"),status="Present")
        self.db.log("Attendance check-in",f"employee={eid}, date={d}"); self.refresh_all()

    def check_out(self):
        eid=self.attendance_selected_employee()
        if not eid: return error(self, "Select an employee row first.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        if self.db.is_holiday(d): return error(self,"This date is declared as a holiday.")
        old=self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?",(eid,d)).fetchone()
        if not old or not old["check_in"]: return error(self,"Record check-in before check-out.")
        if old["check_out"]: return info(self,"Check-out is already recorded.")
        self.db.upsert_attendance(eid,d,check_out=datetime.now().strftime("%H:%M"),status="Present")
        self.db.log("Attendance check-out",f"employee={eid}, date={d}"); self.refresh_all()

    def attendance_note(self):
        eid=self.attendance_selected_employee()
        if not eid: return error(self,"Select an employee row first.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        old=self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?",(eid,d)).fetchone()
        note,ok=QInputDialog.getText(self,"Attendance note","Note / correction reason:",text=old["attendance_note"] if old else "")
        if ok:
            self.db.upsert_attendance(eid,d,note=note)
            self.db.log("Attendance note updated",f"employee={eid}, date={d}, note={note}"); self.refresh_all()

    def declare_holiday(self):
        d=self.att_date.date().toString("yyyy-MM-dd")
        old=self.db.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?",(d,)).fetchone()
        if old: return info(self,f"Holiday already declared: {old['holiday_name'] or 'Holiday'}")
        name,ok=QInputDialog.getText(self,"Declare holiday",f"Holiday name for {d}:")
        if not ok: return
        name=name.strip()
        if not name: return error(self,"Enter a holiday name.")
        if not ask(self,"Confirm holiday",f"Declare {d} as '{name}'? This date will be excluded from working-day counts for all employees."): return
        self.db.conn.execute("INSERT INTO holidays(holiday_date,holiday_name,created_at) VALUES(?,?,?)",(d,name,now_text()))
        self.db.conn.commit(); self.db.log("Holiday declared",f"{d}: {name}"); self.refresh_all()

    def remove_holiday(self):
        d=self.att_date.date().toString("yyyy-MM-dd")
        row=self.db.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?",(d,)).fetchone()
        if not row: return info(self,"No holiday is declared for the selected date.")
        if not ask(self,"Remove holiday",f"Remove holiday '{row['holiday_name']}' on {d}?"): return
        self.db.conn.execute("DELETE FROM holidays WHERE holiday_date=?",(d,)); self.db.conn.commit()
        self.db.log("Holiday removed",d); self.refresh_all()

    def refresh_tasks(self):
        if not hasattr(self,"task_table"): return
        d=self.task_date.date().toString("yyyy-MM-dd"); eid=self.task_filter.currentData()
        rows=self.db.tasks(d,eid)
        self.task_table.setRowCount(0)
        for t in rows:
            r=self.task_table.rowCount(); self.task_table.insertRow(r)
            vals=[t["id"],t["employee_name"],t["title"],t["priority"],t["status"],f'{t["progress"]}%',t["due_time"],t["proof_url"],t["manager_note"]]
            for c,v in enumerate(vals): self.task_table.setItem(r,c,QTableWidgetItem(str(v or "")))
        self.refresh_dashboard()

    def tracking_start_date(self, employee):
        if employee["joining_date"]:
            try: return date.fromisoformat(employee["joining_date"])
            except ValueError: pass
        row=self.db.conn.execute("SELECT MIN(d) AS first_date FROM (SELECT task_date AS d FROM tasks WHERE employee_id=? UNION ALL SELECT work_date AS d FROM attendance WHERE employee_id=?)",(employee["id"],employee["id"])).fetchone()
        if row and row["first_date"]:
            try: return date.fromisoformat(row["first_date"])
            except ValueError: pass
        return date.today()

    def count_working_days(self, start_day, end_day):
        if start_day > end_day: return 0
        weekdays=self.db.working_weekdays()
        holidays={r["holiday_date"] for r in self.db.holidays_between(start_day.isoformat(),end_day.isoformat())}
        total=0; current=start_day
        from datetime import timedelta
        while current <= end_day:
            if current.weekday() in weekdays and current.isoformat() not in holidays: total += 1
            current += timedelta(days=1)
        return total

    def employee_productivity(self, employee):
        start=self.tracking_start_date(employee); today=date.today()
        task_rows=self.db.conn.execute("SELECT progress,status FROM tasks WHERE employee_id=? AND task_date BETWEEN ? AND ?",(employee["id"],start.isoformat(),today.isoformat())).fetchall()
        task_score=(sum(int(t["progress"] or 0) for t in task_rows)/len(task_rows)) if task_rows else None
        att_rows=self.db.conn.execute("SELECT work_date,attendance_status,check_in FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ?",(employee["id"],start.isoformat(),today.isoformat())).fetchall()
        present=sum(1 for a in att_rows if (a["attendance_status"]=="Present" or (a["attendance_status"]=="Unmarked" and a["check_in"])) and not self.db.is_holiday(a["work_date"]))
        eligible=sum(1 for a in att_rows if not self.db.is_holiday(a["work_date"]) and (a["attendance_status"] in ("Present","Absent") or (a["attendance_status"]=="Unmarked" and a["check_in"])))
        attendance_score=(present/eligible*100) if eligible else None
        if task_score is not None and attendance_score is not None: score=round(task_score*0.7+attendance_score*0.3)
        elif task_score is not None: score=round(task_score)
        elif attendance_score is not None: score=round(attendance_score)
        else: score=0
        return {"start":start,"working_days":self.count_working_days(start,today),"present":present,"tasks":len(task_rows),"completed":sum(1 for t in task_rows if t["status"] in ("Completed","Submitted") or int(t["progress"] or 0)>=100),"task_score":task_score,"attendance_score":attendance_score,"score":score}

    def refresh_attendance(self):
        if not hasattr(self,"att_table"): return
        d=self.att_date.date().toString("yyyy-MM-dd")
        holiday=self.db.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?",(d,)).fetchone()
        self.holiday_banner.setText(f"HOLIDAY: {holiday['holiday_name']} — excluded from all working-day counts" if holiday else "No holiday declared for the selected date.")
        rows={a["employee_id"]:a for a in self.db.attendance(d)}
        emps=self.db.employees(False); self.att_table.setRowCount(0)
        for e in emps:
            a=rows.get(e["id"]); r=self.att_table.rowCount(); self.att_table.insertRow(r)
            name=QTableWidgetItem(e["name"]); name.setData(Qt.UserRole,e["id"]); self.att_table.setItem(r,0,name)
            ci=a["check_in"] if a else ""; co=a["check_out"] if a else ""
            status="Holiday" if holiday else (a["attendance_status"] if a else "Unmarked")
            if a and status=="Unmarked" and ci: status="Present"
            hours=""
            if ci and co:
                try:
                    start=datetime.strptime(ci,"%H:%M"); end=datetime.strptime(co,"%H:%M")
                    mins=int((end-start).total_seconds()/60)
                    if mins<0: mins+=1440
                    mins=max(0,mins-int(a["break_minutes"] or 0))
                    hours=f"{mins/60:.2f}"
                except Exception: pass
            vals=[d,status,ci,co,hours,a["attendance_note"] if a else ""]
            for c,v in enumerate(vals,1): self.att_table.setItem(r,c,QTableWidgetItem(str(v or "")))
        self.refresh_attendance_summary()
        self.refresh_dashboard()

    def refresh_attendance_summary(self):
        if not hasattr(self,"attendance_summary_table"): return
        selected=datetime.strptime(self.att_date.date().toString("yyyy-MM-dd"), "%Y-%m-%d").date()
        month_start=selected.replace(day=1)
        from calendar import monthrange
        month_end=selected.replace(day=monthrange(selected.year,selected.month)[1])
        end=min(month_end,date.today())
        self.attendance_summary_table.setRowCount(0)
        for e in self.db.employees(False):
            start=self.tracking_start_date(e)
            effective_start=max(start,month_start)
            working=self.count_working_days(effective_start,end) if effective_start<=end else 0
            month_rows=self.db.conn.execute("SELECT work_date,attendance_status,check_in FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ?",(e["id"],effective_start.isoformat(),end.isoformat())).fetchall() if effective_start<=end else []
            non_holiday_rows=[a for a in month_rows if not self.db.is_holiday(a["work_date"])]
            present=sum(1 for a in non_holiday_rows if a["attendance_status"]=="Present" or (a["attendance_status"]=="Unmarked" and a["check_in"]))
            absent=sum(1 for a in non_holiday_rows if a["attendance_status"]=="Absent")
            leave=sum(1 for a in non_holiday_rows if a["attendance_status"]=="Leave")
            holidays=sum(1 for h in self.db.holidays_between(effective_start.isoformat(),end.isoformat()) if date.fromisoformat(h["holiday_date"]).weekday() in self.db.working_weekdays()) if effective_start<=end else 0
            since_rows=self.db.conn.execute("SELECT work_date,attendance_status,check_in FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ?",(e["id"],start.isoformat(),date.today().isoformat())).fetchall()
            since=sum(1 for a in since_rows if not self.db.is_holiday(a["work_date"]) and (a["attendance_status"]=="Present" or (a["attendance_status"]=="Unmarked" and a["check_in"])))
            vals=[e["name"],start.isoformat(),working,present,absent,leave,holidays,since]
            r=self.attendance_summary_table.rowCount(); self.attendance_summary_table.insertRow(r)
            for c,v in enumerate(vals): self.attendance_summary_table.setItem(r,c,QTableWidgetItem(str(v)))

    def refresh_dashboard(self):
        if not hasattr(self,"kpi_labels"): return
        d=date.today().isoformat()
        active=len(self.db.employees(False)); tasks=self.db.tasks(d)
        completed=sum(1 for t in tasks if t["status"] in ("Completed","Submitted") or int(t["progress"] or 0)>=100)
        pending=sum(1 for t in tasks if t["status"] in ("Not started","In progress","Blocked","Pending review","Pending"))
        missing=sum(1 for t in tasks if not t["proof_url"] and t["status"] in ("Submitted","Completed"))
        for lab,val in zip(self.kpi_labels,[active,len(tasks),completed,pending,missing]): lab.setText(str(val))
        self.dashboard_tasks.setRowCount(0)
        for t in tasks:
            r=self.dashboard_tasks.rowCount(); self.dashboard_tasks.insertRow(r)
            vals=[t["employee_name"],t["title"],t["status"],f'{t["progress"]}%',t["due_time"],"Missing" if not t["proof_url"] else "Provided"]
            for c,v in enumerate(vals): self.dashboard_tasks.setItem(r,c,QTableWidgetItem(str(v or "")))
        metrics=[]
        self.productivity_table.setRowCount(0)
        for e in self.db.employees(False):
            m=self.employee_productivity(e); metrics.append((e["name"],m["score"]))
            vals=[e["name"],m["start"].isoformat(),m["working_days"],m["present"],m["tasks"],m["completed"],f"{m['score']}%"]
            r=self.productivity_table.rowCount(); self.productivity_table.insertRow(r)
            for c,v in enumerate(vals): self.productivity_table.setItem(r,c,QTableWidgetItem(str(v)))
        self.productivity_chart.set_values(metrics)

    def report_data(self, report_date, employee_id=None):
        emps=[self.db.employee(employee_id)] if employee_id else self.db.employees()
        data=[]
        for e in emps:
            if not e: continue
            tasks=self.db.tasks(report_date,e["id"])
            a=self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?",(e["id"],report_date)).fetchone()
            data.append((e,tasks,a))
        return data

    def source_status(self, employee, field, report_date):
        """Use explicitly recorded source audit values for the imported historical date only."""
        if report_date != "2026-10-09":
            return None
        notes = (employee["notes"] or "").lower()
        if field == "work" and ("work: submitted" in notes or "work: submitted in time" in notes):
            return "Submitted (source audit)"
        if field == "late" and "late: no" in notes:
            return "No (source audit)"
        if field == "missing_proof" and ("missing proof: no" in notes or "missing proof: all proofs submitted" in notes):
            return "No (source audit)"
        if field == "links" and ("links: open" in notes or "links open: yes" in notes or "all submitted links reported open" in notes):
            return "Open (source audit; not rechecked)"
        return None

    def employee_missing_proof(self, employee, tasks, report_date):
        source_value = self.source_status(employee, "missing_proof", report_date)
        if source_value:
            return source_value
        return "Yes" if any(t["status"] in ("Submitted", "Completed") and not t["proof_url"] for t in tasks) else "No"

    def task_proof_label(self, employee, task, report_date):
        if task["proof_url"]:
            return task["proof_url"]
        if task["status"] in ("Pending", "Not started", "In progress", "Blocked", "Pending review"):
            return "Not provided (task is pending or in progress)"
        source_missing = self.source_status(employee, "missing_proof", report_date)
        if source_missing and source_missing.startswith("No"):
            return "No direct URL supplied in source; see proof notes / attached EOD evidence."
        if task["status"] in ("Submitted", "Completed"):
            return "MISSING"
        return "Not provided"

    def _report_employees(self, employee_id=None):
        return [self.db.employee(employee_id)] if employee_id else self.db.employees()

    def _attendance_report_rows(self, report_date, employee_id=None):
        rows=[]
        holiday=self.db.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?",(report_date,)).fetchone()
        for e in self._report_employees(employee_id):
            if not e: continue
            a=self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?",(e["id"],report_date)).fetchone()
            status="Holiday" if holiday else (a["attendance_status"] if a else "Unmarked")
            if a and status=="Unmarked" and a["check_in"]: status="Present"
            ci=a["check_in"] if a and a["check_in"] else ""
            co=a["check_out"] if a and a["check_out"] else ""
            net=""
            if ci and co:
                try:
                    st=datetime.strptime(ci,"%H:%M"); en=datetime.strptime(co,"%H:%M")
                    mins=int((en-st).total_seconds()/60)
                    if mins<0: mins+=1440
                    mins=max(0,mins-int(a["break_minutes"] or 0))
                    net=f"{mins/60:.2f}"
                except Exception: pass
            rows.append({"employee":e,"status":status,"check_in":ci,"check_out":co,"net_hours":net,"note":a["attendance_note"] if a else ""})
        return rows

    def _report_title(self, report_type):
        return {"Audit / EOD":"EMPLOYEE AUDIT / END-OF-DAY REPORT", "Employee Attendance":"EMPLOYEE ATTENDANCE REPORT", "Employee Details":"EMPLOYEE DETAILS REGISTER"}.get(report_type,"EMPLOYEE AUDIT / END-OF-DAY REPORT")

    def make_docx(self, path, report_date, employee_id=None, report_type="Audit / EOD"):
        doc=Document(); sec=doc.sections[0]
        sec.top_margin=Inches(.62); sec.bottom_margin=Inches(.58); sec.left_margin=Inches(.68); sec.right_margin=Inches(.68)
        styles=doc.styles; styles["Normal"].font.name="Aptos"; styles["Normal"].font.size=Pt(9); styles["Normal"].paragraph_format.space_after=Pt(4)
        styles["Title"].font.name="Aptos Display"; styles["Title"].font.size=Pt(20); styles["Title"].font.bold=True; styles["Title"].font.color.rgb=RGBColor(31,59,87)
        header=sec.header.paragraphs[0]; header.text="RAW STRENGTH CALISTHENICS  |  EMPLOYEE AUDIT MANAGER"; header.alignment=1
        for r in header.runs: r.font.name="Aptos"; r.font.size=Pt(8); r.font.bold=True; r.font.color.rgb=RGBColor(71,85,105)
        footer=sec.footer.paragraphs[0]; footer.text=f"Confidential internal report  •  Generated {now_text()}"; footer.alignment=1
        for r in footer.runs: r.font.size=Pt(8); r.font.color.rgb=RGBColor(100,116,139)
        title=doc.add_paragraph(style="Title"); title.alignment=1; title.add_run(self._report_title(report_type))
        sub=doc.add_paragraph(); sub.alignment=1; sub.add_run(f"Report date: {report_date}    |    Scope: {self.db.employee(employee_id)['name'] if employee_id and self.db.employee(employee_id) else 'All employees'}").bold=True
        doc.add_paragraph("")
        emps=self._report_employees(employee_id)
        if report_type=="Employee Details":
            tab=doc.add_table(rows=1,cols=8); tab.style="Light Shading Accent 1"
            headers=["Employee ID","Name","Department","Role","Phone","Email","Joining date","Status"]
            for c,v in zip(tab.rows[0].cells,headers): c.text=v
            for e in emps:
                cells=tab.add_row().cells
                vals=[e["employee_code"] or "—",e["name"],e["department"] or "—",e["designation"] or "—",e["phone"] or "—",e["email"] or "—",e["joining_date"] or "—","Active" if e["active"] else "Inactive"]
                for c,v in zip(cells,vals): c.text=str(v)
            doc.add_paragraph(f"Total employees: {len(emps)}")
        elif report_type=="Employee Attendance":
            if self.db.is_holiday(report_date): doc.add_paragraph(f"Declared holiday: {self.db.conn.execute('SELECT holiday_name FROM holidays WHERE holiday_date=?',(report_date,)).fetchone()['holiday_name']}")
            tab=doc.add_table(rows=1,cols=7); tab.style="Light Shading Accent 1"
            headers=["Employee ID","Employee","Status","Check-in","Check-out","Net hours","Remarks"]
            for c,v in zip(tab.rows[0].cells,headers): c.text=v
            rows=self._attendance_report_rows(report_date,employee_id)
            for item in rows:
                e=item["employee"]; cells=tab.add_row().cells
                vals=[e["employee_code"] or "—",e["name"],item["status"],item["check_in"] or "—",item["check_out"] or "—",item["net_hours"] or "—",item["note"] or "—"]
                for c,v in zip(cells,vals): c.text=str(v)
            present=sum(x["status"]=="Present" for x in rows); absent=sum(x["status"]=="Absent" for x in rows); leave=sum(x["status"]=="Leave" for x in rows)
            doc.add_paragraph(f"Summary: Present {present}  |  Absent {absent}  |  Leave {leave}  |  Employees {len(rows)}")
        else:
            data=self.report_data(report_date,employee_id); all_tasks=[t for _,ts,_ in data for t in ts]
            completed=sum(1 for t in all_tasks if t["status"] in ("Completed","Submitted") or int(t["progress"] or 0)>=100)
            pending=sum(1 for t in all_tasks if t["status"] not in ("Completed","Submitted","Cancelled"))
            missing=sum(1 for e,tasks,_ in data if self.employee_missing_proof(e,tasks,report_date).startswith("Yes"))
            tab=doc.add_table(rows=0,cols=4); tab.style="Light Shading Accent 1"
            for vals in [("SUMMARY","COUNT","SUMMARY","COUNT"),("Employees",str(len(data)),"Tasks",str(len(all_tasks))),("Completed / submitted",str(completed),"Pending / other",str(pending)),("Missing proof",str(missing),"Report date",report_date)]:
                cells=tab.add_row().cells
                for c,v in zip(cells,vals): c.text=v
            for e,tasks,a in data:
                doc.add_heading(e["name"],level=1)
                p=doc.add_paragraph(); p.add_run(f'Employee ID: {e["employee_code"] or "—"}   |   Department: {e["department"] or "—"}   |   Role: {e["designation"] or "—"}').bold=True
                p=doc.add_paragraph(f'Phone: {e["phone"] or "—"}   |   Email: {e["email"] or "—"}')
                eod=self.source_status(e,"work",report_date) or ("Submitted" if tasks and all(t["status"] in ("Submitted","Completed") for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                late=self.source_status(e,"late",report_date) or "Review required"; links=self.source_status(e,"links",report_date) or "Not independently checked"
                attendance="Holiday" if self.db.is_holiday(report_date) else (a["attendance_status"] if a else "Unmarked")
                if a and attendance=="Unmarked" and a["check_in"]: attendance="Present"
                doc.add_paragraph(f"WORK / EOD STATUS: {eod}     LATE: {late}     LINKS: {links}")
                doc.add_paragraph(f'ATTENDANCE: {attendance}   |   IN: {a["check_in"] if a and a["check_in"] else "Not recorded"}   |   OUT: {a["check_out"] if a and a["check_out"] else "Not recorded"}')
                prod=self.employee_productivity(e); doc.add_paragraph(f'Productivity score: {prod["score"]}%   |   Working days since tracking start: {prod["working_days"]}   |   Present days recorded: {prod["present"]}')
                doc.add_paragraph(f'MISSING PROOF: {self.employee_missing_proof(e,tasks,report_date)}')
                task_table=doc.add_table(rows=1,cols=4); task_table.style="Light Shading Accent 1"
                for c,v in zip(task_table.rows[0].cells,["Task / Work description","Status / Progress","Proof / Evidence","Manager remarks"]): c.text=v
                for t in tasks:
                    cells=task_table.add_row().cells
                    proof=self.task_proof_label(e,t,report_date)
                    vals=[t["title"]+("\n"+t["details"] if t["details"] else ""),f'{t["status"]} ({t["progress"]}%)'+(f'\nDue: {t["due_time"]}' if t["due_time"] else ""),proof+(f'\n{t["proof_note"]}' if t["proof_note"] else ""),t["manager_note"] or "—"]
                    for c,v in zip(cells,vals): c.text=str(v)
                if not tasks: doc.add_paragraph("No tasks recorded for this date.")
                doc.add_paragraph("PENDING: "+("; ".join(t["title"] for t in tasks if t["status"] not in ("Completed","Submitted","Cancelled")) or "No"))
        doc.save(path)

    def make_pdf(self, path, report_date, employee_id=None, report_type="Audit / EOD"):
        """Create a readable, reference-style PDF using aligned headings and bullets (no tables)."""
        from xml.sax.saxutils import escape
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, HRFlowable
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_regular = resource_path("assets/DejaVuSans.ttf")
        font_bold = resource_path("assets/DejaVuSans-Bold.ttf")
        regular_name, bold_name = "Helvetica", "Helvetica-Bold"
        try:
            if Path(font_regular).exists() and Path(font_bold).exists():
                if "RawStrengthSans" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("RawStrengthSans", font_regular))
                    pdfmetrics.registerFont(TTFont("RawStrengthSans-Bold", font_bold))
                regular_name, bold_name = "RawStrengthSans", "RawStrengthSans-Bold"
        except Exception:
            pass

        navy = colors.HexColor("#102B42")
        cyan = colors.HexColor("#00AEEA")
        muted = colors.HexColor("#526579")
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="RSBrand", fontName=bold_name, fontSize=15, leading=19,
            alignment=TA_CENTER, textColor=navy, spaceAfter=3))
        styles.add(ParagraphStyle(name="RSTitle", fontName=bold_name, fontSize=13, leading=17,
            alignment=TA_CENTER, textColor=cyan, spaceAfter=6))
        styles.add(ParagraphStyle(name="RSSubtitle", fontName=regular_name, fontSize=8.5, leading=12,
            alignment=TA_CENTER, textColor=muted, spaceAfter=12))
        styles.add(ParagraphStyle(name="RSEmployee", fontName=bold_name, fontSize=11, leading=15,
            textColor=navy, spaceBefore=8, spaceAfter=5, keepWithNext=True))
        styles.add(ParagraphStyle(name="RSSection", fontName=bold_name, fontSize=9.2, leading=12,
            textColor=navy, spaceBefore=5, spaceAfter=3, keepWithNext=True))
        styles.add(ParagraphStyle(name="RSBody", fontName=regular_name, fontSize=8.5, leading=12,
            textColor=colors.HexColor("#1F2937"), spaceAfter=3, wordWrap="LTR"))
        styles.add(ParagraphStyle(name="RSBullet", parent=styles["RSBody"], leftIndent=13,
            firstLineIndent=-8, bulletIndent=1, spaceAfter=3))
        styles.add(ParagraphStyle(name="RSMeta", fontName=regular_name, fontSize=8, leading=11,
            textColor=muted, spaceAfter=3))
        styles.add(ParagraphStyle(name="RSLink", fontName=regular_name, fontSize=7.7, leading=10,
            textColor=colors.HexColor("#075E9B"), leftIndent=13, firstLineIndent=-8,
            wordWrap="CJK", spaceAfter=3))

        def clean(value):
            if value is None or str(value).strip() == "":
                return "—"
            return escape(str(value)).replace("\r\n", "\n").replace("\n", "<br/>")

        def para(label, value, style="RSBody"):
            return Paragraph(f"<b>{escape(label)}</b> {clean(value)}", styles[style])

        def bullet(value, style="RSBullet"):
            return Paragraph("&#8226;&nbsp; " + clean(value), styles[style])

        def add_field(story, label, value):
            story.append(para(label, value))

        employee = self.db.employee(employee_id) if employee_id else None
        scope = employee["name"] if employee else "All employees"
        story = [Paragraph("RAW STRENGTH CALISTHENICS", styles["RSBrand"]),
                 Paragraph(escape(self._report_title(report_type)), styles["RSTitle"]),
                 Paragraph(f"Report date: {escape(report_date)} &nbsp;&nbsp; | &nbsp;&nbsp; Scope: {escape(scope)}", styles["RSSubtitle"]),
                 HRFlowable(width="100%", thickness=1.2, color=cyan, spaceAfter=9)]

        if report_type == "Employee Details":
            emps = self._report_employees(employee_id)
            story.append(para("TOTAL EMPLOYEES:", len(emps), "RSSection"))
            for index, e in enumerate(emps, 1):
                block = [Paragraph(f"{index}. {clean(e['name'])}", styles["RSEmployee"]),
                    bullet(f"Employee ID: {e['employee_code'] or '—'}"),
                    bullet(f"Department: {e['department'] or '—'}"),
                    bullet(f"Role / Designation: {e['designation'] or '—'}"),
                    bullet(f"Phone: {e['phone'] or '—'}"),
                    bullet(f"Email: {e['email'] or '—'}"),
                    bullet(f"Joining date: {e['joining_date'] or '—'}"),
                    bullet(f"Status: {'Active' if e['active'] else 'Inactive'}"),
                    Spacer(1, 5), HRFlowable(width="100%", thickness=.35, color=colors.HexColor("#D4DEE7"), spaceAfter=4)]
                story.extend(block)

        elif report_type == "Employee Attendance":
            rows = self._attendance_report_rows(report_date, employee_id)
            holiday = self.db.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?", (report_date,)).fetchone()
            if holiday:
                story.append(para("DECLARED HOLIDAY:", holiday["holiday_name"], "RSSection"))
            present = sum(x["status"] == "Present" for x in rows)
            absent = sum(x["status"] == "Absent" for x in rows)
            leave = sum(x["status"] == "Leave" for x in rows)
            story.append(para("SUMMARY:", f"Employees {len(rows)} | Present {present} | Absent {absent} | Leave {leave}", "RSSection"))
            for index, item in enumerate(rows, 1):
                e = item["employee"]
                block = [Paragraph(f"{index}. {clean(e['name'])}", styles["RSEmployee"]),
                    bullet(f"Employee ID: {e['employee_code'] or '—'}"),
                    bullet(f"Department: {e['department'] or '—'}"),
                    bullet(f"Attendance status: {item['status']}"),
                    bullet(f"Check-in: {item['check_in'] or 'Not recorded'}"),
                    bullet(f"Check-out: {item['check_out'] or 'Not recorded'}"),
                    bullet(f"Net working hours: {item['net_hours'] or 'Not available'}"),
                    bullet(f"Remarks: {item['note'] or '—'}"), Spacer(1, 5),
                    HRFlowable(width="100%", thickness=.35, color=colors.HexColor("#D4DEE7"), spaceAfter=4)]
                story.extend(block)

        else:
            data = self.report_data(report_date, employee_id)
            all_tasks = [t for _, tasks, _ in data for t in tasks]
            completed = sum(1 for t in all_tasks if t["status"] in ("Completed", "Submitted") or int(t["progress"] or 0) >= 100)
            pending = sum(1 for t in all_tasks if t["status"] not in ("Completed", "Submitted", "Cancelled"))
            missing = sum(1 for e, tasks, _ in data if self.employee_missing_proof(e, tasks, report_date).startswith("Yes"))
            story.extend([Paragraph("DAILY SUMMARY", styles["RSSection"]),
                bullet(f"Employees: {len(data)}"), bullet(f"Tasks recorded: {len(all_tasks)}"),
                bullet(f"Completed / submitted tasks: {completed}"), bullet(f"Pending / other tasks: {pending}"),
                bullet(f"Employees flagged for missing proof: {missing}"), Spacer(1, 5),
                HRFlowable(width="100%", thickness=.6, color=cyan, spaceAfter=6)])
            for employee_index, (e, tasks, attendance_row) in enumerate(data):
                if employee_index:
                    story.append(Spacer(1, 6))
                eod = self.source_status(e, "work", report_date) or ("Submitted" if tasks and all(t["status"] in ("Submitted", "Completed") for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                late = self.source_status(e, "late", report_date) or "Review required"
                links = self.source_status(e, "links", report_date) or "Not independently checked"
                attendance = "Holiday" if self.db.is_holiday(report_date) else (attendance_row["attendance_status"] if attendance_row else "Unmarked")
                if attendance_row and attendance == "Unmarked" and attendance_row["check_in"]:
                    attendance = "Present"
                prod = self.employee_productivity(e)
                block = [Paragraph(clean(e["name"]).upper(), styles["RSEmployee"]),
                    bullet(f"Employee ID: {e['employee_code'] or '—'} | Department: {e['department'] or '—'} | Role: {e['designation'] or '—'}"),
                    bullet(f"Phone: {e['phone'] or '—'} | Email: {e['email'] or '—'}"),
                    bullet(f"WORK / EOD STATUS: {eod}"),
                    bullet(f"LATE: {late} | LINKS: {links}"),
                    bullet(f"ATTENDANCE: {attendance} | IN: {attendance_row['check_in'] if attendance_row and attendance_row['check_in'] else 'Not recorded'} | OUT: {attendance_row['check_out'] if attendance_row and attendance_row['check_out'] else 'Not recorded'}"),
                    bullet(f"Productivity score: {prod['score']}% | Working days since tracking start: {prod['working_days']} | Present days recorded: {prod['present']}"),
                    bullet(f"MISSING PROOF: {self.employee_missing_proof(e, tasks, report_date)}"),
                    Paragraph("TASKS / WORK ITEMS", styles["RSSection"])]
                if tasks:
                    for task_index, t in enumerate(tasks, 1):
                        block.append(bullet(f"{task_index}. {t['title']} — Status: {t['status']} — Progress: {t['progress']}%"))
                        if t["details"]:
                            block.append(bullet(f"Details: {t['details']}"))
                        if t["due_time"]:
                            block.append(bullet(f"Due time: {t['due_time']}"))
                        proof_label = self.task_proof_label(e, t, report_date)
                        block.append(bullet(f"Proof / Evidence: {proof_label}"))
                        if t["proof_url"]:
                            block.append(Paragraph("&#8226;&nbsp; " + escape(str(t["proof_url"])), styles["RSLink"]))
                        if t["proof_note"]:
                            block.append(bullet(f"Proof notes: {t['proof_note']}"))
                        block.append(bullet(f"Manager remarks: {t['manager_note'] or '—'}"))
                else:
                    block.append(bullet("No tasks recorded for this date."))
                pending_titles = [t["title"] for t in tasks if t["status"] not in ("Completed", "Submitted", "Cancelled")]
                block.extend([Paragraph("PENDING", styles["RSSection"]), bullet("; ".join(pending_titles) if pending_titles else "No"),
                    Spacer(1, 5), HRFlowable(width="100%", thickness=.4, color=colors.HexColor("#D4DEE7"), spaceAfter=5)])
                story.extend(block)

        def draw_page(canvas, doc_obj):
            canvas.saveState()
            page_width, page_height = A4
            canvas.setStrokeColor(cyan)
            canvas.setLineWidth(.6)
            canvas.line(15*mm, 13*mm, page_width-15*mm, 13*mm)
            canvas.setFont(regular_name, 7)
            canvas.setFillColor(muted)
            canvas.drawString(15*mm, 7.5*mm, "Raw Strength Calisthenics | Confidential internal report")
            canvas.drawRightString(page_width-15*mm, 7.5*mm, f"Page {doc_obj.page}")
            canvas.restoreState()

        document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=17*mm, leftMargin=17*mm,
            topMargin=16*mm, bottomMargin=18*mm, title=self._report_title(report_type),
            author="Raw Strength Calisthenics", subject=f"{report_type} - {report_date}")
        document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)

    def export_report_csv(self, path, report_date, employee_id=None, report_type="Audit / EOD"):
        import csv
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f)
            if report_type=="Employee Details":
                w.writerow(["Employee ID","Name","Department","Role","Phone","Email","Joining date","Status","Notes"])
                for e in self._report_employees(employee_id): w.writerow([e["employee_code"],e["name"],e["department"],e["designation"],e["phone"],e["email"],e["joining_date"],"Active" if e["active"] else "Inactive",e["notes"]])
            elif report_type=="Employee Attendance":
                w.writerow(["Report date","Employee ID","Employee","Department","Status","Check-in","Check-out","Net hours","Remarks"])
                for x in self._attendance_report_rows(report_date,employee_id):
                    e=x["employee"]; w.writerow([report_date,e["employee_code"],e["name"],e["department"],x["status"],x["check_in"],x["check_out"],x["net_hours"],x["note"]])
            else:
                w.writerow(["Report date","Employee ID","Employee","Department","Role","EOD status","Late","Links status","Attendance","Check-in","Check-out","Missing proof","Task","Task details","Task status","Progress %","Due time","Proof URL","Proof notes","Manager remarks","Productivity score"])
                for e,tasks,a in self.report_data(report_date,employee_id):
                    att="Holiday" if self.db.is_holiday(report_date) else (a["attendance_status"] if a else "Unmarked")
                    if a and att=="Unmarked" and a["check_in"]: att="Present"
                    eod=self.source_status(e,"work",report_date) or ("Submitted" if tasks and all(t["status"] in ("Submitted","Completed") for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                    prod=self.employee_productivity(e)
                    if not tasks: w.writerow([report_date,e["employee_code"],e["name"],e["department"],e["designation"],eod,self.source_status(e,"late",report_date) or "Review required",self.source_status(e,"links",report_date) or "Not independently checked",att,a["check_in"] if a else "",a["check_out"] if a else "",self.employee_missing_proof(e,[],report_date),"","","","","","","","",prod["score"]])
                    for t in tasks: w.writerow([report_date,e["employee_code"],e["name"],e["department"],e["designation"],eod,self.source_status(e,"late",report_date) or "Review required",self.source_status(e,"links",report_date) or "Not independently checked",att,a["check_in"] if a else "",a["check_out"] if a else "",self.employee_missing_proof(e,tasks,report_date),t["title"],t["details"],t["status"],t["progress"],t["due_time"],t["proof_url"],t["proof_note"],t["manager_note"],prod["score"]])

    def preview_report(self):
        if not hasattr(self,"report_summary"): return
        d=self.report_date.date().toString("yyyy-MM-dd"); eid=self._effective_report_employee_id(); kind=self.report_type.currentText()
        if kind=="Employee Details":
            emps=self._report_employees(eid); lines=[self._report_title(kind),f"Employees: {len(emps)}","", "\n".join(f'{e["employee_code"] or "—"} | {e["name"]} | {e["department"] or "—"} | {e["designation"] or "—"}' for e in emps)]
            self.report_summary.setPlainText("\n".join(lines))
        elif kind=="Employee Attendance":
            rows=self._attendance_report_rows(d,eid); lines=[self._report_title(kind),f"Date: {d}",""]
            lines += [f'{x["employee"]["name"]} | {x["status"]} | In: {x["check_in"] or "—"} | Out: {x["check_out"] or "—"} | Hours: {x["net_hours"] or "—"}' for x in rows]
            self.report_summary.setPlainText("\n".join(lines))
        else: self.report_summary.setPlainText(self.report_preview_text(d,eid))
        self.db.log("Report previewed",f"type={kind}, date={d}, employee={eid or 'all'}")

    def generate_report(self):
        archived_id = self.archived_report.currentData() if hasattr(self, "archived_report") else None
        if archived_id is not None:
            archived = self.archive_content(archived_id)
            if not archived:
                return error(self, "The selected archived PDF could not be found.")
            path, _ = QFileDialog.getSaveFileName(self, "Export archived PDF", str(EXPORT_DIR / archived["file_name"]), "PDF document (*.pdf)")
            if not path: return
            try:
                Path(path).write_bytes(archived["content"])
                info(self, f"Archived report exported to:\n{path}")
            except Exception as ex:
                error(self, f"Could not export archived PDF:\n{ex}")
            return
        d=self.report_date.date().toString("yyyy-MM-dd"); eid=self._effective_report_employee_id(); fmt=self.report_format.currentText(); kind=self.report_type.currentText()
        ext=".docx" if fmt.startswith("Word") else ".pdf" if fmt.startswith("PDF") else ".csv"
        default=EXPORT_DIR / f"{kind.replace(' / ','_').replace(' ','_')}_{d}{('_Employee_'+str(eid)) if eid else ''}{ext}"
        filters={".docx":"Word document (*.docx)",".pdf":"PDF document (*.pdf)",".csv":"CSV spreadsheet (*.csv)"}
        path,_=QFileDialog.getSaveFileName(self,"Save report",str(default),filters[ext])
        if not path: return
        try:
            if ext==".csv": self.export_report_csv(path,d,eid,kind)
            elif ext==".docx": self.make_docx(path,d,eid,kind)
            else: self.make_pdf(path,d,eid,kind)
            self.preview_report(); self.db.log("Report generated",f"{kind}: {path}"); info(self,f"{kind} report saved:\n{path}")
        except Exception as ex: error(self,f"Could not generate report:\n{ex}")

    def report_preview_text(self,d,eid):
        data=self.report_data(d,eid); lines=[f"RAW STRENGTH CALISTHENICS — EMPLOYEE AUDIT / EOD: {d}",""]
        for e,tasks,a in data:
            status="Holiday" if self.db.is_holiday(d) else (a["attendance_status"] if a else "Unmarked")
            if a and status=="Unmarked" and a["check_in"]: status="Present"
            productivity=self.employee_productivity(e)
            eod=self.source_status(e,"work",d) or ("Submitted" if tasks and all(t["status"] in ("Submitted","Completed") for t in tasks) else "Partial / In progress" if tasks else "No tasks")
            lines.append(f'{e["name"]} | EOD: {eod} | Attendance: {status} | Tasks: {len(tasks)} | Productivity: {productivity["score"]}% | Check-in: {a["check_in"] if a and a["check_in"] else "—"} | Check-out: {a["check_out"] if a and a["check_out"] else "—"}')
            for t in tasks: lines.append(f'  • {t["title"]}: {t["status"]} ({t["progress"]}%) | Proof: {"Yes" if t["proof_url"] else "No"}')
            lines.append(f'  PENDING: {"; ".join(t["title"] for t in tasks if t["status"] not in ("Completed","Submitted","Cancelled")) or "No"}')
        return "\n".join(lines)

    def print_report(self):
        archived_id = self.archived_report.currentData() if hasattr(self, "archived_report") else None
        if archived_id is not None:
            archived = self.archive_content(archived_id)
            if not archived:
                return error(self, "The selected archived PDF could not be found.")
            path = EXPORT_DIR / f"Archived_{archived['id']}_{Path(archived['file_name']).name}"
            try:
                path.write_bytes(archived["content"])
                if sys.platform == "win32": os.startfile(str(path), "print")
                else: info(self, f"Archived PDF prepared for printing:\n{path}")
                self.db.log("Archived EOD sent to print", archived["file_name"])
            except Exception as ex:
                error(self, f"Could not print archived PDF:\n{ex}")
            return
        d=self.report_date.date().toString("yyyy-MM-dd"); eid=self._effective_report_employee_id(); kind=self.report_type.currentText(); fmt=self.report_format.currentText()
        if fmt.startswith("CSV"):
            return info(self,"CSV files are for data export and cannot be sent directly to the print handler. Choose Word or PDF to print, or use Generate / Save to export CSV.")
        ext=".docx" if fmt.startswith("Word") else ".pdf"
        path=EXPORT_DIR/f"Print_{kind.replace(' / ','_').replace(' ','_')}_{d}{('_Employee_'+str(eid)) if eid else ''}{ext}"
        try:
            if ext==".docx": self.make_docx(path,d,eid,kind)
            else: self.make_pdf(path,d,eid,kind)
            if sys.platform=="win32": os.startfile(str(path),"print")
            else: info(self,f"Report created for printing:\n{path}")
            self.db.log("Report sent to print",f"{kind}: {path}")
        except Exception as ex: error(self,f"Could not prepare/print report:\n{ex}")

    def open_export_folder(self):
        if sys.platform=="win32": os.startfile(str(EXPORT_DIR))
        else: webbrowser.open(EXPORT_DIR.as_uri())

    def backup_db(self):
        target=BACKUP_DIR/f"employee_audit_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        try:
            self.db.conn.commit()
            dest=sqlite3.connect(target)
            self.db.conn.backup(dest); dest.close()
            self.db.log("Database backup created",str(target)); info(self,f"Backup created:\n{target}")
        except Exception as ex: error(self,f"Backup failed:\n{ex}")

    def restore_backup(self):
        path,_=QFileDialog.getOpenFileName(self,"Select database backup",str(BACKUP_DIR),"SQLite database (*.db)")
        if not path: return
        if not ask(self,"Restore backup","This replaces current data. A backup of the current database will be created first. Continue?"): return
        try:
            self.backup_db()
            self.db.conn.close()
            shutil.copy2(path,DB_PATH)
            self.db=Database()
            info(self,"Backup restored. Restart the application if any screen does not refresh.")
            self.close()
        except Exception as ex: error(self,f"Restore failed:\n{ex}")

    def save_working_week(self):
        days=[str(i) for i,cb in enumerate(self.workday_checks) if cb.isChecked()]
        if not days: return error(self,"Select at least one working weekday.")
        self.db.set_setting("working_weekdays",",".join(days))
        self.db.log("Working week changed",",".join(days))
        self.refresh_all(); info(self,"Working week saved. Working-day and productivity calculations have been refreshed.")

    def upload_eod_pdfs(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Upload historical EOD PDF files",str(Path.home()),"PDF files (*.pdf)")
        if not paths: return
        emps=self.db.employees()
        options=["Unassigned / All employees"]+[f'{e["name"]} ({e["employee_code"] or e["id"]})' for e in emps]
        selected,ok=QInputDialog.getItem(self,"Associate PDF","Choose the employee for these PDF files:",options,0,False)
        if not ok: return
        employee_id=None
        if options.index(selected)>0: employee_id=emps[options.index(selected)-1]["id"]
        report_date,ok=QInputDialog.getText(self,"EOD report date","Report date (YYYY-MM-DD), or leave blank if unknown:")
        if not ok: return
        report_date=report_date.strip()
        if report_date:
            try: date.fromisoformat(report_date)
            except ValueError: return error(self,"Date must use YYYY-MM-DD, or be left blank.")
        saved=0
        try:
            selected_files=[]
            for file_path in paths:
                path=Path(file_path)
                if path.suffix.lower() != ".pdf": continue
                content=path.read_bytes()
                if not content.startswith(b"%PDF"):
                    return error(self,f"This file does not appear to be a valid PDF: {path.name}")
                selected_files.append((path,content))
            if not selected_files: return info(self,"No PDF files were selected.")
            self.db.conn.execute("BEGIN")
            for path,content in selected_files:
                self.db.conn.execute("INSERT INTO archived_documents(employee_id,report_date,file_name,mime_type,content,notes,uploaded_at) VALUES(?,?,?,?,?,?,?)",
                                      (employee_id,report_date,path.name,"application/pdf",sqlite3.Binary(content),"",now_text()))
                saved+=1
            self.db.conn.commit(); self.db.log("EOD PDF archive uploaded",f"files={saved}, employee={employee_id or 'all'}, date={report_date or 'unknown'}")
            self.refresh_archive(); info(self,f"Saved {saved} PDF file(s) inside the local database.")
        except Exception as ex:
            self.db.conn.rollback(); error(self,f"PDF archive upload failed:\n{ex}")

    def selected_archive_id(self):
        return self.selected_id(self.archive_table)

    def archive_content(self, doc_id):
        return self.db.conn.execute("SELECT * FROM archived_documents WHERE id=?",(doc_id,)).fetchone()

    def open_archived_pdf(self):
        doc_id=self.selected_archive_id()
        if not doc_id: return error(self,"Select a PDF record first.")
        row=self.archive_content(doc_id)
        if not row: return error(self,"The archived PDF was not found.")
        target=APP_DIR/"opened_archived_pdfs"/f"{row['id']}_{Path(row['file_name']).name}"
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(row["content"])
        try:
            if sys.platform=="win32": os.startfile(str(target))
            else: webbrowser.open(target.resolve().as_uri())
        except Exception as ex: error(self,f"Could not open PDF:\n{ex}")

    def export_archived_pdf(self):
        doc_id=self.selected_archive_id()
        if not doc_id: return error(self,"Select a PDF record first.")
        row=self.archive_content(doc_id)
        if not row: return error(self,"The archived PDF was not found.")
        path,_=QFileDialog.getSaveFileName(self,"Export archived PDF",str(EXPORT_DIR/row["file_name"]),"PDF files (*.pdf)")
        if not path: return
        try:
            Path(path).write_bytes(row["content"]); info(self,f"PDF exported to:\n{path}")
        except Exception as ex: error(self,f"Could not export PDF:\n{ex}")

    def delete_archived_pdf(self):
        doc_id=self.selected_archive_id()
        if not doc_id: return error(self,"Select a PDF record first.")
        row=self.archive_content(doc_id)
        if not row: return
        if not ask(self,"Delete archived PDF",f"Permanently delete '{row['file_name']}' from the local database?"): return
        self.db.conn.execute("DELETE FROM archived_documents WHERE id=?",(doc_id,)); self.db.conn.commit()
        self.db.log("EOD PDF deleted",row["file_name"]); self.refresh_archive()

    def refresh_archive(self):
        if not hasattr(self,"archive_table"): return
        self.archive_table.setRowCount(0)
        for d in self.db.archive_documents():
            size=self.db.conn.execute("SELECT length(content) FROM archived_documents WHERE id=?",(d["id"],)).fetchone()[0]
            vals=[d["id"],d["file_name"],d["employee_name"] or "Unassigned / All",d["report_date"] or "Unknown",d["uploaded_at"],d["notes"],f"{(size or 0)/1024:.1f} KB"]
            r=self.archive_table.rowCount(); self.archive_table.insertRow(r)
            for c,v in enumerate(vals): self.archive_table.setItem(r,c,QTableWidgetItem(str(v)))
        self.refresh_archived_report_choices()

    def change_password(self):
        user_id = self.current_user.get("id")
        row = self.db.conn.execute("SELECT * FROM auth_users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return error(self, "Your account could not be found.")
        old, ok = QInputDialog.getText(self, "Change password", "Current password:", QLineEdit.Password)
        if not ok: return
        _, test = hash_pin(old, row["password_salt"])
        if not secrets.compare_digest(test, row["password_hash"]):
            return error(self, "Current password is incorrect.")
        new, ok = QInputDialog.getText(self, "Change password", "New password (8+ characters, letters and numbers):", QLineEdit.Password)
        if not ok: return
        if not password_is_strong(new): return error(self, "Use at least 8 characters, including a letter and a number.")
        confirm, ok = QInputDialog.getText(self, "Change password", "Confirm new password:", QLineEdit.Password)
        if not ok or confirm != new: return error(self, "The passwords do not match.")
        salt, digest = hash_pin(new)
        self.db.conn.execute("UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?", (salt,digest,now_text(),user_id))
        self.db.conn.commit(); self.db.log("Password changed", row["username"])
        info(self, "Your password has been changed.")

    def update_recovery_question(self):
        row = self.db.conn.execute("SELECT * FROM auth_users WHERE id=?", (self.current_user.get("id"),)).fetchone()
        if not row:
            return error(self, "Your account could not be found.")
        current, ok = QInputDialog.getText(self, "Update recovery question", "Confirm your current password:", QLineEdit.Password)
        if not ok: return
        _, digest = hash_pin(current, row["password_salt"])
        if not secrets.compare_digest(digest, row["password_hash"]):
            return error(self, "Current password is incorrect.")
        dialog = QDialog(self); dialog.setWindowTitle("Update recovery question"); dialog.setMinimumWidth(440)
        layout = QFormLayout(dialog)
        question = QComboBox(); question.addItems(SECURITY_QUESTIONS); question.setCurrentText(row["security_question"])
        answer = QLineEdit(); answer.setEchoMode(QLineEdit.Password); answer.setPlaceholderText("New recovery answer")
        confirm = QLineEdit(); confirm.setEchoMode(QLineEdit.Password); confirm.setPlaceholderText("Confirm recovery answer")
        layout.addRow("Recovery question", question); layout.addRow("New answer", answer); layout.addRow("Confirm answer", confirm)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addRow(buttons)
        if dialog.exec() != QDialog.Accepted: return
        a1 = normalized_answer(answer.text()); a2 = normalized_answer(confirm.text())
        if len(a1) < 2: return error(self, "Enter a recovery answer.")
        if a1 != a2: return error(self, "Recovery answers do not match.")
        salt, hashed = hash_pin(a1)
        self.db.conn.execute("UPDATE auth_users SET security_question=?,answer_salt=?,answer_hash=?,updated_at=? WHERE id=?",
                             (question.currentText(), salt, hashed, now_text(), row["id"]))
        self.db.conn.commit(); self.db.log("Recovery question updated", row["username"])
        info(self, "Your password recovery question and answer have been updated.")

    def manage_accounts(self):
        if self.user_role != "Admin":
            return error(self, "Only an Admin account can manage HR/Admin accounts.")
        dialog = QDialog(self); dialog.setWindowTitle("Manage HR / Admin Accounts"); dialog.setMinimumWidth(600)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Create a separate login for HR or Admin. Each user must set their own recovery question and answer."))
        table = QTableWidget(0, 5); table.setHorizontalHeaderLabels(["Username", "Display name", "Role", "Status", "Created"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for row in self.db.conn.execute("SELECT username,display_name,role,active,created_at FROM auth_users ORDER BY username COLLATE NOCASE").fetchall():
            idx=table.rowCount(); table.insertRow(idx)
            for col,val in enumerate([row["username"],row["display_name"],row["role"],"Active" if row["active"] else "Disabled",row["created_at"]]):
                table.setItem(idx,col,QTableWidgetItem(str(val)))
        layout.addWidget(table)
        formbox=QGroupBox("Create account"); form=QFormLayout(formbox)
        username=QLineEdit(); display=QLineEdit(); role=QComboBox(); role.addItems(["HR","Admin"])
        password=QLineEdit(); password.setEchoMode(QLineEdit.Password)
        question=QComboBox(); question.addItems(SECURITY_QUESTIONS)
        answer=QLineEdit(); answer.setEchoMode(QLineEdit.Password)
        form.addRow("Username",username); form.addRow("Display name",display); form.addRow("Role",role)
        form.addRow("Temporary/new password",password); form.addRow("Recovery question",question); form.addRow("Recovery answer",answer)
        layout.addWidget(formbox)
        buttons=QHBoxLayout(); create=QPushButton("Create account"); close=QPushButton("Close")
        buttons.addWidget(create); buttons.addWidget(close); layout.addLayout(buttons)
        close.clicked.connect(dialog.reject)
        def create_account():
            u=username.text().strip(); d=display.text().strip(); pw=password.text(); ans=normalized_answer(answer.text())
            if not u or not d: return error(dialog,"Enter username and display name.")
            if not password_is_strong(pw): return error(dialog,"Password must be 8+ characters with letters and numbers.")
            if len(ans)<2: return error(dialog,"Enter a recovery answer.")
            ps,ph=hash_pin(pw); aus,ah=hash_pin(ans)
            try:
                self.db.conn.execute("INSERT INTO auth_users(username,display_name,role,password_salt,password_hash,security_question,answer_salt,answer_hash,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,1,?,?)",
                    (u,d,role.currentText(),ps,ph,question.currentText(),aus,ah,now_text(),now_text()))
                self.db.conn.commit(); self.db.log("HR/Admin account created",f"{u} ({role.currentText()})")
            except sqlite3.IntegrityError:
                return error(dialog,"That username already exists.")
            info(dialog,"Account created. Share the login details securely with the account owner.")
            dialog.accept()
        create.clicked.connect(create_account)
        dialog.exec()


    def export_employees_csv(self):
        path,_=QFileDialog.getSaveFileName(self,"Export employees",str(EXPORT_DIR/"employees.csv"),"CSV (*.csv)")
        if not path: return
        import csv
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f); w.writerow(["Record ID","Employee ID","Name","Department","Role","Phone","Email","Joining date","Status","Notes"])
            for e in self.db.employees():
                w.writerow([e["id"],e["employee_code"],e["name"],e["department"],e["designation"],e["phone"],e["email"],e["joining_date"],"Active" if e["active"] else "Inactive",e["notes"]])
        info(self,f"Employee list exported:\n{path}")

def resource_path(relative_path):
    """Resolve bundled assets in source and PyInstaller builds."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_path / relative_path)


def main():
    app=QApplication(sys.argv); app.setStyle("Fusion")
    app.setStyleSheet("""
      * { font-family: "Segoe UI"; font-size: 10pt; color: #e6f0ff; }
      QMainWindow { background: #06111f; }
      QWidget { background-color: transparent; }
      QMenuBar { background: #081a2b; border-bottom: 1px solid #183b56; padding: 5px 9px; }
      QMenuBar::item { padding: 8px 12px; border-radius: 6px; background: transparent; }
      QMenuBar::item:selected { background: #123b5c; color: #66d9ff; }
      QMenu { background: #0b1e30; border: 1px solid #24506e; padding: 5px; }
      QMenu::item { padding: 9px 24px; border-radius: 5px; }
      QMenu::item:selected { background: #12476a; color: #ffffff; }
      QTabWidget::pane { border: 1px solid #1c4965; border-radius: 12px; background: #091a2a; top: -1px; }
      QTabWidget { background: transparent; }
      QTabBar { background: transparent; }
      QTabBar::tab { background: #0a2033; color: #b7d3e6; padding: 16px 12px; margin: 3px 5px; border-radius: 9px; font-weight: 700; min-width: 145px; min-height: 24px; text-align: left; }
      QTabBar::tab:selected { background: #07539a; color: #ffffff; border: 1px solid #00c8ff; }
      QTabBar::tab:hover:!selected { background: #123c5a; color: #e9f7ff; }
      QPushButton { padding: 10px 15px; min-height: 20px; border: 1px solid #285574; border-radius: 8px; background: #102b42; color: #e9f6ff; font-weight: 650; }
      QPushButton:hover { background: #164a6b; border-color: #13bdf3; color: #ffffff; }
      QPushButton:pressed { background: #0c3855; }
      QPushButton:disabled { background: #172635; color: #72869a; border-color: #23394b; }
      QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit { background: #071827; color: #e6f0ff; border: 1px solid #28506b; border-radius: 7px; padding: 8px 10px; selection-background-color: #087eae; }
      QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus { border: 1px solid #00b8ff; }
      QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down { border: 0; width: 25px; }
      QComboBox QAbstractItemView { background: #0b2032; color: #e6f0ff; selection-background-color: #155274; border: 1px solid #28506b; }
      QTableWidget { background: #081a2a; alternate-background-color: #0c2235; color: #e6f0ff; border: 1px solid #1d4964; border-radius: 8px; gridline-color: #18364b; selection-background-color: #124e70; selection-color: #ffffff; outline: 0; }
      QTableWidget::item { padding: 8px; border-bottom: 1px solid #122e43; }
      QTableWidget::item:selected { background: #125276; color: #ffffff; }
      QHeaderView::section { background: #102b41; color: #9edfff; padding: 10px 8px; border: none; border-bottom: 1px solid #24506a; font-weight: 700; }
      QGroupBox { font-weight: 700; color: #d8f0ff; border: 1px solid #0876a9; border-radius: 12px; margin-top: 13px; padding: 17px 13px 13px 13px; background: #0a1e2f; }
      QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #6ed8ff; }
      QLabel { background: transparent; color: #e6f0ff; }
      QLabel[h1="true"] { font-size: 22pt; font-weight: 700; color: #f0f8ff; }
      QLabel[pageTitle="true"] { font-size: 20pt; font-weight: 750; color: #f0f8ff; padding: 5px 2px; }
      QProgressBar { border: 1px solid #28506b; border-radius: 5px; text-align: center; color: #f2fbff; background: #10283a; }
      QProgressBar::chunk { background: #00b8a9; border-radius: 4px; }
      QCheckBox { spacing: 7px; padding: 4px; color: #c9deee; }
      QCheckBox::indicator { width: 17px; height: 17px; }
      QRadioButton { spacing: 7px; color: #c9deee; }
      QStatusBar { background: #071827; color: #8caec5; border-top: 1px solid #183b56; }
      QScrollBar:vertical, QScrollBar:horizontal { background: #081a2a; width: 12px; height: 12px; margin: 2px; }
      QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #285574; border-radius: 5px; min-height: 25px; min-width: 25px; }
      QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #1685b5; }
      QDialog { background: #091a2a; }
      QToolTip { background: #102b41; color: #ffffff; border: 1px solid #00a8e8; padding: 5px; }
    """)
    db=Database()
    seed_initial_audit(db)
    if db.conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] == 0:
        setup_dialog = AccountSetupDialog(db)
        if setup_dialog.exec() != QDialog.Accepted:
            return 0
    login=LoginDialog(db)
    if login.exec()!=QDialog.Accepted: return 0
    if db.get_setting("initial_audit_2026_10_09_imported") == "1" and db.get_setting("initial_audit_notice_shown") != "1":
        info(login, "Historical audit imported: 8 employees and 36 task records for 09-10-2026. To review them, select 2026-10-09 in All Tasks, Employee Task Tracker, or Print Center. Today's screens may be empty until you add today's tasks.")
        db.set_setting("initial_audit_notice_shown", "1")
    win=MainWindow(db, login.user); win.show()
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
