"""Durable web session store (file-backed). EXE untouched."""
from __future__ import annotations

import json
import os
from pathlib import Path


class PersistentSessions(dict):
    def __init__(self, path: Path, initial=None):
        super().__init__(initial or {})
        self._path = path

    def _flush(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self), encoding="utf-8")
            os.replace(tmp, self._path)
        except Exception as exc:
            print(f"[Sessions] persist failed: {exc}")

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._flush()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._flush()

    def clear(self):
        super().clear()
        self._flush()


def install(api_module) -> None:
    try:
        import app as desktop_app
        base = Path(getattr(desktop_app, "APP_DIR", Path.home() / "EmployeeAuditManager"))
    except Exception:
        base = Path(os.environ.get("AUDIT_DATA_DIR") or (Path.home() / "EmployeeAuditManager"))
    path = base / "web_sessions.json"
    data = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
    api_module.ACTIVE_SESSIONS = PersistentSessions(path, data)
    print(f"[Sessions] Durable sessions loaded ({len(api_module.ACTIVE_SESSIONS)}) from {path}")
