@app.get("/api/dashboard")
def get_dashboard(conn: sqlite3.Connection = Depends(get_db)):
    """KPI + productivity scores matching desktop refresh_dashboard / worker formulas."""
    from datetime import timedelta

    today = date.today()
    today_str = today.isoformat()
    range_start = date.fromordinal(max(1, today.toordinal() - 90))

    employees = [
        dict(r)
        for r in conn.execute(
            "SELECT id, name, joining_date, active FROM employees WHERE active=1 ORDER BY name ASC"
        ).fetchall()
    ]
    total_employees = len(employees)

    att_by_id = {}
    if employees:
        ids = [int(e["id"]) for e in employees]
        marks = ",".join("?" for _ in ids)
        for record in conn.execute(
            f"SELECT employee_id, attendance_status, check_in, check_out FROM attendance "
            f"WHERE work_date=? AND employee_id IN ({marks})",
            (today_str, *ids),
        ).fetchall():
            att_by_id[int(record["employee_id"])] = dict(record)

    present_today = absent_today = leave_today = checkins_today = 0
    attendance_roster = []
    for emp in employees:
        rec = att_by_id.get(int(emp["id"]))
        status = str((rec or {}).get("attendance_status") or "Unmarked").strip()
        check_in = str((rec or {}).get("check_in") or "").strip()
        check_out = str((rec or {}).get("check_out") or "").strip()
        has_check_in = bool(check_in)
        normalized = status.casefold()
        if desktop_app.is_present_attendance_status(status) or (
            normalized in {"unmarked", ""} and has_check_in
        ):
            if normalized == "unmarked":
                status = "Present"
            present_today += 1
            if has_check_in:
                checkins_today += 1
        elif normalized == "absent":
            status = "Absent"
            absent_today += 1
        elif normalized == "leave":
            status = "Leave"
            leave_today += 1
        else:
            status = "Not checked" if normalized in {"unmarked", "", "not checked"} else status
        attendance_roster.append(
            {
                "employee_id": emp["id"],
                "name": emp["name"],
                "status": status,
                "check_in": check_in or "—",
                "check_out": check_out or "—",
            }
        )
    not_checked_today = max(0, total_employees - present_today - absent_today - leave_today)

    tasks_today = [
        dict(r)
        for r in conn.execute(
            """SELECT t.id, t.title, t.status, t.progress, t.due_time, t.priority, e.name as employee_name
               FROM tasks t LEFT JOIN employees e ON t.employee_id = e.id
               WHERE t.task_date=? ORDER BY t.id DESC LIMIT 12""",
            (today_str,),
        ).fetchall()
    ]
    day_statuses = [r["status"] for r in conn.execute("SELECT status FROM tasks WHERE task_date=?", (today_str,)).fetchall()]
    open_tasks = sum(
        1 for st in day_statuses
        if not desktop_app.is_explicitly_completed_task_status(st)
        and not desktop_app.is_cancelled_task_status(st)
    )
    completed_tasks = sum(1 for st in day_statuses if desktop_app.is_explicitly_completed_task_status(st))

    productivity = []
    avg_productivity = 0.0
    if employees:
        ids = [int(e["id"]) for e in employees]
        marks = ",".join("?" for _ in ids)
        starts = {}
        for emp in employees:
            start = None
            if emp.get("joining_date"):
                try:
                    start = date.fromisoformat(str(emp["joining_date"]))
                except (TypeError, ValueError):
                    start = None
            starts[int(emp["id"])] = max(start or range_start, range_start)
        start_text = min(starts.values()).isoformat()
        end_text = today_str
        task_rows = conn.execute(
            f"SELECT employee_id, task_date, progress, status FROM tasks "
            f"WHERE employee_id IN ({marks}) AND task_date BETWEEN ? AND ?",
            (*ids, start_text, end_text),
        ).fetchall()
        attendance_rows = conn.execute(
            f"SELECT employee_id, work_date, attendance_status, check_in FROM attendance "
            f"WHERE employee_id IN ({marks}) AND work_date BETWEEN ? AND ?",
            (*ids, start_text, end_text),
        ).fetchall()
        holiday_rows = conn.execute(
            "SELECT holiday_date FROM holidays WHERE holiday_date BETWEEN ? AND ?",
            (start_text, end_text),
        ).fetchall()
        setting = conn.execute("SELECT value FROM settings WHERE key='working_weekdays'").fetchone()
        try:
            weekdays = {
                int(v)
                for v in ((setting["value"] if setting else "0,1,2,3,4") or "0,1,2,3,4").split(",")
                if str(v).strip()
            }
        except (TypeError, ValueError):
            weekdays = {0, 1, 2, 3, 4}
        holidays = {row["holiday_date"] for row in holiday_rows}
        tasks_by = {i: [] for i in ids}
        att_by = {i: [] for i in ids}
        for item in task_rows:
            tasks_by[int(item["employee_id"])].append(item)
        for item in attendance_rows:
            att_by[int(item["employee_id"])].append(item)
        scores = []
        for emp in employees:
            eid = int(emp["id"])
            start = starts[eid]
            start_emp = start.isoformat()
            emp_tasks = [t for t in tasks_by[eid] if start_emp <= str(t["task_date"]) <= end_text]
            task_progress_total = 0
            known = 0
            for task in emp_tasks:
                if not desktop_app.is_known_task_status(task["status"]):
                    continue
                known += 1
                try:
                    task_progress_total += max(0, min(100, int(float(task["progress"] or 0))))
                except (TypeError, ValueError, OverflowError):
                    continue
            task_score = (task_progress_total / known) if known else None
            present_count = 0
            for attendance in att_by[eid]:
                st = str(attendance["attendance_status"] or "").strip()
                has_ci = bool(str(attendance["check_in"] or "").strip())
                if desktop_app.is_present_attendance_status(st) or (
                    st.casefold() in {"unmarked", ""} and has_ci
                ):
                    present_count += 1
            working_days = 0
            current_day = start
            while current_day <= today:
                day_text = current_day.isoformat()
                if current_day.weekday() in weekdays and day_text not in holidays:
                    working_days += 1
                current_day += timedelta(days=1)
            eligible = max(1, working_days)
            attendance_score = present_count / eligible * 100 if eligible else None
            if task_score is not None and attendance_score is not None:
                score = round(task_score * 0.7 + attendance_score * 0.3)
            elif task_score is not None:
                score = round(task_score)
            elif attendance_score is not None:
                score = round(attendance_score)
            else:
                score = 0
            completed = sum(
                1 for task in emp_tasks if desktop_app.is_explicitly_completed_task_status(task["status"])
            )
            scores.append(score)
            productivity.append(
                {
                    "employee_id": eid,
                    "name": emp["name"],
                    "score": score,
                    "working_days": working_days,
                    "present_count": present_count,
                    "task_count": len(emp_tasks),
                    "completed": completed,
                    "tracking_start": start_emp,
                }
            )
        avg_productivity = round(sum(scores) / len(scores), 1) if scores else 0.0

    att_rate = round((present_today / total_employees * 100), 1) if total_employees else 0.0
    recent_employees = [
        dict(r)
        for r in conn.execute(
            "SELECT id, employee_code, name, department, designation, active FROM employees ORDER BY id DESC LIMIT 8"
        ).fetchall()
    ]

    return {
        "today": today_str,
        "kpis": {
            "total_employees": total_employees,
            "present_today": present_today,
            "absent_today": absent_today,
            "leave_today": leave_today,
            "not_checked_today": not_checked_today,
            "open_tasks": open_tasks,
            "completed_tasks": completed_tasks,
            "checkins_today": checkins_today,
            "attendance_rate": att_rate,
            "avg_productivity": avg_productivity,
        },
        "recent_employees": recent_employees,
        "today_tasks": tasks_today,
        "attendance_roster": attendance_roster[:12],
        "productivity": productivity,
        "attendance_summary": (
            f"{att_rate}% checked in\n"
            f"{present_today} Present  ·  {absent_today} Absent  ·  "
            f"{leave_today} Leave  ·  {not_checked_today} Not checked"
        ),
    }
