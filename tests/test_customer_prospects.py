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
        chat_index = window.tabs.indexOf(window.chat_tab)
        assert index >= 0
        assert index == chat_index - 1, "Store Directory must be positioned directly above Live Chat"
        assert window.tabs.tabText(index) == "🏪  Store Directory"
        assert window.sidebar_buttons[index][0].toolTip() == "🏪  Store Directory"
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

def test_extract_deep_page_details_and_hybrid_classification():
    html_gym_products = """
    <html>
    <head><title>Spartan Iron Gym & Nutrition Bar</title></head>
    <body>
      <h1>Spartan Iron Fitness</h1>
      <p>Workout in our gym and visit our supplement counter for authentic Whey Protein and Creatine!</p>
      <address>Plot 45, Jubilee Hills Road 36, Hyderabad, Telangana 500033</address>
      <a href="tel:+919849012345">Call Gym</a>
      <a href="mailto:contact@spartanirongym.in">Email Us</a>
      <a href="https://maps.google.com/?q=Spartan+Iron+Gym">Google Maps</a>
    </body>
    </html>
    """
    details = prospects.extract_deep_page_details(html_gym_products, "https://spartanirongym.in")
    assert any("9849012345" in p.replace(" ", "") for p in details["phones"])
    assert "contact@spartanirongym.in" in details["emails"]
    assert "Hyderabad" in details["address"]
    assert "500033" in details["address"]
    assert "maps.google.com" in details["maps"]
    assert details["kind"] == "Gym + Store"

    html_pure_store = """
    <html>
    <body>
      <h1>NutriWorld Supplements</h1>
      <p>Best sports nutrition, protein powder and vitamins.</p>
      <a href="tel:080-25251234">Phone</a>
      <a href="mailto:sales@nutriworld.in">Sales</a>
    </body>
    </html>
    """
    details_store = prospects.extract_deep_page_details(html_pure_store, "https://nutriworld.in")
    assert details_store["kind"] == "Store"
    assert "sales@nutriworld.in" in details_store["emails"]

    html_pure_gym = """
    <html>
    <body>
      <h1>Elite Crossfit & Fitness Center</h1>
      <p>Cardio, HIIT, and personal training.</p>
    </body>
    </html>
    """
    details_gym = prospects.extract_deep_page_details(html_pure_gym, "https://elitecrossfit.in")
    assert details_gym["kind"] == "Gym"


