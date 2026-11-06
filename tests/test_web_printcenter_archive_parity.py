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
