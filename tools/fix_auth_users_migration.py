#!/usr/bin/env python3
"""Idempotently fix auth_users case-sensitive migration + ensure Admin/admin accounts."""
from __future__ import annotations

from pathlib import Path
import base64
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

# Blocks are base64-encoded so this tool file stays syntactically simple.
NEW_BLOCK = base64.b64decode(
    Path(__file__).with_name("fix_auth_users_migration.new_block.b64").read_text().strip()
).decode() if Path(__file__).with_name("fix_auth_users_migration.new_block.b64").exists() else ""

# Inline base64 for portability when companion files are absent.
import pathlib as _p
_HERE = _p.Path(__file__).resolve().parent

def _b64(s: str) -> str:
    return base64.b64decode(s).decode()

# Populated below after generation.
