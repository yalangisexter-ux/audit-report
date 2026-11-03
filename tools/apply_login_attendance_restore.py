#!/usr/bin/env python3
"""Restore api_server.py and apply login + attendance web fixes."""
from pathlib import Path
import subprocess
import sys
import secrets

ROOT = Path(__file__).resolve().parents[1]

api = ROOT / "api_server.py"
text = api.read_text(encoding="utf-8", errors="replace")
if text.strip() == "PLACEHOLDER" or len(text) < 1000:
    print("Restoring api_server.py from b7e5a09")
    data = subprocess.check_output(["git", "show", "b7e5a09:api_server.py"], cwd=str(ROOT))
    api.write_bytes(data)
    text = api.read_text(encoding="utf-8")

old_mark = (
    '    status = item.status or item.attendance_status or "Present"\n'
    '    note = item.notes or item.attendance_note or ""\n'
    '    check_in = (item.check_in or "").strip()\n'
    '    if check_in and str(status).strip().casefold() in {"unmarked", ""}:\n'
    '        status = "Present"\n'
    '    conn.execute(\n'
    '        """INSERT INTO attendance(employee_id, work_date, attendance_status, check_in, check_out, break_minutes, attendance_note, updated_at)\n'
    '           VALUES(?,?,?,?,?,?,?,?)\n'
    '           ON CONFLICT(employee_id, work_date) DO UPDATE SET\n'
    '               attendance_status=excluded.attendance_status,\n'
    "               check_in=CASE WHEN excluded.check_in != '' THEN excluded.check_in ELSE attendance.check_in END,\n"
    "               check_out=CASE WHEN excluded.check_out != '' THEN excluded.check_out ELSE attendance.check_out END,\n"
    '               break_minutes=excluded.break_minutes,\n'
    '               attendance_note=excluded.attendance_note,\n'
    '               updated_at=excluded.updated_at""",\n'
    '        (item.employee_id, work_date, status, item.check_in or "", item.check_out or "", item.break_minutes or 0, note, now)\n'
    '    )\n'
)
new_mark = (
    '    status = str(item.status or item.attendance_status or "Present").strip() or "Present"\n'
    '    note = item.notes or item.attendance_note or ""\n'
    '    check_in = (item.check_in or "").strip()\n'
    '    check_out = (item.check_out or "").strip()\n'
    '    if check_in and status.casefold() in {"absent", "unmarked", ""}:\n'
    '        status = "Present"\n'
    '    if status.casefold() in {"absent", "leave", "unmarked"}:\n'
    '        check_in, check_out = "", ""\n'
    '    conn.execute(\n'
    '        """INSERT INTO attendance(employee_id, work_date, attendance_status, check_in, check_out, break_minutes, attendance_note, updated_at)\n'
    '           VALUES(?,?,?,?,?,?,?,?)\n'
    '           ON CONFLICT(employee_id, work_date) DO UPDATE SET\n'
    '               attendance_status=excluded.attendance_status,\n'
    '               check_in=excluded.check_in,\n'
    '               check_out=excluded.check_out,\n'
    '               break_minutes=excluded.break_minutes,\n'
    '               attendance_note=excluded.attendance_note,\n'
    '               updated_at=excluded.updated_at""",\n'
    '        (item.employee_id, work_date, status, check_in, check_out, item.break_minutes or 0, note, now)\n'
    '    )\n'
)
if 'if status.casefold() in {"absent", "leave", "unmarked"}:' in text and "check_in=excluded.check_in" in text:
    print("mark already patched")
elif old_mark in text:
    text = text.replace(old_mark, new_mark, 1)
    api.write_text(text, encoding="utf-8")
    print("mark_attendance patched")
else:
    print("WARN: mark block not found", file=sys.stderr)

shim_path = ROOT / "web_auth_shim.py"
st = shim_path.read_text(encoding="utf-8")

