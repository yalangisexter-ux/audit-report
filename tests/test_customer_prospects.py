import hashlib

import openpyxl

import customer_prospects as prospects


def _make_reference_workbooks(tmp_path):
    database_path = tmp_path / "customer database.xlsx"
    database = openpyxl.Workbook()
    stores = database.active
    stores.title = "Haryana stores"
    stores.append([
        "Business Name", "Business Category", "State", "City", "Mobile Number",
        "Connected/Not Connected", "Verified (Yes/No)", "Google Maps Link",
    ])
    stores.append(["North Fitness Hub", "Sports retailer", "Haryana", "Gurugram", "9000000001", "Connected", "Yes", "https://maps.example/store"])
    stores.append(["Business Name", "Business Category", "State", "City", "Mobile Number", "Connected/Not Connected", "Verified (Yes/No)", "Google Maps Link"])
    stores.append([None, "section note", None, None, None, None, None, None])

    gyms = database.create_sheet("Punjab gym")
    gyms.append(["Business Name", "Business Category", "Contact Person", "Phone Number", "State", "City", "Address", "Google Maps"])
    gyms.append(["Bodyweight Studio", "Gym", "Manager", "9000000002", "Punjab", "Ludhiana", "Main Road", "https://maps.example/gym"])
    database.save(database_path)

    dashboard_path = tmp_path / "store dashboard.xlsx"
    dashboard = openpyxl.Workbook()
    sheet = dashboard.active
    sheet.append(["State/UT", "Stores"])
    sheet.append(["Haryana", 2])
    sheet.append(["Punjab", 1])
    sheet.append(["TOTAL", 3])
    dashboard.save(dashboard_path)
    return database_path, dashboard_path


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_workbooks_load_read_only_and_normalize_regional_schemas(tmp_path):
    database_path, dashboard_path = _make_reference_workbooks(tmp_path)
    database_before = _sha256(database_path)
    dashboard_before = _sha256(dashboard_path)

    records, stats = prospects.parse_database_workbook(database_path)
    dashboard_counts, dashboard_total = prospects.parse_dashboard_workbook(dashboard_path)

    assert len(records) == 2
    assert records[0]["kind"] == "Store"
    assert records[0]["business_name"] == "North Fitness Hub"
    assert records[0]["phone"] == "9000000001"
    assert records[0]["connection"] == "Connected"
    assert records[0]["verified"] == "Yes"
    assert records[1]["kind"] == "Gym"
    assert records[1]["state"] == "Punjab"
    assert stats == {"scanned_rows": 3, "skipped_unidentified": 1}
    assert dashboard_counts == {"Haryana": 2, "Punjab": 1}
    assert dashboard_total == 3
    assert _sha256(database_path) == database_before
    assert _sha256(dashboard_path) == dashboard_before


def test_regional_summary_shows_source_counts_and_variance_separately():
    records = [
        {"kind": "Store", "state": "Haryana"},
        {"kind": "Store", "state": "Haryana"},
        {"kind": "Gym", "state": "Haryana"},
        {"kind": "Gym", "state": "Punjab"},
    ]

    rows = prospects.build_regional_summary(records, {"Haryana": 3, "Punjab": 1})

    assert rows == [
        {"state": "Haryana", "stores": 2, "gyms": 1, "dashboard_stores": 3, "variance": -1},
        {"state": "Punjab", "stores": 0, "gyms": 1, "dashboard_stores": 1, "variance": -1},
    ]

    assert len(prospects.INDIA_REGIONS) == 36
    assert len(prospects.build_regional_summary([], include_all_regions=True)) == 36


