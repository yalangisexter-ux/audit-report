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
