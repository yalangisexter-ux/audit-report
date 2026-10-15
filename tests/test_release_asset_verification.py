"""Tests for secure verification of downloaded GitHub release installers."""
import hashlib

import pytest

import app


def test_valid_hhmm_rejects_malformed_attendance_times():
    assert app.valid_hhmm("09:30") is True
    assert app.valid_hhmm("23:59") is True
    assert app.valid_hhmm("24:00") is False
    assert app.valid_hhmm("9:30") is False
    assert app.valid_hhmm("noon") is False


def test_release_asset_checksum_accepts_matching_sha256():
    data = b"trusted installer payload"
    asset = {"digest": "sha256:" + hashlib.sha256(data).hexdigest()}
    assert app.verify_release_asset_bytes(data, asset) is True


def test_release_asset_checksum_rejects_modified_payload():
    asset = {"digest": "sha256:" + hashlib.sha256(b"original").hexdigest()}
    with pytest.raises(ValueError, match="checksum verification failed"):
        app.verify_release_asset_bytes(b"modified", asset)


def test_release_asset_requires_digest_for_updates():
    with pytest.raises(ValueError, match="no SHA-256 digest"):
        app.verify_release_asset_bytes(b"payload", {}, require_digest=True)


def test_legacy_rollback_asset_can_be_used_without_digest():
    # Older releases may not expose digest metadata; size and trusted HTTPS URL
    # are checked by the rollback flow before this helper is called.
    assert app.verify_release_asset_bytes(b"legacy payload", {}, require_digest=False) is False


def test_release_asset_rejects_malformed_digest():
    with pytest.raises(ValueError, match="invalid SHA-256 digest"):
        app.verify_release_asset_bytes(b"payload", {"digest": "md5:abc"})



def test_pre_migration_backup_is_a_valid_sqlite_snapshot(tmp_path):
    source_path = tmp_path / "employee_audit.db"
    backup_dir = tmp_path / "backups"
    connection = __import__("sqlite3").connect(source_path)
    connection.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO employees (name) VALUES (?)", ("Existing employee",))
    connection.commit()
    connection.close()

    backup_path = app.create_pre_migration_backup(source_path, backup_dir)

    assert backup_path is not None
    backup = __import__("sqlite3").connect(backup_path)
    assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert backup.execute("SELECT name FROM employees").fetchone()[0] == "Existing employee"
    backup.close()


def test_pre_migration_backup_failure_stops_migrations(tmp_path, monkeypatch):
    source_path = tmp_path / "employee_audit.db"
    connection = __import__("sqlite3").connect(source_path)
    connection.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT)")
    connection.commit()
    connection.close()

    sqlite3 = __import__("sqlite3")

    def fail_connect(*args, **kwargs):
        raise sqlite3.OperationalError("simulated backup failure")

    monkeypatch.setattr(sqlite3, "connect", fail_connect)
    with pytest.raises(RuntimeError, match="migrations were cancelled"):
        app.create_pre_migration_backup(source_path, tmp_path / "backups")



def test_bundled_wallpaper_artwork_is_available():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for name in ("galaxy.svg", "lord_shiva.svg", "love_couples.svg", "milky_way_waves.svg", "ocean_waves.svg"):
        artwork = root / "assets" / "wallpapers" / name
        assert artwork.is_file()
        assert "<svg" in artwork.read_text(encoding="utf-8")


