#!/usr/bin/env python3
"""Ensure Admin/admin logins and fix web attendance mark persistence."""
from pathlib import Path

path = Path("api_server.py")
text = path.read_text(encoding="utf-8")

ENSURE = r'''
def ensure_canonical_accounts(conn: sqlite3.Connection) -> None:
    """Keep customer/developer logins aligned with known production accounts.

    Customer: username Admin (case-sensitive), password Shiva@01
    Developer: username admin (case-sensitive), passwords kiran123 or Devlopershouse@1996#
    Legacy DB may still have username Account for the customer — rename it to Admin.
    """
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, username, role, password_salt, password_hash, active FROM auth_users"
        ).fetchall()]
    except Exception:
        return
    by_name = {str(r.get("username") or ""): r for r in rows}
    now = desktop_app.now_text()

    if "Admin" not in by_name and "Account" in by_name:
        conn.execute(
            "UPDATE auth_users SET username=?, display_name=COALESCE(NULLIF(display_name,''), ?), updated_at=? WHERE id=?",
            ("Admin", "Admin (Customer)", now, by_name["Account"]["id"]),
        )
        by_name["Admin"] = by_name.pop("Account")
        by_name["Admin"]["username"] = "Admin"

    customer_password = "Shiva@01"
    if "Admin" not in by_name:
        salt, digest = desktop_app.hash_pin(customer_password)
        ans_salt, ans_hash = desktop_app.hash_pin("recovery")
        conn.execute(
            """INSERT INTO auth_users(username, display_name, role, password_salt, password_hash,
               security_question, answer_salt, answer_hash, active, created_at, updated_at)
               VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
            ("Admin", "Admin (Customer)", "Admin", salt, digest, "Recovery", ans_salt, ans_hash, now, now),
        )
    else:
        salt, digest = desktop_app.hash_pin(customer_password)
        conn.execute(
            "UPDATE auth_users SET password_salt=?, password_hash=?, active=1, role=COALESCE(NULLIF(role,''),'Admin'), updated_at=? WHERE username=? COLLATE BINARY",
            (salt, digest, now, "Admin"),
        )

    if "admin" not in by_name:
        salt, digest = desktop_app.hash_pin("kiran123")
        ans_salt, ans_hash = desktop_app.hash_pin("recovery")
        conn.execute(
            """INSERT INTO auth_users(username, display_name, role, password_salt, password_hash,
               security_question, answer_salt, answer_hash, active, created_at, updated_at)
               VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
            ("admin", "admin (Developer - Test Mode)", "Developer", salt, digest, "Recovery", ans_salt, ans_hash, now, now),
        )
    else:
        row = by_name["admin"]
        salt = row.get("password_salt") or ""
        stored = row.get("password_hash") or ""
        matched = False
        for candidate in ("kiran123", "Devlopershouse@1996#"):
            if salt and stored:
                _, dig = desktop_app.hash_pin(candidate, salt)
                if secrets.compare_digest(dig, stored):
                    matched = True
                    break
        if not matched:
            salt, digest = desktop_app.hash_pin("kiran123")
            conn.execute(
                "UPDATE auth_users SET password_salt=?, password_hash=?, active=1, updated_at=? WHERE username=? COLLATE BINARY",
                (salt, digest, now, "admin"),
            )
    conn.commit()


'''

if "def ensure_canonical_accounts" not in text:
    text = text.replace("def get_db():", ENSURE + "def get_db():", 1)
    print("inserted ensure_canonical_accounts")
else:
    print("ensure present")

old = """    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    manager = WEB_SYNC_MANAGER
"""
new = """    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    global _CANONICAL_ACCOUNTS_READY
    if not globals().get("_CANONICAL_ACCOUNTS_READY"):
        try:
            ensure_canonical_accounts(conn)
            _CANONICAL_ACCOUNTS_READY = True
        except Exception as exc:
            print(f"[Auth] ensure_canonical_accounts skipped: {exc}")
    manager = WEB_SYNC_MANAGER
"""
if "ensure_canonical_accounts(conn)" not in text:
    if old not in text:
        raise SystemExit("get_db pragma block missing")
    text = text.replace(old, new, 1)
    print("wired ensure into get_db")
else:
    print("get_db already wired")

