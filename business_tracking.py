"""Business Tracking module — additive tables and UI for products, orders, services, and activities.

This module never modifies existing employee, task, or audit tables.
"""
import sqlite3
from datetime import datetime
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QFormLayout,
    QDialog, QDialogButtonBox, QGroupBox, QHeaderView, QAbstractItemView,
    QMessageBox, QInputDialog, QSpinBox,
)
from PySide6.QtCore import Qt


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def parse_quantity(text):
    """Return a finite non-negative float, or None if invalid."""
    try:
        value = float(text or 0)
    except ValueError:
        return None
    if value != value or value == float("inf") or value == float("-inf") or value < 0:
        return None
    return value


def setup_business_tables(conn):
    """Create business tracking tables if they do not exist. Additive only."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS bt_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        name TEXT NOT NULL,
        category TEXT DEFAULT '',
        brand TEXT DEFAULT '',
        package_type TEXT DEFAULT '',
        base_unit TEXT DEFAULT 'PCS',
        opening_stock REAL DEFAULT 0,
        received_qty REAL DEFAULT 0,
        reserved_qty REAL DEFAULT 0,
        dispatched_qty REAL DEFAULT 0,
        free_qty REAL DEFAULT 0,
        returned_qty REAL DEFAULT 0,
        damaged_qty REAL DEFAULT 0,
        expired_qty REAL DEFAULT 0,
        quarantined_qty REAL DEFAULT 0,
        purchase_cost REAL DEFAULT 0,
        selling_price REAL DEFAULT 0,
        reorder_level REAL DEFAULT 0,
        batch_number TEXT DEFAULT '',
        expiry_date TEXT DEFAULT '',
        storage_location TEXT DEFAULT '',
        updated_by TEXT DEFAULT '',
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bt_stock_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        txn_type TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT '',
        reference TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(product_id) REFERENCES bt_products(id)
    );
    CREATE TABLE IF NOT EXISTS bt_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_order_id TEXT DEFAULT '',
        order_date TEXT NOT NULL,
        sales_channel TEXT DEFAULT '',
        customer_name TEXT DEFAULT '',
        contact TEXT DEFAULT '',
        payment_mode TEXT DEFAULT '',
        order_status TEXT DEFAULT 'Pending',
        discount REAL DEFAULT 0,
        order_value REAL DEFAULT 0,
        invoice_number TEXT DEFAULT '',
        shipment_id TEXT DEFAULT '',
        assigned_employee_id INTEGER,
        updated_by TEXT DEFAULT '',
        updated_at TEXT NOT NULL,
        remarks TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS bt_order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        paid_qty REAL DEFAULT 0,
        free_qty REAL DEFAULT 0,
        unit TEXT DEFAULT '',
        unit_price REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        item_status TEXT DEFAULT 'Pending',
        FOREIGN KEY(order_id) REFERENCES bt_orders(id)
    );
    CREATE TABLE IF NOT EXISTS bt_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT DEFAULT '',
        description TEXT DEFAULT '',
        training_mode TEXT DEFAULT 'Offline',
        service_unit TEXT DEFAULT 'Session',
        session_duration INTEGER DEFAULT 0,
        num_sessions INTEGER DEFAULT 0,
        plan_validity INTEGER DEFAULT 0,
        standard_price REAL DEFAULT 0,
        active INTEGER DEFAULT 1,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bt_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT DEFAULT '',
        service_id INTEGER,
        training_mode TEXT DEFAULT '',
        registration_date TEXT DEFAULT '',
        start_date TEXT DEFAULT '',
        expiry_date TEXT DEFAULT '',
        sessions_purchased INTEGER DEFAULT 0,
        sessions_completed INTEGER DEFAULT 0,
        assigned_trainer_id INTEGER,
        status TEXT DEFAULT 'Active',
        payment_status TEXT DEFAULT 'Pending',
        invoice_ref TEXT DEFAULT '',
        remarks TEXT DEFAULT '',
        FOREIGN KEY(service_id) REFERENCES bt_services(id)
    );
    CREATE TABLE IF NOT EXISTS bt_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        related_order_id INTEGER,
        related_service_id INTEGER,
        task_type TEXT DEFAULT '',
        product_id INTEGER,
        quantity REAL DEFAULT 0,
        unit TEXT DEFAULT '',
        assigned_by TEXT DEFAULT '',
        start_time TEXT DEFAULT '',
        completion_time TEXT DEFAULT '',
        task_status TEXT DEFAULT 'Pending',
        verified_by TEXT DEFAULT '',
        proof_ref TEXT DEFAULT '',
        remarks TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );
    """)
    conn.commit()