def test_home_ui_restores_icons_and_quick_dropdowns():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "homeThemeDropdown" in source
    assert "homeWallpaperDropdown" in source
    assert 'icon_label = QLabel(symbol)' in source
    assert 'QPixmap' in source
    assert 'QWidget#appPageSurface { background: #FFFFFF; color: #0F172A; }' in source
    assert 'QWidget#appPageSurface { background: transparent; color: #F8FAFC; }' in source
    assert 'background-color: #F8FAFC' in source
    assert 'background-color: #111827' in source
    assert 'combobox-popup: 0' in source
    assert 'QComboBox QListView::item:selected' in source
    assert 'page.setObjectName("appPageSurface")' in source
    assert 'page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)' in source
    assert 'QWidget#homeContent, QWidget#pageContent { background-color: #F8FAFC' in source
    assert 'QWidget#homeContent, QWidget#pageContent { background-color: #111827' in source
    assert 'page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)' in source
    assert 'QComboBox QAbstractItemView::item:selected' in source
    assert 'self.header_logo_menu.hide()' in source
    assert 'mode == "Shiva"' in source
    assert '"Lord Shiva": ("lord_shiva.jpg"' in source
    assert '"Shiva": ("lord_shiva.jpg"' not in source
    assert 'fade = 22 +' in source
    assert 'final_veil.setColorAt(1.0, QColor(255, 255, 255, 188))' in source
    assert 'QWidget#homeContent { background: #FFFFFF;' in source
    assert 'QWidget#pageContent { background: #FFFFFF;' in source
    assert 'base.setColorAt(0.0, QColor("#FFFFFF"))' in source
    assert 'if is_day else [(124, 92, 252, 42)' in source
    assert 'for col, width in enumerate((156, 120, 158, 126, 126, 96, 220))' in source
    assert 'Scroll horizontally to see every column on smaller screens.' in source
    assert 'update_label.setWordWrap(True)' in source
    assert 'dialog_width = max(240, min(440, available_width - 32))' in source
    assert 'self._update_progress.setMinimumWidth(dialog_width)' in source
    assert 'self.brand_banner = QFrame()' in source
    assert 'main_content_layout.addWidget(self.brand_banner)' in source
    assert 'page_layout.addWidget(welcome)' not in source
    assert 'def _show_message(parent, message, icon):' in source
    assert 'label.setWordWrap(True)' in source
    assert 'dialog_width = max(240, min(500, available_width - 32))' in source
    assert 'box.setMinimumWidth(dialog_width)' in source
    assert 'self.header_clock.show()' in source
    assert 'self._wrap_page_in_scroll(self.dashboard, root)' in source
    assert 'grid.addWidget(productivity, 1, 1, 1, 2)' in source
    assert 'Qt.TextFlag.TextWordWrap, display_name)' in source
    assert 'if slot >= 72:' in source and 'elif slot >= 38:' in source
    assert 'tooltip_for_index(self, index)' in source
    assert 'show_accessible_tooltip(event.globalPosition().toPoint(), self.tooltip_for_index(hovered), self)' in source
    assert 'class AccessibleTooltipController(QObject)' in source
    assert 'color: #111827' in source and 'background-color: #FFFFFF' in source
    assert 'QProgressBar#dashboardProgress' in source
    assert 'self._update_progress.setWindowIcon(QIcon(resource_path("assets/raw_strength_icon.ico")))' in source
    assert "QListView::item:selected {{ background: {colors['accent']}; color: #FFFFFF; }}" in source
    assert 'QWidget#guideItem { background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #7C5CFC;' in source
    assert 'QWidget#guideItem { background: #0F172A; border: 1px solid #334155; border-left: 4px solid #A78BFA;' in source
    assert 'QTextEdit#reportPreview { background: #111827' in source
    assert 'QPrintPreviewDialog' in source
    assert 'def open_print_preview(self):' in source
    assert 'QPrintPreviewDialog(printer, self)' in source
    assert "def apply_content_surface_styles(self, theme_name=None):" in source
    assert 'QWidget#kpiCard, QWidget#dashboardPanel { background-color: #FFFFFF; color: #0F172A;' in source
    assert 'QWidget#kpiCard, QWidget#dashboardPanel { background-color: #0F172A; color: #F8FAFC;' in source
    assert 'QWidget#settingsContent { background-color: #F8FAFC; color: #0F172A; }' in source
    assert 'QWidget#settingsContent { background-color: #111827; color: #F8FAFC; }' in source
    assert 'background, foreground, border = "#FFFFFF", "#0F172A", "#E2E8F0"' in source
    assert 'background, foreground, border = "#111827", "#F8FAFC", "#64748B"' in source
    assert "self.apply_content_surface_styles(theme_name)" in source


