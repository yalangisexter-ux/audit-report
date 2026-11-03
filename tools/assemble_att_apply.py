#!/usr/bin/env python3
import base64
from pathlib import Path
parts = sorted(Path("tools").glob("att_apply_b64_*.txt"), key=lambda p: int(p.stem.split("_")[-1]))
b64 = "".join(p.read_text(encoding="ascii") for p in parts)
Path("tools/apply_attendance_totals_fix.py").write_bytes(base64.b64decode(b64))
print("assembled", Path("tools/apply_attendance_totals_fix.py").stat().st_size)