def available_stock(product_row):
    """Calculate available stock from ledger-style fields."""
    return (
        float(product_row["opening_stock"] or 0)
        + float(product_row["received_qty"] or 0)
        - float(product_row["reserved_qty"] or 0)
        - float(product_row["dispatched_qty"] or 0)
        - float(product_row["free_qty"] or 0)
        - float(product_row["damaged_qty"] or 0)
        - float(product_row["expired_qty"] or 0)
        - float(product_row["quarantined_qty"] or 0)
        + float(product_row["returned_qty"] or 0)
    )


STATUS_PALETTE = {
    "completed": ("#DCFCE7", "#166534"),
    "delivered": ("#DCFCE7", "#166534"),
    "active": ("#DCFCE7", "#166534"),
    "packed": ("#E0E7FF", "#3730A3"),
    "confirmed": ("#CFFAFE", "#0E7490"),
    "dispatched": ("#DBEAFE", "#1E40AF"),
    "in progress": ("#DBEAFE", "#1E40AF"),
    "pending": ("#FEF3C7", "#92400E"),
    "partially completed": ("#FEF3C7", "#92400E"),
    "unmarked": ("#F1F5F9", "#475569"),
    "cancelled": ("#FEE2E2", "#991B1B"),
    "returned": ("#FEE2E2", "#991B1B"),
    "blocked": ("#FEE2E2", "#991B1B"),
    "expired": ("#FEE2E2", "#991B1B"),
    "inactive": ("#F1F5F9", "#475569"),
}


def _table_item(value, is_center=False, status_pill=False):
    """Keep elided table values available on hover with optional colored status pill styling."""
    text = "" if value is None else str(value)
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignCenter if is_center or status_pill else Qt.AlignmentFlag.AlignLeft))
    if text:
        item.setToolTip(text)
    if status_pill:
        key = text.strip().lower()
        bg, fg = STATUS_PALETTE.get(key, ("#F1F5F9", "#475569"))
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    return item


