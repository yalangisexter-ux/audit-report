import csv
from datetime import date, datetime
from docx import Document
import reportlab.platypus

import app


def _make_window(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    qt_app = app.QApplication.instance() or app.QApplication([])
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "target-test.db"))
    monkeypatch.setattr(app, "BACKUP_DIR", str(tmp_path / "backups"))
    database = app.Database()
    window = app.MainWindow(database, {"username": "Target QA", "role": "Admin"})
    return qt_app, database, window


def test_employee_targets_crud_and_report_formatting(tmp_path, monkeypatch):
    qt_app, database, window = _make_window(tmp_path, monkeypatch)
    try:
        today = date.today().isoformat()
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = database.conn.cursor()
        cur.execute(
            """INSERT INTO employees (name, employee_code, department, designation, phone, email, joining_date, active, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("Taruna", "RS-101", "Fitness", "Coach", "9999999999", "taruna@example.com", today, 1, "", now_ts)
        )
        database.conn.commit()
        emp_id = cur.lastrowid

        # 1. Verify default unset target returns NA
        preview_default = window.report_preview_text(today, emp_id)
        assert "Name : Taruna" in preview_default
        assert "• Employee ID: RS-101 | Department: Fitness | Role: Coach" in preview_default
        assert "• Target: NA" in preview_default
        assert "Target status : NA" in preview_default

        # 2. Set custom target and status via db
        database.set_employee_target(emp_id, today, "Complete 5 audits", "In Progress")
        tgt_data = database.get_employee_target(emp_id, today)
        assert tgt_data["target"] == "Complete 5 audits"
        assert tgt_data["target_status"] == "In Progress"

        # 3. Verify text preview reflects custom target and status
        preview_updated = window.report_preview_text(today, emp_id)
        assert "• Employee ID: RS-101 | Department: Fitness | Role: Coach" in preview_updated
        assert "• Target: Complete 5 audits" in preview_updated
        assert "Target status : In Progress" in preview_updated

        # 4. Verify Word (DOCX) export formatting
        docx_path = tmp_path / "target_report.docx"
        window.make_docx(docx_path, today, emp_id, "Audit / EOD", window.selected_eod_options())
        doc = Document(docx_path)
        docx_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Name : Taruna" in docx_text
        assert "Target: Complete 5 audits" in docx_text
        assert "Target status : In Progress" in docx_text

        # 5. Verify CSV export formatting
        csv_path = tmp_path / "target_report.csv"
        window.export_report_csv(csv_path, today, emp_id, "Audit / EOD", window.selected_eod_options())
        with open(csv_path, encoding="utf-8-sig") as f:
            csv_rows = list(csv.reader(f))
        headers = csv_rows[0]
        assert "Target" in headers
        assert "Target status" in headers
        data_rows = csv_rows[1:]
        assert any("Complete 5 audits" in row and "In Progress" in row for row in data_rows)

        # 6. Verify PDF export formatting
        captured_story = []
        class CaptureDoc:
            def __init__(self, *args, **kwargs): pass
            def build(self, story, **kwargs): captured_story.extend(story)
        monkeypatch.setattr(reportlab.platypus, "SimpleDocTemplate", CaptureDoc)
        pdf_path = tmp_path / "target_report.pdf"
        window.make_pdf(pdf_path, today, emp_id, "Audit / EOD", window.selected_eod_options())
        pdf_text = " ".join(getattr(f, "text", "") for f in captured_story if hasattr(f, "text"))
        assert "Target: Complete 5 audits" in pdf_text
        assert "Target status : In Progress" in pdf_text

        # 7. Verify Checkbox toggling in Print Center (disabling target and target status)
        window.eod_checks["target"].setChecked(False)
        window.eod_checks["target_status"].setChecked(False)
        opts_unchecked = window.selected_eod_options()
        assert opts_unchecked["target"] is False
        assert opts_unchecked["target_status"] is False

        preview_unchecked = window.report_preview_text(today, emp_id)
        assert "Target: Complete 5 audits" not in preview_unchecked
        assert "Target status :" not in preview_unchecked

        csv_unchecked_path = tmp_path / "target_unchecked.csv"
        window.export_report_csv(csv_unchecked_path, today, emp_id, "Audit / EOD", opts_unchecked)
        with open(csv_unchecked_path, encoding="utf-8-sig") as f:
            csv_un_headers = list(csv.reader(f))[0]
        assert "Target" not in csv_un_headers
        assert "Target status" not in csv_un_headers

        # 8. Verify Home Update Banner and Neon Attendance Gauge
        assert hasattr(window, "home_update_banner")
        assert window.home_update_banner.isHidden()
        window.show_update_alert("1.2.99")
        assert not window.home_update_banner.isHidden()
        assert "1.2.99" in window.home_update_text.text()

        assert hasattr(window, "neon_attendance_gauge")
        window.neon_attendance_gauge.set_percent(85, 17, 20)
        assert window.neon_attendance_gauge.percent == 85
        assert window.neon_attendance_gauge.present == 17

        # 9. Verify Task Manager toolbar target inputs are removed
        assert not hasattr(window, "employee_target_input")
        assert not hasattr(window, "save_target_btn")

        # 10. Verify TaskDialog contains Target and Target status inputs and 'Partially completed' status
        assert ("Partially completed", "Partially completed") in app.TaskDialog.STATUSES
        assert app.is_known_task_status("Partially completed")
        assert not app.is_explicitly_completed_task_status("Partially completed")

        dialog = app.TaskDialog(database, window, employee_id=emp_id, task_date=today)
        assert hasattr(dialog, "target_input")
        assert hasattr(dialog, "target_status_input")
        assert dialog.target_input.text() == "Complete 5 audits"
        assert dialog.target_status_input.text() == "In Progress"

        # Update target in dialog and accept
        dialog.target_input.setText("Complete 10 audits")
        dialog.target_status_input.setText("5/10 Done")
        dialog.accept()

        updated_target = database.get_employee_target(emp_id, today)
        assert updated_target["target"] == "Complete 10 audits"
        assert updated_target["target_status"] == "5/10 Done"
        dialog.close()
    finally:
        window.close()
        database.conn.close()
        qt_app.processEvents()
