"""Regression tests for Windows-equivalent attendance toolbar actions in the web app."""
from pathlib import Path


def _source(name):
    return (Path(__file__).resolve().parents[1] / name).read_text(encoding="utf-8")


def test_web_attendance_exposes_the_windows_toolbar_actions():
    frontend = _source("frontend/src/App.jsx")
    desktop = _source("app.py")

    for label in ("Check In", "Check Out", "Edit Times", "Remarks"):
        assert ">%s</button>" % label in frontend
        assert '"%s"' % label in desktop
    for status in ("Present", "Absent", "Leave"):
        assert "runAttendanceStatusAction('%s')" % status in frontend
        assert '"● %s"' % status in desktop


def test_toolbar_actions_flush_pending_drafts_before_saving_the_selected_date():
    frontend = _source("frontend/src/App.jsx")
    start = frontend.index("const saveAttendanceToolbarUpdate=")
    end = frontend.index("const runAttendanceStatusAction=", start)
    action = frontend[start:end]

    assert action.index("await flushAttendanceDrafts(selectedAttendanceDate)") < action.index("await apiFetch('/attendance/mark'")
    assert "work_date:selectedAttendanceDate" in action
    assert action.index("await refreshAttendanceDate(selectedAttendanceDate)") < action.index("setAttendanceDrafts({})")


def test_toolbar_requires_one_employee_or_a_single_employee_filter():
    frontend = _source("frontend/src/App.jsx")
    start = frontend.index("const resolveAttendanceToolbarTarget=")
    end = frontend.index("const attendanceIsPresentStatus=", start)
    target = frontend[start:end]

    assert "selectedAttendanceIds.length>1" in target
    assert "attendanceFilter!=='all'" in target
    assert "visibleAttendanceRows.length===1" in target


def test_check_out_and_edit_times_validate_hhmm_and_require_check_in():
    frontend = _source("frontend/src/App.jsx")
    start = frontend.index("const runAttendanceTimeAction=")
    end = frontend.index("const employeeOptions=", start)
    actions = frontend[start:end]

    assert "isValidAttendanceTime(checkIn)" in actions
    assert "if(checkOut&&!checkIn)" in actions
    assert "isValidAttendanceTime(time)" in actions
    assert "attendanceIsPresentStatus(draft.attendance_status)" in actions


def test_toolbar_actions_are_disabled_for_holidays_and_during_saves():
    frontend = _source("frontend/src/App.jsx")
    start = frontend.index("Desktop attendance actions:")
    end = frontend.index("{attendanceIsHoliday&&<p", start)
    toolbar = frontend[start:end]

    assert toolbar.count("disabled={attendanceIsHoliday||attendanceBusy}") == 7
    assert "runAttendanceTimeAction('remarks')" in toolbar
    assert "runAttendanceStatusAction('Absent')" in toolbar

def test_web_attendance_matches_desktop_employee_order_and_editable_remark_presets():
    frontend = _source("frontend/src/App.jsx")
    api = _source("api_server.py")

    assert "ORDER BY e.display_order ASC, e.name COLLATE NOCASE" in api
    assert '"remarks_options": list(desktop_app.ATTENDANCE_REMARK_OPTIONS)' in api
    assert 'list="attendance-remark-presets"' in frontend
    assert "data.attendance.remarks_options" in frontend
    assert "setAttendanceRemarksTarget(row)" in frontend
    assert "Attendance remarks:" not in frontend
