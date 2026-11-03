#!/usr/bin/env python3
import base64
from pathlib import Path
parts = sorted(Path("tools").glob("api_fix_part_*.txt"), key=lambda p: int(p.stem.split("_")[-1]))
b64 = "".join(p.read_text(encoding="ascii") for p in parts)
data = base64.b64decode(b64)
Path("api_server.py").write_bytes(data)
t = data.decode("utf-8")
assert "def ensure_canonical_accounts" in t
assert "Shiva@01" in t
assert 'if status.casefold() in {"absent", "leave", "unmarked"}:' in t
print("installed", len(data))