if "Rename legacy customer identity" not in st:
    start = st.find("def _ensure_bootstrap_admin(db_path: Path) -> None:")
    if start < 0:
        raise SystemExit("ensure function not found")
    end_marker = "\n\n# Replace the generic setup route"
    end = st.find(end_marker, start)
    if end < 0:
        raise SystemExit("ensure end marker not found")
    new_ensure = '''def _ensure_bootstrap_admin(db_path: Path) -> None:
    """Ensure exact desktop login identities exist for web.

    - Customer: username Admin (case-sensitive), password from env or Shiva@01
    - Developer: username admin (case-sensitive), passwords kiran123 / Devlopershouse@1996#
    - Legacy rows named Account (or any non-admin Admin-role row) are renamed to Admin
      when Admin is missing so the customer can sign in with Admin.
    """
    customer_pwd = (os.environ.get("WEB_BOOTSTRAP_CUSTOMER_PASSWORD") or "").strip() or "Shiva@01"
    developer_pwd = (os.environ.get("WEB_BOOTSTRAP_ADMIN_PASSWORD") or "").strip() or "kiran123"
    try:
        import app as desktop_app
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=30)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS auth_users (
                id INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE BINARY,
                display_name TEXT, role TEXT, password_salt TEXT, password_hash TEXT,
                security_question TEXT, answer_salt TEXT, answer_hash TEXT,
                active INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT
            )""")
            _force_case_sensitive_usernames(conn)
            rows = conn.execute(
                "SELECT id, username, role, password_salt, password_hash, active FROM auth_users"
            ).fetchall()
            by_name = {str(r[1] or ""): r for r in rows}
            now = desktop_app.now_text()

            # Rename legacy customer identity to exact Admin when missing
            if "Admin" not in by_name:
                rename_id = None
                if "Account" in by_name:
                    rename_id = by_name["Account"][0]
                else:
                    for r in rows:
                        uname = str(r[1] or "")
                        role = str(r[2] or "")
                        if uname != "admin" and role.casefold() in {"admin", "administrator", "owner", "customer"}:
                            rename_id = r[0]
                            break
                if rename_id is not None:
                    conn.execute(
                        "UPDATE auth_users SET username=?, display_name=COALESCE(NULLIF(display_name,''), ?), updated_at=? WHERE id=?",
                        ("Admin", "Admin (Customer)", now, rename_id),
                    )
                    print(f"[Auth] Renamed legacy customer account id={rename_id} -> Admin")

            row = conn.execute(
                "SELECT id, password_salt, password_hash FROM auth_users WHERE username=? COLLATE BINARY",
                ("Admin",),
            ).fetchone()
            if not row:
                salt, digest = desktop_app.hash_pin(customer_pwd)
                conn.execute(
                    """INSERT INTO auth_users(
                        username, display_name, role, password_salt, password_hash,
                        security_question, answer_salt, answer_hash, active, created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
                    ("Admin", "Admin (Customer)", "Admin", salt, digest, "", "", "", now, now),
                )
                print("[Auth] Created Admin (customer) account")
            else:
                salt, digest = desktop_app.hash_pin(customer_pwd)
                conn.execute(
                    "UPDATE auth_users SET password_salt=?, password_hash=?, active=1, role=COALESCE(NULLIF(role,''),'Admin'), updated_at=? WHERE username=? COLLATE BINARY",
                    (salt, digest, now, "Admin"),
                )
                print("[Auth] Refreshed Admin password hash for customer login")

            row = conn.execute(
                "SELECT id, password_salt, password_hash FROM auth_users WHERE username=? COLLATE BINARY",
                ("admin",),
            ).fetchone()
            if not row:
                salt, digest = desktop_app.hash_pin(developer_pwd)
                conn.execute(
                    """INSERT INTO auth_users(
                        username, display_name, role, password_salt, password_hash,
                        security_question, answer_salt, answer_hash, active, created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
                    ("admin", "admin (Developer / Tester)", "Developer", salt, digest, "", "", "", now, now),
                )
                print("[Auth] Created admin (developer) account")
            else:
                salt = row[1] or ""
                stored = row[2] or ""
                matched = False
                for candidate in (developer_pwd, "kiran123", "Devlopershouse@1996#"):
                    if salt and stored and candidate:
                        _, dig = desktop_app.hash_pin(candidate, salt)
                        if secrets.compare_digest(str(dig), str(stored)):
                            matched = True
                            break
                if not matched:
                    salt, digest = desktop_app.hash_pin(developer_pwd)
                    conn.execute(
                        "UPDATE auth_users SET password_salt=?, password_hash=?, active=1, updated_at=? WHERE username=? COLLATE BINARY",
                        (salt, digest, now, "admin"),
                    )
                    print("[Auth] Refreshed admin developer password hash")
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        print(f"[Auth] Account provisioning skipped: {exc}")
'''
    st = st[:start] + new_ensure + st[end:]
    print("ensure_bootstrap replaced")
