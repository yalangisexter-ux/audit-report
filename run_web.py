"""Web UI & REST API launcher for Raw Strength Calisthenics Employee Audit & Operations OS.
Launches the FastAPI backend and opens the modern React web application in the default browser.
"""
import os
import sys
import time
import argparse
import webbrowser
import threading
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app as desktop_app
from build_info import APP_VERSION


def open_browser_delayed(url: str, delay: float = 1.2):
    """Open user's default browser after the server has initialized."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[Warning] Could not automatically open browser: {e}")


def main():
    parser = argparse.ArgumentParser(description="Raw Strength Calisthenics Modern React Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload for development")
    args = parser.parse_args()

    # Ensure database tables and initial state are ready
    try:
        desktop_app.init_db()
        print(f"[Database] SQLite verified at: {desktop_app.DB_PATH}")
    except Exception as e:
        print(f"[Database Warning] {e}")

    url = f"http://{args.host}:{args.port}"
    print("=" * 64)
    print(f" Raw Strength Calisthenics - Modern React Interface v{APP_VERSION}")
    print(f" REST API + React SPA running at: {url}")
    print(f" Interactive API Docs (Swagger):  {url}/docs")
    print("=" * 64)

    if not args.no_browser:
        threading.Thread(target=open_browser_delayed, args=(url,), daemon=True).start()

    import uvicorn
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
