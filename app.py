import json, os, subprocess, sys, sqlite3, shutil, webbrowser, hashlib, secrets
from pathlib import Path
from datetime import datetime, date
from urllib.request import Request, urlopen
from PySide6.QtCore import Qt, QDate, QTime, QEasingCurve, QPropertyAnimation, QObject, QThread, Signal, QPoint, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QDateEdit, QTimeEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QInputDialog, QDialog, QDialogButtonBox, QHeaderView,
    QGroupBox, QProgressBar, QAbstractItemView, QCheckBox, QScrollArea, QGraphicsOpacityEffect,
    QToolButton, QMenu, QSizePolicy, QFrame
)
from PySide6.QtGui import QAction, QPainter, QColor, QPen, QFont, QFontDatabase, QIcon, QPixmap
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
from build_info import APP_VERSION
from business_tracking import BusinessTrackingTab

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
    # Ensure tables exist before seeding
    db.setup()
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
            db.conn.execute("""INSERT INTO tasks(employee_id,task_date,title,details,due_time,priority,status,progress,proof_url,proof_note,submitted_at,manager_note,created_at,updated_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (employee_ids[name], SOURCE_DATE_ISO, title, details, "", "Normal", status, progress, proof, note, "", "", now_text(), now_text()))
        db.conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, "1"))
        db.conn.execute("INSERT INTO audit_log(timestamp,action,details) VALUES(?,?,?)",
                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Initial historical audit imported", f"Imported {len(EMPLOYEES)} employees and {len(TASKS)} task records from {SOURCE_FILENAME} ({SOURCE_DATE_DISPLAY})."))
        db.conn.commit()
    except Exception as exc:
        db.conn.rollback()
        raise RuntimeError(f"Initial audit seed failed: {exc}") from exc


APP_NAME = "Raw Strength Calisthenics — Employee Audit Manager"
GITHUB_REPOSITORY = "yalangisexter-ux/audit-report"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
GITHUB_RELEASE_DOWNLOAD_PREFIX = f"https://github.com/{GITHUB_REPOSITORY}/releases/download/"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "EmployeeAuditManager"
DB_PATH = APP_DIR / "employee_audit.db"
BACKUP_DIR = APP_DIR / "backups"
EXPORT_DIR = Path.home() / "Documents" / "EmployeeAuditReports"
APP_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def configure_date_edit(date_edit):
    date_edit.setCalendarPopup(True)


def release_version_tuple(version):
    parts = str(version).strip().removeprefix("v").split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Unsupported application version: {version}")
    return tuple(int(part) for part in parts)


class UpdateWorker(QObject):
    ready = Signal(str, str)
    current = Signal(str)
    failed = Signal(str)
    completed = Signal()

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    @staticmethod
    def request_bytes(url, accept="application/vnd.github+json"):
        request = Request(url, headers={
            "Accept": accept,
            "User-Agent": "RawStrengthEmployeeAuditManager",
        })
        with urlopen(request, timeout=30) as response:
            return response.read()

    def run(self):
        try:
            release = json.loads(self.request_bytes(GITHUB_RELEASES_API).decode("utf-8"))
            latest_version = release.get("tag_name", "")
            latest_parts = release_version_tuple(latest_version)
            if latest_parts <= release_version_tuple(self.current_version):
                self.current.emit(self.current_version)
                return

            assets = {asset.get("name"): asset.get("browser_download_url", "")
                      for asset in release.get("assets", [])}
            installer_name = "RawStrengthEmployeeAuditManager-Setup.exe"
            installer_url = assets.get(installer_name, "")
            if not installer_url.startswith(GITHUB_RELEASE_DOWNLOAD_PREFIX):
                raise ValueError("The latest release is missing a trusted installer.")

            version_text = ".".join(str(part) for part in latest_parts)
            update_dir = APP_DIR / "updates" / version_text
            update_dir.mkdir(parents=True, exist_ok=True)
            installer_path = update_dir / installer_name
            partial_path = update_dir / (installer_name + ".part")
            try:
                request = Request(installer_url, headers={"User-Agent": "RawStrengthEmployeeAuditManager"})
                with urlopen(request, timeout=60) as response, partial_path.open("wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                if partial_path.stat().st_size == 0:
                    raise ValueError("The downloaded installer is empty.")
                os.replace(partial_path, installer_path)
            except Exception:
                partial_path.unlink(missing_ok=True)
                raise

            self.ready.emit(str(installer_path), version_text)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.completed.emit()


def hash_pin(pin, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200_000).hex()
    return salt, digest


def migrate_legacy_task_employee_links(conn):
    """Restore task links only when a unique employee match exists."""
    task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    employee_columns = {row["name"] for row in conn.execute("PRAGMA table_info(employees)").fetchall()}
    if "employee_id" not in task_columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN employee_id INTEGER")
    name_columns = [col for col in ("employee_name", "full_name", "employee", "assigned_to") if col in task_columns]
    has_code = "employee_code" in task_columns and "employee_code" in employee_columns
    task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    rows = conn.execute("""
        SELECT * FROM tasks
        WHERE employee_id IS NULL
           OR NOT EXISTS (SELECT 1 FROM employees WHERE employees.id = tasks.employee_id)
    """).fetchall()
    for task in rows:
        matches = []
        if has_code:
            code = str(task["employee_code"] or "").strip()
            if code:
                matches = conn.execute("""
                    SELECT id FROM employees
                    WHERE LOWER(TRIM(COALESCE(employee_code, ''))) = LOWER(?)
                """, (code,)).fetchall()
        if not matches:
            for column in name_columns:
                value = str(task[column] or "").strip()
                if not value:
                    continue
                candidates = conn.execute("""
                    SELECT id FROM employees
                    WHERE LOWER(TRIM(COALESCE(name, ''))) = LOWER(?)
                """, (value,)).fetchall()
                if len(candidates) == 1:
                    matches = candidates
                    break
        if len(matches) == 1:
            conn.execute("UPDATE tasks SET employee_id = ? WHERE id = ?", (matches[0]["id"], task["id"]))
    conn.commit()


class Database:
    def __init__(self):
        try:
            # Backup existing database before migrations if it has data
            db_path = Path(DB_PATH) if not isinstance(DB_PATH, Path) else DB_PATH
            if db_path.exists() and db_path.stat().st_size > 0:
                BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pre_backup = BACKUP_DIR / f"pre_upgrade_{stamp}.db"
                try:
                    shutil.copy2(db_path, pre_backup)
                except Exception as backup_err:
                    print(f"Pre-upgrade backup failed: {backup_err}")
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.setup()
        except Exception as exc:
            # Attempt to close and re-raise with context
            if hasattr(self, "conn") and self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
            raise RuntimeError(f"Database initialization failed: {exc}") from exc

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
        # Additive migrations only — never drop existing data.
        employee_columns = {r["name"] for r in c.execute("PRAGMA table_info(employees)").fetchall()}
        employee_migrations = (
            ("employee_code", "TEXT"),
            ("name", "TEXT NOT NULL DEFAULT ''"),
            ("department", "TEXT DEFAULT ''"),
            ("designation", "TEXT DEFAULT ''"),
            ("phone", "TEXT DEFAULT ''"),
            ("email", "TEXT DEFAULT ''"),
            ("joining_date", "TEXT DEFAULT ''"),
            ("active", "INTEGER DEFAULT 1"),
            ("notes", "TEXT DEFAULT ''"),
            ("created_at", "TEXT NOT NULL DEFAULT ''"),
        )
        for column, declaration in employee_migrations:
            if column not in employee_columns:
                c.execute(f"ALTER TABLE employees ADD COLUMN {column} {declaration}")
        # Re-read columns after adding any missing columns.
        employee_columns = {row["name"] for row in c.execute("PRAGMA table_info(employees)").fetchall()}
        # Preserve employee names from older database schemas.
        if "employee_name" in employee_columns:
            c.execute("""
                UPDATE employees
                SET name = employee_name
                WHERE COALESCE(name, '') = ''
                  AND COALESCE(employee_name, '') <> ''
            """)
        if "full_name" in employee_columns:
            c.execute("""
                UPDATE employees
                SET name = full_name
                WHERE COALESCE(name, '') = ''
                  AND COALESCE(full_name, '') <> ''
            """)

        task_columns = {r["name"] for r in c.execute("PRAGMA table_info(tasks)").fetchall()}
        task_migrations = (
            ("employee_id", "INTEGER"),
            ("task_date", "TEXT NOT NULL DEFAULT ''"),
            ("title", "TEXT NOT NULL DEFAULT ''"),
            ("details", "TEXT DEFAULT ''"),
            ("due_time", "TEXT DEFAULT ''"),
            ("priority", "TEXT DEFAULT 'Normal'"),
            ("status", "TEXT DEFAULT 'Not started'"),
            ("progress", "INTEGER DEFAULT 0"),
            ("proof_url", "TEXT DEFAULT ''"),
            ("proof_note", "TEXT DEFAULT ''"),
            ("submitted_at", "TEXT DEFAULT ''"),
            ("manager_note", "TEXT DEFAULT ''"),
            ("created_at", "TEXT NOT NULL DEFAULT ''"),
            ("updated_at", "TEXT NOT NULL DEFAULT ''"),
        )
        for column, declaration in task_migrations:
            if column not in task_columns:
                c.execute(f"ALTER TABLE tasks ADD COLUMN {column} {declaration}")

        attendance_columns = {r["name"] for r in c.execute("PRAGMA table_info(attendance)").fetchall()}

        # Additive compatibility migration for attendance tables created by older
        # versions. Keep existing rows and recover dates from a legacy date column.
        if "work_date" not in attendance_columns:
            c.execute("ALTER TABLE attendance ADD COLUMN work_date TEXT NOT NULL DEFAULT ''")
            legacy_date_column = next(
                (name for name in ("attendance_date", "date", "record_date")
                 if name in attendance_columns),
                None,
            )
            if legacy_date_column:
                # The column name comes only from the fixed allow-list above.
                c.execute(
                    f"UPDATE attendance SET work_date = CAST({legacy_date_column} AS TEXT) "
                    "WHERE COALESCE(work_date, '') = '' "
                    f"AND COALESCE(CAST({legacy_date_column} AS TEXT), '') <> ''"
                )
            attendance_columns.add("work_date")

        # Ensure columns used by the current attendance screen and reports exist.
        attendance_migrations = (
            ("check_in", "TEXT DEFAULT ''"),
            ("check_out", "TEXT DEFAULT ''"),
            ("break_minutes", "INTEGER DEFAULT 0"),
            ("attendance_status", "TEXT DEFAULT 'Unmarked'"),
            ("attendance_note", "TEXT DEFAULT ''"),
            ("updated_at", "TEXT NOT NULL DEFAULT ''"),
        )
        for column, declaration in attendance_migrations:
            if column not in attendance_columns:
                c.execute(f"ALTER TABLE attendance ADD COLUMN {column} {declaration}")
                attendance_columns.add(column)

        c.execute(
            "UPDATE attendance SET attendance_status='Present' "
            "WHERE COALESCE(check_in, '') <> '' "
            "AND COALESCE(attendance_status, 'Unmarked') = 'Unmarked'"
        )
        if not self.get_setting("working_weekdays"):
            self.set_setting("working_weekdays", "0,1,2,3,4")
        # Restore task-employee links only when unambiguous
        try:
            migrate_legacy_task_employee_links(self.conn)
        except Exception:
            self.conn.rollback()
            raise
        # Do not create a known/default credential. Authentication is handled by
        # the first-run Admin account and per-user password/recovery records.
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
        title.setProperty("pageTitle", True)
        layout.addWidget(title)
        intro = QLabel("Create the first Admin account to enable sign-in.")
        intro.setProperty("pageSubtitle", True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.username = QLineEdit("admin")
        self.display_name = QLineEdit("Administrator")
        pw_container = password_field("At least 8 characters, including a number")
        self.password = pw_container.field
        confirm_container = password_field("Confirm password")
        self.confirm = confirm_container.field
        self.question = QComboBox(); self.question.addItems(SECURITY_QUESTIONS)
        self.answer = QLineEdit(); self.answer.setEchoMode(QLineEdit.Password); self.answer.setPlaceholderText("Recovery answer (remember it exactly)")
        form.addRow("Admin username", self.username)
        form.addRow("Display name", self.display_name)
        form.addRow("New password", pw_container)
        form.addRow("Confirm password", confirm_container)
        form.addRow("Password recovery question", self.question)
        form.addRow("Recovery answer", self.answer)
        layout.addLayout(form)
        note = QLabel("Your recovery answer is stored as a salted hash. Choose an answer you can remember.")
        note.setWordWrap(True); note.setProperty("mutedText", True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save)
        buttons.accepted.connect(self.create_admin)
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


def password_field(placeholder="Enter password"):
    """Create a password field with a show/hide toggle button."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    field = QLineEdit()
    field.setEchoMode(QLineEdit.Password)
    field.setPlaceholderText(placeholder)
    toggle = QPushButton("Show")
    toggle.setFixedWidth(60)
    toggle.setCheckable(True)
    toggle.setStyleSheet("QPushButton { font-size: 11px; padding: 2px 4px; }")
    def on_toggle(checked):
        field.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        toggle.setText("Hide" if checked else "Show")
    toggle.toggled.connect(on_toggle)
    layout.addWidget(field, 1)
    layout.addWidget(toggle)
    container.field = field  # expose the line edit
    return container


class LoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.user = None
        self.setWindowTitle("HR / Admin Sign In")
        self.setMinimumWidth(420)
        self.setModal(True)
        self.setObjectName("loginDialog")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Logo
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(QIcon(resource_path("assets/raw_strength_icon.ico")).pixmap(72, 72))
        layout.addWidget(logo)

        title = QLabel("Raw Strength Calisthenics")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        title.setProperty("pageTitle", True)
        layout.addWidget(title)
        subtitle = QLabel("HR / Admin workspace • Offline and secure")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setProperty("pageSubtitle", True)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter username")
        self.username.setMinimumHeight(36)
        pw_container = password_field("Enter password")
        self.password = pw_container.field
        self.password.setMinimumHeight(36)
        form.addRow("Username", self.username)
        form.addRow("Password", pw_container)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.check)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        links = QHBoxLayout()
        links.setSpacing(16)
        forgot = QPushButton("Forgot password?")
        forgot.setFlat(True)
        forgot.setToolTip("Reset password using recovery question")
        forgot.clicked.connect(self.forgot_password)
        change = QPushButton("Change password")
        change.setFlat(True)
        change.setToolTip("Change password for an existing account")
        change.clicked.connect(self.change_password)
        links.addStretch(1)
        links.addWidget(forgot)
        links.addWidget(change)
        links.addStretch(1)
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
        self.join=QDateEdit(); configure_date_edit(self.join); self.join.setDisplayFormat("yyyy-MM-dd")
        self.join.setDate(QDate.fromString(row["joining_date"], "yyyy-MM-dd") if row and row["joining_date"] else QDate.currentDate())
        self.join_known=QCheckBox("Joining date is known")
        self.join_known.setChecked(bool(not row or row["joining_date"]))
        self.join.setEnabled(self.join_known.isChecked())
        self.join_known.toggled.connect(self.join.setEnabled)
        self.notes=QTextEdit(row["notes"] if row else ""); self.notes.setMaximumHeight(75)
        self.layout.addRow("Employee ID", self.code); self.layout.addRow("Full name *", self.name)
        self.layout.addRow("Department", self.department); self.layout.addRow("Job title", self.designation)
        self.layout.addRow("Phone number (optional)", self.phone); self.layout.addRow("Email address (optional)", self.email)
        self.layout.addRow("Joining date", self.join); self.layout.addRow("", self.join_known); self.layout.addRow("Notes", self.notes)
        buttons=QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); self.layout.addRow(buttons)
    def values(self):
        return (self.code.text().strip() or None, self.name.text().strip(), self.department.text().strip(),
                self.designation.text().strip(), self.phone.text().strip(), self.email.text().strip(),
                self.join.date().toString("yyyy-MM-dd") if self.join_known.isChecked() else "", self.notes.toPlainText().strip())

