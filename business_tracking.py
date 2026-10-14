"""Business Tracking module — additive tables and UI for products, orders, services, and activities.

This module never modifies existing employee, task, or audit tables.
"""
import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QFormLayout,
    QDialog, QDialogButtonBox, QGroupBox, QHeaderView, QAbstractItemView,
    QMessageBox,
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


class BusinessTrackingTab(QWidget):
    """Top-level Business Tracking tab with sub-tabs."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        setup_business_tables(db.conn)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("Business Tracking")
        title.setProperty("pageTitle", True)
        layout.addWidget(title)
        subtitle = QLabel("Record products, orders, services, and employee activities. Does not place orders or process payments.")
        subtitle.setProperty("pageSubtitle", True)
        layout.addWidget(subtitle)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(self._build_dashboard(), "Dashboard")
        self.sub_tabs.addTab(self._build_products(), "Products & Inventory")
        self.sub_tabs.addTab(self._build_orders(), "Orders")
        self.sub_tabs.addTab(self._build_services(), "Services & Members")
        self.sub_tabs.addTab(self._build_activities(), "Employee Activities")
        layout.addWidget(self.sub_tabs)
        self.refresh_all()

    def _build_dashboard(self):
        w = QWidget()
        l = QVBoxLayout(w)
        self.dash_summary = QLabel("Loading...")
        self.dash_summary.setWordWrap(True)
        l.addWidget(self.dash_summary)
        l.addStretch()
        return w

    def _build_products(self):
        w = QWidget()
        l = QVBoxLayout(w)
        row = QHBoxLayout()
        self.prod_search = QLineEdit()
        self.prod_search.setPlaceholderText("Search product name or SKU")
        self.prod_search.textChanged.connect(self.refresh_products)
        row.addWidget(self.prod_search)
        add_btn = QPushButton("Add Product")
        add_btn.clicked.connect(self.add_product)
        row.addWidget(add_btn)
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
        self.order_search.setPlaceholderText("Search order ID or customer")
        self.order_search.textChanged.connect(self.refresh_orders)
        row.addWidget(self.order_search)
        add_btn = QPushButton("Add Order")
        add_btn.clicked.connect(self.add_order)
        row.addWidget(add_btn)
        l.addLayout(row)
        self.order_table = QTableWidget(0, 6)
        self.order_table.setHorizontalHeaderLabels(["ID", "External ID", "Date", "Channel", "Customer", "Status"])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.order_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.order_table)
        return w

    def _build_services(self):
        w = QWidget()
        l = QVBoxLayout(w)
        row = QHBoxLayout()
        add_svc = QPushButton("Add Service")
        add_svc.clicked.connect(self.add_service)
        add_mem = QPushButton("Add Member")
        add_mem.clicked.connect(self.add_member)
        row.addWidget(add_svc)
        row.addWidget(add_mem)
        row.addStretch()
        l.addLayout(row)
        self.svc_table = QTableWidget(0, 4)
        self.svc_table.setHorizontalHeaderLabels(["ID", "Service", "Mode", "Price"])
        self.svc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.svc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.svc_table)
        self.mem_table = QTableWidget(0, 5)
        self.mem_table.setHorizontalHeaderLabels(["ID", "Member", "Service", "Status", "Sessions left"])
        self.mem_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mem_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.mem_table)
        return w

    def _build_activities(self):
        w = QWidget()
        l = QVBoxLayout(w)
        row = QHBoxLayout()
        add_btn = QPushButton("Add Activity")
        add_btn.clicked.connect(self.add_activity)
        row.addWidget(add_btn)
        row.addStretch()
        l.addLayout(row)
        self.act_table = QTableWidget(0, 6)
        self.act_table.setHorizontalHeaderLabels(["ID", "Employee", "Type", "Status", "Start", "Remarks"])
        self.act_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.act_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        l.addWidget(self.act_table)
        return w

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_products()
        self.refresh_orders()
        self.refresh_services()
        self.refresh_activities()

    def refresh_dashboard(self):
        c = self.db.conn
        products = c.execute("SELECT COUNT(*) FROM bt_products").fetchone()[0]
        orders = c.execute("SELECT COUNT(*) FROM bt_orders").fetchone()[0]
        members = c.execute("SELECT COUNT(*) FROM bt_members").fetchone()[0]
        activities = c.execute("SELECT COUNT(*) FROM bt_activities").fetchone()[0]
        self.dash_summary.setText(
            f"Products: {products}  •  Orders: {orders}  •  Members: {members}  •  Activities: {activities}"
        )

    def refresh_products(self):
        text = self.prod_search.text().lower() if hasattr(self, "prod_search") else ""
        rows = self.db.conn.execute("SELECT * FROM bt_products ORDER BY name").fetchall()
        self.prod_table.setRowCount(0)
        for p in rows:
            if text and text not in f"{p['name']} {p['sku'] or ''}".lower():
                continue
            r = self.prod_table.rowCount()
            self.prod_table.insertRow(r)
            avail = available_stock(p)
            vals = [p["id"], p["sku"] or "", p["name"], p["category"], f"{avail:.1f}", p["reorder_level"]]
            for c, v in enumerate(vals):
                self.prod_table.setItem(r, c, QTableWidgetItem(str(v)))

    def refresh_orders(self):
        text = self.order_search.text().lower() if hasattr(self, "order_search") else ""
        rows = self.db.conn.execute("SELECT * FROM bt_orders ORDER BY id DESC").fetchall()
        self.order_table.setRowCount(0)
        for o in rows:
            if text and text not in f"{o['external_order_id']} {o['customer_name']}".lower():
                continue
            r = self.order_table.rowCount()
            self.order_table.insertRow(r)
            vals = [o["id"], o["external_order_id"], o["order_date"], o["sales_channel"], o["customer_name"], o["order_status"]]
            for c, v in enumerate(vals):
                self.order_table.setItem(r, c, QTableWidgetItem(str(v or "")))

    def refresh_services(self):
        svcs = self.db.conn.execute("SELECT * FROM bt_services ORDER BY name").fetchall()
        self.svc_table.setRowCount(0)
        for s in svcs:
            r = self.svc_table.rowCount()
            self.svc_table.insertRow(r)
            vals = [s["id"], s["name"], s["training_mode"], s["standard_price"]]
            for c, v in enumerate(vals):
                self.svc_table.setItem(r, c, QTableWidgetItem(str(v or "")))
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
                self.mem_table.setItem(r, c, QTableWidgetItem(str(v)))

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
                self.act_table.setItem(r, c, QTableWidgetItem(str(v or "")))

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
        if d.exec() != QDialog.Accepted or not name.text().strip():
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
        if d.exec() != QDialog.Accepted or not name.text().strip():
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
        if d.exec() != QDialog.Accepted or not name.text().strip():
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
        if d.exec() != QDialog.Accepted or emp.count() == 0:
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
