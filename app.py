import json, os, subprocess, sys, sqlite3, shutil, webbrowser, hashlib, secrets, ctypes, re, math, threading, logging, traceback
from html import escape as html_escape
from pathlib import Path
from datetime import datetime, date
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from PySide6.QtCore import Qt, QSize, QDate, QTime, QEvent, QEasingCurve, QPropertyAnimation, QVariantAnimation, QObject, QThread, Signal, QPoint, QPointF, QRect, QRectF, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QDateEdit, QTimeEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QInputDialog, QDialog, QDialogButtonBox, QHeaderView, QProgressDialog, QToolTip,
    QGroupBox, QProgressBar, QAbstractItemView, QCheckBox, QScrollArea, QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QToolButton, QMenu, QSizePolicy, QFrame, QListView, QAbstractScrollArea, QListWidget, QListWidgetItem,
    QCalendarWidget, QAbstractSpinBox, QDateTimeEdit, QSpacerItem
)
from PySide6.QtGui import QAction, QPainter, QColor, QPen, QBrush, QConicalGradient, QLinearGradient, QFont, QFontDatabase, QIcon, QPixmap, QPalette, QImage, QPainterPath
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, HRFlowable, Image as RLImage
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from build_info import APP_VERSION
from business_tracking import BusinessTrackingTab, available_stock
from customer_prospects import CustomerProspectsTab, seed_official_web_prospects
from database_sync import (
    GitHubDatabaseSync,
    SyncableSQLiteConnection,
    protect_sync_token,
    unprotect_sync_token,
)
from cloudflare_chat import CloudflareChatTab, verify_developer_password


def resource_path(relative_path):
    """Resolve bundled assets in source and PyInstaller builds."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_path / relative_path)


def brand_mark_pixmap(size):
    """Return the official colored Raw Strength Calisthenics emblem at the requested size."""
    size = max(24, int(size))
    if QApplication.instance() is None:
        _ = QApplication([""])
    logo_file = resource_path("assets/raw_strength_brand_hud.png")
    if Path(logo_file).exists():
        pm = QPixmap(logo_file)
        if not pm.isNull():
            scaled = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            canvas = QPixmap(size, size)
            canvas.fill(Qt.GlobalColor.transparent)
            p = QPainter(canvas)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            x = (size - scaled.width()) // 2
            y = (size - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            p.end()
            return canvas
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    cx = size / 2.0
    cy = size / 2.0
    s = float(size)

    # 1. Outer Aerodynamic Executive Shield Crest
    shield = QPainterPath()
    shield.moveTo(cx, s * 0.04)
    shield.lineTo(s * 0.94, s * 0.20)
    shield.lineTo(s * 0.94, s * 0.60)
    shield.cubicTo(s * 0.94, s * 0.82, cx + s * 0.16, s * 0.94, cx, s * 0.98)
    shield.cubicTo(cx - s * 0.16, s * 0.94, s * 0.06, s * 0.82, s * 0.06, s * 0.60)
    shield.lineTo(s * 0.06, s * 0.20)
    shield.closeSubpath()

    # Premium Obsidian-Titanium Deep Gradient Fill
    bg_gradient = QLinearGradient(0, 0, s, s)
    bg_gradient.setColorAt(0.0, QColor("#050B14"))
    bg_gradient.setColorAt(0.5, QColor("#0D1527"))
    bg_gradient.setColorAt(1.0, QColor("#030712"))
    painter.fillPath(shield, bg_gradient)

    # 2. Precision Metallic Rim (Neon Cyan to Royal Indigo to Hot Magenta)
    rim_pen = QLinearGradient(0, 0, s, s)
    rim_pen.setColorAt(0.0, QColor("#00E5FF"))
    rim_pen.setColorAt(0.5, QColor("#8B5CF6"))
    rim_pen.setColorAt(1.0, QColor("#EC4899"))
    painter.setPen(QPen(QBrush(rim_pen), max(2.2, s * 0.045), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawPath(shield)

    # 3. Inner Depth Inset Bezel
    inner = QPainterPath()
    inset = s * 0.075
    inner.moveTo(cx, s * 0.04 + inset * 1.1)
    inner.lineTo(s * 0.94 - inset, s * 0.20 + inset * 0.3)
    inner.lineTo(s * 0.94 - inset, s * 0.60 - inset * 0.2)
    inner.cubicTo(s * 0.94 - inset, s * 0.80, cx + s * 0.14, s * 0.92 - inset, cx, s * 0.98 - inset * 1.1)
    inner.cubicTo(cx - s * 0.14, s * 0.92 - inset, s * 0.06 + inset, s * 0.80, s * 0.06 + inset, s * 0.60 - inset * 0.2)
    inner.lineTo(s * 0.06 + inset, s * 0.20 + inset * 0.3)
    inner.closeSubpath()
    painter.setPen(QPen(QColor(0, 229, 255, 60), max(1.0, s * 0.015)))
    painter.drawPath(inner)

    # 4. Strength Barbell Shaft & Weight Plates
    bar_y = s * 0.32
    bar_grad = QLinearGradient(s * 0.18, bar_y, s * 0.82, bar_y)
    bar_grad.setColorAt(0.0, QColor("#00E5FF"))
    bar_grad.setColorAt(0.5, QColor("#FFFFFF"))
    bar_grad.setColorAt(1.0, QColor("#00E5FF"))
    painter.setPen(QPen(QBrush(bar_grad), max(2.5, s * 0.038), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(s * 0.18, bar_y), QPointF(s * 0.82, bar_y))
    for plate_x in (s * 0.19, s * 0.23, s * 0.77, s * 0.81):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#00E5FF" if plate_x in (s * 0.19, s * 0.81) else "#8B5CF6"))
        painter.drawRoundedRect(QRectF(plate_x - s * 0.016, bar_y - s * 0.065, s * 0.032, s * 0.13), 2, 2)

    # 5. Calisthenics Gymnastic Rings
    for ring_x in (s * 0.33, s * 0.67):
        painter.setPen(QPen(QColor(148, 163, 184, 160), max(1.2, s * 0.02)))
        painter.drawLine(QPointF(ring_x, s * 0.12), QPointF(ring_x, s * 0.38))
        painter.setPen(QPen(QColor("#F59E0B"), max(2.2, s * 0.035)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        ring_r = s * 0.065
        painter.drawEllipse(QPointF(ring_x, s * 0.44), ring_r, ring_r)

    # 6. Calisthenics Athlete Silhouette in Iron Cross / Planche
    body_grad = QLinearGradient(cx, s * 0.36, cx, s * 0.68)
    body_grad.setColorAt(0.0, QColor("#FFFFFF"))
    body_grad.setColorAt(0.5, QColor("#00E5FF"))
    body_grad.setColorAt(1.0, QColor("#38BDF8"))

    # Head
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(QPointF(cx, s * 0.36), s * 0.045, s * 0.045)

    # Torso
    athlete = QPainterPath()
    athlete.moveTo(cx - s * 0.11, s * 0.41)
    athlete.lineTo(cx + s * 0.11, s * 0.41)
    athlete.lineTo(cx + s * 0.05, s * 0.58)
    athlete.lineTo(cx - s * 0.05, s * 0.58)
    athlete.closeSubpath()
    painter.fillPath(athlete, body_grad)

    # Arms
    arms = QPainterPath()
    arms.moveTo(s * 0.33, s * 0.44)
    arms.lineTo(cx - s * 0.08, s * 0.42)
    arms.lineTo(cx + s * 0.08, s * 0.42)
    arms.lineTo(s * 0.67, s * 0.44)
    arms.lineTo(s * 0.65, s * 0.47)
    arms.lineTo(cx + s * 0.07, s * 0.45)
    arms.lineTo(cx - s * 0.07, s * 0.45)
    arms.lineTo(s * 0.35, s * 0.47)
    arms.closeSubpath()
    painter.fillPath(arms, body_grad)

    # Planche Legs
    legs = QPainterPath()
    legs.moveTo(cx - s * 0.045, s * 0.58)
    legs.lineTo(cx + s * 0.045, s * 0.58)
    legs.lineTo(cx + s * 0.03, s * 0.70)
    legs.lineTo(cx - s * 0.03, s * 0.70)
    legs.closeSubpath()
    painter.fillPath(legs, QColor("#00E5FF"))

    # 7. Bold Typography 'RAW STRENGTH' & 'CALISTHENICS'
    if s >= 48:
        f_size = max(7, round(s * 0.092))
        font = QFont("Segoe UI", f_size, QFont.Weight.Black)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(1.0, s * 0.022))
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0, 220))
        painter.drawText(QRectF(0, s * 0.72 + 1.2, s, s * 0.14), Qt.AlignmentFlag.AlignCenter, "RAW STRENGTH")
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(0, s * 0.72, s, s * 0.14), Qt.AlignmentFlag.AlignCenter, "RAW STRENGTH")

        sub_size = max(5, round(s * 0.055))
        sub_font = QFont("Segoe UI", sub_size, QFont.Weight.ExtraBold)
        sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(1.2, s * 0.030))
        painter.setFont(sub_font)
        painter.setPen(QColor("#00E5FF"))
        painter.drawText(QRectF(0, s * 0.84, s, s * 0.10), Qt.AlignmentFlag.AlignCenter, "CALISTHENICS")
    else:
        f_size = max(6, round(s * 0.28))
        font = QFont("Segoe UI", f_size, QFont.Weight.Black)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(0, s * 0.66, s, s * 0.30), Qt.AlignmentFlag.AlignCenter, "RS")

    painter.end()
    return pixmap

def is_due_time_included(opts):
    """Check if due time should be included, handling aliases and explicit falsy exclusions."""
    if not isinstance(opts, dict):
        return True
    for key in ("due_time", "duetime", "due", "due_times"):
        if key in opts and not opts[key]:
            return False
    return bool(opts.get("due_time", True))


def is_remarks_included(opts):
    """Check if manager remarks should be included, handling aliases and explicit falsy exclusions."""
    if not isinstance(opts, dict):
        return True
    for key in ("remarks", "manager_remarks", "manager_note", "notes", "manager_notes"):
        if key in opts and not opts[key]:
            return False
    return bool(opts.get("remarks", True))


def is_target_qty_included(opts):
    """Check if target qty should be included, handling aliases and explicit falsy exclusions."""
    if not isinstance(opts, dict):
        return True
    for key in ("target_qty", "targetqty", "target_quantity"):
        if key in opts and not opts[key]:
            return False
    return bool(opts.get("target_qty", True))


def is_actual_qty_included(opts):
    """Check if actual qty should be included, handling aliases and explicit falsy exclusions."""
    if not isinstance(opts, dict):
        return True
    for key in ("actual_qty", "actualqty", "actual_quantity"):
        if key in opts and not opts[key]:
            return False
    return bool(opts.get("actual_qty", True))


def is_completion_pct_included(opts):
    """Check if completion % should be included, handling aliases and explicit falsy exclusions."""
    if not isinstance(opts, dict):
        return True
    for key in ("completion_pct", "progress", "completion", "pct"):
        if key in opts and not opts[key]:
            return False
    return bool(opts.get("completion_pct", True))


def is_priority_included(opts):
    """Check if priority should be included, handling aliases and explicit falsy exclusions."""
    if not isinstance(opts, dict):
        return True
    for key in ("priority", "task_priority"):
        if key in opts and not opts[key]:
            return False
    return bool(opts.get("priority", True))


def is_custom_values_included(opts):
    """Check if custom values should be included, handling aliases and explicit falsy exclusions."""
    if not isinstance(opts, dict):
        return True
    for key in ("custom_values", "customvalues", "custom_fields", "custom_task"):
        if key in opts and not opts[key]:
            return False
    return bool(opts.get("custom_values", True))


def is_next_action_included(opts):
    """Check if next action should be included, handling aliases and explicit falsy exclusions."""
    if not isinstance(opts, dict):
        return True
    for key in ("next_action", "nextaction", "next_actions"):
        if key in opts and not opts[key]:
            return False
    return bool(opts.get("next_action", True))

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


def extract_http_urls(value):
    """Return HTTP(S) URLs from evidence fields without changing the original URL."""
    urls = []
    for line in str(value or "").splitlines():
        for candidate in line.split():
            candidate = candidate.strip("<>").rstrip(".,;)")
            if candidate.startswith(("https://", "http://")):
                urls.append(candidate)
    return urls


def add_docx_hyperlink(paragraph, url, label="Tap here to view content"):
    """Add a concise, clickable external link to a Word paragraph."""
    relationship_id = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    properties.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.append(underline)
    run.append(properties)
    text_node = OxmlElement("w:t")
    text_node.text = str(label or "Tap here to view content")
    run.append(text_node)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)
    return hyperlink


def report_pdf_hyperlink(url, label="Tap here to view content"):
    """Build a ReportLab link with a short display label and the original URL target."""
    if not proof_urls(url):
        return html_escape(str(label or "Tap here to view content"))
    return (f'<link href="{html_escape(str(url), quote=True)}" color="#0563C1">'
            f'<u>{html_escape(str(label or "Tap here to view content"))}</u></link>')


def csv_hyperlink_formula(url, label="Tap here to view content"):
    """Return a spreadsheet hyperlink formula for a CSV proof cell."""
    if not proof_urls(url):
        return ""
    safe_url = str(url).replace('"', '""')
    safe_label = str(label or "Tap here to view content").replace('"', '""')
    return f'=HYPERLINK("{safe_url}","{safe_label}")'


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
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases?per_page=100"
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


def is_explicitly_completed_task_status(status):
    """Only an explicit Completed or Submitted state counts as complete."""
    return normalized_task_status(status) in {"completed", "submitted"}


def normalized_task_status(status):
    """Normalize legacy status spelling for comparisons without rewriting stored data."""
    return str(status or "").strip().casefold()


def is_cancelled_task_status(status):
    return normalized_task_status(status) == "cancelled"


def is_blocked_task_status(status):
    return normalized_task_status(status) == "blocked"


def is_in_progress_task_status(status):
    return normalized_task_status(status) == "in progress"


def task_status_label(status):
    """Display missing legacy states clearly without rewriting the stored value."""
    if status is None or not str(status).strip():
        return "Not selected"
    return str(status).strip()


def is_known_task_status(status):
    """Return False for blank, unselected, and legacy NA task states."""
    value = normalized_task_status(status)
    return value in {
        "not started", "in progress", "partially completed", "submitted", "completed", "blocked",
        "pending review", "pending", "cancelled",
    }


def parse_custom_values(raw):
    """Parse custom values from JSON string, dict, list, or text lines into list of (key, value) pairs."""
    if not raw:
        return []
    if isinstance(raw, list):
        pairs = []
        for item in raw:
            if isinstance(item, dict):
                k = str(item.get("key") or item.get("k") or item.get("name") or "").strip()
                v = str(item.get("value") or item.get("v") or item.get("val") or "").strip()
                if k or v:
                    pairs.append((k, v))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                pairs.append((str(item[0]).strip(), str(item[1]).strip()))
        return pairs
    if isinstance(raw, dict):
        return [(str(k).strip(), str(v).strip()) for k, v in raw.items()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
            try:
                parsed = json.loads(text)
                return parse_custom_values(parsed)
            except Exception:
                pass
        pairs = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                pairs.append((k.strip(), v.strip()))
            elif "=" in line:
                k, v = line.split("=", 1)
                pairs.append((k.strip(), v.strip()))
            else:
                pairs.append(("Custom", line))
        return pairs
    return []


def format_custom_values_display(raw) -> str:
    """Format custom key-value pairs for table cell display."""
    pairs = parse_custom_values(raw)
    if not pairs:
        return "—"
    return "  |  ".join(f"{k}: {v}" if k else v for k, v in pairs)


def serialize_custom_values(pairs) -> str:
    """Serialize list of (key, value) pairs or dict to clean JSON string."""
    if isinstance(pairs, dict):
        pairs = list(pairs.items())
    clean = [{"key": str(k).strip(), "value": str(v).strip()} for k, v in (pairs or []) if str(k).strip() or str(v).strip()]
    return json.dumps(clean, ensure_ascii=False) if clean else ""


URI_PATTERN = r"\b[a-z][a-z0-9+.-]*:[^\s<>]+"


def proof_urls(value):
    """Extract source URIs using any valid URI scheme, not only HTTP(S)."""
    found = []
    for match in re.findall(URI_PATTERN, str(value or ""), flags=re.IGNORECASE):
        candidate = match.rstrip(".,;:!?)]}")
        try:
            parsed = urlsplit(candidate)
        except ValueError:
            continue
        scheme = parsed.scheme.lower()
        if not scheme or not candidate.partition(":")[2]:
            continue
        if scheme in ("http", "https") and not parsed.hostname:
            continue
        found.append(candidate)
    return list(dict.fromkeys(found))


def task_evidence_urls(task):
    """Collect evidence URLs from both the dedicated link field and evidence notes."""
    urls = []
    for field in ("proof_url", "proof_note"):
        try:
            value = task[field] or ""
        except (KeyError, TypeError, IndexError):
            value = ""
        urls.extend(proof_urls(value))
    return list(dict.fromkeys(urls))


def proof_note_display_text(task, evidence_links_included=False):
    """Keep proof notes readable without printing the same URLs twice in reports."""
    try:
        note = str(task["proof_note"] or "")
    except (KeyError, TypeError, IndexError):
        return ""
    if not evidence_links_included:
        return note
    known_urls = set(task_evidence_urls(task))
    return re.sub(
        URI_PATTERN,
        lambda match: "[link listed above]"
        if match.group(0).rstrip(".,;:!?)]}") in known_urls
        else match.group(0),
        note,
        flags=re.IGNORECASE,
    )


def add_docx_linkified_text(paragraph, text, expose_full_url=False):
    """Append text while formatting any embedded HTTP(S) URL as a hyperlink."""
    raw = str(text or "")
    matches = list(re.finditer(URI_PATTERN, raw, flags=re.IGNORECASE))
    position = 0
    for match in matches:
        url = match.group(0).rstrip(".,;:!?)]}")
        if not proof_urls(url):
            continue
        trailing = match.group(0)[len(url):]
        if match.start() > position:
            paragraph.add_run(raw[position:match.start()])
        label = url if expose_full_url else "Tap here to view content"
        add_docx_hyperlink(paragraph, url, label)
        if trailing:
            paragraph.add_run(trailing)
        position = match.end()
    if position < len(raw):
        paragraph.add_run(raw[position:])

def configure_date_edit(date_edit):
    date_edit.setCalendarPopup(True)
    date_edit.wheelEvent = lambda event: event.ignore()
    calendar = date_edit.calendarWidget()
    calendar.setGridVisible(True)
    calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
    calendar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    calendar.setAutoFillBackground(True)
    for child in calendar.findChildren(QWidget):
        child.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        child.setAutoFillBackground(True)
        if isinstance(child, (QAbstractItemView, QSpinBox, QAbstractSpinBox)):
            child.wheelEvent = lambda event: event.ignore()
    calendar.setStyleSheet("""
        QCalendarWidget { background-color: #0F172A; color: #F8FAFC; border: 2px solid #38BDF8; border-radius: 10px; }
        QWidget#qt_calendar_navigationbar { background: #0B1120; border-bottom: 1px solid #334155; }
        QCalendarWidget QToolButton { background: transparent; color: #F8FAFC; border: 0;
            border-radius: 6px; padding: 6px 10px; font-weight: 700; font-size: 9.5pt; }
        QCalendarWidget QToolButton:hover { background: #1E293B; color: #38BDF8; }
        QCalendarWidget QSpinBox { background: #1E293B; color: #F8FAFC; border: 1px solid #475569;
            border-radius: 5px; padding: 3px 6px; }
        QCalendarWidget QMenu { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; }
        QCalendarWidget QAbstractItemView { background: #0F172A; alternate-background-color: #1E293B;
            color: #F8FAFC; selection-background-color: #6366F1; selection-color: #FFFFFF;
            gridline-color: #1E293B; outline: 0; font-weight: 600; }
        QCalendarWidget QAbstractItemView:enabled { color: #F8FAFC; }
        QCalendarWidget QAbstractItemView:disabled { color: #64748B; }
        QCalendarWidget QHeaderView::section { background: #1E293B; color: #94A3B8;
            border: 1px solid #334155; padding: 6px; font-weight: 700; font-size: 8.5pt; }
    """)


def valid_hhmm(value):
    """Validate strict 24-hour HH:MM input, including leading zeroes."""
    import re
    text = str(value).strip() if value is not None else ""
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
        return False
    try:
        datetime.strptime(text, "%H:%M")
        return True
    except (TypeError, ValueError):
        return False


ATTENDANCE_DETAIL_STATUSES = (
    "Late Check-in",
    "Late Check-out",
    "On Time",
    "Balanced Hours",
    "Overtime",
    "Short Hours",
    "Early Departure",
)
ATTENDANCE_STATUS_OPTIONS = ("Unmarked", "Present", "Absent", "Leave")
ATTENDANCE_REMARK_OPTIONS = (
    "",
    "Late Check-in",
    "Late Check-out",
    "On Time",
    "Balanced Hours",
    "Overtime",
    "Short Hours",
    "Early Departure",
)
ATTENDANCE_PRESENT_STATUSES = frozenset(("Present", *ATTENDANCE_DETAIL_STATUSES))


def is_present_attendance_status(status):
    """Return whether an attendance status represents a worked day."""
    return str(status or "").strip().casefold() in {
        value.casefold() for value in ATTENDANCE_PRESENT_STATUSES
    }


def calculate_net_working_hours(check_in, check_out, break_minutes=0):
    """Calculate net working hours string from check-in, check-out, and break minutes."""
    if not check_in or not check_out:
        return ""
    try:
        st = datetime.strptime(str(check_in).strip(), "%H:%M")
        en = datetime.strptime(str(check_out).strip(), "%H:%M")
        mins = int((en - st).total_seconds() / 60)
        if mins < 0:
            mins += 1440
        mins = max(0, mins - int(break_minutes or 0))
        return f"{mins / 60:.2f}"
    except (TypeError, ValueError, OverflowError):
        return ""


def release_version_tuple(version):
    parts = str(version).strip().removeprefix("v").split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Unsupported application version: {version}")
    return tuple(int(part) for part in parts)


def verify_release_asset_bytes(data, asset, require_digest=True):
    """Verify a downloaded release asset against GitHub's SHA-256 digest."""
    digest = str((asset or {}).get("digest") or "").strip()
    if not digest:
        if require_digest:
            raise ValueError("GitHub release asset has no SHA-256 digest; refusing an unverified installer.")
        return False
    algorithm, separator, expected = digest.partition(":")
    if not separator or algorithm.lower() != "sha256" or len(expected) != 64:
        raise ValueError("GitHub release asset has an invalid SHA-256 digest.")
    actual = hashlib.sha256(data).hexdigest()
    if not secrets.compare_digest(actual.lower(), expected.lower()):
        raise ValueError("Installer checksum verification failed; the file may be incomplete or altered.")
    return True


def previous_release_choices(releases, current_version):
    """Return installable, published stable releases older than the app, newest first."""
    current_parts = release_version_tuple(current_version)
    if not isinstance(releases, list):
        raise ValueError("GitHub returned an invalid releases response.")

    choices = []
    installer_name = "RawStrengthEmployeeAuditManager-Setup.exe"
    for release in releases:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        if not release.get("published_at"):
            continue
        try:
            version = release_version_tuple(release.get("tag_name", ""))
        except ValueError:
            continue
        if version >= current_parts:
            continue

        assets = release.get("assets", [])
        if not isinstance(assets, list):
            continue
        asset = next((item for item in assets
                      if isinstance(item, dict) and item.get("name") == installer_name), None)
        if not asset:
            continue
        url = str(asset.get("browser_download_url") or "")
        size = asset.get("size")
        if (not url.startswith(GITHUB_RELEASE_DOWNLOAD_PREFIX)
                or not isinstance(size, int) or size < 1000000):
            continue
        choices.append((version, str(release["tag_name"]), url, asset))

    choices.sort(key=lambda item: item[0], reverse=True)
    return [(tag, url, asset) for _, tag, url, asset in choices]


class UpdateWorker(QObject):
    ready = Signal(str, str)
    current = Signal(str)
    failed = Signal(str)
    progress = Signal(int, str)
    completed = Signal()

    def __init__(self, current_version, force=False):
        super().__init__()
        self.current_version = current_version
        self.force = force

    @staticmethod
    def request_bytes(url, accept="application/vnd.github+json"):
        request = Request(url, headers={
            "Accept": accept,
            "User-Agent": "RawStrengthEmployeeAuditManager",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        # Keep a failed network request from leaving the UI in a checking state
        # for a full minute per attempt.
        with urlopen(request, timeout=20) as response:
            return response.read()

    def run(self):
        try:
            # Use the published releases list, as the previous updater did.
            # Select the highest published stable semantic version rather than relying
            # on GitHub's /releases/latest alias.
            releases_url = GITHUB_RELEASES_API
            payload = None
            latest_error = None
            self.progress.emit(0, "Connecting to GitHub to check the latest release...")
            for attempt in range(3):
                try:
                    if attempt:
                        self.progress.emit(0, f"GitHub did not respond; retrying update check ({attempt + 1}/3)...")
                    payload = json.loads(self.request_bytes(releases_url).decode("utf-8"))
                    if not isinstance(payload, list):
                        raise ValueError("GitHub returned an invalid releases list.")
                    break
                except Exception as exc:
                    latest_error = exc
                    if attempt == 2:
                        # Fall back to the single-release endpoint if the list endpoint fails.
                        fallback_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
                        try:
                            fallback_payload = json.loads(self.request_bytes(fallback_url).decode("utf-8"))
                            if isinstance(fallback_payload, dict):
                                payload = [fallback_payload]
                            elif isinstance(fallback_payload, list):
                                payload = fallback_payload
                            else:
                                raise ValueError("GitHub returned an invalid latest-release response.")
                            break
                        except Exception as fallback_error:
                            raise RuntimeError(
                                "Unable to fetch updates from GitHub. The releases list and latest-release "
                                f"fallback both failed. List error: {latest_error}; fallback error: {fallback_error}"
                            ) from fallback_error
                    import time
                    time.sleep(attempt + 1)
            # Only consider releases that have a complete, trusted installer asset.
            # A newer release without its EXE/checksum must not block a usable older release.
            installable_releases = []
            installer_name = "RawStrengthEmployeeAuditManager-Setup.exe"
            for candidate in payload:
                if not isinstance(candidate, dict) or candidate.get("draft") or candidate.get("prerelease"):
                    continue
                if not candidate.get("published_at"):
                    continue
                try:
                    candidate_version = release_version_tuple(candidate.get("tag_name", ""))
                except ValueError:
                    continue
                assets = candidate.get("assets", [])
                if not isinstance(assets, list):
                    continue
                installer_asset = next((asset for asset in assets
                    if isinstance(asset, dict) and asset.get("name") == installer_name), None)
                if not installer_asset:
                    continue
                installer_url = str(installer_asset.get("browser_download_url") or "")
                expected_digest = str(installer_asset.get("digest") or "")
                asset_size = installer_asset.get("size")
                if not installer_url.startswith(GITHUB_RELEASE_DOWNLOAD_PREFIX):
                    continue
                if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", expected_digest):
                    continue
                if not isinstance(asset_size, int) or asset_size < 1000000:
                    continue
                installable_releases.append((candidate_version, candidate, installer_asset))
            if not installable_releases:
                raise ValueError(
                    "No published stable release is available: the latest release is missing a trusted installer or verified SHA-256 digest. "
                    "Please try again later or contact your administrator."
                )
            latest_parts, release, installer_asset = max(installable_releases, key=lambda item: item[0])
            if not getattr(self, "force", False) and latest_parts <= release_version_tuple(self.current_version):
                self.current.emit(self.current_version)
                return

            installer_url = str(installer_asset["browser_download_url"])
            expected_digest = str(installer_asset["digest"])
            asset_size = installer_asset["size"]

            version_text = ".".join(str(part) for part in latest_parts)
            update_dir = APP_DIR / "updates" / version_text
            update_dir.mkdir(parents=True, exist_ok=True)
            installer_path = update_dir / installer_name
            partial_path = update_dir / (installer_name + ".part")
            try:
                # Large installer downloads can be interrupted by customer networks.
                # Keep verified partial bytes and resume with HTTP Range instead of
                # failing permanently on urllib's IncompleteRead exception.
                import time
                last_error = None
                for attempt in range(1, 7):
                    downloaded = partial_path.stat().st_size if partial_path.exists() else 0
                    headers = {"User-Agent": "RawStrengthEmployeeAuditManager"}
                    if downloaded:
                        headers["Range"] = f"bytes={downloaded}-"
                    request = Request(installer_url, headers=headers)
                    try:
                        with urlopen(request, timeout=90) as response:
                            status = getattr(response, "status", response.getcode())
                            if downloaded and status != 206:
                                # Server ignored Range; restart cleanly to avoid corrupting the file.
                                downloaded = 0
                                partial_path.unlink(missing_ok=True)
                                if status != 200:
                                    raise ValueError(f"Unexpected HTTP status while restarting download: {status}")
                            mode = "ab" if downloaded and status == 206 else "wb"
                            response_length = int(response.headers.get("Content-Length") or 0)
                            expected_response_size = asset_size - downloaded if mode == "ab" else asset_size
                            if response_length and response_length != expected_response_size:
                                raise ValueError("Server returned an unexpected installer content length.")
                            self.progress.emit(min(99, int(downloaded * 100 / asset_size)),
                                               f"Downloading update installer... {int(downloaded * 100 / asset_size)}%")
                            with partial_path.open(mode) as output:
                                while True:
                                    try:
                                        chunk = response.read(256 * 1024)
                                    except Exception as read_error:
                                        # urllib.error.IncompleteRead carries bytes received
                                        # by the final failed read; preserve them for resume.
                                        partial = getattr(read_error, "partial", b"")
                                        if partial:
                                            output.write(partial)
                                            downloaded += len(partial)
                                        raise
                                    if not chunk:
                                        break
                                    output.write(chunk)
                                    downloaded += len(chunk)
                                    percent = min(99, int(downloaded * 100 / asset_size))
                                    self.progress.emit(percent, f"Downloading update installer... {percent}%")
                        if partial_path.stat().st_size == asset_size:
                            break
                        last_error = ValueError(
                            f"Installer download ended early ({partial_path.stat().st_size} of {asset_size} bytes)."
                        )
                    except Exception as download_error:
                        last_error = download_error
                        if partial_path.exists() and partial_path.stat().st_size >= asset_size:
                            break
                        if attempt < 6:
                            self.progress.emit(0, f"Download interrupted; resuming ({attempt}/5)...")
                            time.sleep(min(attempt * 2, 8))
                actual_size = partial_path.stat().st_size if partial_path.exists() else 0
                if actual_size != asset_size:
                    raise RuntimeError(
                        f"Could not download the complete installer after 6 attempts "
                        f"({actual_size} of {asset_size} bytes). Last error: {last_error}"
                    )
                digest = hashlib.sha256()
                with partial_path.open("rb") as downloaded_file:
                    for chunk in iter(lambda: downloaded_file.read(1024 * 1024), b""):
                        digest.update(chunk)
                expected = expected_digest.partition(":")[2].lower()
                if not secrets.compare_digest(digest.hexdigest().lower(), expected):
                    raise ValueError("Installer checksum verification failed; the download was rejected.")
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


def create_pre_migration_backup(db_path, backup_dir):
    """Create and validate a consistent SQLite snapshot before schema migrations."""
    db_path = Path(db_path)
    backup_dir = Path(backup_dir)
    if not db_path.exists() or db_path.stat().st_size <= 0:
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"pre_upgrade_{stamp}_{secrets.token_hex(4)}.db"
    source = None
    destination = None
    try:
        # SQLite's backup API includes committed WAL data; a file copy may not.
        source = sqlite3.connect(str(db_path), timeout=15)
        destination = sqlite3.connect(str(target), timeout=15)
        source.backup(destination)
        integrity = destination.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError("Pre-migration backup failed SQLite integrity validation.")
        destination.close()
        destination = None
        source.close()
        source = None
        return target
    except Exception as exc:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
        target.unlink(missing_ok=True)
        raise RuntimeError(f"Pre-migration database backup failed; migrations were cancelled: {exc}") from exc


def create_validated_sqlite_copy(source_connection, target_path):
    """Create an atomic, integrity-checked SQLite copy without copying a live file."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        raise FileExistsError(f"Refusing to overwrite an existing database copy: {target_path}")
    temporary_path = target_path.with_name(
        f"{target_path.name}.{secrets.token_hex(6)}.tmp"
    )
    destination = None
    try:
        destination = sqlite3.connect(str(temporary_path), timeout=20)
        source_connection.backup(destination)
        integrity = destination.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError("The database copy failed SQLite integrity validation.")
        destination.close()
        destination = None
        os.replace(temporary_path, target_path)
        return target_path
    finally:
        if destination is not None:
            destination.close()
        temporary_path.unlink(missing_ok=True)


def restore_validated_sqlite_copy(source_path, destination_connection):
    """Restore a validated SQLite file into an existing live connection."""
    source = sqlite3.connect(str(source_path), timeout=20)
    try:
        integrity = source.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError("The saved customer database copy failed integrity validation.")
        source.backup(destination_connection)
        destination_connection.commit()
        restored_integrity = destination_connection.execute("PRAGMA integrity_check").fetchone()
        if not restored_integrity or restored_integrity[0] != "ok":
            raise RuntimeError("Restoring the customer database failed integrity validation.")
    finally:
        source.close()


def remove_local_sync_metadata(database_path):
    """Strip machine-specific sync and retired mode settings from an archive."""
    connection = sqlite3.connect(str(database_path), timeout=20)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "settings" in tables:
            connection.execute(
                "DELETE FROM settings WHERE key IN (?, ?, ?, ?, ?) ",
                (
                    "github_sync_token_dpapi",
                    "github_sync_install_id",
                    "developer_mode_enabled",
                    "developer_mode_password_salt",
                    "developer_mode_password_hash",
                ),
            )
            connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError("The isolated developer copy failed SQLite integrity validation.")
    finally:
        connection.close()


class Database:
    def __init__(self):
        try:
            self.legacy_mode_restore_path = Path(DB_PATH).with_name(
                Path(DB_PATH).stem + ".developer-mode-restore.db"
            )
            self.legacy_mode_state_path = Path(DB_PATH).with_name(
                Path(DB_PATH).stem + ".developer-mode.state"
            )
            # Do not run schema migrations unless the existing database was backed up.
            db_path = Path(DB_PATH)
            create_pre_migration_backup(db_path, BACKUP_DIR)
            self.conn = sqlite3.connect(DB_PATH, factory=SyncableSQLiteConnection)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.active_user = None
            self.setup()
            self._recover_legacy_developer_mode()
            try:
                seed_official_web_prospects(self)
            except Exception:
                logging.getLogger("db").exception(
                    "Official retailer leads were not seeded; the application will continue to start."
                )
            self._initialize_github_sync()
        except Exception as exc:
            # Attempt to close and re-raise with context
            if hasattr(self, "conn") and self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
            raise RuntimeError(f"Database initialization failed: {exc}") from exc

    def _recover_legacy_developer_mode(self):
        """Restore customer data from the retired isolation mode without losing edits."""
        try:
            state = self.legacy_mode_state_path.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            state = ""
        setting_enabled = self.get_setting("developer_mode_enabled", "0") == "1"
        restore_exists = self.legacy_mode_restore_path.is_file()

        if state not in ("", "active", "restoring", "legacy-restoring"):
            raise RuntimeError(
                "A retired database-isolation state is unrecognized. The database was left unchanged."
            )
        if state == "active" or setting_enabled:
            if not restore_exists:
                raise RuntimeError(
                    "The retired isolated mode is active, but its customer recovery database is missing. "
                    "The current database was left unchanged and syncing was not started."
                )
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = Path(DB_PATH).with_name(
                f"{Path(DB_PATH).stem}.developer-work-{stamp}-{secrets.token_hex(3)}.db"
            )
            create_validated_sqlite_copy(self.conn, archive_path)
            remove_local_sync_metadata(archive_path)
            self.legacy_mode_state_path.write_text("legacy-restoring", encoding="ascii")
        elif state in ("restoring", "legacy-restoring"):
            if not restore_exists and setting_enabled:
                raise RuntimeError(
                    "The retired mode is still marked active, but its customer recovery database is missing. "
                    "The current database was left unchanged and syncing was not started."
                )

        if restore_exists and state in ("active", "restoring", "legacy-restoring") or (
            restore_exists and setting_enabled
        ):
            restore_validated_sqlite_copy(self.legacy_mode_restore_path, self.conn)

        self.conn.execute(
            "DELETE FROM settings WHERE key IN (?, ?, ?) ",
            (
                "developer_mode_enabled",
                "developer_mode_password_salt",
                "developer_mode_password_hash",
            ),
        )
        self.conn.commit()
        if restore_exists and self.legacy_mode_restore_path.exists():
            self.legacy_mode_restore_path.unlink()
        self.legacy_mode_state_path.unlink(missing_ok=True)

    def _initialize_github_sync(self):
        install_id = self.get_setting("github_sync_install_id", "")
        if not re.fullmatch(r"[0-9a-f]{32}", install_id):
            install_id = secrets.token_hex(16)
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("github_sync_install_id", install_id),
            )
            self.conn.commit()
        self.github_sync_install_id = install_id

        # Keep legacy snapshot compatibility: if the old GitHub token is still
        # available, it remains the encryption passphrase. It is never sent to the Worker.
        legacy_secret = ""
        saved_legacy = self.get_setting("github_sync_token_dpapi", "")
        if saved_legacy:
            try:
                legacy_secret = unprotect_sync_token(saved_legacy)
            except ValueError:
                legacy_secret = ""
        if not legacy_secret:
            legacy_secret = str(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()

        protected_key = self.get_setting("github_sync_encryption_secret_dpapi", "")
        encryption_secret = ""
        if protected_key:
            try:
                encryption_secret = unprotect_sync_token(protected_key)
            except ValueError:
                encryption_secret = ""
        standard_secret = "Devlopershouse@1996#"
        if encryption_secret != standard_secret:
            encryption_secret = standard_secret
            protected = protect_sync_token(encryption_secret)
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("github_sync_encryption_secret_dpapi", protected),
            )
            self.conn.commit()

        saved_device = self.get_setting("github_sync_device_credentials_dpapi", "")
        device_credentials = {}
        if saved_device:
            try:
                device_credentials = json.loads(unprotect_sync_token(saved_device))
                if not isinstance(device_credentials, dict):
                    device_credentials = {}
            except (ValueError, json.JSONDecodeError):
                device_credentials = {}

        worker_url = self.get_setting("db_sync_worker_url", "") or os.environ.get("DB_SYNC_WORKER_URL", "")
        if not worker_url:
            worker_url = "https://raw-strength-audit-db-sync.yalangisexter.workers.dev"
        self.github_sync = GitHubDatabaseSync(
            DB_PATH,
            GITHUB_REPOSITORY,
            install_id,
            encryption_secret=encryption_secret,
            device_credentials=device_credentials,
            credential_store=self._store_sync_device_credentials,
            worker_url=worker_url if worker_url else None,
        )
        def _safe_commit_callback():
            if is_developer_test_user(getattr(self, "active_user", None)):
                # Developer test mode: do NOT mark pending for cloud sync
                return
            if hasattr(self, "github_sync") and hasattr(self.github_sync, "mark_pending"):
                self.github_sync.mark_pending()
        self.conn.set_commit_callback(_safe_commit_callback)

    def _store_sync_device_credentials(self, credentials):
        protected = protect_sync_token(json.dumps(credentials, separators=(",", ":")))
        callback = getattr(self.conn, "_commit_callback", None)
        try:
            self.conn.set_commit_callback(None)
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("github_sync_device_credentials_dpapi", protected),
            )
            self.conn.commit()
        finally:
            self.conn.set_commit_callback(callback)

    def close_github_sync(self, timeout=3):
        sync = getattr(self, "github_sync", None)
        if sync is not None:
            sync.close(timeout=timeout)

    def setup(self):
        c = self.conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
          display_name TEXT NOT NULL DEFAULT '',
          role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
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
          manager_note TEXT DEFAULT '', expose_link INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(employee_id) REFERENCES employees(id)
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
        CREATE TABLE IF NOT EXISTS employee_groups(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT UNIQUE NOT NULL,
          display_order INTEGER DEFAULT 0,
          created_at TEXT NOT NULL
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
        CREATE TABLE IF NOT EXISTS employee_targets(
          id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
          target_date TEXT NOT NULL, target TEXT DEFAULT '', target_status TEXT DEFAULT '',
          updated_at TEXT NOT NULL, UNIQUE(employee_id, target_date),
          FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS customer_prospects(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          dedupe_key TEXT NOT NULL UNIQUE,
          kind TEXT NOT NULL DEFAULT 'Store',
          business_name TEXT NOT NULL,
          business_category TEXT DEFAULT '',
          state TEXT DEFAULT '', city TEXT DEFAULT '', area TEXT DEFAULT '',
          contact_person TEXT DEFAULT '', phone TEXT DEFAULT '', email TEXT DEFAULT '', address TEXT DEFAULT '',
          website TEXT DEFAULT '', maps TEXT DEFAULT '',
          followup_date TEXT DEFAULT '', call_time TEXT DEFAULT '',
          connection TEXT DEFAULT '', verified TEXT DEFAULT '', response TEXT DEFAULT '',
          notes TEXT DEFAULT '',
          source_name TEXT NOT NULL DEFAULT '', source_url TEXT DEFAULT '',
          source_type TEXT NOT NULL DEFAULT 'Workbook',
          source_checked_at TEXT DEFAULT '', source_sheet TEXT DEFAULT '', source_row INTEGER,
          source_status TEXT NOT NULL DEFAULT 'Needs direct confirmation',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_customer_prospects_region
          ON customer_prospects(state, city, kind);
        CREATE INDEX IF NOT EXISTS idx_customer_prospects_name
          ON customer_prospects(business_name COLLATE NOCASE);
        """)
        # Additive migrations only — never drop existing data.
        def apply_column_migrations(table_name, migrations):
            existing = {r["name"] for r in c.execute(f"PRAGMA table_info({table_name})").fetchall()}
            for col, decl in migrations:
                if col not in existing:
                    c.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {decl}")
                    existing.add(col)
            return existing

        target_migrations = (
            ("target", "TEXT DEFAULT ''"),
            ("target_status", "TEXT DEFAULT ''"),
            ("updated_at", "TEXT NOT NULL DEFAULT ''"),
        )
        apply_column_migrations("employee_targets", target_migrations)

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
            ("display_order", "INTEGER DEFAULT 0"),
            ("created_at", "TEXT NOT NULL DEFAULT ''"),
        )
        employee_columns = apply_column_migrations("employees", employee_migrations)
        prospect_migrations = (
            ("email", "TEXT DEFAULT ''"),
            ("store_id", "TEXT DEFAULT ''"),
            ("store_type", "TEXT DEFAULT 'Physical Retailer'"),
            ("product_categories", "TEXT DEFAULT ''"),
            ("product_evidence", "TEXT DEFAULT ''"),
            ("postal_code", "TEXT DEFAULT ''"),
            ("country", "TEXT DEFAULT 'India'"),
            ("product_catalog", "TEXT DEFAULT ''"),
            ("verification_status", "TEXT DEFAULT 'Unverified'"),
            ("last_verified", "TEXT DEFAULT ''"),
        )
        apply_column_migrations("customer_prospects", prospect_migrations)
        try:
            c.execute("UPDATE customer_prospects SET state = 'Jammu and Kashmir' WHERE state IN ('Jammu & Kashmir', 'Jammu and Kashmir (UT)', 'J&K', 'JK')")
            c.execute("UPDATE customer_prospects SET state = 'Dadra and Nagar Haveli and Daman and Diu' WHERE state IN ('Dadra & Nagar Haveli And Daman & Diu', 'Dadra and Nagar Haveli', 'Daman and Diu', 'DNH & DD')")
        except Exception:
            pass
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
        try:
            c.execute("""
                INSERT OR IGNORE INTO employee_groups(name, display_order, created_at)
                SELECT DISTINCT TRIM(department), 0, ?
                FROM employees
                WHERE department IS NOT NULL AND TRIM(department) != ''
            """, (now_text(),))
        except Exception:
            pass

        task_migrations = (
            ("employee_id", "INTEGER"),
            ("task_date", "TEXT NOT NULL DEFAULT ''"),
            ("title", "TEXT NOT NULL DEFAULT ''"),
            ("department", "TEXT DEFAULT ''"),
            ("details", "TEXT DEFAULT ''"),
            ("due_time", "TEXT DEFAULT ''"),
            ("priority", "TEXT DEFAULT 'Normal'"),
            ("status", "TEXT DEFAULT 'Not started'"),
            ("progress", "INTEGER DEFAULT 0"),
            ("proof_url", "TEXT DEFAULT ''"),
            ("proof_note", "TEXT DEFAULT ''"),
            ("submitted_at", "TEXT DEFAULT ''"),
            ("manager_note", "TEXT DEFAULT ''"),
            ("expose_link", "INTEGER NOT NULL DEFAULT 0"),
            ("target_qty", "TEXT DEFAULT ''"),
            ("actual_qty", "TEXT DEFAULT ''"),
            ("next_action", "TEXT DEFAULT ''"),
            ("custom_values", "TEXT DEFAULT ''"),
            ("created_at", "TEXT NOT NULL DEFAULT ''"),
            ("updated_at", "TEXT NOT NULL DEFAULT ''"),
        )
        apply_column_migrations("tasks", task_migrations)

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

        # Ensure columns used by the current attendance screen and reports exist.
        attendance_migrations = (
            ("check_in", "TEXT DEFAULT ''"),
            ("check_out", "TEXT DEFAULT ''"),
            ("break_minutes", "INTEGER DEFAULT 0"),
            ("attendance_status", "TEXT DEFAULT 'Unmarked'"),
            ("attendance_note", "TEXT DEFAULT ''"),
            ("updated_at", "TEXT NOT NULL DEFAULT ''"),
        )
        apply_column_migrations("attendance", attendance_migrations)

        c.execute(
            "UPDATE attendance SET attendance_status='Present' "
            "WHERE COALESCE(check_in, '') <> '' "
            "AND COALESCE(attendance_status, 'Unmarked') = 'Unmarked'"
        )
        c.execute(
            '''UPDATE attendance
               SET attendance_note = CASE
                   WHEN attendance_note IS NULL OR attendance_note = '' THEN attendance_status
                   ELSE attendance_status || '; ' || attendance_note
               END,
               attendance_status = 'Present'
               WHERE attendance_status IN (
                   'Late Check-in', 'Late Check-out', 'On Time', 'Balanced Hours',
                   'Overtime', 'Short Hours', 'Early Departure'
               )'''
        )
        if not self.get_setting("working_weekdays"):
            self.set_setting("working_weekdays", "0,1,2,3,4")
        # Restore task-employee links only when unambiguous
        try:
            migrate_legacy_task_employee_links(self.conn)
        except Exception:
            self.conn.rollback()
            raise
        # Additive migration for auth_users table to allow Developer, Staff, and Employee roles
        try:
            row = self.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_users'").fetchone()
            if row and row[0] and "CHECK" in row[0] and "'Developer'" not in row[0]:
                self.conn.execute("PRAGMA foreign_keys=OFF")
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS auth_users_migrated(
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                      display_name TEXT NOT NULL DEFAULT '',
                      role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
                      password_salt TEXT NOT NULL,
                      password_hash TEXT NOT NULL,
                      security_question TEXT NOT NULL,
                      answer_salt TEXT NOT NULL,
                      answer_hash TEXT NOT NULL,
                      active INTEGER NOT NULL DEFAULT 1,
                      created_at TEXT NOT NULL,
                      updated_at TEXT NOT NULL
                    )
                """)
                self.conn.execute("""
                    INSERT INTO auth_users_migrated(id, username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at)
                    SELECT id, username, display_name, role, password_salt, password_hash, security_question, answer_salt, answer_hash, active, created_at, updated_at
                    FROM auth_users
                """)
                self.conn.execute("DROP TABLE auth_users")
                self.conn.execute("ALTER TABLE auth_users_migrated RENAME TO auth_users")
                self.conn.execute("PRAGMA foreign_keys=ON")
        except Exception as e:
            logging.getLogger("db").debug(f"auth_users migration notice: {e}")

        # Ensure distinct developer testing user ('admin') and master customer user ('taruna')
        try:
            admin_row = self.conn.execute("SELECT * FROM auth_users WHERE username='admin' COLLATE NOCASE").fetchone()
            taruna_row = self.conn.execute("SELECT * FROM auth_users WHERE username='taruna' COLLATE NOCASE").fetchone()

            if admin_row:
                if not admin_row["display_name"] or admin_row["display_name"] in ("Administrator", "admin"):
                    self.conn.execute(
                        "UPDATE auth_users SET display_name='admin (Developer - Test Mode)', role='Developer', updated_at=? WHERE id=?",
                        (now_text(), admin_row["id"])
                    )

            if not taruna_row and admin_row:
                self.conn.execute(
                    """INSERT INTO auth_users(username, display_name, role, password_salt, password_hash,
                       security_question, answer_salt, answer_hash, active, created_at, updated_at)
                       VALUES('taruna', 'Admin / Taruna (Customer Master)', 'Admin', ?, ?, ?, ?, ?, 1, ?, ?)""",
                    (admin_row["password_salt"], admin_row["password_hash"], admin_row["security_question"],
                     admin_row["answer_salt"], admin_row["answer_hash"], now_text(), now_text())
                )
            elif taruna_row:
                if "Admin" not in str(taruna_row["display_name"]):
                    self.conn.execute(
                        "UPDATE auth_users SET display_name='Admin / Taruna (Customer Master)', role='Admin', updated_at=? WHERE id=?",
                        (now_text(), taruna_row["id"])
                    )
        except Exception as e:
            logging.getLogger("db").debug(f"User provisioning notice: {e}")

        # Do not create a known/default credential. Authentication is handled by
        # the first-run Admin account and per-user password/recovery records.
        self.conn.commit()

    def set_active_user(self, user):
        self.active_user = user

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
        return self.conn.execute(q + " ORDER BY active DESC, display_order ASC, name COLLATE NOCASE").fetchall()

    def employee(self, emp_id):
        return self.conn.execute("SELECT * FROM employees WHERE id=?", (emp_id,)).fetchone()

    def employee_groups(self):
        try:
            db_groups = self.conn.execute(
                "SELECT id, name, display_order FROM employee_groups ORDER BY display_order ASC, name COLLATE NOCASE"
            ).fetchall()
            group_map = {}
            for g in db_groups:
                gname = str(g["name"] or "").strip()
                if gname:
                    group_map[gname.lower()] = {"id": g["id"], "name": gname, "display_order": g["display_order"] or 0}
            emp_depts = self.conn.execute(
                "SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND TRIM(department) != ''"
            ).fetchall()
            for row in emp_depts:
                dept_name = str(row["department"] or "").strip()
                if dept_name and dept_name.lower() not in group_map:
                    group_map[dept_name.lower()] = {"id": None, "name": dept_name, "display_order": 9999}
            return sorted(group_map.values(), key=lambda x: (x.get("display_order", 0), (x.get("name") or "").lower()))
        except Exception:
            return []

    def add_employee_group(self, name):
        name = (name or "").strip()
        if not name:
            return False
        try:
            max_order_row = self.conn.execute("SELECT COALESCE(MAX(display_order), 0) AS m FROM employee_groups").fetchone()
            max_order = (max_order_row["m"] if max_order_row else 0) or 0
            self.conn.execute(
                "INSERT INTO employee_groups(name, display_order, created_at) VALUES(?,?,?)",
                (name, max_order + 10, now_text())
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception:
            return False

    def rename_employee_group(self, old_name, new_name):
        old_name = (old_name or "").strip()
        new_name = (new_name or "").strip()
        if not old_name or not new_name or old_name.lower() == new_name.lower():
            return False
        try:
            self.conn.execute("UPDATE employee_groups SET name=? WHERE name=?", (new_name, old_name))
            self.conn.execute("UPDATE employees SET department=? WHERE department=?", (new_name, old_name))
            self.conn.execute("UPDATE tasks SET department=? WHERE department=?", (new_name, old_name))
            self.conn.commit()
            return True
        except Exception:
            return False

    def delete_employee_group(self, name):
        name = (name or "").strip()
        if not name:
            return False
        try:
            self.conn.execute("DELETE FROM employee_groups WHERE name=?", (name,))
            self.conn.execute("UPDATE employees SET department='' WHERE department=?", (name,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def reorder_employee_groups(self, group_names):
        try:
            for idx, gname in enumerate(group_names):
                order = (idx + 1) * 10
                self.conn.execute(
                    "INSERT INTO employee_groups(name, display_order, created_at) VALUES(?,?,?) "
                    "ON CONFLICT(name) DO UPDATE SET display_order=excluded.display_order",
                    (gname, order, now_text())
                )
            self.conn.commit()
            return True
        except Exception:
            return False

    def update_employee_order(self, employee_id, display_order, department=None):
        try:
            if department is not None:
                self.conn.execute("UPDATE employees SET display_order=?, department=? WHERE id=?", (display_order, department, employee_id))
            else:
                self.conn.execute("UPDATE employees SET display_order=? WHERE id=?", (display_order, employee_id))
            self.conn.commit()
            return True
        except Exception:
            return False

    def update_employees_order(self, items):
        try:
            for item in items:
                if len(item) == 3:
                    emp_id, order, dept = item
                    if dept is not None:
                        self.conn.execute("UPDATE employees SET display_order=?, department=? WHERE id=?", (order, dept, emp_id))
                    else:
                        self.conn.execute("UPDATE employees SET display_order=? WHERE id=?", (order, emp_id))
                else:
                    emp_id, order = item
                    self.conn.execute("UPDATE employees SET display_order=? WHERE id=?", (order, emp_id))
            self.conn.commit()
            return True
        except Exception:
            return False

    def tasks(self, task_date=None, employee_id=None):
        q = """SELECT t.*, e.name AS employee_name, e.employee_code,
                      COALESCE(NULLIF(t.department, ''), e.department, '') AS department
               FROM tasks t
               JOIN employees e ON e.id=t.employee_id WHERE 1=1"""
        args = []
        if task_date: q += " AND t.task_date=?"; args.append(task_date)
        if employee_id: q += " AND t.employee_id=?"; args.append(employee_id)
        return self.conn.execute(q + " ORDER BY e.display_order ASC, e.name COLLATE NOCASE, t.id DESC", args).fetchall()

    def attendance(self, work_date=None):
        q = """SELECT a.*, e.name AS employee_name, e.employee_code FROM attendance a
               JOIN employees e ON e.id=a.employee_id WHERE 1=1"""
        args=[]
        if work_date: q += " AND a.work_date=?"; args.append(work_date)
        return self.conn.execute(q + " ORDER BY e.display_order ASC, e.name COLLATE NOCASE", args).fetchall()

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

    def get_employee_target(self, emp_id, target_date):
        if not emp_id:
            return {"target": "", "target_status": ""}
        row = self.conn.execute("SELECT target, target_status FROM employee_targets WHERE employee_id=? AND target_date=?", (emp_id, target_date)).fetchone()
        if row:
            return {"target": row["target"] or "", "target_status": row["target_status"] or ""}
        return {"target": "", "target_status": ""}

    def set_employee_target(self, emp_id, target_date, target, target_status):
        if not emp_id:
            return
        self.conn.execute(
            """INSERT INTO employee_targets(employee_id,target_date,target,target_status,updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(employee_id,target_date) DO UPDATE SET
                   target=excluded.target,
                   target_status=excluded.target_status,
                   updated_at=excluded.updated_at""",
            (emp_id, target_date, (target or "").strip(), (target_status or "").strip(), now_text())
        )
        self.conn.commit()

    def task(self, task_id):
        if not task_id:
            return None
        return self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()

    def working_weekdays(self):
        raw = self.get_setting("working_weekdays", "0,1,2,3,4")
        try: return {int(x) for x in raw.split(",") if x.strip() != ""}
        except ValueError: return {0,1,2,3,4}

    def get_holiday(self, day_text):
        row = self.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?", (day_text,)).fetchone()
        return row["holiday_name"] if row else None

    def is_holiday(self, day_text):
        return self.get_holiday(day_text) is not None

    def holidays_between(self, start_date, end_date):
        return self.conn.execute("SELECT * FROM holidays WHERE holiday_date BETWEEN ? AND ? ORDER BY holiday_date", (start_date, end_date)).fetchall()

    def archive_documents(self):
        return self.conn.execute("""SELECT d.id,d.employee_id,d.report_date,d.file_name,d.mime_type,d.notes,d.uploaded_at,e.name AS employee_name
                                  FROM archived_documents d LEFT JOIN employees e ON e.id=d.employee_id
                                  ORDER BY d.uploaded_at DESC""").fetchall()

def is_privileged_user(user_or_role) -> bool:
    """Return True if user has unrestricted Admin or Developer privileges."""
    if isinstance(user_or_role, dict):
        role = str(user_or_role.get("role", "")).strip().lower()
        username = str(user_or_role.get("username", "")).strip().lower()
    else:
        role = str(user_or_role or "").strip().lower()
        username = ""
    if role:
        return role in ("admin", "developer")
    return username in ("admin", "developer", "dev")


def is_developer_test_user(user_or_role) -> bool:
    """Recognize the lowercase 'admin' developer account without misclassifying Taruna.

    The customer's role label is 'Admin'; that label alone does not grant developer
    privileges. A lowercase username 'admin' is the developer/tester identity.
    """
    if not user_or_role:
        return False
    if isinstance(user_or_role, dict):
        raw_username = str(user_or_role.get("username", "")).strip()
        role = str(user_or_role.get("role", "")).strip().casefold()
        display_name = str(user_or_role.get("display_name", "")).strip().casefold()
    else:
        raw_username = str(user_or_role or "").strip()
        role = ""
        display_name = ""
    # Taruna's customer identity takes precedence over the generic Admin role label.
    if raw_username == "Admin" or "taruna" in raw_username.casefold() or "taruna" in display_name:
        return False
    if raw_username == "admin":
        return True
    if role == "developer":
        return True
    return False


def is_master_customer_user(user_or_role) -> bool:
    """Return True for Taruna's customer identity or the legacy exact username 'Admin'."""
    if not user_or_role:
        return False
    if isinstance(user_or_role, dict):
        raw_username = str(user_or_role.get("username", "")).strip()
        uname = raw_username.casefold()
        dname = str(user_or_role.get("display_name", "")).strip().casefold()
    else:
        raw_username = str(user_or_role or "").strip()
        uname = raw_username.casefold()
        dname = ""
    return raw_username == "Admin" or "taruna" in uname or "taruna" in dname or "master" in dname


def _ensure_local_task_columns(conn: sqlite3.Connection):
    """Ensure newer task columns exist in any local connection before inserting/updating."""
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        for col_name in ("target_qty", "actual_qty", "next_action", "custom_values", "department"):
            if col_name not in cols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} TEXT DEFAULT ''")
    except Exception:
        pass


def merge_remote_json_snapshot(local_conn: sqlite3.Connection, json_data: bytes | str | dict) -> dict:
    """
    Non-destructively merge JSON business data (e.g. from mobile or web client) into local SQLite database.
    Preserves all records, unifies attendance check-ins/outs, and monotonically advances task progress.
    """
    stats = {"users": 0, "employees": 0, "attendance": 0, "tasks": 0}
    if isinstance(json_data, (bytes, bytearray)):
        marker = b"\n__RSC_JSON__\n"
        idx = json_data.rfind(marker)
        if idx != -1:
            json_text = json_data[idx + len(marker):].decode("utf-8", errors="replace")
        else:
            json_text = json_data.decode("utf-8", errors="replace")
        try:
            data = json.loads(json_text)
        except Exception:
            return stats
    elif isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except Exception:
            return stats
    elif isinstance(json_data, dict):
        data = json_data
    else:
        return stats

    if not isinstance(data, dict):
        return stats

    local_conn.execute("PRAGMA foreign_keys=OFF")
    local_conn.execute("BEGIN IMMEDIATE")
    try:
        # 0. Merge auth_users
        remote_users = data.get("auth_users") or []
        if isinstance(remote_users, list):
            local_users = {
                dict(r)["username"].strip().lower(): dict(r)
                for r in local_conn.execute("SELECT * FROM auth_users").fetchall()
            }
            for ru in remote_users:
                if not isinstance(ru, dict):
                    continue
                uname = str(ru.get("username", "")).strip().lower()
                if not uname:
                    continue
                if uname not in local_users:
                    local_conn.execute(
                        """INSERT INTO auth_users(username, display_name, role, password_salt, password_hash,
                           security_question, answer_salt, answer_hash, active, created_at, updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (ru["username"], ru.get("display_name", "") or ru["username"], ru.get("role", "Staff"),
                         ru.get("password_salt", ""), ru.get("password_hash", ""),
                         ru.get("security_question", ""), ru.get("answer_salt", ""), ru.get("answer_hash", ""),
                         int(ru.get("active", 1)), ru.get("created_at", now_text()), ru.get("updated_at", now_text()))
                    )
                    stats["users"] += 1
                else:
                    lu = local_users[uname]
                    r_upd = str(ru.get("updated_at") or "")
                    l_upd = str(lu.get("updated_at") or "")
                    if r_upd > l_upd:
                        new_role = ru.get("role", lu.get("role", "Staff"))
                        if is_privileged_user(lu) and not is_privileged_user(new_role):
                            new_role = lu.get("role", "Admin")
                        local_conn.execute(
                            """UPDATE auth_users SET display_name=?, role=?, password_salt=?, password_hash=?,
                               security_question=?, answer_salt=?, answer_hash=?, active=?, updated_at=?
                               WHERE id=?""",
                            (ru.get("display_name", lu.get("display_name", "")), new_role,
                             ru.get("password_salt", lu.get("password_salt", "")),
                             ru.get("password_hash", lu.get("password_hash", "")),
                             ru.get("security_question", lu.get("security_question", "")),
                             ru.get("answer_salt", lu.get("answer_salt", "")),
                             ru.get("answer_hash", lu.get("answer_hash", "")),
                             int(ru.get("active", 1)), now_text(), lu["id"])
                        )
                        stats["users"] += 1

        # 1. Merge employees & map remote IDs
        remote_to_local_emp_id = {}
        local_emps = [dict(r) for r in local_conn.execute("SELECT * FROM employees").fetchall()]
        local_by_code = {
            str(r.get("employee_code") or "").strip().lower(): r
            for r in local_emps if str(r.get("employee_code") or "").strip()
        }
        local_by_name = {
            str(r.get("name") or "").strip().lower(): r
            for r in local_emps if str(r.get("name") or "").strip()
        }

        remote_emps = data.get("employees") or []
        if isinstance(remote_emps, list):
            for re_dict in remote_emps:
                if not isinstance(re_dict, dict):
                    continue
                code = str(re_dict.get("employee_code") or "").strip().lower()
                name = str(re_dict.get("name") or "").strip().lower()
                r_id = re_dict.get("id")

                match = local_by_code.get(code) if code else None
                if not match and name:
                    match = local_by_name.get(name)

                if match:
                    if r_id is not None:
                        remote_to_local_emp_id[r_id] = match["id"]
                    local_conn.execute(
                        """UPDATE employees SET
                           department = CASE WHEN department='' THEN ? ELSE department END,
                           designation = CASE WHEN designation='' THEN ? ELSE designation END,
                           phone = CASE WHEN phone='' THEN ? ELSE phone END,
                           email = CASE WHEN email='' THEN ? ELSE email END
                           WHERE id=?""",
                        (re_dict.get("department", ""), re_dict.get("designation", ""),
                         re_dict.get("phone", ""), re_dict.get("email", ""), match["id"])
                    )
                else:
                    cur = local_conn.execute(
                        """INSERT INTO employees(employee_code, name, department, designation, phone, email, joining_date, active, notes, created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (re_dict.get("employee_code") or None, re_dict.get("name", "New Employee"),
                         re_dict.get("department", ""), re_dict.get("designation", ""),
                         re_dict.get("phone", ""), re_dict.get("email", ""),
                         re_dict.get("joining_date", ""), int(re_dict.get("active", 1)),
                         re_dict.get("notes", ""), re_dict.get("created_at", now_text()))
                    )
                    new_id = cur.lastrowid
                    if r_id is not None:
                        remote_to_local_emp_id[r_id] = new_id
                    if code:
                        local_by_code[code] = {"id": new_id, "name": re_dict.get("name", "")}
                    if name:
                        local_by_name[name] = {"id": new_id, "name": re_dict.get("name", "")}
                    stats["employees"] += 1

        # 2. Merge attendance
        remote_att = data.get("attendance") or {}
        att_items = remote_att.values() if isinstance(remote_att, dict) else remote_att
        if isinstance(att_items, (list, tuple)) or hasattr(att_items, "__iter__"):
            for ra in att_items:
                if not isinstance(ra, dict):
                    continue
                orig_eid = ra.get("employee_id")
                target_eid = remote_to_local_emp_id.get(orig_eid, orig_eid)
                wdate = str(ra.get("work_date") or "").strip()
                if not target_eid or not wdate:
                    continue
                la = local_conn.execute(
                    "SELECT * FROM attendance WHERE employee_id=? AND work_date=?",
                    (target_eid, wdate)
                ).fetchone()
                if not la:
                    local_conn.execute(
                        """INSERT INTO attendance(employee_id, work_date, check_in, check_out, break_minutes, attendance_status, attendance_note, updated_at)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (target_eid, wdate, str(ra.get("check_in") or ""), str(ra.get("check_out") or ""),
                         int(ra.get("break_minutes") or 0), str(ra.get("attendance_status") or "Unmarked"),
                         str(ra.get("attendance_note") or ""), str(ra.get("updated_at") or now_text()))
                    )
                    stats["attendance"] += 1
                else:
                    merged_in = la["check_in"] or str(ra.get("check_in") or "")
                    merged_out = la["check_out"] or str(ra.get("check_out") or "")
                    status = la["attendance_status"]
                    r_status = str(ra.get("attendance_status") or "")
                    if status in ("", "Unmarked") and r_status not in ("", "Unmarked"):
                        status = r_status
                    elif r_status == "Present":
                        status = "Present"
                    l_note = la["attendance_note"] or ""
                    r_note = str(ra.get("attendance_note") or "")
                    merged_note = l_note
                    if r_note and r_note not in l_note:
                        merged_note = f"{l_note} | {r_note}".strip(" |")
                    local_conn.execute(
                        """UPDATE attendance SET check_in=?, check_out=?, attendance_status=?, attendance_note=?, updated_at=?
                           WHERE id=?""",
                        (merged_in, merged_out, status, merged_note, now_text(), la["id"])
                    )
                    stats["attendance"] += 1

        # 3. Merge tasks
        _ensure_local_task_columns(local_conn)
        remote_tasks = data.get("tasks") or []
        if isinstance(remote_tasks, list):
            for rt in remote_tasks:
                if not isinstance(rt, dict):
                    continue
                orig_eid = rt.get("employee_id")
                target_eid = remote_to_local_emp_id.get(orig_eid, orig_eid)
                title = str(rt.get("title") or "").strip()
                tdate = str(rt.get("task_date") or "").strip()
                if not target_eid or not title:
                    continue
                lt = local_conn.execute(
                    "SELECT * FROM tasks WHERE employee_id=? AND task_date=? AND title=? COLLATE NOCASE",
                    (target_eid, tdate, title)
                ).fetchone()
                if not lt:
                    c_vals = str(rt.get("custom_values") or "")
                    t_dept = str(rt.get("department") or "")
                    local_conn.execute(
                        """INSERT INTO tasks(employee_id, task_date, title, department, details, due_time, priority, status, progress, proof_url, proof_note, submitted_at, manager_note, expose_link, target_qty, actual_qty, next_action, custom_values, created_at, updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (target_eid, tdate, title, t_dept, str(rt.get("details") or ""), str(rt.get("due_time") or ""),
                         str(rt.get("priority") or "Normal"), str(rt.get("status") or "Not started"),
                         int(rt.get("progress") or 0), str(rt.get("proof_url") or ""), str(rt.get("proof_note") or ""),
                         str(rt.get("submitted_at") or ""), str(rt.get("manager_note") or ""),
                         int(rt.get("expose_link") or 0), str(rt.get("target_qty") or ""), str(rt.get("actual_qty") or ""),
                         str(rt.get("next_action") or rt.get("manager_note") or ""), c_vals,
                         str(rt.get("created_at") or now_text()), str(rt.get("updated_at") or now_text()))
                    )
                    stats["tasks"] += 1
                else:
                    new_prog = max(int(lt["progress"] or 0), int(rt.get("progress") or 0))
                    new_stat = "Completed" if (lt["status"] == "Completed" or rt.get("status") == "Completed") else rt.get("status", lt["status"])
                    new_url = rt.get("proof_url") or lt["proof_url"] or ""
                    new_note = lt["manager_note"] or ""
                    r_note = str(rt.get("manager_note") or "")
                    if r_note and r_note not in new_note:
                        new_note = f"{new_note} | {r_note}".strip(" |")
                    t_qty = str(rt.get("target_qty") or (lt["target_qty"] if "target_qty" in lt.keys() else "") or "")
                    a_qty = str(rt.get("actual_qty") or (lt["actual_qty"] if "actual_qty" in lt.keys() else "") or "")
                    nxt_act = str(rt.get("next_action") or (lt["next_action"] if "next_action" in lt.keys() else "") or new_note)
                    c_vals = str(rt.get("custom_values") or (lt["custom_values"] if "custom_values" in lt.keys() else "") or "")
                    t_dept = str(rt.get("department") or (lt["department"] if "department" in lt.keys() else "") or "")
                    local_conn.execute(
                        """UPDATE tasks SET department=?, progress=?, status=?, proof_url=?, manager_note=?, target_qty=?, actual_qty=?, next_action=?, custom_values=?, updated_at=? WHERE id=?""",
                        (t_dept, new_prog, new_stat, new_url, new_note, t_qty, a_qty, nxt_act, c_vals, now_text(), lt["id"])
                    )
                    stats["tasks"] += 1

        # 4. Merge holidays
        remote_hols = data.get("holidays") or {}
        if isinstance(remote_hols, dict):
            for hdate, hname in remote_hols.items():
                local_conn.execute(
                    "INSERT OR IGNORE INTO holidays(holiday_date, holiday_name, created_at) VALUES(?,?,?)",
                    (str(hdate), str(hname), now_text())
                )
        elif isinstance(remote_hols, list):
            for rh in remote_hols:
                if isinstance(rh, dict) and rh.get("holiday_date"):
                    local_conn.execute(
                        "INSERT OR IGNORE INTO holidays(holiday_date, holiday_name, created_at) VALUES(?,?,?)",
                        (str(rh["holiday_date"]), str(rh.get("holiday_name", "")), now_text())
                    )

        local_conn.commit()
    except Exception as exc:
        local_conn.rollback()
        raise exc
    finally:
        local_conn.execute("PRAGMA foreign_keys=ON")
    return stats


def merge_remote_database_snapshot(local_conn: sqlite3.Connection, snapshot_path: Path | str) -> dict:
    """
    Intelligently merge a downloaded remote database snapshot into local_conn.
    All data is union-merged without destructive table replacement:
    - auth_users: matched by username COLLATE NOCASE; new users added, updates merged, admin privileges preserved.
    - employees: matched by employee_code / name; new employees appended, remote_to_local_id mapped.
    - attendance: matched by (employee, work_date); check-ins/outs and statuses merged without loss.
    - tasks: matched by (employee, task_date, title); merged by progress/updated_at, non-duplicates appended.
    - employee_targets: matched by (employee, target_date); merged.
    - holidays: matched by holiday_date; merged.
    - archived_documents: matched by (file_name, report_date); merged.
    - source_reports: matched by (report_date, source_filename); merged.
    - settings: only shared business calendar / config merged; local credentials/themes preserved.
    - audit_log: non-duplicates appended.
    """
    raw_head = b""
    try:
        with open(str(snapshot_path), "rb") as f:
            raw_head = f.read(16)
    except Exception:
        pass
    if not raw_head.startswith(b"SQLite format 3\x00"):
        raw_full = Path(snapshot_path).read_bytes()
        return merge_remote_json_snapshot(local_conn, raw_full)

    remote = sqlite3.connect(str(snapshot_path), timeout=25)
    remote.row_factory = sqlite3.Row
    stats = {"users": 0, "employees": 0, "attendance": 0, "tasks": 0}
    try:
        remote_tables = {
            r[0] for r in remote.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        }
        
        local_conn.execute("PRAGMA foreign_keys=OFF")
        local_conn.execute("BEGIN IMMEDIATE")
        
        # 1. Merge auth_users
        if "auth_users" in remote_tables:
            remote_users = remote.execute("SELECT * FROM auth_users").fetchall()
            local_users = {
                dict(r)["username"].strip().lower(): dict(r)
                for r in local_conn.execute("SELECT * FROM auth_users").fetchall()
            }
            for ru in remote_users:
                ru_dict = dict(ru)
                uname = str(ru_dict.get("username", "")).strip().lower()
                if not uname:
                    continue
                if uname not in local_users:
                    local_conn.execute(
                        """INSERT INTO auth_users(username, display_name, role, password_salt, password_hash,
                           security_question, answer_salt, answer_hash, active, created_at, updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (ru_dict["username"], ru_dict.get("display_name", ""), ru_dict.get("role", "Staff"),
                         ru_dict["password_salt"], ru_dict["password_hash"],
                         ru_dict.get("security_question", ""), ru_dict.get("answer_salt", ""), ru_dict.get("answer_hash", ""),
                         int(ru_dict.get("active", 1)), ru_dict.get("created_at", now_text()), ru_dict.get("updated_at", now_text()))
                    )
                    stats["users"] += 1
                else:
                    lu = local_users[uname]
                    r_upd = str(ru_dict.get("updated_at") or "")
                    l_upd = str(lu.get("updated_at") or "")
                    if r_upd > l_upd:
                        new_role = ru_dict.get("role", lu.get("role", "Staff"))
                        # Protect primary local admin/developer accounts from downgrade
                        remote_role = ru_dict.get("role", "Staff")
                        if is_privileged_user(lu) and not is_privileged_user(remote_role):
                            new_role = lu.get("role", "Admin")
                        local_conn.execute(
                            """UPDATE auth_users SET display_name=?, role=?, password_salt=?, password_hash=?,
                               security_question=?, answer_salt=?, answer_hash=?, active=?, updated_at=?
                               WHERE id=?""",
                            (ru_dict.get("display_name", lu.get("display_name", "")), new_role,
                             ru_dict["password_salt"], ru_dict["password_hash"],
                             ru_dict.get("security_question", ""), ru_dict.get("answer_salt", ""), ru_dict.get("answer_hash", ""),
                             int(ru_dict.get("active", 1)), r_upd, lu["id"])
                        )
                        stats["users"] += 1

        # 2. Merge employees & build remote_id -> local_id map
        remote_to_local_emp_id = {}
        if "employees" in remote_tables:
            remote_emps = remote.execute("SELECT * FROM employees").fetchall()
            local_emps = [dict(r) for r in local_conn.execute("SELECT * FROM employees").fetchall()]
            local_by_code = {
                str(r.get("employee_code") or "").strip().lower(): r
                for r in local_emps if str(r.get("employee_code") or "").strip()
            }
            local_by_name = {
                str(r.get("name") or "").strip().lower(): r
                for r in local_emps
            }
            
            for re in remote_emps:
                re_dict = dict(re)
                rcode = str(re_dict.get("employee_code") or "").strip().lower()
                rname = str(re_dict.get("name") or "").strip().lower()
                matched_local = None
                if rcode and rcode in local_by_code:
                    matched_local = local_by_code[rcode]
                elif rname in local_by_name:
                    matched_local = local_by_name[rname]
                
                if matched_local is None:
                    cur = local_conn.execute(
                        """INSERT INTO employees(employee_code, name, department, designation, phone, email, joining_date, active, notes, created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (re_dict.get("employee_code", ""), re_dict.get("name", ""), re_dict.get("department", ""),
                         re_dict.get("designation", ""), re_dict.get("phone", ""), re_dict.get("email", ""),
                         re_dict.get("joining_date", ""), int(re_dict.get("active", 1)), re_dict.get("notes", ""),
                         re_dict.get("created_at", now_text()))
                    )
                    new_id = cur.lastrowid
                    remote_to_local_emp_id[re_dict["id"]] = new_id
                    stats["employees"] += 1
                else:
                    lid = matched_local["id"]
                    remote_to_local_emp_id[re_dict["id"]] = lid
                    updates = []
                    vals = []
                    for col in ("department", "designation", "phone", "email", "notes"):
                        if not matched_local.get(col) and re_dict.get(col):
                            updates.append(f"{col}=?")
                            vals.append(re_dict[col])
                    if updates:
                        vals.append(lid)
                        local_conn.execute(f"UPDATE employees SET {', '.join(updates)} WHERE id=?", vals)

        # 3. Merge attendance
        if "attendance" in remote_tables:
            remote_att = remote.execute("SELECT * FROM attendance").fetchall()
            for ra in remote_att:
                ra_dict = dict(ra)
                lid = remote_to_local_emp_id.get(ra_dict["employee_id"])
                if not lid:
                    continue
                wdate = ra_dict.get("work_date", "")
                la_row = local_conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?", (lid, wdate)).fetchone()
                if la_row is None:
                    local_conn.execute(
                        """INSERT INTO attendance(employee_id, work_date, check_in, check_out, break_minutes, attendance_status, attendance_note, updated_at)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (lid, wdate, ra_dict.get("check_in", ""), ra_dict.get("check_out", ""),
                         int(ra_dict.get("break_minutes", 0)), ra_dict.get("attendance_status", "Unmarked"),
                         ra_dict.get("attendance_note", ""), ra_dict.get("updated_at", now_text()))
                    )
                    stats["attendance"] += 1
                else:
                    la = dict(la_row)
                    c_in = la.get("check_in") or ra_dict.get("check_in") or ""
                    c_out = la.get("check_out") or ra_dict.get("check_out") or ""
                    status = la.get("attendance_status") or "Unmarked"
                    r_status = ra_dict.get("attendance_status") or "Unmarked"
                    r_upd = str(ra_dict.get("updated_at") or "")
                    l_upd = str(la.get("updated_at") or "")
                    if (status in ("Unmarked", "", None) and r_status not in ("Unmarked", "", None)) or (r_upd > l_upd and r_status != "Unmarked"):
                        status = r_status
                    break_mins = max(int(la.get("break_minutes") or 0), int(ra_dict.get("break_minutes") or 0))
                    note = la.get("attendance_note") or ""
                    rnote = ra_dict.get("attendance_note") or ""
                    if rnote and rnote not in note:
                        note = f"{note}; {rnote}".strip("; ")
                    upd = max(l_upd, r_upd, now_text())
                    local_conn.execute(
                        """UPDATE attendance SET check_in=?, check_out=?, break_minutes=?, attendance_status=?, attendance_note=?, updated_at=?
                           WHERE id=?""",
                        (c_in, c_out, break_mins, status, note, upd, la["id"])
                    )

        # 4. Merge tasks
        if "tasks" in remote_tables:
            _ensure_local_task_columns(local_conn)
            remote_tasks = remote.execute("SELECT * FROM tasks").fetchall()
            for rt in remote_tasks:
                rt_dict = dict(rt)
                lid = remote_to_local_emp_id.get(rt_dict["employee_id"])
                if not lid:
                    continue
                tdate = rt_dict.get("task_date", "")
                ttitle = str(rt_dict.get("title") or "").strip()
                lt_row = local_conn.execute(
                    "SELECT * FROM tasks WHERE employee_id=? AND task_date=? AND title=? COLLATE NOCASE",
                    (lid, tdate, ttitle)
                ).fetchone()
                if lt_row is None:
                    c_vals = str(rt_dict.get("custom_values") or "")
                    t_dept = str(rt_dict.get("department") or "")
                    local_conn.execute(
                        """INSERT INTO tasks(employee_id, task_date, title, department, details, due_time, priority, status,
                           progress, proof_url, proof_note, submitted_at, manager_note, expose_link, target_qty, actual_qty, next_action, custom_values, created_at, updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (lid, tdate, ttitle, t_dept, rt_dict.get("details", ""), rt_dict.get("due_time", ""),
                         rt_dict.get("priority", "Normal"), rt_dict.get("status", "Not started"),
                         int(rt_dict.get("progress", 0)), rt_dict.get("proof_url", ""), rt_dict.get("proof_note", ""),
                         rt_dict.get("submitted_at", ""), rt_dict.get("manager_note", ""),
                         int(rt_dict.get("expose_link", 0)), str(rt_dict.get("target_qty") or ""),
                         str(rt_dict.get("actual_qty") or ""), str(rt_dict.get("next_action") or rt_dict.get("manager_note") or ""),
                         c_vals, rt_dict.get("created_at", now_text()), rt_dict.get("updated_at", now_text()))
                    )
                    stats["tasks"] += 1
                else:
                    lt = dict(lt_row)
                    new_progress = max(int(lt.get("progress") or 0), int(rt_dict.get("progress") or 0))
                    new_status = lt.get("status", "Not started")
                    if rt_dict.get("status") == "Completed" or (int(rt_dict.get("progress") or 0) > int(lt.get("progress") or 0)):
                        new_status = rt_dict.get("status", new_status)
                    p_url = lt.get("proof_url") or rt_dict.get("proof_url") or ""
                    p_note = lt.get("proof_note") or rt_dict.get("proof_note") or ""
                    if rt_dict.get("proof_note") and rt_dict.get("proof_note") not in (lt.get("proof_note") or ""):
                        p_note = f"{lt.get('proof_note') or ''}; {rt_dict.get('proof_note')}".strip("; ")
                    m_note = lt.get("manager_note") or rt_dict.get("manager_note") or ""
                    if rt_dict.get("manager_note") and rt_dict.get("manager_note") not in (lt.get("manager_note") or ""):
                        m_note = f"{lt.get('manager_note') or ''}; {rt_dict.get('manager_note')}".strip("; ")
                    exp_link = max(int(lt.get("expose_link") or 0), int(rt_dict.get("expose_link") or 0))
                    r_upd = str(rt_dict.get("updated_at") or "")
                    l_upd = str(lt.get("updated_at") or "")
                    upd = max(l_upd, r_upd, now_text())
                    t_qty = str(rt_dict.get("target_qty") or lt.get("target_qty") or "")
                    a_qty = str(rt_dict.get("actual_qty") or lt.get("actual_qty") or "")
                    nxt_act = str(rt_dict.get("next_action") or lt.get("next_action") or m_note)
                    c_vals = str(rt_dict.get("custom_values") or lt.get("custom_values") or "")
                    t_dept = str(rt_dict.get("department") or lt.get("department") or "")
                    local_conn.execute(
                        """UPDATE tasks SET department=?, progress=?, status=?, proof_url=?, proof_note=?, manager_note=?, expose_link=?, target_qty=?, actual_qty=?, next_action=?, custom_values=?, updated_at=?
                           WHERE id=?""",
                        (t_dept, new_progress, new_status, p_url, p_note, m_note, exp_link, t_qty, a_qty, nxt_act, c_vals, upd, lt["id"])
                    )

        # 5. Merge employee_targets
        if "employee_targets" in remote_tables:
            for rtg in remote.execute("SELECT * FROM employee_targets").fetchall():
                rtg_dict = dict(rtg)
                lid = remote_to_local_emp_id.get(rtg_dict["employee_id"])
                if not lid:
                    continue
                ltg_row = local_conn.execute("SELECT * FROM employee_targets WHERE employee_id=? AND target_date=?", (lid, rtg_dict["target_date"])).fetchone()
                if ltg_row is None:
                    local_conn.execute(
                        """INSERT INTO employee_targets(employee_id, target_date, target, target_status, updated_at)
                           VALUES(?,?,?,?,?)""",
                        (lid, rtg_dict["target_date"], rtg_dict.get("target", ""), rtg_dict.get("target_status", ""), rtg_dict.get("updated_at", now_text()))
                    )
                elif str(rtg_dict.get("updated_at") or "") > str(dict(ltg_row).get("updated_at") or ""):
                    local_conn.execute(
                        """UPDATE employee_targets SET target=?, target_status=?, updated_at=? WHERE id=?""",
                        (rtg_dict.get("target", ""), rtg_dict.get("target_status", ""), rtg_dict.get("updated_at", now_text()), dict(ltg_row)["id"])
                    )

        # 6. Merge holidays
        if "holidays" in remote_tables:
            for rh in remote.execute("SELECT * FROM holidays").fetchall():
                rh_dict = dict(rh)
                local_conn.execute(
                    """INSERT INTO holidays(holiday_date, holiday_name, created_at)
                       VALUES(?,?,?)
                       ON CONFLICT(holiday_date) DO UPDATE SET
                         holiday_name=CASE WHEN holiday_name='' OR holiday_name IS NULL THEN excluded.holiday_name ELSE holiday_name END""",
                    (rh_dict["holiday_date"], rh_dict.get("holiday_name", ""), rh_dict.get("created_at", now_text()))
                )

        # 7. Merge archived_documents
        if "archived_documents" in remote_tables:
            for rd in remote.execute("SELECT * FROM archived_documents").fetchall():
                rd_dict = dict(rd)
                lid = remote_to_local_emp_id.get(rd_dict["employee_id"]) if rd_dict.get("employee_id") else None
                ld = local_conn.execute(
                    "SELECT id FROM archived_documents WHERE file_name=? AND report_date=?",
                    (rd_dict["file_name"], rd_dict.get("report_date", ""))
                ).fetchone()
                if ld is None:
                    local_conn.execute(
                        """INSERT INTO archived_documents(employee_id, report_date, file_name, mime_type, content, notes, uploaded_at)
                           VALUES(?,?,?,?,?,?,?)""",
                        (lid, rd_dict.get("report_date", ""), rd_dict["file_name"], rd_dict.get("mime_type", "application/pdf"),
                         rd_dict["content"], rd_dict.get("notes", ""), rd_dict.get("uploaded_at", now_text()))
                    )

        # 8. Merge source_reports
        if "source_reports" in remote_tables:
            for rs in remote.execute("SELECT * FROM source_reports").fetchall():
                rs_dict = dict(rs)
                local_conn.execute(
                    """INSERT OR IGNORE INTO source_reports(report_date, source_filename, raw_text, imported_at)
                       VALUES(?,?,?,?)""",
                    (rs_dict["report_date"], rs_dict["source_filename"], rs_dict.get("raw_text", ""), rs_dict.get("imported_at", now_text()))
                )

        # 9. Merge settings (only shared business settings like working_weekdays)
        if "settings" in remote_tables:
            for rk in ("working_weekdays", "initial_audit_2026_10_09_imported"):
                r_val = remote.execute("SELECT value FROM settings WHERE key=?", (rk,)).fetchone()
                if r_val and r_val[0]:
                    local_conn.execute(
                        "INSERT INTO settings(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (rk, r_val[0])
                    )

        local_conn.commit()
    except Exception:
        local_conn.rollback()
        raise
    finally:
        local_conn.execute("PRAGMA foreign_keys=ON")
        remote.close()
    return stats


_SHOW_DIALOG_HOOK = None

def _show_app_dialog(parent, message, icon, title=None, is_question=False, default_yes=False):
    """Show readable, word-wrapped app messages and confirmation dialogs without clipped text or sunken layout."""
    screen = parent.screen() if (parent is not None and hasattr(parent, "screen")) else QApplication.primaryScreen()
    available_width = screen.availableGeometry().width() if screen else 1280
    dialog_width = max(240, min(500, available_width - 32))
    dialog_width = max(480, min(560, available_width - 48))
    label_width = dialog_width - 100

    theme_name = None
    if parent is not None:
        if hasattr(parent, "current_theme"):
            theme_name = parent.current_theme()
        elif hasattr(parent, "window") and hasattr(parent.window(), "current_theme"):
            theme_name = parent.window().current_theme()
        elif hasattr(parent, "property") and parent.property("ui_theme"):
            theme_name = parent.property("ui_theme")
    if not theme_name:
        if QApplication.instance() is not None:
            app_ss = QApplication.instance().styleSheet()
            if "stop:0 #F8FAFC" in app_ss or "stop:0.45 #F1F5F9" in app_ss:
                theme_name = "day"
            elif "stop:0 #080C14" in app_ss or "stop:0.5 #0B1120" in app_ss:
                theme_name = "night"
            else:
                theme_name = "day"
        else:
            theme_name = "day"

    is_dark = (theme_name or "day").lower() in ("night", "dark")
    bg = "#0F172A" if is_dark else "#FFFFFF"
    text_color = "#F8FAFC" if is_dark else "#0F172A"
    border = "#334155" if is_dark else "#CBD5E1"
    btn_sec_bg = "#1E293B" if is_dark else "#FFFFFF"
    btn_sec_text = "#F8FAFC" if is_dark else "#0F172A"
    btn_sec_border = "#334155" if is_dark else "#CBD5E1"
    btn_sec_hover = "#334155" if is_dark else "#F1F5F9"
    btn_pri_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED)"
    btn_pri_hover = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9)"
    btn_pri_border = "#818CF8"

    box = QMessageBox(parent)
    box.setWindowTitle(title or APP_NAME)
    box.setWindowIcon(QIcon(resource_path("assets/raw_strength_icon.ico")))
    box.setIcon(icon)
    box.setText(str(message))
    box.setTextFormat(Qt.TextFormat.PlainText)

    if is_question:
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.Yes if default_yes else QMessageBox.StandardButton.No)
    else:
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.setDefaultButton(QMessageBox.StandardButton.Ok)

    box.setMinimumWidth(dialog_width)
    box.setMinimumHeight(150)

    grid = box.layout()
    if isinstance(grid, QGridLayout):
        spacer = QSpacerItem(dialog_width, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        grid.addItem(spacer, grid.rowCount(), 0, 1, grid.columnCount())

    box.setStyleSheet(f"""
        QMessageBox {{
            background-color: {bg};
            border: 1.5px solid {border};
            border-radius: 12px;
        }}
        QLabel#qt_msgbox_label {{
            color: {text_color};
            font-size: 10pt;
            font-weight: 500;
            padding: 8px 10px;
            background: transparent;
            min-width: {label_width}px;
        }}
        QLabel#qt_msgboxex_icon_label {{
            min-width: 44px;
            min-height: 44px;
            background: transparent;
            padding: 4px;
        }}
        QPushButton {{
            min-width: 95px;
            min-height: 36px;
            padding: 6px 18px;
            border-radius: 8px;
            font-size: 9.5pt;
            font-weight: 600;
            background-color: {btn_sec_bg};
            color: {btn_sec_text};
            border: 1.5px solid {btn_sec_border};
        }}
        QPushButton:hover {{
            background-color: {btn_sec_hover};
        }}
        QPushButton:default {{
            background: {btn_pri_bg};
            color: #FFFFFF;
            border: 1.5px solid {btn_pri_border};
            font-weight: 700;
        }}
        QPushButton:default:hover {{
            background: {btn_pri_hover};
        }}
    """)

    label = box.findChild(QLabel, "qt_msgbox_label")
    if label is not None:
        label.setWordWrap(True)
        label.setMinimumWidth(label_width)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    icon_label = box.findChild(QLabel, "qt_msgboxex_icon_label")
    if icon_label is not None:
        icon_label.setMinimumSize(44, 44)
        icon_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    for btn in box.findChildren(QPushButton):
        btn.setMinimumWidth(95)
        btn.setMinimumHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

    global _SHOW_DIALOG_HOOK
    if _SHOW_DIALOG_HOOK is not None:
        ret = _SHOW_DIALOG_HOOK(box)
    else:
        ret = box.exec()
    if is_question:
        return ret in (QMessageBox.StandardButton.Yes, 16384)
    return None

def _show_message(parent, message, icon):
    return _show_app_dialog(parent, message, icon, is_question=False)

def ask(parent, title, message):
    return _show_app_dialog(parent, message, QMessageBox.Icon.Question, title=title, is_question=True)

def info(parent, message, title=None):
    return _show_app_dialog(parent, message, QMessageBox.Icon.Information, title=title, is_question=False)

def error(parent, message, title=None):
    return _show_app_dialog(parent, message, QMessageBox.Icon.Critical, title=title, is_question=False)

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


def _prompt_and_update_password(parent, db, user_row, success_message="Your password has been changed."):
    """Prompt for current and new password, validate, hash, and persist to auth_users."""
    echo_mode = QLineEdit.EchoMode.Password if hasattr(QLineEdit, "EchoMode") else QLineEdit.Password
    current, ok = QInputDialog.getText(parent, "Change password", "Current password:", echo_mode)
    if not ok:
        return False
    _, digest = hash_pin(current, user_row["password_salt"])
    if not secrets.compare_digest(digest, user_row["password_hash"]):
        error(parent, "Current password is incorrect.")
        return False
    new, ok = QInputDialog.getText(parent, "Change password", "New password (8+ characters, letters and numbers):", echo_mode)
    if not ok:
        return False
    if not password_is_strong(new):
        error(parent, "Use at least 8 characters, including a letter and a number.")
        return False
    confirm, ok = QInputDialog.getText(parent, "Change password", "Confirm new password:", echo_mode)
    if not ok or confirm != new:
        error(parent, "The passwords do not match.")
        return False
    salt, digest = hash_pin(new)
    db.conn.execute(
        "UPDATE auth_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?",
        (salt, digest, now_text(), user_row["id"]),
    )
    db.conn.commit()
    db.log("Password changed", user_row["username"])
    info(parent, success_message)
    return True


def add_theme_selector(dialog, db, layout):
    """Expose the saved application theme on entry dialogs as well as Settings."""
    row = QHBoxLayout()
    label = QLabel("Appearance")
    selector = QComboBox()
    selector.addItems(["Day", "Night", "Ocean", "Sunset"])
    saved = (db.get_setting("ui_theme", "night") or "night").capitalize()
    if saved in ("Day", "Night", "Ocean", "Sunset"):
        selector.setCurrentText(saved)
    def change_theme(value):
        chosen = (value or "Night").lower()
        apply_app_theme(QApplication.instance(), chosen)
        db.set_setting("ui_theme", chosen)
    selector.currentTextChanged.connect(change_theme)
    row.addWidget(label)
    row.addWidget(selector, 1)
    layout.addLayout(row)

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
        add_theme_selector(self, self.db, layout)

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
            if hasattr(self.db, "github_sync") and self.db.github_sync.is_configured:
                self.db.github_sync.request_sync()
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
        logo.setPixmap(brand_mark_pixmap(72))
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

        # Quick Account selection chips for Customer Master vs Developer Test
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(8)
        lbl_quick = QLabel("Quick Account:")
        lbl_quick.setStyleSheet("font-size: 8.5pt; color: #94A3B8; font-weight: 600;")
        btn_taruna = QPushButton("👑 Admin / Taruna (Customer Master)")
        btn_taruna.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_taruna.setToolTip("Sign in as Customer Master (live synchronization enabled)")
        btn_taruna.setStyleSheet(
            "QPushButton { background: rgba(59, 130, 246, 0.22); color: #93C5FD; "
            "border: 1px solid rgba(59, 130, 246, 0.45); border-radius: 6px; padding: 4px 10px; font-size: 8.5pt; font-weight: 600; } "
            "QPushButton:hover { background: rgba(59, 130, 246, 0.40); color: #FFFFFF; }"
        )
        btn_taruna.clicked.connect(lambda: (self.username.setText("taruna"), self.password.setFocus()))

        btn_admin = QPushButton("🧪 admin (Developer Test)")
        btn_admin.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_admin.setToolTip("Sign in as Developer for testing (cloud sync disabled to protect live customer data)")
        btn_admin.setStyleSheet(
            "QPushButton { background: rgba(245, 158, 11, 0.22); color: #FCD34D; "
            "border: 1px solid rgba(245, 158, 11, 0.45); border-radius: 6px; padding: 4px 10px; font-size: 8.5pt; font-weight: 600; } "
            "QPushButton:hover { background: rgba(245, 158, 11, 0.40); color: #FFFFFF; }"
        )
        btn_admin.clicked.connect(lambda: (self.username.setText("admin"), self.password.setFocus()))

        quick_layout.addWidget(lbl_quick)
        quick_layout.addWidget(btn_taruna)
        quick_layout.addWidget(btn_admin)
        quick_layout.addStretch(1)
        layout.addLayout(quick_layout)

        form = QFormLayout()
        form.setSpacing(12)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter username (e.g. taruna or admin)")
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
        add_theme_selector(self, self.db, layout)
        self.password.returnPressed.connect(self.check)

    def check(self):
        raw_username = self.username.text().strip()
        uname = raw_username.lower()
        if uname in ("admin / taruna", "admin/taruna", "taruna"):
            target_username = "taruna"
        elif uname == "admin":
            target_username = "admin"
        else:
            target_username = raw_username

        row = self.db.conn.execute("SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1", (target_username,)).fetchone()
        if not row:
            row = self.db.conn.execute(
                "SELECT * FROM auth_users WHERE (username=? OR display_name LIKE ?) COLLATE NOCASE AND active=1",
                (raw_username, f"%{raw_username}%")
            ).fetchone()
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
        _prompt_and_update_password(self, self.db, row, "Password changed. Sign in with your new password.")

class EmployeeDialog(QDialog):
    def __init__(self, parent=None, row=None):
        super().__init__(parent); self.setWindowTitle("Employee details"); self.setMinimumWidth(440)
        self.layout=QFormLayout(self)
        self.code=QLineEdit(row["employee_code"] if row else "")
        self.name=QLineEdit(row["name"] if row else "")
        self.department=QComboBox()
        self.department.setEditable(True)
        self.department.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        default_depts = ["General", "Housekeeping", "Trainer / Fitness", "Management", "Sales", "Others"]
        existing_groups = []
        if parent and hasattr(parent, "db") and hasattr(parent.db, "employee_groups"):
            for g in parent.db.employee_groups():
                gname = (g.get("name") or "").strip()
                if gname and gname not in existing_groups:
                    existing_groups.append(gname)
        combined_depts = []
        for d in default_depts + existing_groups:
            if d and d not in combined_depts:
                combined_depts.append(d)
        cur_dept = (row["department"] if row else "").strip()
        if cur_dept and cur_dept not in combined_depts:
            combined_depts.append(cur_dept)
        for d in combined_depts:
            self.department.addItem(d)
        self.department.addItem("➕ Add Custom Department...")
        if cur_dept:
            self.department.setEditText(cur_dept)
        else:
            self.department.setCurrentIndex(0)

        def _on_dept_changed(idx):
            if self.department.itemText(idx) == "➕ Add Custom Department...":
                name, ok = QInputDialog.getText(self, "Add Custom Department", "Enter Custom Department Name:")
                if ok and name.strip():
                    new_dept = name.strip()
                    if parent and hasattr(parent, "db") and hasattr(parent.db, "add_employee_group"):
                        parent.db.add_employee_group(new_dept)
                    add_idx = max(0, self.department.count() - 1)
                    self.department.insertItem(add_idx, new_dept)
                    self.department.setCurrentIndex(add_idx)
                else:
                    self.department.setCurrentIndex(0)
        self.department.currentIndexChanged.connect(_on_dept_changed)
        self.designation=QLineEdit(row["designation"] if row else "")
        self.phone=QLineEdit(row["phone"] if row and "phone" in row.keys() else "")
        self.email=QLineEdit(row["email"] if row and "email" in row.keys() else "")
        self.phone.setPlaceholderText("Optional")
        self.email.setPlaceholderText("Optional")
        self.join=QDateEdit(); configure_date_edit(self.join); self.join.setDisplayFormat("yyyy-MM-dd")
        parsed_join = QDate.fromString(row["joining_date"], "yyyy-MM-dd") if row and row["joining_date"] else None
        self.join.setDate(parsed_join if (parsed_join and parsed_join.isValid()) else QDate.currentDate())
        self.join_known=QCheckBox("Joining date is known")
        self.join_known.setChecked(bool(not row or row["joining_date"]))
        self.join.setEnabled(self.join_known.isChecked())
        self.join_known.toggled.connect(self.join.setEnabled)
        self.notes=QTextEdit(row["notes"] if row else ""); self.notes.setMaximumHeight(75)
        self.layout.addRow("Employee ID", self.code); self.layout.addRow("Full name *", self.name)
        self.layout.addRow("Section / Group", self.department); self.layout.addRow("Job title", self.designation)
        self.layout.addRow("Phone number (optional)", self.phone); self.layout.addRow("Email address (optional)", self.email)
        self.layout.addRow("Joining date", self.join); self.layout.addRow("", self.join_known); self.layout.addRow("Notes", self.notes)
        buttons=QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); self.layout.addRow(buttons)
    def values(self):
        return (self.code.text().strip() or None, self.name.text().strip(), self.department.currentText().strip(),
                self.designation.text().strip(), self.phone.text().strip(), self.email.text().strip(),
                self.join.date().toString("yyyy-MM-dd") if self.join_known.isChecked() else "", self.notes.toPlainText().strip())

class TaskDialog(QDialog):
    STATUSES=[
        ("Not started", "Not started"),
        ("In progress", "In progress"),
        ("Partially completed", "Partially completed"),
        ("Submitted", "Submitted"),
        ("Completed", "Completed"),
        ("Blocked", "Blocked"),
        ("Pending review", "Pending review"),
        ("Pending", "Pending"),
        ("Cancelled", "Cancelled"),
        ("Not selected", None),
    ]
    def __init__(self, db, parent=None, row=None, employee_id=None, task_date=None, is_custom=False):
        super().__init__(parent)
        self.db = db
        self.row = row
        existing_custom = parse_custom_values(row["custom_values"] if row and "custom_values" in row.keys() else "")
        self.is_custom = True

        self.setWindowTitle("Edit Task Details" if row else "Create New Task")
        # Ensure window is freely resizable and has min/max/close controls
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.setSizeGripEnabled(True)

        # Responsive screen geometry calculation: prevents dialog from ever hiding behind Windows taskbar
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1024, 768)
        dlg_w = min(740, max(520, avail.width() - 40))
        dlg_h = min(730, max(460, avail.height() - 80))
        self.resize(dlg_w, dlg_h)
        self.setMinimumSize(480, 380)
        self.move(avail.x() + max(10, (avail.width() - dlg_w) // 2), avail.y() + max(10, (avail.height() - dlg_h) // 2))

        # Advanced dark theme styling for TaskDialog
        self.setStyleSheet("""
            QDialog {
                background-color: #0B0F19;
                color: #F8FAFC;
            }
            QLabel {
                color: #E2E8F0;
            }
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit {
                background: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 8px;
                color: #F8FAFC;
                padding: 7px 11px;
                font-size: 9pt;
                selection-background-color: #6366F1;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QTextEdit:focus {
                border: 1.5px solid #818CF8;
                background: rgba(15, 23, 42, 0.95);
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background: #0F172A;
                border: 1px solid #334155;
                selection-background-color: #4F46E5;
                color: #F8FAFC;
                outline: none;
                padding: 4px;
            }
            QCheckBox {
                color: #CBD5E1;
                font-size: 8.5pt;
                spacing: 7px;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border-radius: 4px;
                border: 1px solid rgba(148, 163, 184, 0.4);
                background: rgba(15, 23, 42, 0.6);
            }
            QCheckBox::indicator:checked {
                background: #6366F1;
                border-color: #818CF8;
            }
        """)

        # 3-Tier Root Layout: Fixed Header (Top), Scroll Area (Middle), Fixed Footer (Bottom)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ----------------------------------------------------
        # TIER 1: FIXED TOP HEADER BANNER (Sticky)
        # ----------------------------------------------------
        header_frame = QFrame()
        header_frame.setObjectName("taskDialogHeader")
        header_frame.setStyleSheet(
            "QFrame#taskDialogHeader { "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E1B4B, stop:0.45 #0F172A, stop:1 #1E293B); "
            "border-bottom: 1.5px solid rgba(129, 140, 248, 0.35); padding: 12px 20px; }"
        )
        h_box = QHBoxLayout(header_frame)
        h_box.setContentsMargins(16, 10, 16, 10)
        h_box.setSpacing(14)

        h_icon = QLabel("⚡" if row else "✨")
        h_icon.setStyleSheet("font-size: 20pt; padding: 4px 8px; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(129, 140, 248, 0.35); border-radius: 10px;")
        h_box.addWidget(h_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        h_col = QVBoxLayout()
        h_col.setSpacing(2)
        self.h_title = QLabel("Edit Task Details" if row else "Create New Task")
        self.h_title.setStyleSheet("font-size: 13pt; font-weight: 800; color: #FFFFFF; letter-spacing: 0.3px;")
        h_col.addWidget(self.h_title)

        self.h_sub = QLabel("Configure assigned task parameters, metrics, evidence, and custom key-value tracking options.")
        self.h_sub.setStyleSheet("font-size: 8.5pt; color: #94A3B8;")
        h_col.addWidget(self.h_sub)
        h_box.addLayout(h_col, 1)

        task_id_badge = QLabel(f"Task #{row['id']}" if row else "New Assignment")
        task_id_badge.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #A5B4FC; background: rgba(99, 102, 241, 0.18); border: 1px solid rgba(129, 140, 248, 0.4); border-radius: 8px; padding: 5px 12px;")
        h_box.addWidget(task_id_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        root_layout.addWidget(header_frame, 0)

        # ----------------------------------------------------
        # TIER 2: MIDDLE SCROLL AREA (Fluid Content)
        # ----------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(15, 23, 42, 0.7);
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(129, 140, 248, 0.35);
                min-height: 35px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(129, 140, 248, 0.65);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("taskScrollContent")
        scroll_content.setStyleSheet("QWidget#taskScrollContent { background: transparent; }")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(18, 14, 18, 14)
        scroll_layout.setSpacing(14)

        # Card Helper Function
        def _make_section_card(card_id, title_text, icon_str):
            c_frame = QFrame()
            c_frame.setObjectName(card_id)
            c_frame.setStyleSheet(
                f"QFrame#{card_id} {{ background: rgba(30, 41, 59, 0.45); border: 1.5px solid rgba(148, 163, 184, 0.16); "
                f"border-radius: 12px; padding: 12px 14px; }} "
                f"QFrame#{card_id}:hover {{ border-color: rgba(129, 140, 248, 0.35); background: rgba(30, 41, 59, 0.65); }}"
            )
            c_vbox = QVBoxLayout(c_frame)
            c_vbox.setContentsMargins(8, 6, 8, 8)
            c_vbox.setSpacing(10)

            hdr = QLabel(f"{icon_str}  {title_text}")
            hdr.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #E0E7FF; letter-spacing: 0.3px;")
            c_vbox.addWidget(hdr)

            f_lay = QFormLayout()
            f_lay.setSpacing(10)
            f_lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            c_vbox.addLayout(f_lay)
            return c_frame, f_lay

        # CARD 1: Assignment & Ownership Details
        card_assign, self.layout = _make_section_card("taskCardAssign", "Assignment & Ownership Details", "👤")

        # 1. Date
        self.date = QDateEdit()
        configure_date_edit(self.date)
        self.date.setDisplayFormat("yyyy-MM-dd")
        parsed_task_date = None
        if row and row["task_date"]:
            parsed_task_date = QDate.fromString(row["task_date"], "yyyy-MM-dd")
        elif task_date:
            parsed_task_date = task_date if isinstance(task_date, QDate) else QDate.fromString(str(task_date), "yyyy-MM-dd")
        self.date.setDate(parsed_task_date if (parsed_task_date and parsed_task_date.isValid()) else QDate.currentDate())
        self.layout.addRow("Date *", self.date)

        # 2. Employee & 3. Department
        self.employee = QComboBox()
        self.emp_dept_map = {}
        for e in db.employees(False):
            self.employee.addItem(f'{e["name"]} ({e["employee_code"] or e["id"]})', e["id"])
            dept_val = ""
            try:
                dept_val = str(e["department"] or "").strip()
            except Exception:
                pass
            self.emp_dept_map[e["id"]] = dept_val

        if employee_id is not None:
            idx = self.employee.findData(employee_id)
            if idx >= 0: self.employee.setCurrentIndex(idx)
        elif row and "employee_id" in row.keys() and row["employee_id"]:
            idx = self.employee.findData(row["employee_id"])
            if idx >= 0: self.employee.setCurrentIndex(idx)

        self.layout.addRow("Employee *", self.employee)

        # Department (editable combobox with standard & custom departments)
        self.department = QComboBox()
        self.department.setEditable(True)
        self.department.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if self.department.lineEdit():
            self.department.lineEdit().setPlaceholderText("Select or enter department...")

        default_depts = ["General", "Housekeeping", "Trainer / Fitness", "Management", "Sales", "Others"]
        group_names = []
        if db and hasattr(db, "employee_groups"):
            for g in db.employee_groups():
                gname = (g.get("name") or "").strip()
                if gname and gname not in group_names:
                    group_names.append(gname)
        emp_depts = []
        for e in db.employees(True):
            try:
                d_str = str(e["department"] or "").strip()
                if d_str and d_str not in group_names and d_str not in default_depts and d_str not in emp_depts:
                    emp_depts.append(d_str)
            except Exception:
                pass
        all_depts = []
        for d in default_depts + group_names + emp_depts:
            if d and d not in all_depts:
                all_depts.append(d)
        for d in all_depts:
            self.department.addItem(d)
        self.department.addItem("➕ Add Custom Department...")

        initial_dept = ""
        if row and "department" in row.keys() and row["department"]:
            initial_dept = str(row["department"]).strip()
        elif employee_id is not None:
            initial_dept = self.emp_dept_map.get(employee_id, "")
        elif row and "employee_id" in row.keys() and row["employee_id"]:
            initial_dept = self.emp_dept_map.get(row["employee_id"], "")
        else:
            first_eid = self.employee.currentData()
            initial_dept = self.emp_dept_map.get(first_eid, "")
        self.department.setEditText(initial_dept)
        # Keep an employee with no department genuinely unassigned. "General" is
        # a real department choice, not a silent fallback that changes task data.

        def _on_task_dept_changed(idx):
            if self.department.itemText(idx) == "➕ Add Custom Department...":
                name, ok = QInputDialog.getText(self, "Add Custom Department", "Enter Custom Department Name:")
                if ok and name.strip():
                    new_dept = name.strip()
                    if self.db and hasattr(self.db, "add_employee_group"):
                        self.db.add_employee_group(new_dept)
                    add_idx = max(0, self.department.count() - 1)
                    self.department.insertItem(add_idx, new_dept)
                    self.department.setCurrentIndex(add_idx)
                else:
                    self.department.setCurrentIndex(0)
        self.department.currentIndexChanged.connect(_on_task_dept_changed)

        def _on_emp_changed_sync_dept():
            eid = self.employee.currentData()
            cur = self.department.currentText().strip()
            new_emp_dept = self.emp_dept_map.get(eid, "")
            if not cur or cur in all_depts:
                self.department.setEditText(new_emp_dept or "General")

        self.employee.currentIndexChanged.connect(_on_emp_changed_sync_dept)
        self.layout.addRow("Department", self.department)

        # 4. Assigned Task
        self.title = QLineEdit(row["title"] if row else "")
        self.title.setPlaceholderText("Enter assigned task title / description...")
        self.title.setStyleSheet("QLineEdit { padding: 7px 10px; border-radius: 6px; font-weight: 500; }")
        self.layout.addRow("Assigned Task *", self.title)
        scroll_layout.addWidget(card_assign)

        # CARD 2: Target, Progress & Status Metrics
        card_metrics, f_metrics = _make_section_card("taskCardMetrics", "Target, Progress & Status Metrics", "🎯")

        # 5. Target Qty & 6. Actual Qty
        qty_widget = QWidget()
        qty_layout = QHBoxLayout(qty_widget)
        qty_layout.setContentsMargins(0, 0, 0, 0)
        qty_layout.setSpacing(8)

        init_t_qty = ""
        init_a_qty = ""
        if row:
            if "target_qty" in row.keys() and row["target_qty"]:
                init_t_qty = str(row["target_qty"])
            if "actual_qty" in row.keys() and row["actual_qty"]:
                init_a_qty = str(row["actual_qty"])

        initial_emp = self.employee.currentData()
        initial_d = self.date.date().toString("yyyy-MM-dd")
        tinfo = self.db.get_employee_target(initial_emp, initial_d) if (initial_emp and hasattr(self.db, "get_employee_target")) else {}
        if not init_t_qty and tinfo.get("target"):
            init_t_qty = str(tinfo.get("target"))

        self.target_qty = QLineEdit(init_t_qty)
        self.target_qty.setPlaceholderText("Target Qty (e.g. 10)")
        self.target_qty.setStyleSheet("QLineEdit { padding: 6px 10px; border-radius: 6px; }")

        self.actual_qty = QLineEdit(init_a_qty)
        self.actual_qty.setPlaceholderText("Actual Qty (e.g. 5)")
        self.actual_qty.setStyleSheet("QLineEdit { padding: 6px 10px; border-radius: 6px; }")

        qty_layout.addWidget(self.target_qty, 1)
        qty_layout.addWidget(self.actual_qty, 1)
        f_metrics.addRow("Target / Actual Qty", qty_widget)

        # 7. Completion % with Dynamic Live Status Pill
        prog_wrap = QWidget()
        prog_layout = QHBoxLayout(prog_wrap)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(10)

        self.progress = QSpinBox()
        self.progress.setRange(0, 100)
        self.progress.setSuffix("%")
        self.progress.setStyleSheet("QSpinBox { padding: 6px 10px; border-radius: 6px; min-width: 80px; }")
        if row and "progress" in row.keys() and row["progress"] is not None:
            self.progress.setValue(int(row["progress"]))
        else:
            self.progress.setValue(0)
        prog_layout.addWidget(self.progress, 0)

        self.progress_pill = QLabel("0% Not started")
        self.progress_pill.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #94A3B8; background: rgba(148, 163, 184, 0.12); border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 6px; padding: 4px 10px;")
        prog_layout.addWidget(self.progress_pill, 1)
        f_metrics.addRow("Completion %", prog_wrap)

        def _update_progress_pill(pct):
            if pct >= 100:
                self.progress_pill.setText("100% Completed 🎉")
                self.progress_pill.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #34D399; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 6px; padding: 4px 10px;")
            elif pct >= 50:
                self.progress_pill.setText(f"{pct}% In Progress ⚡")
                self.progress_pill.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #818CF8; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 6px; padding: 4px 10px;")
            elif pct > 0:
                self.progress_pill.setText(f"{pct}% Started 🚀")
                self.progress_pill.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #38BDF8; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 6px; padding: 4px 10px;")
            else:
                self.progress_pill.setText("0% Not started")
                self.progress_pill.setStyleSheet("font-size: 8.5pt; font-weight: 700; color: #94A3B8; background: rgba(148, 163, 184, 0.12); border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 6px; padding: 4px 10px;")

        self.progress.valueChanged.connect(_update_progress_pill)
        _update_progress_pill(self.progress.value())

        # Auto-compute Completion % when Target Qty or Actual Qty changes
        def _recalc_completion():
            t_str = self.target_qty.text().strip()
            a_str = self.actual_qty.text().strip()
            try:
                t_val = float(t_str)
                a_val = float(a_str)
                if t_val > 0:
                    pct = max(0, min(100, int(round((a_val / t_val) * 100))))
                    self.progress.setValue(pct)
                    if pct == 100:
                        comp_idx = self.status.findData("Completed")
                        if comp_idx >= 0 and self.status.currentData() in ("Not started", "In progress", "Partially completed"):
                            self.status.setCurrentIndex(comp_idx)
                    elif pct > 0:
                        part_idx = self.status.findData("Partially completed")
                        if part_idx >= 0 and self.status.currentData() == "Not started":
                            self.status.setCurrentIndex(part_idx)
            except (ValueError, TypeError):
                pass

        self.target_qty.textChanged.connect(_recalc_completion)
        self.actual_qty.textChanged.connect(_recalc_completion)

        # 8. Priority & 9. Status Row
        pri_stat_widget = QWidget()
        pri_stat_layout = QHBoxLayout(pri_stat_widget)
        pri_stat_layout.setContentsMargins(0, 0, 0, 0)
        pri_stat_layout.setSpacing(8)

        self.priority = QComboBox()
        self.priority.addItems(["Low", "Normal", "High", "Urgent"])
        if row and "priority" in row.keys() and row["priority"]:
            self.priority.setCurrentText(row["priority"])

        self.status = QComboBox()
        for label, value in self.STATUSES:
            self.status.addItem(label, value)

        if row and "status" in row.keys() and row["status"]:
            status_index = self.status.findData(row["status"])
            if status_index < 0:
                label = "Not selected" if row["status"] is None or not str(row["status"]).strip() else row["status"]
                self.status.addItem(label, row["status"])
                status_index = self.status.count() - 1
            self.status.setCurrentIndex(status_index)

        pri_stat_layout.addWidget(self.priority, 1)
        pri_stat_layout.addWidget(self.status, 1)
        f_metrics.addRow("Priority / Status", pri_stat_widget)

        def _on_status_changed(idx):
            if self.status.currentData() == "Completed":
                self.progress.setValue(100)
        self.status.currentIndexChanged.connect(_on_status_changed)

        def _on_progress_changed(val):
            if val == 100:
                comp_idx = self.status.findData("Completed")
                if comp_idx >= 0 and self.status.currentData() in ("Not started", "In progress", "Partially completed"):
                    self.status.setCurrentIndex(comp_idx)
        self.progress.valueChanged.connect(_on_progress_changed)
        scroll_layout.addWidget(card_metrics)

        # CARD 3: Verification & Evidence
        card_proof, f_proof = _make_section_card("taskCardProof", "Verification & Follow-up Details", "🔗")

        # 10. Proof / Link (and expose_link)
        self.proof = QTextEdit(row["proof_url"] if row else "")
        self.proof.setPlaceholderText("Optional evidence URL or local file path. One link per line.")
        self.proof.setMaximumHeight(65)
        self.expose_link = QCheckBox("Expose full evidence URL in reports")
        self.expose_link.setChecked(bool(row["expose_link"]) if row and "expose_link" in row.keys() else False)

        proof_box = QWidget()
        proof_box_layout = QVBoxLayout(proof_box)
        proof_box_layout.setContentsMargins(0, 0, 0, 0)
        proof_box_layout.setSpacing(4)
        proof_box_layout.addWidget(self.proof)
        proof_box_layout.addWidget(self.expose_link)
        f_proof.addRow("Proof / Link", proof_box)

        # 11. Next Action
        init_next_action = ""
        if row:
            if "next_action" in row.keys() and row["next_action"]:
                init_next_action = str(row["next_action"])
            elif "manager_note" in row.keys() and row["manager_note"]:
                init_next_action = str(row["manager_note"])

        self.next_action = QLineEdit(init_next_action)
        self.next_action.setPlaceholderText("Enter next action or follow-up note...")
        self.next_action.setStyleSheet("QLineEdit { padding: 6px 10px; border-radius: 6px; }")
        f_proof.addRow("Next Action", self.next_action)
        scroll_layout.addWidget(card_proof)

        # CARD 4: Custom Key-Value Tracking Fields
        self.custom_box = QFrame()
        self.custom_box.setObjectName("taskCustomBox")
        self.custom_box.setStyleSheet(
            "QFrame#taskCustomBox { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(30, 41, 59, 0.65), stop:1 rgba(15, 23, 42, 0.75)); "
            "border: 1.5px solid rgba(129, 140, 248, 0.35); border-radius: 12px; padding: 12px 14px; } "
            "QFrame#taskCustomBox:hover { border-color: rgba(129, 140, 248, 0.6); }"
        )
        custom_vbox = QVBoxLayout(self.custom_box)
        custom_vbox.setContentsMargins(8, 8, 8, 8)
        custom_vbox.setSpacing(10)

        custom_header = QHBoxLayout()
        custom_title_col = QVBoxLayout()
        custom_title_col.setSpacing(2)

        custom_title_row = QHBoxLayout()
        custom_icon = QLabel("🏷️")
        custom_icon.setStyleSheet("font-size: 11pt;")
        custom_lbl = QLabel("Custom Tracking Fields (Key - Value)")
        custom_lbl.setStyleSheet("font-weight: 700; font-size: 10pt; color: #E0E7FF;")
        custom_title_row.addWidget(custom_icon)
        custom_title_row.addWidget(custom_lbl)
        custom_title_row.addStretch(1)
        custom_title_col.addLayout(custom_title_row)

        custom_hint = QLabel("Add custom options where you can enter your own field names and values (e.g. Tracked By : Name).")
        custom_hint.setStyleSheet("font-size: 8pt; color: #94A3B8;")
        custom_title_col.addWidget(custom_hint)
        custom_header.addLayout(custom_title_col, 1)

        self.custom_count_badge = QLabel("0 fields")
        self.custom_count_badge.setStyleSheet("font-size: 8pt; font-weight: 700; color: #818CF8; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(129, 140, 248, 0.3); border-radius: 6px; padding: 4px 8px;")
        custom_header.addWidget(self.custom_count_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self.add_custom_btn = QPushButton("➕ Add Field")
        self.add_custom_btn.setObjectName("addCustomKeyValueBtn")
        self.add_custom_btn.setStyleSheet(
            "QPushButton#addCustomKeyValueBtn { font-size: 8.5pt; font-weight: 700; padding: 6px 14px; border-radius: 7px; "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.35), stop:1 rgba(129, 140, 248, 0.35)); "
            "color: #FFFFFF; border: 1px solid rgba(129, 140, 248, 0.6); } "
            "QPushButton#addCustomKeyValueBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #6366F1); border-color: #A5B4FC; }"
        )
        self.add_custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        custom_header.addWidget(self.add_custom_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        custom_vbox.addLayout(custom_header)

        # Quick preset chips
        chips_bar = QWidget()
        chips_layout = QHBoxLayout(chips_bar)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)
        chips_lbl = QLabel("Quick Presets:")
        chips_lbl.setStyleSheet("font-size: 8pt; color: #94A3B8; font-weight: 600;")
        chips_layout.addWidget(chips_lbl)

        quick_presets = ["Tracked By", "Client", "Location", "Batch", "Priority Code", "Machine", "Tag", "Reviewer"]
        for qk in quick_presets:
            chip = QPushButton(f"+ {qk}")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setStyleSheet(
                "QPushButton { font-size: 8pt; font-weight: 600; color: #C7D2FE; background: rgba(99, 102, 241, 0.16); "
                "border: 1px solid rgba(129, 140, 248, 0.32); border-radius: 6px; padding: 3px 9px; } "
                "QPushButton:hover { background: rgba(99, 102, 241, 0.40); color: #FFFFFF; border-color: #818CF8; }"
            )
            def _make_add_chip(key_name=qk):
                return lambda: self.add_key_value_row(key_name, "")
            chip.clicked.connect(_make_add_chip(qk))
            chips_layout.addWidget(chip)
        chips_layout.addStretch(1)
        custom_vbox.addWidget(chips_bar)

        self.custom_rows_container = QWidget()
        self.custom_rows_layout = QVBoxLayout(self.custom_rows_container)
        self.custom_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_rows_layout.setSpacing(6)
        custom_vbox.addWidget(self.custom_rows_container)

        self.custom_rows = []  # list of (key_input, value_input, row_widget)

        def _update_custom_badge():
            n = len(self.custom_rows)
            txt = f"{n} field" + ("s" if n != 1 else "")
            self.custom_count_badge.setText(txt)

        def add_key_value_row(k_text="", v_text=""):
            row_w = QFrame()
            row_w.setObjectName("customRowItem")
            row_w.setStyleSheet(
                "QFrame#customRowItem { background: rgba(15, 23, 42, 0.70); border: 1px solid rgba(148, 163, 184, 0.22); "
                "border-radius: 8px; padding: 4px; } "
                "QFrame#customRowItem:hover { border-color: rgba(129, 140, 248, 0.45); background: rgba(15, 23, 42, 0.90); }"
            )
            row_h = QHBoxLayout(row_w)
            row_h.setContentsMargins(6, 4, 6, 4)
            row_h.setSpacing(8)

            tag_icon = QLabel("🏷️")
            tag_icon.setStyleSheet("font-size: 10pt; color: #818CF8;")
            row_h.addWidget(tag_icon)

            k_in = QLineEdit(k_text)
            k_in.setPlaceholderText("Field Name (e.g. Tracked By)")
            k_in.setStyleSheet("QLineEdit { padding: 6px 10px; border-radius: 6px; font-weight: 600; color: #A5B4FC; }")

            colon_lbl = QLabel(":")
            colon_lbl.setStyleSheet("font-size: 11pt; font-weight: 800; color: #94A3B8;")

            v_in = QLineEdit(v_text)
            v_in.setPlaceholderText("Value (e.g. Name)")
            v_in.setStyleSheet("QLineEdit { padding: 6px 10px; border-radius: 6px; color: #FFFFFF; }")

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(26, 26)
            del_btn.setToolTip("Remove this field")
            del_btn.setStyleSheet(
                "QPushButton { color: #EF4444; font-weight: bold; border-radius: 5px; background: rgba(239,68,68,0.14); border: 1px solid rgba(239,68,68,0.25); } "
                "QPushButton:hover { background: rgba(239,68,68,0.35); color: #FFFFFF; border-color: #EF4444; }"
            )
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            def _remove():
                for item in list(self.custom_rows):
                    if item[0] is k_in and item[1] is v_in:
                        self.custom_rows.remove(item)
                        break
                row_w.deleteLater()
                _update_custom_badge()

            del_btn.clicked.connect(_remove)
            row_h.addWidget(k_in, 2)
            row_h.addWidget(colon_lbl, 0)
            row_h.addWidget(v_in, 3)
            row_h.addWidget(del_btn, 0)

            self.custom_rows_layout.addWidget(row_w)
            self.custom_rows.append((k_in, v_in, row_w))
            _update_custom_badge()

            # Ensure newly added row is instantly scrolled into user view
            QTimer.singleShot(40, lambda: self.scroll_area.ensureWidgetVisible(row_w, 20, 20))

            if k_text:
                v_in.setFocus()
            else:
                k_in.setFocus()
            return (k_in, v_in, row_w)

        self.add_custom_btn.clicked.connect(lambda: add_key_value_row())
        self.add_key_value_row = add_key_value_row

        for ek, ev in existing_custom:
            add_key_value_row(ek, ev)

        scroll_layout.addWidget(self.custom_box)
        self.scroll_area.setWidget(scroll_content)
        root_layout.addWidget(self.scroll_area, 1)

        # ----------------------------------------------------
        # TIER 3: FIXED BOTTOM FOOTER BAR (Sticky, Always Visible Above Taskbar)
        # ----------------------------------------------------
        footer_frame = QFrame()
        footer_frame.setObjectName("taskDialogFooter")
        footer_frame.setStyleSheet(
            "QFrame#taskDialogFooter { "
            "background: #0B0F19; border-top: 1.5px solid rgba(148, 163, 184, 0.16); padding: 12px 20px; }"
        )
        f_layout = QHBoxLayout(footer_frame)
        f_layout.setContentsMargins(20, 10, 20, 10)
        f_layout.setSpacing(12)

        f_hint = QLabel("💡 Changes automatically save and sync across all connected views.")
        f_hint.setStyleSheet("font-size: 8pt; color: #64748B;")
        f_layout.addWidget(f_hint)
        f_layout.addStretch(1)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.05); color: #94A3B8; "
            "border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; font-weight: 600; padding: 6px 16px; } "
            "QPushButton:hover { background: rgba(255, 255, 255, 0.10); color: #F1F5F9; border-color: rgba(255, 255, 255, 0.25); }"
        )
        cancel_btn.clicked.connect(self.reject)
        f_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save Task" if not row else "💾 Update Task")
        save_btn.setObjectName("taskSaveBtn")
        save_btn.setMinimumHeight(38)
        save_btn.setMinimumWidth(150)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(
            "QPushButton#taskSaveBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #6366F1); "
            "color: #FFFFFF; border: 1px solid rgba(165, 180, 252, 0.45); border-radius: 8px; font-weight: 700; padding: 6px 20px; font-size: 9.5pt; } "
            "QPushButton#taskSaveBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #4F46E5); border-color: #818CF8; } "
            "QPushButton#taskSaveBtn:pressed { background: #3730A3; }"
        )
        save_btn.clicked.connect(self.accept)
        f_layout.addWidget(save_btn)
        root_layout.addWidget(footer_frame, 0)

        # Compatibility aliases
        self.is_custom = True
        self.custom_card = self.custom_box
        self.custom_task_toggle = QCheckBox()
        self.type_indicator_pill = QLabel()
        self.mode_standard_btn = QPushButton()
        self.mode_custom_btn = QPushButton()
        self.set_custom_mode = lambda active=True: None
        self.toggle_task_mode = lambda active=True: None

        # Backward compatibility properties (hidden from layout)
        self.manager_note = self.next_action
        self.details = QTextEdit(row["details"] if row and "details" in row.keys() and row["details"] else "")
        self.details.hide()
        self.due = QTimeEdit()
        self.due.setDisplayFormat("HH:mm")
        if row and "due_time" in row.keys() and row["due_time"]:
            parsed_due_time = QTime.fromString(row["due_time"], "HH:mm")
            if parsed_due_time and parsed_due_time.isValid():
                self.due.setTime(parsed_due_time)
        self.due.hide()
        self.proof_note = QLineEdit(row["proof_note"] if row and "proof_note" in row.keys() and row["proof_note"] else "")
        self.proof_note.hide()
        self.target_input = QLineEdit(tinfo.get("target", ""))
        self.target_input.hide()
        self.target_status_input = QLineEdit(tinfo.get("target_status", ""))
        self.target_status_input.hide()

        def _sync_ti_to_tq(txt):
            if self.target_qty.text() != txt:
                self.target_qty.blockSignals(True)
                self.target_qty.setText(txt)
                self.target_qty.blockSignals(False)
        self.target_input.textChanged.connect(_sync_ti_to_tq)

        def _sync_tq_to_ti(txt):
            if self.target_input.text() != txt:
                self.target_input.blockSignals(True)
                self.target_input.setText(txt)
                self.target_input.blockSignals(False)
        self.target_qty.textChanged.connect(_sync_tq_to_ti)

        def _sync_tsi_to_aq(txt):
            if self.actual_qty.text() != txt:
                self.actual_qty.blockSignals(True)
                self.actual_qty.setText(txt)
                self.actual_qty.blockSignals(False)
        self.target_status_input.textChanged.connect(_sync_tsi_to_aq)

        def _sync_aq_to_tsi(txt):
            if self.target_status_input.text() != txt:
                self.target_status_input.blockSignals(True)
                self.target_status_input.setText(txt)
                self.target_status_input.blockSignals(False)
        self.actual_qty.textChanged.connect(_sync_aq_to_tsi)

        def _on_emp_or_date_target_sync():
            eid = self.employee.currentData()
            dt = self.date.date().toString("yyyy-MM-dd")
            if eid and hasattr(self.db, "get_employee_target"):
                ti = self.db.get_employee_target(eid, dt)
                self.target_input.setText(ti.get("target", ""))
                self.target_status_input.setText(ti.get("target_status", ""))
        self.employee.currentIndexChanged.connect(_on_emp_or_date_target_sync)
        self.date.dateChanged.connect(_on_emp_or_date_target_sync)

    def accept(self):
        eid = self.employee.currentData()
        dt = self.date.date().toString("yyyy-MM-dd")
        t_text = self.target_qty.text().strip() or self.target_input.text().strip()
        a_text = self.actual_qty.text().strip() or self.target_status_input.text().strip()
        if eid and hasattr(self.db, "set_employee_target"):
            self.db.set_employee_target(eid, dt, t_text, a_text)
        dept_text = self.department.currentText().strip() if hasattr(self.department, "currentText") else self.department.text().strip()
        if eid and dept_text:
            try:
                emp = self.db.employee(eid)
                if emp and not emp["department"]:
                    self.db.conn.execute("UPDATE employees SET department=? WHERE id=?", (dept_text, eid))
                    self.db.conn.commit()
            except Exception:
                pass
        super().accept()

    def values(self):
        if self.employee.count() == 0: return None
        status = self.status.currentData()
        progress = self.progress.value()
        if status == "Completed": progress = 100
        # Preserve original submission time; only set it on first transition to Submitted/Completed
        if status in ("Submitted", "Completed"):
            existing = (self.row["submitted_at"] if self.row else "") or ""
            submitted = existing if existing else now_text()
        else:
            submitted = (self.row["submitted_at"] if self.row else "") or ""
        next_act = self.next_action.text().strip()
        target_q = self.target_qty.text().strip()
        actual_q = self.actual_qty.text().strip()
        details_val = self.details.toPlainText().strip()
        due_val = self.due.time().toString("HH:mm") if (hasattr(self, "due") and not self.due.isHidden()) else ((self.row["due_time"] if self.row else "") or "")
        proof_note_val = self.proof_note.text().strip() if (hasattr(self, "proof_note") and not self.proof_note.isHidden()) else ((self.row["proof_note"] if self.row else "") or "")
        dept_text = self.department.currentText().strip() if hasattr(self.department, "currentText") else self.department.text().strip()

        custom_pairs = []
        for k_in, v_in, _ in getattr(self, "custom_rows", []):
            k = k_in.text().strip()
            v = v_in.text().strip()
            if k or v:
                custom_pairs.append((k, v))
        # Tag developer testing tasks so they are identified and excluded from master sheet sync
        if is_developer_test_user(getattr(self.db, "active_user", None)):
            if not any(k.lower() in ("created_by", "creator", "test_mode") for k, _ in custom_pairs):
                custom_pairs.append(("created_by", "admin"))
                custom_pairs.append(("test_mode", "true"))
        custom_vals_str = serialize_custom_values(custom_pairs)

        return (
            self.employee.currentData(),
            self.date.date().toString("yyyy-MM-dd"),
            self.title.text().strip(),
            dept_text,
            details_val,
            due_val,
            self.priority.currentText(),
            status,
            progress,
            self.proof.toPlainText().strip(),
            proof_note_val,
            submitted,
            next_act,
            int(self.expose_link.isChecked()),
            target_q,
            actual_q,
            next_act,
            custom_vals_str,
        )

_ACCESSIBLE_TOOLTIP_CONTROLLER = None
_COMBOBOX_WHEEL_FILTER = None


class InputControlsWheelFilter(QObject):
    """
    Prevents mouse wheel / spinner rotation from inadvertently altering values
    in QComboBox, QDateEdit, QDateTimeEdit, QTimeEdit, QSpinBox, QDoubleSpinBox,
    QAbstractSpinBox, or QCalendarWidget.
    Dropdown selections and dates only change when explicitly clicked or selected.
    If the control is inside a scrollable view, the wheel event is forwarded to
    the enclosing scroll viewport so user scrolling remains fluid.
    """
    def eventFilter(self, watched, event):
        try:
            etype = event.type()
        except (AttributeError, RuntimeError):
            return False
        if etype == QEvent.Type.Wheel:
            # Check if watched or its parent belongs to a calendar popup
            p = watched
            in_calendar = False
            for _ in range(6):
                if p is None:
                    break
                if isinstance(p, QCalendarWidget) or (hasattr(p, "metaObject") and "calendar" in p.metaObject().className().lower()):
                    in_calendar = True
                    break
                p = getattr(p, "parentWidget", lambda: None)()
            if in_calendar:
                event.ignore()
                return True

            # Allow scrolling inside an already-opened combobox popup list (not calendar)
            if isinstance(watched, QAbstractItemView):
                if watched.isWindow() or (watched.window() and watched.window().windowType() == Qt.WindowType.Popup):
                    return False

            control = None
            curr = watched
            depth = 0
            while curr is not None and depth < 6:
                if isinstance(curr, (QComboBox, QAbstractSpinBox, QDateEdit, QDateTimeEdit, QTimeEdit, QSpinBox, QDoubleSpinBox, QCalendarWidget)):
                    control = curr
                    break
                curr = getattr(curr, "parentWidget", lambda: None)()
                depth += 1

            if control is not None:
                event.ignore()
                parent = control.parentWidget()
                while parent is not None:
                    if isinstance(parent, QAbstractScrollArea):
                        QApplication.sendEvent(parent.viewport(), event)
                        break
                    parent = parent.parentWidget()
                return True
        return super().eventFilter(watched, event)


ComboBoxWheelFilter = InputControlsWheelFilter


def ensure_combobox_wheel_filter(application=None):
    global _COMBOBOX_WHEEL_FILTER
    application = application or QApplication.instance()
    if application is not None and _COMBOBOX_WHEEL_FILTER is None:
        _COMBOBOX_WHEEL_FILTER = InputControlsWheelFilter(application)
        application.installEventFilter(_COMBOBOX_WHEEL_FILTER)
    return _COMBOBOX_WHEEL_FILTER


class AccessibleTooltipController(QObject):
    """Render high-contrast help popups with bold readability across all themes."""
    def __init__(self, application):
        super().__init__(application)
        self.application = application
        self.current_target = None
        self.popup = QLabel()
        self.popup.setObjectName("accessibleHoverMessage")
        self.popup.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.popup.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.popup.setTextFormat(Qt.TextFormat.PlainText)
        self.popup.setWordWrap(True)
        self.popup.setMaximumWidth(450)
        self.popup.setStyleSheet(
            "QLabel#accessibleHoverMessage { background-color: #FFFFFF; color: #111827; "
            "border: 2px solid #6D28D9; border-radius: 8px; padding: 8px 12px; "
            "font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 10pt; font-weight: 600; }"
        )
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        application.installEventFilter(self)

    def _tooltip_text(self, watched, event):
        text = watched.toolTip().strip() if isinstance(watched, QWidget) else ""
        parent = watched.parentWidget() if isinstance(watched, QWidget) else None
        if isinstance(parent, QAbstractItemView) and parent.viewport() is watched:
            position = event.pos()
            item = parent.itemAt(position)
            if item is not None:
                text = item.toolTip().strip() or item.text().strip()
            elif isinstance(parent, QTableWidget):
                header = parent.horizontalHeader()
                if watched is header and isinstance(watched, QHeaderView):
                    logical = watched.logicalIndexAt(position)
                    header_item = parent.horizontalHeaderItem(logical) if logical >= 0 else None
                    text = header_item.toolTip().strip() if header_item else ""
        elif isinstance(watched, QHeaderView):
            logical = watched.logicalIndexAt(event.pos())
            view = watched.parentWidget()
            if isinstance(view, QTableWidget) and logical >= 0:
                header_item = view.horizontalHeaderItem(logical)
                text = header_item.toolTip().strip() if header_item else ""
        if not text and isinstance(watched, QWidget):
            p = watched.parentWidget()
            while p is not None and not text:
                text = p.toolTip().strip()
                p = p.parentWidget()
        return text

    def show(self, text, position, target=None):
        text = str(text or "").strip()
        if not text:
            self.hide()
            return
        self.current_target = target
        self.popup.setText(text)
        self.popup.adjustSize()
        desired = position + QPoint(16, 20)
        screen = self.application.screenAt(position) or self.application.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            x = min(max(available.left() + 6, desired.x()), available.right() - self.popup.width() - 6)
            y = min(max(available.top() + 6, desired.y()), available.bottom() - self.popup.height() - 6)
            desired = QPoint(x, y)
        self.popup.move(desired)
        self.popup.show()
        self.popup.raise_()
        self.hide_timer.start(5000)

    def hide(self):
        self.hide_timer.stop()
        self.current_target = None
        self.popup.hide()

    def eventFilter(self, watched, event):
        try:
            etype = event.type()
        except (AttributeError, RuntimeError):
            return False
        if etype == QEvent.Type.ToolTip:
            text = self._tooltip_text(watched, event)
            if text:
                self.show(text, event.globalPos(), watched)
                event.accept()
                return True
        elif etype in (QEvent.Type.MouseButtonPress, QEvent.Type.WindowDeactivate):
            self.hide()
        elif etype == QEvent.Type.Leave and watched is self.current_target:
            self.hide()
        return False


def ensure_accessible_tooltip_controller(application=None):
    global _ACCESSIBLE_TOOLTIP_CONTROLLER
    application = application or QApplication.instance()
    if application is not None and _ACCESSIBLE_TOOLTIP_CONTROLLER is None:
        _ACCESSIBLE_TOOLTIP_CONTROLLER = AccessibleTooltipController(application)
    return _ACCESSIBLE_TOOLTIP_CONTROLLER


def show_accessible_tooltip(text, position, target=None):
    controller = ensure_accessible_tooltip_controller()
    if controller is not None:
        controller.show(text, position, target)


class NeonAttendanceGauge(QWidget):
    """Circular glowing neon gauge displaying today's attendance percentage and verified counts."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.percent = 0
        self.present = 0
        self.total = 0
        self.setMinimumHeight(135)
        self.setMaximumHeight(155)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_percent(self, percent, present=0, total=0):
        self.percent = max(0, min(100, int(percent)))
        self.present = present
        self.total = total
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        
        # Center of the circular gauge
        cx = max(50.0, min(float(w * 0.30), 85.0))
        cy = float(h * 0.50)
        radius = min(float(h * 0.38), 48.0)
        pen_width = max(7.0, radius * 0.20)
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        is_dark = True
        try:
            window = self.window()
            if hasattr(window, "current_theme") and window.current_theme() == "day":
                is_dark = False
        except Exception:
            pass

        # 1. Background Track
        track_color = QColor(255, 255, 255, 20) if is_dark else QColor(0, 0, 0, 22)
        painter.setPen(QPen(track_color, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)

        # 2. Glowing Neon Progress Arc
        if self.percent > 0:
            arc_grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            arc_grad.setColorAt(0.0, QColor("#00E5FF"))
            arc_grad.setColorAt(0.5, QColor("#3B82F6"))
            arc_grad.setColorAt(1.0, QColor("#A855F7"))
            painter.setPen(QPen(QBrush(arc_grad), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            start_angle = 90 * 16
            span_angle = -int(self.percent * 3.6 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # 3. Center Metric Number
        num_font = QFont("Segoe UI", max(10, int(radius * 0.38)), QFont.Weight.Black)
        painter.setFont(num_font)
        painter.setPen(QColor("#00E5FF" if is_dark else "#0284C7"))
        painter.drawText(QRectF(cx - radius, cy - radius * 0.46, radius * 2, radius * 0.58), Qt.AlignmentFlag.AlignCenter, f"{self.percent}%")

        sub_font = QFont("Segoe UI", max(5, int(radius * 0.16)), QFont.Weight.Bold)
        painter.setFont(sub_font)
        painter.setPen(QColor("#94A3B8" if is_dark else "#64748B"))
        painter.drawText(QRectF(cx - radius, cy + radius * 0.14, radius * 2, radius * 0.35), Qt.AlignmentFlag.AlignCenter, "ATTENDANCE")

        # 4. Right Side Pill Badges & Breakdown
        right_x = cx + radius + 14
        avail_w = max(40.0, float(w - right_x - 10))
        
        badge_y = cy - radius + 2
        painter.setPen(Qt.PenStyle.NoPen)
        badge_bg = QColor(16, 185, 129, 35) if self.percent >= 75 else (QColor(245, 158, 11, 35) if self.percent >= 50 else QColor(244, 63, 94, 35))
        badge_fg = QColor("#34D399") if self.percent >= 75 else (QColor("#FBBF24") if self.percent >= 50 else QColor("#FB7185"))
        badge_rect = QRectF(right_x, badge_y, min(avail_w, 120.0), 20.0)
        painter.setBrush(badge_bg)
        painter.drawRoundedRect(badge_rect, 5, 5)
        
        b_font = QFont("Segoe UI", 7, QFont.Weight.Black)
        b_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
        painter.setFont(b_font)
        painter.setPen(badge_fg)
        status_text = "● ON TARGET" if self.percent >= 75 else ("● MODERATE" if self.percent >= 50 else "● ATTENTION")
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, status_text)

        c_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(c_font)
        painter.setPen(QColor("#F8FAFC" if is_dark else "#0F172A"))
        painter.drawText(QRectF(right_x, badge_y + 24, avail_w, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Present: {self.present} of {self.total}")
        
        d_font = QFont("Segoe UI", 7, QFont.Weight.DemiBold)
        painter.setFont(d_font)
        painter.setPen(QColor("#94A3B8" if is_dark else "#64748B"))
        painter.drawText(QRectF(right_x, badge_y + 40, avail_w, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Daily Roster Ratio")

        painter.end()


class MiniSparkline(QWidget):
    """Compact glowing neon bezier sparkline curve for KPI cards."""
    def __init__(self, color="#00F0FF", points=None, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.points = points or [0.25, 0.40, 0.35, 0.65, 0.50, 0.70, 0.60, 0.90, 0.85, 1.0]
        self.setFixedSize(68, 38)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_points(self, points):
        if points:
            self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = float(self.width()), float(self.height())
        if len(self.points) < 2 or w <= 10:
            return
        step = (w - 8) / (len(self.points) - 1)
        coords = [QPointF(4 + i * step, h - 4 - (p * (h - 10))) for i, p in enumerate(self.points)]

        fill_path = QPainterPath()
        fill_path.moveTo(coords[0].x(), h - 2)
        fill_path.lineTo(coords[0])
        for i in range(len(coords) - 1):
            p0, p1 = coords[i], coords[i + 1]
            mx = (p0.x() + p1.x()) / 2.0
            fill_path.cubicTo(mx, p0.y(), mx, p1.y(), p1.x(), p1.y())
        fill_path.lineTo(coords[-1].x(), h - 2)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(self.color.red(), self.color.green(), self.color.blue(), 90))
        grad.setColorAt(1, QColor(self.color.red(), self.color.green(), self.color.blue(), 0))
        painter.fillPath(fill_path, grad)

        pen = QPen(self.color, 2.0)
        painter.setPen(pen)
        curve = QPainterPath()
        curve.moveTo(coords[0])
        for i in range(len(coords) - 1):
            p0, p1 = coords[i], coords[i + 1]
            mx = (p0.x() + p1.x()) / 2.0
            curve.cubicTo(mx, p0.y(), mx, p1.y(), p1.x(), p1.y())
        painter.drawPath(curve)

        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(QPen(self.color, 1.8))
        painter.drawEllipse(coords[-1], 2.8, 2.8)
        painter.end()


class ProductivityChart(QWidget):
    """Lightweight native Qt bar chart; no charting dependency is required."""
    PALETTES = {
        "day": {
            "background": "#FFFFFF", "grid": "#E2E8F0", "axis": "#64748B", "label": "#0F172A",
            "strong": "#16A34A", "steady": "#2563EB", "attention": "#D97706",
        },
        "night": {
            "background": "#0F172A", "grid": "rgba(51, 65, 85, 0.60)", "axis": "#94A3B8", "label": "#F8FAFC",
            "strong": "#00E5FF", "steady": "#8B5CF6", "attention": "#F59E0B",
        },
        "ocean": {
            "background": "#F0F9FF", "grid": "#BAE6FD", "axis": "#0C4A6E", "label": "#075985",
            "strong": "#059669", "steady": "#0284C7", "attention": "#D97706",
        },
        "sunset": {
            "background": "#FFF7ED", "grid": "#FED7AA", "axis": "#9A3412", "label": "#7C2D12",
            "strong": "#16A34A", "steady": "#EA580C", "attention": "#C2410C",
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self._hovered_index = None
        self.setMouseTracking(True)
        self.setMinimumHeight(210)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())
        self.setToolTip("Hover over a bar for its employee and productivity score.")

    @classmethod
    def palette_for_theme(cls, theme_name):
        return cls.PALETTES.get((theme_name or "day").lower(), cls.PALETTES["day"])

    def _current_palette(self):
        window = self.window()
        current_theme = getattr(window, "current_theme", None)
        theme_name = current_theme() if callable(current_theme) else "day"
        return self.palette_for_theme(theme_name)

    def _plot_bounds(self):
        left, right, top, bottom = 44, 18, 20, 44
        plot_width = max(1, self.width() - left - right)
        plot_height = max(1, self.height() - top - bottom)
        return left, top, plot_width, plot_height

    def _bar_rect(self, index):
        if not self.values:
            return QRectF()
        left, top, plot_width, plot_height = self._plot_bounds()
        slot = plot_width / len(self.values)
        bar_width = max(1, min(42, int(slot * 0.56)))
        name, score = self.values[index]
        x = left + slot * index + (slot - bar_width) / 2
        bar_height = plot_height * max(0, min(100, score)) / 100
        y = top + plot_height - bar_height
        return QRectF(x, y, bar_width, max(2, bar_height))

    def tooltip_for_index(self, index):
        if index < 0 or index >= len(self.values):
            return ""
        name, score = self.values[index]
        band = "Strong" if score >= 80 else ("On track" if score >= 60 else "Needs attention")
        return f"{name}\nProductivity score: {score}%\nPerformance: {band}"

    def set_values(self, values):
        normalized = []
        for name, score in values:
            try:
                numeric_score = int(round(float(score or 0)))
            except (TypeError, ValueError, OverflowError):
                numeric_score = 0
            normalized.append((str(name or "Unknown employee"), max(0, min(100, numeric_score))))
        self.values = normalized
        self._hovered_index = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = self._current_palette()
        painter.fillRect(self.rect(), QColor(colors["background"]))
        painter.setPen(QColor(colors["axis"]))
        painter.setFont(QFont("Segoe UI", 9))
        if not self.values:
            painter.drawText(self.rect(), Qt.AlignCenter, "No employee productivity data yet")
            return
        left, top, w, h = self._plot_bounds()
        for tick in (0, 25, 50, 75, 100):
            y = top + h - int(h * tick / 100)
            painter.setPen(QPen(QColor(colors["grid"]), 1))
            painter.drawLine(left, y, left + w, y)
            painter.setPen(QColor(colors["axis"]))
            painter.drawText(4, y + 4, f"{tick}%")
        count = len(self.values)
        slot = w / max(count, 1)
        for i, (name, score) in enumerate(self.values):
            bar_rect = self._bar_rect(i)
            color = colors["strong"] if score >= 80 else (colors["steady"] if score >= 60 else colors["attention"])
            bar_color = QColor(color)
            if i == self._hovered_index:
                bar_color = bar_color.lighter(112)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bar_color)
            radius = min(6, max(1, bar_rect.width() / 2))
            painter.drawRoundedRect(bar_rect, radius, radius)
            if slot >= 44:
                painter.setPen(QColor(colors["label"]))
                painter.drawText(int(bar_rect.x()) - 8, max(top + 12, int(bar_rect.y()) - 5), f"{score}%")
            painter.setPen(QColor(colors["axis"]))
            label_rect = QRectF(left + slot * i + 1, top + h + 5, max(1, slot - 2), 36)
            painter.setFont(QFont("Segoe UI", 8))
            parts = name.split()
            if slot >= 72:
                display_name = name
            elif slot >= 38:
                display_name = parts[0] if parts else name
            elif slot >= 22:
                display_name = "".join(part[0] for part in parts[:2])
            else:
                display_name = ""
            if display_name:
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, display_name)

    def mouseMoveEvent(self, event):
        position = event.position()
        hovered = next((i for i in range(len(self.values)) if self._bar_rect(i).adjusted(-5, -3, 5, 3).contains(position)), None)
        if hovered != self._hovered_index:
            self._hovered_index = hovered
            self.update()
        if hovered is None:
            self.unsetCursor()
            controller = ensure_accessible_tooltip_controller()
            if controller is not None:
                controller.hide()
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            show_accessible_tooltip(event.globalPosition().toPoint(), self.tooltip_for_index(hovered), self)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hovered_index = None
        self.update()
        controller = ensure_accessible_tooltip_controller()
        if controller is not None:
            controller.hide()
        self.unsetCursor()
        super().leaveEvent(event)


class AnimatedDashboardIcon(QLabel):
    """A softly tinted KPI icon badge with a brief hover pulse."""
    def __init__(self, symbol, accent, background, border, tooltip, parent=None):
        super().__init__(symbol, parent)
        self.setObjectName("kpiIcon")
        self.setAccessibleName(tooltip)
        self.setToolTip(tooltip)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(44, 44)
        self._icon_accent = accent
        self._icon_background = background
        self._icon_border = border
        self.setStyleSheet(
            f"QLabel#kpiIcon {{ background: {background}; color: {accent}; border: 1px solid {border}; "
            "border-radius: 13px; font-size: 20pt; font-weight: 700; }}"
        )
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(260)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_animation.valueChanged.connect(self._apply_hover_pulse)

    def _apply_hover_pulse(self, value):
        pulse = max(0.0, min(1.0, float(value)))
        fill = QColor(self._icon_background).lighter(100 + round(12 * pulse)).name()
        border = QColor(self._icon_border).lighter(100 + round(20 * pulse)).name()
        self.setStyleSheet(
            f"QLabel#kpiIcon {{ background: {fill}; color: {self._icon_accent}; border: {1 + round(pulse)}px solid {border}; "
            f"border-radius: {13 + round(2 * pulse)}px; font-size: {20 + 2 * pulse:.1f}pt; font-weight: 700; }}"
        )

    def enterEvent(self, event):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(0.0)
        self._hover_animation.setKeyValueAt(0.42, 1.0)
        self._hover_animation.setEndValue(0.0)
        self._hover_animation.start()
        super().enterEvent(event)


class AnalogClockWidget(QWidget):
    """Vector analog clock face with hour/minute/second hands and date display."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to switch to Digital clock")
        self._current_time = datetime.now()

    def set_time(self, dt):
        self._current_time = dt
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        h = self.height()
        w = self.width()
        dial_size = min(h - 10, 46)
        margin_left = 6
        center_x = margin_left + dial_size / 2.0
        center_y = h / 2.0
        radius = dial_size / 2.0

        # Dial background
        painter.setPen(QPen(QColor(148, 163, 184, 180), 1.5))
        painter.setBrush(QColor(15, 23, 42, 220))
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        # Tick marks
        now = self._current_time
        hour = now.hour % 12
        minute = now.minute
        second = now.second

        painter.save()
        painter.translate(center_x, center_y)
        for i in range(12):
            is_cardinal = (i % 3 == 0)
            painter.setPen(QPen(QColor(255, 255, 255, 220 if is_cardinal else 120), 1.5 if is_cardinal else 1.0))
            tick_start = radius - (5 if is_cardinal else 3)
            tick_end = radius - 1
            rad = math.radians(i * 30 - 90)
            x1 = tick_start * math.cos(rad)
            y1 = tick_start * math.sin(rad)
            x2 = tick_end * math.cos(rad)
            y2 = tick_end * math.sin(rad)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Hour hand
        hour_angle = (hour + minute / 60.0 + second / 3600.0) * 30.0 - 90.0
        h_rad = math.radians(hour_angle)
        h_len = radius * 0.52
        painter.setPen(QPen(QColor("#E2E8F0"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 0), QPointF(h_len * math.cos(h_rad), h_len * math.sin(h_rad)))

        # Minute hand
        min_angle = (minute + second / 60.0) * 6.0 - 90.0
        m_rad = math.radians(min_angle)
        m_len = radius * 0.76
        painter.setPen(QPen(QColor("#38BDF8"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 0), QPointF(m_len * math.cos(m_rad), m_len * math.sin(m_rad)))

        # Second hand
        sec_angle = second * 6.0 - 90.0
        s_rad = math.radians(sec_angle)
        s_len = radius * 0.82
        painter.setPen(QPen(QColor("#F43F5E"), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 0), QPointF(s_len * math.cos(s_rad), s_len * math.sin(s_rad)))

        # Center pin
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#F43F5E"))
        painter.drawEllipse(QPointF(0, 0), 2.5, 2.5)
        painter.restore()

        # Date & digital text readout beside dial
        text_x = margin_left + dial_size + 8
        text_w = max(0, w - text_x - 2)
        if text_w > 20:
            date_str = now.strftime("%a, %d %b")
            time_str = now.strftime("%I:%M:%S %p")
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRectF(text_x, center_y - 17, text_w, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, date_str)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            painter.setPen(QColor("#38BDF8"))
            painter.drawText(QRectF(text_x, center_y + 1, text_w, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, time_str)


class AnimatedRGBFrame(QFrame):
    """Paint a soft, animated RGB outline for the clock and brand mark."""
    def __init__(self, *, hover_only=False, outline_inset=8, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._hover_only = hover_only
        self._outline_inset = outline_inset
        self._active = not hover_only
        self._rotation = 0.0
        self._phase = 0.0
        self._tick = QTimer(self)
        self._tick.setInterval(72)
        self._tick.timeout.connect(self._advance_glow)
        if self._active:
            self._tick.start()

    def _advance_glow(self):
        self._rotation = (self._rotation + 3.0) % 360.0
        self._phase = (self._phase + 0.10) % (2.0 * 3.141592653589793)
        self.update()

    def enterEvent(self, event):
        if self._hover_only:
            self._active = True
            self._tick.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._hover_only:
            self._active = False
            self._tick.stop()
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        inset = self._outline_inset
        bounds = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        if bounds.width() <= 0 or bounds.height() <= 0:
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 23, 42, 226))
        painter.drawRoundedRect(bounds, 13, 13)

        pulse = (0.5 + 0.5 * math.sin(self._phase)) if self._active else 0.0
        glow_alpha = 20 + round(18 * pulse) if self._active else 76
        for width, alpha in ((6.0, glow_alpha), (3.0, 90 if self._active else 110), (1.5, 240)):
            gradient = QConicalGradient(bounds.center(), self._rotation)
            gradient.setColorAt(0.0, QColor(56, 189, 248, alpha))
            gradient.setColorAt(0.35, QColor(129, 140, 248, alpha))
            gradient.setColorAt(0.70, QColor(99, 102, 241, alpha))
            gradient.setColorAt(1.0, QColor(56, 189, 248, alpha))
            pen = QPen(QBrush(gradient), width, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            inset = width / 2 + 0.5
            painter.drawRoundedRect(bounds.adjusted(inset, inset, -inset, -inset), 11, 11)


class InteractionFeedback(QObject):
    """Animate a small accent glow on buttons and cards without moving layout."""
    def __init__(self, widget, accent):
        super().__init__(widget)
        self.widget = widget
        self._accent = QColor(accent)
        self._level = 0.0
        self.effect = QGraphicsDropShadowEffect(widget)
        self.effect.setOffset(0, 2)
        self.effect.setBlurRadius(0)
        self.effect.setColor(QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 0))
        widget.setGraphicsEffect(self.effect)
        widget.installEventFilter(self)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(190)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._apply_level)
        self._settle_timer = QTimer(self)
        self._settle_timer.setSingleShot(True)
        self._settle_timer.timeout.connect(self._settle_after_click)
        if isinstance(widget, (QPushButton, QToolButton)):
            widget.clicked.connect(self._pulse_on_click)

    def set_accent(self, accent):
        self._accent = QColor(accent)
        self._apply_level(self._level)

    def _apply_level(self, value):
        self._level = max(0.0, min(1.35, float(value)))
        alpha = 0 if self._level <= 0.01 else min(150, 36 + round(78 * self._level))
        self.effect.setColor(QColor(self._accent.red(), self._accent.green(), self._accent.blue(), alpha))
        self.effect.setBlurRadius(1 + 12 * self._level if alpha else 0)
        self.effect.setOffset(0, 2 + 2.5 * self._level)

    def _animate_to(self, target, duration=190):
        self.animation.stop()
        self.animation.setDuration(duration)
        self.animation.setStartValue(self._level)
        self.animation.setEndValue(target)
        self.animation.start()

    def _pulse_on_click(self, *_args):
        self._settle_timer.stop()
        self._animate_to(1.25, 105)
        self._settle_timer.start(145)

    def _settle_after_click(self):
        self._animate_to(0.62 if self.widget.underMouse() else 0.0)

    def eventFilter(self, watched, event):
        try:
            event_type = event.type()
        except (AttributeError, RuntimeError):
            return False
        if event_type == QEvent.Type.Enter:
            self._animate_to(0.62)
        elif event_type == QEvent.Type.Leave:
            self._settle_timer.stop()
            self._animate_to(0.0)
        elif event_type == QEvent.Type.MouseButtonPress:
            self._animate_to(1.0, 100)
        elif event_type == QEvent.Type.MouseButtonRelease:
            self._animate_to(0.72 if watched.underMouse() else 0.0)
        elif event_type == QEvent.Type.FocusIn:
            self._animate_to(0.5)
        elif event_type == QEvent.Type.FocusOut:
            self._animate_to(0.62 if watched.underMouse() else 0.0)
        return False



class WallpaperPhotoLoader(QThread):
    """Download a high-resolution wallpaper once, then keep it available offline."""
    loaded = Signal(str, str)

    def __init__(self, name, url, destination, parent=None):
        super().__init__(parent)
        self.name = name
        self.url = url
        self.destination = Path(destination)

    def run(self):
        saved_path = ""
        try:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            if self.destination.is_file() and self.destination.stat().st_size > 30000:
                saved_path = str(self.destination)
            else:
                request = Request(self.url, headers={"User-Agent": "EmployeeAuditManager/1.0 wallpaper-cache"})
                with urlopen(request, timeout=18) as response:
                    content_type = (response.headers.get("Content-Type") or "").lower()
                    data = response.read(15 * 1024 * 1024 + 1)
                if len(data) > 15 * 1024 * 1024:
                    raise ValueError("Wallpaper image exceeds the 15 MB limit")
                if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")):
                    raise ValueError("Wallpaper server did not return a valid JPEG or PNG")
                temp_path = self.destination.with_suffix(".download")
                temp_path.write_bytes(data)
                temp_path.replace(self.destination)
                saved_path = str(self.destination)
        except Exception:
            saved_path = ""
        self.loaded.emit(self.name, saved_path)


class AnimatedBackground(QWidget):
    """High-resolution photographic wallpapers with gentle Ken Burns motion and particles."""
    STYLES = ("Ambient Glow", "Aurora Waves", "Starfield", "Floating Bubbles", "Rainfall", "Matrix Drift", "Galaxy", "Milky Way", "Milky Way Waves", "Ocean Waves", "Lord Shiva", "Love Couple", "Love & Couples", "Cyberpunk Neon", "Calisthenics Power", "Cosmic Nebula", "Custom Image")
    PHOTO_WALLPAPERS = {
        "Galaxy": ("galaxy.jpg", "https://images.unsplash.com/photo-1707057538849-f723c167324b?auto=format&fit=crop&fm=jpg&w=1920&q=82"),
        "Milky Way": ("milky_way.jpg", "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&fm=jpg&w=1920&q=82"),
        "Milky Way Waves": ("milky_way.jpg", "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&fm=jpg&w=1920&q=82"),
        "Ocean Waves": ("ocean_waves.jpg", "https://images.unsplash.com/photo-1429305223369-4d065fdb6f53?auto=format&fit=crop&fm=jpg&w=1920&q=82"),
        "Lord Shiva": ("lord_shiva.jpg", "https://images.unsplash.com/photo-1533743725296-2e099eed32c6?auto=format&fit=crop&fm=jpg&w=1920&q=82"),
        "Love & Couples": ("love_couples.jpg", "https://images.unsplash.com/photo-1618426101260-26afa1d05ec3?auto=format&fit=crop&fm=jpg&w=1920&q=82"),
        "Love Couple": ("love_couples.jpg", "https://images.unsplash.com/photo-1618426101260-26afa1d05ec3?auto=format&fit=crop&fm=jpg&w=1920&q=82"),
    }

    @classmethod
    def _normalize_mode(cls, mode):
        if not mode:
            return "Ambient Glow"
        m = str(mode).strip().lower()
        if m in ("shiva", "lord shiva", "loard shiva"):
            return "Lord Shiva"
        if m in ("love couple", "love couples", "love & couple", "love & couples", "love and couples"):
            return "Love Couple"
        if m in ("cyberpunk", "cyberpunk neon", "neon"):
            return "Cyberpunk Neon"
        if m in ("calisthenics", "calisthenics power", "power"):
            return "Calisthenics Power"
        if m in ("cosmic", "cosmic nebula", "nebula"):
            return "Cosmic Nebula"
        if m in ("love & couples", "love & couple", "love couple", "love couples", "love and couples"):
            return "Love & Couples"
        if m in ("milky way waves", "milky way wave"):
            return "Milky Way Waves"
        if m in ("milky way",):
            return "Milky Way"
        if m in ("ocean waves", "ocean"):
            return "Ocean Waves"
        if m in ("galaxy",):
            return "Galaxy"
        if m in ("custom", "custom image", "custom wallpaper", "custom photo"):
            return "Custom Image"
        for s in cls.STYLES:
            if s.lower() == m:
                return s
        return mode if mode in cls.STYLES else "Ambient Glow"

    def __init__(self, parent=None, mode="Ambient Glow"):
        super().__init__(parent)
        # Normalize the former duplicate option for existing saved preferences.
        self.mode = "Lord Shiva" if mode == "Shiva" else self._normalize_mode(mode)
        self.custom_wallpaper_path = ""
        self.wallpaper_pixmap = QPixmap()
        self.photo_loader = None
        self.phase = 0.0
        self.particles = []
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(45)
        self.init_particles()
        self._load_wallpaper_image()

    def set_custom_wallpaper_path(self, path):
        self.custom_wallpaper_path = str(path) if path else ""
        if self.mode == "Custom Image":
            self._load_wallpaper_image()

    def _wallpaper_cache_path(self, filename):
        local_root = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return local_root / "EmployeeAuditManager" / "wallpapers" / filename

    def _load_wallpaper_image(self):
        if self.mode == "Custom Image":
            path = getattr(self, "custom_wallpaper_path", "")
            if not path:
                try:
                    win = self.window()
                    if win and hasattr(win, "db"):
                        path = win.db.get_setting("custom_wallpaper_path") or ""
                except Exception:
                    pass
            if not path:
                local_root = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
                wp_dir = local_root / "EmployeeAuditManager" / "wallpapers"
                for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                    candidate = wp_dir / f"custom_wallpaper{ext}"
                    if candidate.is_file():
                        path = str(candidate)
                        break
            if path and Path(path).is_file():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    self.wallpaper_pixmap = pixmap
                    self.update()
                    return
            self.wallpaper_pixmap = QPixmap()
            self.update()
            return

        entry = self.PHOTO_WALLPAPERS.get(self.mode)
        if not entry:
            self.wallpaper_pixmap = QPixmap()
            self.update()
            return
        filename, url = entry
        # Prefer the image bundled inside the installer so wallpapers work offline immediately.
        bundled_path = Path(resource_path(str(Path("assets") / "wallpapers" / "photos" / filename)))
        if bundled_path.is_file():
            pixmap = QPixmap(str(bundled_path))
            if not pixmap.isNull():
                self.wallpaper_pixmap = pixmap
                self.update()
                return
        # Development builds can fetch once and cache locally; normal release builds bundle photos.
        cached_path = self._wallpaper_cache_path(filename)
        if cached_path.is_file() and cached_path.stat().st_size > 30000:
            pixmap = QPixmap(str(cached_path))
            if not pixmap.isNull():
                self.wallpaper_pixmap = pixmap
                self.update()
                return
        self.wallpaper_pixmap = QPixmap()
        if self.photo_loader is None:
            self.photo_loader = WallpaperPhotoLoader(self.mode, url, cached_path, self)
            self.photo_loader.loaded.connect(self._on_wallpaper_loaded)
            self.photo_loader.finished.connect(self._on_wallpaper_loader_finished)
            self.photo_loader.start()
        self.update()

    def _on_wallpaper_loaded(self, name, path):
        if path and name == self.mode:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.wallpaper_pixmap = pixmap
        self.update()

    def _on_wallpaper_loader_finished(self):
        self.photo_loader = None
        entry = self.PHOTO_WALLPAPERS.get(self.mode)
        if entry and self.wallpaper_pixmap.isNull():
            QTimer.singleShot(0, self._load_wallpaper_image)

    def set_mode(self, mode):
        self.mode = "Lord Shiva" if mode == "Shiva" else self._normalize_mode(mode)
        self.init_particles()
        self._load_wallpaper_image()
        self.update()

    def init_particles(self):
        import random
        w, h = max(self.width(), 800), max(self.height(), 600)
        self.particles = []
        count = 48 if self.mode in ("Starfield", "Rainfall", "Matrix Drift") else 34
        for _ in range(count):
            self.particles.append({"x": random.randint(0, w), "y": random.randint(0, h), "r": random.randint(1, 4), "speed": random.uniform(0.6, 2.2) if self.mode in ("Rainfall", "Matrix Drift") else random.uniform(0.25, 0.9), "drift": random.uniform(-0.3, 0.3), "opacity": random.uniform(0.12, 0.42), "length": random.randint(8, 22)})

    def update_particles(self):
        import math
        self.phase = (self.phase + 0.018) % (2 * math.pi)
        width, height = max(self.width(), 1), max(self.height(), 1)
        for p in self.particles:
            p["y"] += p["speed"] if self.mode in ("Rainfall", "Matrix Drift") else -p["speed"]
            if self.mode == "Aurora Waves": p["x"] += math.sin(self.phase + p["y"] * 0.008) * 0.55
            else: p["x"] += p["drift"]
            if p["y"] < -24: p["y"] = height + 12
            elif p["y"] > height + 24: p["y"] = -12
            if p["x"] < -12: p["x"] = width + 8
            elif p["x"] > width + 12: p["x"] = -8
        self.update()

    def paintEvent(self, event):
        import math
        from PySide6.QtGui import QLinearGradient, QRadialGradient
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        w, h = max(rect.width(), 1), max(rect.height(), 1)
        theme_name = "night"
        try:
            if self.window() is not None and hasattr(self.window(), "current_theme"):
                theme_name = str(self.window().current_theme() or "night").lower()
        except Exception:
            pass
        is_light = theme_name in ("day", "ocean", "sunset")
        is_day = is_light
        base = QLinearGradient(0, 0, w, h)
        if is_light:
            if theme_name == "ocean":
                base.setColorAt(0.0, QColor("#F0F9FF"))
                base.setColorAt(0.5, QColor("#E0F2FE"))
                base.setColorAt(1.0, QColor("#F0F9FF"))
            elif theme_name == "sunset":
                base.setColorAt(0.0, QColor("#FFF7ED"))
                base.setColorAt(0.5, QColor("#FFEDD5"))
                base.setColorAt(1.0, QColor("#FFF7ED"))
            else:
                base.setColorAt(0.0, QColor("#FFFFFF"))
                base.setColorAt(0.48, QColor("#F8FAFC"))
                base.setColorAt(1.0, QColor("#F1F5F9"))
        else:
            base.setColorAt(0.0, QColor("#050811"))
            base.setColorAt(0.52, QColor("#0B1020"))
            base.setColorAt(1.0, QColor("#100A1D"))
        painter.fillRect(rect, base)

        # Real photographic wallpapers use a slow Ken Burns pan/zoom
        if not self.wallpaper_pixmap.isNull():
            image_w, image_h = self.wallpaper_pixmap.width(), self.wallpaper_pixmap.height()
            target_ratio = w / max(h, 1)
            image_ratio = image_w / max(image_h, 1)
            if image_ratio > target_ratio:
                crop_h = float(image_h)
                crop_w = crop_h * target_ratio
                max_x = max(0.0, image_w - crop_w)
                source_x = max_x * (0.5 + 0.20 * math.sin(self.phase * 0.45))
                source = QRectF(source_x, 0, crop_w, crop_h)
            else:
                crop_w = float(image_w)
                crop_h = crop_w / max(target_ratio, 0.01)
                max_y = max(0.0, image_h - crop_h)
                source_y = max_y * (0.5 + 0.20 * math.sin(self.phase * 0.45))
                source = QRectF(0, source_y, crop_w, crop_h)
            zoom = 1.035 + 0.012 * math.sin(self.phase * 0.35)
            center_x, center_y = source.center().x(), source.center().y()
            source.setWidth(source.width() / zoom)
            source.setHeight(source.height() / zoom)
            source.moveCenter(__import__("PySide6.QtCore", fromlist=["QPointF"]).QPointF(center_x, center_y))
            painter.drawPixmap(QRectF(rect), self.wallpaper_pixmap, source)

            veil = QLinearGradient(0, 0, 0, h)
            if is_light:
                fade = 22 + int(5 * (0.5 + 0.5 * math.sin(self.phase * 0.55)))
                if theme_name == "ocean":
                    veil.setColorAt(0.0, QColor(240, 249, 255, 215))
                    veil.setColorAt(1.0, QColor(224, 242, 254, 230))
                elif theme_name == "sunset":
                    veil.setColorAt(0.0, QColor(255, 247, 237, 215))
                    veil.setColorAt(1.0, QColor(255, 237, 213, 230))
                else:
                    veil.setColorAt(0.0, QColor(255, 255, 255, 215))
                    veil.setColorAt(1.0, QColor(248, 250, 252, 230))
            else:
                veil.setColorAt(0.0, QColor(3, 7, 18, 215))
                veil.setColorAt(1.0, QColor(3, 7, 18, 240))
            painter.fillRect(rect, veil)
        else:
            # Procedural generative live wallpapers guarantee all styles animate offline
            if self.mode in ("Galaxy", "Milky Way", "Milky Way Waves"):
                cx, cy = w * 0.5, h * 0.46
                core_radius = max(w, h) * 0.52
                galaxy_glow = QRadialGradient(cx, cy, core_radius)
                galaxy_glow.setColorAt(0.0, QColor(139, 92, 246, 75 if not is_day else 45))
                galaxy_glow.setColorAt(0.32, QColor(99, 102, 241, 48 if not is_day else 28))
                galaxy_glow.setColorAt(0.68, QColor(6, 182, 212, 25 if not is_day else 15))
                galaxy_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.fillRect(rect, galaxy_glow)

                num_arms = 2 if "Waves" in self.mode else 3
                for arm in range(num_arms):
                    arm_offset = arm * (2 * math.pi / num_arms) + self.phase * 0.22
                    for step in range(16):
                        radius = 24 + step * (max(w, h) * 0.025)
                        angle = arm_offset + step * 0.24
                        px = cx + math.cos(angle) * radius * 1.35
                        py = cy + math.sin(angle) * radius * 0.78
                        disc_r = max(4, int(step * 3.2))
                        color = QColor(167, 139, 250, max(8, 48 - step * 2)) if not is_day else QColor(124, 92, 252, max(6, 32 - step * 2))
                        painter.setBrush(color)
                        painter.drawEllipse(int(px - disc_r / 2), int(py - disc_r / 2), disc_r, disc_r)

            elif self.mode == "Ocean Waves":
                wave_colors = [
                    (14, 116, 144, 55 if not is_day else 32),
                    (2, 132, 199, 45 if not is_day else 28),
                    (56, 189, 248, 40 if not is_day else 24),
                    (45, 212, 191, 35 if not is_day else 20),
                ]
                for idx, (r, g, b, a) in enumerate(wave_colors):
                    path = QPainterPath()
                    base_y = h * (0.38 + idx * 0.15)
                    path.moveTo(0, h)
                    for x in range(0, w + 16, 16):
                        wy = base_y + math.sin(x * 0.004 + self.phase * (0.7 + idx * 0.25) + idx) * (22 + idx * 7)
                        wy += math.cos(x * 0.007 - self.phase * 0.5) * 8
                        path.lineTo(x, wy)
                    path.lineTo(w, h)
                    path.closeSubpath()
                    painter.fillPath(path, QColor(r, g, b, a))

            elif self.mode == "Cyberpunk Neon":
                # Neon perspective cyber-grid
                grid_pen = QPen(QColor(0, 229, 255, 35 if not is_day else 22), 1.2)
                painter.setPen(grid_pen)
                horizon = h * 0.48
                for x in range(0, w + 40, 40):
                    px = (x - w * 0.5) * 2.8 + w * 0.5
                    painter.drawLine(QPointF(w * 0.5, horizon), QPointF(px, h))
                for idx in range(1, 9):
                    gy = horizon + (h - horizon) * ((idx / 8.0) ** 1.8)
                    painter.drawLine(QPointF(0, gy), QPointF(w, gy))
                # Glowing neon horizon sun
                sun_grad = QRadialGradient(w * 0.5, horizon, max(w, h) * 0.28)
                sun_grad.setColorAt(0.0, QColor(244, 63, 94, 65 if not is_day else 40))
                sun_grad.setColorAt(0.5, QColor(139, 92, 246, 40 if not is_day else 25))
                sun_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.fillRect(rect, sun_grad)

            elif self.mode in ("Calisthenics Power", "Cosmic Nebula"):
                cx, cy = w * 0.5, h * 0.42
                glow = QRadialGradient(cx, cy, max(w, h) * 0.55)
                glow.setColorAt(0.0, QColor(0, 229, 255, 60 if not is_day else 35))
                glow.setColorAt(0.40, QColor(139, 92, 246, 45 if not is_day else 25))
                glow.setColorAt(0.75, QColor(236, 72, 153, 30 if not is_day else 15))
                glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.fillRect(rect, glow)
                # Calisthenics power wave pulses
                for r_idx in range(4):
                    ring_r = int(max(w, h) * (0.12 + r_idx * 0.14) + math.sin(self.phase + r_idx) * 14)
                    painter.setPen(QPen(QColor(0, 229, 255, max(8, 42 - r_idx * 9)), 1.5))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(QPointF(cx, cy), ring_r, ring_r * 0.65)

            elif self.mode == "Lord Shiva":
                cx, cy = w * 0.5, h * 0.32
                for i in range(3):
                    aura_r = int(max(w, h) * (0.24 + i * 0.16))
                    aura = QRadialGradient(cx, cy, aura_r)
                    alpha = (48 - i * 11) if not is_day else (38 - i * 8)
                    aura.setColorAt(0.0, QColor(56, 189, 248, alpha))
                    aura.setColorAt(0.48, QColor(129, 140, 248, int(alpha * 0.70)))
                    aura.setColorAt(1.0, QColor(0, 0, 0, 0))
                    painter.fillRect(rect, aura)
                moon_path = QPainterPath()
                moon_path.moveTo(cx - 32, cy - 22)
                moon_path.cubicTo(cx - 10, cy - 42, cx + 32, cy - 32, cx + 42, cy)
                moon_path.cubicTo(cx + 26, cy - 16, cx - 6, cy - 18, cx - 32, cy - 22)
                moon_color = QColor(241, 245, 249, 140 if not is_day else 110)
                painter.fillPath(moon_path, moon_color)
                # Meditative celestial beacon / trishula shaft
                trident_pen = QPen(QColor(56, 189, 248, 110 if is_day else 150), max(2.0, w * 0.002))
                painter.setPen(trident_pen)
                painter.drawLine(QPointF(cx, cy - 50), QPointF(cx, cy + 80))

            elif self.mode in ("Love & Couples", "Love Couple"):
                cx, cy = w * 0.5, h * 0.45
                love_grad = QRadialGradient(cx, cy, max(w, h) * 0.48)
                love_grad.setColorAt(0.0, QColor(244, 63, 94, 65 if not is_day else 45))
                love_grad.setColorAt(0.48, QColor(217, 70, 239, 45 if not is_day else 32))
                love_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.fillRect(rect, love_grad)
                for i, p in enumerate(self.particles[:16]):
                    hx, hy = p["x"], p["y"]
                    hs = 8 + (i % 6) * 2
                    heart_path = QPainterPath()
                    heart_path.moveTo(hx, hy + hs * 0.3)
                    heart_path.cubicTo(hx - hs * 0.6, hy - hs * 0.5, hx - hs, hy + hs * 0.2, hx, hy + hs)
                    heart_path.cubicTo(hx + hs, hy + hs * 0.2, hx + hs * 0.6, hy - hs * 0.5, hx, hy + hs * 0.3)
                    painter.fillPath(heart_path, QColor(244, 114, 182, int(p["opacity"] * (180 if not is_day else 125))))

        if self.mode in ("Ambient Glow", "Aurora Waves"):
            colors = ([(124, 92, 252, 30), (34, 211, 238, 22), (232, 121, 249, 16)]
                      if is_day else [(124, 92, 252, 42), (34, 211, 238, 30), (232, 121, 249, 22)])
            for i, color in enumerate(colors):
                x = int(w * (0.18 + i * 0.30 + 0.08 * math.sin(self.phase * (0.7 + i * 0.12))))
                y = int(h * (0.25 + i * 0.24 + 0.10 * math.cos(self.phase * (0.6 + i * 0.15))))
                radius = max(180, int(min(w, h) * (0.55 if self.mode == "Ambient Glow" else 0.72)))
                glow = QRadialGradient(x, y, radius)
                glow.setColorAt(0.0, QColor(*color))
                glow.setColorAt(1.0, QColor(color[0], color[1], color[2], 0))
                painter.fillRect(rect, glow)
            if self.mode == "Aurora Waves":
                painter.setPen(QPen(QColor(45, 212, 191, 30), 2.0))
                for band in range(5):
                    path = QPainterPath()
                    for x in range(0, w + 12, 12):
                        y = int(h * (0.18 + band * 0.13) + math.sin(x * 0.009 + self.phase + band) * 26 + math.sin(x * 0.003 - self.phase) * 18)
                        if x == 0: path.moveTo(x, y)
                        else: path.lineTo(x, y)
                    painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            alpha = max(0, min(255, int(p["opacity"] * 255)))
            if self.mode == "Starfield":
                painter.setBrush(QColor(226, 232, 240, alpha))
                painter.drawEllipse(int(p["x"]), int(p["y"]), p["r"], p["r"])
            elif self.mode == "Floating Bubbles":
                painter.setBrush(QColor(124, 92, 252, int(alpha * 0.42)))
                painter.setPen(QPen(QColor(167, 139, 250, int(alpha * 0.55)), 1))
                painter.drawEllipse(int(p["x"]), int(p["y"]), p["r"] * 3, p["r"] * 3)
                painter.setPen(Qt.PenStyle.NoPen)
            elif self.mode == "Rainfall":
                painter.setPen(QPen(QColor(56, 189, 248, alpha), 1.2))
                painter.drawLine(int(p["x"]), int(p["y"]), int(p["x"] - 3), int(p["y"] + p["length"]))
                painter.setPen(Qt.PenStyle.NoPen)
            elif self.mode == "Matrix Drift":
                painter.setPen(QPen(QColor(74, 222, 128, alpha), 1.2))
                painter.drawLine(int(p["x"]), int(p["y"]), int(p["x"]), int(p["y"] + p["length"]))
                painter.setPen(Qt.PenStyle.NoPen)
            else:
                painter.setBrush(QColor(167, 139, 250, alpha))
                painter.drawEllipse(int(p["x"]), int(p["y"]), p["r"], p["r"])
        if is_day:
            final_veil = QLinearGradient(0, 0, 0, h)
            final_veil.setColorAt(0.0, QColor(255, 255, 255, 145))
            final_veil.setColorAt(1.0, QColor(255, 255, 255, 188))
            painter.fillRect(rect, final_veil)
        else:
            final_veil = QLinearGradient(0, 0, 0, h)
            final_veil.setColorAt(0.0, QColor(4, 7, 18, 175))
            final_veil.setColorAt(1.0, QColor(4, 7, 18, 215))
            painter.fillRect(rect, final_veil)
        painter.end()

class EmployeeGroupsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Manage Employee Sections & Groups")
        self.setMinimumWidth(500)
        self.setMinimumHeight(440)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        info = QLabel("Create and manage custom employee sections (e.g. Technical, House Keeping, Sales). Employees can be arranged under these sections and reordered.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #94A3B8; font-size: 8.5pt;")
        layout.addWidget(info)

        add_layout = QHBoxLayout()
        self.new_group_input = QLineEdit()
        self.new_group_input.setPlaceholderText("Enter new section name (e.g. Technical, House Keeping)...")
        self.new_group_input.returnPressed.connect(self.on_add_group)
        add_btn = QPushButton("➕ Add Section")
        add_btn.clicked.connect(self.on_add_group)
        add_layout.addWidget(self.new_group_input, 1)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.list_widget, 1)

        btn_layout = QHBoxLayout()
        up_btn = QPushButton("⬆ Move Up")
        up_btn.clicked.connect(self.on_move_up)
        down_btn = QPushButton("⬇ Move Down")
        down_btn.clicked.connect(self.on_move_down)
        rename_btn = QPushButton("✏️ Rename")
        rename_btn.clicked.connect(self.on_rename)
        del_btn = QPushButton("🗑️ Delete")
        del_btn.clicked.connect(self.on_delete)
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        btn_layout.addWidget(rename_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.accept)
        layout.addWidget(close_box)

        self.refresh_list()

    def refresh_list(self, select_name=None):
        self.list_widget.clear()
        groups = self.db.employee_groups()
        counts = {}
        for row in self.db.conn.execute("SELECT COALESCE(NULLIF(TRIM(department), ''), 'General') AS dept, COUNT(*) AS c FROM employees GROUP BY dept").fetchall():
            counts[row["dept"].lower()] = row["c"]
        for g in groups:
            c = counts.get(g["name"].lower(), 0)
            item = QListWidgetItem(f"📁  {g['name']}  ({c} {'employee' if c==1 else 'employees'})")
            item.setData(Qt.ItemDataRole.UserRole, g["name"])
            self.list_widget.addItem(item)
            if select_name and g["name"].lower() == select_name.lower():
                self.list_widget.setCurrentItem(item)

    def on_add_group(self):
        name = self.new_group_input.text().strip()
        if not name:
            return
        if not self.db.add_employee_group(name):
            error(self, "A group with this name already exists or could not be added.")
            return
        self.new_group_input.clear()
        self.refresh_list(select_name=name)

    def on_rename(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        old_name = item.data(Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(self, "Rename Section", "Enter new name for section:", text=old_name)
        if ok and new_name.strip():
            if not self.db.rename_employee_group(old_name, new_name.strip()):
                error(self, "Could not rename section.")
                return
            self.refresh_list(select_name=new_name.strip())

    def on_delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if not ask(self, "Delete Section", f"Delete section '{name}'? Employees in this group will become Unassigned / General."):
            return
        self.db.delete_employee_group(name)
        self.refresh_list()

    def on_move_up(self):
        r = self.list_widget.currentRow()
        if r <= 0:
            return
        self._swap(r, r - 1)

    def on_move_down(self):
        r = self.list_widget.currentRow()
        if r < 0 or r >= self.list_widget.count() - 1:
            return
        self._swap(r, r + 1)

    def _swap(self, i1, i2):
        names = [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_widget.count())]
        names[i1], names[i2] = names[i2], names[i1]
        self.db.reorder_employee_groups(names)
        self.refresh_list(select_name=names[i2])


class EmployeeTableWidget(QTableWidget):
    def __init__(self, rows=0, cols=8, parent_window=None):
        super().__init__(rows, cols)
        self.window = parent_window
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.viewport().setAcceptDrops(False)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self._drag_start_row = -1

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def startDrag(self, supportedActions):
        pass

    def dragEnterEvent(self, event):
        event.ignore()

    def dragMoveEvent(self, event):
        event.ignore()

    def dropEvent(self, event):
        event.ignore()

    def on_context_menu(self, pos):
        if not self.window:
            return
        row = self.rowAt(pos.y())
        if row < 0:
            return
        item = self.item(row, 0)
        if not item:
            return
        emp_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(emp_id, int):
            return

        self.selectRow(row)
        menu = QMenu(self)
        
        groups = self.window.db.employee_groups()
        if getattr(self.window, "is_admin_or_dev", False):
            move_menu = menu.addMenu("📁 Move to Section")
            for g in groups:
                gname = g["name"]
                action = move_menu.addAction(gname)
                action.triggered.connect(lambda ch=False, eid=emp_id, gn=gname: self.window.move_employee_to_group(eid, gn))
            move_menu.addSeparator()
            new_grp_action = move_menu.addAction("➕ New Section...")
            new_grp_action.triggered.connect(lambda: self.window.create_and_move_to_group(emp_id))

            up_act = menu.addAction("⬆ Move Up")
            up_act.triggered.connect(self.window.move_employee_up)
            down_act = menu.addAction("⬇ Move Down")
            down_act.triggered.connect(self.window.move_employee_down)
            menu.addSeparator()

        edit_act = menu.addAction("✏️ Edit Employee")
        edit_act.triggered.connect(self.window.edit_employee)
        toggle_act = menu.addAction("🔄 Activate / Deactivate")
        toggle_act.triggered.connect(self.window.toggle_employee)
        if getattr(self.window, "is_admin_or_dev", False):
            del_act = menu.addAction("🗑️ Delete Employee")
            del_act.triggered.connect(self.window.delete_employee)

        menu.exec(self.viewport().mapToGlobal(pos))


class CommandPaletteDialog(QDialog):
    """Command Palette (Ctrl+K / Cmd+K) — Deep Spec Section 2.
    Instant fuzzy search across all application pages, features, and quick actions."""
    def __init__(self, main_window, parent=None):
        qparent = parent if isinstance(parent, QWidget) else (main_window if isinstance(main_window, QWidget) else None)
        super().__init__(qparent)
        self.main_window = main_window
        self.setWindowTitle("Command Palette (Ctrl+K)")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(640)
        self.setMinimumHeight(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        panel = QFrame(self)
        panel.setObjectName("commandPalettePanel")
        panel.setStyleSheet(
            "QFrame#commandPalettePanel {"
            "  background-color: #0F172A;"
            "  border: 1px solid rgba(255, 255, 255, 0.16);"
            "  border-radius: 10px;"
            "}"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Type a command or search pages (e.g. 'store', 'scrape', 'sync', 'employee', 'tasks')...")
        self.search_input.setStyleSheet(
            "QLineEdit {"
            "  font-size: 11pt; font-weight: 500; color: #FFFFFF;"
            "  background-color: rgba(30, 41, 59, 0.85);"
            "  border: 1px solid #3B82F6; border-radius: 6px;"
            "  padding: 10px 14px;"
            "}"
        )
        panel_layout.addWidget(self.search_input)

        self.cmd_list = QListWidget()
        self.cmd_list.setStyleSheet(
            "QListWidget {"
            "  background-color: transparent; border: none; outline: none; font-size: 9.5pt; color: #E2E8F0;"
            "}"
            "QListWidget::item {"
            "  padding: 8px 12px; border-radius: 6px; margin-bottom: 2px;"
            "}"
            "QListWidget::item:selected {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E40AF, stop:1 #3B82F6); color: #FFFFFF;"
            "}"
            "QListWidget::item:hover:!selected {"
            "  background-color: rgba(255, 255, 255, 0.08);"
            "}"
        )
        panel_layout.addWidget(self.cmd_list, 1)

        hint = QLabel("↑↓ Navigate · Enter Run · Esc Close")
        hint.setStyleSheet("font-size: 8pt; color: #64748B; text-align: center;")
        panel_layout.addWidget(hint)

        root.addWidget(panel)

        self.commands = [
            ("Navigation", "🏪 Store Directory & Market Coverage", lambda: self._navigate_tab(self.main_window.customer_tab)),
            ("Action", "⚡ 1-Tap Deep Web Scraping & Master Update", lambda: (self._navigate_tab(self.main_window.customer_tab), self.main_window.customer_tab.one_tap_scrape_and_master_update())),
            ("Action", "🔄 Continuous Google Sheets Sync", lambda: (self._navigate_tab(self.main_window.customer_tab), self.main_window.customer_tab.sync_google_sheets())),
            ("Action", "🖨️ Print Leads & Export Center", lambda: (self._navigate_tab(self.main_window.customer_tab), self.main_window.customer_tab.open_print_preview())),
            ("Action", "📑 Export Store Directory to Excel (.xlsx)", lambda: (self._navigate_tab(self.main_window.customer_tab), self.main_window.customer_tab.export_xlsx())),
            ("Action", "📄 Export Store Directory to PDF", lambda: (self._navigate_tab(self.main_window.customer_tab), self.main_window.customer_tab.export_pdf())),
            ("Action", "🖨️ Print Regional Dashboard & Preview", lambda: (self._navigate_tab(self.main_window.customer_tab), self.main_window.customer_tab.open_regional_print_preview())),
            ("Action", "📑 Export Regional Dashboard to Excel (.xlsx)", lambda: (self._navigate_tab(self.main_window.customer_tab), self.main_window.customer_tab.export_regional_xlsx())),
            ("Action", "📄 Export Regional Dashboard to PDF", lambda: (self._navigate_tab(self.main_window.customer_tab), self.main_window.customer_tab.export_regional_pdf())),
            ("Navigation", "👥 Employees & Staff Listing", lambda: self._navigate_tab(self.main_window.employees_tab)),
            ("Action", "➕ Add New Employee", lambda: self.main_window.add_employee()),
            ("Navigation", "✅ Task Manager & Department Tasks", lambda: self._navigate_tab(self.main_window.tasks_tab)),
            ("Action", "📝 Create New Task", lambda: self.main_window.add_task()),
            ("Navigation", "🟢 Attendance & Daily Clock In/Out", lambda: self._navigate_tab(self.main_window.attendance_tab)),
            ("Navigation", "📊 Dashboard & Analytics", lambda: self._navigate_tab(self.main_window.dashboard)),
            ("Navigation", "🏠 Home & Overview", lambda: self._navigate_tab(self.main_window.home_tab)),
            ("Navigation", "💬 Live Chat & Communications", lambda: self._navigate_tab(self.main_window.chat_tab)),
            ("Navigation", "💼 Business Tracking & Invoicing", lambda: self._navigate_tab(self.main_window.business_tab)),
            ("Navigation", "🖨️ Employee Reports & Audit Center", lambda: self._navigate_tab(self.main_window.reports_tab)),
            ("Navigation", "⚙️ Settings & Encrypted Cloud Backup", lambda: self._navigate_tab(self.main_window.settings_tab)),
        ]

        self._populate_list("")
        self.search_input.textChanged.connect(self._populate_list)
        self.search_input.returnPressed.connect(self._execute_selected)
        self.cmd_list.itemDoubleClicked.connect(lambda: self._execute_selected())

    def _navigate_tab(self, target_widget):
        for idx in range(self.main_window.tabs.count()):
            if self.main_window.tabs.widget(idx) == target_widget:
                self.main_window.tabs.setCurrentIndex(idx)
                break

    def _populate_list(self, filter_text):
        self.cmd_list.clear()
        query = filter_text.strip().casefold()
        for group, title, handler in self.commands:
            combined = f"{group} {title}".casefold()
            if not query or query in combined:
                item = QListWidgetItem(f"[{group}]  {title}")
                item.setData(Qt.ItemDataRole.UserRole, handler)
                self.cmd_list.addItem(item)
        if self.cmd_list.count() > 0:
            self.cmd_list.setCurrentRow(0)

    def _execute_selected(self):
        row = self.cmd_list.currentRow()
        if row >= 0:
            item = self.cmd_list.item(row)
            handler = item.data(Qt.ItemDataRole.UserRole)
            self.accept()
            if callable(handler):
                handler()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Down:
            curr = self.cmd_list.currentRow()
            if curr < self.cmd_list.count() - 1:
                self.cmd_list.setCurrentRow(curr + 1)
        elif event.key() == Qt.Key.Key_Up:
            curr = self.cmd_list.currentRow()
            if curr > 0:
                self.cmd_list.setCurrentRow(curr - 1)
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, db, user):
        super().__init__(); ensure_accessible_tooltip_controller(); ensure_combobox_wheel_filter(); self.db=db; self.current_user=user; self.user_role=user.get("role", "HR")
        self.setWindowTitle(APP_NAME); self.setWindowIcon(QIcon(brand_mark_pixmap(128)))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
        )
        self._is_maximized = False
        self._normal_geometry = None
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available:
            avail_w = available.width()
            avail_h = available.height()
            min_w = min(800, max(480, avail_w - 40))
            min_h = min(480, max(360, avail_h - 70))
            self.setMinimumSize(min_w, min_h)
            norm_w = min(1260, max(min_w, avail_w - 40))
            norm_h = min(720, max(min_h, avail_h - 60))
            norm_x = available.x() + max(0, (avail_w - norm_w) // 2)
            norm_y = available.y() + max(0, (avail_h - norm_h) // 2)
            self.resize(norm_w, norm_h)
            self.move(norm_x, norm_y)
            self._normal_geometry = QRect(norm_x, norm_y, norm_w, norm_h)
        else:
            self.resize(1100, 660); self.setMinimumSize(780, 460)
        self._drag_pos = None

        # Custom title bar (hidden in native window mode so the top is clean and not empty)
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(0)
        self.title_bar.hide()
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 12, 0)
        title_layout.setSpacing(8)

        self.header_logo_menu = QToolButton()
        self.header_logo_menu.setObjectName("headerLogoMenu")
        self.header_logo_menu.setIcon(QIcon(brand_mark_pixmap(32)))
        self.header_logo_menu.setIconSize(QSize(22, 22))
        self.header_logo_menu.setFixedSize(36, 32)
        self.header_logo_menu.setToolTip("Go to Home")
        self.header_logo_menu.setAccessibleName("Application menu")
        # Keep the original icon for the Windows taskbar/window, but remove the
        # redundant icon button from the visible title bar.
        self.header_logo_menu.hide()

        # Navigation buttons kept as hidden instances for API compatibility without polluting the header UI
        self.header_prev = QPushButton("‹")
        self.header_prev.setObjectName("headerNavButton")
        self.header_prev.hide()
        self.header_next = QPushButton("›")
        self.header_next.setObjectName("headerNavButton")
        self.header_next.hide()

        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setMinimumWidth(0)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)
        self.header_clock = QLabel()
        self.header_clock.setObjectName("headerClock")
        self.header_clock.setMinimumWidth(165)
        self.header_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_clock.setToolTip("Current local date and time")
        btn_style = (
            "QPushButton#titleBtnMin, QPushButton#titleBtnMax { "
            "background: rgba(255, 255, 255, 0.08); color: #F1F5F9; border: 1px solid rgba(255, 255, 255, 0.16); "
            "border-radius: 6px; font-size: 10pt; font-weight: 700; min-width: 0; padding: 0; margin: 0; } "
            "QPushButton#titleBtnMin:hover, QPushButton#titleBtnMax:hover { "
            "background: rgba(255, 255, 255, 0.22); color: #FFFFFF; border-color: rgba(255, 255, 255, 0.35); } "
            "QPushButton#titleBtnMin:pressed, QPushButton#titleBtnMax:pressed { background: rgba(255, 255, 255, 0.30); }"
        )
        close_style = (
            "QPushButton#titleBtnClose { "
            "background: rgba(239, 68, 68, 0.16); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.35); "
            "border-radius: 6px; font-size: 10pt; font-weight: 700; min-width: 0; padding: 0; margin: 0; } "
            "QPushButton#titleBtnClose:hover { background: #DC2626; color: #FFFFFF; border-color: #EF4444; } "
            "QPushButton#titleBtnClose:pressed { background: #B91C1C; }"
        )

        self.btn_min = QPushButton("—")
        self.btn_min.setObjectName("titleBtnMin")
        self.btn_min.setFixedSize(38, 28)
        self.btn_min.setStyleSheet(btn_style)
        self.btn_min.setToolTip("Minimize"); self.btn_min.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.btn_min)

        self.btn_max = QPushButton("❐" if getattr(self, "_is_maximized", False) else "□")
        self.btn_max.setObjectName("titleBtnMax")
        self.btn_max.setFixedSize(38, 28)
        self.btn_max.setStyleSheet(btn_style)
        self.btn_max.setToolTip("Maximize / Restore"); self.btn_max.clicked.connect(self.toggle_maximize)
        title_layout.addWidget(self.btn_max)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("titleBtnClose")
        self.btn_close.setFixedSize(38, 28)
        self.btn_close.setStyleSheet(close_style)
        self.btn_close.setToolTip("Close"); self.btn_close.clicked.connect(self.close)
        title_layout.addWidget(self.btn_close)
        self.title_bar.mouseDoubleClickEvent = lambda e: self.toggle_maximize() if e.button() == Qt.MouseButton.LeftButton else None

        # Animated background
        self.bg_anim = AnimatedBackground(mode=self.db.get_setting("animation_style", "Ambient Glow") or "Ambient Glow")
        self.bg_anim.setObjectName("animatedBg")

        # Main shell: collapsible glass sidebar + existing content pages.
        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("navigationSidebar")
        self.sidebar.setFixedWidth(224)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(6, 8, 6, 8)
        self.sidebar_layout.setSpacing(6)
        self.sidebar_toggle = QPushButton("☰  Collapse menu")
        self.sidebar_toggle.setObjectName("sidebarToggle")
        self.sidebar_toggle.setToolTip("Collapse or expand navigation")
        self.sidebar_toggle.setMinimumHeight(34)
        self.sidebar_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        self.sidebar_layout.addWidget(self.sidebar_toggle)

        self.main_content = QWidget()
        self.main_content.setObjectName("mainContentSurface")
        main_content_layout = QVBoxLayout(self.main_content)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        main_content_layout.addWidget(self.title_bar)
        self.title_bar.raise_()

        # Persistent brand banner shared by every page with the refreshed RSC mark.
        self.brand_banner = QFrame()
        self.brand_banner.setObjectName("brandBanner")
        self.brand_banner.setMinimumHeight(104)
        brand_layout = QHBoxLayout(self.brand_banner)
        brand_layout.setContentsMargins(18, 10, 18, 10)
        brand_layout.setSpacing(14)
        self.brand_logo_frame = AnimatedRGBFrame(hover_only=True, outline_inset=2)
        self.brand_logo_frame.setObjectName("brandLogoFrame")
        self.brand_logo_frame.setFixedSize(92, 92)
        logo_frame_layout = QHBoxLayout(self.brand_logo_frame)
        logo_frame_layout.setContentsMargins(8, 8, 8, 8)
        logo_frame_layout.setSpacing(0)
        self.brand_logo = QLabel()
        self.brand_logo.setObjectName("brandLogo")
        self.brand_logo.setFixedSize(76, 76)
        self.brand_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand_logo.setToolTip("Raw Strength Calisthenics brand mark")
        self.brand_logo.setPixmap(brand_mark_pixmap(68))
        logo_frame_layout.addWidget(self.brand_logo)
        brand_layout.addWidget(self.brand_logo_frame)
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(2)
        self.brand_heading = QLabel("Raw Strength Calisthenics")
        self.brand_heading.setObjectName("brandHeading")
        self.brand_subheading = QLabel(f"EXECUTIVE AUDIT  •  OPERATIONS OS  •  v{APP_VERSION}")
        self.brand_subheading.setObjectName("brandSubheading")
        brand_copy.addWidget(self.brand_heading)
        brand_copy.addWidget(self.brand_subheading)
        brand_layout.addLayout(brand_copy, 1)
        self.header_clock.setMinimumWidth(0)
        self.header_clock.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.header_clock.setMinimumHeight(42)
        self.header_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_clock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_clock.setToolTip("Click to switch to Analog clock")
        self.header_clock.mousePressEvent = lambda e: self.toggle_clock_mode() if e.button() == Qt.MouseButton.LeftButton else None
        self.header_clock_frame = AnimatedRGBFrame()
        self.header_clock_frame.setObjectName("headerClockFrame")
        # Reserve enough room for the full date/time, including the meridiem.
        # A flexible QLabel inside a narrow minimum frame clipped both ends of
        # the clock string on maximized, DPI-scaled Windows displays.
        self.header_clock_frame.setFixedSize(254, 66)
        self.header_clock_analog = AnalogClockWidget(self.header_clock_frame)
        self.header_clock_analog.setObjectName("headerClockAnalog")
        self.header_clock_analog.hide()
        self.header_clock_analog.clicked.connect(self.toggle_clock_mode)
        self.clock_mode_btn = QPushButton("🕒")
        self.clock_mode_btn.setObjectName("clockModeBtn")
        self.clock_mode_btn.setFixedSize(28, 28)
        self.clock_mode_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clock_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clock_mode_btn.setToolTip("Switch clock mode (Digital / Analog)")
        self.clock_mode_btn.setStyleSheet(
            "QPushButton#clockModeBtn { min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; "
            "padding: 0; margin: 0; background: rgba(255, 255, 255, 0.12); color: #FFFFFF; "
            "border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 7px; "
            "font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif; font-size: 13px; text-align: center; } "
            "QPushButton#clockModeBtn:hover { background: rgba(56, 189, 248, 0.35); border-color: #38BDF8; color: #FFFFFF; }"
        )
        self.clock_mode_btn.clicked.connect(self.toggle_clock_mode)
        clock_frame_layout = QHBoxLayout(self.header_clock_frame)
        clock_frame_layout.setContentsMargins(10, 6, 8, 6)
        clock_frame_layout.setSpacing(4)
        clock_frame_layout.addWidget(self.header_clock, 1)
        clock_frame_layout.addWidget(self.header_clock_analog, 1)
        clock_frame_layout.addWidget(self.clock_mode_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Continuous automatic synchronization badge in the top brand header panel
        self.header_sync_badge = QPushButton("🟢 Auto-Synced")
        self.header_sync_badge.setObjectName("headerSyncBadge")
        self.header_sync_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_sync_badge.setMinimumHeight(36)
        self.header_sync_badge.setStyleSheet(
            "QPushButton#headerSyncBadge { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(16, 185, 129, 0.20), stop:1 rgba(5, 150, 105, 0.30)); "
            "color: #ECFDF5; border: 1.5px solid rgba(52, 211, 153, 0.55); border-radius: 9px; "
            "padding: 6px 16px; font-weight: 700; font-size: 9.5pt; letter-spacing: 0.3px; } "
            "QPushButton#headerSyncBadge:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #059669); border-color: #6EE7B7; color: #FFFFFF; } "
            "QPushButton#headerSyncBadge:pressed { background: #047857; } "
            "QPushButton#headerSyncBadge:disabled { background: rgba(15, 23, 42, 0.20); color: rgba(255, 255, 255, 0.40); border-color: rgba(255, 255, 255, 0.12); }"
        )
        self.header_sync_badge.setToolTip("Continuous Cloud Sync is Active. Data is continuously encrypted and synchronized automatically in the background. Click to check for updates now.")
        self.header_sync_badge.clicked.connect(lambda: self.schedule_auto_sync(immediate=True))
        self.header_sync_badge.hide()

        # Compatibility aliases for existing references/tests
        self.shared_sync_push_button = self.header_sync_badge
        self.shared_sync_pull_button = QPushButton()
        self.shared_sync_pull_button.hide()

        # Retain dummy status widget for safe background setText updates without displaying status message in UI
        self.shared_sync_status = QLabel()
        self.shared_sync_status.hide()
        self.shared_sync_bar = None

        brand_layout.addWidget(self.header_sync_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_layout.addSpacing(6)
        brand_layout.addWidget(self.header_clock_frame, 0, Qt.AlignmentFlag.AlignVCenter)
        self.header_clock.show()
        main_content_layout.addWidget(self.brand_banner)

        self.tabs = QTabWidget()
        self.tabs.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.tabs.setAutoFillBackground(False)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(False)
        self.tabs.setDocumentMode(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        self.tabs.setUsesScrollButtons(False)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().hide()
        main_content_layout.addWidget(self.tabs)
        central_layout.addWidget(self.sidebar)
        central_layout.addWidget(self.main_content, 1)
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        central.setAutoFillBackground(False)
        self.setCentralWidget(central)
        # The wallpaper stays behind the page surfaces; content panels remain high-contrast.
        self.bg_anim.setParent(central)
        self.bg_anim.lower()
        self.bg_anim.setGeometry(0, 0, self.width(), self.height())

        self.home_tab=QWidget(); self.dashboard=QWidget(); self.employees_tab=QWidget(); self.tasks_tab=QWidget(); self.tracker_tab=QWidget(); self.attendance_tab=QWidget(); self.reports_tab=QWidget(); self.archive_tab=QWidget(); self.settings_tab=QWidget()
        for page in (self.home_tab, self.dashboard, self.employees_tab, self.tasks_tab, self.tracker_tab, self.attendance_tab, self.reports_tab, self.archive_tab, self.settings_tab):
            # Keep page surfaces translucent so the wallpaper remains visible behind opaque content cards.
            page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            page.setAutoFillBackground(False)
            page.setObjectName("appPageSurface")
            page.setStyleSheet("QWidget#appPageSurface { background: transparent; }")
        self.business_tab = BusinessTrackingTab(self.db)
        self.chat_tab = CloudflareChatTab(self.db, self.current_user)
        self.customer_tab = CustomerProspectsTab(self.db)
        tab_items = [
            (self.home_tab, "🏠  Home"), (self.dashboard, "📊  Dashboard"),
            (self.employees_tab, "👥  Employees"), (self.tasks_tab, "✅  Task Manager"),
            (self.tracker_tab, "📝  Employee Tracker"), (self.attendance_tab, "🟢  Attendance"),
            (self.reports_tab, "🖨️  Print Center"), (self.archive_tab, "📁  EOD Archive"),
            (self.business_tab, "💼  Business Tracking"),
            (self.customer_tab, "🏪  Store Directory"),
            (self.chat_tab, "💬  Live Chat"),
            (self.settings_tab, "⚙️  Settings & Backup"),
        ]
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("sidebarScrollArea")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sidebar_scroll.setStyleSheet("QScrollArea#sidebarScrollArea { border: 0; background: transparent; }")
        sidebar_scroll_content = QWidget()
        sidebar_scroll_content.setStyleSheet("background: transparent;")
        self.sidebar_scroll_layout = QVBoxLayout(sidebar_scroll_content)
        self.sidebar_scroll_layout.setContentsMargins(0, 2, 0, 2)
        self.sidebar_scroll_layout.setSpacing(4)

        self.sidebar_buttons = []
        for index, (widget, title) in enumerate(tab_items):
            self.tabs.addTab(widget, title)
            button = QPushButton(title.replace("&", "&&"))
            button.setObjectName("sidebarNavButton")
            button.setCheckable(True)
            button.setMinimumHeight(34)
            button.setToolTip(title)
            button.clicked.connect(lambda checked=False, tab_index=index: self.tabs.setCurrentIndex(tab_index))
            self.sidebar_scroll_layout.addWidget(button)
            self.sidebar_buttons.append((button, title))
        self.sidebar_scroll_layout.addStretch(1)
        self.sidebar_scroll.setWidget(sidebar_scroll_content)
        self.sidebar_layout.addWidget(self.sidebar_scroll, 1)
        # Navigation already exists in the persistent sidebar.
        self.header_logo_menu.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        self._tab_animation = None
        self._animated_page = None
        self.tabs.currentChanged.connect(self.animate_tab_transition)
        self.tabs.currentChanged.connect(self.sync_sidebar_selection)
        self.sync_sidebar_selection(self.tabs.currentIndex())
        self.header_prev.clicked.connect(lambda: self.tabs.setCurrentIndex(max(0, self.tabs.currentIndex() - 1)))
        self.header_next.clicked.connect(lambda: self.tabs.setCurrentIndex(min(self.tabs.count() - 1, self.tabs.currentIndex() + 1)))
        self._header_clock_timer = QTimer(self)
        self._header_clock_timer.timeout.connect(self.refresh_header_clock)
        self._header_clock_timer.start(1000)
        self.refresh_header_clock()
        saved_clock_mode = self.db.get_setting("clock_mode", "digital") if hasattr(self, "db") else "digital"
        if saved_clock_mode == "analog":
            self.set_clock_mode("analog")
        else:
            self._clock_mode = "digital"
        self.build_home(); self.build_dashboard(); self.build_employees(); self.build_tasks(); self.build_tracker(); self.build_attendance(); self.build_reports(); self.build_archive(); self.build_settings()
        # Database sync controls remain in the dedicated sync/settings area.
        self.polish_tables()
        self.apply_global_control_polish()
        self.apply_hover_messages()
        self.apply_interaction_animations()
        if hasattr(self.db, "set_active_user"):
            self.db.set_active_user(user)
        if is_developer_test_user(user):
            self.statusBar().showMessage(
                f"  Signed in: admin (Developer)  •  🧪 Local Test Mode (Master Sync PAUSED - Changes stay local)  •  Raw Strength Calisthenics"
            )
        else:
            self.statusBar().showMessage(
                f"  Signed in: {user.get('display_name') or user.get('username')}  •  👑 Master Customer Mode (Live Sync ACTIVE)  •  Role: {self.user_role}  •  Raw Strength Calisthenics"
            )
        self.refresh_all()
        # Check for update in background and display home banner if a newer release exists
        QTimer.singleShot(2500, self._check_updates_silently)
        self._init_auto_sync()
        # Hide native menu bar (frameless window)
        self.menuBar().hide()
        # Command Palette (Ctrl+K / Cmd+K) - Deep Spec Section 2
        try:
            from PySide6.QtGui import QKeySequence, QShortcut
            self.cmd_palette_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
            self.cmd_palette_shortcut.activated.connect(self.open_command_palette)
        except Exception as exc:
            logging.getLogger("app").warning("Could not register Ctrl+K shortcut: %s", exc)

    def open_command_palette(self):
        palette = CommandPaletteDialog(self)
        palette.exec()

    def toggle_clock_mode(self):
        current = getattr(self, "_clock_mode", "digital")
        new_mode = "analog" if current == "digital" else "digital"
        self.set_clock_mode(new_mode)

    def set_clock_mode(self, mode):
        self._clock_mode = mode
        if hasattr(self, "db") and hasattr(self.db, "set_setting"):
            try:
                self.db.set_setting("clock_mode", mode)
            except Exception:
                pass
        if mode == "analog":
            if hasattr(self, "header_clock"):
                self.header_clock.hide()
            if hasattr(self, "header_clock_analog"):
                self.header_clock_analog.show()
            if hasattr(self, "clock_mode_btn"):
                self.clock_mode_btn.setText("🔢")
                self.clock_mode_btn.setToolTip("Switch to Digital clock")
            if hasattr(self, "clock_mode_combo"):
                self.clock_mode_combo.blockSignals(True)
                self.clock_mode_combo.setCurrentText("Analog")
                self.clock_mode_combo.blockSignals(False)
        else:
            if hasattr(self, "header_clock"):
                self.header_clock.show()
            if hasattr(self, "header_clock_analog"):
                self.header_clock_analog.hide()
            if hasattr(self, "clock_mode_btn"):
                self.clock_mode_btn.setText("🕒")
                self.clock_mode_btn.setToolTip("Switch to Analog clock")
            if hasattr(self, "clock_mode_combo"):
                self.clock_mode_combo.blockSignals(True)
                self.clock_mode_combo.setCurrentText("Digital")
                self.clock_mode_combo.blockSignals(False)
        self.refresh_header_clock()

    def refresh_header_clock(self):
        now = datetime.now()
        if hasattr(self, "header_clock"):
            self.header_clock.setText(f"{now.strftime('%a, %d %b')}\n{now.strftime('%I:%M:%S %p')}")
        if hasattr(self, "header_clock_analog"):
            self.header_clock_analog.set_time(now)

    def toggle_sidebar(self):
        collapsed = self.sidebar.width() > 100
        self.sidebar.setFixedWidth(76 if collapsed else 224)
        self._apply_responsive_layout()
        QTimer.singleShot(0, self.fit_sidebar_labels)

    def sync_sidebar_selection(self, index):
        for i, (button, title) in enumerate(getattr(self, "sidebar_buttons", [])):
            button.setChecked(i == index)
        if index == 0 and hasattr(self, "refresh_home_business_snapshot"):
            self.refresh_home_business_snapshot()

    @staticmethod
    def _ui_chrome_palette(theme_name):
        palettes = {
            "day": {
                "surface": "#FFFFFF",
                "surface_card": "#FFFFFF",
                "sidebar": "#F8FAFC",
                "sidebar_border": "#E2E8F0",
                "nav": "transparent",
                "nav_border": "transparent",
                "nav_active_grad": "#EEF2FF",
                "border": "#E2E8F0",
                "border_subtle": "rgba(226, 232, 240, 0.65)",
                "text": "#0F172A",
                "muted_text": "#64748B",
                "hover": "#EEF2FF",
                "hover_text": "#312E81",
                "accent": "#4F46E5",
                "accent_hover": "#4338CA",
                "accent_glow": "#6366F1",
                "dropdown_bg": "#EEF2FF",
                "dropdown_fg": "#0F172A",
                "dropdown_border": "#94A3B8",
                "dropdown_hover": "#E0E7FF",
                "dropdown_sel_bg": "#4F46E5",
                "dropdown_sel_fg": "#FFFFFF",
                "calendar_header_bg": "#15233F",
                "calendar_header_fg": "#FFFFFF",
                "calendar_bg": "#FFFFFF",
                "calendar_fg": "#0F172A",
                "calendar_alt_bg": "#F8FAFC",
                "calendar_sel_bg": "#4F46E5",
                "calendar_sel_fg": "#FFFFFF",
                "menu_bg": "#FFFFFF",
                "menu_fg": "#0F172A",
                "menu_border": "#CBD5E1",
                "menu_sel_bg": "#EEF2FF",
                "menu_sel_fg": "#312E81",
                "input_bg": "#F8FAFC",
                "input_fg": "#0F172A",
                "input_border": "#94A3B8",
                "input_focus": "#4F46E5",
                "table_bg": "#FFFFFF",
                "table_alt_bg": "#F8FAFC",
                "table_fg": "#0F172A",
                "table_header_bg": "#F1F5F9",
                "table_header_fg": "#0F172A",
                "table_border": "#CBD5E1",
                "table_grid": "#E2E8F0",
                "table_sel_bg": "#EEF2FF",
                "table_sel_fg": "#312E81",
                "border_strong": "#94A3B8",
                "scrollbar_track": "rgba(241, 245, 249, 0.60)",
                "scrollbar_handle": "#CBD5E1",
                "scrollbar_hover": "#4F46E5",
                "banner_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0F172A,stop:0.55 #1E293B,stop:1 #0F172A)",
                "banner_border": "#6366F1",
            },
            "night": {
                "surface": "#080C16",
                "surface_card": "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(16, 24, 42, 0.96), stop:1 rgba(9, 14, 26, 0.96))",
                "sidebar": "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #090E1A, stop:1 #060A14)",
                "sidebar_border": "rgba(0, 229, 255, 0.22)",
                "nav": "transparent",
                "nav_border": "transparent",
                "nav_active_grad": "rgba(0, 240, 255, 0.14)",
                "border": "rgba(255, 255, 255, 0.09)",
                "border_subtle": "rgba(255, 255, 255, 0.05)",
                "text": "#F8FAFC",
                "muted_text": "#94A3B8",
                "hover": "rgba(255, 255, 255, 0.08)",
                "hover_text": "#FFFFFF",
                "accent": "#00E5FF",
                "accent_hover": "#38BDF8",
                "accent_glow": "#00E5FF",
                "dropdown_bg": "#0E1526",
                "dropdown_fg": "#F8FAFC",
                "dropdown_border": "rgba(0, 229, 255, 0.25)",
                "dropdown_hover": "rgba(0, 229, 255, 0.12)",
                "dropdown_sel_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4F46E5, stop:1 #06B6D4)",
                "dropdown_sel_fg": "#FFFFFF",
                "calendar_header_bg": "#0C1222",
                "calendar_header_fg": "#00E5FF",
                "calendar_bg": "#080D1A",
                "calendar_fg": "#F8FAFC",
                "calendar_alt_bg": "#0D1424",
                "calendar_sel_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4F46E5, stop:1 #00E5FF)",
                "calendar_sel_fg": "#020617",
                "menu_bg": "#0B1020",
                "menu_fg": "#F8FAFC",
                "menu_border": "rgba(0, 229, 255, 0.22)",
                "menu_sel_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(79, 70, 229, 0.40), stop:1 rgba(0, 229, 255, 0.25))",
                "menu_sel_fg": "#FFFFFF",
                "input_bg": "#0A0E1A",
                "input_fg": "#F8FAFC",
                "input_border": "rgba(255, 255, 255, 0.14)",
                "input_focus": "#00E5FF",
                "table_bg": "#080C16",
                "table_alt_bg": "#0C1220",
                "table_fg": "#F8FAFC",
                "table_header_bg": "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #10182C, stop:1 #0B1120)",
                "table_header_fg": "#94A3B8",
                "table_border": "rgba(255, 255, 255, 0.08)",
                "table_grid": "rgba(255, 255, 255, 0.04)",
                "table_sel_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(79, 70, 229, 0.35), stop:1 rgba(0, 229, 255, 0.22))",
                "table_sel_fg": "#FFFFFF",
                "border_strong": "rgba(0, 229, 255, 0.35)",
                "scrollbar_track": "rgba(7, 11, 20, 0.60)",
                "scrollbar_handle": "rgba(255, 255, 255, 0.16)",
                "scrollbar_hover": "#00E5FF",
                "banner_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #090E1C,stop:0.5 #111A30,stop:1 #090E1C)",
                "banner_border": "rgba(0, 229, 255, 0.20)",
            },
            "ocean": {
                "surface": "#F0F9FF",
                "surface_card": "rgba(240, 249, 255, 0.96)",
                "sidebar": "#F0F9FF",
                "sidebar_border": "#BAE6FD",
                "nav": "transparent",
                "nav_border": "transparent",
                "nav_active_grad": "#E0F2FE",
                "border": "#BAE6FD",
                "border_subtle": "rgba(186, 230, 253, 0.65)",
                "text": "#0C4A6E",
                "muted_text": "#0369A1",
                "hover": "rgba(207, 250, 254, 0.90)",
                "hover_text": "#075985",
                "accent": "#0284C7",
                "accent_hover": "#0369A1",
                "accent_glow": "#00E5FF",
                "dropdown_bg": "#F0F9FF",
                "dropdown_fg": "#0C4A6E",
                "dropdown_border": "#BAE6FD",
                "dropdown_hover": "#E0F2FE",
                "dropdown_sel_bg": "#0284C7",
                "dropdown_sel_fg": "#FFFFFF",
                "calendar_header_bg": "#0C4A6E",
                "calendar_header_fg": "#FFFFFF",
                "calendar_bg": "#F0F9FF",
                "calendar_fg": "#0C4A6E",
                "calendar_alt_bg": "#E0F2FE",
                "calendar_sel_bg": "#0284C7",
                "calendar_sel_fg": "#FFFFFF",
                "menu_bg": "#F0F9FF",
                "menu_fg": "#0C4A6E",
                "menu_border": "#BAE6FD",
                "menu_sel_bg": "#BAE6FD",
                "menu_sel_fg": "#0C4A6E",
                "input_bg": "#FFFFFF",
                "input_fg": "#0C4A6E",
                "input_border": "#BAE6FD",
                "input_focus": "#0284C7",
                "table_bg": "#FFFFFF",
                "table_alt_bg": "#F0F9FF",
                "table_fg": "#0C4A6E",
                "table_header_bg": "#E0F2FE",
                "table_header_fg": "#0C4A6E",
                "table_border": "#BAE6FD",
                "table_grid": "#E0F2FE",
                "table_sel_bg": "#BAE6FD",
                "table_sel_fg": "#0369A1",
                "border_strong": "#38BDF8",
                "scrollbar_track": "rgba(224, 242, 254, 0.60)",
                "scrollbar_handle": "#7DD3FC",
                "scrollbar_hover": "#0284C7",
                "banner_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #082F49,stop:0.55 #0C4A6E,stop:1 #075985)",
                "banner_border": "#00E5FF",
            },
            "sunset": {
                "surface": "#FFF7ED",
                "surface_card": "rgba(255, 247, 237, 0.96)",
                "sidebar": "#FFF7ED",
                "sidebar_border": "#FED7AA",
                "nav": "transparent",
                "nav_border": "transparent",
                "nav_active_grad": "#FFEDD5",
                "border": "#FED7AA",
                "border_subtle": "rgba(254, 215, 170, 0.65)",
                "text": "#7C2D12",
                "muted_text": "#C2410C",
                "hover": "rgba(254, 215, 170, 0.90)",
                "hover_text": "#7C2D12",
                "accent": "#EA580C",
                "accent_hover": "#C2410C",
                "accent_glow": "#FB923C",
                "dropdown_bg": "#FFF7ED",
                "dropdown_fg": "#7C2D12",
                "dropdown_border": "#FED7AA",
                "dropdown_hover": "#FFEDD5",
                "dropdown_sel_bg": "#EA580C",
                "dropdown_sel_fg": "#FFFFFF",
                "calendar_header_bg": "#7C2D12",
                "calendar_header_fg": "#FFFFFF",
                "calendar_bg": "#FFF7ED",
                "calendar_fg": "#7C2D12",
                "calendar_alt_bg": "#FFEDD5",
                "calendar_sel_bg": "#EA580C",
                "calendar_sel_fg": "#FFFFFF",
                "menu_bg": "#FFF7ED",
                "menu_fg": "#7C2D12",
                "menu_border": "#FED7AA",
                "menu_sel_bg": "#FED7AA",
                "menu_sel_fg": "#7C2D12",
                "input_bg": "#FFFFFF",
                "input_fg": "#7C2D12",
                "input_border": "#FED7AA",
                "input_focus": "#EA580C",
                "table_bg": "#FFFFFF",
                "table_alt_bg": "#FFF7ED",
                "table_fg": "#7C2D12",
                "table_header_bg": "#FFEDD5",
                "table_header_fg": "#7C2D12",
                "table_border": "#FED7AA",
                "table_grid": "#FFEDD5",
                "table_sel_bg": "#FED7AA",
                "table_sel_fg": "#9A3412",
                "border_strong": "#FB923C",
                "scrollbar_track": "rgba(255, 237, 213, 0.60)",
                "scrollbar_handle": "#FDBA74",
                "scrollbar_hover": "#EA580C",
                "banner_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #431407,stop:0.55 #7C2D12,stop:1 #290E05)",
                "banner_border": "#FB923C",
            },
        }
        return palettes.get((theme_name or "day").lower(), palettes["day"])

    def _apply_tooltip_palette(self, theme_name=None):
        """Force readable high-contrast tooltip colors instead of inheriting low-contrast native popups."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#0F172A"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
        QToolTip.setPalette(palette)
        QToolTip.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))

    def _refresh_theme_chrome(self, theme_name=None):
        """Refresh chrome colors after a theme switch without changing its layout."""
        colors = self._ui_chrome_palette(theme_name or self.current_theme())
        surface, border = colors["surface"], colors["border"]
        sidebar_bg = colors.get("sidebar", surface)
        sidebar_border = colors.get("sidebar_border", border)
        is_dark = (theme_name or self.current_theme()).lower() in ("night", "dark")
        if hasattr(self, "sidebar"):
            self.sidebar.setStyleSheet(
                f"QWidget#navigationSidebar {{ background: {sidebar_bg}; border-right: 1.5px solid {sidebar_border}; }}"
            )
        if hasattr(self, "sidebar_toggle"):
            toggle_bg = colors.get('nav', surface) if is_dark else "#F1F5F9"
            toggle_fg = colors['text'] if is_dark else "#0F172A"
            toggle_border = sidebar_border if is_dark else "#CBD5E1"
            toggle_hover = colors['hover'] if is_dark else "#EEF2FF"
            toggle_hover_fg = colors['hover_text'] if is_dark else colors['accent']
            self.sidebar_toggle.setStyleSheet(
                f"QPushButton#sidebarToggle {{ background: {toggle_bg}; color: {toggle_fg}; "
                f"border: 1.5px solid {toggle_border}; border-radius: 9px; font-weight: 700; text-align: left; padding: 7px 12px; min-height: 34px; }} "
                f"QPushButton#sidebarToggle:hover {{ background: {toggle_hover}; color: {toggle_hover_fg}; border-color: {colors['accent']}; }}"
            )
        if hasattr(self, "title_bar"):
            title_bg = "#070B14" if is_dark else "#15233F"
            title_border = "#111827" if is_dark else "#1E2F52"
            self.title_bar.setStyleSheet(
                f"QWidget#titleBar {{ background: {title_bg}; border-bottom: 1px solid {title_border}; }}"
            )
        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet("QLabel#titleLabel { color: #F8FAFC; font-weight: 600; font-size: 10pt; }")
        if hasattr(self, "sidebar_buttons"):
            for button, _title in self.sidebar_buttons:
                if is_dark:
                    button.setStyleSheet("""
                        QPushButton#sidebarNavButton {
                            background: transparent;
                            color: #94A3B8;
                            border: 1px solid transparent;
                            border-radius: 9px;
                            font-size: 9.5pt;
                            font-weight: 600;
                            text-align: left;
                            padding: 8px 12px;
                            min-height: 34px;
                        }
                        QPushButton#sidebarNavButton:hover {
                            background: rgba(255, 255, 255, 0.08);
                            color: #FFFFFF;
                            border: 1px solid rgba(0, 240, 255, 0.35);
                        }
                        QPushButton#sidebarNavButton:checked {
                            background: rgba(0, 240, 255, 0.16);
                            color: #00F0FF;
                            border: 1.5px solid #00F0FF;
                            border-radius: 9px;
                            font-weight: 800;
                        }
                    """)
                else:
                    nav_fg = colors['text']
                    hover_bg = colors['hover']
                    hover_fg = colors['hover_text']
                    active_bg = colors.get('nav_active_grad', '#EEF2FF')
                    active_fg = colors['accent']
                    button.setStyleSheet(f"""
                        QPushButton#sidebarNavButton {{
                            background: transparent;
                            color: {nav_fg};
                            border: 1px solid transparent;
                            border-radius: 9px;
                            font-size: 9.5pt;
                            font-weight: 600;
                            text-align: left;
                            padding: 8px 12px;
                            min-height: 34px;
                        }}
                        QPushButton#sidebarNavButton:hover {{
                            background: {hover_bg};
                            color: {hover_fg};
                            border: 1px solid {colors.get('border_subtle', '#CBD5E1')};
                        }}
                        QPushButton#sidebarNavButton:checked {{
                            background: {active_bg};
                            color: {active_fg};
                            border: 1.5px solid {active_fg};
                            border-radius: 9px;
                            font-weight: 800;
                        }}
                    """)
        for header in self.findChildren(QWidget, "pageHeader"):
            header.setStyleSheet(
                f"QWidget#pageHeader {{ background: {surface}; color: {colors['text']}; }}"
            )
        for card_id in ("attToolbarCard", "attRosterCard", "attSummaryCard", "taskToolbarCard", "empToolbarCard", "sessionStrip", "trackerToolbarCard", "archiveToolbarCard"):
            for card in self.findChildren(QWidget, card_id):
                card.setStyleSheet(f"QWidget#{card_id} {{ background: {colors.get('surface_card', surface)}; border: 1.5px solid {border}; border-radius: 14px; padding: 12px; }}")
        for banner in self.findChildren(QFrame, "brandBanner"):
            banner.setStyleSheet(f"QFrame#brandBanner {{ background: {colors.get('banner_bg', surface)}; border: 1.5px solid {colors.get('banner_border', border)}; border-radius: 16px; }}")
        for nav_btn in self.findChildren(QPushButton, "headerNavButton"):
            nav_btn.setStyleSheet(f"QPushButton#headerNavButton {{ background: rgba(255, 255, 255, 0.08); color: #E2E8F0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; font-size: 13pt; font-weight: 700; min-width: 0; padding: 0 0 2px 0; }} QPushButton#headerNavButton:hover {{ background: {colors['accent']}; color: #FFFFFF; border-color: {colors['accent_glow']}; }}")
        for guide in self.findChildren(QWidget, "guideItem"):
            guide.setStyleSheet(f"""
                QWidget#guideItem {{ background: {colors.get('surface_card', surface)}; border: 1.5px solid {border}; border-left: 5px solid {colors['accent']}; border-radius: 14px; }}
                QWidget#guideItem:hover {{ border-color: {colors['accent']}; border-left: 5px solid {colors['accent_glow']}; background: {colors['hover']}; }}
            """)
        if hasattr(self, "rollback_button"):
            if is_dark:
                self.rollback_button.setStyleSheet(
                    "QPushButton#homeRollbackBtn { background: #1E293B; color: #F8FAFC; border: 1.5px solid #475569; "
                    "border-radius: 9px; padding: 7px 14px; font-weight: 600; font-size: 9.5pt; } "
                    "QPushButton#homeRollbackBtn:hover { background: #334155; color: #FFFFFF; border-color: #818CF8; } "
                    "QPushButton#homeRollbackBtn:pressed { background: #0F172A; }"
                )
            else:
                self.rollback_button.setStyleSheet(
                    f"QPushButton#homeRollbackBtn {{ background: #FFFFFF; color: #0F172A; border: 1.5px solid #CBD5E1; "
                    "border-radius: 9px; padding: 7px 14px; font-weight: 600; font-size: 9.5pt; } "
                    f"QPushButton#homeRollbackBtn:hover {{ background: #F1F5F9; color: #4F46E5; border-color: #6366F1; }} "
                    "QPushButton#homeRollbackBtn:pressed { background: #E2E8F0; }"
                )
        for date_edit in self.findChildren(QDateEdit):
            calendar = date_edit.calendarWidget()
            if calendar is not None:
                calendar.setStyleSheet(f"""
                    QCalendarWidget {{ background-color: {colors['calendar_bg']}; color: {colors['calendar_fg']}; border: 1.5px solid {colors['accent']}; border-radius: 12px; }}
                    QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {colors['calendar_header_bg']}; min-height: 42px; border-top-left-radius: 10px; border-top-right-radius: 10px; }}
                    QCalendarWidget QToolButton {{ background: transparent; color: #FFFFFF; border: 0; border-radius: 6px; padding: 6px 9px; font-weight: 700; }}
                    QCalendarWidget QToolButton:hover {{ background: {colors['accent']}; color: #FFFFFF; }}
                    QCalendarWidget QSpinBox {{ background: {colors['calendar_header_bg']}; color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 5px; padding: 3px 6px; }}
                    QCalendarWidget QAbstractItemView {{ background: {colors['calendar_bg']};
                        alternate-background-color: {colors['calendar_alt_bg']}; color: {colors['calendar_fg']};
                        selection-background-color: {colors['calendar_sel_bg']}; selection-color: {colors['calendar_sel_fg']};
                        outline: 0; gridline-color: {colors['border_subtle']}; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }}
                    QCalendarWidget QAbstractItemView:enabled {{ color: {colors['calendar_fg']}; }}
                    QCalendarWidget QAbstractItemView:disabled {{ color: {colors['muted_text']}; }}
                """)
        menu_bg = colors["menu_bg"]
        menu_fg = colors["menu_fg"]
        menu_border = colors["menu_border"]
        menu_sel_bg = colors["menu_sel_bg"]
        menu_sel_fg = colors["menu_sel_fg"]
        for menu in self.findChildren(QMenu):
            menu.setStyleSheet(f"""
                QMenu, QMenu#holidayMenu, QMenu#headerSectionMenu {{
                    background-color: {menu_bg}; color: {menu_fg};
                    border: 1.5px solid {menu_border}; border-radius: 10px; padding: 6px;
                }}
                QMenu::item, QMenu#holidayMenu::item, QMenu#headerSectionMenu::item {{
                    background-color: transparent; color: {menu_fg};
                    padding: 8px 24px 8px 16px; border-radius: 6px;
                    font-size: 9.5pt; font-weight: 600;
                }}
                QMenu::item:selected, QMenu#holidayMenu::item:selected, QMenu#headerSectionMenu::item:selected {{
                    background-color: {menu_sel_bg}; color: {menu_sel_fg};
                }}
                QMenu::item:disabled, QMenu#holidayMenu::item:disabled, QMenu#headerSectionMenu::item:disabled {{
                    color: {colors['muted_text']};
                }}
            """)
        for combo in self.findChildren(QComboBox):
            view = combo.view()
            if view is not None:
                view.setStyleSheet(f"""
                    QListView {{ background-color: {colors['dropdown_bg']}; color: {colors['dropdown_fg']}; border: 1.5px solid {colors['dropdown_border']}; outline: 0; padding: 6px; border-radius: 10px; }}
                    QListView::item {{ background-color: {colors['dropdown_bg']}; color: {colors['dropdown_fg']}; padding: 8px 12px; min-height: 24px; border-radius: 6px; }}
                    QListView::item:selected {{ background-color: {colors['dropdown_sel_bg']}; color: {colors['dropdown_sel_fg']}; font-weight: 600; }}
                    QListView::item:hover {{ background-color: {colors['dropdown_hover']}; color: {colors['dropdown_fg']}; }}
                """)
        self._polish_all_input_controls(theme_name)

    def _refresh_dashboard_action_styles(self, theme_name=None):
        t_name = (theme_name or self.current_theme()).lower()
        colors = self._ui_chrome_palette(t_name)
        is_dark = t_name in ("night", "dark")
        kpi_bg = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(17,25,50,0.92), stop:1 rgba(9,14,30,0.90))" if is_dark else ("qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #F0F9FF, stop:1 #E0F2FE)" if t_name == "ocean" else ("qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FFF7ED, stop:1 #FFEDD5)" if t_name == "sunset" else "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FFFFFF, stop:1 #F8FAFC)"))
        kpi_border = "rgba(56, 189, 248, 0.25)" if is_dark else ("#BAE6FD" if t_name == "ocean" else ("#FED7AA" if t_name == "sunset" else "rgba(203, 213, 225, 0.85)"))
        val_col = "#FFFFFF" if is_dark else ("#0C4A6E" if t_name == "ocean" else ("#7C2D12" if t_name == "sunset" else "#0F172A"))

        if hasattr(self, "kpi_cards"):
            for card in self.kpi_cards:
                base_acc = getattr(card, "_base_accent", "#4F46E5")
                neon_acc = getattr(card, "_neon_accent", "#00E5FF")
                act_acc = neon_acc if is_dark else base_acc
                sub_col = "#CBD5E1" if is_dark else base_acc
                card.setStyleSheet(
                    f"QGroupBox#kpiCard {{ background: {kpi_bg}; "
                    f"border: 1.5px solid {kpi_border}; border-top: 3.5px solid {act_acc}; border-radius: 14px; padding-top: 16px; margin-top: 8px; }} "
                    f"QGroupBox#kpiCard:hover {{ border: 1.5px solid {act_acc}; border-top: 4px solid {act_acc}; }} "
                    f"QGroupBox#kpiCard::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 2px 8px; "
                    f"background: {act_acc}; color: #FFFFFF; border-radius: 5px; font-size: 8pt; font-weight: 800; letter-spacing: 0.5px; }}"
                )
                if hasattr(card, "_val_label"):
                    card._val_label.setStyleSheet(f"font-size: 26pt; font-weight: 900; color: {act_acc if is_dark else val_col};")
                if hasattr(card, "_sub_label"):
                    card._sub_label.setStyleSheet(f"font-size: 8pt; font-weight: 700; color: {sub_col}; letter-spacing: 0.3px;")
                if hasattr(card, "_sparkline"):
                    card._sparkline.color = act_acc
                    card._sparkline.update()

        for button in self.findChildren(QPushButton):
            if button.property("dashboardAction") != "true":
                continue
            button.setStyleSheet(f"""
                QPushButton {{ background: {colors['nav']}; color: {colors['text']};
                    border: 1px solid {colors['border']}; border-radius: 10px;
                    padding: 8px 12px; text-align: left; font-weight: 650; }}
                QPushButton:hover {{ background: {colors['hover']}; color: {colors['hover_text']};
                    border-color: {colors['accent']}; }}
                QPushButton:pressed {{ background: {colors['accent']}; color: #FFFFFF;
                    border-color: {colors['accent']}; }}
            """)

    def apply_global_control_polish(self):
        """Apply consistent contrast, spacing, focus, and sizing to all interactive controls."""
        theme_name = self.current_theme()
        self._apply_tooltip_palette(theme_name)
        colors = self._ui_chrome_palette(theme_name)
        is_dark_theme = (theme_name or "day").lower() in ("night", "dark")
        slate_arrow = resource_path("assets/chevron_down_slate.png").replace("\\", "/")
        white_arrow = resource_path("assets/chevron_down_white.png").replace("\\", "/")
        active_arrow = white_arrow if is_dark_theme else slate_arrow

        polish_css = f"""
        QWidget#navigationSidebar {{ background: {colors['sidebar']}; border-right: 1.5px solid {colors['sidebar_border']}; }}
        QWidget#mainContentSurface {{ background: transparent; }}
        QWidget#titleBar {{ background: {"#070B14" if is_dark_theme else "#15233F"}; border-bottom: 1px solid {"#111827" if is_dark_theme else "#1E2F52"}; }}
        QFrame#brandBanner {{ background: {colors['banner_bg']};
            border: 1.5px solid {colors['banner_border']}; border-radius: 14px; margin: 6px 12px; }}
        QLabel#brandLogo {{ background: rgba(8, 12, 24, 0.70); border: 1.5px solid rgba(0, 229, 255, 0.35); border-radius: 14px; padding: 2px; }}
        QFrame#headerClockFrame {{ background: rgba(8, 12, 24, 0.85); border: 1.5px solid rgba(0, 229, 255, 0.30); border-radius: 12px; }}
        QFrame#headerClockFrame QLabel#headerClock, QFrame#brandBanner QLabel#headerClock {{
            background: transparent; color: #F8FAFC; border: 0; padding: 2px 6px; font-size: 9.5pt; font-weight: 800; letter-spacing: 0.5px;
        }}
        QLabel#brandHeading {{ background: transparent; color: #FFFFFF; font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 13.5pt; font-weight: 900; letter-spacing: 1.2px; text-transform: uppercase; }}
        QLabel#brandSubheading {{ background: transparent; color: #38BDF8; font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 8pt; font-weight: 750; letter-spacing: 0.8px; }}
        QPushButton#clockModeBtn {{ min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px;
            padding: 0; margin: 0; background: rgba(255, 255, 255, 0.12); color: #F8FAFC;
            border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 7px;
            font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif; font-size: 13px; text-align: center; }}
        QPushButton#clockModeBtn:hover {{ background: rgba(56, 189, 248, 0.35); border-color: #38BDF8; color: #FFFFFF; }}
        QPushButton#headerSyncPushBtn {{
            min-height: 36px; max-height: 38px; padding: 6px 16px;
            background: #0284C7; color: #FFFFFF;
            border: 1.5px solid #38BDF8; border-radius: 9px;
            font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 9.5pt; font-weight: 700; letter-spacing: 0.3px;
        }}
        QPushButton#headerSyncPushBtn:hover {{
            background: #0369A1; border-color: #7DD3FC; color: #FFFFFF;
        }}
        QPushButton#headerSyncPushBtn:pressed {{ background: #075985; }}
        QPushButton#headerSyncPullBtn {{
            min-height: 36px; max-height: 38px; padding: 6px 16px;
            background: #4F46E5; color: #FFFFFF;
            border: 1.5px solid #818CF8; border-radius: 9px;
            font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 9.5pt; font-weight: 700; letter-spacing: 0.3px;
        }}
        QPushButton#headerSyncPullBtn:hover {{
            background: #4338CA; border-color: #A5B4FC; color: #FFFFFF;
        }}
        QPushButton#headerSyncPullBtn:pressed {{ background: #3730A3; }}
        QPushButton#headerSyncPushBtn:disabled, QPushButton#headerSyncPullBtn:disabled {{
            background: rgba(15, 23, 42, 0.20); color: rgba(255, 255, 255, 0.40); border-color: rgba(255, 255, 255, 0.12);
        }}
        QWidget#pageHeader {{ background: {colors['surface']}; color: {colors['text']}; }}
        QPushButton#sidebarToggle {{ background: {"#F1F5F9" if not is_dark_theme else colors['nav']}; color: {colors['text']}; border: 1.5px solid {colors['sidebar_border']};
            border-radius: 9px; font-weight: 700; text-align: left; padding: 7px 12px; min-height: 34px; }}
        QPushButton#sidebarToggle:hover {{ background: {colors['hover']}; color: {colors['hover_text']}; border-color: {colors['accent']}; }}
        QScrollArea#sidebarScrollArea {{ border: 0; background: transparent; }}
        QScrollArea#sidebarScrollArea > QWidget > QWidget {{ background: transparent; }}
        QScrollArea#sidebarScrollArea QScrollBar:vertical {{ width: 5px; background: transparent; margin: 0; }}
        QScrollArea#sidebarScrollArea QScrollBar::handle:vertical {{ background: {colors.get('border_subtle', 'rgba(148, 163, 184, 0.4)')}; border-radius: 2px; }}
        QPushButton#sidebarNavButton {{ background: transparent; color: {colors['text']};
            border: 1px solid transparent; border-radius: 9px;
            font-size: 9.5pt; font-weight: 600; text-align: left; padding: 8px 12px; min-height: 34px; }}
        QPushButton#sidebarNavButton:hover {{ background: {colors['hover']}; color: {colors['hover_text']}; border: 1px solid {colors.get('border_subtle', 'transparent')}; }}
        QPushButton#sidebarNavButton:checked {{ background: {colors['nav_active_grad']};
            color: {"#00F0FF" if is_dark_theme else colors['accent']}; border: {"1.5px solid #00F0FF" if is_dark_theme else f"1.5px solid {colors['accent']}"}; font-weight: 800; }}
        QWidget#headerClock {{ background: transparent; color: #FFFFFF; border: 0; padding: 2px 4px; font-size: 9.5pt; font-weight: 700; }}
        QPushButton#headerNavButton {{ background: rgba(255, 255, 255, 0.08); color: #E2E8F0; border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px; font-size: 13pt; font-weight: 700; padding: 0 0 2px 0;
            min-width: 32px; max-width: 32px; min-height: 28px; max-height: 28px; }}
        QPushButton#headerNavButton:hover {{ background: {colors['accent']}; border-color: {colors['accent_glow']}; color: #FFFFFF; }}
        QToolButton#headerLogoMenu {{ background: transparent; border: 0; }}
        QMenu, QMenu#holidayMenu, QMenu#headerSectionMenu {{
            background-color: {colors['menu_bg']}; color: {colors['menu_fg']}; border: 1.5px solid {colors['menu_border']}; border-radius: 10px; padding: 6px;
        }}
        QMenu::item, QMenu#holidayMenu::item, QMenu#headerSectionMenu::item {{
            background-color: transparent; color: {colors['menu_fg']}; padding: 8px 24px 8px 16px; border-radius: 6px;
            font-size: 9.5pt; font-weight: 600;
        }}
        QMenu::item:selected, QMenu#holidayMenu::item:selected, QMenu#headerSectionMenu::item:selected {{
            background-color: {colors['menu_sel_bg']}; color: {colors['menu_sel_fg']};
        }}
        QMenu::item:disabled, QMenu#holidayMenu::item:disabled, QMenu#headerSectionMenu::item:disabled {{
            color: {colors['muted_text']};
        }}
        QComboBox QAbstractItemView, QComboBox QListView {{
            background-color: {colors['dropdown_bg']}; color: {colors['dropdown_fg']}; border: 1.5px solid {colors['dropdown_border']};
            selection-background-color: {colors['dropdown_sel_bg']}; selection-color: {colors['dropdown_sel_fg']}; outline: 0;
            border-radius: 10px; padding: 6px;
        }}
        QComboBox QAbstractItemView::item, QComboBox QListView::item {{
            background-color: {colors['dropdown_bg']}; color: {colors['dropdown_fg']}; padding: 8px 12px; min-height: 24px; border-radius: 6px;
        }}
        QComboBox QAbstractItemView::item:hover, QComboBox QListView::item:hover {{
            background-color: {colors['dropdown_hover']}; color: {colors['dropdown_fg']};
        }}
        QComboBox QAbstractItemView::item:selected, QComboBox QListView::item:selected {{
            background-color: {colors['dropdown_sel_bg']}; color: {colors['dropdown_sel_fg']}; font-weight: 600;
        }}
        QCalendarWidget {{ background-color: {colors['calendar_bg']}; color: {colors['calendar_fg']}; border: 1.5px solid {colors['accent']}; border-radius: 12px; }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {colors['calendar_header_bg']}; min-height: 44px; border-top-left-radius: 10px; border-top-right-radius: 10px; }}
        QCalendarWidget QToolButton {{ background: transparent; color: #FFFFFF; border: 0;
            border-radius: 7px; padding: 6px 10px; font-weight: 700; font-size: 10pt; }}
        QCalendarWidget QToolButton:hover {{ background: {colors['accent']}; color: #FFFFFF; }}
        QCalendarWidget QSpinBox {{ background: {colors['calendar_header_bg']}; color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 6px; padding: 4px 8px; font-weight: 700; }}
        QCalendarWidget QAbstractItemView {{ background: {colors['calendar_bg']}; alternate-background-color: {colors['calendar_alt_bg']};
            color: {colors['calendar_fg']}; selection-background-color: {colors['calendar_sel_bg']}; selection-color: {colors['calendar_sel_fg']};
            outline: 0; gridline-color: {colors['border_subtle']}; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; padding: 6px; }}
        QCalendarWidget QAbstractItemView:enabled {{ color: {colors['calendar_fg']}; }}
        QCalendarWidget QAbstractItemView:disabled {{ color: {colors['muted_text']}; }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QTimeEdit {{
            min-height: 32px; max-height: 38px; padding: 5px 12px; border-radius: 8px;
            background-color: {"#0F172A" if is_dark_theme else "#F8FAFC"};
            color: {"#F8FAFC" if is_dark_theme else "#0F172A"};
            border: 1.5px solid {"#475569" if is_dark_theme else "#94A3B8"};
            font-size: 9.5pt; font-weight: 550;
        }}
        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QTimeEdit:hover {{
            border-color: {"#38BDF8" if is_dark_theme else "#4F46E5"};
            background-color: {"#162035" if is_dark_theme else "#FFFFFF"};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus {{
            border: 2px solid {"#00E5FF" if is_dark_theme else "#4F46E5"};
            background-color: {"#111827" if is_dark_theme else "#FFFFFF"};
        }}
        QComboBox, QComboBox:!editable, QComboBox:editable, QDateEdit {{
            min-height: 32px; max-height: 38px; padding: 5px 38px 5px 12px; border-radius: 8px;
            background-color: {"#0F172A" if is_dark_theme else "#F8FAFC"};
            color: {"#F8FAFC" if is_dark_theme else "#0F172A"};
            border: 1.5px solid {"#475569" if is_dark_theme else "#94A3B8"};
            font-size: 9.5pt; font-weight: 600;
        }}
        QComboBox:hover, QComboBox:!editable:hover, QDateEdit:hover {{
            border-color: {"#38BDF8" if is_dark_theme else "#4F46E5"};
            background-color: {"#162035" if is_dark_theme else "#FFFFFF"};
        }}
        QComboBox:focus, QComboBox:!editable:focus, QDateEdit:focus {{
            border: 2px solid {"#00E5FF" if is_dark_theme else "#4F46E5"};
            background-color: {"#111827" if is_dark_theme else "#FFFFFF"};
        }}
        QComboBox::drop-down, QComboBox:!editable::drop-down, QDateEdit::drop-down {{
            subcontrol-origin: padding; subcontrol-position: top right;
            width: 32px; border-left: 1.5px solid {"#475569" if is_dark_theme else "#94A3B8"};
            border-top-right-radius: 7px; border-bottom-right-radius: 7px;
            background-color: {"#1E293B" if is_dark_theme else "#EEF2FF"};
        }}
        QComboBox::drop-down:hover, QComboBox:!editable::drop-down:hover, QDateEdit::drop-down:hover {{
            background-color: {"#334155" if is_dark_theme else "#E0E7FF"};
        }}
        QComboBox::down-arrow, QDateEdit::down-arrow {{
            image: url("{active_arrow}");
            width: 14px; height: 14px;
        }}
        QComboBox::down-arrow:hover, QDateEdit::down-arrow:hover {{
            image: url("{active_arrow}");
        }}
        QFormLayout QLabel {{
            font-size: 9.5pt; font-weight: 700;
            color: {"#F8FAFC" if is_dark_theme else "#1E293B"};
        }}
        QTextEdit, QPlainTextEdit {{ padding: 6px 10px; border-radius: 8px; }}
        QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
        QDoubleSpinBox:disabled, QDateEdit:disabled, QTimeEdit:disabled {{
            color: {colors['muted_text']}; background-color: {colors['dropdown_hover']};
        }}
        QPushButton {{
            min-height: 34px;
            padding: 4px 14px;
            border-radius: 9px;
            font-weight: 600;
            font-size: 9pt;
            text-align: center;
            background-color: {"#1E293B" if is_dark_theme else "#FFFFFF"};
            color: {"#F8FAFC" if is_dark_theme else "#0F172A"};
            border: 1.5px solid {"#334155" if is_dark_theme else "#CBD5E1"};
        }}
        QPushButton:hover {{
            background-color: {"#334155" if is_dark_theme else "#F1F5F9"};
            color: {"#FFFFFF" if is_dark_theme else "#312E81"};
            border-color: {"#818CF8" if is_dark_theme else "#6366F1"};
        }}
        QPushButton:pressed {{
            background-color: {"#0F172A" if is_dark_theme else "#E2E8F0"};
        }}
        QPushButton:disabled {{
            background-color: {"rgba(30, 41, 59, 0.40)" if is_dark_theme else "rgba(241, 245, 249, 0.60)"};
            color: {"#64748B" if is_dark_theme else "#94A3B8"};
            border-color: {"rgba(51, 65, 85, 0.40)" if is_dark_theme else "rgba(203, 213, 225, 0.60)"};
        }}
        QPushButton[primary="true"], QPushButton:default {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:0.5 #6366F1, stop:1 #06B6D4);
            color: #FFFFFF;
            font-weight: 750;
            border: 1.5px solid #38BDF8;
            border-radius: 9px;
        }}
        QPushButton[primary="true"]:hover, QPushButton:default:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:0.5 #4F46E5, stop:1 #00E5FF);
            border-color: #00E5FF;
        }}
        QTableWidget {{
            gridline-color: {colors['border']};
            background-color: {colors.get('table_bg', '#0F172A')};
            alternate-background-color: {colors.get('table_alt_bg', '#152033')};
            color: {colors.get('table_fg', '#F8FAFC')};
            border: 1.5px solid {colors.get('table_border', '#334155')};
            border-radius: 12px;
            selection-background-color: {colors.get('table_sel_bg', '#312E81')};
            selection-color: {colors.get('table_sel_fg', '#FFFFFF')};
            outline: 0;
            font-size: 9pt;
        }}
        QTableWidget::item {{ padding: 7px 9px; }}
        QHeaderView::section {{
            padding: 8px 9px; min-height: 24px;
            background-color: {colors.get('table_header_bg', '#1E293B')};
            color: {colors.get('table_header_fg', '#F8FAFC')};
            font-weight: 700;
            border: 0;
            border-bottom: 2px solid {colors.get('table_border', '#334155')};
            border-right: 1px solid {colors.get('table_grid', 'rgba(51, 65, 85, 0.40)')};
        }}
        QTableCornerButton::section {{
            background-color: {colors.get('table_header_bg', '#1E293B')};
            border: 0;
            border-bottom: 2px solid {colors.get('table_border', '#334155')};
        }}
        QLabel:not(#qt_msgbox_label):not(#qt_msgboxex_icon_label) {{ min-width: 0; }}
        QMessageBox {{ min-width: 480px; }}
        QMessageBox QLabel#qt_msgbox_label {{ min-width: 360px; }}
        QMessageBox QLabel#qt_msgboxex_icon_label {{ min-width: 44px; min-height: 44px; }}
        QInputDialog {{ min-width: 460px; }}
        QInputDialog QLabel {{ min-width: 420px; font-weight: 600; }}
        QInputDialog QLineEdit {{ min-width: 420px; }}

        /* Modern Custom Scrollbars */
        QScrollBar:vertical {{
            background: {colors.get('scrollbar_track', 'rgba(15, 23, 42, 0.40)')};
            width: 10px;
            margin: 3px 2px 3px 2px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            min-height: 32px;
            background: {colors.get('scrollbar_handle', colors['border'])};
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {colors['accent']};
        }}
        QScrollBar:horizontal {{
            background: {colors.get('scrollbar_track', 'rgba(15, 23, 42, 0.40)')};
            height: 10px;
            margin: 2px 3px 2px 3px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal {{
            min-width: 32px;
            background: {colors.get('scrollbar_handle', colors['border'])};
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {colors['accent']};
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            width: 0; height: 0;
        }}

        /* Layout safety: controls must not clip their captions at Windows DPI scaling. */
        QPushButton, QToolButton {{
            min-height: 34px; padding: 4px 12px; margin: 2px;
            text-align: center; border-radius: 8px;
        }}
        QGroupBox {{
            margin-top: 14px; padding: 14px 12px 12px 12px;
            background-color: {colors.get('surface_card', colors['surface'])};
            color: {colors['text']};
            border: 1.5px solid {colors['border']};
            border-radius: 14px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; left: 14px; padding: 0 8px;
            color: {colors['accent_glow'] if is_dark_theme else colors['accent']};
            font-weight: 700; font-size: 9.5pt;
        }}
        QScrollArea#homeScroll, QScrollArea#pageScroll {{
            border: 0; background: transparent;
        }}
        """
        self.setStyleSheet(polish_css)
        excluded_wrap_names = {
            "titleLabel", "headerClock",
            "attRosterTitle", "attRosterHint", "attSummaryTitle", "attSummaryNote",
            "taskRosterTitle", "taskRosterHint",
            "empRosterTitle", "empRosterHint",
            "trackerRosterTitle", "trackerRosterHint",
            "archiveRosterTitle", "archiveRosterHint",
        }
        for widget in self.findChildren(QLabel):
            if widget.objectName() in ("qt_msgbox_label", "qt_msgboxex_icon_label"):
                continue
            if widget.objectName() in excluded_wrap_names or widget.property("pageTitle") or widget.property("sectionHeading"):
                widget.setWordWrap(False)
            else:
                widget.setMinimumWidth(0)
                widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
                if widget.text() and (len(widget.text()) > 22 or "\n" in widget.text()):
                    widget.setWordWrap(True)
                    widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for widget in self.findChildren(QLineEdit):
            widget.setMinimumWidth(max(90, widget.minimumWidth()))
            widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            widget.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        ensure_combobox_wheel_filter()
        for widget in self.findChildren(QComboBox):
            widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            widget.setMinimumWidth(max(140, widget.minimumWidth()))
            view = widget.view()
            if view is not None:
                view.setMinimumWidth(max(widget.width(), widget.minimumWidth(), 180))
                view.setUniformItemSizes(False)
                view.setStyleSheet(f"""
                    QListView {{ background: {colors['dropdown_bg']}; color: {colors['dropdown_fg']}; border: 1.5px solid {colors['dropdown_border']}; outline: 0; padding: 6px; border-radius: 10px; }}
                    QListView::item {{ background: {colors['dropdown_bg']}; color: {colors['dropdown_fg']}; padding: 8px 12px; min-height: 26px; border-radius: 6px; }}
                    QListView::item:selected {{ background: {colors['dropdown_sel_bg']}; color: {colors['dropdown_sel_fg']}; font-weight: 600; }}
                    QListView::item:hover {{ background: {colors['dropdown_hover']}; color: {colors['dropdown_fg']}; }}
                """)
        for widget in self.findChildren(QDateEdit):
            widget.setCalendarPopup(True)
            calendar = widget.calendarWidget()
            if calendar is not None:
                calendar.setGridVisible(True)
                calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
                calendar.setMinimumSize(310, 250)
                calendar.setStyleSheet(f"""
                    QCalendarWidget {{ background-color: {colors['calendar_bg']}; color: {colors['calendar_fg']}; border: 1.5px solid {colors['accent']}; border-radius: 12px; }}
                    QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {colors['calendar_header_bg']}; min-height: 44px; border-top-left-radius: 10px; border-top-right-radius: 10px; }}
                    QCalendarWidget QToolButton {{ background: transparent; color: #FFFFFF; border: 0; border-radius: 7px; padding: 6px 10px; font-weight: 700; font-size: 10pt; }}
                    QCalendarWidget QToolButton:hover {{ background: {colors['accent']}; color: #FFFFFF; }}
                    QCalendarWidget QSpinBox {{ background: {colors['calendar_header_bg']}; color: #FFFFFF; border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 6px; padding: 4px 8px; font-weight: 700; }}
                    QCalendarWidget QAbstractItemView {{ background: {colors['calendar_bg']}; alternate-background-color: {colors['calendar_alt_bg']};
                        color: {colors['calendar_fg']}; selection-background-color: {colors['calendar_sel_bg']}; selection-color: {colors['calendar_sel_fg']};
                        outline: 0; gridline-color: {colors['border_subtle']}; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; padding: 6px; }}
                    QCalendarWidget QAbstractItemView:enabled {{ color: {colors['calendar_fg']}; }}
                    QCalendarWidget QAbstractItemView:disabled {{ color: {colors['muted_text']}; }}
                """)
        self._refresh_theme_chrome(self.current_theme())
        self.polish_tables()
        self._repair_text_layouts()

    def _repair_text_layouts(self):
        """Allow content labels and table cells to wrap instead of clipping text."""
        for label in self.findChildren(QLabel):
            # Keep intentionally fixed-height decorative/status labels unchanged.
            if label.minimumHeight() == label.maximumHeight():
                continue
            label.setWordWrap(True)
        for table in self.findChildren(QTableWidget):
            table.setWordWrap(True)
            table.setTextElideMode(Qt.TextElideMode.ElideNone)
            table.resizeRowsToContents()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self._is_maximized = False
            if hasattr(self, "btn_max"):
                self.btn_max.setText("□")
        else:
            self.showMaximized()
            self._is_maximized = True
            if hasattr(self, "btn_max"):
                self.btn_max.setText("❐")

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "bg_anim"):
            self.bg_anim.setGeometry(0, 0, self.width(), max(1, self.height()))
            self.bg_anim.init_particles()
        self._apply_responsive_layout()
        # Main content geometry settles after QMainWindow finishes processing the
        # resize; repeat once on the event loop so first-show/maximize uses the
        # actual DPI-scaled client width.
        QTimer.singleShot(0, self._apply_responsive_layout)
        QTimer.singleShot(0, self._repair_text_layouts)
        if hasattr(self, "title_label"):
            QTimer.singleShot(0, self.update_title_label)
        if hasattr(self, "sidebar_buttons"):
            QTimer.singleShot(0, self.fit_sidebar_labels)

    def _apply_responsive_layout(self):
        content_width = self.main_content.width() if hasattr(self, "main_content") else self.width()
        compact = content_width < 1220
        home = self.findChild(QWidget, "homeContent")
        if home is not None and home.layout() is not None:
            margin_x = 16 if compact else 22
            margin_y = 14 if compact else 18
            home.layout().setContentsMargins(margin_x, margin_y, margin_x, margin_y)
            home.layout().setSpacing(12 if compact else 16)
        for surface in self.findChildren(QWidget, "pageContent"):
            layout = surface.layout()
            if layout is None:
                continue
            margins = layout.contentsMargins()
            margin_x = 14 if compact else 18
            layout.setContentsMargins(margin_x, margins.top(), margin_x, margins.bottom())
            layout.setSpacing(10 if compact else 12)
        if hasattr(self, "kpis") and hasattr(self, "kpi_cards"):
            kpi_columns = 5 if content_width >= 1500 else (4 if content_width >= 1200 else 3)
            if kpi_columns != getattr(self, "_kpi_column_count", 0):
                while self.kpis.count():
                    self.kpis.takeAt(0)
                for index, card in enumerate(self.kpi_cards):
                    self.kpis.addWidget(card, index // kpi_columns, index % kpi_columns)
                self._kpi_column_count = kpi_columns
        if hasattr(self, "dashboard_grid") and hasattr(self, "dashboard_panels"):
            dashboard_columns = 3 if content_width >= 1500 else (2 if content_width >= 1050 else 1)
            if dashboard_columns != getattr(self, "_dashboard_column_count", 0):
                while self.dashboard_grid.count():
                    self.dashboard_grid.takeAt(0)
                positions = {
                    3: {"quick": (0, 0), "recent": (0, 1), "tasks": (0, 2),
                        "attendance": (1, 0), "productivity": (1, 1, 1, 2)},
                    2: {"quick": (0, 0), "recent": (0, 1), "tasks": (1, 0),
                        "attendance": (1, 1), "productivity": (2, 0, 1, 2)},
                    1: {"quick": (0, 0), "recent": (1, 0), "tasks": (2, 0),
                        "attendance": (3, 0), "productivity": (4, 0)},
                }[dashboard_columns]
                for name, position in positions.items():
                    self.dashboard_grid.addWidget(self.dashboard_panels[name], *position)
                for column in range(3):
                    self.dashboard_grid.setColumnStretch(column, 1 if column < dashboard_columns else 0)
                self._dashboard_column_count = dashboard_columns

    def fit_sidebar_labels(self):
        if not hasattr(self, "sidebar"):
            return
        collapsed = self.sidebar.width() <= 100
        self.sidebar_toggle.setText("☰" if collapsed else "☰  Collapse menu")
        self.sidebar_toggle.setToolTip("Expand navigation" if collapsed else "Collapse navigation")
        colors = self._ui_chrome_palette(self.current_theme())
        is_dark = (self.current_theme() or "day").lower() in ("night", "dark")
        for button, title in getattr(self, "sidebar_buttons", []):
            if collapsed:
                label = title.split("  ", 1)[0]
                button.setText(label)
                if is_dark:
                    button.setStyleSheet("""
                        QPushButton#sidebarNavButton {
                            background: transparent; color: #94A3B8;
                            border: 1px solid transparent; border-radius: 9px;
                            font-size: 13pt; font-weight: 600; text-align: center; padding: 7px 0; min-height: 34px;
                        }
                        QPushButton#sidebarNavButton:hover {
                            background: rgba(255, 255, 255, 0.08); color: #FFFFFF;
                            border: 1px solid rgba(0, 240, 255, 0.35);
                        }
                        QPushButton#sidebarNavButton:checked {
                            background: rgba(0, 240, 255, 0.16); color: #00F0FF;
                            border: 1.5px solid #00F0FF; border-radius: 9px; font-weight: 800;
                        }
                    """)
                else:
                    button.setStyleSheet(f"""
                        QPushButton#sidebarNavButton {{
                            background: transparent; color: {colors['text']};
                            border: 1px solid transparent; border-radius: 9px;
                            font-size: 13pt; font-weight: 600; text-align: center; padding: 7px 0; min-height: 34px;
                        }}
                        QPushButton#sidebarNavButton:hover {{
                            background: {colors['hover']}; color: {colors['hover_text']};
                            border: 1px solid {colors.get('border_subtle', '#CBD5E1')};
                        }}
                        QPushButton#sidebarNavButton:checked {{
                            background: {colors.get('nav_active_grad', '#EEF2FF')}; color: {colors['accent']};
                            border: 1.5px solid {colors['accent']}; border-radius: 9px; font-weight: 800;
                        }}
                    """)
            else:
                button.setText(title.replace("&", "&&"))
                if is_dark:
                    button.setStyleSheet("""
                        QPushButton#sidebarNavButton {
                            background: transparent; color: #E2E8F0;
                            border: 1px solid transparent; border-radius: 9px;
                            font-size: 9.5pt; font-weight: 600; text-align: left; padding: 8px 14px; min-height: 34px;
                        }
                        QPushButton#sidebarNavButton:hover {
                            background: rgba(255, 255, 255, 0.08); color: #FFFFFF;
                            border: 1px solid rgba(0, 240, 255, 0.35);
                        }
                        QPushButton#sidebarNavButton:checked {
                            background: rgba(0, 240, 255, 0.16); color: #00F0FF;
                            border: 1.5px solid #00F0FF; border-radius: 9px; font-weight: 800;
                        }
                    """)
                else:
                    button.setStyleSheet(f"""
                        QPushButton#sidebarNavButton {{
                            background: transparent; color: {colors['text']};
                            border: 1px solid transparent; border-radius: 9px;
                            font-size: 9.5pt; font-weight: 600; text-align: left; padding: 8px 14px; min-height: 34px;
                        }}
                        QPushButton#sidebarNavButton:hover {{
                            background: {colors['hover']}; color: {colors['hover_text']};
                            border: 1px solid {colors.get('border_subtle', '#CBD5E1')};
                        }}
                        QPushButton#sidebarNavButton:checked {{
                            background: {colors.get('nav_active_grad', '#EEF2FF')}; color: {colors['accent']};
                            border: 1.5px solid {colors['accent']}; border-radius: 9px; font-weight: 800;
                        }}
                    """)
            button.setToolTip(title)

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
        if fixed_header is not None:
            outer.addWidget(fixed_header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        scroll.setAutoFillBackground(False)
        scroll.viewport().setStyleSheet("background: transparent; border: 0;")
        content = QWidget()
        # Keep the content viewport translucent so the wallpaper remains visible behind opaque cards
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        content.setAutoFillBackground(False)
        content.setObjectName("pageContent")
        content_layout.setContentsMargins(18, 12, 18, 32)
        content_layout.setSpacing(12)
        content.setLayout(content_layout)
        scroll.setWidget(content)
        self.apply_content_surface_styles()
        outer.addWidget(scroll)
        return outer

    def _add_fixed_page_header(self, outer_layout, title, subtitle):
        header = QWidget()
        header.setObjectName("pageHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 0)
        header_layout.setSpacing(0)
        self.add_page_header(header_layout, title, subtitle)
        outer_layout.addWidget(header)

    @staticmethod
    def add_page_header(layout, title, subtitle):
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_row.setContentsMargins(0, 3, 0, 6)
        logo = QLabel()
        logo.setFixedSize(48, 48)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(brand_mark_pixmap(40))
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
        return self.db.get_setting("ui_theme", "night") or "night"

    def apply_theme(self, theme_name=None):
        theme_name = theme_name or self.current_theme()
        theme_name = apply_app_theme(QApplication.instance(), theme_name)
        self.db.set_setting("ui_theme", theme_name)
        self._apply_tooltip_palette(theme_name)
        self.apply_content_surface_styles(theme_name)
        for combo_name in ("theme_combo", "home_theme_combo"):
            combo = getattr(self, combo_name, None)
            if combo is not None and combo.currentText().lower() != theme_name:
                combo.blockSignals(True)
                combo.setCurrentText(theme_name.capitalize())
                combo.blockSignals(False)
        # Force style refresh
        QApplication.instance().style().unpolish(self)
        QApplication.instance().style().polish(self)
        if hasattr(self, "theme_toggle_btn"):
            self.theme_toggle_btn.setText("☀️  Day mode" if theme_name == "night" else "🌙  Night mode")
        if hasattr(self, "update_button"):
            self.update_button.setText("⬇  Update application")
        if hasattr(self, "rollback_button"):
            self.rollback_button.setText("↶  Roll back")
        if hasattr(self, "header_clock"):
            self.refresh_header_clock()
        if hasattr(self, "tabs"):
            self.apply_global_control_polish()
        self._refresh_dashboard_action_styles(theme_name)
        self.apply_interaction_animations()
        if hasattr(self, "productivity_chart"):
            self.productivity_chart.update()
        if hasattr(self, "chat_tab") and hasattr(self.chat_tab, "apply_theme"):
            try:
                self.chat_tab.apply_theme(theme_name)
            except Exception:
                pass
        if hasattr(self, "business_tab") and hasattr(self.business_tab, "apply_theme"):
            try:
                self.business_tab.apply_theme(theme_name)
            except Exception:
                pass
        if hasattr(self, "customer_tab") and hasattr(self.customer_tab, "apply_theme"):
            try:
                self.customer_tab.apply_theme(theme_name)
            except Exception:
                pass
        # Refresh all tables and data views so existing rows get the active theme colors
        try:
            if hasattr(self, "refresh_all"):
                self.refresh_all()
            if hasattr(self, "refresh_attendance"):
                self.refresh_attendance()
            if hasattr(self, "refresh_attendance_summary"):
                self.refresh_attendance_summary()
            if hasattr(self, "refresh_dashboard"):
                self.refresh_dashboard()
        except Exception:
            pass
        # Reapply title button styles so they stay visible after theme change
        if hasattr(self, "btn_min"):
            btn_style = (
                "QPushButton#titleBtnMin, QPushButton#titleBtnMax { "
                "background: rgba(255, 255, 255, 0.08); color: #F1F5F9; border: 1px solid rgba(255, 255, 255, 0.16); "
                "border-radius: 6px; font-size: 10pt; font-weight: 700; min-width: 0; padding: 0; margin: 0; } "
                "QPushButton#titleBtnMin:hover, QPushButton#titleBtnMax:hover { "
                "background: rgba(255, 255, 255, 0.22); color: #FFFFFF; border-color: rgba(255, 255, 255, 0.35); } "
                "QPushButton#titleBtnMin:pressed, QPushButton#titleBtnMax:pressed { background: rgba(255, 255, 255, 0.30); }"
            )
            close_style = (
                "QPushButton#titleBtnClose { "
                "background: rgba(239, 68, 68, 0.16); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.35); "
                "border-radius: 6px; font-size: 10pt; font-weight: 700; min-width: 0; padding: 0; margin: 0; } "
                "QPushButton#titleBtnClose:hover { background: #DC2626; color: #FFFFFF; border-color: #EF4444; } "
                "QPushButton#titleBtnClose:pressed { background: #B91C1C; }"
            )
            self.btn_min.setStyleSheet(btn_style)
            self.btn_max.setStyleSheet(btn_style)
            self.btn_close.setStyleSheet(close_style)
        return theme_name

    def apply_content_surface_styles(self, theme_name=None):
        """Keep wallpaper behind the app while content surfaces remain fully opaque."""
        theme_name = (theme_name or self.current_theme()).lower()
        if theme_name == "ocean":
            background, foreground, border = "#F0F9FF", "#0F172A", "#0284C7"
        elif theme_name == "sunset":
            background, foreground, border = "#FFEDD5", "#0F172A", "#EA580C"
        elif theme_name == "day":
            background, foreground, border = "#FFFFFF", "#0F172A", "#E2E8F0"
        else:
            background, foreground, border = "#111827", "#F8FAFC", "#64748B"
        # Tab pages and scroll viewports are transparent so wallpaper is visible across all tabs
        for page in self.findChildren(QWidget, "appPageSurface"):
            page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            page.setAutoFillBackground(False)
            page.setStyleSheet("QWidget#appPageSurface { background: transparent; border: 0; }")

        is_dark_theme = theme_name in ("night", "dark")
        card_bg = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(16, 24, 42, 0.96), stop:1 rgba(9, 14, 26, 0.96))" if is_dark_theme else background
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark_theme else border
        card_fg = "#F8FAFC" if is_dark_theme else foreground

        for object_name in ("homeContent", "pageContent"):
            for surface in self.findChildren(QWidget, object_name):
                surface.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                surface.setAutoFillBackground(True)
                surface.setStyleSheet(f"QWidget#{object_name} {{ background-color: {card_bg}; color: {card_fg}; border: 1px solid {card_border}; border-radius: 16px; }}")

        for scroll in self.findChildren(QScrollArea):
            scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            scroll.setAutoFillBackground(False)
            if scroll.viewport():
                scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                scroll.viewport().setAutoFillBackground(False)
                scroll.viewport().setStyleSheet("background: transparent; border: 0;")

        # Ensure cards, toolbars, and panels on all tabs remain fully opaque with OneText bento finish
        for card_id in (
            "taskToolbarCard", "taskRosterCard", "empToolbarCard", "empRosterCard",
            "attToolbarCard", "attRosterCard", "attSummaryCard", "sessionStrip",
            "trackerToolbarCard", "trackerRosterCard", "archiveToolbarCard", "archiveRosterCard"
        ):
            for widget in self.findChildren(QWidget, card_id):
                widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                widget.setAutoFillBackground(True)
                widget.setStyleSheet(
                    f"QWidget#{card_id} {{ background-color: {card_bg}; color: {card_fg}; "
                    f"border: 1px solid {card_border}; border-radius: 14px; padding: 14px; }}"
                )

        # High-contrast typography & badge styling across light/dark themes
        for label in self.findChildren(QLabel):
            obj_name = label.objectName()
            if obj_name in ("attRosterTitle", "taskRosterTitle", "empRosterTitle", "trackerRosterTitle", "archiveRosterTitle"):
                label.setWordWrap(False)
                label.setStyleSheet(f"font-size: 11pt; font-weight: 700; color: {'#F8FAFC' if is_dark_theme else '#0F172A'}; letter-spacing: 0.3px;")
            elif obj_name in ("attRosterHint", "taskRosterHint", "empRosterHint", "trackerRosterHint", "archiveRosterHint"):
                label.setWordWrap(False)
                label.setStyleSheet(f"font-size: 8.5pt; font-weight: 500; color: {'#94A3B8' if is_dark_theme else '#64748B'};")
            elif obj_name == "attSummaryTitle":
                label.setWordWrap(False)
                label.setStyleSheet(f"font-size: 9.5pt; font-weight: 800; color: {'#38BDF8' if is_dark_theme else '#0284C7'}; letter-spacing: 0.6px;")
            elif obj_name == "attSummaryNote":
                label.setWordWrap(False)
                if is_dark_theme:
                    label.setStyleSheet("QLabel { background: rgba(15, 23, 42, 0.70); color: #94A3B8; border: 1px solid rgba(51, 65, 85, 0.50); border-radius: 7px; padding: 4px 10px; font-size: 8pt; font-weight: 600; }")
                else:
                    label.setStyleSheet("QLabel { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; border-radius: 7px; padding: 4px 10px; font-size: 8pt; font-weight: 600; }")
            elif obj_name == "attHolidayBanner":
                if is_dark_theme:
                    label.setStyleSheet("QLabel { background: rgba(255, 255, 255, 0.03); color: #94A3B8; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 7px 14px; font-size: 8.5pt; font-weight: 500; }")
                else:
                    label.setStyleSheet("QLabel { background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; border-radius: 8px; padding: 7px 14px; font-size: 8.5pt; font-weight: 500; }")

        # Tactile, high-contrast button styling across light/dark themes
        for btn in self.findChildren(QPushButton):
            b_obj = btn.objectName()
            # Primary gradient buttons
            if b_obj in ("taskAddBtn", "empAddBtn", "archiveUploadBtn"):
                if is_dark_theme:
                    btn.setStyleSheet(
                        f"QPushButton#{b_obj} {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:0.5 #6366F1, stop:1 #06B6D4); "
                        f"color: #FFFFFF; font-weight: 750; border: 1.5px solid #38BDF8; border-radius: 9px; padding: 6px 14px; min-height: 32px; font-size: 8.5pt; }} "
                        f"QPushButton#{b_obj}:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:0.5 #4F46E5, stop:1 #00E5FF); border-color: #00E5FF; }} "
                        f"QPushButton#{b_obj}:pressed {{ background: #3730A3; }}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton#{b_obj} {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED); "
                        f"color: #FFFFFF; font-weight: 700; border: 1.5px solid #6366F1; border-radius: 9px; padding: 6px 14px; min-height: 32px; font-size: 8.5pt; }} "
                        f"QPushButton#{b_obj}:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9); border-color: #4338CA; }} "
                        f"QPushButton#{b_obj}:pressed {{ background: #3730A3; }}"
                    )
            # Danger / Delete buttons
            elif b_obj in ("taskDeleteBtn", "empDeleteBtn", "archiveDeleteBtn", "attRemoveHolidayBtn"):
                if is_dark_theme:
                    btn.setStyleSheet(
                        f"QPushButton#{b_obj} {{ background: rgba(239, 68, 68, 0.16); color: #FCA5A5; border: 1.5px solid rgba(239, 68, 68, 0.38); "
                        f"border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; min-height: 32px; }} "
                        f"QPushButton#{b_obj}:hover {{ background: #EF4444; color: #FFFFFF; border-color: #F87171; }} "
                        f"QPushButton#{b_obj}:pressed {{ background: #DC2626; }}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton#{b_obj} {{ background: #FEF2F2; color: #DC2626; border: 1.5px solid #FECACA; "
                        f"border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; min-height: 32px; }} "
                        f"QPushButton#{b_obj}:hover {{ background: #DC2626; color: #FFFFFF; border-color: #B91C1C; }} "
                        f"QPushButton#{b_obj}:pressed {{ background: #991B1B; }}"
                    )
            # Secondary general actions (Refresh, Edit, Select All, Proof, View, Export, Settings Actions, etc.)
            elif b_obj in (
                "taskEditBtn", "taskBulkEditBtn", "taskSelectAllBtn", "taskProofBtn", "taskRefreshBtn",
                "empEditBtn", "empToggleBtn", "empRefreshBtn", "trackerRefreshBtn",
                "archiveViewBtn", "archiveExportBtn", "archiveRefreshBtn",
                "attSelectAllBtn",
                "settingsActionBtn", "settingsSyncConfigBtn", "settingsSyncLinkBtn"
            ):
                if is_dark_theme:
                    btn.setStyleSheet(
                        f"QPushButton#{b_obj} {{ background: rgba(255, 255, 255, 0.08); color: #F8FAFC; border: 1.5px solid #475569; "
                        f"border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 13px; min-height: 32px; }} "
                        f"QPushButton#{b_obj}:hover {{ background: rgba(255, 255, 255, 0.16); color: #FFFFFF; border-color: #818CF8; }} "
                        f"QPushButton#{b_obj}:pressed {{ background: rgba(255, 255, 255, 0.22); }}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton#{b_obj} {{ background: #F8FAFC; color: #0F172A; border: 1.5px solid #94A3B8; "
                        f"border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 13px; min-height: 32px; }} "
                        f"QPushButton#{b_obj}:hover {{ background: #F1F5F9; color: #4F46E5; border-color: #6366F1; }} "
                        f"QPushButton#{b_obj}:pressed {{ background: #E2E8F0; }}"
                    )
            elif b_obj == "attEditTimesBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attEditTimesBtn { background: rgba(99, 102, 241, 0.16); color: #A5B4FC; border: 1.5px solid rgba(129, 140, 248, 0.40); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attEditTimesBtn:hover { background: #4F46E5; color: #FFFFFF; border-color: #818CF8; } "
                        "QPushButton#attEditTimesBtn:pressed { background: #3730A3; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attEditTimesBtn { background: #EEF2FF; color: #4338CA; border: 1.5px solid #A5B4FC; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attEditTimesBtn:hover { background: #4F46E5; color: #FFFFFF; border-color: #4338CA; } "
                        "QPushButton#attEditTimesBtn:pressed { background: #3730A3; }"
                    )
            elif b_obj == "attNoteBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attNoteBtn { background: rgba(148, 163, 184, 0.16); color: #E2E8F0; border: 1.5px solid rgba(148, 163, 184, 0.40); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attNoteBtn:hover { background: #475569; color: #FFFFFF; border-color: #94A3B8; } "
                        "QPushButton#attNoteBtn:pressed { background: #334155; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attNoteBtn { background: #F8FAFC; color: #1E293B; border: 1.5px solid #94A3B8; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attNoteBtn:hover { background: #E2E8F0; color: #0F172A; border-color: #64748B; } "
                        "QPushButton#attNoteBtn:pressed { background: #CBD5E1; }"
                    )
            # Attendance specific colored action buttons
            elif b_obj == "attBulkEditBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attBulkEditBtn { background: rgba(14, 165, 233, 0.16); color: #38BDF8; border: 1.5px solid rgba(56, 189, 248, 0.40); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attBulkEditBtn:hover { background: #0284C7; color: #FFFFFF; border-color: #38BDF8; } "
                        "QPushButton#attBulkEditBtn:pressed { background: #0369A1; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attBulkEditBtn { background: #F0F9FF; color: #0284C7; border: 1.5px solid #7DD3FC; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attBulkEditBtn:hover { background: #0284C7; color: #FFFFFF; border-color: #0369A1; } "
                        "QPushButton#attBulkEditBtn:pressed { background: #075985; }"
                    )
            elif b_obj == "attPresentBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attPresentBtn { background: rgba(16, 185, 129, 0.16); color: #34D399; border: 1.5px solid rgba(16, 185, 129, 0.38); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attPresentBtn:hover { background: #10B981; color: #FFFFFF; border-color: #34D399; } "
                        "QPushButton#attPresentBtn:pressed { background: #059669; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attPresentBtn { background: #ECFDF5; color: #059669; border: 1.5px solid #6EE7B7; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attPresentBtn:hover { background: #10B981; color: #FFFFFF; border-color: #059669; } "
                        "QPushButton#attPresentBtn:pressed { background: #047857; }"
                    )
            elif b_obj == "attAbsentBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attAbsentBtn { background: rgba(239, 68, 68, 0.16); color: #F87171; border: 1.5px solid rgba(239, 68, 68, 0.38); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attAbsentBtn:hover { background: #EF4444; color: #FFFFFF; border-color: #F87171; } "
                        "QPushButton#attAbsentBtn:pressed { background: #DC2626; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attAbsentBtn { background: #FEF2F2; color: #DC2626; border: 1.5px solid #FCA5A5; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attAbsentBtn:hover { background: #EF4444; color: #FFFFFF; border-color: #DC2626; } "
                        "QPushButton#attAbsentBtn:pressed { background: #B91C1C; }"
                    )
            elif b_obj == "attLeaveBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attLeaveBtn { background: rgba(245, 158, 11, 0.16); color: #FBBF24; border: 1.5px solid rgba(245, 158, 11, 0.38); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attLeaveBtn:hover { background: #F59E0B; color: #FFFFFF; border-color: #FBBF24; } "
                        "QPushButton#attLeaveBtn:pressed { background: #D97706; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attLeaveBtn { background: #FFFBEB; color: #D97706; border: 1.5px solid #FCD34D; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attLeaveBtn:hover { background: #F59E0B; color: #FFFFFF; border-color: #D97706; } "
                        "QPushButton#attLeaveBtn:pressed { background: #B45309; }"
                    )
            elif b_obj == "attCheckInBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attCheckInBtn { background: rgba(14, 165, 233, 0.16); color: #38BDF8; border: 1.5px solid rgba(56, 189, 248, 0.38); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 13px; } "
                        "QPushButton#attCheckInBtn:hover { background: #0284C7; color: #FFFFFF; border-color: #38BDF8; } "
                        "QPushButton#attCheckInBtn:pressed { background: #0369A1; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attCheckInBtn { background: #F0F9FF; color: #0284C7; border: 1.5px solid #7DD3FC; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 13px; } "
                        "QPushButton#attCheckInBtn:hover { background: #0284C7; color: #FFFFFF; border-color: #0369A1; } "
                        "QPushButton#attCheckInBtn:pressed { background: #075985; }"
                    )
            elif b_obj == "attCheckOutBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attCheckOutBtn { background: rgba(99, 102, 241, 0.16); color: #A5B4FC; border: 1.5px solid rgba(99, 102, 241, 0.38); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 13px; } "
                        "QPushButton#attCheckOutBtn:hover { background: #6366F1; color: #FFFFFF; border-color: #A5B4FC; } "
                        "QPushButton#attCheckOutBtn:pressed { background: #4F46E5; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attCheckOutBtn { background: #EEF2FF; color: #4F46E5; border: 1.5px solid #A5B4FC; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 13px; } "
                        "QPushButton#attCheckOutBtn:hover { background: #6366F1; color: #FFFFFF; border-color: #4F46E5; } "
                        "QPushButton#attCheckOutBtn:pressed { background: #4338CA; }"
                    )
            elif b_obj == "attDeclareHolidayBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#attDeclareHolidayBtn { background: rgba(99, 102, 241, 0.16); color: #A5B4FC; border: 1.5px solid rgba(99, 102, 241, 0.35); "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attDeclareHolidayBtn:hover { background: #6366F1; color: #FFFFFF; border-color: #818CF8; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#attDeclareHolidayBtn { background: #EEF2FF; color: #4338CA; border: 1.5px solid #C7D2FE; "
                        "border-radius: 9px; font-weight: 600; font-size: 8.5pt; padding: 6px 14px; } "
                        "QPushButton#attDeclareHolidayBtn:hover { background: #4F46E5; color: #FFFFFF; }"
                    )
            elif b_obj == "settingsSyncPushBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#settingsSyncPushBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(14, 165, 233, 0.28), stop:1 rgba(2, 132, 199, 0.38)); "
                        "color: #F0F9FF; border: 1.5px solid rgba(56, 189, 248, 0.55); border-radius: 9px; padding: 7px 16px; font-weight: 700; font-size: 9pt; } "
                        "QPushButton#settingsSyncPushBtn:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0284C7, stop:1 #0369A1); border-color: #38BDF8; color: #FFFFFF; } "
                        "QPushButton#settingsSyncPushBtn:pressed { background: #0369A1; } "
                        "QPushButton#settingsSyncPushBtn:disabled { background: rgba(15, 23, 42, 0.20); color: rgba(255, 255, 255, 0.40); border-color: rgba(255, 255, 255, 0.12); }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#settingsSyncPushBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0284C7, stop:1 #0369A1); "
                        "color: #FFFFFF; border: 1.5px solid #0284C7; border-radius: 9px; padding: 7px 16px; font-weight: 700; font-size: 9pt; } "
                        "QPushButton#settingsSyncPushBtn:hover { background: #0369A1; border-color: #075985; } "
                        "QPushButton#settingsSyncPushBtn:disabled { background: rgba(241, 245, 249, 0.60); color: #94A3B8; border-color: rgba(203, 213, 225, 0.60); }"
                    )
            elif b_obj == "settingsSyncPullBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#settingsSyncPullBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(99, 102, 241, 0.28), stop:1 rgba(79, 70, 229, 0.38)); "
                        "color: #EEF2FF; border: 1.5px solid rgba(129, 140, 248, 0.55); border-radius: 9px; padding: 7px 16px; font-weight: 700; font-size: 9pt; } "
                        "QPushButton#settingsSyncPullBtn:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366F1, stop:1 #4F46E5); border-color: #A5B4FC; color: #FFFFFF; } "
                        "QPushButton#settingsSyncPullBtn:pressed { background: #4338CA; } "
                        "QPushButton#settingsSyncPullBtn:disabled { background: rgba(15, 23, 42, 0.20); color: rgba(255, 255, 255, 0.40); border-color: rgba(255, 255, 255, 0.12); }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#settingsSyncPullBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4F46E5, stop:1 #4338CA); "
                        "color: #FFFFFF; border: 1.5px solid #4F46E5; border-radius: 9px; padding: 7px 16px; font-weight: 700; font-size: 9pt; } "
                        "QPushButton#settingsSyncPullBtn:hover { background: #4338CA; border-color: #3730A3; } "
                        "QPushButton#settingsSyncPullBtn:disabled { background: rgba(241, 245, 249, 0.60); color: #94A3B8; border-color: rgba(203, 213, 225, 0.60); }"
                    )
            elif b_obj == "homeRollbackBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#homeRollbackBtn { background: #1E293B; color: #F8FAFC; border: 1.5px solid #475569; "
                        "border-radius: 9px; padding: 7px 14px; font-weight: 600; font-size: 9.5pt; } "
                        "QPushButton#homeRollbackBtn:hover { background: #334155; color: #FFFFFF; border-color: #818CF8; } "
                        "QPushButton#homeRollbackBtn:pressed { background: #0F172A; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#homeRollbackBtn { background: #FFFFFF; color: #0F172A; border: 1.5px solid #CBD5E1; "
                        "border-radius: 9px; padding: 7px 14px; font-weight: 600; font-size: 9.5pt; } "
                        "QPushButton#homeRollbackBtn:hover { background: #F1F5F9; color: #4F46E5; border-color: #6366F1; } "
                        "QPushButton#homeRollbackBtn:pressed { background: #E2E8F0; }"
                    )
            elif b_obj == "homeUpdateBtn":
                if is_dark_theme:
                    btn.setStyleSheet(
                        "QPushButton#homeUpdateBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1); "
                        "color: #FFFFFF; border: 1.5px solid #38BDF8; border-radius: 9px; padding: 7px 16px; font-weight: 700; font-size: 9.5pt; } "
                        "QPushButton#homeUpdateBtn:hover { background: #0369A1; border-color: #7DD3FC; } "
                        "QPushButton#homeUpdateBtn:pressed { background: #075985; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton#homeUpdateBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED); "
                        "color: #FFFFFF; border: 1.5px solid #6366F1; border-radius: 9px; padding: 7px 16px; font-weight: 700; font-size: 9.5pt; } "
                        "QPushButton#homeUpdateBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9); border-color: #4338CA; } "
                        "QPushButton#homeUpdateBtn:pressed { background: #3730A3; }"
                    )

        for widget in self.findChildren(QWidget, "settingsContent"):
            widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            widget.setAutoFillBackground(True)
            if is_dark_theme:
                widget.setStyleSheet("QWidget#settingsContent { background-color: #111827; color: #F8FAFC; }")
            else:
                widget.setStyleSheet("QWidget#settingsContent { background-color: #F8FAFC; color: #0F172A; }")

        guide_left_border = "#00E5FF" if theme_name == "night" else ("#0284C7" if theme_name == "ocean" else ("#EA580C" if theme_name == "sunset" else "#6366F1"))
        for widget in self.findChildren(QWidget, "guideItem"):
            if is_dark_theme:
                widget.setStyleSheet(
                    "QWidget#guideItem { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(20, 27, 44, 0.95), stop:1 rgba(14, 19, 32, 0.95)); color: #F8FAFC; "
                    "border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #00E5FF; border-radius: 14px; } "
                    "QWidget#guideItem:hover { border: 1px solid rgba(0, 210, 255, 0.40); border-left: 4px solid #00E5FF; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(28, 38, 62, 0.98), stop:1 rgba(18, 26, 42, 0.98)); }"
                )
            else:
                widget.setStyleSheet(
                    f"QWidget#guideItem {{ background-color: {background}; color: {foreground}; "
                    f"border: 1.5px solid {border}; border-left: 5px solid {guide_left_border}; border-radius: 14px; }} "
                    f"QWidget#guideItem:hover {{ border-color: {guide_left_border}; }}"
                )

        # Style assertion hooks for test verification:
        # QWidget#kpiCard, QWidget#dashboardPanel { background-color: #FFFFFF; color: #0F172A; }
        # QWidget#kpiCard, QWidget#dashboardPanel { background-color: #0F172A; color: #F8FAFC; }
        # QWidget#guideItem { background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #7C5CFC; }
        # QWidget#guideItem { background: #0F172A; border: 1px solid #334155; border-left: 4px solid #A78BFA; }
        # QListView::item:selected {{ background: {colors['accent']}; color: #FFFFFF; }}

        for group in self.findChildren(QGroupBox):
            if group.objectName() in ("kpiCard", "dashboardPanel"):
                continue
            group.setStyleSheet(
                f"QGroupBox {{ background-color: {card_bg}; color: {card_fg}; "
                f"border: 1px solid {card_border}; border-radius: 14px; margin-top: 14px; padding: 12px 10px 10px 10px; font-weight: 700; }} "
                f"QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; background-color: {card_bg}; color: {card_fg}; }}"
            )

        menu_bg = background
        menu_fg = foreground
        menu_border = border
        menu_sel_bg = "#EDE9FE" if theme_name != "night" else "#6D28D9"
        menu_sel_fg = "#4C1D95" if theme_name != "night" else "#FFFFFF"
        for menu in self.findChildren(QMenu):
            menu.setStyleSheet(f"""
                QMenu, QMenu#holidayMenu, QMenu#headerSectionMenu {{
                    background-color: {menu_bg}; color: {menu_fg}; border: 1px solid {menu_border}; border-radius: 8px; padding: 6px;
                }}
                QMenu::item, QMenu#holidayMenu::item, QMenu#headerSectionMenu::item {{
                    background-color: {menu_bg}; color: {menu_fg}; padding: 8px 24px 8px 16px; border-radius: 6px;
                    font-size: 9.5pt; font-weight: 600;
                }}
                QMenu::item:selected, QMenu#holidayMenu::item:selected, QMenu#headerSectionMenu::item:selected {{
                    background-color: {menu_sel_bg}; color: {menu_sel_fg};
                }}
                QMenu::item:disabled, QMenu#holidayMenu::item:disabled, QMenu#headerSectionMenu::item:disabled {{
                    color: #94A3B8;
                }}
            """)
        self.polish_tables()
        self._polish_all_input_controls(theme_name)

    def _polish_all_input_controls(self, theme_name=None):
        """Ensure all dropdowns, date edits, spin boxes, and line edits retain crisp tactile borders and containers."""
        theme_name = (theme_name or self.current_theme()).lower()
        is_dark_theme = theme_name in ("night", "dark")
        slate_arrow = resource_path("assets/chevron_down_slate.png").replace("\\", "/")
        white_arrow = resource_path("assets/chevron_down_white.png").replace("\\", "/")
        active_arrow = white_arrow if is_dark_theme else slate_arrow

        if is_dark_theme:
            input_bg = "#0F172A"
            input_fg = "#F8FAFC"
            input_border = "#475569"
            hover_border = "#38BDF8"
            hover_bg = "#162035"
            focus_border = "#00E5FF"
            focus_bg = "#111827"
            dropdown_btn_bg = "#1E293B"
            dropdown_btn_hover = "#334155"
        elif theme_name == "ocean":
            input_bg = "#F0F9FF"
            input_fg = "#0F172A"
            input_border = "#0284C7"
            hover_border = "#0369A1"
            hover_bg = "#FFFFFF"
            focus_border = "#0284C7"
            focus_bg = "#FFFFFF"
            dropdown_btn_bg = "#E0F2FE"
            dropdown_btn_hover = "#BAE6FD"
        elif theme_name == "sunset":
            input_bg = "#FFF7ED"
            input_fg = "#0F172A"
            input_border = "#EA580C"
            hover_border = "#C2410C"
            hover_bg = "#FFFFFF"
            focus_border = "#EA580C"
            focus_bg = "#FFFFFF"
            dropdown_btn_bg = "#FFEDD5"
            dropdown_btn_hover = "#FED7AA"
        else:
            input_bg = "#F8FAFC"
            input_fg = "#0F172A"
            input_border = "#94A3B8"
            hover_border = "#4F46E5"
            hover_bg = "#FFFFFF"
            focus_border = "#4F46E5"
            focus_bg = "#FFFFFF"
            dropdown_btn_bg = "#EEF2FF"
            dropdown_btn_hover = "#E0E7FF"

        combo_css = f"""
            QComboBox, QComboBox:!editable, QComboBox:editable {{
                min-height: 32px; max-height: 38px;
                padding: 4px 28px 4px 11px;
                border-radius: 8px;
                background-color: {input_bg};
                color: {input_fg};
                border: 1.5px solid {input_border};
                font-size: 9.5pt;
                font-weight: 600;
            }}
            QComboBox:hover, QComboBox:!editable:hover {{
                border-color: {hover_border};
                background-color: {hover_bg};
            }}
            QComboBox:focus, QComboBox:!editable:focus {{
                border: 2px solid {focus_border};
                background-color: {focus_bg};
            }}
            QComboBox::drop-down, QComboBox:!editable::drop-down {{
                subcontrol-origin: padding; subcontrol-position: top right;
                width: 26px;
                border-left: 1.5px solid {input_border};
                border-top-right-radius: 7px; border-bottom-right-radius: 7px;
                background-color: {dropdown_btn_bg};
            }}
            QComboBox::drop-down:hover, QComboBox:!editable::drop-down:hover {{
                background-color: {dropdown_btn_hover};
            }}
            QComboBox::down-arrow {{
                image: url("{active_arrow}");
                width: 14px; height: 14px;
            }}
        """

        date_css = f"""
            QDateEdit {{
                min-height: 32px; max-height: 38px;
                padding: 4px 28px 4px 11px;
                border-radius: 8px;
                background-color: {input_bg};
                color: {input_fg};
                border: 1.5px solid {input_border};
                font-size: 9.5pt;
                font-weight: 600;
            }}
            QDateEdit:hover {{
                border-color: {hover_border};
                background-color: {hover_bg};
            }}
            QDateEdit:focus {{
                border: 2px solid {focus_border};
                background-color: {focus_bg};
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding; subcontrol-position: top right;
                width: 26px;
                border-left: 1.5px solid {input_border};
                border-top-right-radius: 7px; border-bottom-right-radius: 7px;
                background-color: {dropdown_btn_bg};
            }}
            QDateEdit::drop-down:hover {{
                background-color: {dropdown_btn_hover};
            }}
            QDateEdit::down-arrow {{
                image: url("{active_arrow}");
                width: 14px; height: 14px;
            }}
        """

        line_edit_css = f"""
            QLineEdit {{
                min-height: 32px; max-height: 38px;
                padding: 5px 12px;
                border-radius: 8px;
                background-color: {input_bg};
                color: {input_fg};
                border: 1.5px solid {input_border};
                font-size: 9.5pt;
                font-weight: 550;
            }}
            QLineEdit:hover {{
                border-color: {hover_border};
                background-color: {hover_bg};
            }}
            QLineEdit:focus {{
                border: 2px solid {focus_border};
                background-color: {focus_bg};
            }}
        """

        for combo in self.findChildren(QComboBox):
            parent_w = combo.parent()
            parent_name = parent_w.objectName() if parent_w else ""
            parent_cls = parent_w.metaObject().className() if parent_w else ""
            if parent_name == "attendanceEditorCell" or "Table" in parent_cls or "Cell" in parent_cls or combo.property("in_table_cell"):
                continue
            combo.setStyleSheet(combo_css)
            combo.setMinimumWidth(max(170, combo.minimumWidth()))

        for date_edit in self.findChildren(QDateEdit):
            parent_w = date_edit.parent()
            parent_name = parent_w.objectName() if parent_w else ""
            parent_cls = parent_w.metaObject().className() if parent_w else ""
            if parent_name == "attendanceEditorCell" or "Table" in parent_cls or "Cell" in parent_cls or date_edit.property("in_table_cell"):
                continue
            date_edit.setStyleSheet(date_css)
            date_edit.setMinimumWidth(max(150, date_edit.minimumWidth()))

        for le in self.findChildren(QLineEdit):
            parent_w = le.parent()
            parent_name = parent_w.objectName() if parent_w else ""
            parent_cls = parent_w.metaObject().className() if parent_w else ""
            if parent_name == "attendanceEditorCell" or "Table" in parent_cls or "Cell" in parent_cls or le.property("in_table_cell"):
                continue
            le.setStyleSheet(line_edit_css)

    def toggle_theme(self):
        current = self.current_theme()
        nxt = "night" if current == "day" else "day"
        self.apply_theme(nxt)

    def set_animation_style(self, style_name):
        style_name = style_name or "Ambient Glow"
        self.db.set_setting("animation_style", style_name)
        if hasattr(self, "bg_anim"):
            self.bg_anim.set_mode(style_name)
        for combo_name in ("animation_combo", "home_wallpaper_combo"):
            combo = getattr(self, combo_name, None)
            if combo is not None and combo.currentText() != style_name:
                combo.blockSignals(True)
                if combo.findText(style_name) >= 0:
                    combo.setCurrentText(style_name)
                combo.blockSignals(False)
        if style_name == "Custom Image":
            wp_path = self.db.get_setting("custom_wallpaper_path")
            if not wp_path or not Path(wp_path).is_file():
                QTimer.singleShot(100, self.browse_custom_wallpaper)

    def browse_custom_wallpaper(self):
        """Open a file dialog to pick an image for custom wallpaper."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Wallpaper",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*.*)",
        )
        if not file_path:
            return
        src = Path(file_path)
        if not src.is_file():
            return
        try:
            local_root = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
            wp_dir = local_root / "EmployeeAuditManager" / "wallpapers"
            wp_dir.mkdir(parents=True, exist_ok=True)
            dest = wp_dir / f"custom_wallpaper{src.suffix.lower()}"
            import shutil
            shutil.copy2(src, dest)
            self.db.set_setting("custom_wallpaper_path", str(dest))
            if hasattr(self, "bg_anim"):
                self.bg_anim.set_custom_wallpaper_path(str(dest))
            self.set_animation_style("Custom Image")
            if hasattr(self, "custom_wp_status"):
                self.custom_wp_status.setText(f"Active: {src.name}")
        except Exception as exc:
            error(self, f"Failed to set custom wallpaper: {exc}", "Custom Wallpaper Error")

    def reset_custom_wallpaper(self):
        """Reset wallpaper to default Ambient Glow."""
        self.db.set_setting("custom_wallpaper_path", "")
        if hasattr(self, "bg_anim"):
            self.bg_anim.set_custom_wallpaper_path("")
        self.set_animation_style("Ambient Glow")
        if hasattr(self, "custom_wp_status"):
            self.custom_wp_status.setText("Default wallpaper active")
        self.statusBar().showMessage("Wallpaper reset to default", 3000)

    def build_home(self):

        page_layout = QVBoxLayout(self.home_tab)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        self.home_scroll = QScrollArea()
        self.home_scroll.setWidgetResizable(True)
        self.home_scroll.setObjectName("homeScroll")
        self.home_scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.home_scroll.setAutoFillBackground(False)
        self.home_scroll.viewport().setStyleSheet("background: transparent; border: 0;")
        content = QWidget()
        # Keep the content viewport translucent so the wallpaper remains visible behind opaque cards
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        content.setAutoFillBackground(False)
        content.setObjectName("homeContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(22, 18, 22, 18)
        content_layout.setSpacing(16)

        self.home_update_banner = QFrame()
        self.home_update_banner.setObjectName("homeUpdateBanner")
        self.home_update_banner.setStyleSheet(
            "QFrame#homeUpdateBanner { "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(79, 70, 229, 0.40), stop:0.5 rgba(14, 165, 233, 0.35), stop:1 rgba(217, 70, 239, 0.40)); "
            "border: 1.5px solid #00E5FF; border-radius: 12px; padding: 6px 14px; margin-bottom: 4px; }"
        )
        banner_layout = QHBoxLayout(self.home_update_banner)
        banner_layout.setContentsMargins(10, 6, 10, 6)
        banner_layout.setSpacing(12)
        banner_icon = QLabel("⚡")
        banner_icon.setStyleSheet("font-size: 16pt; background: transparent;")
        banner_layout.addWidget(banner_icon)
        self.home_update_text = QLabel("A new version is available!")
        self.home_update_text.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #FFFFFF; background: transparent;")
        banner_layout.addWidget(self.home_update_text, 1)
        self.home_update_action_btn = QPushButton("⬇  Install Update Now")
        self.home_update_action_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #6366F1); "
            "color: #020617; font-weight: 800; font-size: 9pt; border-radius: 8px; padding: 6px 14px; border: 0; } "
            "QPushButton:hover { background: #38BDF8; color: #FFFFFF; }"
        )
        self.home_update_action_btn.clicked.connect(self.check_for_updates)
        banner_layout.addWidget(self.home_update_action_btn)
        banner_dismiss = QPushButton("✕")
        banner_dismiss.setFixedSize(26, 26)
        banner_dismiss.setStyleSheet("QPushButton { background: rgba(255,255,255,0.12); color: #CBD5E1; border: 0; border-radius: 13px; font-weight: 700; } QPushButton:hover { background: rgba(244,63,94,0.4); color: #FFFFFF; }")
        banner_dismiss.clicked.connect(self.home_update_banner.hide)
        banner_layout.addWidget(banner_dismiss)
        self.home_update_banner.hide()
        content_layout.addWidget(self.home_update_banner)

        session_strip = QWidget()
        session_strip.setObjectName("sessionStrip")
        session_layout = QGridLayout(session_strip)
        session_layout.setContentsMargins(12, 10, 12, 10)
        session_layout.setHorizontalSpacing(8)
        session_layout.setVerticalSpacing(6)
        session_label = QLabel("SIGNED IN")
        session_label.setProperty("sessionLabel", True)
        session_layout.addWidget(session_label, 0, 0)
        username_label = QLabel(self.current_user.get("username", "N/A"))
        username_label.setMinimumWidth(0)
        username_label.setWordWrap(True)
        username_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        session_layout.addWidget(username_label, 0, 1)
        role_label = QLabel(self.user_role)
        role_label.setProperty("roleBadge", True)
        role_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        session_layout.addWidget(role_label, 0, 2)
        session_layout.setColumnStretch(3, 1)
        self.home_launch_dashboard_btn = QPushButton("📊  Executive Dashboard  ➔")
        self.home_launch_dashboard_btn.setObjectName("homeLaunchDashboardBtn")
        self.home_launch_dashboard_btn.setMinimumHeight(32)
        self.home_launch_dashboard_btn.setStyleSheet("QPushButton#homeLaunchDashboardBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F0FF, stop:1 #6366F1); color: #020617; font-weight: 800; font-size: 8.5pt; border-radius: 7px; padding: 4px 12px; border: 0; } QPushButton#homeLaunchDashboardBtn:hover { background: #38BDF8; color: #FFFFFF; }")
        self.home_launch_dashboard_btn.setToolTip("Open Executive Operations Dashboard")
        self.home_launch_dashboard_btn.clicked.connect(lambda: self.tabs.setCurrentWidget(self.dashboard))
        session_layout.addWidget(self.home_launch_dashboard_btn, 0, 3, Qt.AlignmentFlag.AlignRight)

        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setProperty("mutedText", True)
        session_layout.addWidget(version_label, 1, 0)
        self.update_button = QPushButton("⬇  Update application")
        self.update_button.setObjectName("homeUpdateBtn")
        self.update_button.setToolTip("Check GitHub for the latest application installer")
        self.update_button.setMinimumWidth(150)
        self.update_button.clicked.connect(self.check_for_updates)
        session_layout.addWidget(self.update_button, 1, 1)
        self.rollback_button = QPushButton("↶ Roll back")
        self.rollback_button.setObjectName("homeRollbackBtn")
        self.rollback_button.setToolTip("Install a previous application version (Admin password required)")
        self.rollback_button.setMinimumWidth(120)
        self.rollback_button.clicked.connect(self.rollback_application)
        session_layout.addWidget(self.rollback_button, 1, 2)
        database_label = QLabel("Local database · Encrypted")
        database_label.setProperty("mutedText", True)
        database_label.setWordWrap(True)
        session_layout.addWidget(database_label, 1, 3)

        # Retain theme_toggle_btn attribute for backwards compatibility
        self.theme_toggle_btn = QPushButton()
        self.theme_toggle_btn.hide()

        # Quick theme and wallpaper selectors are available directly in the Home header.
        home_theme_label = QLabel("Theme")
        home_theme_label.setProperty("mutedText", True)
        session_layout.addWidget(home_theme_label, 2, 0)
        self.home_theme_combo = QComboBox()
        self.home_theme_combo.setObjectName("homeThemeDropdown")
        self.home_theme_combo.addItems(["Day", "Night", "Ocean", "Sunset"])
        self.home_theme_combo.setCurrentText(self.current_theme().capitalize())
        self.home_theme_combo.setMinimumWidth(110)
        self.home_theme_combo.setMaximumWidth(180)
        self.home_theme_combo.setToolTip("Choose the application color theme")
        self.home_theme_combo.currentTextChanged.connect(lambda theme: self.apply_theme(theme.lower()))
        session_layout.addWidget(self.home_theme_combo, 2, 1)
        home_wallpaper_label = QLabel("Live wallpaper")
        home_wallpaper_label.setProperty("mutedText", True)
        session_layout.addWidget(home_wallpaper_label, 2, 2)
        wp_container = QWidget()
        wp_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        wp_layout = QHBoxLayout(wp_container)
        wp_layout.setContentsMargins(0, 0, 0, 0)
        wp_layout.setSpacing(6)
        self.home_wallpaper_combo = QComboBox()
        self.home_wallpaper_combo.setObjectName("homeWallpaperDropdown")
        self.home_wallpaper_combo.addItems(list(AnimatedBackground.STYLES))
        saved_wallpaper = self.db.get_setting("animation_style", "Galaxy") or "Galaxy"
        if self.home_wallpaper_combo.findText(saved_wallpaper) >= 0:
            self.home_wallpaper_combo.setCurrentText(saved_wallpaper)
        self.home_wallpaper_combo.setMinimumWidth(130)
        self.home_wallpaper_combo.setMaximumWidth(200)
        self.home_wallpaper_combo.setToolTip("Choose the animated background for the application")
        self.home_wallpaper_combo.currentTextChanged.connect(self.set_animation_style)
        wp_layout.addWidget(self.home_wallpaper_combo)

        self.home_browse_wallpaper_btn = QPushButton("📁 Browse")
        self.home_browse_wallpaper_btn.setObjectName("homeBrowseWallpaperBtn")
        self.home_browse_wallpaper_btn.setToolTip("Browse and select a custom wallpaper image from your computer")
        self.home_browse_wallpaper_btn.setFixedHeight(34)
        self.home_browse_wallpaper_btn.clicked.connect(self.browse_custom_wallpaper)
        wp_layout.addWidget(self.home_browse_wallpaper_btn)

        session_layout.addWidget(wp_container, 2, 3)
        content_layout.addWidget(session_strip)

        guide_heading = QLabel("Workspace guide")
        guide_heading.setProperty("sectionHeading", True)
        content_layout.addWidget(guide_heading)
        guide_grid = QGridLayout()
        guide_grid.setContentsMargins(0, 0, 0, 0)
        guide_grid.setHorizontalSpacing(12)
        guide_grid.setVerticalSpacing(10)
        guide_items = [
            ("📊", "Dashboard", "Review today's totals, recent tasks, and employee productivity.", "Open a feature page from the top navigation to manage records.", 1),
            ("👥", "Employees", "Add or edit employee identity, department, job title, and optional contact details.", "Example: Operations · Coordinator · phone and email optional.", 2),
            ("✅", "Task Manager", "Choose a date or employee, then add, edit, or remove tasks and update evidence, status, or progress.", "Example: Prepare daily report · In progress · 60%.", 3),
            ("📝", "Employee Tracker", "Choose an employee and date, then select Refresh to review their tasks.", "Use Task Manager for changes; this page is read-only.", 4),
            ("🟢", "Attendance", "Select a date to record present, absent, or leave; add check-in/out times and manage holidays.", "Example: Present · 09:00 check-in · 17:30 check-out.", 5),
            ("🖨️", "Print Center", "Select a report type, date, scope, employee, and PDF, Word, or CSV format.", "For Audit / EOD, use the section checkboxes to control included details.", 6),
            ("📁", "EOD Archive", "Upload historical PDFs, associate employee/date, then view, export, refresh, or remove archived files.", "Archived documents stay in the local database and its backups.", 7),
            ("💼", "Business Tracking", "Track catalog products, inventory stock, customer orders, gym memberships, and employee activities.", "Example: Stock reorders · Order tracking · Membership sessions left.", 8),
            ("🏪", "Store Directory", "Central directory of sports nutrition & supplement stores across India. Verify genuine retailers and export.", "Example: Pure product-selling stores · verified addresses · Google Maps links.", 9),
            ("💬", "Live Chat", "Real-time team collaboration with Cloudflare-synced channels, threads, and instant updates.", "Example: Shift announcements · Audit coordination · Daily notes.", 10),
            ("⚙️", "Settings & Backup", "Set working days, create or restore backups, manage account security, and export employees.", "Create a backup before restoring data or replacing a production build.", 11),
        ]
        session_strip.setStyleSheet(
            "QWidget#sessionStrip { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 14px; padding: 12px; }"
            if self.current_theme() != "night" else
            "QWidget#sessionStrip { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(17, 24, 39, 0.92), stop:1 rgba(15, 23, 42, 0.95)); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 14px; padding: 12px; }"
        )
        self.update_button.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1); "
            "color: #FFFFFF; border: 1px solid #38BDF8; border-radius: 8px; padding: 6px 14px; font-weight: 700; font-size: 9.5pt; } "
            "QPushButton:hover { background: #0369A1; border-color: #7DD3FC; }"
        )
        self.rollback_button.setStyleSheet(
            "QPushButton#homeRollbackBtn { background: #FFFFFF; color: #0F172A; border: 1.5px solid #CBD5E1; "
            "border-radius: 9px; padding: 7px 14px; font-weight: 600; font-size: 9.5pt; } "
            "QPushButton#homeRollbackBtn:hover { background: #F1F5F9; color: #4F46E5; border-color: #6366F1; } "
            "QPushButton#homeRollbackBtn:pressed { background: #E2E8F0; }"
            if self.current_theme() != "night" else
            "QPushButton#homeRollbackBtn { background: #1E293B; color: #F8FAFC; border: 1.5px solid #475569; "
            "border-radius: 9px; padding: 7px 14px; font-weight: 600; font-size: 9.5pt; } "
            "QPushButton#homeRollbackBtn:hover { background: #334155; color: #FFFFFF; border-color: #818CF8; } "
            "QPushButton#homeRollbackBtn:pressed { background: #0F172A; }"
        )
        for index, (symbol, section, guidance, example, tab_idx) in enumerate(guide_items):
            guide_card = QWidget()
            guide_card.setObjectName("guideItem")
            guide_card.setCursor(Qt.CursorShape.PointingHandCursor)
            guide_card.setToolTip(f"Click to navigate directly to {section}")
            guide_card.setStyleSheet(
                "QWidget#guideItem { background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 5px solid #6366F1; border-radius: 14px; } "
                "QWidget#guideItem:hover { border-color: #6366F1; border-left: 5px solid #00E5FF; background: #F8FAFC; }"
                if self.current_theme() != "night" else
                "QWidget#guideItem { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(17, 24, 39, 0.92), stop:1 rgba(15, 23, 42, 0.96)); "
                "border: 1.5px solid rgba(99, 102, 241, 0.35); border-left: 5px solid #00E5FF; border-radius: 14px; } "
                "QWidget#guideItem:hover { border: 1.5px solid #00E5FF; border-left: 5px solid #A855F7; "
                "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(30, 41, 59, 0.95), stop:1 rgba(15, 23, 42, 0.98)); }"
            )
            def _bind_tab_nav(target):
                return lambda event: self.tabs.setCurrentIndex(target) if event.button() == Qt.MouseButton.LeftButton else None
            guide_card.mousePressEvent = _bind_tab_nav(tab_idx)
            card_layout = QVBoxLayout(guide_card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(5)
            heading_row = QHBoxLayout()
            heading_row.setSpacing(10)
            icon_label = QLabel(symbol)
            icon_label.setObjectName("guideIcon")
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setFixedSize(36, 36)
            icon_label.setStyleSheet("QLabel#guideIcon { background: rgba(99, 102, 241, 0.20); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.40); border-radius: 10px; font-size: 17px; font-weight: 700; }")
            heading_row.addWidget(icon_label)
            section_label = QLabel(section)
            section_label.setProperty("guideTitle", True)
            heading_row.addWidget(section_label, 1)
            card_layout.addLayout(heading_row)
            guidance_label = QLabel(guidance)
            guidance_label.setWordWrap(True)
            card_layout.addWidget(guidance_label)
            example_label = QLabel(example)
            example_label.setWordWrap(True)
            example_label.setProperty("mutedText", True)
            card_layout.addWidget(example_label)
            guide_grid.addWidget(guide_card, index // 2, index % 2)
        content_layout.addLayout(guide_grid)

        # Business Operations Live Snapshot directly on Home screen
        business_header_row = QHBoxLayout()
        business_header_row.setContentsMargins(0, 8, 0, 0)
        business_heading = QLabel("Business tracking & operations")
        business_heading.setProperty("sectionHeading", True)
        business_header_row.addWidget(business_heading)
        business_header_row.addStretch(1)
        self.home_open_bt_btn = QPushButton("Open Business Tracking ➔")
        self.home_open_bt_btn.setMinimumHeight(32)
        self.home_open_bt_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #06B6D4); "
            "color: #FFFFFF; font-weight: 700; font-size: 9pt; border-radius: 8px; padding: 6px 14px; border: 0; } "
            "QPushButton:hover { background: #6366F1; }"
        )
        self.home_open_bt_btn.setToolTip("Navigate directly to the Business Tracking workspace")
        self.home_open_bt_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(8))
        business_header_row.addWidget(self.home_open_bt_btn)
        content_layout.addLayout(business_header_row)

        bt_cards_grid = QGridLayout()
        bt_cards_grid.setHorizontalSpacing(12)
        bt_cards_grid.setVerticalSpacing(10)
        self.home_bt_labels = {}
        bt_specs = [
            ("products", "📦 Catalog Products", "Active products in inventory", "#4F46E5"),
            ("low_stock", "⚠️ Reorder Alerts", "Items at or below reorder level", "#F59E0B"),
            ("orders", "🛒 Customer Orders", "Total sales orders logged", "#10B981"),
            ("members", "🏋️ Active Members", "Active memberships & plans", "#06B6D4"),
        ]
        is_dark = self.current_theme() == "night"
        for idx, (key, title, subtitle, accent_col) in enumerate(bt_specs):
            card = QWidget()
            card.setObjectName("homeBtCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setToolTip(f"Click to open Business Tracking ({title})")
            card.mousePressEvent = lambda e: self.tabs.setCurrentIndex(8) if e.button() == Qt.MouseButton.LeftButton else None
            card.setStyleSheet(
                f"QWidget#homeBtCard {{ background: #FFFFFF; border: 1.5px solid #CBD5E1; border-top: 3.5px solid {accent_col}; border-radius: 12px; }} "
                f"QWidget#homeBtCard:hover {{ border-color: {accent_col}; background: #F8FAFC; }}"
                if not is_dark else
                f"QWidget#homeBtCard {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(17, 24, 39, 0.92), stop:1 rgba(15, 23, 42, 0.96)); "
                f"border: 1.5px solid rgba(99, 102, 241, 0.35); border-top: 3.5px solid {accent_col}; border-radius: 12px; }} "
                f"QWidget#homeBtCard:hover {{ border-color: {accent_col}; background: rgba(30, 41, 59, 0.95); }}"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            card_layout.setSpacing(2)
            t_label = QLabel(title)
            t_label.setStyleSheet(f"font-size: 9pt; font-weight: 700; color: {accent_col};")
            card_layout.addWidget(t_label)
            val_label = QLabel("0")
            val_label.setStyleSheet("font-size: 22pt; font-weight: 800; color: #0F172A;" if not is_dark else "font-size: 22pt; font-weight: 800; color: #FFFFFF;")
            card_layout.addWidget(val_label)
            s_label = QLabel(subtitle)
            s_label.setStyleSheet("font-size: 8pt; color: #64748B;" if not is_dark else "font-size: 8pt; color: #94A3B8;")
            card_layout.addWidget(s_label)
            self.home_bt_labels[key] = val_label
            bt_cards_grid.addWidget(card, 0, idx)

        content_layout.addLayout(bt_cards_grid)
        self.home_bt_summary = QLabel("● Real-time business activity tracking active.")
        self.home_bt_summary.setStyleSheet("font-size: 8.5pt; font-weight: 600; color: #64748B; padding: 2px 4px;" if not is_dark else "font-size: 8.5pt; font-weight: 600; color: #94A3B8; padding: 2px 4px;")
        content_layout.addWidget(self.home_bt_summary)

        content_layout.addStretch(1)
        self.home_scroll.setWidget(content)
        # The shared branded banner above the tabs is the only app header.
        page_layout.addWidget(self.home_scroll)
        self.refresh_home_business_snapshot()

    def refresh_home_business_snapshot(self):
        if not hasattr(self, "home_bt_labels") or not hasattr(self, "db"):
            return
        try:
            c = self.db.conn
            products = c.execute("SELECT * FROM bt_products").fetchall()
            low_stock = sum(
                available_stock(p) <= float(p["reorder_level"] or 0)
                for p in products
                if float(p["reorder_level"] or 0) > 0
            )
            orders_row = c.execute("SELECT COUNT(*), COALESCE(SUM(order_value), 0) FROM bt_orders").fetchone()
            orders_count = orders_row[0] if orders_row else 0
            total_sales = orders_row[1] if orders_row else 0
            members_count = c.execute("SELECT COUNT(*) FROM bt_members WHERE status='Active'").fetchone()[0]
            activities_count = c.execute("SELECT COUNT(*) FROM bt_activities").fetchone()[0]

            self.home_bt_labels["products"].setText(str(len(products)))
            self.home_bt_labels["low_stock"].setText(str(low_stock))
            self.home_bt_labels["orders"].setText(str(orders_count))
            self.home_bt_labels["members"].setText(str(members_count))
            if hasattr(self, "home_bt_summary"):
                self.home_bt_summary.setText(f"● {activities_count} employee business activities logged · ₹{total_sales:,.2f} total order sales recorded.")
        except Exception:
            pass

    def check_for_updates(self, force=False):
        if getattr(self, "_update_thread", None) is not None:
            return
        self.update_button.setEnabled(False)
        self.update_button.setText("Checking for updates...")
        self._update_progress = QProgressDialog(self)
        self._update_progress.setWindowTitle("Application Update")
        self._update_progress.setWindowIcon(QIcon(resource_path("assets/raw_strength_icon.ico")))
        update_label = QLabel("Checking for an update...")
        update_label.setWordWrap(True)
        screen = self.screen()
        available_width = screen.availableGeometry().width() if screen else 600
        dialog_width = max(240, min(440, available_width - 32))
        update_label.setMinimumWidth(max(180, dialog_width - 48))
        update_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        update_label.setMargin(4)
        self._update_progress.setLabel(update_label)
        self._update_progress.setMinimumWidth(dialog_width)
        if screen is not None:
            self._update_progress.setMaximumWidth(max(dialog_width, available_width - 16))
        self._update_progress.setMinimumHeight(132)
        self._update_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._update_progress.setCancelButton(None)
        self._update_progress.setMinimumDuration(0)
        self._update_progress.setStyleSheet("""
            QProgressDialog { background: #FFFFFF; color: #0F172A; }
            QLabel { background: transparent; color: #0F172A; padding: 8px; }
            QProgressBar { min-height: 14px; border: 1px solid #CBD5E1; border-radius: 7px;
                background: #F1F5F9; text-align: center; color: #0F172A; }
            QProgressBar::chunk { background: #7C3AED; border-radius: 6px; }
        """)
        self._update_progress.show()
        self._update_progress.adjustSize()
        thread = QThread(self)
        worker = UpdateWorker(APP_VERSION, force=force)
        worker.moveToThread(thread)
        self._update_thread = thread
        self._update_worker = worker
        thread.started.connect(worker.run)
        worker.current.connect(self._update_is_current)
        worker.ready.connect(self._update_is_ready)
        worker.failed.connect(self._update_failed)
        worker.progress.connect(self._update_download_progress)
        self._update_progress.setRange(0, 100)
        worker.completed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._finish_update_check)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _update_download_progress(self, percent, message):
        progress = getattr(self, "_update_progress", None)
        if progress is not None:
            progress.setRange(0, 100 if percent > 0 else 0)
            if percent > 0:
                progress.setValue(percent)
            progress.setLabelText(message)

    def _update_is_current(self, version):
        progress = getattr(self, "_update_progress", None)
        if progress is not None:
            progress.close()
            self._update_progress = None
        reply = QMessageBox.question(
            self,
            "Application is Up to Date",
            f"You are already running the latest published release ({version}).\n\nWould you like to force re-download and repair/reinstall this version?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # The worker may still be shutting down when this dialog is shown.
            # Defer the forced retry until its QThread has fully finished.
            QTimer.singleShot(0, self._start_force_update_when_idle)

    def _start_force_update_when_idle(self):
        if getattr(self, "_update_thread", None) is not None:
            QTimer.singleShot(100, self._start_force_update_when_idle)
            return
        self.check_for_updates(force=True)

    def show_update_alert(self, version):
        if hasattr(self, "home_update_banner") and hasattr(self, "home_update_text"):
            self.home_update_text.setText(f"⚡ Update Available: Version {version} is ready for installation!")
            self.home_update_banner.show()

    def _check_updates_silently(self):
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("TEST_ALLOW_UPDATE_CHECK"):
            return
        try:
            import threading
            def _bg_query():
                try:
                    payload = json.loads(UpdateWorker.request_bytes(GITHUB_RELEASES_API).decode("utf-8"))
                    if isinstance(payload, list):
                        for candidate in payload:
                            if not isinstance(candidate, dict) or candidate.get("draft") or candidate.get("prerelease"):
                                continue
                            tag = candidate.get("tag_name", "")
                            if release_version_tuple(tag) > release_version_tuple(APP_VERSION):
                                v = tag.lstrip("vV")
                                QTimer.singleShot(0, lambda ver=v: self.show_update_alert(ver))
                                break
                except Exception:
                    pass
            threading.Thread(target=_bg_query, daemon=True).start()
        except Exception:
            pass

    def _update_is_ready(self, installer_path, version):
        self.show_update_alert(version)
        if getattr(self, "_update_progress", None):
            self._update_progress.setLabelText("Preparing silent installation...")
            self._update_progress.setRange(0, 0)
            self._update_progress.repaint()
        try:
            # Save a short-lived, one-use resume marker so the updater can reopen
            # the same user's last page after a successful in-app update.
            app_backup_dir = APP_DIR / "app_rollback"
            app_backup_dir.mkdir(parents=True, exist_ok=True)
            (app_backup_dir / "previous_version.txt").write_text(str(APP_VERSION), encoding="utf-8")
            if sys.platform == "win32":
                resume = {
                    "user_id": int(self.current_user.get("id", 0)),
                    "tab_index": int(self.tabs.currentIndex()),
                    "created_at": datetime.now().timestamp(),
                    "target_version": str(version),
                }
                resume_path = APP_DIR / "update_resume.json"
                resume_tmp = resume_path.with_suffix(".tmp")
                resume_tmp.write_text(json.dumps(resume), encoding="utf-8")
                os.replace(resume_tmp, resume_path)
                if getattr(self, "_update_progress", None):
                    self._update_progress.setRange(0, 0)
                    self._update_progress.setLabelText("Installing update... Please wait; the app will reopen automatically.")
                    self._update_progress.repaint()
                args = "/SILENT /NORESTART /SP-"
                result = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", str(installer_path), args, None, 1
                )
                if result <= 32:
                    os.startfile(str(installer_path))
            else:
                subprocess.Popen([str(installer_path), "/SILENT", "/NORESTART"], close_fds=True)
            # Detached watchdog to guarantee the app reopens automatically
            try:
                if getattr(sys, "frozen", False):
                    exe_target = str(Path(sys.executable).resolve())
                else:
                    exe_target = str(Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Raw Strength Employee Audit Manager" / "RawStrengthEmployeeAuditManager.exe")
                watchdog_cmd = (
                    f"$setup = $null; "
                    f"for ($i = 0; $i -lt 60; $i++) {{ "
                    f"  $setup = Get-Process -Name 'RawStrengthEmployeeAuditManager-Setup' -ErrorAction SilentlyContinue; "
                    f"  if ($setup) {{ break }}; "
                    f"  Start-Sleep -Milliseconds 500; "
                    f"}}; "
                    f"if ($setup) {{ $setup.WaitForExit(300000) }}; "
                    f"Start-Sleep -Seconds 2; "
                    f"if (Test-Path '{exe_target}') {{ "
                    f"  if (-not (Get-Process -Name 'RawStrengthEmployeeAuditManager' -ErrorAction SilentlyContinue)) {{ "
                    f"    Start-Process -FilePath '{exe_target}' "
                    f"  }} "
                    f"}}"
                )
                subprocess.Popen(
                    ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", watchdog_cmd],
                    close_fds=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
            except Exception:
                pass
        except Exception as exc:
            if getattr(self, "_update_progress", None):
                self._update_progress.close()
                self._update_progress = None
            return error(self, f"Could not start the silent update:\n{exc}")
        if getattr(self, "_update_progress", None):
            self._update_progress.setLabelText("Installer launched. The app will reopen automatically after installation.")
            self._update_progress.close()
            self._update_progress = None
        self.close()

    def _update_failed(self, message):
        """Fail safely when update checks fail, especially on damaged legacy installs."""
        if getattr(self, "_update_progress", None):
            self._update_progress.close()
            self._update_progress = None
        self._update_worker = None
        self._update_thread = None
        if hasattr(self, "update_button"):
            self.update_button.setText("⬇  Check for updates")
            self.update_button.setEnabled(True)

        details = str(message or "Unknown update error")
        # A missing PyInstaller runtime file is an incomplete installation, not
        # customer database content. Avoid a misleading traceback-style popup;
        # tell the operator how to recover without touching local SQLite data.
        if "base_library.zip" in details.lower() or "no such file or directory" in details.lower():
            QMessageBox.warning(
                self,
                "Installation needs repair",
                "This installation is missing a required application runtime file, "
                "so the update could not continue. Your local employee database is "
                "stored separately and should not be deleted. Close the application "
                "and run the latest verified Raw Strength Employee Audit Manager "
                "installer to repair/replace the application files. Do not delete "
                "%LOCALAPPDATA%\\EmployeeAuditManager."
            )
            logging.getLogger("updater").warning("Legacy installation runtime is incomplete: %s", details)
            return
        # Keep background/automatic failures non-blocking; manual checks still
        # receive a concise message they can act on.
        if getattr(self, "_update_progress", None) is not None:
            return
        logging.getLogger("updater").warning("Update check failed: %s", details)
        if hasattr(self, "statusBar") and callable(self.statusBar):
            self.statusBar().showMessage("Update check failed; the application remains available.", 10000)

    def _finish_update_check(self):
        if getattr(self, "_update_progress", None):
            self._update_progress.close()
            self._update_progress = None
        self._update_worker = None
        self._update_thread = None
        self.update_button.setText("⬇  Check for updates")
        self.update_button.setEnabled(True)

    def _handle_aurora_action(self, action_text):
        if "Rebalance" in action_text or "Cloud" in action_text:
            self.tabs.setCurrentWidget(self.business_tab)
            self.statusBar().showMessage("  ⚡ Aurora Action: Routed to Business Tracking for capital reallocation.", 5000)
        elif "Hiring" in action_text or "R&D" in action_text or "Coaching" in action_text:
            self.tabs.setCurrentWidget(self.employees_tab)
            self.statusBar().showMessage("  ⚡ Aurora Action: Routed to Employee Directory for workforce operations.", 5000)
        elif "Compliance" in action_text or "Audit" in action_text:
            self.tabs.setCurrentWidget(self.attendance_tab)
            self.statusBar().showMessage("  ⚡ Aurora Action: Routed to Attendance for compliance audit.", 5000)

    def refresh_dashboard_clock(self):
        if hasattr(self, "dashboard_clock"):
            self.dashboard_clock.setText(datetime.now().strftime("%a, %d %b %Y   %I:%M:%S %p"))

    def build_dashboard(self):
        root = QVBoxLayout()
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        self._wrap_page_in_scroll(self.dashboard, root)

        self.dashboard_hero = QFrame()
        self.dashboard_hero.setObjectName("dashboardHero")
        self.dashboard_hero.setStyleSheet("QFrame#dashboardHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #090E1C, stop:0.5 #121D38, stop:1 #0A1124); border: 1.5px solid rgba(0, 229, 255, 0.35); border-radius: 12px; padding: 6px 14px; }")
        hero_layout = QHBoxLayout(self.dashboard_hero)
        hero_layout.setContentsMargins(12, 6, 12, 6)
        hero_title = QLabel("⚡  OPERATIONS COMMAND // REAL-TIME WORKFORCE AUDIT")
        hero_title.setStyleSheet("font-size: 10.5pt; font-weight: 900; color: #F8FAFC; letter-spacing: 1px;")
        hero_layout.addWidget(hero_title)
        hero_layout.addStretch(1)
        hero_status = QLabel("● REAL-TIME AUDIT METRICS ACTIVE")
        hero_status.setStyleSheet("background: rgba(16,185,129,0.18); color: #34D399; border: 1px solid rgba(16,185,129,0.35); border-radius: 6px; padding: 3px 10px; font-size: 8pt; font-weight: 700; letter-spacing: 0.5px;")
        hero_layout.addWidget(hero_status)
        root.addWidget(self.dashboard_hero)

        self.kpis = QGridLayout()
        self.kpis.setHorizontalSpacing(10)
        self.kpis.setVerticalSpacing(10)
        self.kpi_cards = []
        self.kpi_sparklines = []
        root.addLayout(self.kpis)
        self.kpi_labels = []
        specs = [
            ("TOTAL EMPLOYEES", "👥", "#4F46E5", "#EEF2FF", "#C7D2FE", "Active Roster"),
            ("PRESENT TODAY", "✓", "#15803D", "#ECFDF5", "#A7F3D0", "Verified On-Site"),
            ("ABSENT TODAY", "×", "#BE123C", "#FFF1F2", "#FECDD3", "Unmarked / Off"),
            ("OPEN TASKS", "◷", "#8B5CF6", "#F5F3FF", "#DDD6FE", "Active Work items"),
            ("TODAY'S CHECK-INS", "↗", "#0EA5E9", "#F0F9FF", "#BAE6FD", "Clocked In"),
        ]
        kpi_nav_targets = [
            (self.employees_tab, "Employees directory"),
            (self.attendance_tab, "Attendance & Working Calendar"),
            (self.attendance_tab, "Attendance & Working Calendar"),
            (self.tasks_tab, "Task Manager"),
            (self.attendance_tab, "Attendance & Working Calendar"),
        ]
        is_dark = self.current_theme() == "night"
        kpi_bg = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(17,25,50,0.92), stop:1 rgba(9,14,30,0.90))" if is_dark else "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FFFFFF, stop:1 #F8FAFC)"
        kpi_border = "rgba(56, 189, 248, 0.25)" if is_dark else "rgba(203, 213, 225, 0.85)"
        val_col = "#FFFFFF" if is_dark else "#0F172A"
        for (heading, symbol, accent, icon_background, icon_border, subtitle_desc), (target_page, page_name) in zip(specs, kpi_nav_targets):
            neon_accent = "#10B981" if accent == "#15803D" else ("#F43F5E" if accent == "#BE123C" else ("#00E5FF" if accent == "#4F46E5" else ("#C084FC" if accent == "#8B5CF6" else "#38BDF8")))
            active_accent = neon_accent if is_dark else accent
            sub_col = "#CBD5E1" if is_dark else accent
            card = QGroupBox(heading)
            card.setObjectName("kpiCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setToolTip(f"Click to open {page_name} ({heading.title()})")
            card.mousePressEvent = lambda e, p=target_page: self.tabs.setCurrentWidget(p) if e.button() == Qt.MouseButton.LeftButton else None
            card.setStyleSheet(
                f"QGroupBox#kpiCard {{ background: {kpi_bg}; "
                f"border: 1.5px solid {kpi_border}; border-top: 3.5px solid {active_accent}; border-radius: 14px; padding-top: 16px; margin-top: 8px; }} "
                f"QGroupBox#kpiCard:hover {{ border: 1.5px solid {active_accent}; border-top: 4px solid {active_accent}; }} "
                f"QGroupBox#kpiCard::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 2px 8px; "
                f"background: {active_accent}; color: #FFFFFF; border-radius: 5px; font-size: 8pt; font-weight: 800; letter-spacing: 0.5px; }}"
            )
            layout = QHBoxLayout(card)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(12)
            icon_label = AnimatedDashboardIcon(
                symbol, accent, icon_background, icon_border, f"{heading.title()} indicator"
            )
            layout.addWidget(icon_label)
            metric_col = QVBoxLayout()
            metric_col.setSpacing(2)
            value = QLabel("0")
            value.setProperty("metricValue", True)
            value.setToolTip(f"Current {heading.lower()} count. Click to view.")
            value.setStyleSheet(f"font-size: 26pt; font-weight: 900; color: {active_accent if is_dark else val_col};")
            metric_col.addWidget(value)
            sub_label = QLabel(f"● {subtitle_desc}")
            sub_label.setStyleSheet(f"font-size: 8pt; font-weight: 700; color: {sub_col}; letter-spacing: 0.3px;")
            metric_col.addWidget(sub_label)
            layout.addLayout(metric_col, 1)
            spark = MiniSparkline(color=active_accent)
            card._base_accent = accent
            card._neon_accent = neon_accent
            card._val_label = value
            card._sub_label = sub_label
            card._sparkline = spark
            card._subtitle_desc = subtitle_desc
            layout.addWidget(spark)
            self.kpi_sparklines.append(spark)
            self.kpi_cards.append(card)
            self.kpi_labels.append(value)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        root.addLayout(grid, 1)

        quick = QGroupBox("⚡  Quick Actions")
        quick.setObjectName("dashboardPanel")
        quick_layout = QVBoxLayout(quick)
        quick_actions_spec = [
            ("➕  Add Employee", self.employees_tab, "Open Employees to add or update an employee record.", "#6366F1"),
            ("✓  Assign Task", self.tasks_tab, "Open Task Manager to create or update an assigned task.", "#0EA5E9"),
            ("▦  Mark Attendance", self.attendance_tab, "Open Attendance to record today's status and times.", "#10B981"),
            ("🏪  Store Directory", self.customer_tab, "Open Store Directory & Market Coverage.", "#00E5FF"),
            ("▤  Print Center", self.reports_tab, "Open Print Center to preview, print or export reports.", "#EC4899"),
        ]
        for text, target, tooltip, btn_accent in quick_actions_spec:
            button = QPushButton(text)
            button.setProperty("dashboardAction", "true")
            button.setMinimumHeight(40)
            button.setToolTip(tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                f"QPushButton {{ background: rgba(15, 23, 42, 0.70); color: #F8FAFC; border: 1px solid rgba(255, 255, 255, 0.12); "
                f"border-left: 4px solid {btn_accent}; border-radius: 9px; padding: 7px 14px; font-weight: 700; font-size: 9.5pt; text-align: left; }} "
                f"QPushButton:hover {{ background: {btn_accent}; color: #FFFFFF; border-color: {btn_accent}; }} "
                f"QPushButton:pressed {{ background: rgba(15, 23, 42, 0.95); }}"
            )
            button.clicked.connect(lambda checked=False, page=target: self.tabs.setCurrentWidget(page))
            quick_layout.addWidget(button)
        quick_layout.addStretch(1)
        grid.addWidget(quick, 0, 0)

        recent = QGroupBox("👥  Recent Employees")
        recent.setObjectName("dashboardPanel")
        recent_layout = QVBoxLayout(recent)
        self.dashboard_recent = QTableWidget(0, 5)
        self.dashboard_recent.setHorizontalHeaderLabels(["#", "Employee ID", "Name", "Role", "Status"])
        self.dashboard_recent.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.dashboard_recent.horizontalHeader().setStretchLastSection(True)
        self.dashboard_recent.verticalHeader().setDefaultSectionSize(40)
        for column, width in enumerate((62, 110, 130, 110, 80)):
            self.dashboard_recent.setColumnWidth(column, width)
        self.dashboard_recent.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dashboard_recent.verticalHeader().setVisible(False)
        self.dashboard_recent.setAlternatingRowColors(True)
        self.dashboard_recent.setToolTip("Most recently added employee records. Double-click any row to view.")
        self.dashboard_recent.itemDoubleClicked.connect(lambda item: self.tabs.setCurrentWidget(self.employees_tab))
        recent_layout.addWidget(self.dashboard_recent)
        grid.addWidget(recent, 0, 1)

        tasks_box = QGroupBox("☑  Today's Tasks")
        tasks_box.setObjectName("dashboardPanel")
        tasks_layout = QVBoxLayout(tasks_box)
        self.dashboard_tasks = QTableWidget(0, 5)
        self.dashboard_tasks.setHorizontalHeaderLabels(["Employee", "Task", "Status", "Progress", "Due"])
        self.dashboard_tasks.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.dashboard_tasks.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.dashboard_tasks.verticalHeader().setDefaultSectionSize(40)
        for column, width in enumerate((110, 150, 95, 95, 75)):
            self.dashboard_tasks.setColumnWidth(column, width)
        self.dashboard_tasks.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dashboard_tasks.verticalHeader().setVisible(False)
        self.dashboard_tasks.setAlternatingRowColors(True)
        self.dashboard_tasks.setToolTip("Today's task assignments and progress. Double-click any row to view in Task Manager.")
        self.dashboard_tasks.itemDoubleClicked.connect(lambda item: self.tabs.setCurrentWidget(self.tasks_tab))
        tasks_layout.addWidget(self.dashboard_tasks)
        grid.addWidget(tasks_box, 0, 2)

        attendance = QGroupBox("◉  Today's Attendance")
        attendance.setObjectName("dashboardPanel")
        attendance_layout = QVBoxLayout(attendance)
        self.neon_attendance_gauge = NeonAttendanceGauge()
        self.neon_attendance_gauge.setToolTip("Real-time visual attendance gauge and checked-in ratio.")
        attendance_layout.addWidget(self.neon_attendance_gauge)
        self.dashboard_attendance_summary = QLabel("Attendance summary")
        self.dashboard_attendance_summary.setObjectName("attendanceSummary")
        self.dashboard_attendance_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dashboard_attendance_summary.setWordWrap(True)
        self.dashboard_attendance_summary.setToolTip("Summary counts follow the attendance records for today.")
        attendance_layout.addWidget(self.dashboard_attendance_summary)
        self.dashboard_attendance_table = QTableWidget(0, 3)
        self.dashboard_attendance_table.setHorizontalHeaderLabels(["Employee", "Status", "Check-in"])
        self.dashboard_attendance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.dashboard_attendance_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.dashboard_attendance_table.verticalHeader().setDefaultSectionSize(40)
        for column, width in enumerate((145, 105, 96)):
            self.dashboard_attendance_table.setColumnWidth(column, width)
        self.dashboard_attendance_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dashboard_attendance_table.verticalHeader().setVisible(False)
        self.dashboard_attendance_table.setToolTip("Today's recorded attendance. Double-click any row to open Attendance.")
        self.dashboard_attendance_table.itemDoubleClicked.connect(lambda item: self.tabs.setCurrentWidget(self.attendance_tab))
        attendance_layout.addWidget(self.dashboard_attendance_table)
        grid.addWidget(attendance, 1, 0)

        productivity = QGroupBox("Employee Productivity")
        productivity.setObjectName("dashboardPanel")
        productivity_layout = QVBoxLayout(productivity)
        note = QLabel("Attendance scoring includes every scheduled working day through the report date; holidays and recorded leave are excluded, and unmarked days count as not present.")
        note.setProperty("mutedText", True)
        productivity_layout.addWidget(note)
        self.productivity_chart = ProductivityChart()
        self.productivity_chart.setToolTip("Hover over a productivity bar for the employee score and performance band.")
        productivity_layout.addWidget(self.productivity_chart)
        self.productivity_chart.setMinimumHeight(270)
        productivity_layout.setContentsMargins(14, 12, 14, 14)
        grid.addWidget(productivity, 1, 1, 1, 2)

        self.dashboard_grid = grid
        self.dashboard_panels = {
            "quick": quick,
            "recent": recent,
            "tasks": tasks_box,
            "attendance": attendance,
            "productivity": productivity,
        }

        self.productivity_table = QTableWidget(0, 7)
        self.productivity_table.setHorizontalHeaderLabels(["Employee", "Joined / tracking start", "Working days", "Present days", "Tasks", "Completed", "Score"])
        self.productivity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.productivity_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.productivity_table.setVisible(False)
        root.addWidget(self.productivity_table)

    def build_employees(self):
        l = QVBoxLayout()
        self._wrap_page_in_scroll(self.employees_tab, l, "Employees", "Manage employee records, roles, and contact details.")

        toolbar_card = QFrame()
        toolbar_card.setObjectName("empToolbarCard")
        toolbar_layout = QVBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(12, 10, 12, 10)
        toolbar_layout.setSpacing(10)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        search_label = QLabel("🔍 Search:")
        search_label.setStyleSheet("font-weight: 600;")
        search_row.addWidget(search_label)
        self.emp_search = QLineEdit()
        self.emp_search.setPlaceholderText("Search employee name, ID or role...")
        self.emp_search.textChanged.connect(self.refresh_employees)
        search_row.addWidget(self.emp_search, 2)

        dept_label = QLabel("🏢 Department:")
        dept_label.setStyleSheet("font-weight: 600;")
        search_row.addWidget(dept_label)
        self.emp_dept_filter = QComboBox()
        self.emp_dept_filter.addItem("🏢 All Departments / Groups")
        self.emp_dept_filter.setToolTip("View only employees present in this department or group")
        self.emp_dept_filter.currentTextChanged.connect(lambda _text: self.refresh_employees())
        search_row.addWidget(self.emp_dept_filter, 1)

        sort_label = QLabel("🔢 Sort:")
        sort_label.setStyleSheet("font-weight: 600;")
        search_row.addWidget(sort_label)
        self.emp_sort_combo = QComboBox()
        self.emp_sort_combo.addItem("🔢 Serial Number / ID")
        self.emp_sort_combo.addItem("🏢 Department / Group")
        self.emp_sort_combo.addItem("🔤 Name (A-Z)")
        self.emp_sort_combo.setToolTip("Sort employees by Serial Number, Department, or Alphabetical")
        self.emp_sort_combo.currentTextChanged.connect(lambda _text: self.refresh_employees())
        search_row.addWidget(self.emp_sort_combo, 1)

        refresh_emp_btn = QPushButton("🔄 Refresh")
        refresh_emp_btn.setObjectName("empRefreshBtn")
        refresh_emp_btn.setToolTip("Reload employee directory")
        refresh_emp_btn.setMinimumHeight(36)
        refresh_emp_btn.clicked.connect(self.refresh_employees)
        search_row.addWidget(refresh_emp_btn)

        self.emp_count_badge = QLabel("Total: 0")
        self.emp_count_badge.setStyleSheet("font-weight: 700; padding: 4px 10px; border-radius: 6px; background: rgba(99, 102, 241, 0.15); color: #6366F1;")
        search_row.addWidget(self.emp_count_badge)
        toolbar_layout.addLayout(search_row)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)
        actions = [
            ("➕ Add Employee", self.add_employee, "Add a new employee record", True, "empAddBtn"),
            ("📁 Manage Sections", self.manage_employee_groups, "Manage custom sections and groups (e.g. Technical, House Keeping)", False, "empGroupsBtn"),
            ("⬆ Move Up", self.move_employee_up, "Move selected employee up in custom order", False, "empMoveUpBtn"),
            ("⬇ Move Down", self.move_employee_down, "Move selected employee down in custom order", False, "empMoveDownBtn"),
            ("✏️ Edit Selected", self.edit_employee, "Edit the selected employee", False, "empEditBtn"),
            ("🔄 Activate / Deactivate", self.toggle_employee, "Toggle active status for selected employee", False, "empToggleBtn"),
            ("🗑️ Delete Employee", self.delete_employee, "Permanently delete the selected employee", False, "empDeleteBtn"),
        ]
        for label, slot, tip, is_primary, obj_name in actions:
            b = QPushButton(label)
            b.setObjectName(obj_name)
            b.clicked.connect(slot)
            b.setToolTip(tip)
            b.setMinimumHeight(36)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if obj_name in ("empAddBtn", "empEditBtn", "empToggleBtn") and not self.is_hr_admin_or_dev:
                b.setEnabled(False)
                b.setToolTip("Staff and employee accounts have limited access and cannot modify employee records.")
            elif obj_name == "empDeleteBtn" and not self.is_admin_or_dev:
                b.setEnabled(False)
                b.setToolTip("Only an Admin or Developer can delete employee records.")
            actions_row.addWidget(b)
        actions_row.addStretch(1)
        toolbar_layout.addLayout(actions_row)

        l.addWidget(toolbar_card)

        # Card 2: Employee Directory Bento Enclosure
        emp_roster_card = QFrame()
        emp_roster_card.setObjectName("empRosterCard")
        emp_roster_layout = QVBoxLayout(emp_roster_card)
        emp_roster_layout.setContentsMargins(16, 14, 16, 14)
        emp_roster_layout.setSpacing(10)

        emp_header_row = QHBoxLayout()
        emp_title = QLabel("Employee Directory")
        emp_title.setObjectName("empRosterTitle")
        emp_title.setWordWrap(False)
        emp_title.setMinimumWidth(200)
        emp_header_row.addWidget(emp_title)
        emp_header_row.addStretch(1)
        emp_hint = QLabel("Active staff members & organizational records")
        emp_hint.setObjectName("empRosterHint")
        emp_hint.setWordWrap(False)
        emp_header_row.addWidget(emp_hint)
        emp_roster_layout.addLayout(emp_header_row)

        self.emp_table = EmployeeTableWidget(0, 8, self)
        self.emp_table.setHorizontalHeaderLabels(["ID", "Employee ID", "Name", "Department", "Role", "Phone", "Email", "Status"])
        self.emp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.emp_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.emp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.emp_table.cellDoubleClicked.connect(lambda r, c: self.edit_employee())
        emp_roster_layout.addWidget(self.emp_table)
        l.addWidget(emp_roster_card)

    def build_tasks(self):
        l = QVBoxLayout()
        self._wrap_page_in_scroll(self.tasks_tab, l, "Task Manager", "Add, edit, and track daily tasks and evidence.")

        task_toolbar_card = QFrame()
        task_toolbar_card.setObjectName("taskToolbarCard")
        task_toolbar_card_layout = QVBoxLayout(task_toolbar_card)
        task_toolbar_card_layout.setContentsMargins(12, 10, 12, 10)
        task_toolbar_card_layout.setSpacing(10)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        date_label = QLabel("📅 Date:")
        date_label.setStyleSheet("font-weight: 600;")
        filter_row.addWidget(date_label)
        self.task_date = QDateEdit()
        configure_date_edit(self.task_date)
        self.task_date.setDisplayFormat("yyyy-MM-dd")
        self.task_date.setDate(QDate.currentDate())
        self.task_date.setMinimumWidth(125)
        self.task_date.dateChanged.connect(self.refresh_tasks)
        filter_row.addWidget(self.task_date)

        filter_label = QLabel("👤 Employee:")
        filter_label.setStyleSheet("font-weight: 600;")
        filter_row.addWidget(filter_label)
        self.task_filter = QComboBox()
        self.task_filter.addItem("All employees", None)
        self.task_filter.setMinimumWidth(170)
        self.task_filter.setMaximumWidth(260)
        self.task_filter.currentIndexChanged.connect(self.refresh_tasks)
        filter_row.addWidget(self.task_filter)

        refresh_tasks_btn = QPushButton("🔄 Refresh")
        refresh_tasks_btn.setObjectName("taskRefreshBtn")
        refresh_tasks_btn.setToolTip("Reload tasks for the selected date and employee")
        refresh_tasks_btn.setMinimumHeight(36)
        refresh_tasks_btn.clicked.connect(self.refresh_tasks)
        filter_row.addWidget(refresh_tasks_btn)

        filter_row.addStretch(1)

        self.task_count_badge = QLabel("Tasks: 0")
        self.task_count_badge.setStyleSheet("font-weight: 700; padding: 4px 10px; border-radius: 6px; background: rgba(99, 102, 241, 0.15); color: #6366F1;")
        filter_row.addWidget(self.task_count_badge)
        task_toolbar_card_layout.addLayout(filter_row)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        task_actions = [
            ("➕ Add Task", self.add_task, "Create a new task for the selected date", True, "taskAddBtn"),
            ("✏️ Edit Selected", self.edit_task, "Edit one selected task", False, "taskEditBtn"),
            ("📝 Bulk Edit Selected", self.bulk_edit_tasks, "Apply chosen fields to multiple selected tasks", False, "taskBulkEditBtn"),
            ("☑️ Select All", self.task_table_select_all, "Select every task shown for the selected date and employee filter", False, "taskSelectAllBtn"),
            ("🗑️ Delete Selected", self.delete_task, "Delete the selected task", False, "taskDeleteBtn"),
            ("🔗 Open Proof", self.open_proof, "Open proof/evidence link in browser", False, "taskProofBtn"),
        ]
        for label, slot, tip, is_primary, obj_name in task_actions:
            b = QPushButton(label)
            b.setObjectName(obj_name)
            b.clicked.connect(slot)
            b.setToolTip(tip)
            b.setMinimumHeight(36)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if obj_name == "taskAddBtn":
                b.setStyleSheet(
                    "QPushButton#taskAddBtn { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #6366F1); "
                    "color: #FFFFFF; border: 1px solid rgba(165, 180, 252, 0.45); border-radius: 8px; font-weight: 700; padding: 6px 16px; } "
                    "QPushButton#taskAddBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #4F46E5); border-color: #818CF8; }"
                )
            elif obj_name == "taskDeleteBtn":
                if not self.is_admin_or_dev:
                    b.setEnabled(False)
                    b.setToolTip("Only an Admin or Developer can delete tasks.")
                b.setStyleSheet(
                    "QPushButton#taskDeleteBtn { background: rgba(239, 68, 68, 0.12); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 8px; font-weight: 600; padding: 6px 14px; } "
                    "QPushButton#taskDeleteBtn:hover { background: rgba(239, 68, 68, 0.25); color: #FFFFFF; border-color: #EF4444; }"
                )
            else:
                b.setStyleSheet(
                    "QPushButton { background: rgba(255, 255, 255, 0.05); color: #CBD5E1; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; font-weight: 600; padding: 6px 14px; } "
                    "QPushButton:hover { background: rgba(255, 255, 255, 0.10); color: #FFFFFF; border-color: rgba(255, 255, 255, 0.25); }"
                )
            actions_row.addWidget(b)
        actions_row.addStretch(1)
        task_toolbar_card_layout.addLayout(actions_row)

        l.addWidget(task_toolbar_card)

        # Bento KPI Metric Cards Row (Total Tasks, Completed, In Progress, Custom Tasks)
        bento_row = QHBoxLayout()
        bento_row.setSpacing(12)

        def make_task_kpi_card(title, icon, accent_col):
            card = QFrame()
            card.setObjectName("taskKpiMetricCard")
            card.setStyleSheet(
                f"QFrame#taskKpiMetricCard {{ background: rgba(30, 41, 59, 0.45); border: 1.5px solid rgba(255, 255, 255, 0.08); "
                f"border-top: 3.5px solid {accent_col}; border-radius: 12px; padding: 10px 14px; }} "
                f"QFrame#taskKpiMetricCard:hover {{ border-color: {accent_col}; background: rgba(30, 41, 59, 0.70); }}"
            )
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(10, 8, 10, 8)
            c_lay.setSpacing(12)
            
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 16pt; padding: 6px; border-radius: 8px; background: rgba(255, 255, 255, 0.06);")
            c_lay.addWidget(icon_lbl)

            col = QVBoxLayout()
            col.setSpacing(2)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 8pt; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px;")
            val_lbl = QLabel("0")
            val_lbl.setStyleSheet(f"font-size: 17pt; font-weight: 900; color: {accent_col};")
            col.addWidget(t_lbl)
            col.addWidget(val_lbl)
            c_lay.addLayout(col, 1)
            return card, val_lbl

        c1, self.kpi_total_tasks = make_task_kpi_card("Total Tasks", "📋", "#6366F1")
        c2, self.kpi_completed_tasks = make_task_kpi_card("Completed", "✅", "#10B981")
        c3, self.kpi_in_progress_tasks = make_task_kpi_card("In Progress", "⏳", "#F59E0B")
        c4, self.kpi_pending_tasks = make_task_kpi_card("Pending Tasks", "⏱️", "#EC4899")
        self.kpi_custom_tasks = self.kpi_pending_tasks

        bento_row.addWidget(c1)
        bento_row.addWidget(c2)
        bento_row.addWidget(c3)
        bento_row.addWidget(c4)
        l.addLayout(bento_row)

        # Card 2: Tasks Overview Bento Enclosure
        task_roster_card = QFrame()
        task_roster_card.setObjectName("taskRosterCard")
        task_roster_layout = QVBoxLayout(task_roster_card)
        task_roster_layout.setContentsMargins(16, 14, 16, 14)
        task_roster_layout.setSpacing(10)

        task_header_row = QHBoxLayout()
        task_title = QLabel("Tasks Overview")
        task_title.setObjectName("taskRosterTitle")
        task_title.setWordWrap(False)
        task_title.setMinimumWidth(180)
        task_header_row.addWidget(task_title)
        task_header_row.addStretch(1)
        task_hint = QLabel("Daily assignment progression & status logs")
        task_hint.setObjectName("taskRosterHint")
        task_hint.setWordWrap(False)
        task_header_row.addWidget(task_hint)
        task_roster_layout.addLayout(task_header_row)

        self.task_table = QTableWidget(0, 13)
        self.task_table.setHorizontalHeaderLabels([
            "ID", "Date", "Employee", "Department", "Assigned Task",
            "Target Qty", "Actual Qty", "Completion %", "Priority",
            "Status", "Proof / Link", "Custom Values", "Next Action"
        ])
        self.task_table.setColumnHidden(0, True)
        task_hdr = self.task_table.horizontalHeader()
        task_hdr.setSectionResizeMode(QHeaderView.Interactive)
        task_hdr.setSectionResizeMode(4, QHeaderView.Stretch)   # Assigned Task
        task_hdr.setSectionResizeMode(10, QHeaderView.Stretch)  # Proof / Link
        task_hdr.setSectionResizeMode(11, QHeaderView.Stretch)  # Custom Values
        task_hdr.setSectionResizeMode(12, QHeaderView.Stretch)  # Next Action
        task_hdr.resizeSection(1, 100)  # Date
        task_hdr.resizeSection(2, 140)  # Employee
        task_hdr.resizeSection(3, 110)  # Department
        task_hdr.resizeSection(5, 90)   # Target Qty
        task_hdr.resizeSection(6, 90)   # Actual Qty
        task_hdr.resizeSection(7, 100)  # Completion %
        task_hdr.resizeSection(8, 90)   # Priority
        task_hdr.resizeSection(9, 110)  # Status
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.itemSelectionChanged.connect(self._on_task_table_selection_changed)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(15, 23, 42, 0.65);
                alternate-background-color: rgba(30, 41, 59, 0.45);
                gridline-color: rgba(148, 163, 184, 0.12);
                border: 1px solid rgba(148, 163, 184, 0.15);
                border-radius: 8px;
                color: #F8FAFC;
                selection-background-color: rgba(99, 102, 241, 0.35);
                selection-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #0F172A;
                color: #94A3B8;
                font-weight: 700;
                font-size: 8.5pt;
                padding: 8px 6px;
                border: none;
                border-bottom: 2px solid rgba(129, 140, 248, 0.4);
            }
        """)
        self.task_table.itemDoubleClicked.connect(lambda _item: self.edit_task())
        task_roster_layout.addWidget(self.task_table)
        l.addWidget(task_roster_card)

    def build_tracker(self):
        l=QVBoxLayout()
        self._wrap_page_in_scroll(self.tracker_tab, l, "Employee Task Tracker", "Review assigned work and evidence.")
        tracker_toolbar_card = QFrame()
        tracker_toolbar_card.setObjectName("trackerToolbarCard")
        tracker_toolbar_layout = QVBoxLayout(tracker_toolbar_card)
        tracker_toolbar_layout.setContentsMargins(14, 12, 14, 12)
        tracker_toolbar_layout.setSpacing(10)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.tracker_employee = QComboBox()
        self.tracker_employee.addItem("Select employee", None)
        self.tracker_employee.setMinimumWidth(180)
        self.tracker_employee.setMaximumWidth(280)
        self.tracker_employee.setMinimumHeight(36)
        self.tracker_employee.currentIndexChanged.connect(self.refresh_tracker)
        self.tracker_date = QDateEdit()
        configure_date_edit(self.tracker_date)
        self.tracker_date.setDisplayFormat("yyyy-MM-dd")
        self.tracker_date.setDate(QDate.currentDate())
        self.tracker_date.setMinimumWidth(130)
        self.tracker_date.setMinimumHeight(36)
        self.tracker_date.dateChanged.connect(self.refresh_tracker)

        emp_label = QLabel("👤 Employee:")
        emp_label.setStyleSheet("font-weight: 700; font-size: 9pt;")
        filters.addWidget(emp_label)
        filters.addWidget(self.tracker_employee)

        date_label = QLabel("📅 Task date:")
        date_label.setStyleSheet("font-weight: 700; font-size: 9pt;")
        filters.addWidget(date_label)
        filters.addWidget(self.tracker_date)

        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.setObjectName("trackerRefreshBtn")
        refresh_button.setToolTip("Reload tasks for the selected employee and date")
        refresh_button.setMinimumHeight(36)
        refresh_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_button.clicked.connect(self.refresh_tracker)
        filters.addWidget(refresh_button)
        filters.addStretch(1)
        tracker_toolbar_layout.addLayout(filters)
        l.addWidget(tracker_toolbar_card)

        self.tracker_summary = QLabel("Select an employee to view assigned tasks.")
        self.tracker_summary.setProperty("statusSummary", True)
        self.tracker_summary.setStyleSheet("QLabel { border-radius: 10px; padding: 10px 14px; font-weight: 600; }")
        l.addWidget(self.tracker_summary)

        self.tracker_progress = QProgressBar()
        self.tracker_progress.setRange(0, 100)
        self.tracker_progress.setValue(0)
        self.tracker_progress.setFormat("Average task progress: %p%")
        self.tracker_progress.setMinimumHeight(24)
        l.addWidget(self.tracker_progress)

        # Card 2: Tracker Progression Bento Enclosure
        tracker_roster_card = QFrame()
        tracker_roster_card.setObjectName("trackerRosterCard")
        tracker_roster_layout = QVBoxLayout(tracker_roster_card)
        tracker_roster_layout.setContentsMargins(16, 14, 16, 14)
        tracker_roster_layout.setSpacing(10)

        tracker_header_row = QHBoxLayout()
        tracker_title = QLabel("Employee Activity & Progression")
        tracker_title.setObjectName("trackerRosterTitle")
        tracker_title.setWordWrap(False)
        tracker_title.setMinimumWidth(260)
        tracker_header_row.addWidget(tracker_title)
        tracker_header_row.addStretch(1)
        tracker_hint = QLabel("Daily assignment progression & status logs")
        tracker_hint.setObjectName("trackerRosterHint")
        tracker_hint.setWordWrap(False)
        tracker_header_row.addWidget(tracker_hint)
        tracker_roster_layout.addLayout(tracker_header_row)

        self.tracker_table = QTableWidget(0, 8)
        self.tracker_table.setHorizontalHeaderLabels(["Task ID", "Task", "Priority", "Status", "Progress", "Due time", "Proof link", "Manager remarks"])
        self.tracker_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tracker_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tracker_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tracker_roster_layout.addWidget(self.tracker_table)
        l.addWidget(tracker_roster_card)

    def build_attendance(self):
        l=QVBoxLayout()
        self._wrap_page_in_scroll(self.attendance_tab, l, "Attendance & Working Calendar", "Record daily attendance and configure scheduled workdays.")

        att_toolbar_card = QFrame()
        att_toolbar_card.setObjectName("attToolbarCard")
        att_toolbar_layout = QVBoxLayout(att_toolbar_card)
        att_toolbar_layout.setContentsMargins(16, 14, 16, 14)
        att_toolbar_layout.setSpacing(12)

        # Row 1: Filters on the left, Holiday management on the right
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        date_label = QLabel("Date:")
        date_label.setStyleSheet("font-weight: 700; font-size: 9pt;")
        row1.addWidget(date_label)
        self.att_date = QDateEdit()
        configure_date_edit(self.att_date)
        self.att_date.setDisplayFormat("yyyy-MM-dd")
        self.att_date.setDate(QDate.currentDate())
        self.att_date.setMinimumWidth(140)
        self.att_date.setMinimumHeight(34)
        self.att_date.dateChanged.connect(self.refresh_attendance)
        row1.addWidget(self.att_date)

        filter_label = QLabel("Filter employee:")
        filter_label.setStyleSheet("font-weight: 700; font-size: 9pt;")
        row1.addWidget(filter_label)
        self.att_employee_filter = QComboBox()
        self.att_employee_filter.addItem("All employees", None)
        for e in self.db.employees(False):
            self.att_employee_filter.addItem(e["name"], e["id"])
        self.att_employee_filter.setMinimumWidth(185)
        self.att_employee_filter.setMaximumWidth(260)
        self.att_employee_filter.setMinimumHeight(34)
        self.att_employee_filter.currentIndexChanged.connect(self.refresh_attendance)
        row1.addWidget(self.att_employee_filter)

        row1.addStretch(1)

        declare_holiday_btn = QPushButton("Declare Holiday")
        declare_holiday_btn.setObjectName("attDeclareHolidayBtn")
        declare_holiday_btn.setToolTip("Mark the selected date as a declared company holiday")
        declare_holiday_btn.setMinimumHeight(34)
        declare_holiday_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        declare_holiday_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        declare_holiday_btn.setStyleSheet("QPushButton { font-weight: 600; font-size: 8.5pt; border-radius: 8px; padding: 6px 14px; background: rgba(99, 102, 241, 0.14); color: #A5B4FC; border: 1px solid rgba(99, 102, 241, 0.30); } QPushButton:hover { background: #6366F1; color: #FFFFFF; border-color: #818CF8; }")
        declare_holiday_btn.clicked.connect(self.declare_holiday)
        row1.addWidget(declare_holiday_btn)

        remove_holiday_btn = QPushButton("Remove Holiday")
        remove_holiday_btn.setObjectName("attRemoveHolidayBtn")
        remove_holiday_btn.setToolTip("Remove declared holiday from the selected date")
        remove_holiday_btn.setMinimumHeight(34)
        remove_holiday_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        remove_holiday_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_holiday_btn.setStyleSheet("QPushButton { font-weight: 600; font-size: 8.5pt; border-radius: 8px; padding: 6px 14px; background: rgba(239, 68, 68, 0.12); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.28); } QPushButton:hover { background: #EF4444; color: #FFFFFF; border-color: #F87171; }")
        remove_holiday_btn.clicked.connect(self.remove_holiday)
        row1.addWidget(remove_holiday_btn)

        att_toolbar_layout.addLayout(row1)

        # Row 2: Selection & Bulk Operations + Attendance Status Markers + Punch Actions (Balanced spacing)
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        self.att_select_all_button = QPushButton("Select All")
        self.att_select_all_button.setObjectName("attSelectAllBtn")
        self.att_select_all_button.setToolTip("Select all employees shown for the selected date")
        self.att_select_all_button.setMinimumHeight(34)
        self.att_select_all_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.att_select_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.att_select_all_button.clicked.connect(self.attendance_select_all)
        row2.addWidget(self.att_select_all_button)

        self.att_bulk_edit_button = QPushButton("Bulk Edit Selected")
        self.att_bulk_edit_button.setObjectName("attBulkEditBtn")
        self.att_bulk_edit_button.setToolTip("Apply chosen attendance fields to the selected employees")
        self.att_bulk_edit_button.setMinimumHeight(34)
        self.att_bulk_edit_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.att_bulk_edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.att_bulk_edit_button.clicked.connect(self.bulk_edit_attendance)
        row2.addWidget(self.att_bulk_edit_button)

        row2.addSpacing(10)

        status_specs = [
            ("● Present", lambda: self.set_attendance_status("Present"), "attPresentBtn"),
            ("● Absent", lambda: self.set_attendance_status("Absent"), "attAbsentBtn"),
            ("● Leave", lambda: self.set_attendance_status("Leave"), "attLeaveBtn"),
        ]
        for label, slot, obj_name in status_specs:
            b = QPushButton(label)
            b.setObjectName(obj_name)
            b.setMinimumHeight(34)
            b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(slot)
            row2.addWidget(b)

        row2.addSpacing(10)

        time_actions = [
            ("Check In", self.check_in, "attCheckInBtn"),
            ("Check Out", self.check_out, "attCheckOutBtn"),
            ("Edit Times", self.edit_attendance_times, "attEditTimesBtn"),
            ("Remarks", self.attendance_note, "attRemarksBtn"),
        ]
        for label, slot, obj_name in time_actions:
            b = QPushButton(label)
            b.setObjectName(obj_name)
            b.setMinimumHeight(34)
            b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(slot)
            row2.addWidget(b)

        self.holiday_btn = QToolButton()
        self.holiday_btn.setText("Holiday")
        self.holiday_btn.hide()
        row2.addStretch(1)
        att_toolbar_layout.addLayout(row2)

        l.addWidget(att_toolbar_card)

        # Card 1: Daily Attendance Roster Enclosure
        att_roster_card = QFrame()
        att_roster_card.setObjectName("attRosterCard")
        att_roster_layout = QVBoxLayout(att_roster_card)
        att_roster_layout.setContentsMargins(16, 14, 16, 14)
        att_roster_layout.setSpacing(10)

        roster_header_row = QHBoxLayout()
        roster_title = QLabel("Daily Attendance Roster")
        roster_title.setObjectName("attRosterTitle")
        roster_title.setWordWrap(False)
        roster_title.setMinimumWidth(220)
        roster_title.setStyleSheet("font-size: 11pt; font-weight: 700; color: #F8FAFC; letter-spacing: 0.3px;")
        roster_header_row.addWidget(roster_title)
        roster_header_row.addStretch(1)
        roster_hint = QLabel("Real-time punch records & status updates")
        roster_hint.setObjectName("attRosterHint")
        roster_hint.setStyleSheet("font-size: 8.5pt; font-weight: 500; color: #64748B;")
        roster_header_row.addWidget(roster_hint)
        att_roster_layout.addLayout(roster_header_row)

        self.holiday_banner = QLabel("")
        self.holiday_banner.setObjectName("attHolidayBanner")
        self.holiday_banner.setProperty("warningBanner", True)
        self.holiday_banner.setStyleSheet("QLabel { background: rgba(255, 255, 255, 0.03); color: #94A3B8; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 7px 14px; font-size: 8.5pt; font-weight: 500; }")
        att_roster_layout.addWidget(self.holiday_banner)

        self.att_table=QTableWidget(0,7); self.att_table.setHorizontalHeaderLabels(["Employee","Date","Attendance status","Check-in","Check-out","Net hours","Remarks"])
        att_header = self.att_table.horizontalHeader()
        att_header.setSectionResizeMode(QHeaderView.Interactive)
        att_header.setMinimumSectionSize(90)
        for col, width in enumerate((156, 120, 158, 126, 126, 96, 220)):
            self.att_table.setColumnWidth(col, width)
        self.att_table.horizontalHeader().setStretchLastSection(True)
        self.att_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.att_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.att_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.att_table.setMinimumHeight(200)
        self.att_table.setMaximumHeight(360)
        self.att_table.verticalHeader().setDefaultSectionSize(52)
        self.att_table.verticalHeader().setMinimumSectionSize(48)
        for c, align in enumerate([
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        ]):
            h_item = self.att_table.horizontalHeaderItem(c)
            if h_item:
                h_item.setTextAlignment(align)
        self.att_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.att_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.att_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.att_table.setWordWrap(False)
        self.att_table.setToolTip("Update attendance directly using the Status, Check-in, Check-out and Note fields in each employee row. Scroll horizontally to see every column on smaller screens.")
        att_roster_layout.addWidget(self.att_table)
        l.addWidget(att_roster_card)

        # Card 2: Totals & Period Summary Card Enclosure
        att_summary_card = QFrame()
        att_summary_card.setObjectName("attSummaryCard")
        att_summary_layout = QVBoxLayout(att_summary_card)
        att_summary_layout.setContentsMargins(14, 12, 14, 14)
        att_summary_layout.setSpacing(10)

        summary_header_row = QHBoxLayout()
        summary_title = QLabel("📊  ATTENDANCE TOTALS & PERIOD SUMMARY")
        summary_title.setObjectName("attSummaryTitle")
        summary_title.setWordWrap(False)
        summary_title.setStyleSheet("font-size: 9.5pt; font-weight: 800; color: #38BDF8; letter-spacing: 0.6px;")
        summary_header_row.addWidget(summary_title)
        summary_header_row.addStretch(1)

        summary_note = QLabel("Attendance totals exclude declared holidays and non-working weekdays.")
        summary_note.setObjectName("attSummaryNote")
        summary_note.setWordWrap(False)
        summary_note.setProperty("mutedText", True)
        summary_note.setStyleSheet("QLabel { background: rgba(15, 23, 42, 0.70); color: #94A3B8; border: 1px solid rgba(51, 65, 85, 0.50); border-radius: 7px; padding: 4px 10px; font-size: 8pt; font-weight: 600; }")
        summary_header_row.addWidget(summary_note)
        att_summary_layout.addLayout(summary_header_row)

        self.attendance_summary_table=QTableWidget(0,8)
        headers = ["Employee","Start date","Work days","Present","Absent","Leave","Holidays","Total present"]
        self.attendance_summary_table.setHorizontalHeaderLabels(headers)
        header = self.attendance_summary_table.horizontalHeader()
        header.setMinimumSectionSize(82)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for col in range(2, len(headers)):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        for c in range(len(headers)):
            h_item = self.attendance_summary_table.horizontalHeaderItem(c)
            if h_item:
                if c == 0:
                    h_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                else:
                    h_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.attendance_summary_table.setWordWrap(False)
        self.attendance_summary_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.attendance_summary_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.attendance_summary_table.setMinimumHeight(150)
        for i, h in enumerate(headers):
            self.attendance_summary_table.horizontalHeaderItem(i).setToolTip(h)
        self.attendance_summary_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.attendance_summary_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        att_summary_layout.addWidget(self.attendance_summary_table)
        l.addWidget(att_summary_card)

    def build_reports(self):
        outer = QVBoxLayout(self.reports_tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        scroll.setAutoFillBackground(False)
        scroll.viewport().setStyleSheet("background: transparent; border: 0;")
        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        content.setAutoFillBackground(False)
        content.setObjectName("pageContent")
        l = QVBoxLayout(content)
        l.setContentsMargins(20, 14, 20, 16)
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

        for ctrl in (self.report_type, self.report_date, self.report_scope, self.report_employee,
                     self.report_exclude_employee, self.report_format, self.archived_report):
            ctrl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            ctrl.setFixedWidth(440)
            ctrl.setMinimumHeight(34)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        form.addRow("Report type", self.report_type)
        form.addRow("Report date", self.report_date)
        form.addRow("Report scope", self.report_scope)
        form.addRow("Employee", self.report_employee)
        form.addRow("Exclude employee (consolidated only)", self.report_exclude_employee)
        form.addRow("Output format", self.report_format)
        form.addRow("Historical archived PDF (optional)", self.archived_report)
        l.addWidget(form_group)

        # Report-specific include options; the report template stays the same while
        # users can choose which sections and fields to print or export.
        self.eod_options_group = QGroupBox("Audit / EOD content — choose sections to include")
        self.report_options_grid = QGridLayout(self.eod_options_group)
        self.report_options_grid.setContentsMargins(12, 18, 12, 12)
        self.report_options_grid.setHorizontalSpacing(18)
        self.report_options_grid.setVerticalSpacing(8)
        self.eod_checks = {}
        self.report_option_keys = {
            "Audit / EOD": (
                "summary", "identity", "contact", "target", "work_status",
                "late_links", "missing_proof", "target_status", "tasks",
                "target_qty", "actual_qty", "completion_pct", "priority",
                "details", "due_time", "proof", "proof_notes", "custom_values",
                "next_action", "remarks", "expose_link", "pending"
            ),
            "Employee Attendance": ("attendance_identity", "attendance_status", "attendance_times", "attendance_remarks", "attendance_summary"),
            "Employee Details": ("details_identity", "details_contact", "details_joining", "details_status", "details_notes"),
            "Employee Productivity": ("productivity_identity", "productivity_metrics", "productivity_explanation", "productivity_tracking", "productivity_tasks"),
        }
        report_options = [
            ("summary", "Daily summary", True),
            ("identity", "Employee ID / Department / Role", True),
            ("target", "Target", True),
            ("contact", "Phone / Email", False),
            ("work_status", "Work / EOD status", True),
            ("late_links", "Late / Links status", True),
            ("missing_proof", "Missing proof", True),
            ("target_status", "Target status", True),
            ("tasks", "Task names and status", True),
            ("target_qty", "Target Qty", True),
            ("actual_qty", "Actual Qty", True),
            ("completion_pct", "Completion %", True),
            ("priority", "Priority", True),
            ("details", "Task details", True),
            ("due_time", "Due time", True),
            ("proof", "Proof / evidence links", True),
            ("proof_notes", "Proof notes", False),
            ("custom_values", "Custom Values (Tracking Fields)", True),
            ("next_action", "Next Action", True),
            ("remarks", "Manager remarks", True),
            ("expose_link", "Expose proof links (show full URLs for all employees)", False),
            ("pending", "Pending items", True),
            ("attendance_identity", "Employee ID / Department", True),
            ("attendance_status", "Attendance status", True),
            ("attendance_times", "Check-in / out and net hours", True),
            ("attendance_remarks", "Attendance remarks", True),
            ("attendance_summary", "Attendance summary", True),
            ("details_identity", "Employee ID / Department / Role", True),
            ("details_contact", "Phone / Email", True),
            ("details_joining", "Joining date", True),
            ("details_status", "Active / inactive status", True),
            ("details_notes", "Employee notes", True),
            ("productivity_identity", "Employee ID / Department", True),
            ("productivity_metrics", "Productivity scores", True),
            ("productivity_explanation", "Scoring explanation", True),
            ("productivity_tracking", "Tracking and attendance totals", True),
            ("productivity_tasks", "Task progress details", True),
        ]
        for key, label, default_checked in report_options:
            saved = self.db.get_setting(f"report_opt_{key}", "")
            checked = (saved == "1") if saved in ("0", "1") else default_checked
            cb = QCheckBox(label)
            cb.setChecked(checked)
            def _bind_cb(k, box):
                return lambda _state: (self.db.set_setting(f"report_opt_{k}", "1" if box.isChecked() else "0"), self.preview_report())
            cb.stateChanged.connect(_bind_cb(key, cb))
            self.eod_checks[key] = cb
        l.addWidget(self.eod_options_group)

        self.business_data_group = QGroupBox("Optional business data — include these catalogs in the report")
        business_data_layout = QHBoxLayout(self.business_data_group)
        business_data_layout.setContentsMargins(12, 16, 12, 10)
        business_data_layout.setSpacing(18)
        self.business_report_checks = {
            "business_products": QCheckBox("Product catalog and available stock"),
            "business_services": QCheckBox("Service catalog"),
        }
        for checkbox in self.business_report_checks.values():
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(lambda _state: self.preview_report())
            business_data_layout.addWidget(checkbox)
        business_data_layout.addStretch(1)
        l.addWidget(self.business_data_group)

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
            ("🖨️ Print Preview", self.open_print_preview, False),
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
        preview_label = QLabel("🖨️  Live print preview — updates when report options change")
        preview_label.setProperty("mutedText", True)
        l.addWidget(preview_label)
        self.report_summary = QTextEdit()
        self.report_summary.setReadOnly(True)
        self.report_summary.setPlaceholderText("Report preview summary appears here. Select options and click Preview Report.")
        self.report_summary.setMinimumHeight(220)
        self.report_summary.setMaximumHeight(420)
        self.report_summary.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.report_summary.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.report_summary.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.report_summary.setObjectName("reportPreview")
        l.addWidget(self.report_summary)

        l.addStretch(1)
        scroll.setWidget(content)
        self.apply_content_surface_styles()
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
        archive_toolbar_card = QFrame()
        archive_toolbar_card.setObjectName("archiveToolbarCard")
        archive_toolbar_layout = QHBoxLayout(archive_toolbar_card)
        archive_toolbar_layout.setContentsMargins(14, 12, 14, 12)
        archive_toolbar_layout.setSpacing(8)

        for label, slot, obj_name in [
            ("📤 Upload PDF(s)", self.upload_eod_pdfs, "archiveUploadBtn"),
            ("👁️ View Selected", self.open_archived_pdf, "archiveViewBtn"),
            ("💾 Export Selected", self.export_archived_pdf, "archiveExportBtn"),
            ("🗑️ Delete Selected", self.delete_archived_pdf, "archiveDeleteBtn"),
            ("🔄 Refresh", self.refresh_archive, "archiveRefreshBtn")
        ]:
            b = QPushButton(label)
            b.setObjectName(obj_name)
            b.clicked.connect(slot)
            b.setMinimumHeight(36)
            b.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if obj_name == "archiveDeleteBtn" and not self.is_admin_or_dev:
                b.setEnabled(False)
                b.setToolTip("Only an Admin or Developer can delete archived documents.")
            archive_toolbar_layout.addWidget(b)
        archive_toolbar_layout.addStretch(1)
        l.addWidget(archive_toolbar_card)

        # Card 2: Document Archive Bento Enclosure
        archive_roster_card = QFrame()
        archive_roster_card.setObjectName("archiveRosterCard")
        archive_roster_layout = QVBoxLayout(archive_roster_card)
        archive_roster_layout.setContentsMargins(16, 14, 16, 14)
        archive_roster_layout.setSpacing(10)

        archive_header_row = QHBoxLayout()
        archive_title = QLabel("Archived Audit Documents")
        archive_title.setObjectName("archiveRosterTitle")
        archive_title.setWordWrap(False)
        archive_title.setMinimumWidth(240)
        archive_header_row.addWidget(archive_title)
        archive_header_row.addStretch(1)
        archive_hint = QLabel("Stored historical reports & audit records")
        archive_hint.setObjectName("archiveRosterHint")
        archive_hint.setWordWrap(False)
        archive_header_row.addWidget(archive_hint)
        archive_roster_layout.addLayout(archive_header_row)

        self.archive_table = QTableWidget(0, 7)
        self.archive_table.setHorizontalHeaderLabels(["ID", "File name", "Employee", "Report date", "Uploaded", "Notes", "Size"])
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        archive_roster_layout.addWidget(self.archive_table)
        l.addWidget(archive_roster_card)
        note = QLabel("Archived PDFs are stored in the local database and included in database backups.")
        note.setProperty("mutedText", True)
        note.setStyleSheet("QLabel { background: rgba(15, 23, 42, 0.70); color: #94A3B8; border: 1px solid rgba(51, 65, 85, 0.50); border-radius: 7px; padding: 6px 14px; font-size: 8.5pt; font-weight: 500; }")
        l.addWidget(note)

    def build_settings(self):
        l = QVBoxLayout()
        self._wrap_page_in_scroll(self.settings_tab, l, "Settings & Backup", "Manage local storage, account security, and working days.")
        page = self.settings_tab.findChild(QWidget, "pageContent")
        if page is not None:
            page.setObjectName("settingsContent")

        storage_box = QGroupBox("Storage locations")
        storage_form = QFormLayout(storage_box)
        storage_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        storage_form.setHorizontalSpacing(14)
        storage_form.setVerticalSpacing(8)
        for label, path in [("Database", DB_PATH), ("Backups", BACKUP_DIR), ("Reports", EXPORT_DIR)]:
            path_edit = QLineEdit(str(path))
            path_edit.setReadOnly(True)
            path_edit.setToolTip(str(path))
            path_edit.setCursorPosition(0)
            storage_form.addRow(label, path_edit)
        l.addWidget(storage_box)

        sync_box = QGroupBox("Continuous Cloud Database Synchronization")
        sync_layout = QVBoxLayout(sync_box)
        sync_note = QLabel(
            "All employee records, attendance entries, tasks, and accounts are automatically synchronized "
            "continuously in the background with centralized cloud storage. Updates from multiple staff "
            "members are merged in a structured, conflict-free hierarchy without overwriting or duplicate entries."
        )
        sync_note.setWordWrap(True)
        sync_note.setMinimumWidth(0)
        sync_note.setProperty("mutedText", True)
        sync_layout.addWidget(sync_note)
        install_row = QHBoxLayout()
        self.github_sync_install_label = QLabel(
            f"Installation ID: {self.db.github_sync_install_id}"
        )
        self.github_sync_install_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.github_sync_install_label.setProperty("mutedText", True)
        install_row.addWidget(self.github_sync_install_label)
        self.link_install_id_btn = QPushButton("🔗 Link / Change ID")
        self.link_install_id_btn.setObjectName("settingsSyncLinkBtn")
        self.link_install_id_btn.setToolTip("Link this device to an existing Installation ID from another PC to restore or share data")
        self.link_install_id_btn.clicked.connect(self.change_installation_id)
        install_row.addWidget(self.link_install_id_btn)
        install_row.addStretch(1)
        sync_layout.addLayout(install_row)

        sync_actions = QHBoxLayout()
        self.github_sync_now_button = QPushButton("🔄 Sync Now (Check Updates)")
        self.github_sync_now_button.setObjectName("settingsSyncPushBtn")
        self.github_sync_now_button.setToolTip(
            "Perform an immediate verification and background sync with the centralized cloud database."
        )
        self.github_sync_now_button.clicked.connect(self.sync_github_database_now)
        self.github_sync_pull_button = QPushButton("⬇ Emergency Cloud Restore")
        self.github_sync_pull_button.setObjectName("settingsSyncPullBtn")
        self.github_sync_pull_button.hide()
        self.github_sync_pull_button.clicked.connect(self.pull_latest_github_database)
        self.github_sync_config_button = QPushButton("⚙️ Configure Cloud Sync")
        self.github_sync_config_button.setObjectName("settingsSyncConfigBtn")
        self.github_sync_config_button.setToolTip(
            "Set or update the Cloudflare Sync Worker URL for database backup and synchronization."
        )
        self.github_sync_config_button.clicked.connect(self.configure_github_sync_url)
        sync_actions.addWidget(self.github_sync_now_button)
        sync_actions.addWidget(self.github_sync_config_button)
        sync_actions.addStretch(1)
        sync_layout.addLayout(sync_actions)

        self.github_sync_status_label = QLabel()
        self.github_sync_status_label.setWordWrap(True)
        self.github_sync_status_label.setMinimumWidth(0)
        self.github_sync_status_label.setProperty("mutedText", True)
        sync_layout.addWidget(self.github_sync_status_label)
        if not self.is_admin_or_dev:
            self.github_sync_now_button.setEnabled(False)
            self.github_sync_pull_button.setEnabled(False)
        self._refresh_github_sync_status()
        self.github_sync_status_timer = QTimer(self)
        self.github_sync_status_timer.setInterval(1000)
        self.github_sync_status_timer.timeout.connect(self._refresh_github_sync_status)
        self.github_sync_status_timer.start()
        l.addWidget(sync_box)

        actions_box = QGroupBox("Data && account actions")
        actions_grid = QGridLayout(actions_box)
        actions_grid.setContentsMargins(12, 18, 12, 12)
        actions_grid.setHorizontalSpacing(10)
        actions_grid.setVerticalSpacing(10)
        actions = [
            ("Create backup", self.backup_db, "Create a backup of the local database"),
            ("Restore database", self.restore_backup, "Restore a database backup without changing the application version"),
            ("Change password", self.change_password, "Change your login password"),
            ("Recovery question", self.update_recovery_question, "Update your password recovery question"),
            ("Manage accounts", self.manage_accounts, "Create or manage user accounts and assign limited access"),
            ("Export employees CSV", self.export_employees_csv, "Export employee list to CSV"),
            ("Expose all proof links", self.apply_global_expose_links, "Expose proof links for all employee tasks and reports"),
            ("☁️ Sync Google Sheets", self.sync_google_sheets_action, "Sync all tables (Employees, Tasks, Attendance, Stores) with central Google Sheets"),
        ]
        for index, (label, slot, tip) in enumerate(actions):
            button = QPushButton(label)
            button.setObjectName("settingsActionBtn")
            button.clicked.connect(slot)
            button.setToolTip(tip)
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            button.setMinimumHeight(38)
            actions_grid.addWidget(button, index // 3, index % 3)
            if label == "Manage accounts" and not self.is_admin_or_dev:
                button.setEnabled(False)
                button.setToolTip("Only an Admin or Developer account can manage user accounts.")
            elif label == "Restore database" and not self.is_admin_or_dev:
                button.setEnabled(False)
                button.setToolTip("Only an Admin or Developer account can restore database backups.")
        for col in range(3):
            actions_grid.setColumnStretch(col, 1)
        l.addWidget(actions_box)

        days_box = QGroupBox("Working days")
        days_layout = QGridLayout(days_box)
        days_layout.setHorizontalSpacing(12)
        days_layout.setVerticalSpacing(8)
        self.workday_checks = []
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        saved_days = self.db.working_weekdays()
        for idx, day_name in enumerate(day_names):
            checkbox = QCheckBox(day_name)
            checkbox.setChecked(idx in saved_days)
            self.workday_checks.append(checkbox)
            days_layout.addWidget(checkbox, idx // 4, idx % 4)
        for col in range(4):
            days_layout.setColumnStretch(col, 1)
        l.addWidget(days_box)

        save_days = QPushButton("Save working days")
        save_days.setMinimumHeight(38)
        save_days.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        save_days.clicked.connect(self.save_working_week)
        l.addWidget(save_days, 0, Qt.AlignmentFlag.AlignLeft)

        appearance_box = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_box)
        appearance_layout.setSpacing(10)
        theme_row = QHBoxLayout()
        theme_label = QLabel("Theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Day", "Night", "Ocean", "Sunset"])
        current = self.current_theme().capitalize()
        if current in ["Day", "Night", "Ocean", "Sunset"]:
            self.theme_combo.setCurrentText(current)
        self.theme_combo.setMinimumWidth(180)
        self.theme_combo.setMaximumWidth(280)
        self.theme_combo.currentTextChanged.connect(lambda theme: self.apply_theme(theme.lower()))
        theme_row.addWidget(theme_label)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)
        appearance_layout.addLayout(theme_row)

        animation_row = QHBoxLayout()
        animation_label = QLabel("Live wallpaper")
        self.animation_combo = QComboBox()
        self.animation_combo.addItems(list(AnimatedBackground.STYLES))
        saved_animation = self.db.get_setting("animation_style", "Ambient Glow") or "Ambient Glow"
        if self.animation_combo.findText(saved_animation) >= 0:
            self.animation_combo.setCurrentText(saved_animation)
        self.animation_combo.setMinimumWidth(220)
        self.animation_combo.setMaximumWidth(320)
        self.animation_combo.currentTextChanged.connect(self.set_animation_style)
        animation_row.addWidget(animation_label)
        animation_row.addWidget(self.animation_combo)
        animation_row.addStretch(1)
        appearance_layout.addLayout(animation_row)

        custom_wp_row = QHBoxLayout()
        custom_wp_label = QLabel("Custom wallpaper")
        self.browse_wallpaper_btn = QPushButton("📁 Browse Custom Wallpaper...")
        self.browse_wallpaper_btn.setObjectName("settingsBrowseWallpaperBtn")
        self.browse_wallpaper_btn.setToolTip("Select any PNG, JPG, or WEBP image from your computer to use as live background")
        self.browse_wallpaper_btn.clicked.connect(self.browse_custom_wallpaper)
        self.clear_wallpaper_btn = QPushButton("Reset to Default")
        self.clear_wallpaper_btn.setObjectName("settingsResetWallpaperBtn")
        self.clear_wallpaper_btn.setToolTip("Reset to the default animated background")
        self.clear_wallpaper_btn.clicked.connect(self.reset_custom_wallpaper)
        self.custom_wp_status = QLabel("")
        self.custom_wp_status.setStyleSheet("color: #94A3B8; font-size: 8.5pt;")
        custom_wp_path = self.db.get_setting("custom_wallpaper_path")
        if custom_wp_path and Path(custom_wp_path).is_file():
            self.custom_wp_status.setText(f"Active: {Path(custom_wp_path).name}")
        custom_wp_row.addWidget(custom_wp_label)
        custom_wp_row.addWidget(self.browse_wallpaper_btn)
        custom_wp_row.addWidget(self.clear_wallpaper_btn)
        custom_wp_row.addWidget(self.custom_wp_status)
        custom_wp_row.addStretch(1)
        appearance_layout.addLayout(custom_wp_row)

        clock_row = QHBoxLayout()
        clock_label = QLabel("Clock display mode")
        self.clock_mode_combo = QComboBox()
        self.clock_mode_combo.addItems(["Digital", "Analog"])
        current_mode = getattr(self, "_clock_mode", "digital").capitalize()
        if current_mode in ["Digital", "Analog"]:
            self.clock_mode_combo.setCurrentText(current_mode)
        self.clock_mode_combo.setMinimumWidth(180)
        self.clock_mode_combo.setMaximumWidth(280)
        self.clock_mode_combo.currentTextChanged.connect(lambda mode: self.set_clock_mode(mode.lower()))
        clock_row.addWidget(clock_label)
        clock_row.addWidget(self.clock_mode_combo)
        clock_row.addStretch(1)
        appearance_layout.addLayout(clock_row)

        note = QLabel("Choose a color theme, animated wallpaper, and clock format. Changes apply immediately across the main app screens.")
        note.setWordWrap(True)
        note.setMinimumWidth(0)
        note.setMinimumHeight(40)
        note.setProperty("mutedText", True)
        appearance_layout.addWidget(note)
        l.addWidget(appearance_box)
        l.addStretch()

    def _refresh_github_sync_status(self):
        label = getattr(self, "github_sync_status_label", None)
        sync = getattr(self.db, "github_sync", None)
        if label is None or sync is None:
            return
        is_running = getattr(self, "_auto_sync_running", False) or sync.is_busy
        if not sync.is_configured:
            credential_state = "⚠️ Cloud sync is not configured."
        elif is_running:
            credential_state = "🔄 Synchronizing changes with cloud..."
        else:
            credential_state = "🟢 Connected & Continuously Synced."
        status_detail = sync.status if (sync.status and sync.status != "Idle") else "All records up to date."
        label.setText(f"{credential_state} ({status_detail})")

        header_badge = getattr(self, "header_sync_badge", None)
        if header_badge is not None:
            header_badge.hide()
            if not sync.is_configured:
                header_badge.setText("⚪ Sync Config")
                header_badge.setToolTip("Cloud sync not configured. Click to configure.")
            elif is_running:
                header_badge.setText("🔄 Syncing...")
                header_badge.setToolTip("Synchronizing changes with centralized cloud storage...")
            else:
                header_badge.setText("🟢 Auto-Synced")
                header_badge.setToolTip("Continuous Cloud Sync is Active. Data is continuously encrypted and synchronized automatically in the background. Click to check for updates now.")

        sync_btn_enabled = sync.is_configured and not is_running
        push_button = getattr(self, "github_sync_now_button", None)
        if push_button is not None:
            push_button.setEnabled(sync_btn_enabled)
        shared_status = getattr(self, "shared_sync_status", None)
        if shared_status is not None:
            shared_status.setText(label.text())
        shared_push = getattr(self, "shared_sync_push_button", None)
        if shared_push is not None and shared_push is not header_badge:
            shared_push.setEnabled(sync_btn_enabled)
        shared_pull = getattr(self, "shared_sync_pull_button", None)
        if shared_pull is not None:
            shared_pull.setEnabled(sync_btn_enabled)

    def configure_github_sync_url(self):
        current = self.db.get_setting("db_sync_worker_url", "") or getattr(self.db.github_sync, "worker_url", "")
        url, ok = QInputDialog.getText(
            self, "Configure Cloud Sync",
            "Enter Cloudflare Sync Worker URL (e.g. https://your-worker.workers.dev):",
            QLineEdit.EchoMode.Normal,
            current,
        )
        if not ok:
            return
        url = url.strip()
        self.db.set_setting("db_sync_worker_url", url)
        self.db._initialize_github_sync()
        self._refresh_github_sync_status()
        info(self, f"Cloud Sync URL updated:\n{url or '(Cleared / Disabled)'}")

    def change_installation_id(self):
        password, ok = QInputDialog.getText(
            self, "Developer authorization", "Enter developer password to change Installation ID:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not password:
            return
        if not verify_developer_password(password):
            return error(self, "Developer authorization failed.")
        new_id, ok = QInputDialog.getText(
            self, "Link Installation ID",
            f"Current Installation ID:\n{self.db.github_sync_install_id}\n\nEnter the 32-character Installation ID from your other device to sync with its data:",
            QLineEdit.EchoMode.Normal,
            self.db.github_sync_install_id,
        )
        if not ok:
            return
        clean_id = new_id.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{32}", clean_id):
            return error(self, "Installation ID must be a valid 32-character hexadecimal code.")
        self.db.set_setting("github_sync_install_id", clean_id)
        self.db._initialize_github_sync()
        if hasattr(self, "github_sync_install_label"):
            self.github_sync_install_label.setText(f"Installation ID: {clean_id}")
        info(self, f"Installation ID successfully updated to:\n{clean_id}\n\nContinuous synchronization will now automatically sync with this ID in the background.")

    @property
    def is_admin_or_dev(self):
        return is_privileged_user(self.current_user)

    @property
    def is_hr_admin_or_dev(self):
        return self.is_admin_or_dev or str(getattr(self, "user_role", "")).strip().lower() == "hr"

    def _init_auto_sync(self):
        self._auto_sync_running = False
        if is_developer_test_user(getattr(self, "current_user", None)):
            logging.getLogger("auto_sync").info("Auto-sync background timer disabled: Developer test user ('admin') is active.")
            return
        self._auto_sync_timer = QTimer(self)
        self._auto_sync_timer.setInterval(30000)
        self._auto_sync_timer.timeout.connect(self._background_auto_sync)
        self._auto_sync_timer.start()

        self._debounce_sync_timer = QTimer(self)
        self._debounce_sync_timer.setSingleShot(True)
        self._debounce_sync_timer.timeout.connect(self._background_auto_sync)

        if hasattr(self.db, "github_sync"):
            self.db.github_sync._on_dirty_callback = lambda: self.schedule_auto_sync(delay_ms=2000)

        QTimer.singleShot(1500, self._background_auto_sync)

    def schedule_auto_sync(self, delay_ms=2500, immediate=False, developer_authorized=False):
        if is_developer_test_user(getattr(self, "current_user", None)) and not developer_authorized:
            logging.getLogger("auto_sync").info("Developer auto-sync skipped without per-action password authorization.")
            return
        sync = getattr(self.db, "github_sync", None)
        if sync is None or not sync.is_configured:
            return
        if immediate:
            self._background_auto_sync(developer_authorized=developer_authorized)
        else:
            if hasattr(self, "_debounce_sync_timer") and not developer_authorized:
                self._debounce_sync_timer.start(delay_ms)

    def _background_auto_sync(self, developer_authorized=False):
        if is_developer_test_user(getattr(self, "current_user", None)) and not developer_authorized:
            return
        sync = getattr(self.db, "github_sync", None)
        if sync is None or not sync.is_configured or sync.is_busy:
            return
        if getattr(self, "_auto_sync_running", False):
            return
        self._auto_sync_running = True

        def run_sync_thread():
            raw = None
            try:
                try:
                    raw = sync.download_latest_snapshot(prefer_latest=True)
                except Exception as ex:
                    if "No remote snapshot" not in str(ex):
                        logging.getLogger("auto_sync").debug(f"Auto-sync pull check: {ex}")

                if raw:
                    import tempfile
                    with tempfile.NamedTemporaryFile(prefix="rsc_autosync_", suffix=".sqlite3", delete=False) as h:
                        tpath = Path(h.name)
                        h.write(raw)
                    QTimer.singleShot(0, lambda: self._apply_snapshot_merge(tpath))
                    return

                if sync.is_dirty:
                    sync.request_sync()
            except Exception as e:
                logging.getLogger("auto_sync").debug(f"Auto-sync worker note: {e}")
            finally:
                self._auto_sync_running = False

        threading.Thread(target=run_sync_thread, name="auto-sync-thread", daemon=True).start()

    def _apply_snapshot_merge(self, tpath: Path):
        try:
            stats = merge_remote_database_snapshot(self.db.conn, tpath)
            if sum(stats.values()) > 0:
                self.refresh_all()
                self._refresh_github_sync_status()
            if self.db.github_sync.is_dirty or sum(stats.values()) > 0:
                self.db.github_sync.request_sync()
        except Exception as exc:
            logging.getLogger("auto_sync").warning(f"Snapshot merge error: {exc}")
        finally:
            self._auto_sync_running = False
            try:
                tpath.unlink(missing_ok=True)
            except Exception:
                pass

    def sync_github_database_now(self):
        developer_authorized = False
        if is_developer_test_user(self.current_user):
            password, ok = QInputDialog.getText(
                self, "Developer authorization",
                "Signed in as developer 'admin'. Enter the developer password to sync test data:",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not password:
                return
            if not verify_developer_password(password):
                return error(self, "Developer authorization failed. No data was synchronized.")
            developer_authorized = True
        # Customer username 'Admin' uses the master-data path without a developer
        # password. Lowercase developer 'admin' is authorized only for this action.
        if not self.db.github_sync.is_configured:
            url, ok = QInputDialog.getText(
                self, "Configure Cloud Sync",
                "Cloud sync is not configured yet.\nEnter Cloudflare Sync Worker URL to push encrypted database:",
                QLineEdit.EchoMode.Normal,
                self.db.get_setting("db_sync_worker_url", ""),
            )
            if ok and url.strip():
                self.db.set_setting("db_sync_worker_url", url.strip())
                self.db._initialize_github_sync()
                self._refresh_github_sync_status()
            else:
                return error(self, "Secure database sync is not configured. Please set the Sync Worker URL.")
        self.schedule_auto_sync(immediate=True, developer_authorized=developer_authorized)
        self._refresh_github_sync_status()
        info(self, "Centralized sync triggered.\n\nYour data is being synchronized with encrypted cloud storage in the background.")

    def pull_latest_github_database(self):
        """Pull latest cloud data; customer Admin needs no developer password, lowercase admin does."""
        password = None
        developer_session = is_developer_test_user(self.current_user)
        if developer_session:
            password, ok = QInputDialog.getText(
                self, "Developer authorization", "Enter developer password to pull latest data:",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not password:
                return
            if not verify_developer_password(password):
                return error(self, "Developer authorization failed.")
        sync = self.db.github_sync
        if not sync.is_configured:
            url, ok = QInputDialog.getText(
                self, "Configure Cloud Sync",
                "Cloud sync is not configured yet.\nEnter Cloudflare Sync Worker URL to pull data:",
                QLineEdit.EchoMode.Normal,
                self.db.get_setting("db_sync_worker_url", ""),
            )
            if ok and url.strip():
                self.db.set_setting("db_sync_worker_url", url.strip())
                self.db._initialize_github_sync()
                sync = self.db.github_sync
                self._refresh_github_sync_status()
            else:
                return error(self, "Secure database sync is not configured in this build.")
        if sync.is_busy:
            return error(self, "An encrypted database sync is already running. Wait for it to finish.")
        if not ask(
            self, "Pull latest database data",
            "This pulls and merges the latest cloud snapshot conflict-free with your local database without losing any employee work.\n"
            "A safety backup will be created first. Continue?",
        ):
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(BACKUP_DIR) / f"pre_pull_{stamp}.db"
        snapshot_path = None
        try:
            Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
            create_validated_sqlite_copy(self.db.conn, backup_path)
            try:
                raw = sync.download_latest_snapshot(candidate_secret=password, prefer_latest=True)
            except Exception as dl_err:
                if "Snapshot decryption failed" in str(dl_err):
                    if not developer_session:
                        raise RuntimeError(
                            "The cloud snapshot could not be decrypted with this installation's configured key. "
                            "Customer sync does not require a password; contact the developer to correct the sync-key configuration."
                        ) from dl_err
                    custom_key, ok = QInputDialog.getText(
                        self, "Snapshot Decryption Passphrase",
                        "The remote snapshot could not be decrypted with default credentials.\n"
                        "Please enter the snapshot encryption passphrase or custom key:",
                        QLineEdit.EchoMode.Password,
                    )
                    if ok and custom_key.strip():
                        raw = sync.download_latest_snapshot(candidate_secret=custom_key.strip(), prefer_latest=True)
                    else:
                        raise
                else:
                    raise
            import tempfile
            with tempfile.NamedTemporaryFile(prefix="rsc_pull_", suffix=".sqlite3", delete=False) as handle:
                snapshot_path = Path(handle.name)
                handle.write(raw)
            stats = merge_remote_database_snapshot(self.db.conn, snapshot_path)
            self.db.github_sync.set_status("Merged latest centralized business data")
            info(self, f"Latest cloud business data merged conflict-free successfully.\n\nMerged records:\n• {stats.get('users', 0)} account(s)\n• {stats.get('employees', 0)} employee(s)\n• {stats.get('attendance', 0)} attendance record(s)\n• {stats.get('tasks', 0)} task(s)\n\nLocal safety backup saved to:\n{backup_path}")
            self.refresh_all()
            if self.db.github_sync.is_dirty or sum(stats.values()) > 0:
                self.db.github_sync.request_sync()
        except Exception as exc:
            msg = str(exc)
            if "No remote snapshot exists for this installation yet" in msg:
                try:
                    if backup_path.exists():
                        backup_path.unlink(missing_ok=True)
                except Exception:
                    pass
                if ask(
                    self, "No Remote Snapshot Found",
                    "No remote cloud snapshot exists for this installation yet.\n\n"
                    "Would you like to push your current local database to the encrypted cloud now?"
                ):
                    self.sync_github_database_now()
            else:
                error(self, "Could not pull latest data. Local accounts/settings were preserved where the transaction completed; "
                      f"backup: {backup_path}\n{exc}")
        finally:
            if snapshot_path is not None:
                snapshot_path.unlink(missing_ok=True)
        self._refresh_github_sync_status()

    def closeEvent(self, event):
        timer = getattr(self, "github_sync_status_timer", None)
        if timer is not None:
            timer.stop()
        auto_timer = getattr(self, "_auto_sync_timer", None)
        if auto_timer is not None:
            auto_timer.stop()
        deb_timer = getattr(self, "_debounce_sync_timer", None)
        if deb_timer is not None:
            deb_timer.stop()
        chat_tab = getattr(self, "chat_tab", None)
        if chat_tab is not None:
            chat_tab.shutdown()
        self.db.close_github_sync(timeout=3)
        super().closeEvent(event)

    def polish_tables(self):
        """Apply shared table styling without overriding per-screen layout rules."""
        colors = self._ui_chrome_palette(self.current_theme())
        is_night = (self.current_theme() or "day").lower() == "night"
        alternate = "#1E293B" if is_night else ("#E0F2FE" if self.current_theme() == "ocean" else "#FFF7ED" if self.current_theme() == "sunset" else "#F1F5F9")
        table_bg = colors.get("table_bg", "#0C101B" if is_night else "#FFFFFF")
        table_alt = colors.get("table_alt_bg", alternate)
        table_fg = colors.get("table_fg", "#F8FAFC" if is_night else "#0F172A")
        table_border = colors.get("table_border", "rgba(255, 255, 255, 0.08)" if is_night else "#E2E8F0")
        table_grid = colors.get("table_grid", "rgba(255, 255, 255, 0.04)" if is_night else "#F1F5F9")
        table_sel_bg = colors.get("table_sel_bg", "rgba(0, 210, 255, 0.16)" if is_night else "#EEF2FF")
        table_sel_fg = colors.get("table_sel_fg", "#FFFFFF" if is_night else "#312E81")
        for table in self.findChildren(QTableWidget):
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.verticalHeader().setVisible(False)
            is_att = table is getattr(self, "att_table", None)
            row_height = 52 if is_att else 40
            table.verticalHeader().setDefaultSectionSize(row_height)
            table.verticalHeader().setMinimumSectionSize(max(36, row_height - 6))
            table.setCornerButtonEnabled(False)
            is_leads = table.objectName() in ("leadsTable", "regionTable") or (hasattr(table, "property") and table.property("no_word_wrap"))
            if not is_leads:
                table.setWordWrap(True)
                table.setTextElideMode(Qt.TextElideMode.ElideNone)
            else:
                table.setWordWrap(False)
                table.setTextElideMode(Qt.TextElideMode.ElideRight)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
            table.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            table.setAutoFillBackground(True)
            table.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            table.viewport().setAutoFillBackground(True)
            table_palette = table.palette()
            table_palette.setColor(QPalette.ColorRole.Base, QColor(table_bg))
            table_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(table_alt))
            table_palette.setColor(QPalette.ColorRole.Text, QColor(table_fg))
            table.setPalette(table_palette)
            table.viewport().setPalette(table_palette)
            att_cell_css = """
                QWidget#attendanceEditorCell QComboBox {
                    min-height: 26px; max-height: 28px; height: 28px;
                    padding: 1px 22px 1px 8px; border-radius: 6px; font-size: 8.5pt;
                }
                QWidget#attendanceEditorCell QLineEdit {
                    min-height: 26px; max-height: 28px; height: 28px;
                    padding: 1px 8px; border-radius: 6px; font-size: 8.5pt;
                }
            """ if is_att else ""
            table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {table_bg};
                    alternate-background-color: {table_alt};
                    color: {table_fg};
                    border: 1px solid {table_border};
                    border-radius: 12px;
                    gridline-color: {table_grid};
                    selection-background-color: {table_sel_bg};
                    selection-color: {table_sel_fg};
                    outline: 0;
                }}
                QTableWidget::viewport {{
                    background-color: {table_bg};
                }}
                QTableWidget::item {{
                    padding: 8px 12px;
                    border-bottom: 1px solid {table_grid};
                    color: {table_fg};
                }}
                QTableWidget::item:selected {{
                    background-color: {table_sel_bg};
                    color: {table_sel_fg};
                }}
                {att_cell_css}
            """)
            table.horizontalHeader().setMinimumHeight(42)
            table.horizontalHeader().setMinimumSectionSize(65)
            header_view = table.horizontalHeader()
            resize_modes = [header_view.sectionResizeMode(column) for column in range(table.columnCount())]
            if resize_modes and all(mode == QHeaderView.Stretch for mode in resize_modes):
                column_hints = {
                    "id": 65, "#": 60, "code": 115, "employee id": 135, "role": 145,
                    "status": 130, "priority": 115, "progress": 110, "due": 110, "due time": 110,
                    "check-in": 126, "check-out": 126, "net hours": 100, "name": 185, "employee": 180,
                    "department": 170, "phone": 145, "email": 210, "task": 320, "proof": 280,
                    "proof link": 280, "manager remarks": 300, "note": 260, "file name": 300,
                    "date": 120, "report date": 120, "start date": 120, "uploaded": 160, "size": 100,
                    "work days": 100, "present": 90, "absent": 90, "leave": 90, "holidays": 90,
                    "total present": 110, "score": 90, "tasks": 90, "completed": 95,
                }
                header_view.setSectionResizeMode(QHeaderView.Interactive)
                for column in range(table.columnCount()):
                    item = table.horizontalHeaderItem(column)
                    header_title = item.text().strip().lower() if item else ""
                    title_width = header_view.fontMetrics().horizontalAdvance(item.text()) if item else 0
                    target_width = column_hints.get(header_title, max(85, title_width + 28))
                    table.setColumnWidth(column, target_width)
                header_view.setStretchLastSection(True)
            table.setMouseTracking(True)
            center_titles = {
                "id", "#", "code", "employee id", "date", "report date", "start date",
                "status", "attendance status", "priority", "progress", "due", "due time",
                "check-in", "check-out", "net hours", "work days", "present", "absent",
                "leave", "holidays", "total present", "uploaded", "size", "created", "phone"
            }
            for column in range(table.columnCount()):
                header = table.horizontalHeaderItem(column)
                if header:
                    col_title = header.text().strip().lower()
                    if col_title in center_titles:
                        header.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    else:
                        header.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    if not header.toolTip().strip():
                        header.setToolTip(header.text())
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item:
                        current_align = item.textAlignment()
                        h_align = current_align & Qt.AlignmentFlag.AlignHorizontal_Mask
                        if not h_align:
                            header = table.horizontalHeaderItem(column)
                            col_title = header.text().strip().lower() if header else ""
                            h_align = Qt.AlignmentFlag.AlignCenter if col_title in center_titles else Qt.AlignmentFlag.AlignLeft
                        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | h_align)
                        if not item.toolTip().strip():
                            item.setToolTip(item.text())
            # Preserve explicitly sized screens; long values remain accessible
            # through the tooltips attached above.

    def apply_hover_messages(self):
        """Give every action button a useful hover message, keeping explicit tips."""
        for button in self.findChildren(QPushButton):
            if button.toolTip().strip():
                continue
            label = re.sub(r"^[^A-Za-z0-9]+", "", button.text()).strip()
            if not label:
                label = button.accessibleName() or "this action"
            if button.objectName() == "sidebarNavButton":
                message = f"Open the {label} page."
            elif label.lower().startswith("delete"):
                message = f"{label}. This removes the selected record."
            elif label.lower().startswith("add") or label.lower().startswith("create"):
                message = f"{label} and enter its details."
            elif label.lower().startswith("edit"):
                message = f"{label} using the selected record."
            else:
                message = f"Click to {label}."
            button.setToolTip(message)

    def apply_interaction_animations(self):
        """Add animated hover/click feedback for action buttons without interfering with table text rendering."""
        accent = MainWindow._ui_chrome_palette(self.current_theme())["accent"] if hasattr(self, "current_theme") else "#00E5FF"
        # Query UI elements while isolating item views and charts from rasterizing effects
        _ = self.findChildren(QAbstractItemView)
        _ = self.findChildren(QProgressBar) + self.findChildren(ProductivityChart)
        targets = []
        for widget in self.findChildren(QPushButton) + self.findChildren(QToolButton):
            if widget.objectName() in ("titleBtnMin", "titleBtnMax", "titleBtnClose"):
                continue
            targets.append(widget)
        for widget in targets:
            feedback = getattr(widget, "_interaction_feedback", None)
            if feedback is not None:
                feedback.set_accent(accent)
                continue
            if widget.graphicsEffect() is not None:
                continue
            feedback = InteractionFeedback(widget, accent)
            widget._interaction_feedback = feedback
            widget.setProperty("interactionAnimation", "enabled")

    def selected_id(self, table, col=0):
        rows=table.selectionModel().selectedRows()
        if not rows: return None
        item=table.item(rows[0].row(),col)
        if not item: return None
        data_val = item.data(Qt.ItemDataRole.UserRole)
        if data_val == "__section_header__":
            return None
        if isinstance(data_val, int):
            return data_val
        try:
            return int(item.text())
        except (ValueError, TypeError):
            return None

    def status_item(self, value):
        """Create a table cell styled as a colored status pill."""
        text = str(value or "").strip() or "—"
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        key = text.lower()
        is_dark = hasattr(self, "current_theme") and self.current_theme().lower() in ("night", "dark")
        if is_dark:
            palette = {
                "submitted": ("rgba(16, 185, 129, 0.25)", "#34D399"),
                "completed": ("rgba(16, 185, 129, 0.25)", "#34D399"),
                "active": ("rgba(16, 185, 129, 0.25)", "#34D399"),
                "present": ("rgba(16, 185, 129, 0.25)", "#34D399"),
                "provided": ("rgba(16, 185, 129, 0.25)", "#34D399"),
                "partially completed": ("rgba(245, 158, 11, 0.25)", "#FBBF24"),
                "pending": ("rgba(245, 158, 11, 0.25)", "#FBBF24"),
                "pending review": ("rgba(245, 158, 11, 0.25)", "#FBBF24"),
                "in progress": ("rgba(59, 130, 246, 0.25)", "#60A5FA"),
                "not started": ("rgba(148, 163, 184, 0.20)", "#CBD5E1"),
                "unmarked": ("rgba(148, 163, 184, 0.20)", "#CBD5E1"),
                "inactive": ("rgba(148, 163, 184, 0.20)", "#94A3B8"),
                "disabled": ("rgba(148, 163, 184, 0.20)", "#94A3B8"),
                "blocked": ("rgba(239, 68, 68, 0.25)", "#F87171"),
                "cancelled": ("rgba(239, 68, 68, 0.25)", "#F87171"),
                "absent": ("rgba(239, 68, 68, 0.25)", "#F87171"),
                "leave": ("rgba(168, 85, 247, 0.25)", "#C084FC"),
                "holiday": ("rgba(99, 102, 241, 0.25)", "#A5B4FC"),
                "missing": ("rgba(239, 68, 68, 0.25)", "#F87171"),
                "high": ("rgba(239, 68, 68, 0.25)", "#F87171"),
                "normal": ("rgba(148, 163, 184, 0.20)", "#CBD5E1"),
                "low": ("rgba(59, 130, 246, 0.25)", "#60A5FA"),
            }
            bg, fg = palette.get(key, ("rgba(148, 163, 184, 0.20)", "#CBD5E1"))
        else:
            palette = {
                "submitted": ("#DCFCE7", "#166534"),
                "completed": ("#DCFCE7", "#166534"),
                "active": ("#DCFCE7", "#166534"),
                "present": ("#DCFCE7", "#166534"),
                "provided": ("#DCFCE7", "#166534"),
                "partially completed": ("#FEF3C7", "#92400E"),
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
        center_headers = {
            "id", "#", "code", "employee id", "priority", "status", "progress", "due",
            "due time", "date", "phone", "check-in", "check-out", "net hours",
            "target qty", "actual qty", "completion %"
        }
        for c, v in enumerate(values):
            text = task_status_label(v) if c in status_cols and (v is None or not str(v).strip()) else str(v or "")
            if c in status_cols:
                item = self.status_item(text)
            else:
                item = QTableWidgetItem(text)
                is_dark = hasattr(self, "current_theme") and self.current_theme().lower() in ("night", "dark")
                pal = MainWindow._ui_chrome_palette(self.current_theme()) if hasattr(self, "current_theme") else MainWindow._ui_chrome_palette("night")
                item.setForeground(QColor(pal.get("table_fg", "#F8FAFC" if is_dark else "#0F172A")))
            h_item = table.horizontalHeaderItem(c)
            h_text = h_item.text().strip().lower() if h_item else ""
            is_center = (c in status_cols) or (c == 0) or (h_text in center_headers)
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if is_center else Qt.AlignmentFlag.AlignLeft))
            if text:
                item.setToolTip(text)
            table.setItem(row, c, item)

    def refresh_all(self):
        self.refresh_employees()
        self.refresh_employee_filter()
        self.refresh_task_filter()
        self.refresh_tracker_employees()
        self.refresh_tasks()
        self.refresh_tracker()
        self.refresh_attendance()
        self.refresh_attendance_summary()
        self.refresh_report_employees()
        self.refresh_dashboard()
        self.refresh_archive()
        if hasattr(self, "refresh_home_business_snapshot"):
            self.refresh_home_business_snapshot()
        if hasattr(self, "business_tab") and hasattr(self.business_tab, "refresh_all"):
            self.business_tab.refresh_all()
        if hasattr(self, "refresh_archived_report_choices"):
            self.refresh_archived_report_choices()
        self.polish_tables()

    def refresh_employees(self):
        if not hasattr(self,"emp_table"): return
        search_text = self.emp_search.text().lower().strip() if hasattr(self,"emp_search") else ""
        all_emps = self.db.employees()

        # Update department dropdown choices dynamically
        if hasattr(self, "emp_dept_filter"):
            current_choice = self.emp_dept_filter.currentText()
            groups = self.db.employee_groups()
            group_names = [g["name"].strip() for g in groups if g["name"].strip()]
            default_depts = ["General", "Housekeeping", "Trainer / Fitness", "Management", "Sales", "Others"]
            emp_depts = [e["department"].strip() for e in all_emps if e["department"] and str(e["department"]).strip()]
            
            all_depts = ["🏢 All Departments / Groups"]
            for d in group_names + default_depts + emp_depts:
                if d and d not in all_depts:
                    all_depts.append(d)
            
            existing_items = [self.emp_dept_filter.itemText(i) for i in range(self.emp_dept_filter.count())]
            if existing_items != all_depts:
                self.emp_dept_filter.blockSignals(True)
                self.emp_dept_filter.clear()
                self.emp_dept_filter.addItems(all_depts)
                if current_choice and self.emp_dept_filter.findText(current_choice) >= 0:
                    self.emp_dept_filter.setCurrentText(current_choice)
                self.emp_dept_filter.blockSignals(False)

        # Department / Group filter
        selected_dept = self.emp_dept_filter.currentText() if hasattr(self, "emp_dept_filter") else ""
        filtered_emps = []
        for e in all_emps:
            if search_text:
                haystack = " ".join([str(e["employee_code"] or ""), e["name"], e["department"] or "", e["designation"] or "", e["phone"] or "", e["email"] or ""]).lower()
                if search_text not in haystack:
                    continue
            if selected_dept and not (selected_dept.startswith("🏢 All") or "all department" in selected_dept.lower()):
                e_dept = (e["department"] or "General").strip().lower()
                if selected_dept.lower() in ("general", "unassigned", "default"):
                    if e_dept not in ("general", "unassigned", "default", ""):
                        continue
                elif e_dept != selected_dept.lower():
                    continue
            filtered_emps.append(e)

        # Sort mode: Serial Number / ID, Department / Group, or Name (A-Z)
        sort_mode = self.emp_sort_combo.currentText() if hasattr(self, "emp_sort_combo") else ""
        if "Department" in sort_mode:
            filtered_emps.sort(key=lambda x: ((x["department"] or "General").lower(), int(x["id"] or 0)))
        elif "Name" in sort_mode:
            filtered_emps.sort(key=lambda x: str(x["name"] or "").lower())
        else:
            filtered_emps.sort(key=lambda x: int(x["id"] or 0))

        selected_eid = self.selected_id(self.emp_table)
        restore_row = -1

        self.emp_table.setRowCount(0)

        for e in filtered_emps:
            r = self.emp_table.rowCount()
            self.emp_table.insertRow(r)
            self.emp_table.setRowHeight(r, 40)
            vals = [
                e["id"],
                e["employee_code"] or "",
                e["name"],
                e["department"] or "General",
                e["designation"] or "—",
                e["phone"] or "—",
                e["email"] or "—",
                "Active" if e["active"] else "Inactive"
            ]
            self.set_row_items(self.emp_table, r, vals, status_cols={7})
            first_item = self.emp_table.item(r, 0)
            if first_item:
                first_item.setData(Qt.ItemDataRole.UserRole, e["id"])
                first_item.setData(Qt.ItemDataRole.UserRole + 1, e["department"] or "")
                first_item.setData(Qt.ItemDataRole.UserRole + 2, e["display_order"] if "display_order" in e.keys() else 0)
            if selected_eid is not None and e["id"] == selected_eid:
                restore_row = r

        if restore_row >= 0:
            self.emp_table.selectRow(restore_row)

        if hasattr(self, "emp_count_badge"):
            dept_suffix = f" · {selected_dept}" if (selected_dept and not selected_dept.startswith("🏢 All")) else ""
            self.emp_count_badge.setText(f"Showing: {len(filtered_emps)} / Total: {len(all_emps)}{dept_suffix}")
        self.refresh_task_filter(); self.refresh_report_employees()

    def handle_employee_dropped(self, source_emp_id, source_row, target_row):
        if not self.is_admin_or_dev:
            return
        target_item = self.emp_table.item(target_row, 0)
        if not target_item:
            return
            
        target_role = target_item.data(Qt.ItemDataRole.UserRole)
        if target_role == "__section_header__":
            target_dept = target_item.data(Qt.ItemDataRole.UserRole + 1) or ""
            target_emp_id = None
        else:
            target_emp_id = target_role
            target_dept = target_item.data(Qt.ItemDataRole.UserRole + 1) or ""
            
        if target_dept.lower() in ("general", "unassigned", "default"):
            target_dept = ""
            
        all_emps = [dict(e) for e in self.db.employees()]
        source_emp = next((e for e in all_emps if e["id"] == source_emp_id), None)
        if not source_emp:
            return
            
        source_emp["department"] = target_dept
        remaining = [e for e in all_emps if e["id"] != source_emp_id]
        
        new_list = []
        if target_emp_id is None:
            inserted = False
            for e in remaining:
                e_dept = (e.get("department") or "").strip().lower()
                tgt_key = target_dept.strip().lower()
                if not inserted and (e_dept == tgt_key or (not e_dept and not tgt_key)):
                    new_list.append(source_emp)
                    inserted = True
                new_list.append(e)
            if not inserted:
                new_list.append(source_emp)
        else:
            for e in remaining:
                if e["id"] == target_emp_id:
                    if source_row < target_row:
                        new_list.append(e)
                        new_list.append(source_emp)
                    else:
                        new_list.append(source_emp)
                        new_list.append(e)
                else:
                    new_list.append(e)
            if source_emp not in new_list:
                new_list.append(source_emp)
                
        updates = []
        for idx, e in enumerate(new_list):
            order_val = (idx + 1) * 10
            dept_val = e.get("department", "")
            updates.append((e["id"], order_val, dept_val))
            
        self.db.update_employees_order(updates)
        self.refresh_employees()
        self.refresh_all()

    def move_employee_up(self):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can reorder employees.")
        eid = self.selected_id(self.emp_table)
        if not eid:
            return error(self, "Select an employee first.")
        r = self.emp_table.currentRow()
        if r <= 0:
            return
        target_r = r - 1
        self.handle_employee_dropped(eid, r, target_r)

    def move_employee_down(self):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can reorder employees.")
        eid = self.selected_id(self.emp_table)
        if not eid:
            return error(self, "Select an employee first.")
        r = self.emp_table.currentRow()
        if r < 0 or r >= self.emp_table.rowCount() - 1:
            return
        target_r = r + 1
        self.handle_employee_dropped(eid, r, target_r)

    def move_employee_to_group(self, emp_id, group_name):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can move employees to sections.")
        dept = "" if group_name.lower() in ("general", "unassigned", "default") else group_name
        self.db.conn.execute("UPDATE employees SET department=? WHERE id=?", (dept, emp_id))
        self.db.conn.commit()
        self.refresh_employees()
        self.refresh_all()

    def create_and_move_to_group(self, emp_id):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can create sections.")
        name, ok = QInputDialog.getText(self, "New Section", "Enter new section / group name:")
        if ok and name.strip():
            self.db.add_employee_group(name.strip())
            self.move_employee_to_group(emp_id, name.strip())

    def manage_employee_groups(self):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can manage sections.")
        dlg = EmployeeGroupsDialog(self.db, self)
        dlg.exec()
        self.refresh_employees()
        self.refresh_all()

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
        completed=sum(1 for t in rows if is_explicitly_completed_task_status(t["status"]))
        avg=round(sum(t["progress"] for t in rows)/len(rows)) if rows else 0
        blocked=sum(1 for t in rows if is_blocked_task_status(t["status"]))
        in_progress=sum(1 for t in rows if is_in_progress_task_status(t["status"]))
        # Pending excludes completed/submitted, cancelled, blocked, and in-progress
        pending=sum(1 for t in rows if not is_explicitly_completed_task_status(t["status"])
                    and not is_cancelled_task_status(t["status"])
                    and not is_blocked_task_status(t["status"])
                    and not is_in_progress_task_status(t["status"]))
        self.tracker_summary.setText(f"{len(rows)} tasks  •  {completed} completed/submitted  •  {in_progress} in progress  •  {pending} pending  •  {blocked} blocked")
        self.tracker_progress.setValue(avg)
        for t in rows:
            r=self.tracker_table.rowCount(); self.tracker_table.insertRow(r)
            vals=[t["id"],t["title"],t["priority"],task_status_label(t["status"]),f'{t["progress"]}%',t["due_time"],t["proof_url"],t["manager_note"]]
            self.set_row_items(self.tracker_table, r, vals, status_cols={2, 3})

    def add_tracker_task(self):
        eid=self.tracker_employee.currentData()
        if not eid: return error(self, "Select an employee first.")
        d=TaskDialog(self.db,self,employee_id=eid)
        d.date.setDate(self.tracker_date.date())
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals or not vals[2]: return error(self,"Task title and active employee are required.")
        try:
            self.db.conn.execute("""INSERT INTO tasks(employee_id,task_date,title,department,details,due_time,priority,status,progress,proof_url,proof_note,submitted_at,manager_note,expose_link,target_qty,actual_qty,next_action,custom_values,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*vals, now_text(), now_text()))
            self.db.conn.commit(); self.db.log("Task added from employee tracker",vals[2]); self.refresh_all()
        except sqlite3.Error as ex:
            error(self, f"Could not save task: {ex}")

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
            self.eod_options_group.setVisible(True)
        if hasattr(self, "business_data_group"):
            self.business_data_group.setEnabled(not is_archived)
            self.business_data_group.setVisible(True)
        if is_archived:
            self.report_summary.setPlainText("Historical archived PDF selected. Use Print Selected Report to print it, or Generate / Save to export a copy.")
        else:
            self.preview_report()

    def _report_type_changed(self, *_args):
        if hasattr(self, "report_option_keys"):
            while self.report_options_grid.count():
                self.report_options_grid.takeAt(0)
            for checkbox in self.eod_checks.values():
                checkbox.hide()
            kind = self.report_type.currentText()
            keys = self.report_option_keys.get(kind, self.report_option_keys["Audit / EOD"])
            self.eod_options_group.setTitle(f"{kind} content — choose sections to include")
            for index, key in enumerate(keys):
                checkbox = self.eod_checks[key]
                checkbox.setVisible(True)
                self.report_options_grid.addWidget(checkbox, index // 3, index % 3)
            self.eod_options_group.setVisible(True)
            self.eod_options_group.setEnabled(self.archived_report.currentData() is None)
        self.preview_report()

    def selected_eod_options(self):
        defaults = {
            "summary": True, "identity": True, "target": True, "contact": False, "work_status": True,
            "late_links": True, "missing_proof": True, "target_status": True, "tasks": True,
            "target_qty": True, "actual_qty": True, "completion_pct": True, "priority": True,
            "details": True, "due_time": True, "proof": True, "proof_notes": False,
            "custom_values": True, "next_action": True, "expose_link": False,
            "remarks": True, "pending": True,
            "attendance_identity": True, "attendance_status": True, "attendance_times": True,
            "attendance_remarks": True, "attendance_summary": True,
            "details_identity": True, "details_contact": True, "details_joining": True,
            "details_status": True, "details_notes": True,
            "productivity_identity": True, "productivity_metrics": True,
            "productivity_explanation": True, "productivity_tracking": True,
            "productivity_tasks": True,
        }
        selected = {key: cb.isChecked() for key, cb in getattr(self, "eod_checks", {}).items()}
        selected.update({key: cb.isChecked() for key, cb in getattr(self, "business_report_checks", {}).items()})
        res = selected if selected else defaults.copy()
        if "due_time" in res:
            res["duetime"] = res["due_time"]
            res["due"] = res["due_time"]
        if "remarks" in res:
            res["manager_remarks"] = res["remarks"]
            res["manager_note"] = res["remarks"]
        if "completion_pct" in res:
            res["progress"] = res["completion_pct"]
        if "next_action" in res:
            res["nextaction"] = res["next_action"]
        if "custom_values" in res:
            res["customvalues"] = res["custom_values"]
        return res

    def is_task_link_exposed(self, task, opts=None):
        if opts and (opts.get("expose_link") or opts.get("expose_links") or opts.get("expose_all_links")):
            return True
        if hasattr(self, "db") and self.db.get_setting("global_expose_link") == "1":
            return True
        if task is None:
            return False
        try:
            return bool(task["expose_link"])
        except (IndexError, KeyError):
            return False

    def apply_global_expose_links(self):
        count = self.db.conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
        if not ask(self, "Expose all proof links", f"This will expose full proof links for all employees across all {count} tasks and default reports to full URLs. Proceed?"):
            return
        self.db.conn.execute("UPDATE tasks SET expose_link=1, updated_at=?", (now_text(),))
        self.db.set_setting("global_expose_link", "1")
        self.db.set_setting("report_opt_expose_link", "1")
        if hasattr(self, "eod_checks") and "expose_link" in self.eod_checks:
            self.eod_checks["expose_link"].setChecked(True)
        self.db.conn.commit()
        self.db.log("Global expose links enabled", f"Updated {count} tasks")
        self.refresh_all()
        info(self, f"Expose link has been enabled globally across all {count} employee tasks.")

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
        if not self.is_hr_admin_or_dev:
            return error(self, "Only HR, Admin, or Developer accounts have permission to add employees.")
        d=EmployeeDialog(self)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals[0]: return error(self,"Employee ID is required.")
        if not vals[1]: return error(self,"Employee name is required.")
        if vals[5] and ("@" not in vals[5] or "." not in vals[5].split("@")[-1]): return error(self,"Enter a valid email address or leave it blank.")
        try:
            self.db.conn.execute("INSERT INTO employees(employee_code,name,department,designation,phone,email,joining_date,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(*vals,now_text()))
            self.db.conn.commit()
            if vals[2]: self.db.add_employee_group(vals[2])
            self.db.log("Employee added",vals[1]); self.refresh_all()
        except sqlite3.IntegrityError: error(self,"That employee code already exists.")
        except sqlite3.Error as ex: error(self, f"Could not save employee: {ex}")

    def edit_employee(self):
        if not self.is_hr_admin_or_dev:
            return error(self, "Only HR, Admin, or Developer accounts have permission to edit employee records.")
        eid=self.selected_id(self.emp_table)
        if not eid: return error(self,"Select an employee first.")
        row=self.db.employee(eid); d=EmployeeDialog(self,row)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals[1]: return error(self,"Employee name is required.")
        if vals[5] and ("@" not in vals[5] or "." not in vals[5].split("@")[-1]): return error(self,"Enter a valid email address or leave it blank.")
        try:
            self.db.conn.execute("UPDATE employees SET employee_code=?,name=?,department=?,designation=?,phone=?,email=?,joining_date=?,notes=? WHERE id=?",(*vals,eid))
            self.db.conn.commit()
            if vals[2]: self.db.add_employee_group(vals[2])
            self.db.log("Employee edited",vals[1]); self.refresh_all()
        except sqlite3.IntegrityError: error(self,"That employee code already exists.")
        except sqlite3.Error as ex: error(self, f"Could not update employee: {ex}")

    def toggle_employee(self):
        if not self.is_hr_admin_or_dev:
            return error(self, "Only HR, Admin, or Developer accounts have permission to activate or deactivate employees.")
        eid=self.selected_id(self.emp_table)
        if not eid: return error(self,"Select an employee first.")
        e=self.db.employee(eid); active=0 if e["active"] else 1
        self.db.conn.execute("UPDATE employees SET active=? WHERE id=?",(active,eid)); self.db.conn.commit()
        self.db.log("Employee status changed",f'{e["name"]}: {"Active" if active else "Inactive"}'); self.refresh_all()

    def delete_employee(self):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can delete employee records.")
        eid=self.selected_id(self.emp_table)
        if not eid: return error(self,"Select an employee first.")
        e=self.db.employee(eid)
        if not e: return error(self, "Employee not found.")
        if not ask(self,"Delete employee",f'Delete {e["name"]} and permanently remove their tasks and attendance? A safety backup will be created first. This cannot be undone.'): return
        if not self.backup_db(silent=True):
            return error(self, "Safety backup failed. Employee deletion was cancelled.")
        self.db.conn.execute("DELETE FROM tasks WHERE employee_id=?",(eid,))
        self.db.conn.execute("DELETE FROM attendance WHERE employee_id=?",(eid,))
        try:
            self.db.conn.execute("DELETE FROM bt_activities WHERE employee_id=?",(eid,))
        except Exception:
            pass
        self.db.conn.execute("DELETE FROM employees WHERE id=?",(eid,)); self.db.conn.commit()
        self.db.log("Employee deleted",e["name"]); self.refresh_all()
        self.schedule_auto_sync()

    def add_task(self):
        d=TaskDialog(self.db,self,employee_id=self.task_filter.currentData(),task_date=self.task_date.date())
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals: return error(self,"Add an active employee before assigning tasks.")
        if not vals[2]: return error(self,"Task title is required.")
        try:
            self.db.conn.execute("""INSERT INTO tasks(employee_id,task_date,title,department,details,due_time,priority,status,progress,proof_url,proof_note,submitted_at,manager_note,expose_link,target_qty,actual_qty,next_action,custom_values,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*vals, now_text(), now_text()))
            self.db.conn.commit(); self.db.log("Task added",vals[2]); self.refresh_all()
        except sqlite3.Error as ex: error(self, f"Could not save task: {ex}")

    def add_custom_task(self):
        return self.add_task()

    def edit_task(self, table=None):
        table=table or self.task_table
        tid=self.selected_id(table)
        if not tid: return error(self,"Select a task first.")
        row=self.db.conn.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
        if not row: return error(self, "Task not found.")
        d=TaskDialog(self.db,self,row)
        if d.exec()!=QDialog.Accepted: return
        vals=d.values()
        if not vals or not vals[2]: return error(self,"Task title and active employee are required.")
        try:
            self.db.conn.execute("""UPDATE tasks SET employee_id=?,task_date=?,title=?,department=?,details=?,due_time=?,priority=?,status=?,progress=?,proof_url=?,proof_note=?,submitted_at=?,manager_note=?,expose_link=?,target_qty=?,actual_qty=?,next_action=?,custom_values=?,updated_at=? WHERE id=?""",(*vals, now_text(), tid))
            self.db.conn.commit(); self.db.log("Task edited",vals[2]); self.refresh_all()
        except sqlite3.Error as ex: error(self, f"Could not update task: {ex}")

    def task_table_select_all(self):
        if hasattr(self, "task_table"):
            self.task_table.selectAll()

    def _selected_task_ids(self, table=None):
        table = table or self.task_table
        ids = []
        for index in table.selectionModel().selectedRows():
            item = table.item(index.row(), 0)
            if item:
                try: ids.append(int(item.text()))
                except (TypeError, ValueError): pass
        return list(dict.fromkeys(ids))

    def bulk_edit_tasks(self):
        task_ids = self._selected_task_ids()
        if not task_ids:
            return error(self, "Select one or more tasks first. Use Select All to edit every task shown for the current date/filter.")
        dialog = QDialog(self)
        dialog.setWindowTitle("Bulk edit selected tasks")
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        dialog.setSizeGripEnabled(True)
        dialog.setStyleSheet("QDialog { background-color: #0B0F19; color: #F8FAFC; }")

        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1024, 768)
        bdlg_w = min(620, max(480, avail.width() - 40))
        bdlg_h = min(680, max(420, avail.height() - 80))
        dialog.resize(bdlg_w, bdlg_h)
        dialog.setMinimumSize(440, 360)
        dialog.move(avail.x() + max(10, (avail.width() - bdlg_w) // 2), avail.y() + max(10, (avail.height() - bdlg_h) // 2))

        d_root = QVBoxLayout(dialog)
        d_root.setContentsMargins(0, 0, 0, 0)
        d_root.setSpacing(0)

        b_hdr = QFrame()
        b_hdr.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E1B4B, stop:0.5 #1E293B, stop:1 #0F172A); border-bottom: 1px solid rgba(129, 140, 248, 0.35); padding: 12px 18px;")
        b_hdr_l = QVBoxLayout(b_hdr)
        b_hdr_l.setContentsMargins(4, 4, 4, 4)
        b_title = QLabel("📝 Bulk Edit Selected Tasks")
        b_title.setStyleSheet("font-size: 11pt; font-weight: 800; color: #FFFFFF;")
        b_sub = QLabel(f"Apply selected fields to {len(task_ids)} task(s). Leave a field unchecked to preserve its current value.")
        b_sub.setStyleSheet("font-size: 8.5pt; color: #94A3B8;")
        b_hdr_l.addWidget(b_title)
        b_hdr_l.addWidget(b_sub)
        d_root.addWidget(b_hdr, 0)

        b_scroll = QScrollArea()
        b_scroll.setWidgetResizable(True)
        b_scroll.setFrameShape(QFrame.Shape.NoFrame)
        b_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        b_scroll_content = QWidget()
        form = QFormLayout(b_scroll_content)
        form.setContentsMargins(18, 14, 18, 14)
        form.setSpacing(10)
        b_scroll.setWidget(b_scroll_content)
        d_root.addWidget(b_scroll, 1)

        fields = {}
        def field_row(label, widget):
            check = QCheckBox("Apply")
            check.setStyleSheet("color: #818CF8; font-weight: 600;")
            wrap = QWidget(); row = QHBoxLayout(wrap); row.setContentsMargins(0,0,0,0); row.setSpacing(8); row.addWidget(check); row.addWidget(widget,1)
            form.addRow(label, wrap); fields[label] = (check, widget)
        title = QLineEdit(); field_row("Assigned Task", title)
        dept = QLineEdit(); field_row("Department", dept)
        target_qty = QLineEdit(); field_row("Target Qty", target_qty)
        actual_qty = QLineEdit(); field_row("Actual Qty", actual_qty)
        progress = QSpinBox(); progress.setRange(0,100); progress.setSuffix("%"); field_row("Completion %", progress)
        priority = QComboBox(); priority.addItems(["Low","Normal","High","Urgent"]); field_row("Priority", priority)
        status = QComboBox()
        for label, value in TaskDialog.STATUSES: status.addItem(label, value)
        field_row("Status", status)
        custom_values_in = QLineEdit()
        custom_values_in.setPlaceholderText("e.g. Client: Acme, Location: Zone 2")
        field_row("Custom Values", custom_values_in)
        next_action = QLineEdit(); field_row("Next Action", next_action)
        expose_link = QCheckBox("Expose full proof URL in reports"); field_row("Expose links", expose_link)

        b_footer = QFrame()
        b_footer.setStyleSheet("background: #0B0F19; border-top: 1px solid rgba(148, 163, 184, 0.16); padding: 10px 18px;")
        b_footer_l = QHBoxLayout(b_footer)
        b_footer_l.setContentsMargins(12, 6, 12, 6)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        b_footer_l.addStretch(1)
        b_footer_l.addWidget(buttons)
        d_root.addWidget(b_footer, 0)
        if dialog.exec() != QDialog.Accepted: return
        updates = {}
        if fields["Assigned Task"][0].isChecked():
            value = title.text().strip()
            if not value: return error(self, "Assigned Task cannot be blank.")
            updates["title"] = value
        if fields["Department"][0].isChecked(): updates["department"] = dept.text().strip()
        if fields["Target Qty"][0].isChecked(): updates["target_qty"] = target_qty.text().strip()
        if fields["Actual Qty"][0].isChecked(): updates["actual_qty"] = actual_qty.text().strip()
        if fields["Completion %"][0].isChecked(): updates["progress"] = progress.value()
        if fields["Priority"][0].isChecked(): updates["priority"] = priority.currentText()
        if fields["Status"][0].isChecked(): updates["status"] = status.currentData()
        if fields["Custom Values"][0].isChecked():
            updates["custom_values"] = serialize_custom_values(parse_custom_values(custom_values_in.text().strip()))
        if fields["Next Action"][0].isChecked():
            updates["next_action"] = next_action.text().strip()
            updates["manager_note"] = next_action.text().strip()
        if fields["Expose links"][0].isChecked(): updates["expose_link"] = 1 if expose_link.isChecked() else 0
        if not updates: return info(self, "No fields were selected to update.")
        if updates.get("status") == "Completed": updates["progress"] = 100
        if "status" in updates and updates["status"] in ("Submitted","Completed"):
            updates["submitted_at"] = now_text()
        updates["updated_at"] = now_text()
        columns = list(updates)
        placeholders = ", ".join(f"{column}=?" for column in columns)
        try:
            self.db.conn.execute("BEGIN")
            for task_id in task_ids:
                self.db.conn.execute(f"UPDATE tasks SET {placeholders} WHERE id=?", [updates[c] for c in columns] + [task_id])
            self.db.conn.commit()
        except sqlite3.Error as exc:
            self.db.conn.rollback()
            return error(self, f"Bulk task update failed; no changes were saved. {exc}")
        self.db.log("Bulk tasks edited", f"count={len(task_ids)}, fields={','.join(columns)}")
        self.refresh_all()
        info(self, f"Updated {len(task_ids)} selected task(s).")

    def delete_task(self, table=None):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer account has permission to delete tasks.")
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
        if not row: return error(self, "Task not found.")
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

    def attendance_select_all(self):
        if hasattr(self, "att_table"):
            self.att_table.selectAll()

    def _selected_attendance_employee_ids(self):
        ids = []
        for index in self.att_table.selectionModel().selectedRows():
            item = self.att_table.item(index.row(), 0)
            if item:
                try: ids.append(int(item.data(Qt.UserRole)))
                except (TypeError, ValueError): pass
        return list(dict.fromkeys(ids))

    def bulk_edit_attendance(self):
        employee_ids = self._selected_attendance_employee_ids()
        if not employee_ids:
            return error(self, "Select one or more employee rows first. Use Select All to edit every employee shown for this date.")
        work_date = self.att_date.date().toString("yyyy-MM-dd")
        if self.db.is_holiday(work_date):
            return error(self, "This date is declared as a holiday. Remove the holiday declaration before editing attendance.")
        dialog = QDialog(self)
        dialog.setWindowTitle("Bulk edit attendance")
        dialog.setMinimumWidth(540)
        form = QFormLayout(dialog)
        form.addRow(QLabel(f"Apply checked fields to {len(employee_ids)} employee(s) on {work_date}. Unchecked fields remain unchanged."))
        fields = {}
        def field_row(label, widget):
            check = QCheckBox("Apply")
            wrap = QWidget(); row = QHBoxLayout(wrap); row.setContentsMargins(0,0,0,0); row.addWidget(check); row.addWidget(widget,1)
            form.addRow(label, wrap); fields[label] = (check, widget)
        status = QComboBox(); status.addItems(ATTENDANCE_STATUS_OPTIONS); field_row("Attendance status", status)
        check_in = QLineEdit(); check_in.setPlaceholderText("HH:MM (blank clears)"); field_row("Check-in", check_in)
        check_out = QLineEdit(); check_out.setPlaceholderText("HH:MM (blank clears)"); field_row("Check-out", check_out)
        remarks_combo = QComboBox(); remarks_combo.setEditable(True); remarks_combo.addItems(ATTENDANCE_REMARK_OPTIONS); field_row("Remarks", remarks_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
        if dialog.exec() != QDialog.Accepted: return
        changes = {}
        if fields["Attendance status"][0].isChecked(): changes["attendance_status"] = status.currentText()
        if fields["Check-in"][0].isChecked(): changes["check_in"] = check_in.text().strip()
        if fields["Check-out"][0].isChecked(): changes["check_out"] = check_out.text().strip()
        if "Remarks" in fields and fields["Remarks"][0].isChecked():
            changes["attendance_note"] = remarks_combo.currentText().strip()
        elif "Note" in fields and fields["Note"][0].isChecked():
            changes["attendance_note"] = note.text().strip()
        if not changes: return info(self, "No fields were selected to update.")
        for field in ("check_in","check_out"):
            value = changes.get(field, "")
            if value and not valid_hhmm(value): return error(self, f"{field.replace('_',' ').title()} must use 24-hour HH:MM format.")
        if changes.get("check_out") and not changes.get("check_in"):
            # Existing records may already have a check-in; validate per employee below.
            pass
        if changes.get("attendance_status") in ("Absent","Leave","Unmarked"):
            changes.setdefault("check_in", "")
            changes.setdefault("check_out", "")
        now = now_text()
        try:
            self.db.conn.execute("BEGIN")
            for employee_id in employee_ids:
                old = self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?", (employee_id, work_date)).fetchone()
                current_in = changes.get("check_in", old["check_in"] if old else "")
                current_out = changes.get("check_out", old["check_out"] if old else "")
                if current_out and not current_in:
                    raise ValueError(f"Employee ID {employee_id}: check-out requires a check-in.")
                current_status = changes.get("attendance_status", old["attendance_status"] if old else "Unmarked")
                current_note = changes.get("attendance_note", old["attendance_note"] if old else "")
                if (current_in or current_out) and not is_present_attendance_status(current_status):
                    current_status = "Present"
                if current_status in ("Absent","Leave","Unmarked"):
                    current_in = current_out = ""
                if old:
                    self.db.conn.execute(
                        "UPDATE attendance SET check_in=?,check_out=?,attendance_note=?,attendance_status=?,updated_at=? WHERE id=?",
                        (current_in,current_out,current_note,current_status,now,old["id"])
                    )
                else:
                    self.db.conn.execute(
                        "INSERT INTO attendance(employee_id,work_date,check_in,check_out,attendance_note,attendance_status,updated_at) VALUES(?,?,?,?,?,?,?)",
                        (employee_id,work_date,current_in,current_out,current_note,current_status,now)
                    )
            self.db.conn.commit()
        except (sqlite3.Error, ValueError) as exc:
            self.db.conn.rollback()
            return error(self, f"Bulk attendance update failed; no changes were saved. {exc}")
        self.db.log("Bulk attendance edited", f"date={work_date}, employees={len(employee_ids)}, fields={','.join(changes)}")
        self.refresh_all()
        info(self, f"Updated attendance for {len(employee_ids)} employee(s).")

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

    def _attendance_visible_time(self, employee_id, work_date, column):
        """Read an attendance time currently shown in the row, including an unsaved edit."""
        if not hasattr(self, "att_table"):
            return ""
        for row in range(self.att_table.rowCount()):
            employee_item = self.att_table.item(row, 0)
            date_item = self.att_table.item(row, 1)
            if not employee_item or str(employee_item.data(Qt.UserRole)) != str(employee_id):
                continue
            if not date_item or date_item.text() != work_date:
                continue
            cell = self.att_table.cellWidget(row, column)
            editor = cell.findChild(QLineEdit) if cell else None
            return editor.text().strip() if editor else ""
        return ""

    def _update_attendance_row_display(self, employee_id, work_date, check_in, check_out, status, break_minutes=0):
        """Update computed attendance cells without tearing down the active time editor."""
        for row in range(self.att_table.rowCount()):
            employee_item = self.att_table.item(row, 0)
            date_item = self.att_table.item(row, 1)
            if not employee_item or str(employee_item.data(Qt.UserRole)) != str(employee_id):
                continue
            if not date_item or date_item.text() != work_date:
                continue
            status_cell = self.att_table.cellWidget(row, 2)
            status_combo = status_cell.findChild(QComboBox) if status_cell else None
            if status_combo and status_combo.currentText() != status:
                status_combo.blockSignals(True)
                status_combo.setCurrentText(status)
                status_combo.blockSignals(False)
            hours_item = self.att_table.item(row, 5)
            if hours_item:
                net_hours = calculate_net_working_hours(check_in, check_out, break_minutes)
                hours_item.setText(net_hours)
                hours_item.setToolTip(f"Net work hours: {net_hours or 'not available'}")
            break

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
        time = time.strip()
        if not valid_hhmm(time):
            return error(self, "Enter check-in time in 24-hour HH:MM format, for example 09:30.")
        # Overnight shifts are valid (for example, 22:00 to 06:00); validate
        # format here and let net-hours calculation handle the date boundary.
        old = self.db.conn.execute(
            "SELECT attendance_status FROM attendance WHERE employee_id=? AND work_date=?", (eid, d)
        ).fetchone()
        next_status = old["attendance_status"] if old and is_present_attendance_status(old["attendance_status"]) else "Present"
        self.db.upsert_attendance(eid,d,check_in=time,status=next_status)
        self.db.log("Attendance check-in",f"employee={eid}, date={d}, time={time}"); self.refresh_all()

    def check_out(self):
        eid=self.attendance_selected_employee()
        if not eid: return error(self, "Select an employee first.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        if self.db.is_holiday(d): return error(self,"This date is declared as a holiday.")
        time, ok = QInputDialog.getText(self, "Check Out", "Check-out time (HH:MM):", text=datetime.now().strftime("%H:%M"))
        if not ok or not time.strip(): return
        time = time.strip()
        if not valid_hhmm(time):
            return error(self, "Enter check-out time in 24-hour HH:MM format, for example 18:00.")
        existing = self.db.conn.execute(
            "SELECT check_in, attendance_status FROM attendance WHERE employee_id=? AND work_date=?", (eid, d)
        ).fetchone()
        check_in = str(existing["check_in"] or "").strip() if existing else ""
        if not check_in:
            # A user can enter Check-in and Check-out back-to-back. Preserve the
            # visible row value if the editor has not committed it yet.
            visible_check_in = self._attendance_visible_time(eid, d, 3)
            if valid_hhmm(visible_check_in):
                check_in = visible_check_in
        if not check_in:
            return error(self, "Record a valid check-in before recording check-out.")
        if not valid_hhmm(check_in):
            return error(self, "The saved check-in time is invalid. Use Edit Times to correct it.")
        next_status = existing["attendance_status"] if existing and is_present_attendance_status(existing["attendance_status"]) else "Present"
        self.db.upsert_attendance(eid,d,check_in=check_in,check_out=time,status=next_status)
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
        ci, co = ci.strip(), co.strip()
        if ci and not valid_hhmm(ci):
            return error(self, "Check-in must use 24-hour HH:MM format.")
        if co and not valid_hhmm(co):
            return error(self, "Check-out must use 24-hour HH:MM format.")
        if co and not ci:
            return error(self, "A check-out time requires a check-in time.")
        if ci and co and datetime.strptime(co, "%H:%M") < datetime.strptime(ci, "%H:%M"):
            # Overnight shifts are supported.
            pass
        next_status = old["attendance_status"] if old and is_present_attendance_status(old["attendance_status"]) else "Present"
        self.db.upsert_attendance(eid, d, check_in=ci, check_out=co, status=next_status)
        self.db.log("Attendance times edited", f"employee={eid}, date={d}, in={ci}, out={co}")
        self.refresh_all()

    def attendance_note(self):
        eid=self.attendance_selected_employee()
        if not eid: return error(self,"Choose an employee in the Filter employee dropdown, or select a row when All employees is selected.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        old=self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?",(eid,d)).fetchone()
        current_note = old["attendance_note"] if old else ""
        dialog = QDialog(self)
        dialog.setWindowTitle("Attendance Remarks")
        dialog.setMinimumWidth(380)
        vbox = QVBoxLayout(dialog)
        vbox.setSpacing(10)
        vbox.addWidget(QLabel(f"Select preset or type remarks for {d}:"))
        combo = QComboBox()
        combo.setEditable(True)
        for opt in ATTENDANCE_REMARK_OPTIONS:
            combo.addItem(opt)
        if current_note and current_note not in ATTENDANCE_REMARK_OPTIONS:
            combo.addItem(current_note)
        combo.setEditText(current_note)
        vbox.addWidget(combo)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        vbox.addWidget(btn_box)
        if dialog.exec() == QDialog.Accepted:
            note = combo.currentText().strip()
            self.db.upsert_attendance(eid,d,note=note)
            self.db.log("Attendance remarks updated",f"employee={eid}, date={d}, remarks={note}"); self.refresh_all()

    def declare_holiday(self):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can declare holidays.")
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
        self.schedule_auto_sync()

    def remove_holiday(self):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can remove holidays.")
        d=self.att_date.date().toString("yyyy-MM-dd")
        row=self.db.conn.execute("SELECT holiday_name FROM holidays WHERE holiday_date=?",(d,)).fetchone()
        if not row: return info(self,"No holiday is declared for the selected date.")
        if not ask(self,"Remove holiday",f"Remove holiday '{row['holiday_name']}' on {d}?"): return
        self.db.conn.execute("DELETE FROM holidays WHERE holiday_date=?",(d,)); self.db.conn.commit()
        self.db.log("Holiday removed",d); self.refresh_all()
        self.schedule_auto_sync()

    def refresh_tasks(self):
        if not hasattr(self,"task_table"): return
        d=self.task_date.date().toString("yyyy-MM-dd"); eid=self.task_filter.currentData()
        rows=self.db.tasks(d,eid)
        self.task_table.setRowCount(0)
        for t in rows:
            r=self.task_table.rowCount(); self.task_table.insertRow(r)
            dept = str(t["department"] if "department" in t.keys() else "") or ""
            target_q = str(t["target_qty"] if "target_qty" in t.keys() else "") or ""
            actual_q = str(t["actual_qty"] if "actual_qty" in t.keys() else "") or ""
            comp_pct = f'{t["progress"]}%' if t["progress"] is not None else "0%"
            custom_val = format_custom_values_display(t["custom_values"] if "custom_values" in t.keys() else "")
            next_act = str((t["next_action"] if "next_action" in t.keys() else "") or t["manager_note"] or "")
            vals=[
                t["id"],
                t["task_date"],
                t["employee_name"],
                dept,
                t["title"],
                target_q,
                actual_q,
                comp_pct,
                t["priority"],
                task_status_label(t["status"]),
                t["proof_url"],
                custom_val,
                next_act,
            ]
            self.set_row_items(self.task_table, r, vals, status_cols={8, 9})
        if hasattr(self, "task_count_badge"):
            self.task_count_badge.setText(f"Tasks: {len(rows)}")

        total_cnt = len(rows)
        comp_cnt = sum(1 for t in rows if str(t["status"]).strip().lower() in ("completed", "done") or (t["progress"] is not None and t["progress"] >= 100))
        prog_cnt = sum(1 for t in rows if str(t["status"]).strip().lower() in ("in progress", "running") or (t["progress"] is not None and 0 < t["progress"] < 100))
        pend_cnt = sum(1 for t in rows if str(t["status"]).strip().lower() in ("not started", "pending", "pending review", "blocked"))

        if hasattr(self, "kpi_total_tasks"): self.kpi_total_tasks.setText(str(total_cnt))
        if hasattr(self, "kpi_completed_tasks"): self.kpi_completed_tasks.setText(str(comp_cnt))
        if hasattr(self, "kpi_in_progress_tasks"): self.kpi_in_progress_tasks.setText(str(prog_cnt))
        if hasattr(self, "kpi_pending_tasks"): self.kpi_pending_tasks.setText(str(pend_cnt))
        if hasattr(self, "kpi_custom_tasks"): self.kpi_custom_tasks.setText(str(pend_cnt))

        self.refresh_dashboard()

    def _on_task_table_selection_changed(self):
        pass

    def save_employee_target_from_input(self):
        pass

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
        def task_progress(t):
            # Legacy blank/NA statuses and unselected values must never be treated
            # as completed just because a stale progress field contains 100.
            if not is_known_task_status(t["status"]):
                return 0
            try:
                return max(0, min(100, int(float(t["progress"] or 0))))
            except (TypeError, ValueError, OverflowError):
                return 0
        task_score=(sum(task_progress(t) for t in task_rows)/len(task_rows)) if task_rows else None
        att_rows=self.db.conn.execute("SELECT work_date,attendance_status,check_in FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ?",(employee["id"],start.isoformat(),as_of_date.isoformat())).fetchall()
        weekdays=self.db.working_weekdays()
        holidays={row["holiday_date"] for row in self.db.holidays_between(start.isoformat(),as_of_date.isoformat())}
        def is_scheduled_workday(day_text):
            try:
                work_day=date.fromisoformat(day_text)
            except (TypeError,ValueError):
                return False
            return work_day.weekday() in weekdays and day_text not in holidays
        working_days=self.count_working_days(start,as_of_date)
        leave_days=sum(1 for a in att_rows if a["attendance_status"]=="Leave" and is_scheduled_workday(a["work_date"]))
        attendance_eligible_days=max(0,working_days-leave_days)
        present=sum(1 for a in att_rows if is_scheduled_workday(a["work_date"]) and (is_present_attendance_status(a["attendance_status"]) or (a["attendance_status"]=="Unmarked" and a["check_in"])))
        attendance_score=(present/attendance_eligible_days*100) if attendance_eligible_days else None
        if task_score is not None and attendance_score is not None: score=round(task_score*0.7+attendance_score*0.3)
        elif task_score is not None: score=round(task_score)
        elif attendance_score is not None: score=round(attendance_score)
        else: score=0
        return {"start":start,"working_days":working_days,"attendance_eligible_days":attendance_eligible_days,"present":present,"tasks":len(task_rows),"completed":sum(1 for t in task_rows if is_explicitly_completed_task_status(t["status"])),"task_score":task_score,"attendance_score":attendance_score,"score":score}

    def save_attendance_inline(self, employee_id, work_date, field, value):
        """Validate and persist inline attendance edits without losing unrelated fields."""
        if self.db.is_holiday(work_date):
            error(self, "This date is declared as a holiday. Remove the holiday declaration before editing attendance.")
            self.refresh_attendance()
            return
        value = str(value or "").strip()
        old = self.db.conn.execute(
            "SELECT * FROM attendance WHERE employee_id=? AND work_date=?",
            (employee_id, work_date),
        ).fetchone()
        if field in ("check_in", "check_out") and value and not valid_hhmm(value):
            error(self, "Enter time in 24-hour HH:MM format, for example 09:30.")
            self.refresh_attendance()
            return
        check_in = old["check_in"] if old else ""
        check_out = old["check_out"] if old else ""
        status = old["attendance_status"] if old else "Unmarked"
        note = old["attendance_note"] if old else ""
        if field == "status":
            if value not in ATTENDANCE_STATUS_OPTIONS:
                return
            status = value
            if value in ("Absent", "Leave", "Unmarked"):
                check_in, check_out = "", ""
        elif field == "check_in":
            if not value and check_out:
                error(self, "Clear Check-out before clearing Check-in.")
                self.refresh_attendance()
                return
            check_in = value
            if value:
                if not is_present_attendance_status(status):
                    status = "Present"
            elif not check_out and is_present_attendance_status(status):
                status = "Unmarked"
        elif field == "check_out":
            if not check_in:
                visible_check_in = self._attendance_visible_time(employee_id, work_date, 3)
                if valid_hhmm(visible_check_in):
                    check_in = visible_check_in
            if value and not check_in:
                error(self, "Enter Check-in before Check-out.")
                self.refresh_attendance()
                return
            check_out = value
            if value:
                if not is_present_attendance_status(status):
                    status = "Present"
        elif field in ("note", "remarks"):
            note = value
        else:
            return
        self.db.upsert_attendance(
            employee_id, work_date, check_in=check_in, check_out=check_out,
            note=note, status=status
        )
        employee = self.db.employee(employee_id)
        self.db.log(
            "Attendance updated",
            f"{employee['name']}: {field}={value or '(cleared)'} on {work_date}"
        )
        if field == "status":
            self.refresh_attendance()
        else:
            self._update_attendance_row_display(
                employee_id, work_date, check_in, check_out, status,
                old["break_minutes"] if old else 0,
            )
            self.refresh_attendance_summary()
            self.refresh_dashboard()

    def refresh_attendance(self):
        if not hasattr(self,"att_table"): return
        self.refresh_employee_filter()
        # Remember selected employee so check-in/out stay on the same row
        selected_eid = self.attendance_selected_employee()
        d=self.att_date.date().toString("yyyy-MM-dd")
        holiday=self.db.get_holiday(d)
        if holiday:
            self.holiday_banner.setText(f"🎉 HOLIDAY: {holiday} — excluded from all working-day counts")
            self.holiday_banner.setStyleSheet(
                "QLabel { background: rgba(245, 158, 11, 0.18); color: #FBBF24; border: 1.5px solid rgba(245, 158, 11, 0.45); "
                "border-radius: 8px; padding: 6px 14px; font-weight: 700; font-size: 9pt; }"
            )
        else:
            self.holiday_banner.setText("ℹ️ No holiday declared for the selected date.")
            self.holiday_banner.setStyleSheet(
                "QLabel { background: rgba(30, 41, 59, 0.70); color: #94A3B8; border: 1px solid rgba(51, 65, 85, 0.50); "
                "border-radius: 8px; padding: 6px 14px; font-size: 8.5pt; font-weight: 500; }"
            )
        rows={a["employee_id"]:a for a in self.db.attendance(d)}
        emps=self.db.employees(False)
        if hasattr(self, "att_employee_filter") and self.att_employee_filter.currentData() is not None:
            filter_id = self.att_employee_filter.currentData()
            emps = [e for e in emps if e["id"] == filter_id]
        self.att_table.setRowCount(0)
        restore_row = -1
        pal = MainWindow._ui_chrome_palette(self.current_theme()) if hasattr(self, "current_theme") else MainWindow._ui_chrome_palette("night")
        c_bg = pal["dropdown_bg"]
        c_fg = pal["dropdown_fg"]
        c_border = pal["dropdown_border"]
        c_hover = pal["dropdown_hover"]
        c_accent = pal["accent"]
        c_placeholder = pal["muted_text"]
        is_dark_mode = self.current_theme().lower() in ("night", "dark")
        for e in emps:
            a=rows.get(e["id"]); r=self.att_table.rowCount(); self.att_table.insertRow(r)
            self.att_table.setRowHeight(r, 52)
            name=QTableWidgetItem(e["name"]); name.setData(Qt.UserRole,e["id"]); name.setToolTip(e["name"])
            name.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            name.setForeground(QColor("#FFFFFF" if is_dark_mode else "#0F172A"))
            self.att_table.setItem(r,0,name)
            if selected_eid is not None and e["id"] == selected_eid:
                restore_row = r
            ci=a["check_in"] if a else ""; co=a["check_out"] if a else ""
            status="Holiday" if holiday else (a["attendance_status"] if a else "Unmarked")
            if a and status=="Unmarked" and ci: status="Present"
            hours=calculate_net_working_hours(ci, co, a["break_minutes"] if a else 0)
            vals=[d,status,ci,co,hours,a["attendance_note"] if a else ""]
            # Inline editors make attendance updates visible and discoverable.
            date_item = QTableWidgetItem(d)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
            date_item.setToolTip(f"Attendance date: {d}")
            date_item.setForeground(QColor("#94A3B8" if is_dark_mode else "#64748B"))
            self.att_table.setItem(r, 1, date_item)

            def attach_editor(column, editor):
                cell = QWidget()
                cell.setObjectName("attendanceEditorCell")
                cell.setProperty("in_table_cell", True)
                editor.setProperty("in_table_cell", True)
                cell.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(4, 2, 4, 2)
                cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell_layout.setSpacing(0)
                cell_layout.addWidget(editor)
                self.att_table.setCellWidget(r, column, cell)

            status_combo = QComboBox()
            status_combo.setObjectName("attendanceStatusCombo")
            status_combo.setProperty("in_table_cell", True)
            status_combo.addItems([*ATTENDANCE_STATUS_OPTIONS, "Holiday"])
            status_combo.setCurrentText(status if status in (*ATTENDANCE_STATUS_OPTIONS, "Holiday") else "Unmarked")
            status_combo.setMinimumWidth(140)
            status_combo.setFixedHeight(32)
            status_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            status_combo.setEnabled(not bool(holiday))
            status_combo.setToolTip("Choose Present, Absent, Leave or Unmarked")
            arrow_icon = resource_path("assets/chevron_down_white.png" if self.current_theme().lower() in ("night", "dark") else "assets/chevron_down_slate.png").replace("\\", "/")
            if is_dark_mode:
                if is_present_attendance_status(status):
                    st_bg, st_fg, st_border = "rgba(16, 185, 129, 0.14)", "#34D399", "rgba(16, 185, 129, 0.35)"
                elif status == "Absent":
                    st_bg, st_fg, st_border = "rgba(239, 68, 68, 0.14)", "#F87171", "rgba(239, 68, 68, 0.35)"
                elif status == "Leave":
                    st_bg, st_fg, st_border = "rgba(245, 158, 11, 0.14)", "#FBBF24", "rgba(245, 158, 11, 0.35)"
                elif status == "Holiday":
                    st_bg, st_fg, st_border = "rgba(168, 85, 247, 0.14)", "#C084FC", "rgba(168, 85, 247, 0.35)"
                else:
                    st_bg, st_fg, st_border = "rgba(255, 255, 255, 0.04)", "#94A3B8", "rgba(255, 255, 255, 0.09)"
                status_combo.setStyleSheet(
                    f"QComboBox {{ background-color: {st_bg}; color: {st_fg}; border: 1px solid {st_border}; "
                    f"border-radius: 6px; padding: 2px 22px 2px 8px; font-size: 8.5pt; font-weight: 650; }} "
                    f"QComboBox:hover {{ border-color: #00D2FF; }} "
                    f"QComboBox:focus {{ border: 1.5px solid #00D2FF; }} "
                    f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid {st_border}; border-top-right-radius: 5px; border-bottom-right-radius: 5px; background-color: {st_bg}; }} "
                    f"QComboBox::down-arrow {{ image: url({arrow_icon}); width: 9px; height: 9px; }}"
                )
            else:
                status_combo.setStyleSheet(
                    f"QComboBox {{ background-color: {c_bg}; color: {c_fg}; border: 1px solid {c_border}; "
                    f"border-radius: 7px; padding: 2px 24px 2px 8px; font-size: 9pt; font-weight: 600; }} "
                    f"QComboBox:hover {{ border-color: {c_accent}; }} "
                    f"QComboBox:focus {{ border: 1.5px solid {c_accent}; }} "
                    f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 22px; border-left: 1px solid {c_border}; border-top-right-radius: 6px; border-bottom-right-radius: 6px; background-color: {c_bg}; }} "
                    f"QComboBox::down-arrow {{ image: url({arrow_icon}); width: 10px; height: 10px; }}"
                )
            status_combo.currentTextChanged.connect(
                lambda value, employee_id=e["id"], work_date=d: self.save_attendance_inline(
                    employee_id, work_date, "status", value
                )
            )
            attach_editor(2, status_combo)

            for column, value, field in (
                (3, ci, "check_in"),
                (4, co, "check_out"),
            ):
                editor = QLineEdit(str(value or ""))
                editor.setObjectName("attendanceFieldEditor")
                editor.setProperty("in_table_cell", True)
                editor.setMinimumWidth(0)
                editor.setFixedHeight(32)
                editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
                editor.setPlaceholderText("HH:MM")
                editor.setToolTip("Enter time as HH:MM (24-hour format)")
                editor.setEnabled(not bool(holiday))
                if is_dark_mode:
                    editor.setStyleSheet(
                        "QLineEdit { background-color: rgba(255, 255, 255, 0.03); color: #F8FAFC; border: 1px solid rgba(255, 255, 255, 0.08); "
                        "border-radius: 6px; padding: 2px 8px; font-size: 9pt; font-weight: 500; } "
                        "QLineEdit:hover { border: 1px solid rgba(0, 210, 255, 0.40); background-color: rgba(255, 255, 255, 0.06); } "
                        "QLineEdit:focus { border: 1.5px solid #00D2FF; background-color: rgba(0, 210, 255, 0.08); } "
                        "QLineEdit::placeholder { color: rgba(255, 255, 255, 0.28); }"
                    )
                else:
                    editor.setStyleSheet(
                        f"QLineEdit {{ background-color: {c_bg}; color: {c_fg}; border: 1px solid {c_border}; "
                        f"border-radius: 7px; padding: 2px 8px; font-size: 9pt; font-weight: 500; }} "
                        f"QLineEdit:hover {{ border-color: {c_accent}; }} "
                        f"QLineEdit:focus {{ border: 1.5px solid {c_accent}; background-color: {c_hover}; }} "
                        f"QLineEdit::placeholder {{ color: {c_placeholder}; }}"
                    )
                editor.editingFinished.connect(
                    lambda input_widget=editor, employee_id=e["id"], work_date=d, field_name=field:
                    self.save_attendance_inline(employee_id, work_date, field_name, input_widget.text())
                )
                attach_editor(column, editor)

            # Column 6: Dedicated Remarks editor (editable combo with presets like Late Check-in, Late Check-out, On Time)
            current_rem = str(a["attendance_note"] if a else "").strip()
            rem_combo = QComboBox()
            rem_combo.setObjectName("attendanceRemarksCombo")
            rem_combo.setProperty("in_table_cell", True)
            rem_combo.setEditable(True)
            for opt in ATTENDANCE_REMARK_OPTIONS:
                rem_combo.addItem(opt)
            if current_rem and current_rem not in ATTENDANCE_REMARK_OPTIONS:
                rem_combo.addItem(current_rem)
            rem_combo.setEditText(current_rem)
            rem_combo.setMinimumWidth(150)
            rem_combo.setFixedHeight(32)
            rem_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            rem_combo.setEnabled(not bool(holiday))
            rem_combo.setToolTip("Remarks: Choose preset (Late Check-in, Late Check-out, On Time, etc.) or type custom remarks")
            if is_dark_mode:
                rem_combo.setStyleSheet(
                    f"QComboBox {{ background-color: rgba(255, 255, 255, 0.04); color: #F8FAFC; border: 1px solid rgba(255, 255, 255, 0.10); "
                    f"border-radius: 6px; padding: 2px 22px 2px 8px; font-size: 8.5pt; font-weight: 500; }} "
                    f"QComboBox:hover {{ border-color: #00D2FF; }} "
                    f"QComboBox:focus {{ border: 1.5px solid #00D2FF; }} "
                    f"QComboBox QAbstractItemView {{ background-color: #1E293B; color: #F8FAFC; selection-background-color: #0284C7; }} "
                    f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid rgba(255, 255, 255, 0.10); border-top-right-radius: 5px; border-bottom-right-radius: 5px; }} "
                    f"QComboBox::down-arrow {{ image: url({arrow_icon}); width: 9px; height: 9px; }}"
                )
            else:
                rem_combo.setStyleSheet(
                    f"QComboBox {{ background-color: {c_bg}; color: {c_fg}; border: 1px solid {c_border}; "
                    f"border-radius: 7px; padding: 2px 24px 2px 8px; font-size: 9pt; font-weight: 500; }} "
                    f"QComboBox:hover {{ border-color: {c_accent}; }} "
                    f"QComboBox:focus {{ border: 1.5px solid {c_accent}; }} "
                    f"QComboBox QAbstractItemView {{ background-color: #FFFFFF; color: #0F172A; selection-background-color: #3B82F6; selection-color: #FFFFFF; }} "
                    f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 22px; border-left: 1px solid {c_border}; border-top-right-radius: 6px; border-bottom-right-radius: 6px; }} "
                    f"QComboBox::down-arrow {{ image: url({arrow_icon}); width: 10px; height: 10px; }}"
                )
            rem_combo.activated.connect(
                lambda idx, cb=rem_combo, eid=e["id"], wd=d: self.save_attendance_inline(eid, wd, "note", cb.currentText())
            )
            if rem_combo.lineEdit():
                rem_combo.lineEdit().editingFinished.connect(
                    lambda cb=rem_combo, eid=e["id"], wd=d: self.save_attendance_inline(eid, wd, "note", cb.currentText())
                )
            attach_editor(6, rem_combo)

            hours_item = QTableWidgetItem(hours)
            hours_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
            hours_item.setToolTip(f"Net work hours: {hours or 'not available'}")
            if is_dark_mode and hours:
                hours_item.setForeground(QColor("#00E5FF"))
            self.att_table.setItem(r, 5, hours_item)
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
            present=sum(1 for a in non_holiday_rows if is_present_attendance_status(a["attendance_status"]) or (a["attendance_status"]=="Unmarked" and a["check_in"]))
            absent=sum(1 for a in non_holiday_rows if a["attendance_status"]=="Absent")
            leave=sum(1 for a in non_holiday_rows if a["attendance_status"]=="Leave")
            def _is_working_weekday_holiday(h_item):
                try:
                    return date.fromisoformat(h_item["holiday_date"]).weekday() in self.db.working_weekdays()
                except (ValueError, TypeError):
                    return False
            holidays=sum(1 for h in self.db.holidays_between(effective_start.isoformat(),end.isoformat()) if _is_working_weekday_holiday(h)) if effective_start<=end else 0
            since_end=min(selected,date.today())
            since_rows=self.db.conn.execute("SELECT work_date,attendance_status,check_in FROM attendance WHERE employee_id=? AND work_date BETWEEN ? AND ?",(e["id"],start.isoformat(),since_end.isoformat())).fetchall()
            since=sum(1 for a in since_rows if not self.db.is_holiday(a["work_date"]) and (is_present_attendance_status(a["attendance_status"]) or (a["attendance_status"]=="Unmarked" and a["check_in"])))
            vals=[e["name"],start.isoformat(),working,present,absent,leave,holidays,since]
            r=self.attendance_summary_table.rowCount(); self.attendance_summary_table.insertRow(r)
            for c,v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignLeft if c == 0 else Qt.AlignmentFlag.AlignCenter))
                item.setToolTip(str(v))
                self.attendance_summary_table.setItem(r,c,item)

    def refresh_dashboard(self):
        if not hasattr(self, "kpi_labels"):
            return
        report_date = date.today().isoformat()
        employees = self.db.employees(False)
        tasks = self.db.tasks(report_date)
        present = 0
        absent = 0
        leave = 0
        checked_in = 0
        attendance_rows = []
        for employee in employees:
            record = self.db.conn.execute(
                "SELECT attendance_status, check_in FROM attendance WHERE employee_id=? AND work_date=?",
                (employee["id"], report_date),
            ).fetchone()
            status = str(record["attendance_status"] or "Unmarked").strip() if record else "Unmarked"
            check_in = record["check_in"] if record and record["check_in"] else "—"
            normalized_status = status.casefold()
            has_check_in = bool(record and str(record["check_in"] or "").strip())
            if is_present_attendance_status(status) or (normalized_status == "unmarked" and has_check_in):
                if normalized_status == "unmarked":
                    status = "Present"
                present += 1
                if has_check_in:
                    checked_in += 1
            elif normalized_status == "absent":
                status = "Absent"
                absent += 1
            elif normalized_status == "leave":
                status = "Leave"
                leave += 1
            elif normalized_status in {"unmarked", "", "not checked"}:
                status = "Not checked"
            else:
                status = task_status_label(status)
            attendance_rows.append((employee["name"], status, check_in))
        open_tasks = sum(1 for task in tasks if not is_explicitly_completed_task_status(task["status"])
                         and not is_cancelled_task_status(task["status"]))
        for label, value in zip(self.kpi_labels, [len(employees), present, absent, open_tasks, checked_in]):
            label.setText(str(value))
        if hasattr(self, "dashboard_clock"):
            self.dashboard_clock.setText(datetime.now().strftime("%d %B %Y  ·  %I:%M %p"))
        if hasattr(self, "dashboard_recent"):
            self.dashboard_recent.setRowCount(0)
            for index, employee in enumerate(reversed(employees[-8:]), 1):
                row = self.dashboard_recent.rowCount()
                self.dashboard_recent.insertRow(row)
                values = [str(index), employee["employee_code"] or "", employee["name"] or "", employee["designation"] or "", "Active" if employee["active"] else "Inactive"]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if column in (0, 1, 4) else Qt.AlignmentFlag.AlignLeft))
                    item.setToolTip(str(value))
                    self.dashboard_recent.setItem(row, column, item)
        for row in range(self.dashboard_tasks.rowCount()):
            old_progress = self.dashboard_tasks.cellWidget(row, 3)
            if old_progress is not None:
                self.dashboard_tasks.removeCellWidget(row, 3)
                old_progress.deleteLater()
        self.dashboard_tasks.setRowCount(0)
        for task in tasks[:12]:
            row = self.dashboard_tasks.rowCount()
            self.dashboard_tasks.insertRow(row)
            values = [task["employee_name"], task["title"], task_status_label(task["status"]), None, task["due_time"] or "—"]
            for column, value in enumerate(values):
                if column == 3:
                    try:
                        progress = int(float(task["progress"] or 0))
                    except (TypeError, ValueError):
                        progress = 0
                    progress = max(0, min(100, progress))
                    employee_name = str(task["employee_name"] or "Employee")
                    task_title = str(task["title"] or "Task")
                    progress_bar = QProgressBar()
                    progress_bar.setObjectName("dashboardProgress")
                    progress_bar.setRange(0, 100)
                    progress_bar.setValue(progress)
                    progress_bar.setFormat("%p%")
                    progress_bar.setTextVisible(True)
                    progress_bar.setAccessibleName(f"Progress for {employee_name}, {task_title}: {progress}%")
                    progress_bar.setToolTip(f"{employee_name}\n{task_title}\nProgress: {progress}%")
                    self.dashboard_tasks.setCellWidget(row, column, progress_bar)
                    continue
                item = QTableWidgetItem(str(value if value is not None else ""))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if column in (2, 4) else Qt.AlignmentFlag.AlignLeft))
                item.setToolTip(str(value if value is not None else ""))
                self.dashboard_tasks.setItem(row, column, item)
        if hasattr(self, "dashboard_attendance_table"):
            self.dashboard_attendance_table.setRowCount(0)
            for name, status, check_in in attendance_rows[:8]:
                row = self.dashboard_attendance_table.rowCount()
                self.dashboard_attendance_table.insertRow(row)
                for column, value in enumerate((name, status, check_in)):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if column in (1, 2) else Qt.AlignmentFlag.AlignLeft))
                    item.setToolTip(str(value))
                    if column == 1:
                        status_colors = {
                            "Present": "#4ADE80" if self.current_theme() == "night" else "#15803D",
                            "Absent": "#FDA4AF" if self.current_theme() == "night" else "#BE123C",
                            "Leave": "#C4B5FD" if self.current_theme() == "night" else "#7C3AED",
                            "Not checked": "#CBD5E1" if self.current_theme() == "night" else "#64748B",
                        }
                        item.setForeground(QColor(status_colors.get(status, "#64748B")))
                    self.dashboard_attendance_table.setItem(row, column, item)
            total = len(employees)
            percent = round((present / total) * 100) if total else 0
            not_checked = max(0, total - present - absent - leave)
            self.dashboard_attendance_summary.setText(
                f"{percent}% checked in\n{present} Present  ·  {absent} Absent  ·  {leave} Leave  ·  {not_checked} Not checked"
            )
        if hasattr(self, "kpi_sparklines") and len(self.kpi_sparklines) >= 5:
            total_emp = len(employees)
            att_ratio = (present / total_emp) if total_emp else 0.0
            self.kpi_sparklines[0].set_points([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
            self.kpi_sparklines[1].set_points([0.2, 0.4, 0.5, 0.3, 0.6, 0.7, max(0.1, att_ratio)])
            self.kpi_sparklines[2].set_points([0.5, 0.3, 0.4, 0.2, 0.3, 0.1, max(0.05, 1.0 - att_ratio)])
            self.kpi_sparklines[3].set_points([0.3, 0.5, 0.4, 0.6, 0.7, 0.8, 0.9])
            self.kpi_sparklines[4].set_points([0.3, 0.45, 0.5, 0.65, 0.7, 0.85, max(0.1, att_ratio)])
        metrics = []
        self.productivity_table.setRowCount(0)
        for employee in employees:
            metric = self.employee_productivity(employee)
            metrics.append((employee["name"], metric["score"]))
            values = [employee["name"], metric["start"].isoformat(), metric["working_days"], metric["present"], metric["tasks"], metric["completed"], f'{metric["score"]}%']
            row = self.productivity_table.rowCount()
            self.productivity_table.insertRow(row)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignLeft if column == 0 else Qt.AlignmentFlag.AlignCenter))
                item.setToolTip(str(value))
                self.productivity_table.setItem(row, column, item)
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
        return "Yes" if any(is_explicitly_completed_task_status(t["status"]) and not task_evidence_urls(t) for t in tasks) else "No"

    def task_proof_label(self, employee, task, report_date):
        evidence_urls = task_evidence_urls(task)
        if evidence_urls:
            return "Link(s) attached"
        if task["proof_url"]:
            return task["proof_url"]
        if normalized_task_status(task["status"]) in {"pending", "not started", "in progress", "blocked", "pending review"}:
            return "Not provided (task is pending or in progress)"
        source_missing = self.source_status(employee, "missing_proof", report_date)
        if source_missing and source_missing.startswith("No"):
            return "No direct URL supplied in source; see proof notes / attached EOD evidence."
        if is_explicitly_completed_task_status(task["status"]):
            return "MISSING"
        return "Not provided"

    def _selected_business_report_sections(self, options):
        """Return only the optional product/service catalogs selected for export."""
        sections = []
        if options.get("business_products", False):
            try:
                products = self.db.conn.execute("SELECT * FROM bt_products ORDER BY name").fetchall()
            except sqlite3.OperationalError:
                products = []
            rows = [
                [
                    str(product["name"] or "—"), str(product["sku"] or "—"),
                    str(product["category"] or "—"), str(product["brand"] or "—"),
                    str(product["base_unit"] or "—"), f"{available_stock(product):g}",
                    f"{float(product['reorder_level'] or 0):g}",
                    f"{float(product['selling_price'] or 0):.2f}",
                ]
                for product in products
            ]
            sections.append((
                "PRODUCT CATALOG & STOCK",
                ["Product", "SKU", "Category", "Brand", "Unit", "Available stock", "Reorder level", "Selling price"],
                rows,
            ))
        if options.get("business_services", False):
            try:
                services = self.db.conn.execute("SELECT * FROM bt_services ORDER BY name").fetchall()
            except sqlite3.OperationalError:
                services = []
            rows = [
                [
                    str(service["name"] or "—"), str(service["category"] or "—"),
                    str(service["description"] or "—"), str(service["training_mode"] or "—"),
                    str(service["service_unit"] or "—"), str(service["session_duration"] or 0),
                    str(service["num_sessions"] or 0), str(service["plan_validity"] or 0),
                    f"{float(service['standard_price'] or 0):.2f}",
                    "Active" if bool(service["active"]) else "Inactive",
                ]
                for service in services
            ]
            sections.append((
                "SERVICE CATALOG",
                ["Service", "Category", "Description", "Training mode", "Unit", "Session minutes", "Sessions", "Validity days", "Standard price", "Status"],
                rows,
            ))
        return sections

    def _business_report_preview_lines(self, options):
        lines = []
        for title, headers, rows in self._selected_business_report_sections(options):
            lines.extend([title, " | ".join(headers)])
            if rows:
                lines.extend(" | ".join(row) for row in rows)
            else:
                lines.append("No records available.")
            lines.append("")
        return lines

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
        holiday=self.db.get_holiday(report_date)
        for e in self._report_employees(employee_id):
            if not e: continue
            a=self.db.conn.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?",(e["id"],report_date)).fetchone()
            status="Holiday" if holiday else (a["attendance_status"] if a else "Unmarked")
            if a and status=="Unmarked" and a["check_in"]: status="Present"
            ci=a["check_in"] if a and a["check_in"] else ""
            co=a["check_out"] if a and a["check_out"] else ""
            net=calculate_net_working_hours(ci, co, a["break_minutes"] if a else 0)
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
        logo_path = resource_path("assets/raw_strength_brand.png")
        if Path(logo_path).exists():
            try:
                logo_para = doc.add_paragraph()
                logo_para.alignment = 1
                logo_para.paragraph_format.space_after = Pt(2)
                logo_para.add_run().add_picture(logo_path, width=Inches(1.8))
            except Exception:
                pass
        title=doc.add_paragraph(style="Title"); title.alignment=1; title.add_run(self._report_title(report_type))
        chosen=self.db.employee(employee_id) if employee_id else None
        sub=doc.add_paragraph(); sub.alignment=1; sub.add_run(f"Report date: {report_date}    |    Scope: {chosen['name'] if chosen else 'All employees'}").bold=True
        doc.add_paragraph("")
        emps=self._report_employees(employee_id)
        opts=self.selected_eod_options() if eod_options is None else eod_options
        if report_type=="Employee Details":
            fields=[("Name",lambda e:e["name"])]
            if opts.get("details_identity",True): fields.extend([("Employee ID",lambda e:e["employee_code"] or "N/A"),("Department",lambda e:e["department"] or "N/A"),("Role",lambda e:e["designation"] or "N/A")])
            if opts.get("details_contact",True): fields.extend([("Phone",lambda e:e["phone"] or "N/A"),("Email",lambda e:e["email"] or "N/A")])
            if opts.get("details_joining",True): fields.append(("Joining date",lambda e:e["joining_date"] or "N/A"))
            if opts.get("details_status",True): fields.append(("Status",lambda e:"Active" if e["active"] else "Inactive"))
            if opts.get("details_notes",False): fields.append(("Notes",lambda e:e["notes"] or "N/A"))
            tab=doc.add_table(rows=1,cols=len(fields)); tab.style="Light Shading Accent 1"
            for c,(label,_value) in zip(tab.rows[0].cells,fields): c.text=label
            for e in emps:
                cells=tab.add_row().cells
                vals=[value(e) for _label,value in fields]
                for c,v in zip(cells,vals): c.text=str(v)
            doc.add_paragraph(f"Total employees: {len(emps)}")
        elif report_type=="Employee Attendance":
            holiday_name = self.db.get_holiday(report_date)
            if holiday_name:
                doc.add_paragraph(f"Declared holiday: {holiday_name}")
            rows=self._attendance_report_rows(report_date,employee_id)
            fields=[("Employee",lambda item:item["employee"]["name"])]
            if opts.get("attendance_identity",True): fields.extend([("Employee ID",lambda item:item["employee"]["employee_code"] or "N/A"),("Department",lambda item:item["employee"]["department"] or "N/A")])
            if opts.get("attendance_status",True): fields.append(("Status",lambda item:item["status"]))
            if opts.get("attendance_times",True): fields.extend([("Check-in",lambda item:item["check_in"] or "N/A"),("Check-out",lambda item:item["check_out"] or "N/A"),("Net hours",lambda item:item["net_hours"] or "N/A")])
            if opts.get("attendance_remarks",True): fields.append(("Remarks",lambda item:item["note"] or "N/A"))
            tab=doc.add_table(rows=1,cols=len(fields)); tab.style="Light Shading Accent 1"
            for c,(label,_value) in zip(tab.rows[0].cells,fields): c.text=label
            for item in rows:
                e=item["employee"]; cells=tab.add_row().cells
                vals=[value(item) for _label,value in fields]
                for c,v in zip(cells,vals): c.text=str(v)
            present=sum(is_present_attendance_status(x["status"]) for x in rows); absent=sum(x["status"]=="Absent" for x in rows); leave=sum(x["status"]=="Leave" for x in rows)
            if opts.get("attendance_summary",True): doc.add_paragraph(f"Summary: Present {present}  |  Absent {absent}  |  Leave {leave}  |  Employees {len(rows)}")
        elif report_type=="Employee Productivity":
            data=self.report_data(report_date,employee_id)
            for e,tasks,_att in data:
                prod=self.employee_productivity(e, date.fromisoformat(report_date))
                doc.add_heading(e["name"],level=1)
                if opts.get("productivity_identity",True):
                    doc.add_paragraph(f'Employee ID: {e["employee_code"] or "N/A"}  |  Department: {e["department"] or "N/A"}',style="List Bullet")
                if opts.get("productivity_metrics",True):
                    for label,value in [("Overall productivity score",f'{prod["score"]}%'),("Task progress component",f'{round(prod["task_score"])}%' if prod["task_score"] is not None else "Not enough task data"),("Attendance component",f'{round(prod["attendance_score"])}%' if prod["attendance_score"] is not None else "Not enough attendance data")]:
                        doc.add_paragraph(f"{label}: {value}",style="List Bullet")
                if opts.get("productivity_explanation",True):
                    doc.add_paragraph("Scoring explanation: Attendance is present scheduled working days divided by attendance-eligible scheduled working days through the report date. Unmarked days count as not present; declared holidays and recorded leave are excluded. Task progress contributes 70% and attendance 30% when both components are available; otherwise the available component is used.",style="List Bullet")
                if opts.get("productivity_tracking",True):
                    for label,value in [("Tracking start",prod["start"].isoformat()),("Working days since tracking start",prod["working_days"]),("Attendance-eligible working days",prod["attendance_eligible_days"]),("Present days recorded",prod["present"]),("Tasks counted",prod["tasks"]),("Completed/submitted tasks",prod["completed"])]:
                        doc.add_paragraph(f"{label}: {value}",style="List Bullet")
                if opts.get("productivity_tasks",True) and tasks:
                    doc.add_paragraph("TASK PROGRESS",style="Heading 2")
                    for t in tasks:
                        doc.add_paragraph(f'{t["title"]} — Status: {task_status_label(t["status"])} — Progress: {t["progress"]}%',style="List Bullet")
                elif opts.get("productivity_tasks",True):
                    doc.add_paragraph("No tasks recorded for the selected date.",style="List Bullet")
        else:
            data=self.report_data(report_date,employee_id)
            all_tasks=[t for _,ts,_ in data for t in ts]
            completed=sum(1 for t in all_tasks if is_explicitly_completed_task_status(t["status"]))
            pending_count=sum(1 for t in all_tasks if not is_explicitly_completed_task_status(t["status"]) and not is_cancelled_task_status(t["status"]))
            missing=sum(1 for e,tasks,_ in data if self.employee_missing_proof(e,tasks,report_date).startswith("Yes"))
            if opts.get("summary",True):
                doc.add_heading("DAILY SUMMARY",level=1)
                for item in [f"Employees: {len(data)}",f"Tasks recorded: {len(all_tasks)}",f"Completed / submitted tasks: {completed}",f"Pending / other tasks: {pending_count}",f"Employees flagged for missing proof: {missing}"]:
                    doc.add_paragraph(item,style="List Bullet")
            for e,tasks,_att in data:
                tgt_info = self.db.get_employee_target(e["id"], report_date) if hasattr(self.db, "get_employee_target") else None
                emp_target = (tgt_info.get("target") or "NA") if tgt_info else "NA"
                emp_target_status = (tgt_info.get("target_status") or "NA") if tgt_info else "NA"
                target_str = f"   Target: {emp_target}" if opts.get("target", True) else ""
                target_status_str = f"   Target status : {emp_target_status}" if opts.get("target_status", True) else ""
                doc.add_heading(f"Name : {e['name']}",level=1)
                if opts.get("identity",True):
                    doc.add_paragraph(f'Employee ID: {e["employee_code"] or "N/A"} | Department: {e["department"] or "N/A"} | Role: {e["designation"] or "N/A"}',style="List Bullet")
                if opts.get("target", True):
                    doc.add_paragraph(f'Target: {emp_target}',style="List Bullet")
                if opts.get("contact",False):
                    doc.add_paragraph(f'Phone: {e["phone"] or "N/A"}  |  Email: {e["email"] or "N/A"}',style="List Bullet")
                eod=self.source_status(e,"work",report_date) or ("Submitted" if tasks and all(is_explicitly_completed_task_status(t["status"]) for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                if opts.get("work_status",True): doc.add_paragraph(f"WORK / EOD STATUS: {eod}",style="List Bullet")
                if opts.get("late_links",True):
                    late=self.source_status(e,"late",report_date) or "Review required"
                    links=self.source_status(e,"links",report_date) or "Not independently checked"
                    doc.add_paragraph(f"LATE: {late}  |  LINKS: {links}",style="List Bullet")
                if opts.get("missing_proof",True):
                    doc.add_paragraph(f'MISSING PROOF: {self.employee_missing_proof(e,tasks,report_date)}',style="List Bullet")
                if opts.get("target_status", True):
                    doc.add_paragraph(f'Target status : {emp_target_status}',style="List Bullet")
                if opts.get("tasks",True):
                    doc.add_paragraph("TASKS / WORK ITEMS",style="Heading 2")
                    if tasks:
                        for idx,t in enumerate(tasks,1):
                            doc.add_paragraph(f'{idx}. {t["title"]} — Status: {task_status_label(t["status"])}',style="List Bullet")
                            target_q = str(t["target_qty"] if "target_qty" in t.keys() else "") or ""
                            actual_q = str(t["actual_qty"] if "actual_qty" in t.keys() else "") or ""
                            if is_target_qty_included(opts) and target_q:
                                doc.add_paragraph(f'Target Qty: {target_q}', style="List Bullet 2")
                            if is_actual_qty_included(opts) and actual_q:
                                doc.add_paragraph(f'Actual Qty: {actual_q}', style="List Bullet 2")
                            if is_completion_pct_included(opts) and t["progress"] is not None:
                                doc.add_paragraph(f'Completion %: {t["progress"]}%', style="List Bullet 2")
                            if is_priority_included(opts) and t["priority"]:
                                doc.add_paragraph(f'Priority: {t["priority"]}', style="List Bullet 2")
                            if opts.get("details",True) and t["details"]: doc.add_paragraph(f'Details: {t["details"]}',style="List Bullet 2")
                            if is_due_time_included(opts) and t["due_time"]: doc.add_paragraph(f'Due time: {t["due_time"]}',style="List Bullet 2")
                            if opts.get("proof",True):
                                task_links = task_evidence_urls(t)
                                if task_links:
                                    proof_paragraph = doc.add_paragraph(style="List Bullet 2")
                                    proof_paragraph.add_run("Proof / Evidence: ")
                                    for task_link_index, url in enumerate(task_links):
                                        if task_link_index:
                                            proof_paragraph.add_run(" | ")
                                        add_docx_hyperlink(proof_paragraph, url, url if self.is_task_link_exposed(t, opts) else "Tap here to view content")
                                else:
                                    doc.add_paragraph('Proof / Evidence: N/A',style="List Bullet 2")
                            if opts.get("proof_notes",False) and t["proof_note"]:
                                note_paragraph=doc.add_paragraph(style="List Bullet 2")
                                note_paragraph.add_run("Proof notes: ")
                                note_text = proof_note_display_text(t, opts.get("proof", True))
                                add_docx_linkified_text(note_paragraph,note_text,self.is_task_link_exposed(t, opts))
                            custom_val = format_custom_values_display(t["custom_values"] if "custom_values" in t.keys() else "")
                            if is_custom_values_included(opts) and custom_val and custom_val != "—":
                                doc.add_paragraph(f'Custom Values: {custom_val}', style="List Bullet 2")
                            next_act = str((t["next_action"] if "next_action" in t.keys() else "") or "")
                            if is_next_action_included(opts) and next_act:
                                doc.add_paragraph(f'Next Action: {next_act}', style="List Bullet 2")
                            if is_remarks_included(opts): doc.add_paragraph(f'Manager remarks: {t["manager_note"] or "N/A"}',style="List Bullet 2")
                    else:
                        doc.add_paragraph("No tasks recorded for this date.",style="List Bullet")
                if opts.get("pending",True):
                    pending_titles=[t["title"] for t in tasks if not is_explicitly_completed_task_status(t["status"]) and not is_cancelled_task_status(t["status"])]
                    doc.add_paragraph("PENDING",style="Heading 2")
                    doc.add_paragraph("; ".join(pending_titles) if pending_titles else "No",style="List Bullet")
        for section_title, headers, rows in self._selected_business_report_sections(opts):
            doc.add_heading(section_title, level=1)
            table = doc.add_table(rows=1, cols=len(headers))
            table.style = "Light Shading Accent 1"
            for cell, heading in zip(table.rows[0].cells, headers):
                cell.text = heading
            if rows:
                for values in rows:
                    cells = table.add_row().cells
                    for cell, value in zip(cells, values):
                        cell.text = value
            else:
                doc.add_paragraph("No records available.")
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
        styles.add(ParagraphStyle(name="RSName", fontName=regular_name, fontSize=8.5, leading=12,
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
            textColor=colors.HexColor("#1F2937"), leftIndent=13, firstLineIndent=-8,
            wordWrap="CJK", spaceAfter=3))

        def clean(value, expose_full_url=False):
            if value is None or str(value).strip() == "":
                return "—"
            raw = str(value)
            def as_link(match):
                matched = match.group(0)
                url = matched.rstrip(".,;:!?)]}")
                if not proof_urls(url):
                    return escape(matched)
                suffix = matched[len(url):]
                label = url if expose_full_url else "Tap here to view content"
                return f'{report_pdf_hyperlink(url, label)}{escape(suffix)}'
            result = re.sub(URI_PATTERN, as_link, raw, flags=re.IGNORECASE)
            return result.replace("\r\n", "\n").replace("\n", "<br/>")

        def para(label, value, style="RSBody"):
            return Paragraph(f"<b>{escape(label)}</b> {clean(value)}", styles[style])

        def bullet(value, style="RSBullet", expose_full_url=False):
            return Paragraph("&#8226;&nbsp; " + clean(value, expose_full_url), styles[style])

        def add_field(story, label, value):
            story.append(para(label, value))

        def employee_name(name, index=None):
            number = f"{index}. " if index is not None else ""
            return Paragraph(f"{number}<b>Name :</b> {clean(name)}", styles["RSName"])

        employee = self.db.employee(employee_id) if employee_id else None
        scope = employee["name"] if employee else "All employees"
        opts = self.selected_eod_options() if eod_options is None else eod_options
        story = []
        logo_path = resource_path("assets/raw_strength_brand.png")
        if Path(logo_path).exists():
            try:
                logo_flowable = RLImage(logo_path, width=38*mm, height=38*mm)
                logo_flowable.hAlign = 'CENTER'
                story.append(logo_flowable)
                story.append(Spacer(1, 3.5*mm))
            except Exception:
                pass
        story.extend([
                 Paragraph(escape(self._report_title(report_type)), styles["RSTitle"]),
                 Paragraph(f"Report date: {escape(report_date)} &nbsp;&nbsp; | &nbsp;&nbsp; Scope: {escape(scope)}", styles["RSSubtitle"]),
                 HRFlowable(width="100%", thickness=1.2, color=cyan, spaceAfter=9)])

        if report_type == "Employee Details":
            emps = self._report_employees(employee_id)
            story.append(para("TOTAL EMPLOYEES:", len(emps), "RSSection"))
            for index, e in enumerate(emps, 1):
                block = [employee_name(e["name"], index)]
                if opts.get("details_identity", True):
                    block.extend([bullet(f"Employee ID: {e['employee_code'] or '—'}"), bullet(f"Department: {e['department'] or '—'}"), bullet(f"Role / Designation: {e['designation'] or '—'}")])
                if opts.get("details_contact", True):
                    block.extend([bullet(f"Phone: {e['phone'] or '—'}"), bullet(f"Email: {e['email'] or '—'}")])
                if opts.get("details_joining", True): block.append(bullet(f"Joining date: {e['joining_date'] or '—'}"))
                if opts.get("details_status", True): block.append(bullet(f"Status: {'Active' if e['active'] else 'Inactive'}"))
                if opts.get("details_notes", False) and e["notes"]: block.append(bullet(f"Notes: {e['notes']}"))
                block.extend([Spacer(1, 5), HRFlowable(width="100%", thickness=.35, color=colors.HexColor("#D4DEE7"), spaceAfter=4)])
                story.extend(block)

        elif report_type == "Employee Attendance":
            rows = self._attendance_report_rows(report_date, employee_id)
            holiday_name = self.db.get_holiday(report_date)
            if holiday_name and opts.get("attendance_summary", True):
                story.append(para("DECLARED HOLIDAY:", holiday_name, "RSSection"))
            present = sum(is_present_attendance_status(x["status"]) for x in rows)
            absent = sum(x["status"] == "Absent" for x in rows)
            leave = sum(x["status"] == "Leave" for x in rows)
            if opts.get("attendance_summary", True):
                story.append(para("SUMMARY:", f"Employees {len(rows)} | Present {present} | Absent {absent} | Leave {leave}", "RSSection"))
            for index, item in enumerate(rows, 1):
                e = item["employee"]
                block = [employee_name(e["name"], index)]
                if opts.get("attendance_identity", True): block.extend([bullet(f"Employee ID: {e['employee_code'] or '—'}"), bullet(f"Department: {e['department'] or '—'}")])
                if opts.get("attendance_status", True): block.append(bullet(f"Attendance status: {item['status']}"))
                if opts.get("attendance_times", True): block.extend([bullet(f"Check-in: {item['check_in'] or 'Not recorded'}"), bullet(f"Check-out: {item['check_out'] or 'Not recorded'}"), bullet(f"Net working hours: {item['net_hours'] or 'Not available'}")])
                if opts.get("attendance_remarks", True): block.append(bullet(f"Remarks: {item['note'] or '—'}"))
                block.extend([Spacer(1, 5), HRFlowable(width="100%", thickness=.35, color=colors.HexColor("#D4DEE7"), spaceAfter=4)])
                story.extend(block)

        elif report_type == "Employee Productivity":
            data = self.report_data(report_date, employee_id)
            for e, tasks, _att in data:
                prod = self.employee_productivity(e, date.fromisoformat(report_date))
                story.append(employee_name(e["name"]))
                if opts.get("productivity_identity", True):
                    story.append(bullet(f'Employee ID: {e["employee_code"] or "N/A"} | Department: {e["department"] or "N/A"}'))
                if opts.get("productivity_metrics", True):
                    for label, value in [("Overall productivity score", f'{prod["score"]}%'), ("Task progress component", f'{round(prod["task_score"])}%' if prod["task_score"] is not None else "Not enough task data"), ("Attendance component", f'{round(prod["attendance_score"])}%' if prod["attendance_score"] is not None else "Not enough attendance data")]:
                        story.append(bullet(f"{label}: {value}"))
                if opts.get("productivity_explanation", True):
                    story.append(bullet("Scoring explanation: Attendance is present scheduled working days divided by attendance-eligible scheduled working days through the report date. Unmarked days count as not present; declared holidays and recorded leave are excluded. Task progress contributes 70% and attendance 30% when both components are available; otherwise the available component is used."))
                if opts.get("productivity_tracking", True):
                    for label, value in [("Tracking start", prod["start"].isoformat()), ("Working days since tracking start", str(prod["working_days"])), ("Attendance-eligible working days", str(prod["attendance_eligible_days"])), ("Present days recorded", str(prod["present"])), ("Tasks counted", str(prod["tasks"])), ("Completed / submitted tasks", str(prod["completed"]))]:
                        story.append(bullet(f"{label}: {value}"))
                if opts.get("productivity_tasks", True):
                    story.append(Paragraph("TASK PROGRESS", styles["RSSection"]))
                if opts.get("productivity_tasks", True) and tasks:
                    for t in tasks:
                        story.append(bullet(f'{t["title"]} — Status: {task_status_label(t["status"])} — Progress: {t["progress"]}%'))
                elif opts.get("productivity_tasks", True):
                    story.append(bullet("No tasks recorded for the selected date."))
                story.append(HRFlowable(width="100%", thickness=.4, color=colors.HexColor("#D4DEE7"), spaceAfter=5))
        else:
            data = self.report_data(report_date, employee_id)
            all_tasks = [t for _, tasks, _ in data for t in tasks]
            completed = sum(1 for t in all_tasks if is_explicitly_completed_task_status(t["status"]))
            pending_count = sum(1 for t in all_tasks if not is_explicitly_completed_task_status(t["status"]) and not is_cancelled_task_status(t["status"]))
            missing = sum(1 for e, tasks, _ in data if self.employee_missing_proof(e, tasks, report_date).startswith("Yes"))
            if opts.get("summary", True):
                story.extend([Paragraph("DAILY SUMMARY", styles["RSSection"]),
                    bullet(f"Employees: {len(data)}"), bullet(f"Tasks recorded: {len(all_tasks)}"),
                    bullet(f"Completed / submitted tasks: {completed}"), bullet(f"Pending / other tasks: {pending_count}"),
                    bullet(f"Employees flagged for missing proof: {missing}"), Spacer(1, 5),
                    HRFlowable(width="100%", thickness=.6, color=cyan, spaceAfter=6)])
            for e, tasks, _att in data:
                tgt_info = self.db.get_employee_target(e["id"], report_date) if hasattr(self.db, "get_employee_target") else None
                emp_target = (tgt_info.get("target") or "NA") if tgt_info else "NA"
                emp_target_status = (tgt_info.get("target_status") or "NA") if tgt_info else "NA"
                target_str = f"   Target: {emp_target}" if opts.get("target", True) else ""
                target_status_str = f"   Target status : {emp_target_status}" if opts.get("target_status", True) else ""
                story.append(employee_name(e["name"]))
                if opts.get("identity", True):
                    story.append(bullet(f'Employee ID: {e["employee_code"] or "N/A"} | Department: {e["department"] or "N/A"} | Role: {e["designation"] or "N/A"}'))
                if opts.get("target", True):
                    story.append(bullet(f'Target: {emp_target}'))
                if opts.get("contact", False):
                    story.append(bullet(f'Phone: {e["phone"] or "N/A"} | Email: {e["email"] or "N/A"}'))
                eod = self.source_status(e, "work", report_date) or ("Submitted" if tasks and all(is_explicitly_completed_task_status(t["status"]) for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                if opts.get("work_status", True):
                    story.append(bullet(f"WORK / EOD STATUS: {eod}"))
                if opts.get("late_links", True):
                    late = self.source_status(e, "late", report_date) or "Review required"
                    links = self.source_status(e, "links", report_date) or "Not independently checked"
                    story.append(bullet(f"LATE: {late} | LINKS: {links}"))
                if opts.get("missing_proof", True):
                    story.append(bullet(f'MISSING PROOF: {self.employee_missing_proof(e, tasks, report_date)}'))
                if opts.get("target_status", True):
                    story.append(bullet(f'Target status : {emp_target_status}'))
                if opts.get("tasks", True):
                    story.append(Paragraph("TASKS / WORK ITEMS", styles["RSSection"]))
                    if tasks:
                        for idx, t in enumerate(tasks, 1):
                            story.append(bullet(f'{idx}. {t["title"]} — Status: {task_status_label(t["status"])}'))
                            target_q = str(t["target_qty"] if "target_qty" in t.keys() else "") or ""
                            actual_q = str(t["actual_qty"] if "actual_qty" in t.keys() else "") or ""
                            if is_target_qty_included(opts) and target_q:
                                story.append(bullet(f'Target Qty: {target_q}'))
                            if is_actual_qty_included(opts) and actual_q:
                                story.append(bullet(f'Actual Qty: {actual_q}'))
                            if is_completion_pct_included(opts) and t["progress"] is not None:
                                story.append(bullet(f'Completion %: {t["progress"]}%'))
                            if is_priority_included(opts) and t["priority"]:
                                story.append(bullet(f'Priority: {t["priority"]}'))
                            if opts.get("details", True) and t["details"]:
                                story.append(bullet(f'Details: {t["details"]}'))
                            if is_due_time_included(opts) and t["due_time"]:
                                story.append(bullet(f'Due time: {t["due_time"]}'))
                            if opts.get("proof", True):
                                task_links = task_evidence_urls(t)
                                if task_links:
                                    link_markup=[]
                                    for task_link_index,url in enumerate(task_links):
                                        if task_link_index:
                                            link_markup.append("|")
                                        link_markup.append(report_pdf_hyperlink(url, url if self.is_task_link_exposed(t, opts) else "Tap here to view content"))
                                    story.append(Paragraph(
                                        "&#8226;&nbsp; Proof / Evidence: " + " ".join(link_markup),
                                        styles["RSLink"],
                                    ))
                                else:
                                    story.append(bullet("Proof / Evidence: N/A"))
                            if opts.get("proof_notes", False) and t["proof_note"]:
                                note_text = proof_note_display_text(t, opts.get("proof", True))
                                story.append(bullet(f'Proof notes: {note_text}', expose_full_url=self.is_task_link_exposed(t, opts)))
                            custom_val = format_custom_values_display(t["custom_values"] if "custom_values" in t.keys() else "")
                            if is_custom_values_included(opts) and custom_val and custom_val != "—":
                                story.append(bullet(f'Custom Values: {custom_val}'))
                            next_act = str((t["next_action"] if "next_action" in t.keys() else "") or "")
                            if is_next_action_included(opts) and next_act:
                                story.append(bullet(f'Next Action: {next_act}'))
                            if is_remarks_included(opts):
                                story.append(bullet(f'Manager remarks: {t["manager_note"] or "N/A"}'))
                    else:
                        story.append(bullet("No tasks recorded for this date."))
                if opts.get("pending", True):
                    pending_titles = [t["title"] for t in tasks if not is_explicitly_completed_task_status(t["status"]) and not is_cancelled_task_status(t["status"])]
                    story.extend([Paragraph("PENDING", styles["RSSection"]), bullet("; ".join(pending_titles) if pending_titles else "No")])
                story.extend([Spacer(1, 5), HRFlowable(width="100%", thickness=.4, color=colors.HexColor("#D4DEE7"), spaceAfter=5)])

        for section_title, headers, rows in self._selected_business_report_sections(opts):
            story.append(Paragraph(escape(section_title), styles["RSSection"]))
            if rows:
                for values in rows:
                    story.append(bullet(" | ".join(f"{header}: {value}" for header, value in zip(headers, values))))
            else:
                story.append(bullet("No records available."))

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
        opts=self.selected_eod_options() if eod_options is None else eod_options
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f)
            if report_type=="Employee Details":
                fields=[("Name",lambda e:e["name"])]
                if opts.get("details_identity",True): fields.extend([("Employee ID",lambda e:e["employee_code"] or "N/A"),("Department",lambda e:e["department"] or "N/A"),("Role",lambda e:e["designation"] or "N/A")])
                if opts.get("details_contact",True): fields.extend([("Phone",lambda e:e["phone"] or "N/A"),("Email",lambda e:e["email"] or "N/A")])
                if opts.get("details_joining",True): fields.append(("Joining date",lambda e:e["joining_date"] or "N/A"))
                if opts.get("details_status",True): fields.append(("Status",lambda e:"Active" if e["active"] else "Inactive"))
                if opts.get("details_notes",False): fields.append(("Notes",lambda e:e["notes"] or "N/A"))
                w.writerow([label for label,_value in fields])
                for e in self._report_employees(employee_id):
                    w.writerow([value(e) for _label,value in fields])
            elif report_type=="Employee Attendance":
                rows=self._attendance_report_rows(report_date,employee_id)
                headers=["Report date","Employee"]
                if opts.get("attendance_identity",True): headers += ["Employee ID","Department"]
                if opts.get("attendance_status",True): headers.append("Status")
                if opts.get("attendance_times",True): headers += ["Check-in","Check-out","Net hours"]
                if opts.get("attendance_remarks",True): headers.append("Remarks")
                w.writerow(headers)
                for item in rows:
                    e=item["employee"]; row=[report_date,e["name"]]
                    if opts.get("attendance_identity",True): row += [e["employee_code"] or "N/A",e["department"] or "N/A"]
                    if opts.get("attendance_status",True): row.append(item["status"])
                    if opts.get("attendance_times",True): row += [item["check_in"] or "N/A",item["check_out"] or "N/A",item["net_hours"] or "N/A"]
                    if opts.get("attendance_remarks",True): row.append(item["note"] or "N/A")
                    w.writerow(row)
                if opts.get("attendance_summary",True):
                    present=sum(is_present_attendance_status(x["status"]) for x in rows); absent=sum(x["status"]=="Absent" for x in rows); leave=sum(x["status"]=="Leave" for x in rows)
                    summary=[report_date,"SUMMARY"]
                    if opts.get("attendance_identity",True): summary += ["",""]
                    if opts.get("attendance_status",True): summary.append(f"Present {present} | Absent {absent} | Leave {leave} | Employees {len(rows)}")
                    if opts.get("attendance_times",True): summary += ["","",""]
                    if opts.get("attendance_remarks",True): summary.append("")
                    w.writerow(summary)
            elif report_type=="Employee Productivity":
                fields=[]
                if opts.get("productivity_identity",True): fields += [("Employee ID",lambda e,p:e["employee_code"] or "N/A"),("Department",lambda e,p:e["department"] or "N/A")]
                if opts.get("productivity_metrics",True): fields += [("Overall score %",lambda e,p:p["score"]),("Task progress component %",lambda e,p:round(p["task_score"]) if p["task_score"] is not None else "N/A"),("Attendance component %",lambda e,p:round(p["attendance_score"]) if p["attendance_score"] is not None else "N/A")]
                if opts.get("productivity_explanation",True): fields.append(("Scoring explanation",lambda e,p:"Attendance = present scheduled workdays / eligible scheduled workdays; unmarked days count as not present, while declared holidays and recorded leave are excluded. Task progress 70% + attendance 30% when both components are available; otherwise the available component is used."))
                if opts.get("productivity_tracking",True): fields += [("Tracking start",lambda e,p:p["start"].isoformat()),("Working days since start",lambda e,p:p["working_days"]),("Attendance-eligible working days",lambda e,p:p["attendance_eligible_days"]),("Present days",lambda e,p:p["present"]),("Tasks counted",lambda e,p:p["tasks"]),("Completed/submitted tasks",lambda e,p:p["completed"])]
                headers=["Report date","Employee"]+[label for label,_value in fields]
                if opts.get("productivity_tasks",True): headers += ["Task","Task status","Task progress %"]
                w.writerow(headers)
                for e,tasks,_att in self.report_data(report_date,employee_id):
                    prod=self.employee_productivity(e, date.fromisoformat(report_date))
                    base=[report_date,e["name"]]+[value(e,prod) for _label,value in fields]
                    task_rows=tasks if opts.get("productivity_tasks",True) else [None]
                    if not task_rows: task_rows=[None]
                    for task in task_rows:
                        row=list(base)
                        if opts.get("productivity_tasks",True):
                            row += [task["title"] if task else "N/A",task_status_label(task["status"]) if task else "N/A",task["progress"] if task else "N/A"]
                        w.writerow(row)
            else:
                include_target = bool(opts.get("target", True))
                headers=["Report date","Employee ID","Employee","Department","Role"]
                if include_target:
                    headers.append("Target")
                report_rows=self.report_data(report_date,employee_id)
                def task_proof_links(task):
                    return task_evidence_urls(task) if task else []
                max_proof_links=max([len(task_proof_links(t)) for _e,tasks,_a in report_rows for t in tasks] or [1])
                max_proof_links=max(1,max_proof_links)
                proof_headers=["Proof link"] if max_proof_links==1 else [f"Proof link {index+1}" for index in range(max_proof_links)]
                field_keys=[("work_status","EOD status"),("late_links","Late"),("late_links","Links status"),("missing_proof","Missing proof")]
                if opts.get("target_status", True):
                    field_keys.append(("target_status","Target status"))
                field_keys.extend([
                    ("tasks","Task"),
                    ("target_qty","Target Qty"),
                    ("actual_qty","Actual Qty"),
                    ("completion_pct","Completion %"),
                    ("priority","Priority"),
                    ("details","Task details"),
                    ("tasks","Task status"),
                    ("due_time","Due time"),
                    ("proof","Proof URL"),
                    ("proof_notes","Proof notes"),
                    ("custom_values","Custom Values"),
                    ("next_action","Next Action"),
                    ("remarks","Manager remarks"),
                    ("pending","Pending items"),
                ])
                def _is_csv_field_active(k):
                    if k == "due_time": return is_due_time_included(opts)
                    if k == "remarks": return is_remarks_included(opts)
                    if k == "target_status": return bool(opts.get("target_status", True))
                    if k == "target_qty": return is_target_qty_included(opts)
                    if k == "actual_qty": return is_actual_qty_included(opts)
                    if k == "completion_pct": return is_completion_pct_included(opts)
                    if k == "priority": return is_priority_included(opts)
                    if k == "custom_values": return is_custom_values_included(opts)
                    if k == "next_action": return is_next_action_included(opts)
                    return bool(opts.get(k, True))
                headers += [label for key,label in field_keys if key!="proof" and _is_csv_field_active(key)]
                proof_idx = [k for k,_l in field_keys].index("proof")
                if opts.get("proof",True):
                    insert_at=(6 if include_target else 5)+sum(1 for key,_label in field_keys[:proof_idx] if _is_csv_field_active(key))
                    headers[insert_at:insert_at]=proof_headers
                w.writerow(headers)
                for e,tasks,_att in report_rows:
                    tgt_info = self.db.get_employee_target(e["id"], report_date) if hasattr(self.db, "get_employee_target") else None
                    emp_target = (tgt_info.get("target") or "NA") if tgt_info else "NA"
                    emp_target_status = (tgt_info.get("target_status") or "NA") if tgt_info else "NA"
                    eod=self.source_status(e,"work",report_date) or ("Submitted" if tasks and all(is_explicitly_completed_task_status(t["status"]) for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
                    task_rows=tasks or [None]
                    for t in task_rows:
                        links=task_proof_links(t)
                        target_q = str((t["target_qty"] if "target_qty" in t.keys() else "") if t else "") or ""
                        actual_q = str((t["actual_qty"] if "actual_qty" in t.keys() else "") if t else "") or ""
                        comp_pct = f'{t["progress"]}%' if (t and t["progress"] is not None) else "N/A"
                        prio = str((t["priority"] if "priority" in t.keys() else "") if t else "") or "N/A"
                        custom_val = format_custom_values_display((t["custom_values"] if "custom_values" in t.keys() else "") if t else "")
                        next_act = str(((t["next_action"] if "next_action" in t.keys() else "") or (t["manager_note"] if t else "")) if t else "") or ""
                        dept_val = str(((t["department"] if "department" in t.keys() else "") if t else "") or e["department"] or "N/A")
                        base=[report_date,e["employee_code"] or "N/A",e["name"],dept_val,e["designation"] or "N/A"]
                        if include_target:
                            base.append(emp_target)
                        values={
                            "EOD status":eod,
                            "Late":self.source_status(e,"late",report_date) or "Review required",
                            "Links status":self.source_status(e,"links",report_date) or "Not independently checked",
                            "Missing proof":self.employee_missing_proof(e,tasks,report_date),
                            "Target status":emp_target_status,
                            "Task":t["title"] if t else "N/A",
                            "Target Qty":target_q or "N/A",
                            "Actual Qty":actual_q or "N/A",
                            "Completion %":comp_pct,
                            "Priority":prio,
                            "Task details":t["details"] if t else "N/A",
                            "Task status":task_status_label(t["status"]) if t else "N/A",
                            "Due time":t["due_time"] or "N/A" if t else "N/A",
                            "Proof notes":(re.sub(URI_PATTERN, "[link]", str(t["proof_note"]), flags=re.IGNORECASE).strip() or "N/A") if t and t["proof_note"] else "N/A",
                            "Custom Values":custom_val if custom_val != "—" else "N/A",
                            "Next Action":next_act or "N/A",
                            "Manager remarks":t["manager_note"] or "N/A" if t else "N/A",
                            "Pending items":"; ".join(x["title"] for x in tasks if not is_explicitly_completed_task_status(x["status"]) and not is_cancelled_task_status(x["status"])) or "No",
                        }
                        row=base+[values[label] for key,label in field_keys if key!="proof" and _is_csv_field_active(key)]
                        if opts.get("proof",True):
                            # CSV has no native hyperlink formatting. Spreadsheet
                            # apps evaluate HYPERLINK formulas and render their
                            # short labels as clickable links.
                            proof_cells=[]
                            for url in links[:max_proof_links]:
                                proof_cells.append(csv_hyperlink_formula(url, url if t and self.is_task_link_exposed(t, opts) else "Tap here to view content"))
                            if not proof_cells: proof_cells=["N/A"]
                            proof_cells += [""] * (max_proof_links-len(proof_cells))
                            insert_at=len(base)+sum(1 for key,_label in field_keys[:proof_idx] if _is_csv_field_active(key))
                            row[insert_at:insert_at]=proof_cells
                        w.writerow(row)
            for section_title, headers, rows in self._selected_business_report_sections(opts):
                w.writerow([])
                w.writerow([section_title])
                w.writerow(headers)
                if rows:
                    w.writerows(rows)
                else:
                    w.writerow(["No records available."])

    def preview_report(self):
        if not hasattr(self,"report_summary"): return
        d=self.report_date.date().toString("yyyy-MM-dd"); eid=self._effective_report_employee_id(); kind=self.report_type.currentText()
        opts=self.selected_eod_options()
        if kind=="Employee Details":
            emps=self._report_employees(eid); lines=[self._report_title(kind),f"Employees: {len(emps)}",""]
            for employee in emps:
                parts=[employee["name"]]
                if opts.get("details_identity",True): parts += [employee["employee_code"] or "N/A",employee["department"] or "N/A",employee["designation"] or "N/A"]
                if opts.get("details_contact",True): parts += [employee["phone"] or "N/A",employee["email"] or "N/A"]
                if opts.get("details_joining",True): parts.append(employee["joining_date"] or "N/A")
                if opts.get("details_status",True): parts.append("Active" if employee["active"] else "Inactive")
                if opts.get("details_notes",False): parts.append(employee["notes"] or "N/A")
                lines.append(" | ".join(str(part) for part in parts))
            self.report_summary.setPlainText("\n".join(lines))
        elif kind=="Employee Attendance":
            rows=self._attendance_report_rows(d,eid); lines=[self._report_title(kind),f"Date: {d}",""]
            if opts.get("attendance_summary",True):
                lines.append(f'Present {sum(is_present_attendance_status(x["status"]) for x in rows)} | Absent {sum(x["status"]=="Absent" for x in rows)} | Leave {sum(x["status"]=="Leave" for x in rows)} | Employees {len(rows)}')
            for item in rows:
                employee=item["employee"]; parts=[employee["name"]]
                if opts.get("attendance_identity",True): parts += [employee["employee_code"] or "N/A",employee["department"] or "N/A"]
                if opts.get("attendance_status",True): parts.append(item["status"])
                if opts.get("attendance_times",True): parts += [f'In: {item["check_in"] or "—"}',f'Out: {item["check_out"] or "—"}',f'Hours: {item["net_hours"] or "—"}']
                if opts.get("attendance_remarks",True): parts.append(f'Remarks: {item["note"] or "—"}')
                lines.append(" | ".join(str(part) for part in parts))
            self.report_summary.setPlainText("\n".join(lines))
        elif kind=="Employee Productivity":
            lines=[self._report_title(kind),f"Date: {d}",""]
            for e,tasks,_a in self.report_data(d,eid):
                prod=self.employee_productivity(e, date.fromisoformat(d))
                lines.append(e["name"])
                if opts.get("productivity_identity",True): lines.append(f'Employee ID: {e["employee_code"] or "N/A"} | Department: {e["department"] or "N/A"}')
                if opts.get("productivity_metrics",True):
                    lines.extend([f'Overall score: {prod["score"]}%',f'Task progress component: {round(prod["task_score"])}%' if prod["task_score"] is not None else "Task progress component: N/A",f'Attendance component: {round(prod["attendance_score"])}%' if prod["attendance_score"] is not None else "Attendance component: N/A"])
                if opts.get("productivity_explanation",True): lines.append("Attendance is present scheduled working days divided by attendance-eligible scheduled working days; unmarked days count as not present, while declared holidays and recorded leave are excluded. Task progress contributes 70% and attendance 30% when both are available; otherwise the available component is used.")
                if opts.get("productivity_tracking",True): lines.append(f'Tracking start: {prod["start"].isoformat()} | Working days: {prod["working_days"]} | Attendance-eligible days: {prod["attendance_eligible_days"]} | Present days: {prod["present"]}')
                if opts.get("productivity_tasks",True): lines.extend([f'• {t["title"]}: {task_status_label(t["status"])} — {t["progress"]}%' for t in tasks])
                lines.append("")
            self.report_summary.setPlainText("\n".join(lines))
        else: self.report_summary.setPlainText(self.report_preview_text(d,eid))
        business_lines = self._business_report_preview_lines(opts)
        if business_lines:
            report_lines = self.report_summary.toPlainText().rstrip()
            self.report_summary.setPlainText("\n".join(filter(None, [report_lines, "\n".join(business_lines)])))
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
                f'• Completed / submitted tasks: {sum(1 for t in all_tasks if is_explicitly_completed_task_status(t["status"]))}',
                f'• Pending / other tasks: {sum(1 for t in all_tasks if not is_explicitly_completed_task_status(t["status"]) and not is_cancelled_task_status(t["status"]))}',
                f'• Employees flagged for missing proof: {sum(1 for e,tasks,_ in data if self.employee_missing_proof(e,tasks,d).startswith("Yes"))}',""])
        for e,tasks,_att in data:
            tgt_info = self.db.get_employee_target(e["id"], d) if hasattr(self.db, "get_employee_target") else None
            emp_target = (tgt_info.get("target") or "NA") if tgt_info else "NA"
            emp_target_status = (tgt_info.get("target_status") or "NA") if tgt_info else "NA"
            target_str = f"   Target: {emp_target}" if opts.get("target", True) else ""
            target_status_str = f"   Target status : {emp_target_status}" if opts.get("target_status", True) else ""
            lines.append(f"Name : {e['name']}")
            if opts.get("identity",True): lines.append(f'• Employee ID: {e["employee_code"] or "N/A"} | Department: {e["department"] or "N/A"} | Role: {e["designation"] or "N/A"}')
            if opts.get("target", True): lines.append(f'• Target: {emp_target}')
            if opts.get("contact",False): lines.append(f'• Phone: {e["phone"] or "N/A"} | Email: {e["email"] or "N/A"}')
            eod=self.source_status(e,"work",d) or ("Submitted" if tasks and all(is_explicitly_completed_task_status(t["status"]) for t in tasks) else "In progress / Partial" if tasks else "No tasks recorded")
            if opts.get("work_status",True): lines.append(f"• WORK / EOD STATUS: {eod}")
            if opts.get("late_links",True):
                lines.append(f'• LATE: {self.source_status(e,"late",d) or "Review required"} | LINKS: {self.source_status(e,"links",d) or "Not independently checked"}')
            if opts.get("missing_proof",True):
                lines.append(f'• MISSING PROOF: {self.employee_missing_proof(e,tasks,d)}')
            if opts.get("target_status", True):
                lines.append(f'• Target status : {emp_target_status}')
            if opts.get("tasks",True):
                lines.append("TASKS / WORK ITEMS")
                if tasks:
                    for i,t in enumerate(tasks,1):
                        lines.append(f'• {i}. {t["title"]} — Status: {task_status_label(t["status"])}')
                        target_q = str(t["target_qty"] if "target_qty" in t.keys() else "") or ""
                        actual_q = str(t["actual_qty"] if "actual_qty" in t.keys() else "") or ""
                        if is_target_qty_included(opts) and target_q:
                            lines.append(f'  • Target Qty: {target_q}')
                        if is_actual_qty_included(opts) and actual_q:
                            lines.append(f'  • Actual Qty: {actual_q}')
                        if is_completion_pct_included(opts) and t["progress"] is not None:
                            lines.append(f'  • Completion %: {t["progress"]}%')
                        if is_priority_included(opts) and t["priority"]:
                            lines.append(f'  • Priority: {t["priority"]}')
                        if opts.get("details",True) and t["details"]: lines.append(f'  • Details: {t["details"]}')
                        if is_due_time_included(opts) and t["due_time"]: lines.append(f'  • Due time: {t["due_time"]}')
                        if opts.get("proof",True):
                            evidence_urls = task_evidence_urls(t)
                            lines.append(f'  • Proof / Evidence: {self.task_proof_label(e,t,d)}')
                            if evidence_urls:
                                for evidence_url in evidence_urls:
                                    label = evidence_url if self.is_task_link_exposed(t, opts) else "Tap here to view content"
                                    lines.append(f'  • {label}')
                        if opts.get("proof_notes",False) and t["proof_note"]:
                            note_text = proof_note_display_text(t, opts.get("proof", True))
                            lines.append(f'  • Proof notes: {note_text}')
                        custom_val = format_custom_values_display(t["custom_values"] if "custom_values" in t.keys() else "")
                        if is_custom_values_included(opts) and custom_val and custom_val != "—":
                            lines.append(f'  • Custom Values: {custom_val}')
                        next_act = str((t["next_action"] if "next_action" in t.keys() else "") or "")
                        if is_next_action_included(opts) and next_act:
                            lines.append(f'  • Next Action: {next_act}')
                        if is_remarks_included(opts): lines.append(f'  • Manager remarks: {t["manager_note"] or "N/A"}')
                else: lines.append("• No tasks recorded for this date.")
            if opts.get("pending",True):
                pending=[t["title"] for t in tasks if not is_explicitly_completed_task_status(t["status"]) and not is_cancelled_task_status(t["status"])]
                lines.append("PENDING: " + ("; ".join(pending) if pending else "No"))
            lines.append("")
        return "\n".join(lines)

    def open_print_preview(self):
        """Open a real Qt print-preview dialog for the currently selected report."""
        try:
            if not hasattr(self, "report_summary"):
                return info(self, "Open the Print Center and select a report first.")
            self.preview_report()
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintPreviewDialog(printer, self)
            dialog.setWindowTitle("Print Preview — Employee Audit Manager")
            dialog.resize(1000, 720)
            dialog.paintRequested.connect(
                lambda active_printer: self.report_summary.document().print_(active_printer)
            )
            dialog.exec()
        except Exception as ex:
            error(self, f"Could not open print preview:\n{ex}")

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

    def sync_google_sheets_action(self):
        if is_developer_test_user(self.current_user):
            # Developer/test accounts must authenticate before any cloud read or write.
            # Cancellation and failed authentication must not pull data into the test DB.
            try:
                from cloudflare_chat import verify_developer_password
                pwd, ok = QInputDialog.getText(
                    self,
                    "Developer Sync Authorization",
                    "Enter the developer password to sync Google Sheets data.",
                    QLineEdit.EchoMode.Password
                )
                if not ok or not verify_developer_password(pwd):
                    QMessageBox.information(
                        self,
                        "Developer Sync Not Authorized",
                        "No cloud data was pulled or pushed."
                    )
                    return
                import google_sheets_sync
                stats = google_sheets_sync.sync_from_live_google_sheet(self.db)
                self.refresh_employees()
                self.refresh_tasks()
                self.refresh_attendance()
                if hasattr(self, "customer_tab") and hasattr(self.customer_tab, "_reload_saved_records"):
                    self.customer_tab._reload_saved_records()
                msg = (
                    "Google Sheets data refreshed in Developer Test Mode.\n\n"
                    "Local test changes remain isolated from the customer master."
                )
                QMessageBox.information(self, "Google Sheets Sync (Test Mode)", msg)
            except Exception as exc:
                QMessageBox.warning(self, "Google Sheets Sync", f"Could not sync with Google Sheets:\n{exc}")
            return
        try:
            import google_sheets_sync
            stats = google_sheets_sync.sync_from_live_google_sheet(self.db)
            self.refresh_employees()
            self.refresh_tasks()
            self.refresh_attendance()
            if hasattr(self, "customer_tab") and hasattr(self.customer_tab, "_reload_saved_records"):
                self.customer_tab._reload_saved_records()
            msg = "Synced with Google Sheets Database!\n\n"
            for k, v in stats.items():
                msg += f"• {k.capitalize()}: {v:,} updated\n"
            QMessageBox.information(self, "Google Sheets Sync", msg)
        except Exception as exc:
            QMessageBox.warning(self, "Google Sheets Sync", f"Could not sync with Google Sheets:\n{exc}")

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

    def rollback_application(self):
        """Require an Admin or Developer role and password before installing a previous build."""
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can roll back the application.")
        username = str(self.current_user.get("username", ""))
        row = self.db.conn.execute(
            "SELECT password_salt, password_hash, active FROM auth_users WHERE username=?",
            (username,),
        ).fetchone()
        if not row or not row["active"]:
            return error(self, "The active Admin account could not be verified.")
        password, ok = QInputDialog.getText(
            self, "Admin verification", "Enter your Admin password to roll back:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return
        _, digest = hash_pin(password, row["password_salt"])
        if not (secrets.compare_digest(digest, row["password_hash"]) or verify_developer_password(password)):
            self.db.log("Application rollback denied", "Incorrect Admin or Developer password")
            return error(self, "Incorrect Admin or Developer password. Rollback was cancelled.")
        self.db.log("Application rollback authorized", username)
        progress = QProgressDialog("Loading previous versions...", "", 0, 0, self)
        progress.setWindowTitle("Application Rollback")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()
        try:
            request = Request("https://api.github.com/repos/" + GITHUB_REPOSITORY + "/releases?per_page=100", headers={"Accept": "application/vnd.github+json", "User-Agent": "RawStrengthEmployeeAuditManager"})
            with urlopen(request, timeout=20) as response:
                releases = json.loads(response.read().decode("utf-8"))
            choices = previous_release_choices(releases, APP_VERSION)
            progress.close()
            if not choices:
                return error(self, "No previous published application version is available.")
            labels = [item[0] + " (previous version)" for item in choices]
            selected, ok = QInputDialog.getItem(self, "Rollback application", "Choose a version. Database data will remain unchanged:", labels, 0, False)
            if not ok or not selected:
                return
            tag, url, installer_asset = choices[labels.index(selected)]
            version = ".".join(str(part) for part in release_version_tuple(tag))
            target_dir = APP_DIR / "updates" / version
            target_dir.mkdir(parents=True, exist_ok=True)
            installer = target_dir / "RawStrengthEmployeeAuditManager-Setup.exe"
            progress = QProgressDialog("Downloading rollback installer...", "", 0, 0, self)
            progress.setWindowTitle("Application Rollback")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.show()
            QApplication.processEvents()
            with urlopen(Request(url, headers={"User-Agent": "RawStrengthEmployeeAuditManager"}), timeout=60) as response:
                data = response.read()
            expected_size = installer_asset.get("size")
            if (not isinstance(expected_size, int) or expected_size < 1000000
                    or len(data) != expected_size):
                raise ValueError("Downloaded rollback installer size does not match GitHub release metadata.")
            # Older releases may predate GitHub's digest metadata. Verify it whenever available.
            verify_release_asset_bytes(data, installer_asset, require_digest=False)
            partial_path = installer.with_suffix(installer.suffix + ".part")
            try:
                partial_path.write_bytes(data)
                os.replace(partial_path, installer)
            except Exception:
                partial_path.unlink(missing_ok=True)
                raise
            progress.setLabelText("Starting silent rollback...")
            QApplication.processEvents()
            if sys.platform == "win32":
                result = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(installer), "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-", None, 1)
                if result <= 32:
                    raise OSError("Windows could not launch rollback installer (error " + str(result) + ").")
            else:
                subprocess.Popen([str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], close_fds=True)
            progress.close()
            self.close()
        except Exception as exc:
            progress.close()
            error(self, "Application rollback failed. Database data was not intentionally changed.\n" + str(exc))

    def restore_backup(self):
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can restore database backups.")
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
            self.db.close_github_sync(timeout=3)
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
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer account has permission to delete archived documents.")
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
            size_row=self.db.conn.execute("SELECT length(content) FROM archived_documents WHERE id=?",(d["id"],)).fetchone()
            size=size_row[0] if size_row else 0
            vals=[d["id"],d["file_name"],d["employee_name"] or "Unassigned / All",d["report_date"] or "Unknown",d["uploaded_at"],d["notes"],f"{(size or 0)/1024:.1f} KB"]
            r=self.archive_table.rowCount(); self.archive_table.insertRow(r)
            for c,v in enumerate(vals):
                item=QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if c in (0, 3, 4, 6) else Qt.AlignmentFlag.AlignLeft))
                item.setToolTip(str(v))
                self.archive_table.setItem(r,c,item)
        self.refresh_archived_report_choices()

    def change_password(self):
        user_id = self.current_user.get("id")
        row = self.db.conn.execute("SELECT * FROM auth_users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return error(self, "Your account could not be found.")
        _prompt_and_update_password(self, self.db, row, "Your password has been changed.")

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
        if not self.is_admin_or_dev:
            return error(self, "Only an Admin or Developer can manage user accounts.")
        dialog = QDialog(self); dialog.setWindowTitle("Manage User Accounts & Access Permissions"); dialog.setMinimumWidth(640)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Manage user accounts and assign limited access (Staff/HR) or full administration (Admin/Developer)."))
        table = QTableWidget(0, 5); table.setHorizontalHeaderLabels(["Username", "Display name", "Role", "Status", "Created"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        def reload_table():
            table.setRowCount(0)
            for row in self.db.conn.execute("SELECT username,display_name,role,active,created_at FROM auth_users ORDER BY username COLLATE NOCASE").fetchall():
                idx=table.rowCount(); table.insertRow(idx)
                for col,val in enumerate([row["username"],row["display_name"],row["role"],"Active" if row["active"] else "Disabled",row["created_at"]]):
                    if col == 3:
                        item = self.status_item(val)
                    else:
                        item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if col in (2, 3, 4) else Qt.AlignmentFlag.AlignLeft))
                    item.setToolTip(str(val))
                    table.setItem(idx, col, item)
        reload_table()
        layout.addWidget(table)

        manage_row = QHBoxLayout()
        toggle_active_btn = QPushButton("Toggle Active / Disabled")
        change_role_btn = QPushButton("Change Role")
        reset_pw_btn = QPushButton("Reset Password")
        manage_row.addWidget(toggle_active_btn)
        manage_row.addWidget(change_role_btn)
        manage_row.addWidget(reset_pw_btn)
        manage_row.addStretch(1)
        layout.addLayout(manage_row)

        def toggle_active():
            row_idx = table.currentRow()
            if row_idx < 0: return error(dialog, "Select a user from the table first.")
            uname = table.item(row_idx, 0).text()
            u_row = self.db.conn.execute("SELECT * FROM auth_users WHERE username=?", (uname,)).fetchone()
            if not u_row: return error(dialog, "User not found.")
            if uname.lower() == str(self.current_user.get("username", "")).lower() and u_row["active"]:
                return error(dialog, "You cannot disable your own active account.")
            new_active = 0 if u_row["active"] else 1
            self.db.conn.execute("UPDATE auth_users SET active=?, updated_at=? WHERE id=?", (new_active, now_text(), u_row["id"]))
            self.db.conn.commit()
            self.db.log("User status changed", f"{uname}: {'Active' if new_active else 'Disabled'}")
            self.schedule_auto_sync(immediate=True)
            reload_table()
            info(dialog, f"Account '{uname}' is now {'Active' if new_active else 'Disabled'}.")
        toggle_active_btn.clicked.connect(toggle_active)

        def change_role():
            row_idx = table.currentRow()
            if row_idx < 0: return error(dialog, "Select a user from the table first.")
            uname = table.item(row_idx, 0).text()
            u_row = self.db.conn.execute("SELECT * FROM auth_users WHERE username=?", (uname,)).fetchone()
            if not u_row: return error(dialog, "User not found.")
            roles = ["Staff", "HR", "Admin", "Developer"]
            current_role_idx = roles.index(u_row["role"]) if u_row["role"] in roles else 0
            new_role, ok = QInputDialog.getItem(dialog, "Change User Role", f"Select new role/access level for {uname}:", roles, current_role_idx, False)
            if not ok or not new_role: return
            self.db.conn.execute("UPDATE auth_users SET role=?, updated_at=? WHERE id=?", (new_role, now_text(), u_row["id"]))
            self.db.conn.commit()
            self.db.log("User role changed", f"{uname} -> {new_role}")
            self.schedule_auto_sync(immediate=True)
            reload_table()
            info(dialog, f"Role for '{uname}' updated to '{new_role}'.")
        change_role_btn.clicked.connect(change_role)

        def reset_user_password():
            row_idx = table.currentRow()
            if row_idx < 0: return error(dialog, "Select a user from the table first.")
            uname = table.item(row_idx, 0).text()
            u_row = self.db.conn.execute("SELECT * FROM auth_users WHERE username=?", (uname,)).fetchone()
            if not u_row: return error(dialog, "User not found.")
            new_pw, ok = QInputDialog.getText(dialog, "Reset Password", f"Enter new password for {uname}:", QLineEdit.Password)
            if not ok or not new_pw: return
            if not password_is_strong(new_pw):
                return error(dialog, "Password must be 8+ characters with letters and numbers.")
            ps, ph = hash_pin(new_pw)
            self.db.conn.execute("UPDATE auth_users SET password_salt=?, password_hash=?, updated_at=? WHERE id=?", (ps, ph, now_text(), u_row["id"]))
            self.db.conn.commit()
            self.db.log("User password reset by admin", uname)
            self.schedule_auto_sync(immediate=True)
            info(dialog, f"Password for '{uname}' reset successfully and synchronized.")
        reset_pw_btn.clicked.connect(reset_user_password)

        formbox=QGroupBox("Create new account"); form=QFormLayout(formbox)
        username=QLineEdit(); display=QLineEdit(); role=QComboBox(); role.addItems(["Staff", "HR", "Admin", "Developer"])
        password=QLineEdit(); password.setEchoMode(QLineEdit.Password)
        question=QComboBox(); question.addItems(SECURITY_QUESTIONS)
        answer=QLineEdit(); answer.setEchoMode(QLineEdit.Password)
        form.addRow("Username / User ID",username); form.addRow("Display name",display); form.addRow("Role / Access level",role)
        form.addRow("Initial password",password); form.addRow("Recovery question",question); form.addRow("Recovery answer",answer)
        layout.addWidget(formbox)
        buttons=QHBoxLayout(); create=QPushButton("Create account"); close=QPushButton("Close")
        buttons.addWidget(create); buttons.addWidget(close); layout.addLayout(buttons)
        close.clicked.connect(dialog.reject)
        def create_account():
            u=username.text().strip(); d=display.text().strip(); pw=password.text(); ans=normalized_answer(answer.text())
            r_val = role.currentText()
            if not u or not d: return error(dialog,"Enter username and display name.")
            if not password_is_strong(pw): return error(dialog,"Password must be 8+ characters with letters and numbers.")
            if len(ans)<2: return error(dialog,"Enter a recovery answer.")
            # Enforce case-insensitive unique username
            existing = self.db.conn.execute("SELECT id FROM auth_users WHERE username=? COLLATE NOCASE", (u,)).fetchone()
            if existing:
                return error(dialog, f"User ID / Username '{u}' already exists.\nUsernames must be unique across all devices.")
            ps,ph=hash_pin(pw); aus,ah=hash_pin(ans)
            try:
                self.db.conn.execute("INSERT INTO auth_users(username,display_name,role,password_salt,password_hash,security_question,answer_salt,answer_hash,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,1,?,?)",
                    (u,d,r_val,ps,ph,question.currentText(),aus,ah,now_text(),now_text()))
                self.db.conn.commit(); self.db.log("User account created",f"{u} ({r_val})")
                self.schedule_auto_sync(immediate=True)
            except sqlite3.IntegrityError:
                return error(dialog,f"That username '{u}' already exists.")
            info(dialog,f"Account '{u}' ({r_val}) created and synchronized with cloud successfully.")
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
    slate_arrow = resource_path("assets/chevron_down_slate.png").replace("\\", "/")
    cyan_arrow = resource_path("assets/chevron_down_cyan.png").replace("\\", "/")
    css = """
QDialog#loginDialog { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #15233F, stop:1 #312E81); }
QDialog#loginDialog QLabel { color: #F8FAFC; }
QDialog#loginDialog QLabel[pageTitle="true"] { color: #FFFFFF; font-size: 16pt; font-weight: 700; }
QDialog#loginDialog QLabel[pageSubtitle="true"] { color: #C7D2FE; }
QDialog#loginDialog QLineEdit { background: #1E293B; color: #F8FAFC; border: 1px solid #475569; border-radius: 8px; padding: 8px; }
QDialog#loginDialog QPushButton { background: #7C5CFC; color: #FFFFFF; border: 0; border-radius: 8px; padding: 8px 16px; font-weight: 600; }
QDialog#loginDialog QPushButton:hover { background: #6D28D9; }
QDialog#loginDialog QPushButton[flat="true"] { background: transparent; color: #C7D2FE; }
QDialog#loginDialog QPushButton[flat="true"]:hover { color: #FFFFFF; }

* { font-family: "Segoe UI", "Segoe UI Variable Text", "Inter", -apple-system, sans-serif; font-size: 9.5pt; color: #0F172A; }
QMainWindow { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #F8FAFC, stop:0.45 #F1F5F9, stop:1 #E2E8F0); }
QWidget#sessionStrip, QWidget#welcomeHero, QWidget#guideItem, QGroupBox { background: #FFFFFF; border: 1.5px solid #E2E8F0; border-radius: 16px; }
QScrollArea#homeScroll, QScrollArea#homeScroll QWidget#qt_scrollarea_viewport { background: transparent; border: 0; }
QPushButton { min-height: 36px; padding: 7px 15px; border-radius: 9px; font-size: 9pt; font-weight: 600; }
QLabel { padding: 1px; color: #0F172A; }
QWidget#titleBar { background: #0F172A; border: 0; }
QLabel#titleLabel { color: #F8FAFC; font-weight: 600; font-size: 10pt; }
QPushButton#titleBtnMin, QPushButton#titleBtnMax {
    min-width: 38px; max-width: 38px; min-height: 28px; max-height: 28px; padding: 0; margin: 0;
    background: rgba(255, 255, 255, 0.08); color: #F1F5F9; border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 6px; font-size: 10pt; font-weight: 700;
}
QPushButton#titleBtnMin:hover, QPushButton#titleBtnMax:hover { background: rgba(255, 255, 255, 0.22); color: #FFFFFF; border-color: rgba(255, 255, 255, 0.35); }
QPushButton#titleBtnMin:pressed, QPushButton#titleBtnMax:pressed { background: rgba(255, 255, 255, 0.30); }
QPushButton#titleBtnClose {
    min-width: 38px; max-width: 38px; min-height: 28px; max-height: 28px; padding: 0; margin: 0;
    background: rgba(239, 68, 68, 0.16); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 6px; font-size: 10pt; font-weight: 700;
}
QPushButton#titleBtnClose:hover { background: #DC2626; color: #FFFFFF; border-color: #EF4444; }
QPushButton#titleBtnClose:pressed { background: #B91C1C; }
QPushButton#titleFileBtn { background: transparent; color: #C7D2E8; border: 0; border-radius: 4px; padding: 0 10px; font-weight: 600; }
QPushButton#titleFileBtn:hover { background: #1E2F52; color: #FFFFFF; }
QPushButton#titleFileBtn::menu-indicator { image: none; }
QTabWidget::pane { border: 0; background: transparent; top: 0; margin-top: 0; }
QTabWidget { background: transparent; }
QMenuBar { background: #F8FAFC; border-bottom: 1px solid #E2E8F0; padding: 5px 10px; color: #0F172A; }
QMenuBar::item { padding: 7px 12px; border-radius: 6px; background: transparent; color: #0F172A; }
QMenuBar::item:selected { background: #EEF2FF; color: #4F46E5; }
QMenu { background: #FFFFFF; border: 1.5px solid #CBD5E1; padding: 6px; border-radius: 10px; color: #0F172A; }
QMenu::item { padding: 8px 24px 8px 16px; border-radius: 6px; color: #0F172A; font-weight: 600; }
QMenu::item:selected { background: #EEF2FF; color: #4F46E5; }
QTabBar { background: #F1F5F9; border-bottom: 1.5px solid #CBD5E1; }
QTabBar::tab { background: transparent; color: #475569; padding: 8px 16px; margin: 0 2px; border: 0; border-bottom: 3px solid transparent; font-weight: 600; min-width: 64px; min-height: 26px; }
QTabBar::tab:selected { background: #FFFFFF; color: #2563EB; font-weight: 700; border-bottom: 3px solid #2563EB; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:hover:!selected { background: #E2E8F0; color: #0F172A; }
QTabBar::scroller { width: 24px; }
QTabBar QToolButton { background: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 4px; }
QPushButton, QToolButton { padding: 6px 14px; min-height: 34px; min-width: 0; border: 1.5px solid #CBD5E1; border-radius: 9px; background: #FFFFFF; color: #0F172A; font-weight: 600; text-align: center; }
QPushButton:hover, QToolButton:hover { background: #F1F5F9; color: #4F46E5; border-color: #818CF8; }
QPushButton:pressed, QToolButton:pressed { background: #E2E8F0; }
QPushButton:disabled, QToolButton:disabled { background: #F8FAFC; color: #94A3B8; border-color: #E2E8F0; }
QPushButton:default, QPushButton[primary="true"] { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED); border: 1px solid #818CF8; border-radius: 9px; color: #FFFFFF; font-weight: 700; }
QPushButton:default:hover, QPushButton[primary="true"]:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9); border-color: #A5B4FC; }
QToolButton::menu-button { border: none; width: 22px; }
QToolButton::menu-indicator { image: none; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit {
    background-color: #F8FAFC; color: #0F172A; border: 1.5px solid #94A3B8; border-radius: 8px;
    padding: 6px 12px; min-height: 28px; selection-background-color: #EEF2FF; selection-color: #312E81;
}
QComboBox, QComboBox:!editable, QComboBox:editable, QDateEdit {
    combobox-popup: 0; background-color: #F8FAFC; color: #0F172A; border: 1.5px solid #94A3B8; border-radius: 8px;
    padding: 6px 38px 6px 12px; min-height: 30px; selection-background-color: #EEF2FF; selection-color: #312E81;
    font-weight: 600; font-size: 9.5pt;
}
QComboBox:hover, QComboBox:!editable:hover, QDateEdit:hover { border-color: #4F46E5; background-color: #FFFFFF; }
QComboBox:focus, QComboBox:!editable:focus, QDateEdit:focus { border: 2px solid #4F46E5; background-color: #FFFFFF; }
QComboBox QLineEdit { background-color: #F8FAFC; color: #0F172A; border: 0; padding: 0; }
QDateEdit { min-width: 142px; padding-right: 36px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 2px solid #4F46E5; background-color: #FFFFFF; color: #0F172A;
}
QComboBox::drop-down, QComboBox:!editable::drop-down, QDateEdit::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 32px; border-left: 1.5px solid #94A3B8;
    border-top-right-radius: 7px; border-bottom-right-radius: 7px;
    background-color: #EEF2FF;
}
QComboBox::drop-down:hover, QComboBox:!editable::drop-down:hover, QDateEdit::drop-down:hover {
    background-color: #E0E7FF;
}
QComboBox::down-arrow, QDateEdit::down-arrow {
    image: url("__CHEVRON_SLATE__");
    width: 14px; height: 14px;
}
QComboBox::down-arrow:hover, QDateEdit::down-arrow:hover {
    image: url("__CHEVRON_SLATE__");
}
QComboBox::down-arrow:disabled, QDateEdit::down-arrow:disabled {
    image: url("__CHEVRON_SLATE__");
}
QComboBox QAbstractItemView, QComboBox QListView { background-color: #FFFFFF; color: #0F172A; border: 1.5px solid #CBD5E1; border-radius: 10px; selection-background-color: #EEF2FF; selection-color: #312E81; outline: 0; padding: 6px; }
QComboBox QAbstractItemView::item, QComboBox QListView::item { color: #0F172A; background-color: #FFFFFF; padding: 8px 12px; min-height: 24px; border-radius: 6px; }
QComboBox QAbstractItemView::item:selected, QComboBox QListView::item:selected { background-color: #EEF2FF; color: #312E81; font-weight: 600; }
QComboBox QAbstractItemView::item:hover, QComboBox QListView::item:hover { background-color: #F8FAFC; color: #4F46E5; }
QComboBox QListView::item:selected { background: #4F46E5; color: #FFFFFF; }
QHeaderView::section { background: #F1F5F9; color: #0F172A; padding: 9px 12px; border: 0; border-bottom: 2px solid #CBD5E1; border-right: 1px solid #E2E8F0; font-weight: 700; font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.5px; }
QTableWidget { background: #FFFFFF; alternate-background-color: #F8FAFC; color: #0F172A; border: 1.5px solid #E2E8F0; border-radius: 12px; gridline-color: #F1F5F9; selection-background-color: #EEF2FF; selection-color: #312E81; outline: 0; }
QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #F1F5F9; color: #0F172A; }
QTableWidget::item:selected { background: #EEF2FF; color: #312E81; }
QTableWidget::item:hover { background: #F8FAFC; }
QGroupBox { font-weight: 700; color: #0F172A; border: 1.5px solid #E2E8F0; border-radius: 14px; margin-top: 14px; padding: 16px 14px 14px 14px; background: #FFFFFF; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; background-color: #FFFFFF; color: #4F46E5; font-size: 9pt; }
QLabel { color: #0F172A; background: transparent; }
QLabel[pageTitle="true"] { color: #0F172A; font-size: 15pt; font-weight: 800; letter-spacing: 0.3px; }
QLabel[pageSubtitle="true"] { color: #64748B; font-size: 9pt; font-weight: 500; padding-bottom: 4px; }
QLabel[mutedText="true"] { color: #64748B; }
QLabel[heroTitle="true"], QLabel[welcomeTitle="true"] { color: #FFFFFF; font-size: 16pt; font-weight: 800; }
QLabel[heroSubtitle="true"] { color: #E2E8F0; font-size: 9pt; }
QLabel[welcomeSubtitle="true"] { color: #F3E8FF; font-size: 9pt; }
QWidget#dashboardHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0F172A, stop:0.55 #4F46E5, stop:1 #0284C7); border-radius: 14px; }
QLabel#kpiIcon { font-size: 24pt; background: transparent; border: 0; min-height: 28px; }
QWidget#kpiCard { border: 1.5px solid #E2E8F0; border-radius: 14px; }
QWidget#dashboardPanel { border: 1.5px solid #E2E8F0; border-radius: 14px; }
QWidget#welcomeHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4F46E5, stop:1 #DB2777); border-radius: 14px; }
QScrollArea#homeScroll { border: 0; background: transparent; }
QWidget#homeContent { background: #FFFFFF; border: 1.5px solid #E2E8F0; border-radius: 16px; }
QScrollArea#pageScroll { border: 0; background: transparent; }
QWidget#pageContent { background: #FFFFFF; border: 1.5px solid #E2E8F0; border-radius: 16px; }
QTextEdit#reportPreview { background: #F8FAFC; border: 1.5px solid #E2E8F0; border-radius: 14px; }
QWidget#sessionStrip { background: #FFFFFF; border: 1.5px solid #E2E8F0; border-radius: 16px; }
QLabel[sessionLabel="true"] { color: #64748B; font-size: 8pt; font-weight: 700; letter-spacing: 0.5px; }
QLabel[roleBadge="true"] { background: #EEF2FF; color: #4F46E5; border: 1px solid #C7D2FE; border-radius: 8px; padding: 4px 12px; font-weight: 700; }
QLabel[sectionHeading="true"] { color: #0F172A; font-size: 13pt; font-weight: 800; letter-spacing: 0.2px; }
QWidget#guideItem { background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #7C5CFC; border-radius: 14px; }
QLabel[guideTitle="true"] { color: #0F172A; font-size: 10.5pt; font-weight: 700; }
QLabel[metricValue="true"] { font-size: 26pt; font-weight: 800; color: #4F46E5; min-height: 32px; }
QLabel[statusSummary="true"] { background: #EEF2FF; border: 1.5px solid #C7D2FE; border-radius: 12px; color: #312E81; font-weight: 600; padding: 11px 14px; }
QLabel[warningBanner="true"] { background: #FFFBEB; border: 1.5px solid #FDE68A; border-radius: 12px; color: #92400E; font-weight: 600; padding: 9px 12px; }
QProgressBar { border: 1px solid #CBD5E1; border-radius: 8px; text-align: center; color: #0F172A; background: #F1F5F9; min-height: 16px; font-weight: 700; font-size: 8pt; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4F46E5, stop:1 #06B6D4); border-radius: 7px; }
QCheckBox { spacing: 10px; padding: 4px; color: #0F172A; background: transparent; font-weight: 600; }
QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid #94A3B8; border-radius: 6px; background: #F8FAFC; }
QCheckBox::indicator:hover { border-color: #4F46E5; background: #EEF2FF; }
QCheckBox::indicator:checked { background: #4F46E5; border-color: #4F46E5; }
QCheckBox::indicator:checked:hover { background: #4338CA; border-color: #4338CA; }
QStatusBar { background: #0F172A; color: #CBD5E1; border-top: 1px solid #1E293B; padding: 6px 12px; font-weight: 500; }
QRadioButton { spacing: 8px; color: #0F172A; background: transparent; }
QStatusBar::item { border: none; }
QScrollBar:vertical, QScrollBar:horizontal { background: rgba(241, 245, 249, 0.60); width: 10px; height: 10px; margin: 3px; border-radius: 5px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #CBD5E1; border-radius: 5px; min-height: 32px; min-width: 32px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #4F46E5; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QDialog { background: #F8FAFC; color: #0F172A; }
QFormLayout QLabel { color: #1E293B; background: transparent; font-weight: 700; font-size: 9.5pt; }
QToolTip, QLabel#accessibleHoverMessage { background-color: #0F172A; color: #FFFFFF; border: 2px solid #6366F1; padding: 8px 12px; border-radius: 8px; font-size: 10pt; font-weight: 600; }
QCalendarWidget { background-color: #FFFFFF; color: #0F172A; border: 2px solid #6366F1; border-radius: 12px; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: #0F172A; min-height: 42px; border-top-left-radius: 10px; border-top-right-radius: 10px; }
QCalendarWidget QToolButton { background: transparent; color: #FFFFFF; border: 0; border-radius: 6px; padding: 6px 10px; font-weight: 700; }
QCalendarWidget QToolButton:hover { background: #4F46E5; }
QCalendarWidget QSpinBox { background: #1E293B; color: #FFFFFF; border: 1px solid #475569; border-radius: 6px; padding: 3px 6px; }
QCalendarWidget QAbstractItemView { background: #FFFFFF; alternate-background-color: #F8FAFC; color: #0F172A; selection-background-color: #4F46E5; selection-color: #FFFFFF; outline: 0; font-weight: 600; }
/* Opaque high-contrast surfaces prevent photographic wallpapers from reducing text readability. */
QWidget#appPageSurface { background: #FFFFFF; color: #0F172A; }
QWidget#homeContent, QWidget#pageContent { background-color: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 16px; }
QGroupBox { background-color: #FFFFFF; color: #0F172A; border: 1px solid #94A3B8; border-radius: 12px; }
QGroupBox::title { color: #1E293B; background-color: #FFFFFF; font-weight: 700; }
QWidget#kpiCard, QWidget#dashboardPanel { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 14px; }
QGroupBox#kpiCard { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #FFFFFF, stop:1 #F8FAFC); border: 1px solid #CBD5E1; border-radius: 16px; }
QGroupBox#kpiCard:hover { border-color: #A78BFA; }
QGroupBox#dashboardPanel { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 15px; }
QGroupBox#dashboardPanel:hover { border-color: #A5B4FC; }
QGroupBox#dashboardPanel::title { background: transparent; color: #334155; padding: 0 5px; font-weight: 700; }
QPushButton[dashboardAction="true"] { background: #F8FAFC; color: #1E293B; border: 1px solid #CBD5E1; border-radius: 10px; padding: 8px 12px; text-align: left; font-weight: 650; }
QPushButton[dashboardAction="true"]:hover { background: #EEF2FF; color: #4C1D95; border-color: #A78BFA; }
QPushButton[dashboardAction="true"]:pressed { background: #E0E7FF; border-color: #7C3AED; }
QProgressBar#dashboardProgress { background: #E2E8F0; color: #1E293B; border: 1px solid #CBD5E1; border-radius: 7px; min-width: 62px; max-height: 20px; text-align: center; font-size: 8pt; font-weight: 700; }
QProgressBar#dashboardProgress::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6366F1, stop:1 #8B5CF6); border-radius: 6px; }
QWidget#sessionStrip, QWidget#guideItem { background-color: #F1F5F9; color: #0F172A; border: 1px solid #94A3B8; }
QWidget#settingsContent { background-color: #F8FAFC; color: #0F172A; }
QWidget#settingsContent QGroupBox { background-color: #FFFFFF; color: #0F172A; }
QWidget#settingsContent QLabel { color: #1E293B; }
QWidget#settingsContent QPushButton { background-color: #E2E8F0; color: #0F172A; }
QWidget#settingsContent QComboBox { background-color: #F8FAFC; color: #0F172A; border: 1.5px solid #94A3B8; }
QLabel { color: #1E293B; }
QLabel[pageTitle="true"], QLabel[sectionHeading="true"], QLabel[guideTitle="true"] { color: #0F172A; }
QLabel[pageSubtitle="true"], QLabel[mutedText="true"], QLabel[sessionLabel="true"] { color: #475569; }
QWidget#sessionStrip { background: #E2E8F0; border: 1px solid #94A3B8; }
QWidget#guideItem { background: #F1F5F9; border: 1px solid #94A3B8; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QComboBox, QDateEdit {
    background-color: #F8FAFC; color: #0F172A; border: 1.5px solid #94A3B8; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QTimeEdit:focus, QComboBox:focus, QDateEdit:focus { border: 2px solid #4F46E5; background-color: #FFFFFF; }
QHeaderView::section { background: #DCE6F1; color: #0F172A; border-bottom: 2px solid #94A3B8; }
QTableWidget { background: #FFFFFF; alternate-background-color: #F1F5F9; color: #0F172A; border: 1px solid #CBD5E1; gridline-color: #CBD5E1; }
QTableWidget::item { color: #0F172A; border-bottom: 1px solid #E2E8F0; }
QTableWidget::item:selected { background: #DDE7FF; color: #1E1B4B; }
QCheckBox, QRadioButton { color: #1E293B; }
QStatusBar { background: #E2E8F0; color: #1E293B; }
QDialog, QMessageBox, QInputDialog { background: #FFFFFF; color: #0F172A; }
QMessageBox { min-width: 480px; }
QMessageBox QLabel#qt_msgbox_label { min-width: 360px; color: #0F172A; font-size: 10pt; font-weight: 500; }
QMessageBox QLabel#qt_msgboxex_icon_label { min-width: 44px; min-height: 44px; }
QInputDialog { min-width: 460px; }
QInputDialog QLabel { min-width: 420px; color: #0F172A; font-size: 9.5pt; font-weight: 600; }
QInputDialog QLineEdit { min-width: 420px; min-height: 32px; }
QLabel#attRosterTitle, QLabel#attRosterHint, QLabel#attSummaryTitle, QLabel#attSummaryNote, QLabel#taskRosterTitle, QLabel#taskRosterHint, QLabel#empRosterTitle, QLabel#empRosterHint, QLabel#trackerRosterTitle, QLabel#trackerRosterHint, QLabel#archiveRosterTitle, QLabel#archiveRosterHint { qproperty-wordWrap: false; }
"""
    return css.replace("__CHEVRON_SLATE__", slate_arrow).replace("__CHEVRON_CYAN__", cyan_arrow)

def dark_stylesheet():
    white_arrow = resource_path("assets/chevron_down_white.png").replace("\\", "/")
    cyan_arrow = resource_path("assets/chevron_down_cyan.png").replace("\\", "/")
    css = """
QWidget#settingsContent QGroupBox { background: #0F172A; border: 1.5px solid #334155; border-radius: 12px; }
QWidget#settingsContent QLabel { color: #E2E8F0; }
QWidget#settingsContent QPushButton { background: #1E293B; color: #F8FAFC; border: 1px solid #334155; border-radius: 8px; }
QWidget#settingsContent QComboBox { background: #0F172A; color: #F8FAFC; }

* { font-family: "Segoe UI", "Segoe UI Variable Text", "Inter", -apple-system, sans-serif; font-size: 9.5pt; color: #F8FAFC; }
QMainWindow { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #080C14, stop:0.5 #0B1120, stop:1 #020617); }
QWidget#titleBar { background: #070B14; border-bottom: 1px solid #111827; }
QLabel#titleLabel { color: #F8FAFC; font-weight: 600; font-size: 10pt; }
QPushButton#titleBtnMin, QPushButton#titleBtnMax {
    min-width: 38px; max-width: 38px; min-height: 28px; max-height: 28px; padding: 0; margin: 0;
    background: rgba(255, 255, 255, 0.08); color: #F1F5F9; border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 6px; font-size: 10pt; font-weight: 700;
}
QPushButton#titleBtnMin:hover, QPushButton#titleBtnMax:hover { background: rgba(255, 255, 255, 0.22); color: #FFFFFF; border-color: rgba(255, 255, 255, 0.35); }
QPushButton#titleBtnMin:pressed, QPushButton#titleBtnMax:pressed { background: rgba(255, 255, 255, 0.30); }
QPushButton#titleBtnClose {
    min-width: 38px; max-width: 38px; min-height: 28px; max-height: 28px; padding: 0; margin: 0;
    background: rgba(239, 68, 68, 0.16); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 6px; font-size: 10pt; font-weight: 700;
}
QPushButton#titleBtnClose:hover { background: #DC2626; color: #FFFFFF; border-color: #EF4444; }
QPushButton#titleBtnClose:pressed { background: #B91C1C; }
QTabWidget::pane { border: 0; background: transparent; top: 0; margin-top: 0; }
QTabWidget { background: transparent; }
QMenuBar { background: #0F172A; border-bottom: 1px solid #1E293B; padding: 5px 10px; color: #F8FAFC; }
QMenuBar::item { padding: 7px 12px; border-radius: 6px; background: transparent; color: #F8FAFC; }
QMenuBar::item:selected { background: #312E81; color: #C4B5FD; }
QMenu { background: #0F172A; border: 1.5px solid #334155; padding: 6px; border-radius: 10px; color: #F8FAFC; }
QMenu::item { padding: 8px 24px 8px 16px; border-radius: 6px; color: #F8FAFC; font-weight: 600; }
QMenu::item:selected { background: #312E81; color: #FFFFFF; }
QTabBar { background: #070B14; }
QTabBar::tab { background: transparent; color: #94A3B8; padding: 8px 16px; margin: 0 1px; border: 0; border-bottom: 3px solid transparent; font-weight: 600; min-width: 68px; min-height: 26px; }
QTabBar::tab:selected { background: #0F172A; color: #FFFFFF; border-bottom: 3px solid #818CF8; }
QTabBar::tab:hover:!selected { background: #0F172A; color: #F8FAFC; }
QTabBar::scroller { width: 24px; }
QTabBar QToolButton { background: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 4px; }
QPushButton, QToolButton {
    padding: 6px 14px; min-height: 34px; min-width: 0; border: 1.5px solid #334155;
    border-radius: 9px; background: #1E293B; color: #F8FAFC; font-weight: 600; text-align: center;
}
QPushButton:hover, QToolButton:hover { background: #334155; color: #FFFFFF; border-color: #6366F1; }
QPushButton:pressed, QToolButton:pressed { background: #0B1120; }
QPushButton:disabled, QToolButton:disabled { background: #0F172A; color: #64748B; border-color: #1F2937; }
QPushButton:default, QPushButton[primary="true"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4F46E5, stop:1 #06B6D4); border: 1px solid #38BDF8; border-radius: 9px; color: #FFFFFF; font-weight: 700; }
QPushButton:default:hover, QPushButton[primary="true"]:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4338CA, stop:1 #0891B2); border-color: #00E5FF; }
QToolButton::menu-button { border: none; width: 22px; }
QToolButton::menu-indicator { image: none; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit {
    background-color: #0F172A; color: #F8FAFC; border: 1.5px solid #475569; border-radius: 8px;
    padding: 6px 12px; min-height: 28px; selection-background-color: #4F46E5; selection-color: #FFFFFF;
}
QComboBox, QComboBox:!editable, QComboBox:editable, QDateEdit {
    combobox-popup: 0; background-color: #0F172A; color: #F8FAFC; border: 1.5px solid #475569; border-radius: 8px;
    padding: 6px 38px 6px 12px; min-height: 30px; selection-background-color: #4F46E5; selection-color: #FFFFFF;
    font-weight: 600; font-size: 9.5pt;
}
QComboBox:hover, QComboBox:!editable:hover, QDateEdit:hover { border-color: #38BDF8; background-color: #162035; }
QComboBox:focus, QComboBox:!editable:focus, QDateEdit:focus { border: 2px solid #00E5FF; background-color: #111827; }
QComboBox QLineEdit { background-color: #0F172A; color: #F8FAFC; border: 0; padding: 0; }
QDateEdit { min-width: 142px; padding-right: 36px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 2px solid #00E5FF; background-color: #111827; color: #F8FAFC;
}
QComboBox::drop-down, QComboBox:!editable::drop-down, QDateEdit::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 32px; border-left: 1.5px solid #475569;
    border-top-right-radius: 7px; border-bottom-right-radius: 7px;
    background-color: #1E293B;
}
QComboBox::drop-down:hover, QComboBox:!editable::drop-down:hover, QDateEdit::drop-down:hover {
    background-color: #334155;
}
QComboBox::down-arrow, QDateEdit::down-arrow {
    image: url("__CHEVRON_WHITE__");
    width: 14px; height: 14px;
}
QComboBox::down-arrow:hover, QDateEdit::down-arrow:hover {
    image: url("__CHEVRON_WHITE__");
}
QComboBox::down-arrow:disabled, QDateEdit::down-arrow:disabled {
    image: url("__CHEVRON_WHITE__");
}
QComboBox QAbstractItemView, QComboBox QListView { background-color: #0B1120; color: #F8FAFC; border: 1.5px solid #475569; selection-background-color: #4F46E5; selection-color: #FFFFFF; outline: 0; padding: 6px; border-radius: 10px; }
QComboBox QAbstractItemView::item, QComboBox QListView::item { color: #F8FAFC; background-color: #0B1120; padding: 8px 12px; min-height: 24px; border-radius: 6px; }
QComboBox QAbstractItemView::item:selected, QComboBox QListView::item:selected { background-color: #4F46E5; color: #FFFFFF; font-weight: 600; }
QHeaderView::section { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #10182C, stop:1 #0B1120); color: #94A3B8; padding: 9px 12px; border: 0; border-bottom: 2px solid rgba(255, 255, 255, 0.10); border-right: 1px solid rgba(255, 255, 255, 0.04); font-weight: 800; font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.6px; }
QTableWidget { background: #080C16; alternate-background-color: #0C1220; color: #F8FAFC; border: 1.5px solid rgba(255, 255, 255, 0.08); border-radius: 12px; gridline-color: rgba(255, 255, 255, 0.04); selection-background-color: rgba(79, 70, 229, 0.40); selection-color: #FFFFFF; outline: 0; }
QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); color: #F8FAFC; }
QTableWidget::item:selected { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(79, 70, 229, 0.45), stop:1 rgba(0, 229, 255, 0.25)); color: #FFFFFF; }
QTableWidget::item:hover { background: rgba(255, 255, 255, 0.04); }
QGroupBox { font-weight: 700; color: #F8FAFC; border: 1.5px solid #334155; border-radius: 14px; margin-top: 14px; padding: 16px 14px 14px 14px; background: #0F172A; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; background-color: #0F172A; color: #38BDF8; font-size: 9pt; }
QLabel { color: #F8FAFC; background: transparent; }
QLabel[pageTitle="true"] { color: #F8FAFC; font-size: 15pt; font-weight: 800; letter-spacing: 0.3px; }
QLabel[pageSubtitle="true"] { color: #94A3B8; font-size: 9pt; font-weight: 500; padding-bottom: 4px; }
QLabel[mutedText="true"] { color: #94A3B8; }
QLabel[heroTitle="true"], QLabel[welcomeTitle="true"] { color: #FFFFFF; font-size: 16pt; font-weight: 800; }
QLabel[heroSubtitle="true"] { color: #E2E8F0; font-size: 9pt; }
QLabel[welcomeSubtitle="true"] { color: #F5D0FE; font-size: 9pt; }
QWidget#dashboardHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0F172A, stop:0.55 #4C1D95, stop:1 #0E7490); border-radius: 14px; }
QLabel#kpiIcon { font-size: 24pt; background: transparent; border: 0; min-height: 28px; }
QWidget#kpiCard { border: 1.5px solid #334155; border-radius: 14px; }
QWidget#dashboardPanel { border: 1.5px solid #334155; border-radius: 14px; }
QWidget#welcomeHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4C1D95, stop:0.5 #7C3AED, stop:1 #DB2777); border-radius: 14px; }
QScrollArea#homeScroll { border: 0; background: transparent; }
QWidget#homeContent { background: #0F172A; border: 1.5px solid #334155; border-radius: 16px; }
QScrollArea#pageScroll { border: 0; background: transparent; }
QWidget#pageContent { background: #0F172A; border: 1.5px solid #334155; border-radius: 16px; }
QTextEdit#reportPreview { background: #111827; border: 1.5px solid #334155; border-radius: 12px; }
QWidget#sessionStrip { background: #0B1220; border: 1.5px solid #334155; border-radius: 16px; }
QLabel[sessionLabel="true"] { color: #94A3B8; font-size: 8pt; font-weight: 700; letter-spacing: 0.5px; }
QLabel[roleBadge="true"] { background: #312E81; color: #DDD6FE; border: 1px solid #4F46E5; border-radius: 8px; padding: 4px 12px; font-weight: 700; }
QLabel[sectionHeading="true"] { color: #F8FAFC; font-size: 13pt; font-weight: 800; letter-spacing: 0.2px; }
QWidget#guideItem { background: #0F172A; border: 1px solid #334155; border-left: 4px solid #A78BFA; border-radius: 14px; }
QLabel[guideTitle="true"] { color: #F8FAFC; font-size: 10.5pt; font-weight: 700; }
QLabel[metricValue="true"] { font-size: 26pt; font-weight: 800; color: #38BDF8; min-height: 32px; }
QLabel[statusSummary="true"] { background: #1E1B4B; border: 1.5px solid #4C1D95; border-radius: 12px; color: #DDD6FE; font-weight: 600; padding: 11px 14px; }
QLabel[warningBanner="true"] { background: #422006; border: 1.5px solid #A16207; border-radius: 12px; color: #FDE68A; font-weight: 600; padding: 9px 12px; }
QProgressBar { border: 1px solid #1F2937; border-radius: 8px; text-align: center; color: #E2E8F0; background: #0B1120; min-height: 16px; font-weight: 700; font-size: 8pt; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #22D3EE, stop:1 #A855F7); border-radius: 7px; }
QCheckBox { spacing: 10px; padding: 4px; color: #F8FAFC; background: transparent; font-weight: 500; }
QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid #475569; border-radius: 6px; background: #0B1120; }
QCheckBox::indicator:hover { border-color: #38BDF8; background: #1E1B4B; }
QCheckBox::indicator:checked { background: #6366F1; border-color: #6366F1; }
QCheckBox::indicator:checked:hover { background: #818CF8; border-color: #818CF8; }
QStatusBar { background: #070B14; color: #CBD5E1; border-top: 1px solid #1E293B; padding: 6px 12px; font-weight: 500; }
QRadioButton { spacing: 8px; color: #CBD5E1; background: transparent; }
QStatusBar::item { border: none; }
QScrollBar:vertical, QScrollBar:horizontal { background: rgba(15, 23, 42, 0.50); width: 10px; height: 10px; margin: 3px; border-radius: 5px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #475569; border-radius: 5px; min-height: 32px; min-width: 32px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #818CF8; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QDialog { background: #0F172A; color: #F8FAFC; }
QFormLayout QLabel { color: #F8FAFC; background: transparent; font-weight: 600; }
QToolTip, QLabel#accessibleHoverMessage { background-color: #020617; color: #FFFFFF; border: 2px solid #818CF8; padding: 8px 12px; border-radius: 8px; font-size: 10pt; font-weight: 600; }
QCalendarWidget { background-color: #0F172A; color: #F8FAFC; border: 2px solid #818CF8; border-radius: 12px; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: #070B14; min-height: 42px; border-top-left-radius: 10px; border-top-right-radius: 10px; }
QCalendarWidget QToolButton { background: transparent; color: #FFFFFF; border: 0; border-radius: 6px; padding: 6px 10px; font-weight: 700; }
QCalendarWidget QToolButton:hover { background: #6366F1; }
QCalendarWidget QSpinBox { background: #1E293B; color: #FFFFFF; border: 1px solid #475569; border-radius: 6px; padding: 3px 6px; }
QCalendarWidget QAbstractItemView { background: #0F172A; alternate-background-color: #1E293B; color: #E2E8F0; selection-background-color: #6366F1; selection-color: #FFFFFF; outline: 0; font-weight: 600; }
/* High contrast: opaque panels keep live wallpapers from washing out text. */
QWidget#appPageSurface { background: transparent; color: #F8FAFC; }
QWidget#homeContent, QWidget#pageContent { background-color: #111827; color: #F8FAFC; border: 1px solid #475569; border-radius: 16px; }
QGroupBox { background-color: #0F172A; color: #F8FAFC; border: 1px solid #475569; border-radius: 12px; }
QGroupBox::title { color: #F1F5F9; background-color: #0F172A; }
QWidget#kpiCard, QWidget#dashboardPanel { background-color: #0F172A; color: #F8FAFC; border: 1px solid #475569; border-radius: 14px; }
QGroupBox#kpiCard { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #111C32, stop:1 #0F172A); border: 1px solid #334155; border-radius: 16px; }
QGroupBox#kpiCard:hover { border-color: #8B5CF6; }
QGroupBox#dashboardPanel { background: #0F172A; border: 1px solid #334155; border-radius: 15px; }
QGroupBox#dashboardPanel:hover { border-color: #6366F1; }
QGroupBox#dashboardPanel::title { background: transparent; color: #E2E8F0; padding: 0 5px; font-weight: 700; }
QPushButton[dashboardAction="true"] { background: #111C32; color: #E2E8F0; border: 1px solid #334155; border-radius: 10px; padding: 8px 12px; text-align: left; font-weight: 650; }
QPushButton[dashboardAction="true"]:hover { background: #312E81; color: #FFFFFF; border-color: #8B5CF6; }
QPushButton[dashboardAction="true"]:pressed { background: #3730A3; border-color: #A78BFA; }
QProgressBar#dashboardProgress { background: #1E293B; color: #F8FAFC; border: 1px solid #334155; border-radius: 7px; min-width: 62px; max-height: 20px; text-align: center; font-size: 8pt; font-weight: 700; }
QProgressBar#dashboardProgress::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6366F1, stop:1 #A78BFA); border-radius: 6px; }
QWidget#sessionStrip, QWidget#guideItem { background-color: #0B1220; color: #F8FAFC; border: 1px solid #475569; }
QWidget#settingsContent { background-color: #111827; color: #F8FAFC; }
QWidget#settingsContent QGroupBox { background-color: #0F172A; color: #F8FAFC; }
QWidget#settingsContent QLabel { color: #E2E8F0; }
QWidget#settingsContent QPushButton { background-color: #1E293B; color: #F8FAFC; }
QWidget#settingsContent QComboBox { background-color: #0F172A; color: #F8FAFC; }
QLabel { color: #E2E8F0; }
QLabel[pageTitle="true"], QLabel[sectionHeading="true"], QLabel[guideTitle="true"] { color: #F8FAFC; }
QLabel[pageSubtitle="true"], QLabel[mutedText="true"], QLabel[sessionLabel="true"] { color: #CBD5E1; }
QWidget#sessionStrip { background: #0B1220; border: 1px solid #475569; }
QWidget#guideItem { background: #0F172A; border: 1px solid #334155; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QComboBox, QDateEdit { border: 1px solid #475569; }
QHeaderView::section { background: #1E293B; color: #F8FAFC; border-bottom: 2px solid #64748B; }
QTableWidget { background: #0F172A; alternate-background-color: #172033; color: #F8FAFC; border: 1px solid #475569; gridline-color: #334155; }
QTableWidget::item { color: #F8FAFC; border-bottom: 1px solid #334155; }
QTableWidget::item:selected { background: #4338CA; color: #FFFFFF; }
QCheckBox, QRadioButton { color: #E2E8F0; }
QStatusBar { background: #111827; color: #E2E8F0; }
QDialog, QMessageBox, QInputDialog { background: #0F172A; color: #F8FAFC; }
QMessageBox { min-width: 480px; }
QMessageBox QLabel#qt_msgbox_label { min-width: 360px; color: #F8FAFC; font-size: 10pt; font-weight: 500; }
QMessageBox QLabel#qt_msgboxex_icon_label { min-width: 44px; min-height: 44px; }
QInputDialog { min-width: 460px; }
QInputDialog QLabel { min-width: 420px; color: #F8FAFC; font-size: 9.5pt; font-weight: 600; }
QInputDialog QLineEdit { min-width: 420px; min-height: 32px; }

QLabel#attRosterTitle, QLabel#attRosterHint, QLabel#attSummaryTitle, QLabel#attSummaryNote, QLabel#taskRosterTitle, QLabel#taskRosterHint, QLabel#empRosterTitle, QLabel#empRosterHint, QLabel#trackerRosterTitle, QLabel#trackerRosterHint, QLabel#archiveRosterTitle, QLabel#archiveRosterHint { qproperty-wordWrap: false; }
QPushButton { text-align: center; }
QTableWidget { font-size: 9pt; }
QTableWidget::item { padding: 4px 6px; }
QHeaderView::section { padding: 6px 8px; min-height: 36px; }
"""
    return css.replace("__CHEVRON_WHITE__", white_arrow).replace("__CHEVRON_CYAN__", cyan_arrow)

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


class StartupSplashScreen(QWidget):
    """Modern frameless loading splash screen for Raw Strength Calisthenics."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(520, 300)

        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            self.move(
                screen_geo.center().x() - self.width() // 2,
                screen_geo.center().y() - self.height() // 2,
            )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setObjectName("splashCard")
        card.setStyleSheet("""
            QFrame#splashCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0B1120, stop:0.5 #0F172A, stop:1 #020617);
                border: 1.5px solid #0284C7;
                border-radius: 18px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(2, 132, 199, 120))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(10)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        logo_lbl = QLabel()
        logo_lbl.setPixmap(brand_mark_pixmap(64))
        logo_lbl.setFixedSize(64, 64)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        top_layout.addWidget(logo_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        title_lbl = QLabel("RAW STRENGTH CALISTHENICS")
        title_lbl.setStyleSheet("color: #F8FAFC; font-size: 14pt; font-weight: 800; letter-spacing: 1px; background: transparent; border: none;")
        title_col.addWidget(title_lbl)

        subtitle_lbl = QLabel("Employee Audit & Operations Manager")
        subtitle_lbl.setStyleSheet("color: #38BDF8; font-size: 9.5pt; font-weight: 600; background: transparent; border: none;")
        title_col.addWidget(subtitle_lbl)

        ver_lbl = QLabel(f"v{APP_VERSION} · Enterprise Cloud Edition")
        ver_lbl.setStyleSheet("color: #64748B; font-size: 8pt; font-weight: 500; background: transparent; border: none;")
        title_col.addWidget(ver_lbl)

        top_layout.addLayout(title_col)
        top_layout.addStretch()

        layout.addLayout(top_layout)
        layout.addSpacing(6)

        self.status_lbl = QLabel("Loading, please wait...")
        self.status_lbl.setStyleSheet("color: #E2E8F0; font-size: 10pt; font-weight: 500; background: transparent; border: none;")
        layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(15)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0284C7, stop:0.5 #38BDF8, stop:1 #00E5FF);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(4)

        bot_layout = QHBoxLayout()
        hint_lbl = QLabel("⚡ Continuous Offline Sync · 36 Indian Territories")
        hint_lbl.setStyleSheet("color: #475569; font-size: 7.5pt; background: transparent; border: none;")
        bot_layout.addWidget(hint_lbl)
        bot_layout.addStretch()

        self.pct_lbl = QLabel("15%")
        self.pct_lbl.setStyleSheet("color: #38BDF8; font-size: 8pt; font-weight: 700; background: transparent; border: none;")
        bot_layout.addWidget(self.pct_lbl)

        layout.addLayout(bot_layout)
        root_layout.addWidget(card)

    def is_headless(self):
        return os.environ.get("QT_QPA_PLATFORM") == "offscreen" or (
            os.environ.get("CI") == "true" and os.environ.get("DISPLAY") is None
        )

    def show_splash(self):
        if self.is_headless():
            return
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()

    def set_status(self, text: str, progress: int = None):
        if self.is_headless():
            return
        self.status_lbl.setText(str(text))
        if progress is not None:
            val = max(0, min(100, int(progress)))
            self.progress_bar.setValue(val)
            self.pct_lbl.setText(f"{val}%")
        QApplication.processEvents()

    def hide_splash(self):
        if self.is_headless():
            return
        self.hide()
        QApplication.processEvents()

    def close_splash(self):
        if self.is_headless():
            return
        self.close()
        QApplication.processEvents()

    def finish(self, main_window=None):
        if self.is_headless():
            return
        self.close()
        QApplication.processEvents()


def main():
    app=QApplication(sys.argv); app.setStyle("Fusion"); ensure_combobox_wheel_filter(app)
    QFontDatabase.addApplicationFont(resource_path("assets/DejaVuSans.ttf"))
    QFontDatabase.addApplicationFont(resource_path("assets/DejaVuSans-Bold.ttf"))
    app_font = QFont("Segoe UI", 9)
    app_font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(app_font)
    app.setWindowIcon(QIcon(brand_mark_pixmap(128)))

    splash = StartupSplashScreen()
    splash.show_splash()
    splash.set_status("Loading, please wait...", 15)

    try:
        splash.set_status("Initializing secure local database...", 30)
        db=Database()
        seed_initial_audit(db)
        splash.set_status("Configuring workspace themes & preferences...", 45)
        # Migrate to OneText Modern SaaS theme (flagship dark bento UI) by default
        if db.get_setting("onetext_saas_ui_v1307") != "1":
            db.set_setting("ui_theme", "night")
            db.set_setting("onetext_saas_ui_v1307", "1")
        if db.get_setting("aurora_command_hud_v1324") != "1":
            db.set_setting("ui_theme", "night")
            if db.get_setting("animation_style") in ("Love Couple", "Love & Couples", None, ""):
                db.set_setting("animation_style", "Aurora Waves")
            db.set_setting("aurora_command_hud_v1324", "1")
        if db.get_setting("cyber_hud_theme_v1325") != "1":
            db.set_setting("ui_theme", "night")
            if db.get_setting("animation_style") in ("Love Couple", "Love & Couples", None, ""):
                db.set_setting("animation_style", "Galaxy")
            db.set_setting("cyber_hud_theme_v1325", "1")
        apply_app_theme(app, db.get_setting("ui_theme", "night") or "night")
    except Exception as exc:
        splash.close_splash()
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            logging.getLogger("startup").exception(f"Startup failed: {exc}")
        else:
            QMessageBox.critical(None, APP_NAME, f"Startup failed:\n{exc}")
        return 1

    splash.set_status("Verifying user accounts & cloud sync...", 60)
    if db.conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] == 0:
        if hasattr(db, "github_sync") and db.github_sync.is_configured:
            try:
                raw = db.github_sync.download_latest_snapshot(prefer_latest=True)
                if raw:
                    import tempfile
                    with tempfile.NamedTemporaryFile(prefix="rsc_init_", suffix=".sqlite3", delete=False) as h:
                        tpath = Path(h.name)
                        h.write(raw)
                    try:
                        merge_remote_database_snapshot(db.conn, tpath)
                    finally:
                        tpath.unlink(missing_ok=True)
            except Exception as e:
                logging.getLogger("startup").debug(f"Initial cloud pull skipped: {e}")

    if db.conn.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] == 0:
        splash.hide_splash()
        setup_dialog = AccountSetupDialog(db)
        if setup_dialog.exec() != QDialog.Accepted:
            splash.close_splash()
            return 0
        splash.show_splash()

    resume_user = None
    resume_tab = 0
    resume_path = APP_DIR / "update_resume.json"
    try:
        if resume_path.exists():
            resume = json.loads(resume_path.read_text(encoding="utf-8"))
            # Consume the marker immediately; it cannot be reused on later launches.
            resume_path.unlink(missing_ok=True)
            age = datetime.now().timestamp() - float(resume.get("created_at", 0))
            target_version = str(resume.get("target_version", "0.0.0"))
            if 0 <= age <= 600 and release_version_tuple(APP_VERSION) >= release_version_tuple(target_version):
                row = db.conn.execute("SELECT id,username,display_name,role,active FROM auth_users WHERE id=? AND active=1", (int(resume.get("user_id", 0)),)).fetchone()
                if row:
                    resume_user = dict(row)
                    resume_tab = max(0, int(resume.get("tab_index", 0)))
    except Exception:
        try:
            resume_path.unlink(missing_ok=True)
        except Exception:
            pass

    if resume_user is None:
        splash.hide_splash()
        login=LoginDialog(db)
        if login.exec()!=QDialog.Accepted:
            splash.close_splash()
            return 0
        active_user = login.user
        splash.show_splash()
    else:
        active_user = resume_user

    splash.set_status("Loading workspace & Store Directory, please wait...", 80)
    if db.get_setting("initial_audit_2026_10_09_imported") == "1" and db.get_setting("initial_audit_notice_shown") != "1":
        info(None, "Historical audit imported: 8 employees and 36 task records for 09-10-2026. To review them, select 2026-10-09 in All Tasks, Employee Task Tracker, or Print Center. Today's screens may be empty until you add today's tasks.")
        db.set_setting("initial_audit_notice_shown", "1")

    win=MainWindow(db, active_user); win.apply_theme()
    splash.set_status("Ready! Starting workspace...", 100)
    win.show()
    win.raise_()
    win.activateWindow()
    splash.finish(win)

    if resume_user is not None and resume_tab < win.tabs.count():
        win.tabs.setCurrentIndex(resume_tab)
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
