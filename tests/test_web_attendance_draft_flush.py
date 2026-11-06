"""Regression tests for web attendance draft persistence during navigation."""
from pathlib import Path


def _web_source():
    return (
        Path(__file__).resolve().parents[1] / "frontend" / "src" / "App.jsx"
    ).read_text(encoding="utf-8")


def _const_block(source: str, marker: str) -> str:
    start = source.index(marker)
    end = source.find("\n  const ", start + len(marker))
    return source[start:] if end < 0 else source[start:end]


def test_date_navigation_saves_pending_rows_before_loading_the_next_date():
    source = _web_source()
    flush = _const_block(source, "const flushAttendanceDrafts=")

    assert "Object.entries(attendanceDrafts)" in flush
    assert "rowsById.get(String(employeeId))" in flush
    assert "await apiFetch('/attendance/mark'" in flush
    assert "work_date:workDate" in flush

    marker = "value={selectedAttendanceDate} disabled={attendanceBusy} onChange={async e=>{"
    start = source.index(marker)
    end = source.index("}/></label>", start)
    date_handler = source[start:end]
    assert date_handler.index("await flushAttendanceDrafts(selectedAttendanceDate)") < date_handler.index(
        "apiFetch('/attendance?work_date='+encodeURIComponent(selectedDate))"
    )
    assert date_handler.index("setAttendanceDrafts({})") > date_handler.index(
        "apiFetch('/attendance?work_date='+encodeURIComponent(selectedDate))"
    )
    assert "finally{setAttendanceBusy(false)}" in date_handler


def test_saving_one_attendance_row_preserves_other_pending_rows():
    source = _web_source()
    save_one = _const_block(source, "const saveAttendanceDraft=")

    assert "await apiFetch('/attendance/mark'" in save_one
    assert "delete next[r.employee_id]" in save_one
    assert "setAttendanceDrafts({})" not in save_one
    assert "post('/attendance/mark'" not in save_one


def test_attendance_screen_exposes_save_all_and_disables_concurrent_date_changes():
    source = _web_source()

    assert "const saveAllAttendanceDrafts=async()=>{" in source
    assert "onClick={saveAllAttendanceDrafts}" in source
    assert "Save all {Object.keys(attendanceDrafts).length} pending" in source
    assert "disabled={attendanceBusy}" in source