def test_customer_prospects_tab_filters_loaded_rows_locally(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    qt_app = QApplication.instance() or QApplication([])
    database_path, dashboard_path = _make_reference_workbooks(tmp_path)
    tab = prospects.CustomerProspectsTab()
    try:
        assert tab.load_database_workbook(str(database_path))
        assert tab.load_dashboard_workbook(str(dashboard_path))
        assert tab.pages.count() == 2
        assert tab.leads_table.rowCount() == 2
        assert tab.kpi_values["prospects"].text() == "2"
        assert tab.kpi_values["dashboard"].text() == "3"
        assert "Difference: -2" in tab.reconciliation_label.text()

        tab.kind_filter.setCurrentText("Gym")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(0)
        assert not tab.leads_table.isRowHidden(1)
        assert tab.results_label.text().startswith("Showing 1 of 2")
        qt_app.processEvents()
    finally:
        tab.close()


def test_main_window_exposes_customer_prospects_tab(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    import app
    from PySide6.QtWidgets import QApplication

    qt_app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "customer-prospects.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    database = app.Database()
    initially_seeded = prospects.load_saved_prospects(database)
    web_record = {
        **prospects.RESEARCHED_WEB_LEADS[0],
        "kind": "Store",
        "business_category": "Sports nutrition retailer",
        "source_name": prospects.RESEARCHED_SOURCE_NAME,
        "source_url": prospects.RESEARCHED_SOURCE_URL,
        "source_type": "Official web listing",
        "source_checked_at": prospects.RESEARCH_DATE,
        "source_status": prospects.RESEARCHED_SOURCE_STATUS,
    }
    first_import = prospects.persist_prospect_records(database, [web_record])
    second_import = prospects.persist_prospect_records(database, [web_record])
    seed_again = prospects.seed_official_web_prospects(database)
    window = app.MainWindow(database, {"username": "Prospect QA", "role": "Admin"})
    try:
        saved = prospects.load_saved_prospects(database)
        index = window.tabs.indexOf(window.customer_tab)
        assert index >= 0
        assert window.tabs.tabText(index) == "📈  Customer Prospects"
        assert window.sidebar_buttons[index][0].toolTip() == "📈  Customer Prospects"
        assert len(initially_seeded) >= len(prospects.RESEARCHED_WEB_LEADS)
        assert first_import == {"inserted": 0, "duplicates": 1}
        assert second_import == {"inserted": 0, "duplicates": 1}
        assert seed_again == {"inserted": 0, "duplicates": 0}
        matching = [s for s in saved if s["business_name"] == web_record["business_name"]]
        assert matching and matching[0]["source_url"] == prospects.RESEARCHED_SOURCE_URL
        assert matching[0]["source_status"] == prospects.RESEARCHED_SOURCE_STATUS
        assert len(window.customer_tab.records) >= len(prospects.RESEARCHED_WEB_LEADS)
        qt_app.processEvents()
    finally:
        window.close()
        database.conn.close()


def test_negative_filter_excludes_pharmacy_herbal_healthkart():
    # Strict negative filter checks
    assert prospects.NEGATIVE_FILTER_PATTERN.search("Apollo Pharmacy Store")
    assert prospects.NEGATIVE_FILTER_PATTERN.search("MedPlus Medical and Chemist")
    assert prospects.NEGATIVE_FILTER_PATTERN.search("Herbalife Nutrition Center")
    assert prospects.NEGATIVE_FILTER_PATTERN.search("Patanjali Ayurvedic Shop")
    assert prospects.NEGATIVE_FILTER_PATTERN.search("HealthKart Store Rohini")
    assert prospects.NEGATIVE_FILTER_PATTERN.search("Health Kart Store")

    # Clean supplement stores should NOT be matched
    assert not prospects.NEGATIVE_FILTER_PATTERN.search("Alpha Sports Nutrition")
    assert not prospects.NEGATIVE_FILTER_PATTERN.search("Fit Fuel Supplements")
    assert not prospects.NEGATIVE_FILTER_PATTERN.search("Pro Body Nutrition")
    assert not prospects.NEGATIVE_FILTER_PATTERN.search("Optimum Vitamin Store")


def test_export_csv_pdf_doc_generate_files(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

    qt_app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)

    tab = prospects.CustomerProspectsTab()
    tab.records = [
        {
            "state": "Himachal Pradesh", "city": "Shimla", "area": "BCS market",
            "business_category": "Vitamin & supplements stores", "business_name": "NR Nutrition and Supplements",
            "phone": "88898 50001", "address": "3rd Floor of Building, BCS Market, Shimla 171009",
            "maps": "https://maps.google.com/test", "website": "https://nr.example"
        }
    ]
    tab._fill_leads_table()

    # Test CSV export
    csv_file = str(tmp_path / "test_out.csv")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (csv_file, "CSV"))
    tab.export_csv()
    assert (tmp_path / "test_out.csv").is_file()
    assert "NR Nutrition and Supplements" in (tmp_path / "test_out.csv").read_text(encoding="utf-8")

    # Test PDF export
    pdf_file = str(tmp_path / "test_out.pdf")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (pdf_file, "PDF"))
    tab.export_pdf()
    assert (tmp_path / "test_out.pdf").is_file()
    assert (tmp_path / "test_out.pdf").stat().st_size > 500

    # Test DOC export
    doc_file = str(tmp_path / "test_out.doc")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (doc_file, "DOC"))
    tab.export_doc()
    assert (tmp_path / "test_out.doc").is_file()
    assert "NR Nutrition and Supplements" in (tmp_path / "test_out.doc").read_text(encoding="utf-8")

    tab.close()
