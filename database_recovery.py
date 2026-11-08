"""Pre-startup recovery of an existing Raw Strength SQLite customer database.

Only the exact application database filename is considered. Candidates are
validated as SQLite databases with application tables and meaningful records.
A populated current database is never replaced.
"""
from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

_LOG = logging.getLogger("db_recovery")
_SKIP_DIRS = {
    "$recycle.bin", "system volume information", "windows", "program files",
    "program files (x86)", "programdata", "recovery", "perflogs",
    "node_modules", ".git", "__pycache__", "windowsapps",
}
_REQUIRED_TABLES = {"settings", "auth_users", "employees", "tasks", "attendance"}
_DATA_TABLES = ("auth_users", "employees", "tasks", "attendance", "holidays",
                "archived_documents", "source_reports", "audit_log")

def _drives():
    if os.name == "nt":
        try:
            import ctypes
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            return [Path(f"{chr(65+i)}:\\") for i in range(26) if mask & (1 << i)]
        except Exception:
            pass
    roots = [Path.home(), Path(os.environ.get("LOCALAPPDATA", str(Path.home())))]
    return list(dict.fromkeys(p for p in roots if p.exists()))

def _candidate_paths():
    seen = set()
    for root in _drives():
        if not root.exists():
            continue
        for current, dirs, files in os.walk(str(root), topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if d.casefold() not in _SKIP_DIRS]
            if "employee_audit.db" in {f.casefold() for f in files}:
                candidate = Path(current) / next(f for f in files if f.casefold() == "employee_audit.db")
                try:
                    resolved = str(candidate.resolve()).casefold()
                except OSError:
                    resolved = str(candidate).casefold()
                if resolved not in seen:
                    seen.add(resolved)
                    yield candidate

def _inspect(path):
    try:
        if not path.is_file() or path.stat().st_size < 4096:
            return None
        with path.open("rb") as handle:
            if handle.read(16) != b"SQLite format 3\x00":
                return None
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return None
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if not (_REQUIRED_TABLES & tables):
                return None
            counts = {}
            for table in _DATA_TABLES:
                if table in tables:
                    counts[table] = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            if not any(counts.values()):
                return None
            # Prioritize real business records, then preserve account identities.
            score = sum(counts.values()) + counts.get("auth_users", 0) * 1000
            return score, counts
        finally:
            conn.close()
    except Exception:
        return None

def _is_populated(path):
    info = _inspect(path)
    return bool(info)

def recover_database_before_startup(target_path):
    """Import the strongest validated legacy DB before Database.setup() runs."""
    target = Path(target_path)
    current = _inspect(target) if target.exists() else None
    if current:
        return {"status": "existing_database_kept", "path": str(target), "counts": current[1]}
    candidates = []
    for candidate in _candidate_paths():
        try:
            if candidate.resolve() == target.resolve():
                continue
        except OSError:
            pass
        info = _inspect(candidate)
        if info:
            candidates.append((info[0], candidate, info[1]))
    if not candidates:
        return {"status": "no_valid_local_database_found"}
    candidates.sort(key=lambda item: (item[0], item[1].stat().st_mtime), reverse=True)
    best_score = candidates[0][0]
    tied = [item for item in candidates if item[0] == best_score]
    if len(tied) > 1:
        # Never guess between equally complete customer databases.
        raise RuntimeError("Multiple equally complete Raw Strength databases were found. "
                           "No database was changed; contact support to select the correct customer copy.")
    _, source, counts = candidates[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if target.exists():
        backup = target.with_name(target.name + f".pre-recovery-{stamp}.bak")
        shutil.copy2(target, backup)
    fd, staged_name = tempfile.mkstemp(prefix="rsc-recovery-", suffix=".db", dir=str(target.parent))
    os.close(fd)
    staged = Path(staged_name)
    try:
        src = sqlite3.connect(str(source), timeout=20)
        dst = sqlite3.connect(str(staged), timeout=20)
        try:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Recovered database failed integrity validation.")
            dst.commit()
        finally:
            dst.close()
            src.close()
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)
    _LOG.warning("Recovered customer database from %s with record counts %s", source, counts)
    return {"status": "recovered", "source": str(source), "path": str(target), "counts": counts}