def test_live_wallpapers_use_high_resolution_photos_with_animation():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "class WallpaperPhotoLoader(QThread)" in source
    assert "PHOTO_WALLPAPERS" in source
    assert "images.unsplash.com/photo-1707057538849-f723c167324b" in source
    assert "images.unsplash.com/photo-1429305223369-4d065fdb6f53" in source
    assert "images.unsplash.com/photo-1533743725296-2e099eed32c6" in source
    assert "wallpaper_pixmap" in source
    assert "zoom = 1.035 + 0.012 * math.sin(self.phase * 0.35)" in source
    assert "Real photographic wallpapers use a slow Ken Burns pan/zoom" in source
    assert "QSvgRenderer" not in source


def test_release_build_bundles_photo_wallpapers_for_offline_use():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "master.yml").read_text(encoding="utf-8")
    app_source = (root / "app.py").read_text(encoding="utf-8")
    assert "Download high-resolution photographic wallpaper assets" in workflow
    assert '"galaxy.jpg"' in workflow
    assert '"milky_way.jpg"' in workflow
    assert '"ocean_waves.jpg"' in workflow
    assert '"lord_shiva.jpg"' in workflow
    assert '"love_couples.jpg"' in workflow
    assert 'Path("assets") / "wallpapers" / "photos" / filename' in app_source
    assert '--add-data "assets;assets"' in workflow


def test_dashboard_clock_colorful_icons_and_print_preview_regression():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "def refresh_header_clock(self):" in source
    assert "self.header_clock = QLabel()" in source
    assert "main_content_layout.addWidget(self.brand_banner)" in source
    assert "self._header_clock_timer.start(1000)" in source
    assert "self.header_clock.show()" in source
    assert "self._dashboard_clock_timer.start(1000)" not in source
    assert 'page_layout.addWidget(self.home_scroll)' in source
    assert 'page_layout.addWidget(welcome)' not in source
    assert 'def _show_message(parent, message, icon):' in source
    assert 'label.setWordWrap(True)' in source
    assert 'dialog_width = max(240, min(500, available_width - 32))' in source
    assert 'box.setMinimumWidth(dialog_width)' in source
    assert '"PRESENT TODAY", "✓", "#15803D"' in source
    assert '"ABSENT TODAY", "×", "#BE123C"' in source
    assert 'class AnimatedDashboardIcon(QLabel)' in source
    assert 'self._hover_animation.start()' in source
    assert 'class AnimatedRGBFrame(QFrame)' in source
    assert 'QConicalGradient(bounds.center(), self._rotation)' in source
    assert 'self.brand_logo_frame = AnimatedRGBFrame(hover_only=True, outline_inset=2)' in source
    assert 'self.brand_logo_frame.setFixedSize(92, 92)' in source
    assert 'self.header_clock_frame.setFixedSize(254, 66)' in source
    assert 'self.brand_logo.setPixmap(brand_mark_pixmap(68))' in source
    assert 'self.showMaximized()' in source
    assert 'class InteractionFeedback(QObject)' in source
    assert 'QEvent.Type.MouseButtonPress' in source and 'QEvent.Type.MouseButtonRelease' in source
    assert 'self.findChildren(QAbstractItemView)' in source
    assert 'self.findChildren(QProgressBar)' in source and 'self.findChildren(ProductivityChart)' in source
    assert 'self.apply_interaction_animations()' in source
    assert 'not is_explicitly_completed_task_status(task["status"])' in source
    assert 'def is_explicitly_completed_task_status(status):' in source
    assert 'not_checked = max(0, total - present - absent - leave)' in source
    assert "Live print preview — updates when report options change" in source
    assert "self.report_summary.setMinimumHeight(220)" in source
    assert "def preview_report(self):" in source
    assert "def print_report(self):" in source


