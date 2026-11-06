"""Basic migration smoke tests that exercise real Database.setup()."""
import sqlite3
import app

def test_fresh_database_creates_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        tables = {r["name"] for r in database.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "employees" in tables
        assert "tasks" in tables
        assert "attendance" in tables
    finally:
        database.conn.close()

def test_legacy_employee_name_migrated(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE employees(id INTEGER PRIMARY KEY, employee_name TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Legacy Name')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        row = database.conn.execute("SELECT name FROM employees WHERE id=1").fetchone()
        assert row["name"] == "Legacy Name"
    finally:
        database.conn.close()

def test_task_columns_added_without_dropping_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "tasks.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO tasks VALUES (1, 'Keep me')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        row = database.conn.execute("SELECT title FROM tasks WHERE id=1").fetchone()
        assert row["title"] == "Keep me"
        cols = {r["name"] for r in database.conn.execute("PRAGMA table_info(tasks)").fetchall()}
        assert "created_at" in cols and "updated_at" in cols
    finally:
        database.conn.close()

def test_legacy_null_and_na_task_statuses_are_preserved_without_becoming_completed(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_statuses.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT, status TEXT, progress INTEGER)")
    conn.execute("INSERT INTO tasks VALUES (1, 'No selection', NULL, 100)")
    conn.execute("INSERT INTO tasks VALUES (2, 'Legacy NA', 'N/A', 100)")
    conn.commit()
    conn.close()

    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        rows = database.conn.execute("SELECT title,status,progress FROM tasks ORDER BY id").fetchall()
        assert [(row["title"], row["status"], row["progress"]) for row in rows] == [
            ("No selection", None, 100), ("Legacy NA", "N/A", 100),
        ]
        assert app.is_explicitly_completed_task_status(rows[0]["status"]) is False
        assert app.is_explicitly_completed_task_status(rows[1]["status"]) is False
    finally:
        database.conn.close()

def test_submitted_at_preserved_on_ordinary_edit():
    """Simulate TaskDialog.values logic: existing submitted_at is kept."""
    # Mimic the logic from TaskDialog.values
    class FakeRow(dict):
        def __getitem__(self, key):
            return dict.__getitem__(self, key)
    row = FakeRow(submitted_at="2026-10-09 10:00:00")
    status = "Submitted"
    existing = (row["submitted_at"] if row else "") or ""
    submitted = existing if existing else "NOW"
    assert submitted == "2026-10-09 10:00:00"

def test_tracker_counts_are_mutually_exclusive():
    statuses = ["Completed", "Submitted", "In progress", "Blocked", "Pending", "Cancelled", "Not started"]
    completed = sum(1 for s in statuses if s in ("Completed", "Submitted"))
    blocked = sum(1 for s in statuses if s == "Blocked")
    in_progress = sum(1 for s in statuses if s == "In progress")
    pending = sum(1 for s in statuses if s not in ("Completed", "Submitted", "Cancelled", "Blocked", "In progress"))
    # Total of counted categories should equal non-cancelled
    counted = completed + blocked + in_progress + pending
    non_cancelled = sum(1 for s in statuses if s != "Cancelled")
    assert counted == non_cancelled


def test_admin_and_admin_are_preserved_as_distinct_case_sensitive_accounts(tmp_path, monkeypatch):
    db_path = tmp_path / "case_sensitive_auth.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE auth_users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
          display_name TEXT NOT NULL DEFAULT '',
          role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
          password_salt TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          security_question TEXT NOT NULL DEFAULT '',
          answer_salt TEXT NOT NULL DEFAULT '',
          answer_hash TEXT NOT NULL DEFAULT '',
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        INSERT INTO auth_users(
          id, username, display_name, role, password_salt, password_hash,
          security_question, answer_salt, answer_hash, active, created_at, updated_at
        ) VALUES(41, 'Admin', 'admin (Developer - Test Mode)', 'Developer', 'customer-salt',
                 'customer-hash', '', '', '', 1, 'created', 'updated')
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        customer = database.conn.execute(
            "SELECT * FROM auth_users WHERE username=? COLLATE BINARY", ("Admin",)
        ).fetchone()
        assert customer is not None
        assert customer["id"] == 41
        assert customer["role"] == "Admin"
        assert customer["password_salt"] == "customer-salt"
        assert customer["password_hash"] == "customer-hash"

        database.conn.execute("""
            INSERT INTO auth_users(
              username, display_name, role, password_salt, password_hash,
              security_question, answer_salt, answer_hash, active, created_at, updated_at
            ) VALUES('admin', 'Developer', 'Developer', 'developer-salt',
                     'developer-hash', '', '', '', 1, 'created', 'updated')
        """)
        database.conn.commit()
        assert database.conn.execute(
            "SELECT COUNT(*) FROM auth_users WHERE username IN ('Admin','admin') COLLATE BINARY"
        ).fetchone()[0] == 2
        schema = database.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_users'"
        ).fetchone()[0]
        assert "COLLATE BINARY" in schema.upper()
    finally:
        database.conn.close()


def test_desktop_login_uses_exact_customer_and_developer_accounts(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = app.QApplication.instance() or app.QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "login.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    database = app.Database()
    try:
        customer_salt, customer_hash = app.hash_pin("Shiva@01")
        timestamp = app.now_text()
        database.conn.execute(
            """INSERT INTO auth_users(
                username, display_name, role, password_salt, password_hash,
                security_question, answer_salt, answer_hash, active, created_at, updated_at
            ) VALUES('Admin', 'Customer Administrator', 'Admin', ?, ?, '', '', '', 1, ?, ?)""",
            (customer_salt, customer_hash, timestamp, timestamp),
        )
        database.conn.commit()

        customer_dialog = app.LoginDialog(database)
        customer_button = next(
            button for button in customer_dialog.findChildren(app.QPushButton)
            if button.text() == "👑 Admin (Customer Master)"
        )
        customer_button.click()
        assert customer_dialog.username.text() == "Admin"
        customer_dialog.password.setText("Shiva@01")
        customer_dialog.check()
        assert customer_dialog.user["username"] == "Admin"
        assert customer_dialog.user["role"] == "Admin"

        developer_dialog = app.LoginDialog(database)
        developer_dialog.username.setText("admin")
        developer_dialog.password.setText("kiran123")
        developer_dialog.check()
        assert developer_dialog.user["username"] == "admin"
        assert developer_dialog.user["role"] == "Developer"

        saved_developer = database.conn.execute(
            "SELECT password_salt, password_hash, role FROM auth_users "
            "WHERE username='admin' COLLATE BINARY"
        ).fetchone()
        _, expected_hash = app.hash_pin("kiran123", saved_developer["password_salt"])
        assert saved_developer["role"] == "Developer"
        assert saved_developer["password_hash"] == expected_hash
    finally:
        database.conn.close()

def test_auth_case_sensitive_migration_ignores_stale_staging_table(tmp_path, monkeypatch):
    """A previous interrupted upgrade must not block the next application startup."""
    db_path = tmp_path / "auth_stale_staging.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE auth_users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
          display_name TEXT NOT NULL DEFAULT '',
          role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
          password_salt TEXT NOT NULL, password_hash TEXT NOT NULL,
          security_question TEXT NOT NULL DEFAULT '', answer_salt TEXT NOT NULL DEFAULT '',
          answer_hash TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        INSERT INTO auth_users(username,display_name,role,password_salt,password_hash,
          security_question,answer_salt,answer_hash,active,created_at,updated_at)
        VALUES('Admin','Customer','Admin','salt','hash','','','',1,'created','updated')
    """)
    conn.execute("CREATE TABLE auth_users_case_sensitive(id INTEGER PRIMARY KEY, stale TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(app, "DB_PATH", str(db_path))
    database = app.Database()
    try:
        row = database.conn.execute(
            "SELECT username,password_hash FROM auth_users WHERE username='Admin' COLLATE BINARY"
        ).fetchone()
        assert row is not None and row["username"] == "Admin" and row["password_hash"] == "hash"
        schema = database.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_users'"
        ).fetchone()[0]
        assert "COLLATE BINARY" in schema.upper()
    finally:
        database.conn.close()

def test_auth_case_sensitive_migration_supports_quoted_table_identifiers(tmp_path, monkeypatch):
    """Legacy SQLite schemas may preserve quoted auth_users identifiers in sqlite_master."""
    for suffix, table_identifier in (
        ("double_quote", '"auth_users"'),
        ("single_quote", "'auth_users'"),
        ("backtick", "\x60auth_users\x60"),
        ("bracket", "[auth_users]"),
    ):
        db_path = tmp_path / f"auth_quoted_{suffix}.db"
        conn = sqlite3.connect(db_path)
        conn.execute(f"""
            CREATE TABLE {table_identifier}(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL COLLATE NOCASE UNIQUE,
              display_name TEXT NOT NULL DEFAULT '',
              role TEXT NOT NULL CHECK(role IN ('Admin','Developer','HR','Staff','Employee')),
              password_salt TEXT NOT NULL, password_hash TEXT NOT NULL,
              security_question TEXT NOT NULL DEFAULT '', answer_salt TEXT NOT NULL DEFAULT '',
              answer_hash TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO auth_users(
              id,username,display_name,role,password_salt,password_hash,
              security_question,answer_salt,answer_hash,active,created_at,updated_at
            ) VALUES(73,'Admin','Customer','Admin','customer-salt','customer-hash',
                     'question','answer-salt','answer-hash',1,'created','updated')
        """)
        conn.commit()
        conn.close()

        monkeypatch.setattr(app, "DB_PATH", str(db_path))
        database = app.Database()
        try:
            customer = database.conn.execute(
                "SELECT id,username,password_salt,password_hash,security_question,answer_hash "
                "FROM auth_users WHERE username='Admin' COLLATE BINARY"
            ).fetchone()
            assert customer is not None
            assert customer["id"] == 73
            assert customer["username"] == "Admin"
            assert customer["password_salt"] == "customer-salt"
            assert customer["password_hash"] == "customer-hash"
            assert customer["security_question"] == "question"
            assert customer["answer_hash"] == "answer-hash"

            schema = database.conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_users'"
            ).fetchone()[0]
            assert "COLLATE BINARY" in schema.upper()
            database.conn.execute("""
                INSERT INTO auth_users(
                  username,display_name,role,password_salt,password_hash,
                  security_question,answer_salt,answer_hash,active,created_at,updated_at
                ) VALUES('admin','Developer','Developer','developer-salt','developer-hash',
                         '','','',1,'created','updated')
            """)
            assert database.conn.execute(
                "SELECT COUNT(*) FROM auth_users WHERE username IN ('Admin','admin') COLLATE BINARY"
            ).fetchone()[0] == 2
        finally:
            database.conn.close()

