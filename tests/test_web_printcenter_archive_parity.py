from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRINT_CENTER = ROOT / "frontend" / "src" / "PrintCenter.jsx"
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"


def test_print_center_can_select_view_print_and_export_historical_archived_pdfs():
    source = PRINT_CENTER.read_text(encoding="utf-8")
    assert "Historical archived PDF (optional)" in source
    assert "archive.map(item" in source
    assert "'/download'" in source
    assert "'/view'" in source
    assert "Export archived PDF copy" in source
    assert "View / Print archived PDF" in source
    assert "disabled={archivedSelected}" in source


def test_print_center_exposes_the_desktop_business_catalog_group_for_every_report_type():
    source = PRINT_CENTER.read_text(encoding="utf-8")
    audit_group = source.split("'Audit / EOD': [", 1)[1].split("],\n  'Employee Attendance'", 1)[0]
    assert "business_products" not in audit_group
    assert "business_services" not in audit_group
    assert "['attendance','Attendance status and times']" not in audit_group
    assert "Optional business data — include these catalogs in the report" in source
    assert "businessOptions.map" in source


def test_print_center_can_open_the_shared_archive_from_the_report_screen():
    source = PRINT_CENTER.read_text(encoding="utf-8")
    app = APP_SOURCE.read_text(encoding="utf-8")
    assert "onOpenArchive" in source
    assert "Browse saved reports" in source
    assert "archive={data.archive}" in app
    assert "onOpenArchive={()=>setTab('archive')}" in app


def test_web_eod_report_default_matches_desktop_attendance_visibility():
    import sqlite3
    from datetime import date

    import api_server

    assert api_server._REPORT_OPTION_DEFAULTS["attendance"] is False
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, name TEXT, employee_code TEXT, department TEXT,
            designation TEXT, phone TEXT, email TEXT, notes TEXT, active INTEGER
        );
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY, employee_id INTEGER, task_date TEXT, title TEXT,
            status TEXT, target_qty TEXT, actual_qty TEXT, progress INTEGER, priority TEXT,
            details TEXT, due_time TEXT, proof_url TEXT, proof_note TEXT,
            custom_values TEXT, next_action TEXT, manager_note TEXT
        );
        CREATE TABLE attendance (
            employee_id INTEGER, work_date TEXT, attendance_status TEXT,
            check_in TEXT, check_out TEXT, break_minutes INTEGER, attendance_note TEXT
        );
        """
    )
    report_date = date.today().isoformat()
    connection.execute(
        "INSERT INTO employees(id,name,employee_code,department,designation,phone,email,notes,active) "
        "VALUES(1,?,?,?,?,?,?,?,1)",
        ("Report Default Attendance Test", "RPT-DEFAULT", "QA", "Tester", "", "", ""),
    )
    connection.execute(
        "INSERT INTO attendance(employee_id,work_date,attendance_status,check_in,check_out,break_minutes,attendance_note) "
        "VALUES(1,?,'Present','09:00','17:00',0,'Recorded attendance')",
        (report_date,),
    )
    connection.commit()
    try:
        report = api_server._build_report_preview(
            api_server.ReportOptionsModel(date=report_date, report_type="Audit / EOD"),
            connection,
        )
        assert "EMPLOYEE: Report Default Attendance Test" in report["preview_text"]
        assert "Attendance: Present" not in report["preview_text"]
    finally:
        connection.close()


def test_print_center_refreshes_preview_automatically_for_desktop_trigger_fields():
    source = PRINT_CENTER.read_text(encoding="utf-8")

    assert "const previewSequence = useRef(0);" in source
    assert "const previewTimer = useRef(null);" in source
    assert "window.setTimeout" in source
    assert "}, 300);" in source
    assert "report.date, report.report_type" in source
    assert "report.employee_id, report.exclude_employee_id, report.options" in source
    assert "requestId === previewSequence.current" in source
    assert "Previewing…" in source


def test_print_center_restores_desktop_report_preferences_and_uses_desktop_default_format():
    source = PRINT_CENTER.read_text(encoding="utf-8")
    assert "apiFetch('/reports/options')" in source
    assert "method:'PUT'" in source
    assert "preferencesLoaded" in source
    assert "output_format:'docx'" in source
    assert "preferenceWrites.current[key]" in source
