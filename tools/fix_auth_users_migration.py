#!/usr/bin/env python3
"""Idempotently fix auth_users case-sensitive migration in app.py."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

NEW_BLOCK = (
    "        # Rebuild auth_users with exact-case username uniqueness. Older releases\n"
    "        # used COLLATE NOCASE, which made customer \"Admin\" and developer \"admin\"\n"
    "        # collide and caused the wrong account to be assigned the Developer role.\n"
    "        try:\n"
    "            auth_sql_row = self.conn.execute(\n"
    "                \"SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_users'\"\n"
    "            ).fetchone()\n"
    "            auth_sql = auth_sql_row[0] if auth_sql_row else \"\"\n"
    "            needs_case_migration = bool(auth_sql) and \"COLLATE NOCASE\" in auth_sql.upper()\n"
    "            if needs_case_migration:\n"
    "                # Drop leftover staging tables from interrupted upgrades so they\n"
    "                # cannot collide with a new staging name or confuse diagnostics.\n"
    "                for row in self.conn.execute(\n"
    "                    \"SELECT name FROM sqlite_master WHERE type='table' \"\n"
    "                    \"AND name LIKE 'auth_users_case_sensitive%'\"\n"
    "                ).fetchall():\n"
    "                    try:\n"
    "                        self.conn.execute('DROP TABLE IF EXISTS \"%s\"' % str(row[0]).replace('\"', '\"\"'))\n"
    "                    except Exception:\n"
    "                        pass\n"
    "                columns_info = list(self.conn.execute(\"PRAGMA table_info(auth_users)\").fetchall())\n"
    "                columns = [row[\"name\"] for row in columns_info]\n"
    "                if not columns or \"username\" not in columns:\n"
    "                    raise RuntimeError(\"auth_users schema is missing its username column\")\n"
    "                # Build a deterministic staging schema instead of regex-rewriting the\n"
    "                # legacy CREATE TABLE text. Some quoted/IF-NOT-EXISTS variants left the\n"
    "                # table name as auth_users and raised \"table auth_users already exists\"\n"
    "                # or failed the regex with \"Could not safely prepare...\".\n"
    "                staging_table = \"auth_users_case_sensitive_\" + secrets.token_hex(6)\n"
    "                col_defs = []\n"
    "                for row in columns_info:\n"
    "                    name = row[\"name\"]\n"
    "                    decl = (row[\"type\"] or \"TEXT\").strip() or \"TEXT\"\n"
    "                    if name == \"id\":\n"
    "                        decl = \"INTEGER PRIMARY KEY AUTOINCREMENT\"\n"
    "                    elif name == \"username\":\n"
    "                        decl = \"TEXT NOT NULL COLLATE BINARY\"\n"
    "                    piece = '\"%s\" %s' % (name.replace('\"', '\"\"'), decl)\n"
    "                    if name not in {\"id\", \"username\"} and row[\"notnull\"] and \"NOT NULL\" not in decl.upper():\n"
    "                        piece += \" NOT NULL\"\n"
    "                    if name != \"id\" and row[\"dflt_value\"] is not None and \"DEFAULT\" not in decl.upper():\n"
    "                        piece += \" DEFAULT %s\" % row[\"dflt_value\"]\n"
    "                    col_defs.append(piece)\n"
    "                create_sql = (\n"
    "                    'CREATE TABLE \"%s\" (' % staging_table\n"
    "                    + \", \".join(col_defs)\n"
    "                    + ', UNIQUE(\"username\")'\n"
    "                    + \")\"\n"
    "                )\n"
    "                index_sql = [\n"
    "                    row[0] for row in self.conn.execute(\n"
    "                        \"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='auth_users' AND sql IS NOT NULL\"\n"
    "                    ).fetchall()\n"
    "                ]\n"
    "                trigger_sql = [\n"
    "                    row[0] for row in self.conn.execute(\n"
    "                        \"SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name='auth_users' AND sql IS NOT NULL\"\n"
    "                    ).fetchall()\n"
    "                ]\n"
    "                if not self.conn.in_transaction:\n"
    "                    self.conn.execute(\"BEGIN IMMEDIATE\")\n"
    "                try:\n"
    "                    self.conn.execute(create_sql)\n"
    "                    column_list = \", \".join('\"' + name.replace('\"', '\"\"') + '\"' for name in columns)\n"
    "                    self.conn.execute(\n"
    "                        'INSERT INTO \"%s\" (%s) SELECT %s FROM auth_users'\n"
    "                        % (staging_table, column_list, column_list)\n"
    "                    )\n"
    "                    self.conn.execute(\"DROP TABLE auth_users\")\n"
    "                    self.conn.execute('ALTER TABLE \"%s\" RENAME TO auth_users' % staging_table)\n"
    "                    for statement in index_sql + trigger_sql:\n"
    "                        if not statement:\n"
    "                            continue\n"
    "                        if \"NOCASE\" in statement.upper():\n"
    "                            statement = re.sub(\n"
    "                                r\"COLLATE\\s+NOCASE\", \"COLLATE BINARY\", statement, flags=re.IGNORECASE\n"
    "                            )\n"
    "                        try:\n"
    "                            self.conn.execute(statement)\n"
    "                        except sqlite3.Error as idx_exc:\n"
    "                            logging.getLogger(\"db\").warning(\n"
    "                                \"auth_users index/trigger rebuild skipped: %s\", idx_exc\n"
    "                            )\n"
    "                    self.conn.commit()\n"
    "                except Exception:\n"
    "                    self.conn.rollback()\n"
    "                    try:\n"
    "                        self.conn.execute('DROP TABLE IF EXISTS \"%s\"' % staging_table)\n"
    "                        self.conn.commit()\n"
    "                    except Exception:\n"
    "                        pass\n"
    "                    raise\n"
    "\n"
)

def main() -> int:
    text = APP.read_text(encoding="utf-8")
    changed = False

    old_setup = (
        "        CREATE TABLE IF NOT EXISTS auth_users(\n"
        "          id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "          username TEXT NOT NULL COLLATE NOCASE UNIQUE,"
    )
    new_setup = (
        "        CREATE TABLE IF NOT EXISTS auth_users(\n"
        "          id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "          username TEXT NOT NULL COLLATE BINARY UNIQUE,"
    )
    if old_setup in text:
        text = text.replace(old_setup, new_setup, 1)
        changed = True
        print("updated setup() auth_users COLLATE to BINARY")

    if "deterministic staging schema" in text:
        print("migration block already uses deterministic staging schema")
    else:
        start = text.find("        # Rebuild auth_users with exact-case username uniqueness.")
        end = text.find("            # Repair legacy role corruption using exact-case identity only.", start)
        if start < 0 or end < 0:
            print("ERROR: migration markers not found", start, end)
            return 1
        text = text[:start] + NEW_BLOCK + text[end:]
        changed = True
        print("replaced auth_users case-sensitive migration block")

    if "Could not safely prepare auth_users" in text:
        print("ERROR: old failure string still present")
        return 1

    if changed:
        APP.write_text(text, encoding="utf-8")
        print("wrote", APP)
    else:
        print("no changes needed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
