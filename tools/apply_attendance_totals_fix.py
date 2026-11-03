#!/usr/bin/env python3
from pathlib import Path
app = Path("app.py")
text = app.read_text(encoding="utf-8")
old = """        if status in ("Absent", "Leave"):
            self.db.conn.execute("UPDATE attendance SET attendance_status=?,check_in='',check_out='',updated_at=? WHERE employee_id=? AND work_date=?",(status,now_text(),eid,d))
            if not self.db.conn.execute("SELECT 1 FROM attendance WHERE employee_id=? AND work_date=?",(eid,d)).fetchone():
                self.db.upsert_attendance(eid,d,status=status)
        else:
            self.db.upsert_attendance(eid,d,status=status)
"""
new = """        # Always persist through upsert_attendance so INSERT/UPDATE is committed.
        status = str(status or "").strip()
        if status in ("Absent", "Leave", "Unmarked"):
            self.db.upsert_attendance(eid, d, check_in="", check_out="", status=status)
        else:
            self.db.upsert_attendance(eid, d, status=status)
"""
if "Always persist through upsert_attendance" in text:
    print("already patched status")
elif old not in text:
    raise SystemExit("status block missing")
else:
    text = text.replace(old, new, 1)
    print("patched status")
old_c = """            present = sum(
                1 for row in monthly_rows
                if is_present_attendance_status(row["attendance_status"])
                or (row["attendance_status"] == "Unmarked" and row["check_in"])
            )
            absent = sum(1 for row in monthly_rows if row["attendance_status"] == "Absent")
            leave = sum(1 for row in monthly_rows if row["attendance_status"] == "Leave")
"""
new_c = """            present = sum(
                1 for row in monthly_rows
                if is_present_attendance_status(row["attendance_status"])
                or (
                    str(row["attendance_status"] or "").strip().casefold() in {"unmarked", ""}
                    and str(row["check_in"] or "").strip()
                )
            )
            absent = sum(
                1 for row in monthly_rows
                if str(row["attendance_status"] or "").strip().casefold() == "absent"
            )
            leave = sum(
                1 for row in monthly_rows
                if str(row["attendance_status"] or "").strip().casefold() == "leave"
            )
"""
if 'strip().casefold() == "absent"' in text:
    print("already patched counts")
elif old_c not in text:
    raise SystemExit("count block missing")
else:
    text = text.replace(old_c, new_c, 1)
    print("patched counts")
app.write_text(text, encoding="utf-8")
print("app ok")