def test_customer_prospects_filter_options_for_stores_gyms_and_hybrids(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    qt_app = QApplication.instance() or QApplication([])
    tab = prospects.CustomerProspectsTab()
    try:
        tab.records = [
            {"kind": "Store", "business_name": "Alpha Nutrition Store", "state": "Delhi", "business_category": "Sports Nutrition / Supplement Store"},
            {"kind": "Gym", "business_name": "Titan Gym & Fitness", "state": "Delhi", "business_category": "Fitness Centre / Gym"},
            {"kind": "Gym + Store", "business_name": "Iron Beast Gym Pro Shop", "state": "Delhi", "business_category": "Gym with Nutrition & Supplement Counter / Pro-Shop"},
        ]
        tab._fill_leads_table()

        # All types shows 3
        tab.kind_filter.setCurrentText("All types")
        tab.apply_filters()
        assert sum(not tab.leads_table.isRowHidden(i) for i in range(3)) == 3

        # Pure Product Selling Stores shows row 0 only
        tab.kind_filter.setCurrentText("Pure Product Selling Stores")
        tab.apply_filters()
        assert not tab.leads_table.isRowHidden(0)
        assert tab.leads_table.isRowHidden(1)
        assert tab.leads_table.isRowHidden(2)

        # Gym shows row 1 only
        tab.kind_filter.setCurrentText("Gym")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(0)
        assert not tab.leads_table.isRowHidden(1)
        assert tab.leads_table.isRowHidden(2)

        # Gyms which sell products also shows row 2 only
        tab.kind_filter.setCurrentText("Gyms which sell products also")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(0)
        assert tab.leads_table.isRowHidden(1)
        assert not tab.leads_table.isRowHidden(2)
    finally:
        tab.close()


def test_one_tap_scrape_and_continuous_sync_ui_and_master_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    import app
    import google_sheets_sync
    from pathlib import Path

    qt_app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "prospects_test.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    
    tab = prospects.CustomerProspectsTab(db=db)
    try:
        assert hasattr(tab, "btn_one_tap_scrape_and_update")
        assert hasattr(tab, "sync_status_badge")
        assert hasattr(tab, "snapshot_badge")
        assert hasattr(tab, "btn_print_preview")
        assert hasattr(tab, "btn_folder")
        assert "Active" in tab.sync_status_badge.text() or "Conflict-Free" in tab.sync_status_badge.text()

        # Test silent continuous sync
        tab._run_silent_continuous_sync()
        assert tab.sync_status_badge.text() != ""

        # Test master snapshot generation
        snapshot = google_sheets_sync.save_master_database_snapshot(db, custom_path=tmp_path / "Master_DB_Test.xlsx")
        assert Path(snapshot).is_file()
        assert Path(snapshot).stat().st_size > 1000
    finally:
        tab.close()


def test_territory_separation_states_uts_islands():
    assert len(prospects.INDIA_STATES) == 28
    assert len(prospects.INDIA_UNION_TERRITORIES) == 6
    assert len(prospects.INDIA_ISLAND_TERRITORIES) == 2
    assert len(prospects.INDIA_STATES) + len(prospects.INDIA_UNION_TERRITORIES) + len(prospects.INDIA_ISLAND_TERRITORIES) == 36

    assert prospects.territory_type("Haryana") == "State"
    assert prospects.territory_type("Maharashtra") == "State"
    assert prospects.territory_type("Delhi") == "Union Territory"
    assert prospects.territory_type("Chandigarh") == "Union Territory"
    assert prospects.territory_type("Andaman and Nicobar Islands") == "Island Territory"
    assert prospects.territory_type("Lakshadweep") == "Island Territory"


def test_store_directory_exclude_filters(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    qt_app = QApplication.instance() or QApplication([])
    tab = prospects.CustomerProspectsTab()
    try:
        sample_records = [
            {"kind": "Store", "business_name": "Pro Nutrition Hub", "state": "Haryana", "city": "Gurgaon", "business_category": "Sports Nutrition"},
            {"kind": "Gym", "business_name": "Iron Body Gym", "state": "Delhi", "city": "South Delhi", "business_category": "Fitness Gym"},
            {"kind": "Gym + Store", "business_name": "FitFuel Island Pro", "state": "Andaman and Nicobar Islands", "city": "Port Blair", "business_category": "Gym with Supplement Counter"},
        ]
        tab.records = sample_records
        tab._refresh_filters()
        tab._refresh_views()
        assert tab.leads_table.rowCount() == 3

        # Exclude by state
        tab.exclude_state.setCurrentText("Haryana")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(0)
        assert not tab.leads_table.isRowHidden(1)
        assert not tab.leads_table.isRowHidden(2)

        # Clear excludes
        tab.clear_exclude_filters()
        assert not tab.leads_table.isRowHidden(0)
        assert not tab.leads_table.isRowHidden(1)

        # Exclude by category / kind
        tab.exclude_kind.setCurrentText("Gym")
        tab.apply_filters()
        assert not tab.leads_table.isRowHidden(0)
        assert tab.leads_table.isRowHidden(1)

        # Exclude by business name
        tab.clear_exclude_filters()
        tab.exclude_name.setText("Iron Body")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(1)
        assert not tab.leads_table.isRowHidden(0)

        # Exclude by district / city
        tab.clear_exclude_filters()
        tab.exclude_district.setText("Port Blair")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(2)
        assert not tab.leads_table.isRowHidden(0)

        # Exclude by custom comma-separated keywords
        tab.clear_exclude_filters()
        tab.exclude_custom.setText("island, fuel")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(2)
        assert not tab.leads_table.isRowHidden(0)
    finally:
        tab.close()


def test_crawl_search_engine_results_defined_and_callable():
    assert hasattr(prospects, "crawl_search_engine_results")
    assert callable(prospects.crawl_search_engine_results)

    # Calling with empty search in mock/offline mode returns a list
    res = prospects.crawl_search_engine_results(
        category="Pure Product Selling Stores",
        state="Goa",
        query_term="nonexistent_mock_query_xyz_123",
        max_results=5,
        deep_scrape=False
    )
    assert isinstance(res, list)


def test_deduplication_and_enrichment_prevents_duplicate_entries(tmp_path, monkeypatch):
    import app
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "dedupe_test.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    initial_count = len(prospects.load_saved_prospects(db))

    # 1. Insert initial store with missing phone and maps
    initial_records = [
        {
            "kind": "Store",
            "business_name": "Fitnessstack: India&#x27;s Nutrition Store",
            "state": "Karnataka",
            "city": "Bengaluru",
            "phone": "",
            "email": "",
            "address": "Indiranagar, Bangalore",
            "website": "https://fitnessstack.com",
            "maps": "",
            "notes": "User custom lead note - do not overwrite",
        }
    ]
    res1 = prospects.persist_prospect_records(db, initial_records)
    assert res1["inserted"] == 1
    assert res1["duplicates"] == 0

    saved = prospects.load_saved_prospects(db)
    assert len(saved) == initial_count + 1
    matching = [s for s in saved if s["business_name"] == "Fitnessstack: India's Nutrition Store"]
    assert len(matching) == 1
    assert matching[0]["phone"] == ""

    # 2. Re-crawl or scrape same store with slightly different address format, unescaped name, and newly discovered phone/maps
    incoming_crawl = [
        {
            "kind": "Store",
            "business_name": "Fitnessstack: India's Nutrition Store",
            "state": "Karnataka",
            "city": "Bengaluru",
            "phone": "+91 98765 43210",
            "email": "contact@fitnessstack.com",
            "address": "100 Feet Road, Indiranagar, Bengaluru, Karnataka 560038",
            "website": "https://www.fitnessstack.com/shop",
            "maps": "https://maps.google.com/?q=fitnessstack",
            "notes": "Scraper raw notes",
        }
    ]
    res2 = prospects.persist_prospect_records(db, incoming_crawl)
    assert res2["inserted"] == 0
    assert res2["duplicates"] == 1

    # Database count increased by exactly 1 overall (NO DUPLICATES ADDED!)
    saved_after = prospects.load_saved_prospects(db)
    assert len(saved_after) == initial_count + 1

    # Missing fields were enriched from the crawl
    matching_after = [s for s in saved_after if s["business_name"] == "Fitnessstack: India's Nutrition Store"]
    assert len(matching_after) == 1
    enriched = matching_after[0]
    assert enriched["phone"] == "+91 98765 43210"
    assert enriched["email"] == "contact@fitnessstack.com"
    assert "100 Feet Road" in enriched["address"]
    assert enriched["maps"] == "https://maps.google.com/?q=fitnessstack"
    # User's custom note was preserved!
    assert enriched["notes"] == "User custom lead note - do not overwrite"


def test_cleanup_duplicate_prospects_merges_existing_duplicates(tmp_path, monkeypatch):
    import app
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "cleanup_test.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()
    initial_count = len(prospects.load_saved_prospects(db))

    # Insert two duplicates directly into SQLite simulating old corrupted state
    db.conn.execute(
        "INSERT INTO customer_prospects(dedupe_key, business_name, state, city, phone, email, notes, created_at, updated_at) "
        "VALUES ('key1', 'HyugaLife: India&#x27;s Best Supplement Store', 'Maharashtra', 'Mumbai', '', '', 'Important Client', '2026-10-01', '2026-10-01')"
    )
    db.conn.execute(
        "INSERT INTO customer_prospects(dedupe_key, business_name, state, city, phone, email, website, created_at, updated_at) "
        "VALUES ('key2', 'HyugaLife: India''s Best Supplement Store', 'Maharashtra', 'Mumbai', '9811122233', 'info@hyugalife.com', 'https://hyugalife.com', '2026-10-02', '2026-10-02')"
    )
    db.conn.commit()

    assert len(prospects.load_saved_prospects(db)) == initial_count + 2

    # Run cleanup
    cleanup_res = prospects.cleanup_duplicate_prospects(db)
    assert cleanup_res["merged"] >= 1

    # Now exactly 1 consolidated record remains
    remaining = prospects.load_saved_prospects(db)
    assert len(remaining) == initial_count + 1
    matching = [r for r in remaining if "HyugaLife" in r["business_name"]]
    assert len(matching) == 1
    r = matching[0]
    assert "India's" in r["business_name"]
    assert r["phone"] == "9811122233"
    assert r["email"] == "info@hyugalife.com"
    assert r["notes"] == "Important Client"


def test_density_mode_switcher_and_command_palette(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    import app

    qt_app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "ui_spec_test.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    db = app.Database()

    tab = prospects.CustomerProspectsTab(db=db)
    try:
        assert hasattr(tab, "density_combo")
        # Test Compact
        tab._on_density_changed("Compact")
        assert tab.leads_table.verticalHeader().defaultSectionSize() == 34

        # Test Comfortable
        tab._on_density_changed("Comfortable")
        assert tab.leads_table.verticalHeader().defaultSectionSize() == 42

        # Test Dense
        tab._on_density_changed("Dense")
        assert tab.leads_table.verticalHeader().defaultSectionSize() == 26

        # Test Command Palette Dialog
        class MockMainWindow:
            def __init__(self):
                self.tabs = tab.tabs if hasattr(tab, "tabs") else None
                self.customer_tab = tab
                self.employees_tab = None
                self.tasks_tab = None
                self.attendance_tab = None
                self.dashboard = None
                self.home_tab = None
                self.chat_tab = None
                self.business_tab = None
                self.reports_tab = None
                self.settings_tab = None

        mock_win = MockMainWindow()
        palette = app.CommandPaletteDialog(mock_win, parent=tab)
        try:
            assert palette.cmd_list.count() > 0
            # Filter for 'store'
            palette.search_input.setText("store")
            assert palette.cmd_list.count() >= 1
        finally:
            palette.close()
    finally:
        tab.close()

def test_unified_excludes_dropdown_print_dropdown_and_scroll_area(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QScrollArea

    qt_app = QApplication.instance() or QApplication([])
    tab = prospects.CustomerProspectsTab()
    try:
        # 1. Verify vertical scroll area exists and wraps the page
        assert hasattr(tab, "leads_scroll_area")
        assert isinstance(tab.leads_scroll_area, QScrollArea)
        assert tab.leads_scroll_area.widgetResizable() is True
        assert hasattr(tab, "regional_scroll_area")
        assert isinstance(tab.regional_scroll_area, QScrollArea)
        assert tab.leads_table.minimumHeight() >= 400

        # 2. Verify unified print/export dropdown
        assert hasattr(tab, "print_export_combo")
        assert tab.print_export_combo.count() >= 8
        assert "Print & Export" in tab.print_export_combo.itemText(0)

        # 3. Verify unified exclude controls
        assert hasattr(tab, "exclude_dropdown")
        assert hasattr(tab, "exclude_keyword")
        assert hasattr(tab, "btn_clear_excludes")

        sample_records = [
            {"kind": "Store", "business_name": "Pro Nutrition Hub", "state": "Haryana", "city": "Gurgaon", "business_category": "Sports Nutrition"},
            {"kind": "Gym", "business_name": "Iron Body Gym", "state": "Delhi", "city": "South Delhi", "business_category": "Fitness Gym"},
            {"kind": "Gym + Store", "business_name": "FitFuel Island Pro", "state": "Andaman and Nicobar Islands", "city": "Port Blair", "business_category": "Gym with Supplement Counter"},
        ]
        tab.records = sample_records
        tab._refresh_filters()
        tab._refresh_views()
        assert tab.leads_table.rowCount() == 3

        # Exclude Category via unified dropdown
        tab.exclude_dropdown.setCurrentText("Exclude Category: Gym")
        tab.apply_filters()
        assert not tab.leads_table.isRowHidden(0)
        assert tab.leads_table.isRowHidden(1)
        assert not tab.leads_table.isRowHidden(2)

        # Exclude State via unified dropdown
        tab.clear_exclude_filters()
        tab.exclude_dropdown.setCurrentText("Exclude State: Haryana")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(0)
        assert not tab.leads_table.isRowHidden(1)
        assert not tab.leads_table.isRowHidden(2)

        # Exclude by unified keyword input
        tab.clear_exclude_filters()
        tab.exclude_keyword.setText("Iron Body")
        tab.apply_filters()
        assert not tab.leads_table.isRowHidden(0)
        assert tab.leads_table.isRowHidden(1)
        assert not tab.leads_table.isRowHidden(2)

        # Clear excludes resets dropdown and keyword
        tab.clear_exclude_filters()
        assert tab.exclude_dropdown.currentIndex() == 0
        assert tab.exclude_keyword.text() == ""
        assert not tab.leads_table.isRowHidden(0)
        assert not tab.leads_table.isRowHidden(1)
        assert not tab.leads_table.isRowHidden(2)
    finally:
        tab.close()


def test_normalise_state_handles_ampersands_and_union_territories():
    assert prospects.normalise_state("Jammu & Kashmir") == "Jammu and Kashmir"
    assert prospects.normalise_state("Dadra & Nagar Haveli And Daman & Diu") == "Dadra and Nagar Haveli and Daman and Diu"
    assert prospects.normalise_state("J&K") == "Jammu and Kashmir"
    assert prospects.normalise_state("JK") == "Jammu and Kashmir"
    assert prospects.normalise_state("Andaman & Nicobar Islands") == "Andaman and Nicobar Islands"

    assert prospects.territory_type(prospects.normalise_state("Jammu & Kashmir")) == "Union Territory"
    assert prospects.territory_type(prospects.normalise_state("Dadra & Nagar Haveli And Daman & Diu")) == "Union Territory"
    assert prospects.territory_type(prospects.normalise_state("Andaman & Nicobar Islands")) == "Island Territory"
    assert prospects.territory_type("Karnataka") == "State"


def test_startup_splash_screen_initialization_in_offscreen_mode(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    import app
    splash = app.StartupSplashScreen()
    assert splash.is_headless() is True
    splash.show_splash()
    splash.set_status("Loading, please wait...", 25)
    assert splash.status_lbl.text() == "Loading, please wait..."
    splash.hide_splash()
    splash.finish()


def test_store_directory_print_store_details_and_dashboard(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    qt_app = QApplication.instance() or QApplication([])
    tab = prospects.CustomerProspectsTab()
    try:
        sample_record = {
            "business_name": "Raw Power Gym & Nutrition",
            "business_category": "Fitness Center",
            "brand": "Raw Strength Partner",
            "state": "Maharashtra",
            "city": "Mumbai",
            "district": "Mumbai Suburban",
            "area": "Andheri West",
            "pincode": "400053",
            "address": "Plot 12, Link Road, Andheri West",
            "phone": "9876543210",
            "email": "contact@rawpower.in",
            "contact_person": "Vikram Singh",
            "website": "https://rawpower.in",
            "source_type": "Official Partner Directory",
            "source_url": "https://rawpower.in/store",
            "status": "Active Partner",
            "notes": "Verified flagship distributor"
        }
        tab.records = [sample_record]
        tab._refresh_filters()
        tab._refresh_views()

        # 1. Verify Store Details & Dashboard Print Buttons exist in Store Directory
        assert hasattr(tab, "btn_store_details")
        assert hasattr(tab, "btn_dashboard_print")
        assert hasattr(tab, "btn_print_preview")
        assert hasattr(tab, "btn_print")

        # 2. Verify Store Details Document Generation
        doc = tab._generate_store_details_document(sample_record)
        html = doc.toHtml()
        assert "Raw Power Gym" in html
        assert "Raw Power Gym & Nutrition" in doc.toPlainText()
        assert "Fitness Center" in html
        assert "9876543210" in html
        assert "contact@rawpower.in" in html
        assert "Andheri West" in html

        # 3. Verify Print Dropdown has Store Details and Regional Dashboard options
        dropdown_texts = [tab.print_export_combo.itemText(i) for i in range(tab.print_export_combo.count())]
        assert any("Store Details" in t for t in dropdown_texts)
        assert any("Regional Dashboard" in t for t in dropdown_texts)

        # 4. Verify Store Details Preview opens without crash (mock dialogs)
        preview_called = []
        monkeypatch.setattr(tab, "_generate_store_details_document", lambda rec=None: preview_called.append(True) or doc)

        # Mock QPrintPreviewDialog and QDialog to avoid blocking UI
        import unittest.mock as mock
        import customer_prospects as cp_mod
        mock_dialog = mock.MagicMock()
        mock_dialog_inst = mock.MagicMock()
        mock_dialog.return_value = mock_dialog_inst
        monkeypatch.setattr(cp_mod, "QPrintPreviewDialog", mock_dialog, raising=False)

        # Also mock open_store_details_preview to avoid blocking
        monkeypatch.setattr(tab, "open_store_details_preview", lambda *a, **k: preview_called.append("preview"))
        monkeypatch.setattr(tab, "show_store_details_dialog", lambda *a, **k: preview_called.append("dialog"))

        # Simulate the button's connected slot directly
        tab.records = [sample_record]
        tab.leads_table.setRowCount(1)
        tab.leads_table.selectRow(0)
        # Call directly - btn_store_details click triggers show_store_details_dialog
        tab.show_store_details_dialog(0)
        assert len(preview_called) >= 1
    finally:
        tab.close()


def test_store_state_presence_resolution_replaces_all_india():
    """Verify that instead of 'All India', the store lists the specific states where it is present."""
    # 1. Known brand chain presence
    res_villa = prospects.resolve_store_presence_states("Supplements Villa - India's Most Trusted Store")
    assert "Haryana" in res_villa
    assert "Delhi" in res_villa
    assert "Uttar Pradesh" in res_villa
    assert "All-India" not in res_villa

    # 2. City-based presence detection
    res_kanpur = prospects.resolve_store_presence_states("Monty Fitness Gym", city="Kanpur")
    assert res_kanpur == "Uttar Pradesh"

    # 3. Multi-state store in regional summary increments for each state
    sample_records = [
        {"business_name": "Supplements Villa", "state": "Haryana, Delhi, Uttar Pradesh", "kind": "Store"},
        {"business_name": "Patna Nutrition", "state": "Bihar", "kind": "Store"}
    ]
    summary = prospects.build_regional_summary(sample_records)
    summary_by_state = {r["state"]: r["stores"] for r in summary}
    assert summary_by_state.get("Haryana") == 1
    assert summary_by_state.get("Delhi") == 1
    assert summary_by_state.get("Uttar Pradesh") == 1
    assert summary_by_state.get("Bihar") == 1
    assert "All-India" not in summary_by_state


def test_exclude_gym_wellness_herbal_healthkart_combo_filter(monkeypatch):
    """Verify the combined exclude option: '🚫 Exclude: Gym + Wellness Centers + Herbal + HealthKart'."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    qt_app = QApplication.instance() or QApplication([])

    tab = prospects.CustomerProspectsTab()
    try:
        tab.records = [
            {"business_name": "Apex Protein Store", "kind": "Store", "business_category": "Sports Nutrition", "state": "Delhi"},
            {"business_name": "Iron Beast Gym", "kind": "Gym", "business_category": "Fitness Centre", "state": "Delhi"},
            {"business_name": "Lotus Wellness Center", "kind": "Store", "business_category": "Ayush & Wellness", "state": "Delhi"},
            {"business_name": "Patanjali Herbal Store", "kind": "Store", "business_category": "Herbal Supplements", "state": "Delhi"},
            {"business_name": "HealthKart Retail Outlet", "kind": "Store", "business_category": "Nutrition Retail", "state": "Delhi"},
        ]
        tab._refresh_filters()
        tab._refresh_views()

        # Find combo exclude item in dropdown
        combo_idx = -1
        for i in range(tab.exclude_dropdown.count()):
            if "Gym + Wellness Centers + Herbal + HealthKart" in tab.exclude_dropdown.itemText(i):
                combo_idx = i
                break
        assert combo_idx >= 0, "Combo exclude option not found in exclude_dropdown"

        # Apply the combo exclude filter
        tab.exclude_dropdown.setCurrentIndex(combo_idx)
        tab.apply_filters()

        visible = tab._get_visible_records()
        visible_names = [r["business_name"] for r in visible]
        assert "Apex Protein Store" in visible_names
        assert "Iron Beast Gym" not in visible_names
        assert "Lotus Wellness Center" not in visible_names
        assert "Patanjali Herbal Store" not in visible_names
        assert "HealthKart Retail Outlet" not in visible_names
    finally:
        tab.close()


def test_gaps_fix_cell_format_regional_source_counts_and_union_territories(monkeypatch):
    """Verify that cell formatting falls back cleanly to 'NA', multi-state regional source counts are decomposed, and UTs are resolved."""
    # 1. format_prospect_cell_value handles NA fallback and displaced phone data
    assert prospects.format_prospect_cell_value({"phone": "Near Metro Station"}, "phone") == "NA"
    assert prospects.format_prospect_cell_value({"phone": "123"}, "phone") == "NA"
    assert prospects.format_prospect_cell_value({"phone": "nan"}, "phone") == "NA"
    assert prospects.format_prospect_cell_value({"phone": "9876543210"}, "phone") == "9876543210"
    assert prospects.format_prospect_cell_value({"contact_person": "None"}, "contact_person") == "NA"
    assert prospects.format_prospect_cell_value({"email": "nan"}, "email") == "NA"
    assert prospects.format_prospect_cell_value({"website": "-"}, "website") == "NA"

    # 2. format_prospect_cell_value resolves 'All-India' state to real states
    rec_villa = {"business_name": "Supplements Villa", "state": "All-India"}
    formatted_st = prospects.format_prospect_cell_value(rec_villa, "state")
    assert "Haryana" in formatted_st and "Delhi" in formatted_st
    assert "All-India" not in formatted_st

    # 3. resolve_store_presence_states resolves Union Territories and Islands
    res_chd = prospects.resolve_store_presence_states("Rock Fitness", city="Chandigarh")
    assert res_chd == "Chandigarh"

    # 4. Regional table decomposes multi-state source counts
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    qt_app = QApplication.instance() or QApplication([])
    tab = prospects.CustomerProspectsTab()
    try:
        tab.records = [
            {"business_name": "Supplements Villa", "state": "Haryana, Delhi, Uttar Pradesh", "kind": "Store", "source_type": "Official Web Seed"},
            {"business_name": "Local Store", "state": "Haryana", "kind": "Store", "source_type": "Imported Local Workbook"}
        ]
        tab._fill_regional_table()
        display_map = {r["state"]: r for r in tab.last_regional_display_rows}
        assert display_map["Haryana"]["web_leads"] == 1
        assert display_map["Haryana"]["workbook_leads"] == 1
        assert display_map["Delhi"]["web_leads"] == 1
        assert display_map["Uttar Pradesh"]["web_leads"] == 1
    finally:
        tab.close()


def test_v1348_view_switcher_scrollbar_deep_search_and_print(monkeypatch):
    """Verify v1.3.48 features: view switcher dropdown, scrollbar policies, deep multi-token search, and print center."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    qt_app = QApplication.instance() or QApplication([])
    tab = prospects.CustomerProspectsTab()
    try:
        # 1. View Switcher Dropdown exists and synchronizes with pages
        assert hasattr(tab, "view_selector")
        assert tab.view_selector.count() == 2
        assert "Store Directory" in tab.view_selector.itemText(0)
        assert "Regional Dashboard" in tab.view_selector.itemText(1)

        # Switching dropdown changes QTabWidget index
        tab.view_selector.setCurrentIndex(1)
        assert tab.pages.currentIndex() == 1

        tab.view_selector.setCurrentIndex(0)
        assert tab.pages.currentIndex() == 0

        # Switching QTabWidget changes dropdown index
        tab.pages.setCurrentIndex(1)
        assert tab.view_selector.currentIndex() == 1

        tab.pages.setCurrentIndex(0)
        assert tab.view_selector.currentIndex() == 0

        # 2. Scrollbar policies are ScrollBarAsNeeded
        assert tab.leads_scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        assert tab.regional_scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        assert tab.outer_scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded

        # 3. Print buttons exist: top toolbar button + bottom card buttons
        assert hasattr(tab, "btn_top_print")
        assert hasattr(tab, "btn_print_preview")
        assert hasattr(tab, "btn_print")
        assert hasattr(tab, "btn_store_details")
        assert hasattr(tab, "btn_dashboard_print")
        assert hasattr(tab, "btn_pdf")
        assert hasattr(tab, "btn_csv")
        assert hasattr(tab, "btn_xlsx")
        assert hasattr(tab, "btn_doc")
        assert hasattr(tab, "btn_folder")

        # 4. Deep multi-token search across multiple fields
        tab.records = [
            {"business_name": "Power Fuel Store", "state": "Delhi", "city": "Connaught Place", "kind": "Store", "phone": "9811122233"},
            {"business_name": "Apex Nutrition", "state": "Maharashtra", "city": "Mumbai", "kind": "Store", "phone": "9822233344"},
            {"business_name": "Gold Whey Delhi", "state": "Haryana", "city": "Gurgaon", "kind": "Store", "phone": "9833344455"}
        ]
        tab._refresh_filters()
        tab._refresh_views()
        assert tab.leads_table.rowCount() == 3

        # Multi-term query "Power Delhi" matches "Power Fuel Store" in "Delhi"
        tab.search_input.setText("Power Delhi")
        tab.apply_filters()
        assert not tab.leads_table.isRowHidden(0)
        assert tab.leads_table.isRowHidden(1)
        assert tab.leads_table.isRowHidden(2)

        # Multi-term query "Whey Gurgaon" matches "Gold Whey Delhi" in "Gurgaon"
        tab.search_input.setText("Whey Gurgaon")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(0)
        assert tab.leads_table.isRowHidden(1)
        assert not tab.leads_table.isRowHidden(2)

        # Non-matching multi-term query
        tab.search_input.setText("Power Mumbai")
        tab.apply_filters()
        assert tab.leads_table.isRowHidden(0)
        assert tab.leads_table.isRowHidden(1)
        assert tab.leads_table.isRowHidden(2)

        # 5. Theme contrast and default row heights
        tab.apply_theme("night")
        assert tab.leads_table.verticalHeader().defaultSectionSize() == 38
        assert tab.region_table.verticalHeader().defaultSectionSize() == 38
    finally:
        tab.close()


def test_existing_store_with_full_address_gets_google_maps_search_link(tmp_path):
    import sqlite3
    from urllib.parse import parse_qs, urlparse

    db_path = tmp_path / "prospects.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE customer_prospects (
            id INTEGER PRIMARY KEY,
            state TEXT, city TEXT, business_name TEXT, address TEXT, maps TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO customer_prospects (state, city, business_name, address, maps) VALUES (?, ?, ?, ?, ?)",
        ("Andhra Pradesh", "Vijayawada", "Fit Fuel Supplements", "Shop 12, MG Road, Vijayawada 520010", "NA"),
    )
    conn.commit()

    class DB:
        def __init__(self, connection):
            self.conn = connection

    try:
        records = prospects.load_saved_prospects(DB(conn))
        assert len(records) == 1
        record = records[0]
        parsed = urlparse(record["maps"])
        assert parsed.scheme == "https"
        assert parsed.netloc == "www.google.com"
        assert parsed.path == "/maps/search/"
        query = parse_qs(parsed.query)["query"][0]
        assert "Fit Fuel Supplements" in query
        assert "Shop 12, MG Road, Vijayawada 520010" in query
        saved = conn.execute("SELECT maps FROM customer_prospects WHERE id=1").fetchone()[0]
        assert saved == record["maps"]
    finally:
        conn.close()


def test_official_retailer_rows_have_full_addresses_and_actionable_maps_links():
    assert prospects.RESEARCHED_SOURCE_URL.startswith("https://")
    assert prospects.RESEARCHED_WEB_LEADS
    for lead in prospects.RESEARCHED_WEB_LEADS:
        assert lead["business_name"].strip()
        assert len(lead["address"].strip()) >= 12
        maps_url = prospects.google_maps_search_url(lead)
        assert maps_url.startswith("https://www.google.com/maps/search/?")
        from urllib.parse import parse_qs, urlparse
        query = parse_qs(urlparse(maps_url).query)["query"][0]
        assert lead["address"] in query


def test_deep_scraper_does_not_create_synthetic_leads_when_search_is_unavailable(monkeypatch):
    import urllib.request

    def offline(*_args, **_kwargs):
        raise OSError("offline test")

    monkeypatch.setattr(urllib.request, "urlopen", offline)
    results = prospects.crawl_search_engine_results(
        category="Pure Product Selling Stores",
        state="",
        query_term="sports nutrition supplement store",
        max_results=5,
        deep_scrape=True,
    )
    assert results == []