class TaskDialog(QDialog):
    STATUSES=[
        ("Not started", "Not started"),
        ("In progress", "In progress"),
        ("Submitted", "Submitted"),
        ("Completed", "Completed"),
        ("Blocked", "Blocked"),
        ("Pending review", "Pending review"),
        ("Pending", "Pending"),
        ("Cancelled", "Cancelled"),
    ]
    def __init__(self, db, parent=None, row=None, employee_id=None):
        super().__init__(parent); self.setWindowTitle("Task details"); self.setMinimumWidth(520)
        self.layout=QFormLayout(self); self.db=db; self.row=row
        self.employee=QComboBox()
        for e in db.employees(False): self.employee.addItem(f'{e["name"]} ({e["employee_code"] or e["id"]})', e["id"])
        if employee_id is not None:
            idx=self.employee.findData(employee_id)
            if idx >= 0: self.employee.setCurrentIndex(idx)
        self.date=QDateEdit(); configure_date_edit(self.date); self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setDate(QDate.fromString(row["task_date"],"yyyy-MM-dd") if row else QDate.currentDate())
        self.title=QLineEdit(row["title"] if row else "")
        self.details=QTextEdit(row["details"] if row else ""); self.details.setMaximumHeight(70)
        self.due=QTimeEdit(); self.due.setDisplayFormat("HH:mm"); self.due.setTime(QTime.fromString(row["due_time"],"HH:mm") if row and row["due_time"] else QTime(17,0))
        self.priority=QComboBox(); self.priority.addItems(["Low","Normal","High","Urgent"])
        self.status=QComboBox()
        for label, value in self.STATUSES: self.status.addItem(label, value)
        self.progress=QSpinBox(); self.progress.setRange(0,100); self.progress.setSuffix("%")
        self.proof=QTextEdit(row["proof_url"] if row else ""); self.proof.setPlaceholderText("Optional URL or local file path. Use one proof link per line."); self.proof.setMaximumHeight(78)
        self.proof_note=QLineEdit(row["proof_note"] if row else "")
        self.manager_note=QLineEdit(row["manager_note"] if row else "")
        if row:
            idx=self.employee.findData(row["employee_id"])
            if idx>=0: self.employee.setCurrentIndex(idx)
            self.priority.setCurrentText(row["priority"])
            status_index=self.status.findData(row["status"])
            if status_index < 0:
                self.status.addItem(row["status"], row["status"])
                status_index=self.status.count()-1
            self.status.setCurrentIndex(status_index); self.progress.setValue(row["progress"])
        self.layout.addRow("Employee *", self.employee); self.layout.addRow("Task date", self.date)
        self.layout.addRow("Task title *", self.title); self.layout.addRow("Description", self.details)
        self.layout.addRow("Due time", self.due); self.layout.addRow("Priority", self.priority)
        self.layout.addRow("Status", self.status); self.layout.addRow("Progress", self.progress)
        self.layout.addRow("Evidence link or file", self.proof); self.layout.addRow("Evidence notes", self.proof_note)
        self.layout.addRow("Manager notes", self.manager_note)
        buttons=QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); self.layout.addRow(buttons)
    def values(self):
        if self.employee.count()==0: return None
        status=self.status.currentData(); progress=self.progress.value()
        if status=="Completed": progress=100
        # Preserve original submission time; only set it on first transition to Submitted/Completed
        if status in ("Submitted","Completed"):
            existing = (self.row["submitted_at"] if self.row else "") or ""
            submitted = existing if existing else now_text()
        else:
            submitted = (self.row["submitted_at"] if self.row else "") or ""
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



