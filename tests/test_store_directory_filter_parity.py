import sqlite3
from pathlib import Path

from web_parity_routes import _store_directory_rows


def _directory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE customer_prospects (
            id INTEGER PRIMARY KEY,
            business_name TEXT, business_category TEXT, kind TEXT, state TEXT,
            city TEXT, area TEXT, contact_person TEXT, phone TEXT, email TEXT,
            address TEXT, website TEXT, maps TEXT, followup_date TEXT, call_time TEXT,
            connection TEXT, verified TEXT, response TEXT, notes TEXT, source_name TEXT,
            source_url TEXT, source_type TEXT, source_checked_at TEXT, source_sheet TEXT,
            source_status TEXT
        )
        """
    )
    rows = [
        (1, "Peak Supplement Store", "Sports Nutrition", "Store", "Andhra Pradesh",
         "Visakhapatnam", "MVP Colony", "", "9876543210", "peak@example.com",
         "Door 1, Main Road, 530001", "https://peak.example", "", "", "", "", "Yes",
         "", "safe", "", "", "Workbook", "", "", "Needs direct confirmation"),
        (2, "City Gym", "Fitness Center", "Gym", "Andhra Pradesh",
         "Vijayawada", "Benz Circle", "", "", "N/A", "", "NA", "", "", "", "", "No",
         "", "gym wellness", "", "", "Web", "", "", "Needs direct confirmation"),
        (3, "HealthKart Herbal", "Herbal Nutrition", "Store", "Telangana",
         "Hyderabad", "Gachibowli", "", "None", "null", "", "https://healthkart.example",
         "", "", "", "", "No", "", "herbal healthkart", "", "", "Web", "", "", "verified"),
        (4, "Local Retail", "Retail", "Store", "Andhra Pradesh",
         "Kakinada", "Main Road", "", "9999999999", "", "Address", "-", "", "", "",
         "", "Yes", "", "safe", "", "", "Workbook", "", "", "Needs direct confirmation"),
    ]
    conn.executemany(
        "INSERT INTO customer_prospects VALUES (" + ",".join("?" for _ in range(25)) + ")",
        rows,
    )
    return conn


def test_store_directory_contact_website_and_verification_filters_match_desktop():
    conn = _directory_db()
    try:
        assert {row["id"] for row in _store_directory_rows(conn, contact="has")} == {1, 4}
        assert {row["id"] for row in _store_directory_rows(conn, contact="missing")} == {2, 3}
        assert {row["id"] for row in _store_directory_rows(conn, exclude="missing_contact")} == {1, 4}
        assert {row["id"] for row in _store_directory_rows(conn, website="has")} == {1, 3}
        assert {row["id"] for row in _store_directory_rows(conn, exclude="missing_website")} == {1, 3}
        assert {row["id"] for row in _store_directory_rows(conn, verification="pending")} == {2, 3}
        assert {row["id"] for row in _store_directory_rows(conn, exclude="unverified")} == {1, 4}
    finally:
        conn.close()


def test_store_directory_exclusion_filters_match_desktop():
    conn = _directory_db()
    try:
        assert {row["id"] for row in _store_directory_rows(
            conn, exclude="gym_wellness_herbal_healthkart"
        )} == {1, 4}
        assert {row["id"] for row in _store_directory_rows(conn, exclude_kind="Gym")} == {1, 3, 4}
        assert {row["id"] for row in _store_directory_rows(conn, exclude_state="Andhra Pradesh")} == {3}
        assert {row["id"] for row in _store_directory_rows(conn, exclude_name="healthkart")} == {1, 2, 4}
        assert {row["id"] for row in _store_directory_rows(conn, exclude_district="vijayawada")} == {1, 3, 4}
        assert {row["id"] for row in _store_directory_rows(
            conn, exclude_keywords="herbal,healthkart"
        )} == {1, 2, 4}
    finally:
        conn.close()


def test_store_directory_search_requires_every_term_and_state_filter_supports_multiple_regions():
    conn = _directory_db()
    try:
        assert {row["id"] for row in _store_directory_rows(conn, query="sports nutrition")} == {1}
        assert {row["id"] for row in _store_directory_rows(
            conn, state="Andhra Pradesh"
        )} == {1, 2, 4}
    finally:
        conn.close()



def test_store_directory_kind_filters_match_desktop_strict_pure_product_rules():
    conn = _directory_db()
    try:
        extra_rows = [
            (5, "Peak Nutrition Retailer", "Sports nutrition / supplement retailer", "Store",
             "Andhra Pradesh", "Rajahmundry", "Main Road", "", "9000000000", "peak@example.com",
             "Shop 4, Main Road, Rajahmundry, Andhra Pradesh 533101", "https://peak.example",
             "https://www.google.com/maps/place/Peak", "", "", "", "Yes", "", "", "", "",
             "Web", "", "", "verified"),
            (6, "Whey Shop", "Whey protein retailer", "Store", "Andhra Pradesh", "Kakinada",
             "Main Road", "", "", "", "Main Road", "https://whey.example",
             "https://maps.google.com/?q=Whey", "", "", "", "No", "", "", "", "", "Web", "", "",
             "verified"),
            (7, "Town Nutrition", "Sports nutrition retailer", "Store", "Telangana", "Warangal",
             "Main Road", "", "", "", "Shop 2, Main Road, Warangal, Telangana 506001",
             "https://town.example", "https://maps.google.com/?q=Town", "", "", "", "No", "",
             "pharmacy", "", "", "Web", "", "", "verified"),
            (8, "Hybrid Fitness Store", "Gym sports nutrition counter", "Gym + Store",
             "Andhra Pradesh", "Vijayawada", "Main Road", "", "", "",
             "Shop 8, Main Road, Vijayawada, Andhra Pradesh 520010", "https://hybrid.example",
             "https://www.google.com/maps/place/Hybrid", "", "", "", "Yes", "", "", "", "",
             "Web", "", "", "verified"),
            (9, "Supplement Outlet", "Protein retailer", "Supplement Store", "Kerala", "Kochi",
             "Market Road", "", "", "", "Unit 3, Market Road, Kochi, Kerala 682001",
             "https://outlet.example", "https://maps.app.goo.gl/outlet", "", "", "", "Yes", "",
             "", "", "", "Web", "", "", "verified"),
        ]
        conn.executemany(
            "INSERT INTO customer_prospects VALUES (" + ",".join("?" for _ in range(25)) + ")",
            extra_rows,
        )
        assert {row["id"] for row in _store_directory_rows(
            conn, kind="Pure Product Selling Stores"
        )} == {5, 9}
        assert {row["id"] for row in _store_directory_rows(conn, kind="Store")} == {
            1, 3, 4, 5, 6, 7, 9
        }
        assert {row["id"] for row in _store_directory_rows(
            conn, kind="Gyms which sell products also"
        )} == {8}
    finally:
        conn.close()


def test_store_directory_web_defaults_to_desktop_pure_product_view_and_clear_exclusions():
    app_source = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.jsx").read_text(
        encoding="utf-8"
    )
    assert "const [prospectKindFilter,setProspectKindFilter]=useState('pure product selling stores')" in app_source
    assert "clearStoreExclusions" in app_source
    assert "Clear exclusions" in app_source
