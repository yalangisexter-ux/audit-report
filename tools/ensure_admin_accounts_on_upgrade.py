#!/usr/bin/env python3
"""Append Admin/Shiva@01 and admin/kiran123 ensure block to app.py if missing."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

OLD = """            # Never infer identity or change roles by a case-insensitive username
            # lookup. Preserve all existing customer/developer credentials.
        except Exception as e:
            logging.getLogger("db").exception("auth_users case-sensitive migration failed: %s", e)
            raise

        # Do not create a known/default credential. Authentication is handled by
        # the first-run Admin account and per-user password/recovery records.
        self.conn.commit()
"""

NEW = """            # Never infer identity or change roles by a case-insensitive username
            # lookup. Preserve all existing customer/developer credentials.

            # Ensure the two real accounts always exist after upgrade without wiping
            # the customer database or overwriting existing password hashes:
            #   Admin  / Shiva@01     -> customer Admin
            #   admin  / kiran123     -> developer
            # Only INSERT when the exact-case username is missing.
            ts = now_text()
            if not self.conn.execute(
                "SELECT 1 FROM auth_users WHERE username='Admin' COLLATE BINARY"
            ).fetchone():
                salt, digest = hash_pin("Shiva@01")
                self.conn.execute(
                    "INSERT INTO auth_users("
                    "username, display_name, role, password_salt, password_hash, "
                    "security_question, answer_salt, answer_hash, active, created_at, updated_at"
                    ") VALUES('Admin', 'Customer Administrator', 'Admin', ?, ?, '', '', '', 1, ?, ?)",
                    (salt, digest, ts, ts),
                )
            else:
                self.conn.execute(
                    "UPDATE auth_users SET role='Admin', active=1, updated_at=? "
                    "WHERE username='Admin' COLLATE BINARY",
                    (ts,),
                )

            if not self.conn.execute(
                "SELECT 1 FROM auth_users WHERE username='admin' COLLATE BINARY"
            ).fetchone():
                salt, digest = hash_pin("kiran123")
                self.conn.execute(
                    "INSERT INTO auth_users("
                    "username, display_name, role, password_salt, password_hash, "
                    "security_question, answer_salt, answer_hash, active, created_at, updated_at"
                    ") VALUES('admin', 'admin (Developer - Test Mode)', 'Developer', ?, ?, '', '', '', 1, ?, ?)",
                    (salt, digest, ts, ts),
                )
            else:
                self.conn.execute(
                    "UPDATE auth_users SET role='Developer', active=1, updated_at=? "
                    "WHERE username='admin' COLLATE BINARY",
                    (ts,),
                )
        except Exception as e:
            logging.getLogger("db").exception("auth_users case-sensitive migration failed: %s", e)
            raise

        # Existing customer tables (employees, tasks, attendance, etc.) are never
        # wiped. Only missing Admin/admin auth rows are appended above.
        self.conn.commit()
"""

def main() -> int:
    text = APP.read_text(encoding="utf-8")
    if "Admin  / Shiva@01" in text:
        print("ensure-both-users already present")
        return 0
    if OLD not in text:
        print("ERROR: ensure markers not found")
        return 1
    APP.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("wrote ensure-both-users into", APP)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