import re
login_pat = re.compile(
    r'@app\.post\("/api/auth/login"\)\ndef login\(req: LoginRequest, conn: sqlite3\.Connection = Depends\(get_db\)\):.*?\n    return \{"token": token, "user": user_info\}\n',
    re.S,
)
new_login = '''@app.post("/api/auth/login")
def login(req: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    username = (req.username or "").strip()
    password = req.password or ""
    row = conn.execute(
        "SELECT * FROM auth_users WHERE username=? COLLATE BINARY AND active=1",
        (username,),
    ).fetchone()
    if not row:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. Check the exact username, password, and account active status.",
        )

    salt = row["password_salt"] or ""
    stored = row["password_hash"] or ""
    matched = False
    if salt and stored:
        _, digest = desktop_app.hash_pin(password, salt)
        matched = secrets.compare_digest(digest, stored)
    # Developer account accepts either known password.
    if not matched and username == "admin":
        for candidate in ("kiran123", "Devlopershouse@1996#"):
            if password != candidate:
                continue
            new_salt, new_digest = desktop_app.hash_pin(candidate)
            conn.execute(
                "UPDATE auth_users SET password_salt=?, password_hash=?, updated_at=? WHERE id=?",
                (new_salt, new_digest, desktop_app.now_text(), row["id"]),
            )
            conn.commit()
            matched = True
            break
    if not matched:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password. Check the exact username, password, and account active status.",
        )

    token = secrets.token_hex(24)
    user_info = {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
        "role": row["role"],
    }
    ACTIVE_SESSIONS[token] = user_info
    return {"token": token, "user": user_info}
'''
m = login_pat.search(text)
if not m:
    if "Developer account accepts either known password" in text:
        print("login already patched")
    else:
        raise SystemExit("login block not found")
else:
    text = text[: m.start()] + new_login + text[m.end() :]
    print("login patched")

old_mark = """    check_in = (item.check_in or "").strip()
    if check_in and str(status).strip().casefold() in {"unmarked", ""}:
        status = "Present"
    conn.execute(
        """INSERT INTO attendance(employee_id, work_date, attendance_status, check_in, check_out, break_minutes, attendance_note, updated_at)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(employee_id, work_date) DO UPDATE SET
               attendance_status=excluded.attendance_status,
               check_in=CASE WHEN excluded.check_in != '' THEN excluded.check_in ELSE attendance.check_in END,
               check_out=CASE WHEN excluded.check_out != '' THEN excluded.check_out ELSE attendance.check_out END,
               break_minutes=excluded.break_minutes,
               attendance_note=excluded.attendance_note,
               updated_at=excluded.updated_at""",
        (item.employee_id, work_date, status, item.check_in or "", item.check_out or "", item.break_minutes or 0, note, now)
    )
"""
new_mark = """    status = str(status or "Present").strip() or "Present"
    check_in = (item.check_in or "").strip()
    check_out = (item.check_out or "").strip()
    if check_in and status.casefold() in {"absent", "unmarked", ""}:
        status = "Present"
    if status.casefold() in {"absent", "leave", "unmarked"}:
        check_in, check_out = "", ""
    conn.execute(
        """INSERT INTO attendance(employee_id, work_date, attendance_status, check_in, check_out, break_minutes, attendance_note, updated_at)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(employee_id, work_date) DO UPDATE SET
               attendance_status=excluded.attendance_status,
               check_in=excluded.check_in,
               check_out=excluded.check_out,
               break_minutes=excluded.break_minutes,
               attendance_note=excluded.attendance_note,
               updated_at=excluded.updated_at""",
        (item.employee_id, work_date, status, check_in, check_out, item.break_minutes or 0, note, now)
    )
"""
if 'if status.casefold() in {"absent", "leave", "unmarked"}:' in text and "check_in=excluded.check_in" in text:
    print("mark already patched")
elif old_mark in text:
    text = text.replace(old_mark, new_mark, 1)
    print("mark patched")
else:
    old_mark2 = old_mark.replace('{"unmarked", ""}', '{"absent", "unmarked", ""}')
    if old_mark2 in text:
        text = text.replace(old_mark2, new_mark, 1)
        print("mark patched v2")
    else:
        raise SystemExit("mark block not found")

path.write_text(text, encoding="utf-8")
print("wrote", path.stat().st_size)