def test_release_version_tuple_normalizes_v_prefix_and_rejects_invalid_tags():
    assert app.release_version_tuple("v1.2.31") == (1, 2, 31)
    assert app.release_version_tuple("1.2.32") == (1, 2, 32)
    with pytest.raises(ValueError):
        app.release_version_tuple("v1.2")
    with pytest.raises(ValueError):
        app.release_version_tuple("v1.2.3-rc1")


def test_release_metadata_is_consistent_and_newer_than_installed_version():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    version = app.APP_VERSION
    assert app.release_version_tuple(version) > app.release_version_tuple("1.2.55")
    assert f'APP_VERSION = "{version}"' in (root / "build_info.py").read_text(encoding="utf-8")
    assert f'MyAppVersion "{version}"' in (root / "installer.iss").read_text(encoding="utf-8")
    assert f"StringStruct('FileVersion', '{version}.0')" in (root / "version_info.txt").read_text(encoding="utf-8")
    assert f"StringStruct('ProductVersion', '{version}.0')" in (root / "version_info.txt").read_text(encoding="utf-8")
    assert f"filevers=(1, 2, {app.release_version_tuple(version)[2]}, 0)" in (root / "version_info.txt").read_text(encoding="utf-8")
    assert f"prodvers=(1, 2, {app.release_version_tuple(version)[2]}, 0)" in (root / "version_info.txt").read_text(encoding="utf-8")
    workflow = (root / ".github" / "workflows" / "master.yml").read_text(encoding="utf-8")
    assert f'APP_VERSION: "{version}"' in workflow
    assert f"tag_name: v{version}" in workflow
    assert f"Raw Strength Employee Audit Manager v{version}" in workflow


def test_update_worker_uses_latest_published_stable_release(monkeypatch):
    release = [{
        "tag_name": "v1.2.36",
        "draft": False,
        "prerelease": False,
        "published_at": "2026-10-14T08:00:00Z",
        "assets": [],
    }]
    requested = []
    monkeypatch.setattr(
        app.UpdateWorker,
        "request_bytes",
        staticmethod(lambda url, accept="application/vnd.github+json": (
            requested.append(url) or __import__("json").dumps(release).encode()
        )),
    )
    worker = app.UpdateWorker("1.2.35")
    emitted = []
    worker.current.connect(lambda version: emitted.append(("current", version)))
    worker.failed.connect(lambda message: emitted.append(("failed", message)))
    worker.ready.connect(lambda path, version: emitted.append(("ready", version)))

    worker.run()

    assert requested == [
        "https://api.github.com/repos/yalangisexter-ux/audit-report/releases?per_page=100"
    ]
    assert emitted
    assert emitted[0][0] == "failed"
    assert "missing a trusted installer" in emitted[0][1]
def test_update_request_uses_bounded_timeout_and_reports_check_progress(monkeypatch):
    import urllib.request
    import app

    captured = {}

    class FakeResponse:
        status = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(app, "urlopen", fake_urlopen)
    payload = app.UpdateWorker.request_bytes("https://api.github.com/test")
    assert payload == b'{"ok": true}'
    assert captured["timeout"] == 20


def test_update_worker_retries_after_a_read_timeout(monkeypatch):
    release = [{
        "tag_name": "v1.2.36",
        "draft": False,
        "prerelease": False,
        "published_at": "2026-10-14T08:00:00Z",
        "assets": [],
    }]
    attempts = []

    def request(url, accept="application/vnd.github+json"):
        attempts.append(url)
        if len(attempts) == 1:
            raise TimeoutError("The read operation timed out")
        return __import__("json").dumps(release).encode()

    monkeypatch.setattr(app.UpdateWorker, "request_bytes", staticmethod(request))
    monkeypatch.setattr(__import__("time"), "sleep", lambda _seconds: None)
    worker = app.UpdateWorker("1.2.35")
    emitted = []
    worker.failed.connect(lambda message: emitted.append(message))

    worker.run()

    assert len(attempts) == 2
    assert emitted
    assert "missing a trusted installer" in emitted[0]


