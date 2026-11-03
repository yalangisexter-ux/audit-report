#!/usr/bin/env python3
import base64
from pathlib import Path
parts = sorted(Path("tools").glob("app_b64_*.txt"))
if not parts:
    raise SystemExit("missing app_b64_*.txt parts")
b64 = "".join(p.read_text(encoding="ascii").strip() for p in parts)
data = base64.b64decode(b64)
path = Path("frontend/src/App.jsx")
path.write_bytes(data)
assert b"ProgressBar" in data
assert b"AVG PRODUCTIVITY" in data
print("ok", path.stat().st_size)