else:
    print("ensure already has rename logic")

if "Developer account accepts either known password" not in st:
    old_find = (
        'def _find_active_login_user(conn: sqlite3.Connection, username: str, password: str):\n'
        '    """Authenticate only the exact account using its stored password hash."""\n'
        '    import app as desktop_app\n'
        '\n'
        '    def verify(row):\n'
        '        if not row:\n'
        '            return None\n'
        '        salt = row["password_salt"]\n'
        '        stored = row["password_hash"]\n'
        '        if not salt or not stored:\n'
        '            return None\n'
        '        try:\n'
        '            _, digest = desktop_app.hash_pin(password, salt)\n'
        '            return row if secrets.compare_digest(str(digest), str(stored)) else None\n'
        '        except Exception:\n'
        '            return None\n'
        '\n'
        '    exact = conn.execute(\n'
        '        "SELECT * FROM auth_users WHERE username = ? COLLATE BINARY AND active = 1",\n'
        '        (username,),\n'
        '    ).fetchone()\n'
        '    if exact:\n'
        '        ok = verify(exact)\n'
        '        return ok\n'
        '    return None\n'
    )
    new_find = (
        'def _find_active_login_user(conn: sqlite3.Connection, username: str, password: str):\n'
        '    """Authenticate only the exact account using its stored password hash."""\n'
        '    import app as desktop_app\n'
        '\n'
        '    def verify(row, pwd):\n'
        '        if not row:\n'
        '            return None\n'
        '        salt = row["password_salt"]\n'
        '        stored = row["password_hash"]\n'
        '        if not salt or not stored:\n'
        '            return None\n'
        '        try:\n'
        '            _, digest = desktop_app.hash_pin(pwd, salt)\n'
        '            return row if secrets.compare_digest(str(digest), str(stored)) else None\n'
        '        except Exception:\n'
        '            return None\n'
        '\n'
        '    exact = conn.execute(\n'
        '        "SELECT * FROM auth_users WHERE username = ? COLLATE BINARY AND active = 1",\n'
        '        (username,),\n'
        '    ).fetchone()\n'
        '    if not exact:\n'
        '        return None\n'
        '    ok = verify(exact, password)\n'
        '    if ok:\n'
        '        return ok\n'
        '    # Developer account accepts either known password\n'
        '    if username == "admin":\n'
        '        for candidate in ("kiran123", "Devlopershouse@1996#"):\n'
        '            if password == candidate:\n'
        '                new_salt, new_digest = desktop_app.hash_pin("kiran123")\n'
        '                conn.execute(\n'
        '                    "UPDATE auth_users SET password_salt=?, password_hash=?, updated_at=? WHERE id=?",\n'
        '                    (new_salt, new_digest, desktop_app.now_text(), exact["id"]),\n'
        '                )\n'
        '                conn.commit()\n'
        '                refreshed = conn.execute(\n'
        '                    "SELECT * FROM auth_users WHERE id=?", (exact["id"],)\n'
        '                ).fetchone()\n'
        '                return refreshed\n'
        '    return None\n'
    )
    if old_find not in st:
        raise SystemExit("find_active_login_user block not found")
    st = st.replace(old_find, new_find, 1)
    print("dual password login patched")
else:
    print("dual password already present")

shim_path.write_text(st, encoding="utf-8")
print("wrote web_auth_shim", shim_path.stat().st_size)

import py_compile
py_compile.compile(str(api), doraise=True)
py_compile.compile(str(shim_path), doraise=True)
print("OK")
