#!/usr/bin/env python3
from pathlib import Path
def join(prefix, out):
    parts = sorted(Path("tools/phase1_chunks").glob(f"{prefix}_*.txt"))
    text = "".join(p.read_text(encoding="utf-8") for p in parts)
    Path(out).write_text(text, encoding="utf-8")
    print("assembled", out, len(text))
join("dash", "tools/apply_phase1_dashboard_only.py")
join("app", "tools/apply_phase1_app_only.py")