def test_previous_release_choices_only_returns_installable_stable_versions_sorted_newest_first():
    def release(tag, *, draft=False, prerelease=False, published=True, size=1000000, url=None):
        return {
            "tag_name": tag,
            "draft": draft,
            "prerelease": prerelease,
            "published_at": "2026-10-14T00:00:00Z" if published else None,
            "assets": [{
                "name": "RawStrengthEmployeeAuditManager-Setup.exe",
                "browser_download_url": url or (
                    "https://github.com/yalangisexter-ux/audit-report/releases/download/"
                    + tag + "/RawStrengthEmployeeAuditManager-Setup.exe"
                ),
                "size": size,
            }],
        }

    releases = [
        release("v1.2.10"),
        release("v1.2.31"),
        release("v1.2.99", prerelease=True),
        release("v9.0.0", draft=True),
        release("v1.2.30", published=False),
        release("v1.2.29", size=999999),
        release("v1.2.28", url="https://example.com/installer.exe"),
        release("not-a-version"),
        release("v1.2.32"),
    ]
    choices = app.previous_release_choices(releases, "1.2.32")
    assert [choice[0] for choice in choices] == ["v1.2.31", "v1.2.10"]


def test_dashboard_summaries_and_progress_widgets_remain_accurate(monkeypatch, tmp_path):
    from datetime import date, datetime
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = app.QApplication.instance() or app.QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "dashboard.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    today = date.today().isoformat()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    employees = [("EMP-1", "Present Person"), ("EMP-2", "Absent Person"),
                 ("EMP-3", "On Leave"), ("EMP-4", "Unmarked Person")]
    for code, name in employees:
        db.conn.execute(
            "INSERT INTO employees(employee_code,name,joining_date,active,created_at) VALUES(?,?,?,?,?)",
            (code, name, today, 1, timestamp),
        )
    employee_ids = [row["id"] for row in db.employees()]
    for employee_id, status, check_in in (
        (employee_ids[0], "Present", "09:00"),
        # An explicit Absent status must win over a stale or inconsistent check-in value.
        (employee_ids[1], "Absent", "09:15"),
        (employee_ids[2], "Leave", ""),
    ):
        db.conn.execute(
            "INSERT INTO attendance(employee_id,work_date,check_in,attendance_status,updated_at) VALUES(?,?,?,?,?)",
            (employee_id, today, check_in, status, timestamp),
        )
    tasks = [(employee_ids[0], "In progress", 50), (employee_ids[1], "Cancelled", 0),
             (employee_ids[2], "Submitted", 100), (employee_ids[3], None, 100),
             (employee_ids[3], "N/A", 100)]
    for employee_id, status, progress in tasks:
        db.conn.execute(
            "INSERT INTO tasks(employee_id,task_date,title,status,progress,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (employee_id, today, f"{status} task", status, progress, timestamp, timestamp),
        )
    db.conn.commit()

    window = app.MainWindow(db, {"username": "Preview", "role": "Admin"})
    try:
        window.apply_theme("day")
        for _ in range(3):
            window.refresh_dashboard()
        qt_app.processEvents()

        assert "1 Present" in window.dashboard_attendance_summary.text()
        assert "1 Absent" in window.dashboard_attendance_summary.text()
        assert "1 Leave" in window.dashboard_attendance_summary.text()
        assert "1 Not checked" in window.dashboard_attendance_summary.text()
        assert window.kpi_labels[3].text() == "3"
        bars = [window.dashboard_tasks.cellWidget(row, 3) for row in range(window.dashboard_tasks.rowCount())]
        assert len(bars) == len(tasks)
        assert all(isinstance(bar, app.QProgressBar) and bar.toolTip() for bar in bars)
    finally:
        window.close()
        db.conn.close()


