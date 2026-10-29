# Deploy on Render (testing)

1. Open https://dashboard.render.com and sign in (GitHub login recommended).
2. **New → Blueprint** and connect the repository `yalangisexter-ux/audit-report`.
3. Render reads `render.yaml` and creates the free web service `audit-report-web`.
4. After the first deploy finishes, open the service URL (looks like `https://audit-report-web.onrender.com`).

## Notes for testing

- Serves the React build from `frontend/dist` and the FastAPI API from `api_server.py`.
- SQLite data lives on the instance disk and **resets** when the free service spins down or is redeployed.
- First request after idle may take ~30–60s (free tier cold start).
- Desktop Windows installer is unchanged; this is web-only testing.

## Local equivalent

```bash
python run_web.py --no-browser
# or
uvicorn api_server:app --host 0.0.0.0 --port 8000
```
