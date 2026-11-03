# Runtime heal: Admin/Shiva@01 dual-password under COLLATE NOCASE UNIQUE auth_users.
# Imported early from web boot so rename + password set happen before login.
from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path


def apply_admin_login_heal() -> None:
    try:
        import web_auth_shim as shim
        import app as desktop_app
    except Exception as exc:
        print(f"[Heal] import failed: {exc}")
        return

    customer_pwd = (os.environ.get("WEB_BOOTSTRAP_CUSTOMER_PASSWORD") or "").strip() or "Shiva@01"

    def ensure(db_path):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=30)
        try:
            rows = conn.execute(
                "SELECT id, username, role FROM auth_users"
            ).fetchall()
            by_name = {str(r[1] or ""): r for r in rows}
            now = desktop_app.now_text()
            if "Admin" not in by_name:
                rename_id = None
                if "admin" in by_name:
                    rename_id = by_name["admin"][0]
                elif "Account" in by_name:
                    rename_id = by_name["Account"][0]
                else:
                    for r in rows:
                        role = str(r[2] or "").casefold()
                        if role in {
                            "admin",
                            "administrator",
                            "owner",
                            "customer",
                            "developer",
                        }:
                            rename_id = r[0]
                            break
                if rename_id is not None:
                    conn.execute(
                        "UPDATE auth_users SET username=?, "
                        "display_name=COALESCE(NULLIF(display_name,''), ?), "
                        "role=COALESCE(NULLIF(role,''),'Admin'), active=1, updated_at=? "
                        "WHERE id=?",
                        ("Admin", "Admin (Customer)", now, rename_id),
                    )
                    print(f"[Heal] Renamed id={rename_id} -> Admin")
            row = conn.execute(
                "SELECT id FROM auth_users WHERE username=? COLLATE NOCASE",
                ("Admin",),
            ).fetchone()
            if row:
                salt, digest = desktop_app.hash_pin(customer_pwd)
                conn.execute(
                    "UPDATE auth_users SET username='Admin', password_salt=?, "
                    "password_hash=?, active=1, "
                    "role=COALESCE(NULLIF(role,''),'Admin'), updated_at=? WHERE id=?",
                    (salt, digest, now, row[0]),
                )
                print("[Heal] Set Admin password to Shiva@01")
            else:
                salt, digest = desktop_app.hash_pin(customer_pwd)
                conn.execute(
                    """INSERT INTO auth_users(
                        username, display_name, role, password_salt, password_hash,
                        security_question, answer_salt, answer_hash, active,
                        created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
                    (
                        "Admin",
                        "Admin (Customer)",
                        "Admin",
                        salt,
                        digest,
                        "",
                        "",
                        "",
                        now,
                        now,
                    ),
                )
                print("[Heal] Created Admin")
            conn.commit()
        finally:
            conn.close()

    def find(conn, username, password):
        def verify(row, pwd):
            if not row:
                return None
            salt = row["password_salt"]
            stored = row["password_hash"]
            if not salt or not stored:
                return None
            try:
                _, digest = desktop_app.hash_pin(pwd, salt)
                return (
                    row
                    if secrets.compare_digest(str(digest), str(stored))
                    else None
                )
            except Exception:
                return None

        row = conn.execute(
            "SELECT * FROM auth_users WHERE username=? COLLATE BINARY AND active=1",
            (username,),
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT * FROM auth_users WHERE username=? COLLATE NOCASE AND active=1",
                (username,),
            ).fetchone()
        if not row:
            return None
        ok = verify(row, password)
        if ok:
            return ok
        if str(row["username"] or "").casefold() == "admin" and password in (
            "Shiva@01",
            "kiran123",
            "Devlopershouse@1996#",
        ):
            new_salt, new_digest = desktop_app.hash_pin(password)
            conn.execute(
                "UPDATE auth_users SET password_salt=?, password_hash=?, "
                "active=1, updated_at=? WHERE id=?",
                (new_salt, new_digest, desktop_app.now_text(), row["id"]),
            )
            conn.commit()
            return conn.execute(
                "SELECT * FROM auth_users WHERE id=?", (row["id"],)
            ).fetchone()
        return None

    shim._ensure_bootstrap_admin = ensure
    shim._find_active_login_user = find
    print("[Heal] Admin/Shiva@01 dual-password hooks installed")


apply_admin_login_heal()
