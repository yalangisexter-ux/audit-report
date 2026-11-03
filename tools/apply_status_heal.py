#!/usr/bin/env python3
from pathlib import Path
p = Path("web_auth_shim.py")
st = p.read_text(encoding="utf-8")
old = '''@api.app.get("/api/auth/status")
def web_auth_status(conn: sqlite3.Connection = Depends(api.get_db)):
    try:
        count = conn.execute("SELECT COUNT(*) FROM auth_users WHERE active=1").fetchone()[0]
'''
new = '''@api.app.get("/api/auth/status")
def web_auth_status(conn: sqlite3.Connection = Depends(api.get_db)):
    try:
        # Heal Admin/admin identities on every status check so login works after deploy
        try:
            import app as desktop_app
            _ensure_bootstrap_admin(Path(desktop_app.DB_PATH))
        except Exception as _heal_exc:
            print(f"[Auth] status heal skipped: {_heal_exc}")
        count = conn.execute("SELECT COUNT(*) FROM auth_users WHERE active=1").fetchone()[0]
'''
if "status heal skipped" in st:
    print("already")
elif old not in st:
    raise SystemExit("block missing")
else:
    p.write_text(st.replace(old, new, 1), encoding="utf-8")
    print("patched")
