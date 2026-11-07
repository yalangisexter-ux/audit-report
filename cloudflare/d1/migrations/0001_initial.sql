-- Cloudflare D1 baseline schema for Raw Strength Employee Audit Manager.
-- Derived from app.Database.setup(), business_tracking.setup_business_tables(),
-- and the standalone web authentication/chat tables.
-- This migration creates schema only. It imports no customer data and creates no accounts.
-- Apply only to the dedicated raw-strength-audit-manager D1 database.

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Preserve case-sensitive account identities: "Admin" and "admin" are distinct.
CREATE TABLE IF NOT EXISTS auth_users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL COLLATE BINARY UNIQUE,
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

CREATE TABLE IF NOT EXISTS employees (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_code TEXT UNIQUE,
  name TEXT NOT NULL DEFAULT '',
  department TEXT DEFAULT '',
  designation TEXT DEFAULT '',
  phone TEXT DEFAULT '',
  email TEXT DEFAULT '',
  joining_date TEXT DEFAULT '',
  active INTEGER DEFAULT 1,
  notes TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id INTEGER,
  task_date TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  department TEXT DEFAULT '',
  details TEXT DEFAULT '',
  due_time TEXT DEFAULT '',
  priority TEXT DEFAULT 'Normal',
  status TEXT DEFAULT 'Not started',
  progress INTEGER DEFAULT 0,
  proof_url TEXT DEFAULT '',
  proof_note TEXT DEFAULT '',
  submitted_at TEXT DEFAULT '',
  manager_note TEXT DEFAULT '',
  expose_link INTEGER NOT NULL DEFAULT 0,
  target_qty TEXT DEFAULT '',
  actual_qty TEXT DEFAULT '',
  next_action TEXT DEFAULT '',
  custom_values TEXT DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  FOREIGN KEY(employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS attendance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id INTEGER NOT NULL,
  work_date TEXT NOT NULL DEFAULT '',
  check_in TEXT DEFAULT '',
  check_out TEXT DEFAULT '',
  break_minutes INTEGER DEFAULT 0,
  attendance_status TEXT DEFAULT 'Unmarked',
  attendance_note TEXT DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  UNIQUE(employee_id, work_date),
  FOREIGN KEY(employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS holidays (
  holiday_date TEXT PRIMARY KEY,
  holiday_name TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  display_order INTEGER DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS archived_documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id INTEGER NULL,
  report_date TEXT DEFAULT '',
  file_name TEXT NOT NULL,
  mime_type TEXT DEFAULT 'application/pdf',
  content BLOB NOT NULL,
  notes TEXT DEFAULT '',
  uploaded_at TEXT NOT NULL,
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  action TEXT NOT NULL,
  details TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS source_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date TEXT NOT NULL,
  source_filename TEXT NOT NULL,
  raw_text TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  UNIQUE(report_date, source_filename)
);

CREATE TABLE IF NOT EXISTS employee_targets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id INTEGER NOT NULL,
  target_date TEXT NOT NULL,
  target TEXT DEFAULT '',
  target_status TEXT DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  UNIQUE(employee_id, target_date),
  FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_prospects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dedupe_key TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL DEFAULT 'Store',
  business_name TEXT NOT NULL,
  business_category TEXT DEFAULT '',
  state TEXT DEFAULT '',
  city TEXT DEFAULT '',
  area TEXT DEFAULT '',
  contact_person TEXT DEFAULT '',
  phone TEXT DEFAULT '',
  email TEXT DEFAULT '',
  address TEXT DEFAULT '',
  website TEXT DEFAULT '',
  maps TEXT DEFAULT '',
  followup_date TEXT DEFAULT '',
  call_time TEXT DEFAULT '',
  connection TEXT DEFAULT '',
  verified TEXT DEFAULT '',
  response TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  source_name TEXT NOT NULL DEFAULT '',
  source_url TEXT DEFAULT '',
  source_type TEXT NOT NULL DEFAULT 'Workbook',
  source_checked_at TEXT DEFAULT '',
  source_sheet TEXT DEFAULT '',
  source_row INTEGER,
  source_status TEXT NOT NULL DEFAULT 'Needs direct confirmation',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  store_id TEXT DEFAULT '',
  store_type TEXT DEFAULT 'Physical Retailer',
  product_categories TEXT DEFAULT '',
  product_evidence TEXT DEFAULT '',
  postal_code TEXT DEFAULT '',
  country TEXT DEFAULT 'India',
  product_catalog TEXT DEFAULT '',
  verification_status TEXT DEFAULT 'Unverified',
  last_verified TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_customer_prospects_region
  ON customer_prospects(state, city, kind);
CREATE INDEX IF NOT EXISTS idx_customer_prospects_name
  ON customer_prospects(business_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_tasks_employee_date
  ON tasks(employee_id, task_date);
CREATE INDEX IF NOT EXISTS idx_tasks_date_employee
  ON tasks(task_date, employee_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date_employee
  ON attendance(work_date, employee_id);

-- Inventory, orders, services, memberships and operational activities.
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

CREATE TABLE IF NOT EXISTS web_auth_sessions (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES auth_users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_web_auth_sessions_expiry
  ON web_auth_sessions(expires_at);

CREATE TABLE IF NOT EXISTS local_chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel TEXT DEFAULT 'general',
  sender TEXT NOT NULL,
  role TEXT DEFAULT 'Staff',
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Sunday remains a working day by default, matching the desktop application's
-- current working_weekdays() fallback. Admin-configured values can override it.
INSERT OR IGNORE INTO settings(key, value)
VALUES ('working_weekdays', '0,1,2,3,4,6');