class BusinessTrackingTab(QWidget):
    """Top-level Business Tracking tab with sub-tabs."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        setup_business_tables(db.conn)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.kpi_cards = []
        self.heading = None
        self.lbl_svc = None
        self.lbl_mem = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 8)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(self._build_dashboard(), "📊 Dashboard")
        self.sub_tabs.addTab(self._build_products(), "📦 Products & Inventory")
        self.sub_tabs.addTab(self._build_orders(), "🛒 Orders")
        self.sub_tabs.addTab(self._build_services(), "🏋️ Services & Members")
        self.sub_tabs.addTab(self._build_activities(), "⚡ Employee Activities")
        layout.addWidget(self.sub_tabs)
        self.apply_theme()
        self.refresh_all()

    def apply_theme(self, theme_name=None):
        if not theme_name and hasattr(self, "db") and hasattr(self.db, "get_setting"):
            try:
                theme_name = self.db.get_setting("ui_theme", "day")
            except Exception:
                theme_name = "day"
        theme = (theme_name or "day").lower()
        if theme in ("night", "dark"):
            pane_bg = "rgba(15, 23, 42, 0.92)"
            border = "rgba(99, 102, 241, 0.35)"
            tab_bg = "rgba(30, 41, 59, 0.85)"
            tab_fg = "#CBD5E1"
            tab_sel_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #00E5FF)"
            heading_color = "#F8FAFC"
            kpi_card_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(17, 25, 50, 0.92), stop:1 rgba(9, 14, 30, 0.95))"
            kpi_border = "rgba(99, 102, 241, 0.35)"
            kpi_hover_border = "#00E5FF"
            kpi_hover_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(23, 35, 70, 0.95), stop:1 rgba(15, 23, 42, 0.98))"
            kpi_title_color = "#94A3B8"
            kpi_value_color = "#00E5FF"
            kpi_desc_color = "#94A3B8"
            summary_color = "#E2E8F0"
            subhead_color = "#818CF8"
            search_bg = "#0B1120"
            search_fg = "#F8FAFC"
            search_border = "#334155"
        elif theme == "ocean":
            pane_bg = "rgba(240, 249, 255, 0.94)"
            border = "#BAE6FD"
            tab_bg = "rgba(224, 242, 254, 0.90)"
            tab_fg = "#0C4A6E"
            tab_sel_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #00E5FF)"
            heading_color = "#0C4A6E"
            kpi_card_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F0F9FF, stop:1 #E0F2FE)"
            kpi_border = "#BAE6FD"
            kpi_hover_border = "#0284C7"
            kpi_hover_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E0F2FE, stop:1 #BAE6FD)"
            kpi_title_color = "#0369A1"
            kpi_value_color = "#0284C7"
            kpi_desc_color = "#0C4A6E"
            summary_color = "#0C4A6E"
            subhead_color = "#0284C7"
            search_bg = "#FFFFFF"
            search_fg = "#0C4A6E"
            search_border = "#BAE6FD"
        elif theme == "sunset":
            pane_bg = "rgba(255, 247, 237, 0.94)"
            border = "#FED7AA"
            tab_bg = "rgba(255, 237, 213, 0.90)"
            tab_fg = "#7C2D12"
            tab_sel_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EA580C, stop:1 #F43F5E)"
            heading_color = "#7C2D12"
            kpi_card_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFF7ED, stop:1 #FFEDD5)"
            kpi_border = "#FED7AA"
            kpi_hover_border = "#EA580C"
            kpi_hover_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFEDD5, stop:1 #FED7AA)"
            kpi_title_color = "#C2410C"
            kpi_value_color = "#EA580C"
            kpi_desc_color = "#7C2D12"
            summary_color = "#7C2D12"
            subhead_color = "#EA580C"
            search_bg = "#FFFFFF"
            search_fg = "#7C2D12"
            search_border = "#FED7AA"
        else:  # Day
            pane_bg = "rgba(255, 255, 255, 0.95)"
            border = "#CBD5E1"
            tab_bg = "rgba(241, 245, 249, 0.90)"
            tab_fg = "#334155"
            tab_sel_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6D28D9, stop:1 #DB2777)"
            heading_color = "#0F172A"
            kpi_card_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F8FAFC)"
            kpi_border = "#CBD5E1"
            kpi_hover_border = "#6D28D9"
            kpi_hover_bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F8FAFC, stop:1 #EDE9FE)"
            kpi_title_color = "#64748B"
            kpi_value_color = "#6D28D9"
            kpi_desc_color = "#64748B"
            summary_color = "#334155"
            subhead_color = "#6D28D9"
            search_bg = "#FFFFFF"
            search_fg = "#0F172A"
            search_border = "#CBD5E1"

        if hasattr(self, "sub_tabs"):
            self.sub_tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1.5px solid {border};
                    border-radius: 14px;
                    background: {pane_bg};
                    padding: 10px;
                }}
                QTabBar::tab {{
                    background: {tab_bg};
                    color: {tab_fg};
                    font-weight: 700;
                    font-size: 9.5pt;
                    padding: 5px 16px;
                    margin-right: 6px;
                    border-radius: 8px;
                    border: 1px solid {border};
                }}
                QTabBar::tab:selected {{
                    background: {tab_sel_bg};
                    color: #FFFFFF;
                    border: 1px solid {border};
                }}
                QTabBar::tab:hover:!selected {{
                    background: {tab_bg};
                    color: {heading_color};
                }}
            """)
        if hasattr(self, "heading") and self.heading:
            self.heading.setStyleSheet(f"font-size: 15pt; font-weight: 800; color: {heading_color};")
        if hasattr(self, "kpi_cards"):
            for card, title_label, value_label, desc_label in self.kpi_cards:
                card.setStyleSheet(f"""
                    QWidget#kpiCard {{
                        background: {kpi_card_bg};
                        border: 1.5px solid {kpi_border};
                        border-radius: 14px;
                        padding: 8px;
                    }}
                    QWidget#kpiCard:hover {{
                        border: 1.5px solid {kpi_hover_border};
                        background: {kpi_hover_bg};
                    }}
                """)
                title_label.setStyleSheet(f"font-size: 9.5pt; font-weight: 700; color: {kpi_title_color}; text-transform: uppercase; letter-spacing: 0.5px;")
                value_label.setStyleSheet(f"font-size: 26pt; font-weight: 800; color: {kpi_value_color};")
                desc_label.setStyleSheet(f"font-size: 8.5pt; color: {kpi_desc_color};")
        if hasattr(self, "dash_summary"):
            self.dash_summary.setStyleSheet(f"font-size: 10pt; font-weight: 600; color: {summary_color}; padding: 8px;")
        if hasattr(self, "lbl_svc") and self.lbl_svc:
            self.lbl_svc.setStyleSheet(f"font-weight: 700; font-size: 10.5pt; color: {subhead_color}; margin-top: 4px;")
        if hasattr(self, "lbl_mem") and self.lbl_mem:
            self.lbl_mem.setStyleSheet(f"font-weight: 700; font-size: 10.5pt; color: {subhead_color}; margin-top: 8px;")
        for search_edit in (getattr(self, "prod_search", None), getattr(self, "order_search", None)):
            if search_edit is not None:
                search_edit.setStyleSheet(f"QLineEdit {{ background: {search_bg}; color: {search_fg}; border: 1.5px solid {search_border}; border-radius: 8px; padding: 6px 10px; }}")

    def _build_dashboard(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(18, 18, 18, 18)
        l.setSpacing(14)

        self.heading = QLabel("Business overview")
        self.heading.setProperty("sectionHeading", True)
        self.heading.setStyleSheet("font-size: 15pt; font-weight: 800; color: #FFFFFF;")
        l.addWidget(self.heading)

        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        self.dashboard_metrics = {}
        self.kpi_cards = []
        metric_specs = (
            ("products", "Products", "Catalog items"),
            ("low_stock", "Low stock", "At or below reorder level"),
            ("orders", "Orders", "Order records"),
            ("members", "Active members", "Current memberships"),
        )
        for index, (key, title, description) in enumerate(metric_specs):
            card = QWidget()
            card.setObjectName("kpiCard")
            card.setMinimumHeight(122)
            card.setToolTip(f"{title}: {description}.")
            card.setStyleSheet("""
                QWidget#kpiCard {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(17,25,50,0.92), stop:1 rgba(9,14,30,0.95));
                    border: 1.5px solid rgba(99, 102, 241, 0.35);
                    border-radius: 14px;
                    padding: 8px;
                }
                QWidget#kpiCard:hover {
                    border: 1.5px solid #00E5FF;
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(23,35,70,0.95), stop:1 rgba(15,23,42,0.98));
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(4)

            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px;")
            value_label = QLabel("—")
            value_label.setObjectName("metricValue")
            value_label.setStyleSheet("font-size: 26pt; font-weight: 800; color: #00E5FF;")
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            value_label.setToolTip(f"{title}: {description}.")
            description_label = QLabel(description)
            description_label.setStyleSheet("font-size: 8.5pt; color: #94A3B8;")
            description_label.setWordWrap(True)

            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            card_layout.addWidget(description_label)
            self.dashboard_metrics[key] = value_label
            self.kpi_cards.append((card, title_label, value_label, description_label))
            cards.addWidget(card, index // 4, index % 4)

        l.addLayout(cards)
        self.dash_summary = QLabel("Loading business activity...")
        self.dash_summary.setWordWrap(True)
        self.dash_summary.setProperty("statusSummary", True)
        self.dash_summary.setStyleSheet("font-size: 10pt; font-weight: 600; color: #E2E8F0; padding: 8px;")
        l.addWidget(self.dash_summary)
        l.addStretch()
        return w

    def _build_products(self):
        w = QWidget()
        l = QVBoxLayout(w)
        row = QHBoxLayout()
        self.prod_search = QLineEdit()
        self.prod_search.setPlaceholderText("🔍 Search product name or SKU")
        self.prod_search.setClearButtonEnabled(True)
        self.prod_search.setMinimumHeight(34)
        self.prod_search.textChanged.connect(self.refresh_products)
        row.addWidget(self.prod_search)
        add_btn = QPushButton("➕ Add Product")
        add_btn.setToolTip("Add a product and its opening or received stock quantities.")
        add_btn.setMinimumHeight(34)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED); color: #FFFFFF; font-weight: 700; border-radius: 8px; padding: 4px 14px; } QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9); }")
        add_btn.clicked.connect(self.add_product)
        row.addWidget(add_btn)
        ref_btn = QPushButton("🔄 Refresh")
        ref_btn.setMinimumHeight(34)
        ref_btn.clicked.connect(self.refresh_products)
        row.addWidget(ref_btn)
        l.addLayout(row)
        self.prod_table = QTableWidget(0, 6)
        self.prod_table.setHorizontalHeaderLabels(["ID", "SKU", "Name", "Category", "Available", "Reorder"])
        self.prod_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.prod_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.prod_table)
        return w

    def _build_orders(self):
        w = QWidget()
        l = QVBoxLayout(w)
        row = QHBoxLayout()
        self.order_search = QLineEdit()
        self.order_search.setPlaceholderText("🔍 Search order ID or customer")
        self.order_search.setClearButtonEnabled(True)
        self.order_search.setMinimumHeight(34)
        self.order_search.textChanged.connect(self.refresh_orders)
        row.addWidget(self.order_search)
        add_btn = QPushButton("➕ Add Order")
        add_btn.setToolTip("Record an order and its current tracking status.")
        add_btn.setMinimumHeight(34)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED); color: #FFFFFF; font-weight: 700; border-radius: 8px; padding: 4px 14px; } QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9); }")
        add_btn.clicked.connect(self.add_order)
        row.addWidget(add_btn)
        ref_btn = QPushButton("🔄 Refresh")
        ref_btn.setMinimumHeight(34)
        ref_btn.clicked.connect(self.refresh_orders)
        row.addWidget(ref_btn)
        l.addLayout(row)
        self.order_table = QTableWidget(0, 6)
        self.order_table.setHorizontalHeaderLabels(["ID", "External ID", "Date", "Channel", "Customer", "Status"])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.order_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.order_table.setToolTip("Double-click an order row to update its tracking status.")
        self.order_table.cellDoubleClicked.connect(self.edit_order_status)
        l.addWidget(self.order_table)
        return w

    def _build_services(self):
        w = QWidget()
        l = QVBoxLayout(w)
        row = QHBoxLayout()
        add_svc = QPushButton("➕ Add Service")
        add_svc.setToolTip("Add a service offered to members.")
        add_svc.setMinimumHeight(34)
        add_svc.setCursor(Qt.CursorShape.PointingHandCursor)
        add_svc.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED); color: #FFFFFF; font-weight: 700; border-radius: 8px; padding: 4px 14px; } QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9); }")
        add_svc.clicked.connect(self.add_service)
        add_mem = QPushButton("➕ Add Member")
        add_mem.setToolTip("Add a member and record their service and purchased sessions.")
        add_mem.setMinimumHeight(34)
        add_mem.setCursor(Qt.CursorShape.PointingHandCursor)
        add_mem.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #6366F1); color: #020617; font-weight: 800; border-radius: 8px; padding: 4px 14px; } QPushButton:hover { background: #38BDF8; color: #FFFFFF; }")
        add_mem.clicked.connect(self.add_member)
        ref_btn = QPushButton("🔄 Refresh")
        ref_btn.setMinimumHeight(34)
        ref_btn.clicked.connect(self.refresh_services)
        row.addWidget(add_svc)
        row.addWidget(add_mem)
        row.addWidget(ref_btn)
        row.addStretch()
        l.addLayout(row)

        self.lbl_svc = QLabel("🏋️ Services & Training Programs")
        self.lbl_svc.setStyleSheet("font-weight: 700; font-size: 10.5pt; color: #818CF8; margin-top: 4px;")
        l.addWidget(self.lbl_svc)
        self.svc_table = QTableWidget(0, 4)
        self.svc_table.setHorizontalHeaderLabels(["ID", "Service", "Mode", "Price"])
        self.svc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.svc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.svc_table)

        self.lbl_mem = QLabel("👥 Active Memberships & Sessions")
        self.lbl_mem.setStyleSheet("font-weight: 700; font-size: 10.5pt; color: #818CF8; margin-top: 8px;")
        l.addWidget(self.lbl_mem)
        self.mem_table = QTableWidget(0, 5)
        self.mem_table.setHorizontalHeaderLabels(["ID", "Member", "Service", "Status", "Sessions left"])
        self.mem_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mem_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mem_table.setToolTip("Double-click a member to log completed sessions or update membership status.")
        self.mem_table.cellDoubleClicked.connect(self.edit_member_status)
        l.addWidget(self.mem_table)
        return w

    def _build_activities(self):
        w = QWidget()
        l = QVBoxLayout(w)
        row = QHBoxLayout()
        add_btn = QPushButton("➕ Add Activity")
        add_btn.setToolTip("Record an employee activity and its current status.")
        add_btn.setMinimumHeight(34)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED); color: #FFFFFF; font-weight: 700; border-radius: 8px; padding: 4px 14px; } QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9); }")
        add_btn.clicked.connect(self.add_activity)
        ref_btn = QPushButton("🔄 Refresh")
        ref_btn.setMinimumHeight(34)
        ref_btn.clicked.connect(self.refresh_activities)
        row.addWidget(add_btn)
        row.addWidget(ref_btn)
        row.addStretch()
        l.addLayout(row)
        self.act_table = QTableWidget(0, 6)
        self.act_table.setHorizontalHeaderLabels(["ID", "Employee", "Type", "Status", "Start", "Remarks"])
        self.act_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.act_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.act_table.setToolTip("Double-click an activity row to change its status.")
        self.act_table.cellDoubleClicked.connect(self.edit_activity_status)
        l.addWidget(self.act_table)
        return w

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_products()
        self.refresh_orders()
        self.refresh_services()
        self.refresh_activities()
        parent_win = self.window()
        if parent_win is not None and hasattr(parent_win, "refresh_home_business_snapshot"):
            try:
                parent_win.refresh_home_business_snapshot()
            except Exception:
                pass

    def refresh_dashboard(self):
        c = self.db.conn
        products = c.execute("SELECT * FROM bt_products ORDER BY name").fetchall()
        low_stock = sum(
            available_stock(product) <= float(product["reorder_level"] or 0)
            for product in products
        )
        orders = c.execute("SELECT COUNT(*) FROM bt_orders").fetchone()[0]
        members = c.execute("SELECT COUNT(*) FROM bt_members WHERE status='Active'").fetchone()[0]
        activities = c.execute("SELECT COUNT(*) FROM bt_activities").fetchone()[0]

        for key, value in {
            "products": len(products),
            "low_stock": low_stock,
            "orders": orders,
            "members": members,
        }.items():
            self.dashboard_metrics[key].setText(str(value))
        self.dash_summary.setText(f"{activities} employee activity records are available.")

    def refresh_products(self):
        text = self.prod_search.text().lower() if hasattr(self, "prod_search") else ""
        rows = self.db.conn.execute("SELECT * FROM bt_products ORDER BY name").fetchall()
        self.prod_table.setRowCount(0)
        for p in rows:
            if text and text not in f"{p['name'] or ''} {p['sku'] or ''}".lower():
                continue
            r = self.prod_table.rowCount()
            self.prod_table.insertRow(r)
            avail = available_stock(p)
            vals = [p["id"], p["sku"] or "", p["name"], p["category"], f"{avail:.1f}", p["reorder_level"]]
            for c, v in enumerate(vals):
                self.prod_table.setItem(r, c, _table_item(v, is_center=(c in (0, 1, 4, 5))))

    def refresh_orders(self):
        text = self.order_search.text().lower() if hasattr(self, "order_search") else ""
        rows = self.db.conn.execute("SELECT * FROM bt_orders ORDER BY id DESC").fetchall()
        self.order_table.setRowCount(0)
        for o in rows:
            if text and text not in f"{o['external_order_id'] or ''} {o['customer_name'] or ''}".lower():
                continue
            r = self.order_table.rowCount()
            self.order_table.insertRow(r)
            vals = [o["id"], o["external_order_id"], o["order_date"], o["sales_channel"], o["customer_name"], o["order_status"]]
            for c, v in enumerate(vals):
                self.order_table.setItem(r, c, _table_item(v, is_center=(c in (0, 1, 2, 5)), status_pill=(c == 5)))

    def refresh_services(self):
        svcs = self.db.conn.execute("SELECT * FROM bt_services ORDER BY name").fetchall()
        self.svc_table.setRowCount(0)
        for s in svcs:
            r = self.svc_table.rowCount()
            self.svc_table.insertRow(r)
            vals = [s["id"], s["name"], s["training_mode"], s["standard_price"]]
            for c, v in enumerate(vals):
                self.svc_table.setItem(r, c, _table_item(v, is_center=(c in (0, 3))))
        mems = self.db.conn.execute("""
            SELECT m.*, s.name AS service_name FROM bt_members m
            LEFT JOIN bt_services s ON s.id = m.service_id ORDER BY m.name
        """).fetchall()
        self.mem_table.setRowCount(0)
        for m in mems:
            r = self.mem_table.rowCount()
            self.mem_table.insertRow(r)
            left = int(m["sessions_purchased"] or 0) - int(m["sessions_completed"] or 0)
            vals = [m["id"], m["name"], m["service_name"] or "", m["status"], left]
            for c, v in enumerate(vals):
                self.mem_table.setItem(r, c, _table_item(v, is_center=(c in (0, 3, 4)), status_pill=(c == 3)))

    def refresh_activities(self):
        rows = self.db.conn.execute("""
            SELECT a.*, e.name AS employee_name FROM bt_activities a
            LEFT JOIN employees e ON e.id = a.employee_id
            ORDER BY a.id DESC
        """).fetchall()
        self.act_table.setRowCount(0)
        for a in rows:
            r = self.act_table.rowCount()
            self.act_table.insertRow(r)
            vals = [a["id"], a["employee_name"] or a["employee_id"], a["task_type"], a["task_status"], a["start_time"], a["remarks"]]
            for c, v in enumerate(vals):
                self.act_table.setItem(r, c, _table_item(v, is_center=(c in (0, 3, 4)), status_pill=(c == 3)))

    def edit_activity_status(self, row, column):
        item = self.act_table.item(row, 0)
        if item is None: return
        try: act_id = int(item.text())
        except (ValueError, TypeError): return
        current = self.db.conn.execute("SELECT task_status FROM bt_activities WHERE id=?", (act_id,)).fetchone()
        if not current: return
        statuses = ["Pending", "In Progress", "Completed", "Blocked", "Cancelled"]
        selected, ok = QInputDialog.getItem(self, "Update Activity Status", "Activity status:", statuses,
                                            max(0, statuses.index(current["task_status"]) if current["task_status"] in statuses else 0), False)
        if not ok or not selected: return
        self.db.conn.execute("UPDATE bt_activities SET task_status=? WHERE id=?", (selected, act_id))
        self.db.conn.commit()
        self.refresh_all()

    def edit_member_status(self, row, column):
        item = self.mem_table.item(row, 0)
        if item is None: return
        try: mem_id = int(item.text())
        except (ValueError, TypeError): return
        current = self.db.conn.execute("SELECT name, status, sessions_purchased, sessions_completed FROM bt_members WHERE id=?", (mem_id,)).fetchone()
        if not current: return
        action, ok = QInputDialog.getItem(self, f"Member: {current['name']}", "Choose action:",
                                          ["Record 1 completed session", "Change status to Active", "Change status to Expired", "Change status to Inactive"], 0, False)
        if not ok or not action: return
        if "completed session" in action:
            self.db.conn.execute("UPDATE bt_members SET sessions_completed=COALESCE(sessions_completed,0)+1 WHERE id=?", (mem_id,))
        elif "Active" in action:
            self.db.conn.execute("UPDATE bt_members SET status='Active' WHERE id=?", (mem_id,))
        elif "Expired" in action:
            self.db.conn.execute("UPDATE bt_members SET status='Expired' WHERE id=?", (mem_id,))
        elif "Inactive" in action:
            self.db.conn.execute("UPDATE bt_members SET status='Inactive' WHERE id=?", (mem_id,))
        self.db.conn.commit()
        self.refresh_all()

    def add_product(self):
        d = QDialog(self)
        d.setWindowTitle("Add Product")
        form = QFormLayout(d)
        name = QLineEdit()
        sku = QLineEdit()
        category = QComboBox()
        category.addItems(["supplements", "accessories", "apparel", "equipment"])
        opening = QLineEdit("0")
        received = QLineEdit("0")
        form.addRow("Name *", name)
        form.addRow("SKU", sku)
        form.addRow("Category", category)
        form.addRow("Opening stock", opening)
        form.addRow("Received qty", received)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        form.addRow(buttons)
        if d.exec() != QDialog.Accepted:
            return
        if not name.text().strip():
            QMessageBox.warning(self, "Missing Name", "Product name is required.")
            return
        open_qty = parse_quantity(opening.text())
        recv_qty = parse_quantity(received.text())
        if open_qty is None or recv_qty is None:
            QMessageBox.warning(self, "Invalid quantity", "Opening and received quantities must be non-negative numbers.")
            return
        try:
            self.db.conn.execute(
                "INSERT INTO bt_products(sku,name,category,opening_stock,received_qty,updated_at) VALUES(?,?,?,?,?,?)",
                (sku.text().strip() or None, name.text().strip(), category.currentText(), open_qty, recv_qty, now_text()),
            )
            self.db.conn.commit()
        except sqlite3.IntegrityError:
            self.db.conn.rollback()
            QMessageBox.warning(self, "Duplicate SKU", "A product with that SKU already exists.")
            return
        except sqlite3.Error as ex:
            self.db.conn.rollback()
            QMessageBox.warning(self, "Could not save product", str(ex))
            return
        self.refresh_all()

    def edit_order_status(self, row, column):
        item = self.order_table.item(row, 0)
        if item is None:
            return
        try:
            order_id = int(item.text())
        except (ValueError, TypeError):
            return
        current = self.db.conn.execute("SELECT order_status FROM bt_orders WHERE id=?", (order_id,)).fetchone()
        if not current:
            return
        statuses = ["Pending", "Confirmed", "Packed", "Dispatched", "Delivered", "Cancelled", "Returned"]
        selected, ok = QInputDialog.getItem(self, "Update order status", "Tracking status:", statuses,
                                            max(0, statuses.index(current["order_status"]) if current["order_status"] in statuses else 0), False)
        if not ok or not selected:
            return
        try:
            self.db.conn.execute("UPDATE bt_orders SET order_status=?, updated_at=? WHERE id=?",
                                 (selected, now_text(), order_id))
            self.db.conn.commit()
        except sqlite3.Error as ex:
            self.db.conn.rollback()
            QMessageBox.warning(self, "Could not update order", str(ex))
            return
        self.refresh_all()

    def add_order(self):
        d = QDialog(self)
        d.setWindowTitle("Add Order")
        form = QFormLayout(d)
        external = QLineEdit()
        customer = QLineEdit()
        channel = QComboBox()
        channel.addItems(["Amazon", "Flipkart", "website", "WhatsApp", "gym counter", "other"])
        status = QComboBox()
        status.addItems(["Pending", "Confirmed", "Packed", "Dispatched", "Delivered", "Cancelled", "Returned"])
        form.addRow("External Order ID", external)
        form.addRow("Customer", customer)
        form.addRow("Channel", channel)
        form.addRow("Status", status)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        form.addRow(buttons)
        if d.exec() != QDialog.Accepted:
            return
        try:
            self.db.conn.execute(
                "INSERT INTO bt_orders(external_order_id,order_date,sales_channel,customer_name,order_status,updated_at) VALUES(?,?,?,?,?,?)",
                (external.text().strip(), datetime.now().strftime("%Y-%m-%d"), channel.currentText(), customer.text().strip(), status.currentText(), now_text()),
            )
            self.db.conn.commit()
        except sqlite3.Error as ex:
            self.db.conn.rollback()
            QMessageBox.warning(self, "Could not save order", str(ex))
            return
        self.refresh_all()

    def add_service(self):
        d = QDialog(self)
        d.setWindowTitle("Add Service")
        form = QFormLayout(d)
        name = QLineEdit()
        mode = QComboBox()
        mode.addItems(["Offline", "Online", "Hybrid"])
        form.addRow("Name *", name)
        form.addRow("Mode", mode)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        form.addRow(buttons)
        if d.exec() != QDialog.Accepted:
            return
        if not name.text().strip():
            QMessageBox.warning(self, "Missing Name", "Service name is required.")
            return
        try:
            self.db.conn.execute(
                "INSERT INTO bt_services(name,training_mode,updated_at) VALUES(?,?,?)",
                (name.text().strip(), mode.currentText(), now_text()),
            )
            self.db.conn.commit()
        except sqlite3.Error as ex:
            self.db.conn.rollback()
            QMessageBox.warning(self, "Could not save service", str(ex))
            return
        self.refresh_all()

    def add_member(self):
        d = QDialog(self)
        d.setWindowTitle("Add Member")
        form = QFormLayout(d)
        name = QLineEdit()
        contact = QLineEdit()
        service = QComboBox()
        service.addItem("Select service", None)
        for svc in self.db.conn.execute("SELECT id, name, training_mode FROM bt_services WHERE active=1 ORDER BY name").fetchall():
            service.addItem(f"{svc['name']} ({svc['training_mode']})", svc["id"])
        mode = QComboBox()
        mode.addItems(["Offline", "Online", "Hybrid"])
        sessions = QSpinBox()
        sessions.setRange(0, 10000)
        sessions.setValue(0)
        form.addRow("Name *", name)
        form.addRow("Contact", contact)
        form.addRow("Service", service)
        form.addRow("Training mode", mode)
        form.addRow("Sessions purchased", sessions)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        form.addRow(buttons)
        if d.exec() != QDialog.Accepted:
            return
        if not name.text().strip():
            QMessageBox.warning(self, "Missing Name", "Member name is required.")
            return
        try:
            self.db.conn.execute(
                "INSERT INTO bt_members(name,contact,service_id,training_mode,sessions_purchased,registration_date,status) VALUES(?,?,?,?,?,?,?)",
                (name.text().strip(), contact.text().strip(), service.currentData(), mode.currentText(), sessions.value(), datetime.now().strftime("%Y-%m-%d"), "Active"),
            )
            self.db.conn.commit()
        except sqlite3.Error as ex:
            self.db.conn.rollback()
            QMessageBox.warning(self, "Could not save member", str(ex))
            return
        self.refresh_all()

    def add_activity(self):
        d = QDialog(self)
        d.setWindowTitle("Add Activity")
        form = QFormLayout(d)
        emp = QComboBox()
        for e in self.db.employees(False):
            emp.addItem(e["name"], e["id"])
        task_type = QComboBox()
        task_type.addItems(["Picking", "Packing", "QC", "Dispatch", "Training", "Attendance", "other"])
        qty = QLineEdit("0")
        status = QComboBox()
        status.addItems(["Pending", "In Progress", "Completed", "Blocked", "Cancelled"])
        remarks = QLineEdit()
        form.addRow("Employee *", emp)
        form.addRow("Task type", task_type)
        form.addRow("Quantity", qty)
        form.addRow("Status", status)
        form.addRow("Remarks", remarks)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(d.accept)
        buttons.rejected.connect(d.reject)
        form.addRow(buttons)
        if d.exec() != QDialog.Accepted:
            return
        if emp.count() == 0 or emp.currentData() is None:
            QMessageBox.warning(self, "Missing Employee", "Please select an employee.")
            return
        quantity = parse_quantity(qty.text())
        if quantity is None:
            QMessageBox.warning(self, "Invalid quantity", "Quantity must be a non-negative number.")
            return
        try:
            self.db.conn.execute(
                "INSERT INTO bt_activities(employee_id,task_type,quantity,remarks,start_time,task_status,created_at) VALUES(?,?,?,?,?,?,?)",
                (emp.currentData(), task_type.currentText(), quantity, remarks.text().strip(),
                 now_text() if status.currentText() == "In Progress" else "", status.currentText(), now_text()),
            )
            self.db.conn.commit()
        except sqlite3.Error as ex:
            self.db.conn.rollback()
            QMessageBox.warning(self, "Could not save activity", str(ex))
            return
        self.refresh_all()
