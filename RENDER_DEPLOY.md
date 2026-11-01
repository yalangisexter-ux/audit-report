# Deploy the standalone web edition on Render

1. Connect `yalangisexter-ux/audit-report` to Render as a Blueprint.
2. The service starts FastAPI and serves the checked-in production client in `frontend/dist`.
3. Set `WEB_STANDALONE=1` and `AUDIT_DATA_DIR=/var/data` (already declared in `render.yaml`).
4. Attach a persistent disk mounted at `/var/data` before using the service for real customer data. Render's free web service has ephemeral storage; a deploy or instance replacement can erase its local SQLite database. A persistent disk requires a paid Render service plan.

## Independent web database

- The web service creates `web_employee_audit.db` under `AUDIT_DATA_DIR`.
- The web process does not pull the desktop database snapshot and does not send web writes to the desktop database-sync Worker.
- The Windows EXE continues using its existing LocalAppData database and updater; this web-only change does not alter the EXE.
- Import an existing desktop `.db` file from **Settings → Standalone Web Database → Import old database**. The import validates SQLite integrity and required tables, retains a pre-import backup, and then replaces only the web database.
- Export a complete SQLite copy from the same Settings page. Keep downloaded exports somewhere safe.
- After an import, sign in using credentials contained in the imported database.

## Mobile and desktop access

The browser interface is responsive and can be opened from a phone, tablet, or desktop browser. Use the same web URL and web account on each device. For durable multi-device use, the persistent disk requirement above must be met.

## Local development

```bash
python run_web.py --no-browser
# or
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

For local standalone testing, set `WEB_STANDALONE=1` and `AUDIT_DATA_DIR=./web-data` before starting the server.