def test_unknown_task_status_never_counts_as_completed_from_stale_progress(monkeypatch, tmp_path):
    from datetime import date, datetime

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = app.QApplication.instance() or app.QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "task-status.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    today = date.today().isoformat()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = db.conn.execute(
        "INSERT INTO employees(name,joining_date,active,created_at) VALUES(?,?,?,?)",
        ("Status Check", today, 1, timestamp),
    )
    employee_id = cursor.lastrowid
    for status in (None, "N/A", "Completed", "In progress"):
        db.conn.execute(
            "INSERT INTO tasks(employee_id,task_date,title,status,progress,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (employee_id, today, f"{status} task", status, 100, timestamp, timestamp),
        )
    db.conn.commit()
    window = app.MainWindow(db, {"username": "Preview", "role": "Admin"})
    try:
        metric = window.employee_productivity(db.employee(employee_id), date.today())
        assert metric["completed"] == 1
        assert metric["task_score"] == 50
    finally:
        window.close()
        db.conn.close()
    qt_app.processEvents()


def test_print_center_options_and_proof_links_work_in_exports(monkeypatch, tmp_path):
    import csv
    import xml.etree.ElementTree as ET
    import zipfile
    from datetime import date, datetime
    import reportlab.platypus

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = app.QApplication.instance() or app.QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "report-links.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    today = date.today().isoformat()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = db.conn.execute(
        "INSERT INTO employees(employee_code,name,department,joining_date,active,created_at) VALUES(?,?,?,?,?,?)",
        ("EMP-LINK", "Proof Link", "QA", today, 1, timestamp),
    )
    employee_id = cursor.lastrowid
    urls = "https://example.com/proof?id=1&x=2\nhttps://example.org/second"
    db.conn.execute(
        "INSERT INTO tasks(employee_id,task_date,title,status,progress,proof_url,proof_note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (employee_id, today, "Linked task", "Submitted", 100, urls, "See https://example.net/note", timestamp, timestamp),
    )
    exposed_url = (
        "https://docs.google.com/spreadsheets/d/long-example-document-id-"
        "0123456789abcdef0123456789abcdef/edit?gid=70451726&usp=sharing&resourcekey=sample-key"
    )
    exposed_note_url = "https://docs.google.com/document/d/exposed-note-proof/edit?usp=sharing"
    db.conn.execute(
        "INSERT INTO tasks(employee_id,task_date,title,status,progress,proof_url,proof_note,expose_link,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (employee_id, today, "Second linked task", "In progress", 50, exposed_url, f"Related proof: {exposed_note_url}", 1, timestamp, timestamp),
    )
    db.conn.execute(
        "INSERT INTO tasks(employee_id,task_date,title,status,progress,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (employee_id, today, "Task without proof", "Not started", 0, timestamp, timestamp),
    )
    db.conn.commit()
    window = app.MainWindow(db, {"username": "Preview", "role": "Admin"})
    try:
        window.eod_checks["proof_notes"].setChecked(True)
        options = window.selected_eod_options()
        docx_path = tmp_path / "proof-links.docx"
        pdf_path = tmp_path / "proof-links.pdf"
        csv_path = tmp_path / "proof-links.csv"
        window.make_docx(docx_path, today, employee_id, "Audit / EOD", options)
        window.make_pdf(pdf_path, today, employee_id, "Audit / EOD", options)
        window.export_report_csv(csv_path, today, employee_id, "Audit / EOD", options)

        with zipfile.ZipFile(docx_path) as archive:
            relationships = archive.read("word/_rels/document.xml.rels").decode("utf-8")
            document_xml = archive.read("word/document.xml").decode("utf-8")
        assert "https://example.com/proof?id=1&amp;x=2" in relationships
        assert "https://example.org/second" in relationships
        assert "https://example.net/note" in relationships
        assert "<w:hyperlink" in document_xml
        doc_root = ET.fromstring(document_xml)
        word_ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        docx_link_labels = [node.text for node in doc_root.findall(".//w:hyperlink//w:t", word_ns)]
        assert docx_link_labels == [exposed_url, exposed_note_url] + ["Tap here to view content"] * 3
        from docx import Document
        assert any(paragraph.text == "Proof / Evidence: N/A" for paragraph in Document(docx_path).paragraphs)
        pdf_bytes = pdf_path.read_bytes()
        assert b"/URI" in pdf_bytes and b"https://example.com/proof" in pdf_bytes

        captured_story = []

        class CaptureDocument:
            def __init__(self, *args, **kwargs):
                pass

            def build(self, story, **kwargs):
                captured_story.extend(story)

        monkeypatch.setattr(reportlab.platypus, "SimpleDocTemplate", CaptureDocument)
        window.make_pdf(tmp_path / "captured-proof-links.pdf", today, employee_id, "Audit / EOD", options)
        proof_paragraphs = [
            flowable for flowable in captured_story
            if hasattr(flowable, "frags") and getattr(flowable, "getPlainText", lambda: "")().find("Proof") >= 0
        ]
        assert any("Proof / Evidence: N/A" in paragraph.getPlainText() for paragraph in proof_paragraphs)
        pdf_link_fragments = [
            fragment for paragraph in proof_paragraphs for fragment in paragraph.frags
            if getattr(fragment, "link", None)
        ]
        visible_pdf_links = {}
        for fragment in pdf_link_fragments:
            target = fragment.link[0][1]
            visible_pdf_links.setdefault(target, "")
            visible_pdf_links[target] += fragment.text
        assert list(visible_pdf_links) == [
            exposed_url, exposed_note_url,
            "https://example.com/proof?id=1&x=2", "https://example.org/second", "https://example.net/note",
        ]
        assert visible_pdf_links == {
            exposed_url: exposed_url,
            exposed_note_url: exposed_note_url,
            "https://example.com/proof?id=1&x=2": "Tap here to view content",
            "https://example.org/second": "Tap here to view content",
            "https://example.net/note": "Tap here to view content",
        }
        assert all(fragment.textColor.hexval() == "0x0563c1" and fragment.us_lines for fragment in pdf_link_fragments)
        evidence_line = next(paragraph for paragraph in proof_paragraphs if "Proof / Evidence:" in paragraph.getPlainText())
        evidence_prefix = next(fragment for fragment in evidence_line.frags if "Proof / Evidence:" in fragment.text)
        assert evidence_prefix.textColor.hexval() == "0x1f2937"

        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
        proof_columns = [index for index, heading in enumerate(rows[0]) if heading.startswith("Proof link")]
        assert len(proof_columns) == 3
        assert rows[1][proof_columns[0]] == "N/A"
        assert rows[1][proof_columns[1]] == ""
        assert rows[1][proof_columns[2]] == ""
        assert rows[2][proof_columns[0]] == f'=HYPERLINK("{exposed_url}","{exposed_url}")'
        assert rows[2][proof_columns[1]] == f'=HYPERLINK("{exposed_note_url}","{exposed_note_url}")'
        assert rows[2][proof_columns[2]] == ""
        assert rows[3][proof_columns[0]] == '=HYPERLINK("https://example.com/proof?id=1&x=2","Tap here to view content")'
        assert rows[3][proof_columns[1]] == '=HYPERLINK("https://example.org/second","Tap here to view content")'
        assert rows[3][proof_columns[2]] == '=HYPERLINK("https://example.net/note","Tap here to view content")'
        assert "https://example.net/note" not in rows[3][rows[0].index("Proof notes")]

        window.report_type.setCurrentText("Employee Attendance")
        window.eod_checks["attendance_times"].setChecked(False)
        attendance_csv = tmp_path / "attendance.csv"
        window.export_report_csv(attendance_csv, today, employee_id, "Employee Attendance", window.selected_eod_options())
        with attendance_csv.open(encoding="utf-8-sig", newline="") as stream:
            attendance_headers = next(csv.reader(stream))
        assert "Check-in" not in attendance_headers and "Check-out" not in attendance_headers
    finally:
        window.close()
        db.conn.close()
    qt_app.processEvents()