class AnimatedBackground(QWidget):
    """Animated particle background (bubbles or stars)."""
    def __init__(self, parent=None, mode="bubbles"):
        super().__init__(parent)
        self.mode = mode
        self.particles = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(40)
        self.init_particles()

    def init_particles(self):
        import random
        w, h = max(self.width(), 800), max(self.height(), 600)
        self.particles = []
        for _ in range(30):
            self.particles.append({
                "x": random.randint(0, w),
                "y": random.randint(0, h),
                "r": random.randint(4, 12),
                "speed": random.uniform(0.3, 1.2),
                "opacity": random.uniform(0.15, 0.45),
            })

    def update_particles(self):
        for p in self.particles:
            p["y"] -= p["speed"]
            if p["y"] < -20:
                p["y"] = self.height() + 10
                p["x"] = __import__("random").randint(0, self.width())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for p in self.particles:
            color = QColor(124, 92, 252, int(p["opacity"] * 255)) if self.mode == "bubbles" else QColor(255, 255, 255, int(p["opacity"] * 200))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(p["x"]), int(p["y"]), p["r"], p["r"])
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self, db, user):
        super().__init__(); self.db=db; self.current_user=user; self.user_role=user.get("role", "HR")
        self.setWindowTitle(APP_NAME); self.setWindowIcon(QIcon(resource_path("assets/raw_strength_icon.ico")))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available:
            self.setMinimumSize(min(1080, available.width()), min(700, available.height()))
            self.resize(min(1380, available.width()), min(860, available.height()))
            self.move(available.center() - self.rect().center())
        else:
            self.resize(1380, 860); self.setMinimumSize(1080, 700)
        self._drag_pos = None

        # Custom title bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(42)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 12, 0)
        title_layout.setSpacing(8)

        title_icon = QLabel()
        title_icon.setPixmap(QIcon(resource_path("assets/raw_strength_icon.ico")).pixmap(18, 18))
        title_layout.addWidget(title_icon)
        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setMinimumWidth(0)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)

        btn_style = "QPushButton { background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 11pt; font-weight: 700; min-width: 0; max-width: 32px; padding: 0; margin: 0; } QPushButton:hover { background: #E2E8F0; color: #0F172A; }"
        close_style = "QPushButton { background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 11pt; font-weight: 700; min-width: 0; max-width: 32px; padding: 0; margin: 0; } QPushButton:hover { background: #FEE2E2; color: #DC2626; }"

        self.btn_min = QPushButton("—")
        self.btn_min.setObjectName("titleBtnMin")
        self.btn_min.setFixedSize(36, 28)
        self.btn_min.setStyleSheet(btn_style)
        self.btn_min.setToolTip("Minimize"); self.btn_min.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.btn_min)

        self.btn_max = QPushButton("□")
        self.btn_max.setObjectName("titleBtnMax")
        self.btn_max.setFixedSize(36, 28)
        self.btn_max.setStyleSheet(btn_style)
        self.btn_max.setToolTip("Maximize / Restore"); self.btn_max.clicked.connect(self.toggle_maximize)
        title_layout.addWidget(self.btn_max)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("titleBtnClose")
        self.btn_close.setFixedSize(36, 28)
        self.btn_close.setStyleSheet(close_style)
        self.btn_close.setToolTip("Close"); self.btn_close.clicked.connect(self.close)
        title_layout.addWidget(self.btn_close)

        # Animated background
        self.bg_anim = AnimatedBackground(mode="bubbles")
        self.bg_anim.setObjectName("animatedBg")

        # Central content
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.title_bar)
        self.title_bar.raise_()

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(False)
        self.tabs.setDocumentMode(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setExpanding(False)
        central_layout.addWidget(self.tabs)
        self.setCentralWidget(central)
        # Resize background with window
        self.bg_anim.setParent(central)
        self.bg_anim.lower()
        self.bg_anim.setGeometry(0, 42, self.width(), self.height() - 42)

        self.home_tab=QWidget(); self.dashboard=QWidget(); self.employees_tab=QWidget(); self.tasks_tab=QWidget(); self.tracker_tab=QWidget(); self.attendance_tab=QWidget(); self.reports_tab=QWidget(); self.archive_tab=QWidget(); self.settings_tab=QWidget()
        self.business_tab = BusinessTrackingTab(self.db)
        for widget,title in [(self.home_tab,"Home"),(self.dashboard,"Dashboard"),(self.employees_tab,"Employees"),(self.tasks_tab,"Task Manager"),(self.tracker_tab,"Employee Tracker"),(self.attendance_tab,"Attendance"),(self.reports_tab,"Print Center"),(self.archive_tab,"EOD Archive"),(self.business_tab,"Business Tracking"),(self.settings_tab,"Settings && Backup")]:
            self.tabs.addTab(widget,title)
        self._tab_animation = None
        self._animated_page = None
        self.tabs.currentChanged.connect(self.animate_tab_transition)
        self.build_home(); self.build_dashboard(); self.build_employees(); self.build_tasks(); self.build_tracker(); self.build_attendance(); self.build_reports(); self.build_archive(); self.build_settings()
        self.polish_tables()
        self.statusBar().showMessage(f"  Signed in: {user.get('display_name') or user.get('username')}  •  Role: {self.user_role}  •  Local database (offline)  •  Raw Strength Calisthenics")
        self.refresh_all()
        # Hide native menu bar (frameless window)
        self.menuBar().hide()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("□")
        else:
            self.showMaximized()
            self.btn_max.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 36:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "bg_anim"):
            self.bg_anim.setGeometry(0, 42, self.width(), self.height() - 42)
            self.bg_anim.init_particles()
        if hasattr(self, "title_label"):
            QTimer.singleShot(0, self.update_title_label)

    def update_title_label(self):
        self.title_label.setText(self.title_label.fontMetrics().elidedText(
            APP_NAME, Qt.TextElideMode.ElideRight, self.title_label.width()))

    def animate_tab_transition(self, index):
        page = self.tabs.widget(index)
        if page is None:
            return
        if self._tab_animation:
            self._tab_animation.stop()
        if self._animated_page:
            self._animated_page.setGraphicsEffect(None)
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(120)
        animation.setStartValue(0.9)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: page.setGraphicsEffect(None) if page.graphicsEffect() is effect else None)
        self._animated_page = page
        self._tab_animation = animation
        animation.start()

    def _wrap_page_in_scroll(self, page_widget, content_layout, page_title=None, page_subtitle="", fixed_header=None):
        """Helper: put page content inside a scroll area so every section has a scrollbar."""
        outer = QVBoxLayout(page_widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        if page_title:
            self._add_fixed_page_header(outer, page_title, page_subtitle)
        elif fixed_header is not None:
            outer.addWidget(fixed_header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("pageContent")
        content_layout.setContentsMargins(20, 0 if page_title else 16, 20, 16)
        content_layout.setSpacing(12)
        content.setLayout(content_layout)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return outer

    def _add_fixed_page_header(self, outer_layout, title, subtitle):
        header = QWidget()
        header.setObjectName("pageHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 0)
        header_layout.setSpacing(0)
        self.add_page_header(header_layout, title, subtitle)
        outer_layout.addWidget(header)

    @staticmethod
    def add_page_header(layout, title, subtitle):
        header_row = QHBoxLayout()
        header_row.setSpacing(14)
        header_row.setContentsMargins(0, 4, 0, 8)
        logo = QLabel()
        logo.setFixedSize(48, 48)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(QIcon(resource_path("assets/raw_strength_icon.ico")).pixmap(40, 40))
        header_row.addWidget(logo)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_label = QLabel(title)
        title_label.setProperty("pageTitle", True)
        title_label.setWordWrap(True)
        text_col.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setProperty("pageSubtitle", True)
            subtitle_label.setWordWrap(True)
            text_col.addWidget(subtitle_label)
        header_row.addLayout(text_col, 1)
        layout.addLayout(header_row)

    def current_theme(self):
        return self.db.get_setting("ui_theme", "day") or "day"

    def apply_theme(self, theme_name=None):
        theme_name = theme_name or self.current_theme()
        theme_name = apply_app_theme(QApplication.instance(), theme_name)
        self.db.set_setting("ui_theme", theme_name)
        # Force style refresh
        QApplication.instance().style().unpolish(self)
        QApplication.instance().style().polish(self)
        if hasattr(self, "theme_toggle_btn"):
            self.theme_toggle_btn.setText("Switch to Night mode" if theme_name == "day" else "Switch to Day mode")
        # Reapply title button styles so they stay visible after theme change
        if hasattr(self, "btn_min"):
            btn_style = "QPushButton { background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 11pt; font-weight: 700; min-width: 0; max-width: 32px; padding: 0; margin: 0; } QPushButton:hover { background: #E2E8F0; color: #0F172A; }"
            close_style = "QPushButton { background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 11pt; font-weight: 700; min-width: 0; max-width: 32px; padding: 0; margin: 0; } QPushButton:hover { background: #FEE2E2; color: #DC2626; }"
            self.btn_min.setStyleSheet(btn_style)
            self.btn_max.setStyleSheet(btn_style)
            self.btn_close.setStyleSheet(close_style)
        return theme_name

    def toggle_theme(self):
        nxt = "night" if self.current_theme() == "day" else "day"
        self.apply_theme(nxt)

    def build_home(self):

        page_layout = QVBoxLayout(self.home_tab)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        self.home_scroll = QScrollArea()
        self.home_scroll.setWidgetResizable(True)
        self.home_scroll.setObjectName("homeScroll")
        content = QWidget()
        content.setObjectName("homeContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26, 22, 26, 22)
        content_layout.setSpacing(18)

        welcome = QWidget()
        welcome.setObjectName("welcomeHero")
        welcome_layout = QHBoxLayout(welcome)
        welcome_layout.setContentsMargins(22, 18, 22, 18)
        welcome_layout.setSpacing(18)
        brand_mark = QLabel()
        brand_mark.setObjectName("welcomeMark")
        brand_mark.setFixedSize(80, 80)
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setPixmap(QIcon(resource_path("assets/raw_strength_icon.ico")).pixmap(72, 72))
        welcome_layout.addWidget(brand_mark)
        welcome_copy = QVBoxLayout()
        welcome_title = QLabel(f"Welcome, {self.current_user.get('display_name') or self.current_user.get('username')}")
        welcome_title.setProperty("welcomeTitle", True)
        welcome_copy.addWidget(welcome_title)
        welcome_subtitle = QLabel("Raw Strength Calisthenics · Employee Audit Manager")
        welcome_subtitle.setProperty("welcomeSubtitle", True)
        welcome_copy.addWidget(welcome_subtitle)
        welcome_layout.addLayout(welcome_copy, 1)

        session_strip = QWidget()
        session_strip.setObjectName("sessionStrip")
        session_layout = QHBoxLayout(session_strip)
        session_layout.setContentsMargins(14, 9, 14, 9)
        session_layout.setSpacing(8)
        session_label = QLabel("SIGNED IN")
        session_label.setProperty("sessionLabel", True)
        session_layout.addWidget(session_label)
        session_layout.addWidget(QLabel(self.current_user.get("username", "N/A")))
        role_label = QLabel(self.user_role)
        role_label.setProperty("roleBadge", True)
        session_layout.addWidget(role_label)
        session_layout.addStretch(1)
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setProperty("mutedText", True)
        session_layout.addWidget(version_label)
        self.update_button = QPushButton("Update application")
        self.update_button.setToolTip("Check GitHub for the latest application installer")
        self.update_button.clicked.connect(self.check_for_updates)
        session_layout.addWidget(self.update_button)
        self.theme_toggle_btn = QPushButton("Switch to Night mode")
        self.theme_toggle_btn.setToolTip("Toggle day / night appearance")
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        session_layout.addWidget(self.theme_toggle_btn)
        session_layout.addWidget(QLabel("Local database · Offline"))
        content_layout.addWidget(session_strip)

        guide_heading = QLabel("Workspace guide")
        guide_heading.setProperty("sectionHeading", True)
        content_layout.addWidget(guide_heading)
        guide_grid = QGridLayout()
        guide_grid.setContentsMargins(0, 0, 0, 0)
        guide_grid.setHorizontalSpacing(12)
        guide_grid.setVerticalSpacing(10)
        guide_items = [
            ("Dashboard", "Review today's totals, recent tasks, and employee productivity.", "Open a feature page from the top navigation to manage records."),
            ("Employees", "Add or edit employee identity, department, job title, and optional contact details.", "Example: Operations · Coordinator · phone and email optional."),
            ("Task Manager", "Choose a date or employee, then add, edit, or remove tasks and update evidence, status, or progress.", "Example: Prepare daily report · In progress · 60%."),
            ("Employee Tracker", "Choose an employee and date, then select Refresh to review their tasks.", "Use Task Manager for changes; this page is read-only."),
            ("Attendance", "Select a date to record present, absent, or leave; add check-in/out times and manage holidays.", "Example: Present · 09:00 check-in · 17:30 check-out."),
            ("Print Center", "Select a report type, date, scope, employee, and PDF, Word, or CSV format.", "For Audit / EOD, use the section checkboxes to control included details."),
            ("EOD Archive", "Upload historical PDFs, associate employee/date, then view, export, refresh, or remove archived files.", "Archived documents stay in the local database and its backups."),
            ("Settings & Backup", "Set working days, create or restore backups, manage account security, and export employees.", "Create a backup before restoring data or replacing a production build."),
        ]
        for index, (section, guidance, example) in enumerate(guide_items):
            guide_card = QWidget()
            guide_card.setObjectName("guideItem")
            card_layout = QVBoxLayout(guide_card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(6)
            section_label = QLabel(section)
            section_label.setProperty("guideTitle", True)
            card_layout.addWidget(section_label)
            guidance_label = QLabel(guidance)
            guidance_label.setWordWrap(True)
            card_layout.addWidget(guidance_label)
            example_label = QLabel(example)
            example_label.setWordWrap(True)
            example_label.setProperty("mutedText", True)
            card_layout.addWidget(example_label)
            guide_grid.addWidget(guide_card, index // 2, index % 2)
        content_layout.addLayout(guide_grid)
        content_layout.addStretch(1)
        self.home_scroll.setWidget(content)
        page_layout.addWidget(welcome)
        page_layout.addWidget(self.home_scroll)

    def check_for_updates(self):
        if getattr(self, "_update_thread", None) is not None:
            return
        self.update_button.setEnabled(False)
        self.update_button.setText("Checking for updates...")
        thread = QThread(self)
        worker = UpdateWorker(APP_VERSION)
        worker.moveToThread(thread)
        self._update_thread = thread
        self._update_worker = worker
        thread.started.connect(worker.run)
        worker.current.connect(self._update_is_current)
        worker.ready.connect(self._update_is_ready)
        worker.failed.connect(self._update_failed)
        worker.completed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._finish_update_check)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _update_is_current(self, version):
        info(self, f"You are already using the latest version ({version}).")

    def _update_is_ready(self, installer_path, version):
        answer = QMessageBox.question(
            self,
            "Update ready",
            f"Version {version} has been downloaded and verified. Close the app and start the installer now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            subprocess.Popen([installer_path], close_fds=True)
        except OSError as exc:
            return error(self, f"Could not start the update installer:\n{exc}")
        self.close()

    def _update_failed(self, message):
        error(self, f"Could not check for or install updates:\n{message}")

    def _finish_update_check(self):
        self._update_worker = None
        self._update_thread = None
        self.update_button.setText("Update application")
        self.update_button.setEnabled(True)

    def build_dashboard(self):
        l=QVBoxLayout()
        l.setContentsMargins(20, 16, 20, 16)
        l.setSpacing(14)
        hero_widget=QWidget(); hero_widget.setObjectName("dashboardHero"); hero_widget.setFixedHeight(112)
        hero=QHBoxLayout(hero_widget); hero.setContentsMargins(18,14,18,14); hero.setSpacing(18)
        brand_mark=QLabel()
        brand_mark.setObjectName("dashboardMark")
        brand_mark.setFixedSize(80, 80)
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setPixmap(QIcon(resource_path("assets/raw_strength_icon.ico")).pixmap(72, 72))
        hero.addWidget(brand_mark)
        heading=QVBoxLayout()
        title=QLabel("Raw Strength Calisthenics")
        title.setProperty("heroTitle", True)
        heading.addWidget(title)
        subtitle=QLabel("Employee Audit Manager · Offline workforce operations")
        subtitle.setProperty("heroSubtitle", True)
        heading.addWidget(subtitle)
        heading.addStretch(1)
        hero.addLayout(heading, 1)
        self._wrap_page_in_scroll(self.dashboard, l, fixed_header=hero_widget)
        self.kpis=QHBoxLayout(); l.addLayout(self.kpis)
        self.kpi_labels=[]
        for title in ["Active employees","Tasks today","Completed today","Pending or blocked","Proof missing"]:
            box=QGroupBox(title); v=QVBoxLayout(box); label=QLabel("0"); label.setProperty("metricValue", True); v.addWidget(label); self.kpis.addWidget(box); self.kpi_labels.append(label)
        row=QHBoxLayout(); l.addLayout(row)
        self.dashboard_tasks=QTableWidget(0,6); self.dashboard_tasks.setHorizontalHeaderLabels(["Employee","Task","Status","Progress","Due","Proof"])
        self.dashboard_tasks.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.dashboard_tasks.setEditTriggers(QAbstractItemView.NoEditTriggers)
        row.addWidget(self.dashboard_tasks, 3)
        productivity_box = QGroupBox("Productivity score")
        productivity_layout = QVBoxLayout(productivity_box)
        score_note = QLabel("Task progress 70% · attendance 30%. If one component is unavailable, the other is used.")
        score_note.setProperty("mutedText", True)
        score_note.setToolTip("For new employees, the score period starts on the joining date. Otherwise, it starts with the first recorded activity.")
        productivity_layout.addWidget(score_note)
        self.productivity_chart = ProductivityChart()
        productivity_layout.addWidget(self.productivity_chart)
        row.addWidget(productivity_box, 2)
        self.productivity_table = QTableWidget(0, 7)
        self.productivity_table.setHorizontalHeaderLabels(["Employee", "Joined / tracking start", "Working days", "Present days", "Tasks", "Completed", "Score"])
        self.productivity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.productivity_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.productivity_table)

    def build_employees(self):
        l=QVBoxLayout()
        self._wrap_page_in_scroll(self.employees_tab, l, "Employees", "Manage employee records, roles, and contact details.")
        row=QHBoxLayout(); l.addLayout(row)
        self.emp_search=QLineEdit(); self.emp_search.setPlaceholderText("Search employee name, ID or department"); self.emp_search.textChanged.connect(self.refresh_employees); row.addWidget(self.emp_search)
        emp_tips = {"Add": "Add a new employee", "Edit": "Edit the selected employee", "Activate / Deactivate": "Toggle active status", "Delete": "Permanently delete the selected employee"}
        for label,slot in [("Add",self.add_employee),("Edit",self.edit_employee),("Activate / Deactivate",self.toggle_employee),("Delete",self.delete_employee)]:
            b=QPushButton(label); b.clicked.connect(slot); b.setToolTip(emp_tips.get(label, "")); b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed); row.addWidget(b)
        self.emp_table=QTableWidget(0,8); self.emp_table.setHorizontalHeaderLabels(["ID","Employee ID","Name","Department","Role","Phone","Email","Status"])
        self.emp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.emp_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.emp_table.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.emp_table)

    def build_tasks(self):
        l=QVBoxLayout()
        self._wrap_page_in_scroll(self.tasks_tab, l, "Task Manager", "Add, edit, and track daily tasks and evidence.")
        row=QHBoxLayout(); l.addLayout(row)
        self.task_date=QDateEdit(); configure_date_edit(self.task_date); self.task_date.setDisplayFormat("yyyy-MM-dd"); self.task_date.setDate(QDate.currentDate()); self.task_date.dateChanged.connect(self.refresh_tasks)
        row.addWidget(QLabel("Date")); row.addWidget(self.task_date)
        self.task_filter=QComboBox(); self.task_filter.addItem("All employees",None)
        row.addWidget(self.task_filter)
        self.task_filter.currentIndexChanged.connect(self.refresh_tasks)
        task_tips = {"Add Task": "Create a new task for the selected date", "Edit Selected": "Edit the selected task", "Delete Selected": "Delete the selected task", "Open Proof": "Open proof/evidence link in browser"}
        for label,slot in [("Add Task",self.add_task),("Edit Selected",self.edit_task),("Delete Selected",self.delete_task),("Open Proof",self.open_proof)]:
            b=QPushButton(label); b.clicked.connect(slot); b.setToolTip(task_tips.get(label, "")); b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed); row.addWidget(b)
        self.task_table=QTableWidget(0,9); self.task_table.setHorizontalHeaderLabels(["ID","Employee","Task","Priority","Status","Progress","Due","Proof","Manager remarks"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.task_table)

    def build_tracker(self):
        l=QVBoxLayout()
        self._wrap_page_in_scroll(self.tracker_tab, l, "Employee Task Tracker", "Review assigned work and evidence.")
        filters=QHBoxLayout(); l.addLayout(filters)
        self.tracker_employee=QComboBox(); self.tracker_employee.addItem("Select employee", None)
        self.tracker_employee.currentIndexChanged.connect(self.refresh_tracker)
        self.tracker_date=QDateEdit(); configure_date_edit(self.tracker_date); self.tracker_date.setDisplayFormat("yyyy-MM-dd"); self.tracker_date.setDate(QDate.currentDate()); self.tracker_date.dateChanged.connect(self.refresh_tracker)
        filters.addWidget(QLabel("Employee")); filters.addWidget(self.tracker_employee,2)
        filters.addWidget(QLabel("Task date")); filters.addWidget(self.tracker_date)
        self.tracker_summary=QLabel("Select an employee to view assigned tasks.")
        self.tracker_summary.setProperty("statusSummary", True)
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
        l=QVBoxLayout()
        self._wrap_page_in_scroll(self.attendance_tab, l, "Attendance & Working Calendar", "Record daily attendance and configure scheduled workdays.")

        # Date row
        row=QHBoxLayout(); row.setSpacing(8); l.addLayout(row)
        self.att_date=QDateEdit(); configure_date_edit(self.att_date); self.att_date.setDisplayFormat("yyyy-MM-dd"); self.att_date.setDate(QDate.currentDate()); self.att_date.dateChanged.connect(self.refresh_attendance)
        row.addWidget(QLabel("Selected date")); row.addWidget(self.att_date)
        row.addStretch(1)

        # Scrollable action toolbar so labels never clip on narrow windows
        toolbar_scroll = QScrollArea()
        toolbar_scroll.setWidgetResizable(True)
        toolbar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        toolbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        toolbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        toolbar_scroll.setFixedHeight(48)
        toolbar_scroll.setStyleSheet("QScrollArea { background: transparent; border: 0; } QWidget#attToolbarInner { background: transparent; }")
        toolbar_inner = QWidget()
        toolbar_inner.setObjectName("attToolbarInner")
        row2 = QHBoxLayout(toolbar_inner)
        row2.setContentsMargins(0, 2, 0, 2)
        row2.setSpacing(8)

        for label, slot in [
            ("Present", lambda: self.set_attendance_status("Present")),
            ("Absent", lambda: self.set_attendance_status("Absent")),
            ("Leave", lambda: self.set_attendance_status("Leave")),
            ("Check In", self.check_in),
            ("Check Out", self.check_out),
            ("Edit Times", self.edit_attendance_times),
            ("Note", self.attendance_note),
        ]:
            b = QPushButton(label)
            b.setMinimumWidth(90)
            b.setMinimumHeight(32)
            b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            b.clicked.connect(slot)
            row2.addWidget(b)

        # Holiday actions in a dropdown (never truncates)
        holiday_btn = QToolButton()
        holiday_btn.setText("Holiday")
        holiday_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        holiday_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        holiday_btn.setMinimumWidth(110)
        holiday_btn.setMinimumHeight(32)
        holiday_menu = QMenu(holiday_btn)
        act_declare = QAction("Declare Holiday", self)
        act_declare.triggered.connect(self.declare_holiday)
        act_remove = QAction("Remove Holiday", self)
        act_remove.triggered.connect(self.remove_holiday)
        holiday_menu.addAction(act_declare)
        holiday_menu.addAction(act_remove)
        holiday_btn.setMenu(holiday_menu)
        holiday_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        row2.addWidget(holiday_btn)
        row2.addStretch(1)

        toolbar_scroll.setWidget(toolbar_inner)
        l.addWidget(toolbar_scroll)

        self.holiday_banner=QLabel("")
        self.holiday_banner.setProperty("warningBanner", True)
        l.addWidget(self.holiday_banner)
        emp_row = QHBoxLayout()
        emp_row.addWidget(QLabel("Filter employee:"))
        self.att_employee_filter = QComboBox()
        self.att_employee_filter.addItem("All employees", None)
        for e in self.db.employees(False):
            self.att_employee_filter.addItem(e["name"], e["id"])
        self.att_employee_filter.currentIndexChanged.connect(self.refresh_attendance)
        emp_row.addWidget(self.att_employee_filter)
        emp_row.addStretch(1)
        l.addLayout(emp_row)
        self.att_table=QTableWidget(0,7); self.att_table.setHorizontalHeaderLabels(["Employee","Date","Attendance status","Check-in","Check-out","Net hours","Note"])
        self.att_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.att_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.att_table.setEditTriggers(QAbstractItemView.NoEditTriggers); l.addWidget(self.att_table, 3)
        summary_note=QLabel("Attendance totals exclude declared holidays and non-working weekdays.")
        summary_note.setProperty("mutedText", True)
        l.addWidget(summary_note)
        self.attendance_summary_table=QTableWidget(0,8)
        headers = ["Employee","Start date","Work days","Present","Absent","Leave","Holidays","Total present"]
        self.attendance_summary_table.setHorizontalHeaderLabels(headers)
        header = self.attendance_summary_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(70)
        for i, h in enumerate(headers):
            self.attendance_summary_table.horizontalHeaderItem(i).setToolTip(h)
        self.attendance_summary_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.attendance_summary_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        l.addWidget(self.attendance_summary_table, 2)

    def build_reports(self):
        outer = QVBoxLayout(self.reports_tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._add_fixed_page_header(outer, "Reports", "Generate audit, attendance, productivity, and employee reports.")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("pageContent")
        l = QVBoxLayout(content)
        l.setContentsMargins(20, 0, 20, 16)
        l.setSpacing(12)

        # Form section in a card-like group
        form_group = QGroupBox("Report parameters")
        form = QFormLayout(form_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setContentsMargins(14, 18, 14, 14)

        self.report_type = QComboBox()
        self.report_type.addItems(["Audit / EOD", "Employee Attendance", "Employee Details", "Employee Productivity"])
        self.report_date = QDateEdit()
        configure_date_edit(self.report_date)
        self.report_date.setDisplayFormat("yyyy-MM-dd")
        self.report_date.setMaximumDate(QDate.currentDate())
        self.report_date.setDate(QDate.currentDate())
        self.report_scope = QComboBox()
        self.report_scope.addItems(["Consolidated — all employees", "Individual — selected employee"])
        self.report_employee = QComboBox()
        self.report_employee.addItem("All employees", None)
        self.report_exclude_employee = QComboBox()
        self.report_exclude_employee.addItem("Exclude none", None)
        self.report_format = QComboBox()
        self.report_format.addItems(["Word (.docx)", "PDF (.pdf)", "CSV (.csv)"])
        self.archived_report = QComboBox()
        self.archived_report.addItem("Generated report for selected date", None)

        form.addRow("Report type", self.report_type)
        form.addRow("Report date", self.report_date)
        form.addRow("Report scope", self.report_scope)
        form.addRow("Employee", self.report_employee)
        form.addRow("Exclude employee (consolidated only)", self.report_exclude_employee)
        form.addRow("Output format", self.report_format)
        form.addRow("Historical archived PDF (optional)", self.archived_report)
        l.addWidget(form_group)

        # EOD options with proper grid
        self.eod_options_group = QGroupBox("Audit / EOD content — choose sections to include")
        eod_grid = QGridLayout(self.eod_options_group)
        eod_grid.setContentsMargins(12, 18, 12, 12)
        eod_grid.setHorizontalSpacing(18)
        eod_grid.setVerticalSpacing(8)
        self.eod_checks = {}
        eod_options = [
            ("summary", "Daily summary", True),
            ("identity", "Employee ID / Department / Role", True),
            ("contact", "Phone / Email", False),
            ("work_status", "Work / EOD status", True),
            ("late_links", "Late / Links status", True),
            ("missing_proof", "Missing proof", True),
            ("tasks", "Task names and status", True),
            ("details", "Task details", True),
            ("due_time", "Due time", True),
            ("proof", "Proof / evidence links", True),
            ("proof_notes", "Proof notes", False),
            ("remarks", "Manager remarks", True),
            ("pending", "Pending items", True),
        ]
        cols = 4
        for index, (key, label, checked) in enumerate(eod_options):
            cb = QCheckBox(label)
            cb.setChecked(checked)
            cb.stateChanged.connect(lambda _state: self.preview_report())
            self.eod_checks[key] = cb
            eod_grid.addWidget(cb, index // cols, index % cols)
        l.addWidget(self.eod_options_group)

        self.report_scope.currentIndexChanged.connect(self._report_scope_changed)
        self.report_exclude_employee.currentIndexChanged.connect(lambda _value: self.preview_report())
        self.archived_report.currentIndexChanged.connect(self._archived_report_changed)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        tooltips = {
            "Preview Report": "Preview the report content before generating",
            "Generate / Save": "Create and save the report to your documents folder",
            "Print Selected Report": "Send the selected report to the printer",
            "Open reports folder": "Open the folder where reports are saved",
        }
        for label, slot, primary in [
            ("Preview Report", self.preview_report, False),
            ("Generate / Save", self.generate_report, True),
            ("Print Selected Report", self.print_report, False),
            ("Open reports folder", self.open_export_folder, False),
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            b.setToolTip(tooltips.get(label, ""))
            if primary:
                b.setDefault(True)
                b.setProperty("primary", True)
            b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed); btn_row.addWidget(b)
        btn_row.addStretch(1)
        l.addLayout(btn_row)

        # Preview summary — notification-style scrollable panel
        preview_label = QLabel("Live preview")
        preview_label.setProperty("mutedText", True)
        l.addWidget(preview_label)
        self.report_summary = QTextEdit()
        self.report_summary.setReadOnly(True)
        self.report_summary.setPlaceholderText("Report preview summary appears here. Select options and click Preview Report.")
        self.report_summary.setMinimumHeight(140)
        self.report_summary.setMaximumHeight(220)
        self.report_summary.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.report_summary.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.report_summary.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.report_summary.setObjectName("reportPreview")
        l.addWidget(self.report_summary)

        l.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.report_type.currentTextChanged.connect(self._report_type_changed)
        self.report_date.dateChanged.connect(lambda _value: self.preview_report())
        self.report_employee.currentIndexChanged.connect(lambda _value: self.preview_report())
        self.refresh_report_employees()
        self.refresh_archived_report_choices()
        self._report_scope_changed()
        self._report_type_changed()

    def build_archive(self):
        l=QVBoxLayout()
        self._wrap_page_in_scroll(self.archive_tab, l, "Historical EOD Archive", "Store and retrieve uploaded EOD PDFs.")
        row=QHBoxLayout(); l.addLayout(row)
        for label,slot in [("Upload PDF(s)",self.upload_eod_pdfs),("View Selected",self.open_archived_pdf),("Export Selected",self.export_archived_pdf),("Delete Selected",self.delete_archived_pdf),("Refresh",self.refresh_archive)]:
            b=QPushButton(label); b.clicked.connect(slot); b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed); row.addWidget(b)
        self.archive_table=QTableWidget(0,7)
        self.archive_table.setHorizontalHeaderLabels(["ID","File name","Employee","Report date","Uploaded","Notes","Size"])
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.archive_table)
        note=QLabel("Archived PDFs are stored in the local database and included in database backups.")
        note.setProperty("mutedText", True)
        l.addWidget(note)

    def build_settings(self):
        l=QVBoxLayout()
        self._wrap_page_in_scroll(self.settings_tab, l, "Settings & Backup", "Manage local storage, account security, and working days.")
        if hasattr(self, "settings_tab"):
            page = self.settings_tab.findChild(QWidget, "pageContent")
            if page is not None:
                page.setObjectName("settingsContent")
        storage_box=QGroupBox("Storage locations"); storage_form=QFormLayout(storage_box)
        for label,path in [("Database",DB_PATH),("Backups",BACKUP_DIR),("Reports",EXPORT_DIR)]:
            path_label=QLabel(str(path)); path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); path_label.setProperty("mutedText", True)
            storage_form.addRow(label,path_label)
        l.addWidget(storage_box)
        row=QHBoxLayout(); l.addLayout(row)
        set_tips = {"Create backup": "Create a backup of the local database", "Restore backup": "Restore database from a backup file", "Change password": "Change your login password", "Update recovery question": "Update your password recovery question", "Manage HR/Admin accounts": "Create or manage HR and Admin accounts", "Export employees CSV": "Export employee list to CSV"}
        for label,slot in [("Create backup",self.backup_db),("Restore backup",self.restore_backup),("Change password",self.change_password),("Update recovery question",self.update_recovery_question),("Manage HR/Admin accounts",self.manage_accounts),("Export employees CSV",self.export_employees_csv)]:
            b=QPushButton(label); b.clicked.connect(slot); b.setToolTip(set_tips.get(label, "")); b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed); row.addWidget(b)
            if label == "Manage HR/Admin accounts" and self.user_role != "Admin":
                b.setEnabled(False); b.setToolTip("Only an Admin account can manage user accounts.")
        days_box=QGroupBox("Working days")
        days_layout=QHBoxLayout(days_box)
        self.workday_checks=[]
        for day_name in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]:
            cb=QCheckBox(day_name); cb.setChecked(day_name in ["Monday","Tuesday","Wednesday","Thursday","Friday"])
            self.workday_checks.append(cb); days_layout.addWidget(cb)
        saved_days=self.db.working_weekdays()
        for idx,cb in enumerate(self.workday_checks): cb.setChecked(idx in saved_days)
        l.addWidget(days_box)
        save_days=QPushButton("Save working days")
        save_days.clicked.connect(self.save_working_week)
        l.addWidget(save_days)
        appearance_box=QGroupBox("Appearance")
        appearance_layout=QVBoxLayout(appearance_box)
        appearance_layout.setSpacing(12)
        theme_row=QHBoxLayout()
        theme_row.addWidget(QLabel("Theme"))
        self.theme_combo=QComboBox()
        self.theme_combo.addItems(["Day", "Night", "Ocean", "Sunset"])
        current = self.current_theme().capitalize()
        if current in ["Day", "Night", "Ocean", "Sunset"]:
            self.theme_combo.setCurrentText(current)
        self.theme_combo.currentTextChanged.connect(lambda t: self.apply_theme(t.lower()))
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)
        appearance_layout.addLayout(theme_row)
        note=QLabel("Choose a color theme. Changes apply immediately.")
        note.setProperty("mutedText", True)
        appearance_layout.addWidget(note)
        l.addWidget(appearance_box)
        l.addStretch()

    def polish_tables(self):
        """Apply consistent, readable table behavior across the application."""
        for page in (self.dashboard, self.employees_tab, self.tasks_tab, self.tracker_tab, self.attendance_tab, self.reports_tab, self.archive_tab, self.settings_tab):
            page_layout = page.layout()
            if page_layout:
                page_layout.setContentsMargins(26, 22, 26, 22)
                page_layout.setSpacing(18)
        for table in (self.dashboard_tasks, self.emp_table, self.task_table, self.tracker_table, self.att_table, self.productivity_table, self.attendance_summary_table, self.archive_table):
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.verticalHeader().setVisible(False)
            table.verticalHeader().setDefaultSectionSize(40)
            table.setWordWrap(True)
            table.setCornerButtonEnabled(False)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.setFocusPolicy(Qt.StrongFocus)
            table.horizontalHeader().setMinimumHeight(42)
            table.horizontalHeader().setMinimumSectionSize(80)
            table.horizontalHeader().setHighlightSections(False)
            table.horizontalHeader().setStretchLastSection(True)

    def selected_id(self, table, col=0):
        rows=table.selectionModel().selectedRows()
        if not rows: return None
        item=table.item(rows[0].row(),col)
        return int(item.text()) if item else None

    def status_item(self, value):
        """Create a table cell styled as a colored status pill."""
        text = str(value or "").strip() or "—"
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        key = text.lower()
        # (bg, fg)
        palette = {
            "submitted": ("#DCFCE7", "#166534"),
            "completed": ("#DCFCE7", "#166534"),
            "active": ("#DCFCE7", "#166534"),
            "present": ("#DCFCE7", "#166534"),
            "provided": ("#DCFCE7", "#166534"),
            "pending": ("#FEF3C7", "#92400E"),
            "pending review": ("#FEF3C7", "#92400E"),
            "in progress": ("#DBEAFE", "#1E40AF"),
            "not started": ("#F1F5F9", "#475569"),
            "unmarked": ("#F1F5F9", "#475569"),
            "inactive": ("#F1F5F9", "#475569"),
            "disabled": ("#F1F5F9", "#475569"),
            "blocked": ("#FEE2E2", "#991B1B"),
            "cancelled": ("#FEE2E2", "#991B1B"),
            "absent": ("#FEE2E2", "#991B1B"),
            "leave": ("#EDE9FE", "#5B21B6"),
            "holiday": ("#E0E7FF", "#3730A3"),
            "missing": ("#FEE2E2", "#991B1B"),
            "high": ("#FEE2E2", "#991B1B"),
            "normal": ("#F1F5F9", "#475569"),
            "low": ("#DBEAFE", "#1E40AF"),
        }
        bg, fg = palette.get(key, ("#F1F5F9", "#475569"))
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        return item

    def set_row_items(self, table, row, values, status_cols=None):
        """Fill a table row; status_cols get colored pill styling."""
        status_cols = set(status_cols or [])
        for c, v in enumerate(values):
            if c in status_cols:
                table.setItem(row, c, self.status_item(v))
            else:
                table.setItem(row, c, QTableWidgetItem(str(v or "")))

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
            self.set_row_items(self.emp_table, r, vals, status_cols={7})
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
        completed=sum(1 for t in rows if t["status"] in ("Completed", "Submitted"))
        avg=round(sum(t["progress"] for t in rows)/len(rows)) if rows else 0
        blocked=sum(1 for t in rows if t["status"]=="Blocked")
        in_progress=sum(1 for t in rows if t["status"]=="In progress")
        # Pending excludes completed/submitted, cancelled, blocked, and in-progress
        pending=sum(1 for t in rows if t["status"] not in ("Completed", "Submitted", "Cancelled", "Blocked", "In progress"))
        self.tracker_summary.setText(f"{len(rows)} tasks  •  {completed} completed/submitted  •  {in_progress} in progress  •  {pending} pending  •  {blocked} blocked")
        self.tracker_progress.setValue(avg)
        for t in rows:
            r=self.tracker_table.rowCount(); self.tracker_table.insertRow(r)
            vals=[t["id"],t["title"],t["priority"],t["status"],f'{t["progress"]}%',t["due_time"],t["proof_url"],t["manager_note"]]
            self.set_row_items(self.tracker_table, r, vals, status_cols={2, 3})

    def add_tracker_task(self):
        eid=self.tracker_employee.currentData()
        if not eid: return error(self, "Select an employee first.")
        d=TaskDialog(self.db,self,employee_id=eid)
        d.date.setDate(self.tracker_date.date())
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals or not vals[2]: return error(self,"Task title and active employee are required.")
        self.db.conn.execute("""INSERT INTO tasks(employee_id,task_date,title,details,due_time,priority,status,progress,proof_url,proof_note,submitted_at,manager_note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*vals, now_text(), now_text()))
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
        if hasattr(self, "eod_options_group"):
            self.eod_options_group.setEnabled(not is_archived)
            self.eod_options_group.setVisible(self.report_type.currentText() == "Audit / EOD")
        if is_archived:
            self.report_summary.setPlainText("Historical archived PDF selected. Use Print Selected Report to print it, or Generate / Save to export a copy.")
        else:
            self.preview_report()

    def _report_type_changed(self, *_args):
        if hasattr(self, "eod_options_group"):
            self.eod_options_group.setVisible(self.report_type.currentText() == "Audit / EOD")
            self.eod_options_group.setEnabled(self.archived_report.currentData() is None)
        self.preview_report()

    def selected_eod_options(self):
        defaults = {
            "summary": True, "identity": True, "contact": False, "work_status": True,
            "late_links": True, "missing_proof": True, "tasks": True, "details": True,
            "due_time": True, "proof": True, "proof_notes": False, "remarks": True, "pending": True,
        }
        return {key: cb.isChecked() for key, cb in getattr(self, "eod_checks", {}).items()} or defaults

    def _report_scope_changed(self, *_args):
        if not hasattr(self, "report_scope") or not hasattr(self, "report_employee"):
            return
        individual = self.report_scope.currentIndex() == 1
        self.report_employee.setEnabled(individual)
        if hasattr(self, "report_exclude_employee"):
            self.report_exclude_employee.setEnabled(not individual)
        if individual and self.report_employee.currentData() is None and self.report_employee.count() > 1:
            self.report_employee.setCurrentIndex(1)
        self.preview_report()

    def refresh_report_employees(self):
        if not hasattr(self,"report_employee"): return
        current=self.report_employee.currentData()
        excluded=self.report_exclude_employee.currentData() if hasattr(self,"report_exclude_employee") else None
        employees=self.db.employees()
        for combo in (self.report_employee, self.report_exclude_employee):
            if combo is not None:
                combo.blockSignals(True)
        self.report_employee.clear(); self.report_employee.addItem("All employees",None)
        for e in employees: self.report_employee.addItem(f'{e["name"]} ({e["employee_code"] or "No ID"})',e["id"])
        idx=self.report_employee.findData(current); self.report_employee.setCurrentIndex(max(idx,0))
        if hasattr(self, "report_exclude_employee"):
            self.report_exclude_employee.clear()
            self.report_exclude_employee.addItem("Exclude none", None)
            for e in employees:
                self.report_exclude_employee.addItem(f'{e["name"]} ({e["employee_code"] or "No ID"})', e["id"])
            ex_idx=self.report_exclude_employee.findData(excluded)
            self.report_exclude_employee.setCurrentIndex(max(ex_idx,0))
        self.report_employee.blockSignals(False)
        if hasattr(self, "report_exclude_employee"):
            self.report_exclude_employee.blockSignals(False)

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
        except sqlite3.Error as ex: error(self, f"Could not save employee: {ex}")

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
        except sqlite3.Error as ex: error(self, f"Could not update employee: {ex}")

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
        try:
            self.db.conn.execute("""INSERT INTO tasks(employee_id,task_date,title,details,due_time,priority,status,progress,proof_url,proof_note,submitted_at,manager_note,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*vals, now_text(), now_text()))
            self.db.conn.commit(); self.db.log("Task added",vals[2]); self.refresh_all()
        except sqlite3.Error as ex: error(self, f"Could not save task: {ex}")

    def edit_task(self, table=None):
        table=table or self.task_table
        tid=self.selected_id(table)
        if not tid: return error(self,"Select a task first.")
        row=self.db.conn.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
        d=TaskDialog(self.db,self,row)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals or not vals[2]: return error(self,"Task title and active employee are required.")
        self.db.conn.execute("""UPDATE tasks SET employee_id=?,task_date=?,title=?,details=?,due_time=?,priority=?,status=?,progress=?,proof_url=?,proof_note=?,submitted_at=?,manager_note=?,updated_at=? WHERE id=?""",(*vals, now_text(), tid))
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

    def refresh_employee_filter(self):
        if not hasattr(self, "att_employee_filter"): return
        current = self.att_employee_filter.currentData()
        self.att_employee_filter.blockSignals(True)
        self.att_employee_filter.clear()
        self.att_employee_filter.addItem("All employees", None)
        for e in self.db.employees(False):
            self.att_employee_filter.addItem(e["name"], e["id"])
        idx = self.att_employee_filter.findData(current)
        if idx >= 0:
            self.att_employee_filter.setCurrentIndex(idx)
        self.att_employee_filter.blockSignals(False)

    def attendance_selected_employee(self):
        # A specific employee in the filter is the source of truth for attendance actions.
        # Only require a table-row choice when the filter is set to All employees.
        if hasattr(self, "att_employee_filter"):
            employee_id = self.att_employee_filter.currentData()
            if employee_id is not None:
                return employee_id
        rows = self.att_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.att_table.item(rows[0].row(), 0)
        return item.data(Qt.UserRole) if item else None

    def set_attendance_status(self, status):
        eid=self.attendance_selected_employee()
        if not eid: return error(self,"Choose an employee in the Filter employee dropdown, or select a row when All employees is selected.")
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
        if not eid: return error(self, "Select an employee first.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        if self.db.is_holiday(d): return error(self,"This date is declared as a holiday. Remove the holiday declaration before recording attendance.")
        time, ok = QInputDialog.getText(self, "Check In", "Check-in time (HH:MM):", text=datetime.now().strftime("%H:%M"))
        if not ok or not time.strip(): return
        self.db.upsert_attendance(eid,d,check_in=time.strip(),status="Present")
        self.db.log("Attendance check-in",f"employee={eid}, date={d}, time={time}"); self.refresh_all()

    def check_out(self):
        eid=self.attendance_selected_employee()
        if not eid: return error(self, "Select an employee first.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        if self.db.is_holiday(d): return error(self,"This date is declared as a holiday.")
        time, ok = QInputDialog.getText(self, "Check Out", "Check-out time (HH:MM):", text=datetime.now().strftime("%H:%M"))
        if not ok or not time.strip(): return
        self.db.upsert_attendance(eid,d,check_out=time.strip(),status="Present")
        self.db.log("Attendance check-out",f"employee={eid}, date={d}, time={time}"); self.refresh_all()

    def edit_attendance_times(self):
        eid = self.attendance_selected_employee()
        if not eid: return error(self,"Choose an employee in the Filter employee dropdown, or select a row when All employees is selected.")
        d = self.att_date.date().toString("yyyy-MM-dd")
        if self.db.is_holiday(d): return error(self, "This date is declared as a holiday.")
        old = self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?", (eid, d)).fetchone()
        ci, ok = QInputDialog.getText(self, "Edit check-in", "Check-in time (HH:MM):", text=old["check_in"] if old else "")
        if not ok: return
        co, ok = QInputDialog.getText(self, "Edit check-out", "Check-out time (HH:MM):", text=old["check_out"] if old else "")
        if not ok: return
        self.db.upsert_attendance(eid, d, check_in=ci.strip(), check_out=co.strip(), status="Present")
        self.db.log("Attendance times edited", f"employee={eid}, date={d}, in={ci}, out={co}")
        self.refresh_all()

    def attendance_note(self):
        eid=self.attendance_selected_employee()
        if not eid: return error(self,"Choose an employee in the Filter employee dropdown, or select a row when All employees is selected.")
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
            self.set_row_items(self.task_table, r, vals, status_cols={3, 4})
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

    def employee_productivity(self, employee, as_of_date=None):
        start=self.tracking_start_date(employee); today=date.today()
        as_of_date=min(as_of_date or today,today)
        task_rows=self.db.conn.execute("SELECT progress,status FROM tasks WHERE employee_id=? AND task_date BETWEEN ? AND ?",(employee["id"],start.isoformat(),as_of_date.isoformat())).fetchall()
        task_score=(sum(int(t["progress"] or 0) for t in task_rows)/len(task_rows)) if task_rows else None
        att_rows=self.db.conn.execute("SELECT work_date,attendance_status,check_in FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ?",(employee["id"],start.isoformat(),as_of_date.isoformat())).fetchall()
        present=sum(1 for a in att_rows if (a["attendance_status"]=="Present" or (a["attendance_status"]=="Unmarked" and a["check_in"])) and not self.db.is_holiday(a["work_date"]))
        eligible=sum(1 for a in att_rows if not self.db.is_holiday(a["work_date"]) and (a["attendance_status"] in ("Present","Absent") or (a["attendance_status"]=="Unmarked" and a["check_in"])))
        attendance_score=(present/eligible*100) if eligible else None
        if task_score is not None and attendance_score is not None: score=round(task_score*0.7+attendance_score*0.3)
        elif task_score is not None: score=round(task_score)
        elif attendance_score is not None: score=round(attendance_score)
        else: score=0
        return {"start":start,"working_days":self.count_working_days(start,as_of_date),"present":present,"tasks":len(task_rows),"completed":sum(1 for t in task_rows if t["status"] in ("Completed","Submitted") or int(t["progress"] or 0)>=100),"task_score":task_score,"attendance_score":attendance_score,"score":score}

    def refresh_attendance(self):
        if not hasattr(self,"att_table"): return
        self.refresh_employee_filter()
        # Remember selected employee so check-in/out stay on the same row
        selected_eid = self.attendance_selected_employee()
        d=self.att_date.date().toString("yyyy-MM-dd")
        holiday=self.db.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?",(d,)).fetchone()
        self.holiday_banner.setText(f"HOLIDAY: {holiday['holiday_name']} — excluded from all working-day counts" if holiday else "No holiday declared for the selected date.")
        rows={a["employee_id"]:a for a in self.db.attendance(d)}
        emps=self.db.employees(False)
        if hasattr(self, "att_employee_filter") and self.att_employee_filter.currentData() is not None:
            filter_id = self.att_employee_filter.currentData()
            emps = [e for e in emps if e["id"] == filter_id]
        self.att_table.setRowCount(0)
        restore_row = -1
        for e in emps:
            a=rows.get(e["id"]); r=self.att_table.rowCount(); self.att_table.insertRow(r)
            name=QTableWidgetItem(e["name"]); name.setData(Qt.UserRole,e["id"]); self.att_table.setItem(r,0,name)
            if selected_eid is not None and e["id"] == selected_eid:
                restore_row = r
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
            for c,v in enumerate(vals,1):
                if c == 2:
                    self.att_table.setItem(r, c, self.status_item(v))
                else:
                    self.att_table.setItem(r, c, QTableWidgetItem(str(v or "")))
        if restore_row >= 0:
            self.att_table.selectRow(restore_row)
        self.refresh_attendance_summary()
        self.refresh_dashboard()

    def refresh_attendance_summary(self):
        if not hasattr(self,"attendance_summary_table"): return
        selected=datetime.strptime(self.att_date.date().toString("yyyy-MM-dd"), "%Y-%m-%d").date()
        month_start=selected.replace(day=1)
        from calendar import monthrange
        month_end=selected.replace(day=monthrange(selected.year,selected.month)[1])
        end=min(month_end,selected,date.today())
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
            since_end=min(selected,date.today())
            since_rows=self.db.conn.execute("SELECT work_date,attendance_status,check_in FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ?",(e["id"],start.isoformat(),since_end.isoformat())).fetchall()
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
            self.set_row_items(self.dashboard_tasks, r, vals, status_cols={2, 5})
        metrics=[]
        self.productivity_table.setRowCount(0)
        for e in self.db.employees(False):
            m=self.employee_productivity(e); metrics.append((e["name"],m["score"]))
            vals=[e["name"],m["start"].isoformat(),m["working_days"],m["present"],m["tasks"],m["completed"],f"{m['score']}%"]
            r=self.productivity_table.rowCount(); self.productivity_table.insertRow(r)
            for c,v in enumerate(vals): self.productivity_table.setItem(r,c,QTableWidgetItem(str(v)))
        self.productivity_chart.set_values(metrics)

    def report_data(self, report_date, employee_id=None):
        emps=self._report_employees(employee_id)
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
        # Exclusion is report-only: it never deletes or changes employee records.
        if employee_id:
            employee = self.db.employee(employee_id)
            return [employee] if employee else []
        employees = self.db.employees()
        excluded_id = self.report_exclude_employee.currentData() if hasattr(self, "report_exclude_employee") else None
        return [employee for employee in employees if employee["id"] != excluded_id]

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
        return {"Audit / EOD":"EMPLOYEE AUDIT / END-OF-DAY REPORT", "Employee Attendance":"EMPLOYEE ATTENDANCE REPORT", "Employee Details":"EMPLOYEE DETAILS REGISTER", "Employee Productivity":"EMPLOYEE PRODUCTIVITY REPORT"}.get(report_type,"EMPLOYEE AUDIT / END-OF-DAY REPORT")

    def make_docx(self, path, report_date, employee_id=None, report_type="Audit / EOD", eod_options=None):
        doc=Document(); sec=doc.sections[0]
        sec.top_margin=Inches(.62); sec.bottom_margin=Inches(.58); sec.left_margin=Inches(.68); sec.right_margin=Inches(.68)
        styles=doc.styles; styles["Normal"].font.name="Aptos"; styles["Normal"].font.size=Pt(9); styles["Normal"].paragraph_format.space_after=Pt(4)
        styles["Title"].font.name="Aptos Display"; styles["Title"].font.size=Pt(20); styles["Title"].font.bold=True; styles["Title"].font.color.rgb=RGBColor(31,59,87)
        header=sec.header.paragraphs[0]; header.text="RAW STRENGTH CALISTHENICS  |  EMPLOYEE AUDIT MANAGER"; header.alignment=1
        for r in header.runs: r.font.name="Aptos"; r.font.size=Pt(8); r.font.bold=True; r.font.color.rgb=RGBColor(71,85,105)
        footer=sec.footer.paragraphs[0]; footer.text=f"Confidential internal report  •  Generated {now_text()}"; footer.alignment=1
        for r in footer.runs: r.font.size=Pt(8); r.font.color.rgb=RGBColor(100,116,139)
        title=doc.add_paragraph(style="Title"); title.alignment=1; title.add_run(self._report_title(report_type))
        chosen=self.db.employee(employee_id) if employee_id else None
        sub=doc.add_paragraph(); sub.alignment=1; sub.add_run(f"Report date: {report_date}    |    Scope: {chosen['name'] if chosen else 'All employees'}").bold=True
        doc.add_paragraph("")
        emps=self._report_employees(employee_id)
        if report_type=="Employee Details":
            tab=doc.add_table(rows=1,cols=8); tab.style="Light Shading Accent 1"
            headers=["Employee ID","Name","Department","Role","Phone","Email","Joining date","Status"]
            for c,v in zip(tab.rows[0].cells,headers): c.text=v
            for e in emps:
                cells=tab.add_row().cells
                vals=[e["employee_code"] or "N/A",e["name"],e["department"] or "N/A",e["designation"] or "N/A",e["phone"] or "N/A",e["email"] or "N/A",e["joining_date"] or "N/A","Active" if e["active"] else "Inactive"]
                for c,v in zip(cells,vals): c.text=str(v)
            doc.add_paragraph(f"Total employees: {len(emps)}")
        elif report_type=="Employee Attendance":
            if self.db.is_holiday(report_date):
                holiday=self.db.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?",(report_date,)).fetchone()
                doc.add_paragraph(f"Declared holiday: {holiday['holiday_name'] if holiday else 'Holiday'}")
            tab=doc.add_table(rows=1,cols=7); tab.style="Light Shading Accent 1"
            headers=["Employee ID","Employee","Status","Check-in","Check-out","Net hours","Remarks"]
            for c,v in zip(tab.rows[0].cells,headers): c.text=v
            rows=self._attendance_report_rows(report_date,employee_id)
            for item in rows:
                e=item["employee"]; cells=tab.add_row().cells
                vals=[e["employee_code"] or "N/A",e["name"],item["status"],item["check_in"] or "N/A",item["check_out"] or "N/A",item["net_hours"] or "N/A",item["note"] or "N/A"]
                for c,v in zip(cells,vals): c.text=str(v)
            present=sum(x["status"]=="Present" for x in rows); absent=sum(x["status"]=="Absent" for x in rows); leave=sum(x["status"]=="Leave" for x in rows)
            doc.add_paragraph(f"Summary: Present {present}  |  Absent {absent}  |  Leave {leave}  |  Employees {len(rows)}")
        elif report_type=="Employee Productivity":
            data=self.report_data(report_date,employee_id)
            for e,tasks,_att in data:
                prod=self.employee_productivity(e, date.fromisoformat(report_date))
                doc.add_heading(e["name"],level=1)
                for label,value in [
                    ("Employee ID",e["employee_code"] or "N/A"),("Department",e["department"] or "N/A"),
                    ("Overall productivity score",f'{prod["score"]}%'),
                    ("Task progress component",f'{round(prod["task_score"])}%' if prod["task_score"] is not None else "Not enough task data"),
                    ("Attendance component",f'{round(prod["attendance_score"])}%' if prod["attendance_score"] is not None else "Not enough attendance data"),
                    ("Scoring explanation","Task progress contributes 70% and attendance contributes 30% when both are available; if only one component is available, that component is used."),
                    ("Tracking start",prod["start"].isoformat()),("Working days since tracking start",prod["working_days"]),
                    ("Present days recorded",prod["present"]),("Tasks counted",prod["tasks"]),("Completed/submitted tasks",prod["completed"]),
                ]:
                    doc.add_paragraph(f"{label}: {value}",style="List Bullet")
                if tasks:
                    doc.add_paragraph("TASK PROGRESS",style="Heading 2")
                    for t in tasks:
                        doc.add_paragraph(f'{t["title"]} — Status: {t["status"]} — Progress: {t["progress"]}%',style="List Bullet")
                else:
                    doc.add_paragraph("No tasks recorded for the selected date.",style="List Bullet")
        else:
            opts=eod_options or self.selected_eod_options()
            data=self.report_data(report_date,employee_id)
            all_tasks=[t for _,ts,_ in data for t in ts]
            completed=sum(1 for t in all_tasks if t["status"] in ("Completed","Submitted"))
            pending_count=sum(1 for t in all_tasks if t["status"] not in ("Completed","Submitted","Cancelled"))
            missing=sum(1 for e,tasks,_ in data if self.employee_missing_proof(e,tasks,report_date).startswith("Yes"))
            if opts.get("summary",True):
                doc.add_heading("DAILY SUMMARY",level=1)
                for item in [f"Employees: {len(data)}",f"Tasks recorded: {len(all_tasks)}",f"Completed / submitted tasks: {completed}",f"Pending / other tasks: {pending_count}",f"Employees flagged for missing proof: {missing}"]:
                    doc.add_paragraph(item,style="List Bullet")
            for e,tasks,_att in data:
                doc.add_heading(e["name"].upper(),level=1)
                if opts.get("identity",True):
                    doc.add_paragraph(f'Employee ID: {e["employee_code"] or "N/A"}  |  Department: {e["department"] or "N/A"}  |  Role: {e["designation"] or "N/A"}',style="List Bullet")
                if opts.get("contact",False):
                    doc.add_paragraph(f'Phone: {e["phone"] or "N/A"}  |  Email: {e["email"] or "N/A"}',style="List Bullet")
                eod=self.source_status(e,"work",report_date) or ("Submitted" if tasks and all(t["status"] in ("Submitted","Completed") for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                if opts.get("work_status",True): doc.add_paragraph(f"WORK / EOD STATUS: {eod}",style="List Bullet")
                if opts.get("late_links",True):
                    late=self.source_status(e,"late",report_date) or "Review required"
                    links=self.source_status(e,"links",report_date) or "Not independently checked"
                    doc.add_paragraph(f"LATE: {late}  |  LINKS: {links}",style="List Bullet")
                if opts.get("missing_proof",True):
                    doc.add_paragraph(f'MISSING PROOF: {self.employee_missing_proof(e,tasks,report_date)}',style="List Bullet")
                if opts.get("tasks",True):
                    doc.add_paragraph("TASKS / WORK ITEMS",style="Heading 2")
                    if tasks:
                        for idx,t in enumerate(tasks,1):
                            doc.add_paragraph(f'{idx}. {t["title"]} — Status: {t["status"]}',style="List Bullet")
                            if opts.get("details",True) and t["details"]: doc.add_paragraph(f'Details: {t["details"]}',style="List Bullet 2")
                            if opts.get("due_time",True) and t["due_time"]: doc.add_paragraph(f'Due time: {t["due_time"]}',style="List Bullet 2")
                            if opts.get("proof",True):
                                doc.add_paragraph(f'Proof / Evidence: {self.task_proof_label(e,t,report_date)}',style="List Bullet 2")
                                if t["proof_url"]: doc.add_paragraph(str(t["proof_url"]),style="List Bullet 2")
                            if opts.get("proof_notes",False) and t["proof_note"]: doc.add_paragraph(f'Proof notes: {t["proof_note"]}',style="List Bullet 2")
                            if opts.get("remarks",True): doc.add_paragraph(f'Manager remarks: {t["manager_note"] or "N/A"}',style="List Bullet 2")
                    else:
                        doc.add_paragraph("No tasks recorded for this date.",style="List Bullet")
                if opts.get("pending",True):
                    pending_titles=[t["title"] for t in tasks if t["status"] not in ("Completed","Submitted","Cancelled")]
                    doc.add_paragraph("PENDING",style="Heading 2")
                    doc.add_paragraph("; ".join(pending_titles) if pending_titles else "No",style="List Bullet")
        doc.save(path)

    def make_pdf(self, path, report_date, employee_id=None, report_type="Audit / EOD", eod_options=None):
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

        elif report_type == "Employee Productivity":
            data = self.report_data(report_date, employee_id)
            for e, tasks, _att in data:
                prod = self.employee_productivity(e, date.fromisoformat(report_date))
                story.append(Paragraph(clean(e["name"]).upper(), styles["RSEmployee"]))
                for label, value in [
                    ("Employee ID", e["employee_code"] or "N/A"),
                    ("Department", e["department"] or "N/A"),
                    ("Overall productivity score", f'{prod["score"]}%'),
                    ("Task progress component", f'{round(prod["task_score"])}%' if prod["task_score"] is not None else "Not enough task data"),
                    ("Attendance component", f'{round(prod["attendance_score"])}%' if prod["attendance_score"] is not None else "Not enough attendance data"),
                    ("Scoring explanation", "Task progress contributes 70% and attendance contributes 30% when both are available. If only one component is available, that component is used."),
                    ("Tracking start", prod["start"].isoformat()),
                    ("Working days since tracking start", str(prod["working_days"])),
                    ("Present days recorded", str(prod["present"])),
                    ("Tasks counted", str(prod["tasks"])),
                    ("Completed / submitted tasks", str(prod["completed"])),
                ]:
                    story.append(bullet(f"{label}: {value}"))
                story.append(Paragraph("TASK PROGRESS", styles["RSSection"]))
                if tasks:
                    for t in tasks:
                        story.append(bullet(f'{t["title"]} — Status: {t["status"]} — Progress: {t["progress"]}%'))
                else:
                    story.append(bullet("No tasks recorded for the selected date."))
                story.append(HRFlowable(width="100%", thickness=.4, color=colors.HexColor("#D4DEE7"), spaceAfter=5))
        else:
            opts = eod_options or self.selected_eod_options()
            data = self.report_data(report_date, employee_id)
            all_tasks = [t for _, tasks, _ in data for t in tasks]
            completed = sum(1 for t in all_tasks if t["status"] in ("Completed", "Submitted"))
            pending_count = sum(1 for t in all_tasks if t["status"] not in ("Completed", "Submitted", "Cancelled"))
            missing = sum(1 for e, tasks, _ in data if self.employee_missing_proof(e, tasks, report_date).startswith("Yes"))
            if opts.get("summary", True):
                story.extend([Paragraph("DAILY SUMMARY", styles["RSSection"]),
                    bullet(f"Employees: {len(data)}"), bullet(f"Tasks recorded: {len(all_tasks)}"),
                    bullet(f"Completed / submitted tasks: {completed}"), bullet(f"Pending / other tasks: {pending_count}"),
                    bullet(f"Employees flagged for missing proof: {missing}"), Spacer(1, 5),
                    HRFlowable(width="100%", thickness=.6, color=cyan, spaceAfter=6)])
            for e, tasks, _att in data:
                story.append(Paragraph(clean(e["name"]).upper(), styles["RSEmployee"]))
                if opts.get("identity", True):
                    story.append(bullet(f'Employee ID: {e["employee_code"] or "N/A"} | Department: {e["department"] or "N/A"} | Role: {e["designation"] or "N/A"}'))
                if opts.get("contact", False):
                    story.append(bullet(f'Phone: {e["phone"] or "N/A"} | Email: {e["email"] or "N/A"}'))
                eod = self.source_status(e, "work", report_date) or ("Submitted" if tasks and all(t["status"] in ("Submitted", "Completed") for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                if opts.get("work_status", True):
                    story.append(bullet(f"WORK / EOD STATUS: {eod}"))
                if opts.get("late_links", True):
                    late = self.source_status(e, "late", report_date) or "Review required"
                    links = self.source_status(e, "links", report_date) or "Not independently checked"
                    story.append(bullet(f"LATE: {late} | LINKS: {links}"))
                if opts.get("missing_proof", True):
                    story.append(bullet(f'MISSING PROOF: {self.employee_missing_proof(e, tasks, report_date)}'))
                if opts.get("tasks", True):
                    story.append(Paragraph("TASKS / WORK ITEMS", styles["RSSection"]))
                    if tasks:
                        for idx, t in enumerate(tasks, 1):
                            story.append(bullet(f'{idx}. {t["title"]} — Status: {t["status"]}'))
                            if opts.get("details", True) and t["details"]:
                                story.append(bullet(f'Details: {t["details"]}'))
                            if opts.get("due_time", True) and t["due_time"]:
                                story.append(bullet(f'Due time: {t["due_time"]}'))
                            if opts.get("proof", True):
                                story.append(bullet(f'Proof / Evidence: {self.task_proof_label(e, t, report_date)}'))
                                if t["proof_url"]:
                                    story.append(Paragraph("&#8226;&nbsp; " + escape(str(t["proof_url"])), styles["RSLink"]))
                            if opts.get("proof_notes", False) and t["proof_note"]:
                                story.append(bullet(f'Proof notes: {t["proof_note"]}'))
                            if opts.get("remarks", True):
                                story.append(bullet(f'Manager remarks: {t["manager_note"] or "N/A"}'))
                    else:
                        story.append(bullet("No tasks recorded for this date."))
                if opts.get("pending", True):
                    pending_titles = [t["title"] for t in tasks if t["status"] not in ("Completed", "Submitted", "Cancelled")]
                    story.extend([Paragraph("PENDING", styles["RSSection"]), bullet("; ".join(pending_titles) if pending_titles else "No")])
                story.extend([Spacer(1, 5), HRFlowable(width="100%", thickness=.4, color=colors.HexColor("#D4DEE7"), spaceAfter=5)])

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

    def export_report_csv(self, path, report_date, employee_id=None, report_type="Audit / EOD", eod_options=None):
        import csv
        opts=eod_options or self.selected_eod_options()
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f)
            if report_type=="Employee Details":
                w.writerow(["Employee ID","Name","Department","Role","Phone","Email","Joining date","Status","Notes"])
                for e in self._report_employees(employee_id):
                    w.writerow([e["employee_code"] or "N/A",e["name"],e["department"] or "N/A",e["designation"] or "N/A",e["phone"] or "N/A",e["email"] or "N/A",e["joining_date"] or "N/A","Active" if e["active"] else "Inactive",e["notes"] or "N/A"])
            elif report_type=="Employee Attendance":
                w.writerow(["Report date","Employee ID","Employee","Department","Status","Check-in","Check-out","Net hours","Remarks"])
                for x in self._attendance_report_rows(report_date,employee_id):
                    e=x["employee"]; w.writerow([report_date,e["employee_code"] or "N/A",e["name"],e["department"] or "N/A",x["status"],x["check_in"] or "N/A",x["check_out"] or "N/A",x["net_hours"] or "N/A",x["note"] or "N/A"])
            elif report_type=="Employee Productivity":
                w.writerow(["Report date","Employee ID","Employee","Department","Overall score %","Task progress component %","Attendance component %","Scoring explanation","Tracking start","Working days since start","Present days","Tasks counted","Completed/submitted tasks","Task","Task status","Task progress %"])
                for e,tasks,_att in self.report_data(report_date,employee_id):
                    prod=self.employee_productivity(e, date.fromisoformat(report_date))
                    explanation="Task progress 70% + attendance 30% when both available; otherwise available component used."
                    if not tasks:
                        w.writerow([report_date,e["employee_code"] or "N/A",e["name"],e["department"] or "N/A",prod["score"],round(prod["task_score"]) if prod["task_score"] is not None else "N/A",round(prod["attendance_score"]) if prod["attendance_score"] is not None else "N/A",explanation,prod["start"].isoformat(),prod["working_days"],prod["present"],prod["tasks"],prod["completed"],"N/A","N/A","N/A"])
                    for t in tasks:
                        w.writerow([report_date,e["employee_code"] or "N/A",e["name"],e["department"] or "N/A",prod["score"],round(prod["task_score"]) if prod["task_score"] is not None else "N/A",round(prod["attendance_score"]) if prod["attendance_score"] is not None else "N/A",explanation,prod["start"].isoformat(),prod["working_days"],prod["present"],prod["tasks"],prod["completed"],t["title"],t["status"],t["progress"]])
            else:
                headers=["Report date","Employee ID","Employee","Department","Role"]
                field_keys=[("work_status","EOD status"),("late_links","Late"),("late_links","Links status"),("missing_proof","Missing proof"),("tasks","Task"),("details","Task details"),("tasks","Task status"),("due_time","Due time"),("proof","Proof URL"),("proof_notes","Proof notes"),("remarks","Manager remarks"),("pending","Pending items")]
                headers += [label for key,label in field_keys if opts.get(key,True)]
                w.writerow(headers)
                for e,tasks,_att in self.report_data(report_date,employee_id):
                    eod=self.source_status(e,"work",report_date) or ("Submitted" if tasks and all(t["status"] in ("Submitted","Completed") for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                    base=[report_date,e["employee_code"] or "N/A",e["name"],e["department"] or "N/A",e["designation"] or "N/A"]
                    task_rows=tasks or [None]
                    for t in task_rows:
                        values={
                            "EOD status":eod,
                            "Late":self.source_status(e,"late",report_date) or "Review required",
                            "Links status":self.source_status(e,"links",report_date) or "Not independently checked",
                            "Missing proof":self.employee_missing_proof(e,tasks,report_date),
                            "Task":t["title"] if t else "N/A",
                            "Task details":t["details"] if t else "N/A",
                            "Task status":t["status"] if t else "N/A",
                            "Due time":t["due_time"] or "N/A" if t else "N/A",
                            "Proof URL":t["proof_url"] or "N/A" if t else "N/A",
                            "Proof notes":t["proof_note"] or "N/A" if t else "N/A",
                            "Manager remarks":t["manager_note"] or "N/A" if t else "N/A",
                            "Pending items":"; ".join(x["title"] for x in tasks if x["status"] not in ("Completed","Submitted","Cancelled")) or "No",
                        }
                        row=base+[values[label] for key,label in field_keys if opts.get(key,True)]
                        w.writerow(row)

    def preview_report(self):
        if not hasattr(self,"report_summary"): return
        d=self.report_date.date().toString("yyyy-MM-dd"); eid=self._effective_report_employee_id(); kind=self.report_type.currentText()
        if kind=="Employee Details":
            emps=self._report_employees(eid); lines=[self._report_title(kind),f"Employees: {len(emps)}","", "\n".join(f'{e["employee_code"] or "N/A"} | {e["name"]} | {e["department"] or "N/A"} | {e["designation"] or "N/A"}' for e in emps)]
            self.report_summary.setPlainText("\n".join(lines))
        elif kind=="Employee Attendance":
            rows=self._attendance_report_rows(d,eid); lines=[self._report_title(kind),f"Date: {d}",""]
            lines += [f'{x["employee"]["name"]} | {x["status"]} | In: {x["check_in"] or "—"} | Out: {x["check_out"] or "—"} | Hours: {x["net_hours"] or "—"}' for x in rows]
            self.report_summary.setPlainText("\n".join(lines))
        elif kind=="Employee Productivity":
            lines=[self._report_title(kind),f"Date: {d}",""]
            for e,tasks,_a in self.report_data(d,eid):
                prod=self.employee_productivity(e, date.fromisoformat(d))
                lines.extend([e["name"],f'Employee ID: {e["employee_code"] or "N/A"} | Department: {e["department"] or "N/A"}',
                    f'Overall score: {prod["score"]}%',
                    f'Task progress component: {round(prod["task_score"])}%' if prod["task_score"] is not None else "Task progress component: N/A",
                    f'Attendance component: {round(prod["attendance_score"])}%' if prod["attendance_score"] is not None else "Attendance component: N/A",
                    "Reason: task progress contributes 70% and attendance 30% when both are available; otherwise the available component is used.",
                    f'Tracking start: {prod["start"].isoformat()} | Working days: {prod["working_days"]} | Present days: {prod["present"]}'])
                lines.extend([f'• {t["title"]}: {t["status"]} — {t["progress"]}%' for t in tasks]); lines.append("")
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
            if ext==".csv": self.export_report_csv(path,d,eid,kind,self.selected_eod_options())
            elif ext==".docx": self.make_docx(path,d,eid,kind,self.selected_eod_options())
            else: self.make_pdf(path,d,eid,kind,self.selected_eod_options())
            self.preview_report(); self.db.log("Report generated",f"{kind}: {path}"); info(self,f"{kind} report saved:\n{path}")
        except Exception as ex: error(self,f"Could not generate report:\n{ex}")

    def report_preview_text(self,d,eid):
        data=self.report_data(d,eid); opts=self.selected_eod_options()
        lines=[f"RAW STRENGTH CALISTHENICS — EMPLOYEE AUDIT / EOD: {d}",""]
        all_tasks=[t for _,tasks,_ in data for t in tasks]
        if opts.get("summary",True):
            lines.extend(["DAILY SUMMARY",f"• Employees: {len(data)}",f"• Tasks recorded: {len(all_tasks)}",
                f'• Completed / submitted tasks: {sum(1 for t in all_tasks if t["status"] in ("Completed","Submitted"))}',
                f'• Pending / other tasks: {sum(1 for t in all_tasks if t["status"] not in ("Completed","Submitted","Cancelled"))}',
                f'• Employees flagged for missing proof: {sum(1 for e,tasks,_ in data if self.employee_missing_proof(e,tasks,d).startswith("Yes"))}',""])
        for e,tasks,_att in data:
            lines.append(e["name"].upper())
            if opts.get("identity",True): lines.append(f'• Employee ID: {e["employee_code"] or "N/A"} | Department: {e["department"] or "N/A"} | Role: {e["designation"] or "N/A"}')
            if opts.get("contact",False): lines.append(f'• Phone: {e["phone"] or "N/A"} | Email: {e["email"] or "N/A"}')
            eod=self.source_status(e,"work",d) or ("Submitted" if tasks and all(t["status"] in ("Submitted","Completed") for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
            if opts.get("work_status",True): lines.append(f"• WORK / EOD STATUS: {eod}")
            if opts.get("late_links",True):
                lines.append(f'• LATE: {self.source_status(e,"late",d) or "Review required"} | LINKS: {self.source_status(e,"links",d) or "Not independently checked"}')
            if opts.get("missing_proof",True): lines.append(f'• MISSING PROOF: {self.employee_missing_proof(e,tasks,d)}')
            if opts.get("tasks",True):
                lines.append("TASKS / WORK ITEMS")
                if tasks:
                    for i,t in enumerate(tasks,1):
                        lines.append(f'• {i}. {t["title"]} — Status: {t["status"]}')
                        if opts.get("details",True) and t["details"]: lines.append(f'  • Details: {t["details"]}')
                        if opts.get("due_time",True) and t["due_time"]: lines.append(f'  • Due time: {t["due_time"]}')
                        if opts.get("proof",True):
                            lines.append(f'  • Proof / Evidence: {self.task_proof_label(e,t,d)}')
                            if t["proof_url"]: lines.append(f'  • {t["proof_url"]}')
                        if opts.get("proof_notes",False) and t["proof_note"]: lines.append(f'  • Proof notes: {t["proof_note"]}')
                        if opts.get("remarks",True): lines.append(f'  • Manager remarks: {t["manager_note"] or "N/A"}')
                else: lines.append("• No tasks recorded for this date.")
            if opts.get("pending",True):
                pending=[t["title"] for t in tasks if t["status"] not in ("Completed","Submitted","Cancelled")]
                lines.append("PENDING: " + ("; ".join(pending) if pending else "No"))
            lines.append("")
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
            if ext==".docx": self.make_docx(path,d,eid,kind,self.selected_eod_options())
            else: self.make_pdf(path,d,eid,kind,self.selected_eod_options())
            if sys.platform=="win32": os.startfile(str(path),"print")
            else: info(self,f"Report created for printing:\n{path}")
            self.db.log("Report sent to print",f"{kind}: {path}")
        except Exception as ex: error(self,f"Could not prepare/print report:\n{ex}")

    def open_export_folder(self):
        if sys.platform=="win32": os.startfile(str(EXPORT_DIR))
        else: webbrowser.open(EXPORT_DIR.as_uri())

    def backup_db(self, silent=False):
        """Create a backup. Returns True on success, False on failure."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = BACKUP_DIR / f"employee_audit_backup_{stamp}_{secrets.token_hex(4)}.db"
        try:
            self.db.conn.commit()
            dest=sqlite3.connect(target)
            self.db.conn.backup(dest); dest.close()
            self.db.log("Database backup created",str(target))
            if not silent:
                info(self,f"Backup created:\n{target}")
            return True
        except Exception as ex:
            error(self,f"Backup failed:\n{ex}")
            return False

    def restore_backup(self):
        path,_=QFileDialog.getOpenFileName(self,"Select database backup",str(BACKUP_DIR),"SQLite database (*.db)")
        if not path: return
        if not ask(self,"Restore backup","This replaces current data. A backup of the current database will be created first. Continue?"): return
        # Safety backup of current database
        if not self.backup_db(silent=True):
            return error(self, "Safety backup failed. Restore cancelled.")
        # Validate selected file
        try:
            test = sqlite3.connect(path)
            integrity = test.execute("PRAGMA integrity_check").fetchone()
            if integrity and integrity[0] != "ok":
                test.close()
                return error(self, "The selected database failed integrity check.")
            tables = {r[0] for r in test.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            test.close()
            required = {"employees", "tasks", "attendance"}
            if not required.issubset(tables):
                return error(self, "The selected file is missing required tables.")
        except Exception as ex:
            return error(self, f"The selected file is not a valid database:\n{ex}")
        # Keep a recoverable copy of the original, fully validate the temp file,
        # then replace. On reopen failure, restore the original.
        temp_path = DB_PATH.with_suffix(".restore.tmp")
        original_copy = DB_PATH.with_suffix(".pre-restore.bak")
        try:
            shutil.copy2(path, temp_path)
            # Full validation of the temporary copy
            check = sqlite3.connect(temp_path)
            integrity = check.execute("PRAGMA integrity_check").fetchone()
            if integrity and integrity[0] != "ok":
                check.close()
                raise ValueError("Temporary restore copy failed integrity check.")
            tables = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            check.close()
            if not {"employees", "tasks", "attendance"}.issubset(tables):
                raise ValueError("Temporary restore copy is missing required tables.")
            # Preserve original for recovery
            shutil.copy2(DB_PATH, original_copy)
            self.db.conn.close()
            os.replace(temp_path, DB_PATH)
            try:
                self.db = Database()
            except Exception:
                # Reopen failed — restore the original
                shutil.copy2(original_copy, DB_PATH)
                self.db = Database()
                raise RuntimeError("Restore reopened unsuccessfully; original database was restored.")
            info(self, "Backup restored. Restart the application if any screen does not refresh.")
            self.close()
        except Exception as ex:
            for p in (temp_path,):
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
            error(self, f"Restore failed.\n{ex}")

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
                if col == 3:
                    table.setItem(idx, col, self.status_item(val))
                else:
                    table.setItem(idx, col, QTableWidgetItem(str(val)))
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


def light_stylesheet():
    return """
QDialog#loginDialog { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #15233F, stop:1 #312E81); }
QDialog#loginDialog QLabel { color: #F8FAFC; }
QDialog#loginDialog QLabel[pageTitle="true"] { color: #FFFFFF; font-size: 16pt; font-weight: 700; }
QDialog#loginDialog QLabel[pageSubtitle="true"] { color: #C7D2FE; }
QDialog#loginDialog QLineEdit { background: #1E293B; color: #F8FAFC; border: 1px solid #475569; border-radius: 8px; padding: 8px; }
QDialog#loginDialog QPushButton { background: #7C5CFC; color: #FFFFFF; border: 0; border-radius: 8px; padding: 8px 16px; font-weight: 600; }
QDialog#loginDialog QPushButton:hover { background: #6D28D9; }
QDialog#loginDialog QPushButton[flat="true"] { background: transparent; color: #C7D2FE; }
QDialog#loginDialog QPushButton[flat="true"]:hover { color: #FFFFFF; }

* { font-family: "DejaVu Sans"; font-size: 9pt; color: #1E293B; }
QMainWindow { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #EAF2FF, stop:0.48 #F4F0FF, stop:1 #E0F7FA); }
QWidget#titleBar { background: #15233F; border: 0; }
QLabel#titleLabel { color: #F8FAFC; font-weight: 600; font-size: 10pt; }
QPushButton#titleBtnMin, QPushButton#titleBtnMax, QPushButton#titleBtnClose {
    min-width: 0; max-width: 32px; min-height: 0; max-height: 28px; padding: 0; margin: 0;
    background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 11pt; font-weight: 700;
}
QPushButton#titleBtnMin:hover, QPushButton#titleBtnMax:hover { background: #E2E8F0; color: #0F172A; }
QPushButton#titleBtnClose:hover { background: #FEE2E2; color: #DC2626; }
QPushButton#titleFileBtn { background: transparent; color: #C7D2E8; border: 0; border-radius: 4px; padding: 0 10px; font-weight: 600; }
QPushButton#titleFileBtn:hover { background: #1E2F52; color: #FFFFFF; }
QPushButton#titleFileBtn::menu-indicator { image: none; }
QTabWidget::pane { border: 0; background: transparent; top: 0; margin-top: 0; }
QTabWidget { background: transparent; }
QMenuBar { background: #F1F5F9; border-bottom: 1px solid #CBD5E1; padding: 5px 10px; color: #1E293B; }
QMenuBar::item { padding: 7px 12px; border-radius: 6px; background: transparent; color: #1E293B; }
QMenuBar::item:selected { background: #E0E7FF; color: #5B21B6; }
QMenu { background: #F1F5F9; border: 1px solid #CBD5E1; padding: 6px; border-radius: 8px; color: #1E293B; }
QMenu::item { padding: 8px 22px; border-radius: 5px; color: #1E293B; }
QMenu::item:selected { background: #E0E7FF; color: #5B21B6; }
QTabBar { background: #15233F; }
QTabBar::tab { background: transparent; color: #C7D2E8; padding: 10px 12px; margin: 0 1px; border: 0; border-bottom: 3px solid transparent; font-weight: 600; min-width: 60px; min-height: 22px; }
QTabBar::tab:selected { background: #1E2F52; color: #ffffff; border-bottom: 3px solid #7C5CFC; }
QTabBar::tab:hover:!selected { background: #1A2A4A; color: #ffffff; }
QTabBar::scroller { width: 24px; }
QTabBar QToolButton { background: #1A2A4A; color: #ffffff; border: 1px solid #3B4F75; border-radius: 4px; }
QPushButton, QToolButton { padding: 8px 12px; min-height: 30px; min-width: 0; border: 1px solid #CBD5E1; border-radius: 8px; background: #FFFFFF; color: #1E293B; font-weight: 600; text-align: center; }
QPushButton:hover, QToolButton:hover { background: #E2E8F0; color: #0F172A; }
QPushButton:pressed, QToolButton:pressed { background: #CBD5E1; }
QPushButton:disabled, QToolButton:disabled { background: #F1F5F9; color: #94A3B8; border-color: #E2E8F0; }
QPushButton:default, QPushButton[primary="true"] { background: #7C5CFC; border-color: #7C5CFC; color: #ffffff; }
QPushButton:default:hover, QPushButton[primary="true"]:hover { background: #6D28D9; border-color: #6D28D9; }
QToolButton::menu-button { border: none; width: 22px; }
QToolButton::menu-indicator { image: none; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit {
    background-color: #FFFFFF; color: #0F172A; border: 0; border-radius: 12px;
    padding: 10px 14px; selection-background-color: #EDE9FE; selection-color: #0F172A;
}
QComboBox, QDateEdit {
    background-color: #FFFFFF; color: #0F172A; border: 0; border-radius: 12px;
    padding: 10px 14px; min-height: 20px; selection-background-color: #EDE9FE; selection-color: #0F172A;
}
QComboBox:editable, QComboBox:!editable, QComboBox::drop-down:editable { background-color: #F1F5F9; color: #0F172A; }
QComboBox QLineEdit { background-color: #F1F5F9; color: #0F172A; border: 0; padding: 0; }
QDateEdit { min-width: 142px; padding-right: 30px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 2px solid #7C5CFC; background-color: #F1F5F9; color: #0F172A;
}
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 28px; border: none; background: transparent; }
QComboBox QAbstractItemView { background-color: #F1F5F9; color: #0F172A; border: 1px solid #94A3B8; selection-background-color: #EDE9FE; selection-color: #4C1D95; outline: 0; padding: 4px; }
QComboBox QAbstractItemView::item { color: #0F172A; background-color: #F1F5F9; padding: 6px 10px; min-height: 22px; }
QComboBox QAbstractItemView::item:selected { background-color: #EDE9FE; color: #4C1D95; }
QHeaderView::section { background: #E2E8F0; color: #334155; padding: 10px; border: 0; border-bottom: 1px solid #CBD5E1; font-weight: 700; }
QTableWidget { background: rgba(255,255,255,0.68); alternate-background-color: rgba(241,245,249,0.66); color: #0F172A; border: 1px solid rgba(255,255,255,0.82); border-radius: 16px; gridline-color: rgba(226,232,240,0.65); selection-background-color: #DDE7FF; selection-color: #312E81; outline: 0; }
QTableWidget::item { padding: 8px 10px; border-bottom: 1px solid #E2E8F0; color: #0F172A; }
QTableWidget::item:selected { background: #EEF2FF; color: #312E81; }
QTableWidget::item:hover { background: #F5F3FF; }
QGroupBox { font-weight: 650; color: #1E293B; border: 1px solid rgba(255,255,255,0.78); border-radius: 16px; margin-top: 0; padding: 24px 14px 14px 14px; background: rgba(255,255,255,0.72); }
QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; top: 8px; left: 12px; padding: 0; background: transparent; color: #475569; }
QLabel { color: #1E293B; background: transparent; }
QLabel[pageTitle="true"] { color: #0F172A; font-size: 15pt; font-weight: 700; }
QLabel[pageSubtitle="true"] { color: #64748B; font-size: 9pt; font-weight: 500; padding-bottom: 4px; }
QLabel[mutedText="true"] { color: #64748B; }
QLabel[heroTitle="true"], QLabel[welcomeTitle="true"] { color: #FFFFFF; font-size: 16pt; font-weight: 700; }
QLabel[heroSubtitle="true"] { color: #E2E8F0; font-size: 9pt; }
QLabel[welcomeSubtitle="true"] { color: #F3E8FF; font-size: 9pt; }
QWidget#dashboardHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #15233F, stop:1 #312E81); border-radius: 14px; }
QWidget#welcomeHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #5B21B6, stop:1 #DB2777); border-radius: 14px; }
QScrollArea#homeScroll { border: 0; background: transparent; }
QWidget#homeContent { background: rgba(255,255,255,0.58); border: 1px solid rgba(255,255,255,0.75); border-radius: 18px; }
QScrollArea#pageScroll { border: 0; background: transparent; }
QWidget#pageContent { background: rgba(255,255,255,0.54); border: 1px solid rgba(255,255,255,0.72); border-radius: 18px; }
QTextEdit#reportPreview { background: #F1F5F9; border: 0; border-radius: 14px; }
QWidget#sessionStrip { background: #F1F5F9; border: 0; border-radius: 16px; }
QLabel[sessionLabel="true"] { color: #64748B; font-size: 8pt; font-weight: 700; }
QLabel[roleBadge="true"] { background: #EDE9FE; color: #5B21B6; border-radius: 8px; padding: 4px 10px; font-weight: 700; }
QLabel[sectionHeading="true"] { color: #0F172A; font-size: 12.5pt; font-weight: 700; }
QWidget#guideItem { background: #F1F5F9; border: 0; border-left: 4px solid #7C5CFC; border-radius: 16px; }
QLabel[guideTitle="true"] { color: #0F172A; font-size: 10.5pt; font-weight: 700; }
QLabel[metricValue="true"] { font-size: 26pt; font-weight: 700; color: #7C5CFC; }
QLabel[statusSummary="true"] { background: #EEF2FF; border: 0; border-radius: 14px; color: #312E81; font-weight: 600; padding: 11px 14px; }
QLabel[warningBanner="true"] { background: #FFFBEB; border: 0; border-radius: 14px; color: #92400E; font-weight: 600; padding: 9px 12px; }
QProgressBar { border: 1px solid #CBD5E1; border-radius: 8px; text-align: center; color: #1E293B; background: #E2E8F0; min-height: 15px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7C5CFC, stop:1 #DB2777); border-radius: 7px; }
QCheckBox { spacing: 10px; padding: 4px; color: #334155; background: transparent; font-weight: 500; }
QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid #94A3B8; border-radius: 5px; background: #F1F5F9; }
QCheckBox::indicator:hover { border-color: #7C5CFC; background: #EEF2FF; }
QCheckBox::indicator:checked { background: #7C5CFC; border-color: #7C5CFC; }
QCheckBox::indicator:checked:hover { background: #6D28D9; border-color: #6D28D9; }
QStatusBar { background: #F1F5F9; color: #334155; border-top: 1px solid #CBD5E1; padding: 4px 8px; font-weight: 500; }
QRadioButton { spacing: 8px; color: #334155; background: transparent; }
QStatusBar { background: #F1F5F9; color: #64748B; border-top: 1px solid #CBD5E1; }
QStatusBar::item { border: none; }
QScrollBar:vertical, QScrollBar:horizontal { background: transparent; width: 11px; height: 11px; margin: 2px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #CBD5E1; border-radius: 5px; min-height: 24px; min-width: 24px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #94A3B8; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QDialog { background: #E8EEF6; color: #1E293B; }
QFormLayout QLabel { color: #334155; background: transparent; }
QToolTip { background: #F1F5F9; color: #1E293B; border: 1px solid #CBD5E1; padding: 6px 8px; border-radius: 6px; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: #15233F; }
QCalendarWidget QToolButton { background: transparent; color: #ffffff; border: 0; border-radius: 4px; padding: 6px 8px; font-weight: 600; }
QCalendarWidget QToolButton:hover { background: #7C5CFC; }
QCalendarWidget QSpinBox { background: transparent; color: #ffffff; border: 0; padding: 3px; }
QCalendarWidget QAbstractItemView { background: #F1F5F9; alternate-background-color: #F1F5F9; color: #0F172A; selection-background-color: #7C5CFC; selection-color: #ffffff; outline: 0; }
"""

def dark_stylesheet():
    return """
QWidget#settingsContent QGroupBox { background: #111827; }
QWidget#settingsContent QLabel { color: #E2E8F0; }
QWidget#settingsContent QPushButton { background: #1E293B; color: #F1F5F9; }
QWidget#settingsContent QComboBox { background: #0F172A; color: #F8FAFC; }

* { font-family: "DejaVu Sans"; font-size: 9pt; color: #E2E8F0; }
QMainWindow { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #080F20, stop:0.52 #11152E, stop:1 #082F49); }
QWidget#titleBar { background: #070B14; border-bottom: 1px solid #111827; }
QLabel#titleLabel { color: #F8FAFC; font-weight: 600; font-size: 10pt; }
QPushButton#titleBtnMin, QPushButton#titleBtnMax, QPushButton#titleBtnClose {
    min-width: 0; max-width: 32px; min-height: 0; max-height: 28px; padding: 0; margin: 0;
    background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 11pt; font-weight: 700;
}
QPushButton#titleBtnMin:hover, QPushButton#titleBtnMax:hover { background: #E2E8F0; color: #0F172A; }
QPushButton#titleBtnClose:hover { background: #FEE2E2; color: #DC2626; }
QTabWidget::pane { border: 0; background: transparent; top: 0; margin-top: 0; }
QTabWidget { background: transparent; }
QMenuBar { background: #111827; border-bottom: 1px solid #1F2937; padding: 5px 10px; color: #E2E8F0; }
QMenuBar::item { padding: 7px 12px; border-radius: 6px; background: transparent; color: #E2E8F0; }
QMenuBar::item:selected { background: #1E1B4B; color: #C4B5FD; }
QMenu { background: #111827; border: 1px solid #1F2937; padding: 6px; border-radius: 8px; color: #E2E8F0; }
QMenu::item { padding: 8px 22px; border-radius: 5px; color: #E2E8F0; }
QMenu::item:selected { background: #1E1B4B; color: #C4B5FD; }
QTabBar { background: #070B14; }
QTabBar::tab { background: transparent; color: #94A3B8; padding: 12px 15px; margin: 0 1px; border: 0; border-bottom: 3px solid transparent; font-weight: 600; min-width: 68px; min-height: 24px; }
QTabBar::tab:selected { background: #111827; color: #FFFFFF; border-bottom: 3px solid #A78BFA; }
QTabBar::tab:hover:!selected { background: #0F172A; color: #F8FAFC; }
QTabBar::scroller { width: 24px; }
QTabBar QToolButton { background: #111827; color: #E2E8F0; border: 1px solid #334155; border-radius: 4px; }
QPushButton, QToolButton {
    padding: 8px 12px; min-height: 30px; min-width: 0; border: 1px solid #334155;
    border-radius: 8px; background: #1E293B; color: #F1F5F9; font-weight: 600; text-align: center;
}
QPushButton:hover, QToolButton:hover { background: #334155; color: #FFFFFF; }
QPushButton:pressed, QToolButton:pressed { background: #0F172A; }
QPushButton:disabled, QToolButton:disabled { background: #111827; color: #64748B; border-color: #1F2937; }
QPushButton:default, QPushButton[primary="true"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7C5CFC, stop:1 #DB2777); border: 0; color: #ffffff; }
QPushButton:default:hover, QPushButton[primary="true"]:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6D28D9, stop:1 #BE185D); }
QToolButton::menu-button { border: none; width: 22px; }
QToolButton::menu-indicator { image: none; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit {
    background-color: #0F172A; color: #F8FAFC; border: 0; border-radius: 12px;
    padding: 10px 14px; selection-background-color: #4C1D95; selection-color: #FFFFFF;
}
QComboBox, QDateEdit {
    background-color: #111827; color: #F8FAFC; border: 0; border-radius: 14px;
    padding: 8px 10px; min-height: 20px; selection-background-color: #4C1D95; selection-color: #FFFFFF;
}
QComboBox:editable, QComboBox:!editable, QComboBox::drop-down:editable { background-color: #111827; color: #F8FAFC; }
QComboBox QLineEdit { background-color: #111827; color: #F8FAFC; border: 0; padding: 0; }
QDateEdit { min-width: 142px; padding-right: 30px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 2px solid #A78BFA; background-color: #0F172A; color: #F8FAFC;
}
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 28px; border: none; background: transparent; }
QComboBox QAbstractItemView { background-color: #111827; color: #F8FAFC; border: 1px solid #334155; selection-background-color: #4C1D95; selection-color: #FFFFFF; outline: 0; padding: 4px; }
QComboBox QAbstractItemView::item { color: #F8FAFC; background-color: #111827; padding: 6px 10px; min-height: 22px; }
QComboBox QAbstractItemView::item:selected { background-color: #4C1D95; color: #FFFFFF; }
QHeaderView::section { background: #111827; color: #CBD5E1; padding: 10px; border: 0; border-bottom: 1px solid #1F2937; font-weight: 700; }
QTableWidget { background: rgba(15,23,42,0.76); alternate-background-color: rgba(30,41,59,0.60); color: #E2E8F0; border: 1px solid rgba(148,163,184,0.20); border-radius: 20px; gridline-color: rgba(71,85,105,0.50); selection-background-color: #312E81; selection-color: #FFFFFF; outline: 0; }
QTableWidget::item { padding: 8px 10px; border-bottom: 1px solid #1F2937; color: #E2E8F0; }
QTableWidget::item:selected { background: #312E81; color: #FFFFFF; }
QTableWidget::item:hover { background: #1E1B4B; }
QGroupBox { font-weight: 650; color: #E2E8F0; border: 1px solid rgba(148,163,184,0.22); border-radius: 16px; margin-top: 0; padding: 24px 14px 14px 14px; background: rgba(17,24,39,0.78); }
QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; top: 8px; left: 12px; padding: 0; background: transparent; color: #94A3B8; }
QLabel { color: #E2E8F0; background: transparent; }
QLabel[pageTitle="true"] { color: #F8FAFC; font-size: 15pt; font-weight: 700; }
QLabel[pageSubtitle="true"] { color: #94A3B8; font-size: 9pt; font-weight: 500; padding-bottom: 4px; }
QLabel[mutedText="true"] { color: #94A3B8; }
QLabel[heroTitle="true"], QLabel[welcomeTitle="true"] { color: #FFFFFF; font-size: 16pt; font-weight: 700; }
QLabel[heroSubtitle="true"] { color: #E2E8F0; font-size: 9pt; }
QLabel[welcomeSubtitle="true"] { color: #F5D0FE; font-size: 9pt; }
QWidget#dashboardHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0F172A, stop:1 #4C1D95); border-radius: 16px; }
QWidget#welcomeHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4C1D95, stop:0.5 #7C3AED, stop:1 #DB2777); border-radius: 16px; }
QScrollArea#homeScroll { border: 0; background: transparent; }
QWidget#homeContent { background: rgba(15,23,42,0.48); border: 1px solid rgba(148,163,184,0.20); border-radius: 18px; }
QScrollArea#pageScroll { border: 0; background: transparent; }
QWidget#pageContent { background: rgba(15,23,42,0.48); border: 1px solid rgba(148,163,184,0.20); border-radius: 18px; }
QTextEdit#reportPreview { background: #111827; border: 1px solid #334155; border-radius: 12px; }
QWidget#sessionStrip { background: #111827; border: 0; border-radius: 16px; }
QLabel[sessionLabel="true"] { color: #94A3B8; font-size: 8pt; font-weight: 700; }
QLabel[roleBadge="true"] { background: #312E81; color: #DDD6FE; border-radius: 8px; padding: 4px 10px; font-weight: 700; }
QLabel[sectionHeading="true"] { color: #F8FAFC; font-size: 12.5pt; font-weight: 700; }
QWidget#guideItem { background: #111827; border: 1px solid #1F2937; border-left: 4px solid #A78BFA; border-radius: 14px; }
QLabel[guideTitle="true"] { color: #F8FAFC; font-size: 10.5pt; font-weight: 700; }
QLabel[metricValue="true"] { font-size: 26pt; font-weight: 700; color: #A78BFA; }
QLabel[statusSummary="true"] { background: #1E1B4B; border: 1px solid #4C1D95; border-radius: 12px; color: #DDD6FE; font-weight: 600; padding: 11px 14px; }
QLabel[warningBanner="true"] { background: #422006; border: 1px solid #A16207; border-radius: 12px; color: #FDE68A; font-weight: 600; padding: 9px 12px; }
QProgressBar { border: 1px solid #1F2937; border-radius: 8px; text-align: center; color: #E2E8F0; background: #0F172A; min-height: 15px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #22D3EE, stop:1 #E879F9); border-radius: 7px; }
QCheckBox { spacing: 10px; padding: 4px; color: #E2E8F0; background: transparent; font-weight: 500; }
QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid #475569; border-radius: 5px; background: #111827; }
QCheckBox::indicator:hover { border-color: #A78BFA; background: #1E1B4B; }
QCheckBox::indicator:checked { background: #A78BFA; border-color: #A78BFA; }
QCheckBox::indicator:checked:hover { background: #C4B5FD; border-color: #C4B5FD; }
QStatusBar { background: #111827; color: #CBD5E1; border-top: 1px solid #1F2937; padding: 4px 8px; font-weight: 500; }
QRadioButton { spacing: 8px; color: #CBD5E1; background: transparent; }
QStatusBar { background: #111827; color: #94A3B8; border-top: 1px solid #1F2937; }
QStatusBar::item { border: none; }
QScrollBar:vertical, QScrollBar:horizontal { background: transparent; width: 11px; height: 11px; margin: 2px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #334155; border-radius: 5px; min-height: 24px; min-width: 24px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #64748B; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QDialog { background: #111827; color: #E2E8F0; }
QFormLayout QLabel { color: #CBD5E1; background: transparent; }
QToolTip { background: #111827; color: #E2E8F0; border: 1px solid #334155; padding: 6px 8px; border-radius: 6px; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: #070B14; }
QCalendarWidget QToolButton { background: transparent; color: #ffffff; border: 0; border-radius: 4px; padding: 6px 8px; font-weight: 600; }
QCalendarWidget QToolButton:hover { background: #7C5CFC; }
QCalendarWidget QSpinBox { background: transparent; color: #ffffff; border: 0; padding: 3px; }
QCalendarWidget QAbstractItemView { background: #111827; alternate-background-color: #0F172A; color: #E2E8F0; selection-background-color: #7C5CFC; selection-color: #ffffff; outline: 0; }
"""

def apply_app_theme(app, theme_name):
    theme_name = (theme_name or "day").lower()
    if theme_name in ("night", "dark"):
        app.setStyleSheet(dark_stylesheet())
        return "night"
    if theme_name == "ocean":
        app.setStyleSheet(ocean_stylesheet())
        return "ocean"
    if theme_name == "sunset":
        app.setStyleSheet(sunset_stylesheet())
        return "sunset"
    app.setStyleSheet(light_stylesheet())
    return "day"

def ocean_stylesheet():
    return light_stylesheet().replace("#7C5CFC", "#0EA5E9").replace("#6D28D9", "#0284C7").replace("#15233F", "#0C4A6E").replace("#E2E8F0", "#E0F2FE").replace("#F1F5F9", "#F0F9FF")

def sunset_stylesheet():
    return light_stylesheet().replace("#7C5CFC", "#F97316").replace("#6D28D9", "#EA580C").replace("#15233F", "#7C2D12").replace("#E2E8F0", "#FFF7ED").replace("#F1F5F9", "#FFEDD5")


def resource_path(relative_path):
    """Resolve bundled assets in source and PyInstaller builds."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_path / relative_path)


def main():
    app=QApplication(sys.argv); app.setStyle("Fusion")
    QFontDatabase.addApplicationFont(resource_path("assets/DejaVuSans.ttf"))
    QFontDatabase.addApplicationFont(resource_path("assets/DejaVuSans-Bold.ttf"))
    app.setFont(QFont("DejaVu Sans", 9))
    app.setWindowIcon(QIcon(resource_path("assets/raw_strength_icon.ico")))
    apply_app_theme(app, "day")

    try:
        db=Database()
        seed_initial_audit(db)
    except Exception as exc:
        QMessageBox.critical(None, APP_NAME, f"Startup failed:\n{exc}")
        return 1
    if db.conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] == 0:
        setup_dialog = AccountSetupDialog(db)
        if setup_dialog.exec() != QDialog.Accepted:
            return 0
    login=LoginDialog(db)
    if login.exec()!=QDialog.Accepted: return 0
    if db.get_setting("initial_audit_2026_10_09_imported") == "1" and db.get_setting("initial_audit_notice_shown") != "1":
        info(login, "Historical audit imported: 8 employees and 36 task records for 09-10-2026. To review them, select 2026-10-09 in All Tasks, Employee Task Tracker, or Print Center. Today's screens may be empty until you add today's tasks.")
        db.set_setting("initial_audit_notice_shown", "1")
    win=MainWindow(db, login.user); win.apply_theme(); win.show()
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
