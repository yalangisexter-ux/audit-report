import csv
from datetime import date, datetime

import app


def _make_window(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = app.QApplication.instance() or app.QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "ui-print.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    database = app.Database()
    window = app.MainWindow(database, {"username": "Print QA", "role": "Admin"})
    return qt_app, database, window


def _insert_business_data(database):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    database.conn.execute(
        """INSERT INTO bt_products(name,sku,category,brand,base_unit,opening_stock,
           received_qty,reserved_qty,reorder_level,selling_price,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        ("QA Protein Bar", "QA-PB-1", "Nutrition", "Raw Strength", "PCS", 10, 5, 1, 4, 89.5, timestamp),
    )
    database.conn.execute(
        """INSERT INTO bt_services(name,category,description,training_mode,service_unit,
           session_duration,num_sessions,plan_validity,standard_price,active,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        ("QA Calisthenics Plan", "Training", "Four-week starter plan", "Hybrid", "Session", 45, 12, 28, 2400, 1, timestamp),
    )
    database.conn.commit()


def test_product_and_service_print_checkboxes_filter_all_export_formats(tmp_path, monkeypatch):
    from docx import Document
    import reportlab.platypus

    qt_app, database, window = _make_window(tmp_path, monkeypatch)
    try:
        _insert_business_data(database)
        today = date.today().isoformat()
        options = window.selected_eod_options()
        assert options["business_products"] is False
        assert options["business_services"] is False
        assert not window.business_data_group.isHidden()

        window.business_report_checks["business_products"].setChecked(True)
        window.business_report_checks["business_services"].setChecked(True)
        options = window.selected_eod_options()
        assert options["business_products"] is True
        assert options["business_services"] is True

        docx_path = tmp_path / "with-business-data.docx"
        csv_path = tmp_path / "with-business-data.csv"
        pdf_path = tmp_path / "with-business-data.pdf"
        window.make_docx(docx_path, today, report_type="Employee Details", eod_options=options)
        window.export_report_csv(csv_path, today, report_type="Employee Details", eod_options=options)
        window.make_pdf(pdf_path, today, report_type="Employee Details", eod_options=options)

        word = Document(docx_path)
        word_text = "\n".join(
            [paragraph.text for paragraph in word.paragraphs]
            + [cell.text for table in word.tables for row in table.rows for cell in row.cells]
        )
        assert "QA Protein Bar" in word_text
        assert "QA Calisthenics Plan" in word_text
        assert "14" in word_text  # available stock: 10 + 5 - 1

        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            csv_text = "\n".join(",".join(row) for row in csv.reader(stream))
        assert "QA Protein Bar" in csv_text
        assert "QA Calisthenics Plan" in csv_text
        assert pdf_path.is_file() and pdf_path.stat().st_size > 1000

        captured = []

        class CaptureDocument:
            def __init__(self, *args, **kwargs):
                pass

            def build(self, story, **kwargs):
                captured.extend(story)

        monkeypatch.setattr(reportlab.platypus, "SimpleDocTemplate", CaptureDocument)
        window.make_pdf(tmp_path / "captured.pdf", today, report_type="Employee Details", eod_options=options)
        pdf_story_text = "\n".join(
            flowable.getPlainText() for flowable in captured if hasattr(flowable, "getPlainText")
        )
        assert "QA Protein Bar" in pdf_story_text
        assert "QA Calisthenics Plan" in pdf_story_text

        window.business_report_checks["business_products"].setChecked(False)
        window.preview_report()
        assert "QA Protein Bar" not in window.report_summary.toPlainText()
        assert "QA Calisthenics Plan" in window.report_summary.toPlainText()
        service_only = tmp_path / "service-only.csv"
        window.export_report_csv(service_only, today, report_type="Employee Details", eod_options=window.selected_eod_options())
        with service_only.open(encoding="utf-8-sig", newline="") as stream:
            service_csv = "\n".join(",".join(row) for row in csv.reader(stream))
        assert "QA Calisthenics Plan" in service_csv
        assert "QA Protein Bar" not in service_csv
    finally:
        window.close()
        database.conn.close()
        qt_app.processEvents()


def test_responsive_dashboard_and_tooltip_use_visible_high_contrast_layout(tmp_path, monkeypatch):
    qt_app, database, window = _make_window(tmp_path, monkeypatch)
    try:
        window.resize(1100, 760)
        window._apply_responsive_layout()
        qt_app.processEvents()

        assert window._kpi_column_count in (3, 4)
        assert window._dashboard_column_count in (1, 2)
        assert window.kpis.count() == 5
        assert window.dashboard_grid.count() == 5
        assert window.header_clock_frame.width() == 254
        assert window.att_table.horizontalHeader().stretchLastSection()
        positions = [window.kpis.getItemPosition(index) for index in range(window.kpis.count())]
        assert len({(row, column) for row, column, _row_span, _column_span in positions}) == 5

        tooltip = app.ensure_accessible_tooltip_controller()
        assert tooltip is not None
        style = tooltip.popup.styleSheet()
        assert "background-color: #FFFFFF" in style
        assert "color: #111827" in style
        assert "border: 2px solid #6D28D9" in style
        assert window.brand_logo.pixmap().size() == app.QSize(68, 68)
    finally:
        window.close()
        database.conn.close()
        qt_app.processEvents()


def test_add_task_preserves_selected_employee_and_task_date(tmp_path, monkeypatch):
    qt_app, database, window = _make_window(tmp_path, monkeypatch)
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        employee_ids = {}
        for name in ("Gopi", "Sai Teja"):
            cursor = database.conn.execute(
                "INSERT INTO employees(name,joining_date,active,created_at) VALUES(?,?,?,?)",
                (name, "", 1, timestamp),
            )
            employee_ids[name] = cursor.lastrowid
        database.conn.commit()
        window.refresh_task_filter()
        window.task_filter.setCurrentIndex(window.task_filter.findData(employee_ids["Sai Teja"]))
        selected_date = app.QDate(2026, 10, 8)
        window.task_date.setDate(selected_date)

        captured = {}
        base_dialog = app.TaskDialog

        class InspectTaskDialog(base_dialog):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                captured["employee_id"] = self.employee.currentData()
                captured["dialog"] = self

            def exec(self):
                return app.QDialog.DialogCode.Rejected

        monkeypatch.setattr(app, "TaskDialog", InspectTaskDialog)
        window.add_task()

        assert captured["employee_id"] == employee_ids["Sai Teja"]
        assert captured["dialog"].date.date().toString("yyyy-MM-dd") == "2026-10-08"
    finally:
        window.close()
        database.conn.close()
        qt_app.processEvents()
