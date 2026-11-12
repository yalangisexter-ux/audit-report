"""Build a guarded, idempotent SQL import from the canonical encrypted customer snapshot."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
import sys

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from cloudflare_migration_guard import decrypt_snapshot, validate_source

EXCLUDED_TABLES = {"web_auth_sessions"}
MAX_CHUNK_BYTES = 350_000
MAX_CHUNK_STATEMENTS = 120


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def expected_migration_schema(migrations_dir: Path) -> dict[str, set[str]]:
    """Apply every checked-in D1 migration and return its table/column contract."""
    migration_files = sorted(Path(migrations_dir).glob("*.sql"))
    if not migration_files:
        raise ValueError("No Cloudflare D1 migration files were found.")

    connection = sqlite3.connect(":memory:")
    try:
        for migration in migration_files:
            connection.executescript(migration.read_text(encoding="utf-8"))
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if not row[0].startswith("sqlite_")
        }
        schema = {}
        for table in sorted(tables):
            columns = {
                row[1]
                for row in connection.execute(
                    f"PRAGMA table_info({quote_identifier(table)})"
                ).fetchall()
            }
            if not columns:
                raise ValueError(f"Migration schema has no columns for {table}.")
            schema[table] = columns
        return schema
    finally:
        connection.close()


def ensure_empty_target(counts: dict[str, int]) -> None:
    """Refuse canonical import/reconciliation if any application table already has rows."""
    populated = {
        table: int(count)
        for table, count in counts.items()
        if table != "settings" and int(count) > 0
    }
    if populated:
        detail = ", ".join(f"{table}={count}" for table, count in sorted(populated.items()))
        raise ValueError(
            "Cloudflare D1 already contains application rows; refusing to import or "
            "reconcile the canonical snapshot into a non-empty database. "
            f"Populated tables: {detail}. Export and verify a current D1 backup and "
            "use an explicit reviewed merge path."
        )


def sql_value(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite floating point values cannot be imported.")
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def ordered_tables(connection: sqlite3.Connection) -> list[str]:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if not row[0].startswith("sqlite_") and row[0] not in EXCLUDED_TABLES
    }
    dependencies = {table: set() for table in tables}
    for table in tables:
        for row in connection.execute(
            f"PRAGMA foreign_key_list({quote_identifier(table)})"
        ).fetchall():
            parent = row[2]
            if parent in tables and parent != table:
                dependencies[table].add(parent)

    ordered: list[str] = []
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(table: str) -> None:
        if table in permanent:
            return
        if table in temporary:
            raise ValueError("Foreign-key dependency cycle prevents a safe ordered import.")
        temporary.add(table)
        for parent in sorted(dependencies[table]):
            visit(parent)
        temporary.remove(table)
        permanent.add(table)
        ordered.append(table)

    for table in sorted(tables):
        visit(table)
    return ordered


def build_import(source: sqlite3.Connection, schema_path: Path, output_dir: Path) -> dict:
    target = sqlite3.connect(":memory:")
    try:
        target.executescript(schema_path.read_text(encoding="utf-8"))
        source_tables = {
            row[0] for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall() if not row[0].startswith("sqlite_")
        }
        target_tables = {
            row[0] for row in target.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall() if not row[0].startswith("sqlite_")
        }
        missing = sorted(source_tables - target_tables)
        if missing:
            raise ValueError("D1 migration schema is missing source tables: " + ", ".join(missing))
        for table in sorted(source_tables):
            source_columns = [r[1] for r in source.execute(
                f"PRAGMA table_info({quote_identifier(table)})"
            ).fetchall()]
            target_columns = [r[1] for r in target.execute(
                f"PRAGMA table_info({quote_identifier(table)})"
            ).fetchall()]
            # SQLite column order is not part of the data contract. Desktop
            # upgrades append columns with ALTER TABLE, while the D1 baseline
            # declares the same columns in canonical order. Import statements
            # name every source column explicitly, so require source coverage
            # but safely allow additional target columns with defaults.
            missing_columns = sorted(set(source_columns) - set(target_columns))
            if missing_columns:
                raise ValueError(
                    f"Schema mismatch for {table}; D1 is missing source columns: "
                    + ", ".join(missing_columns)
                )

        output_dir.mkdir(parents=True, exist_ok=True)
        for pattern in ("chunk-*.sql", "chunk-*.json"):
            for old in output_dir.glob(pattern):
                old.unlink()

        chunks: list[Path] = []
        statements: list[str] = []
        chunk_bytes = 0
        counts: dict[str, int] = {}
        chunk_index = 0

        def flush() -> None:
            nonlocal statements, chunk_bytes, chunk_index
            if not statements:
                return
            chunk_index += 1
            path = output_dir / f"chunk-{chunk_index:04d}.sql"
            path.write_text("\n".join(statements) + "\n", encoding="utf-8")
            (output_dir / f"chunk-{chunk_index:04d}.json").write_text(
                json.dumps(statements, ensure_ascii=False), encoding="utf-8"
            )
            chunks.append(path)
            statements = []
            chunk_bytes = 0

        for table in ordered_tables(source):
            columns = [r[1] for r in source.execute(
                f"PRAGMA table_info({quote_identifier(table)})"
            ).fetchall()]
            if not columns:
                continue
            cursor = source.execute(f"SELECT * FROM {quote_identifier(table)}")
            count = 0
            for row in cursor:
                names = ", ".join(quote_identifier(name) for name in columns)
                values = ", ".join(sql_value(value) for value in row)
                statement = (
                    f"INSERT OR REPLACE INTO {quote_identifier(table)} ({names}) "
                    f"VALUES ({values});"
                )
                size = len(statement.encode("utf-8")) + 1
                if statements and (
                    len(statements) >= MAX_CHUNK_STATEMENTS
                    or chunk_bytes + size > MAX_CHUNK_BYTES
                ):
                    flush()
                statements.append(statement)
                chunk_bytes += size
                count += 1
            counts[table] = count
        flush()

        manifest = {
            "format": "raw-strength-d1-import-v1",
            "tables": counts,
            "total_rows": sum(counts.values()),
            "chunks": [path.name for path in chunks],
            "excluded_ephemeral_tables": sorted(EXCLUDED_TABLES & source_tables),
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest
    finally:
        target.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    secret = __import__("os").environ.get("DB_SYNC_ENCRYPTION_SECRET", "").strip()
    if not secret:
        raise SystemExit("DB_SYNC_ENCRYPTION_SECRET is missing from the protected Actions environment.")
    payload = decrypt_snapshot(args.source, secret)
    import tempfile

    with tempfile.NamedTemporaryFile(prefix="rsc_d1_source_", suffix=".db") as handle:
        handle.write(payload)
        handle.flush()
        source = sqlite3.connect(f"file:{handle.name}?mode=ro", uri=True)
        try:
            validate_source(source)
            manifest = build_import(source, args.schema, args.output_dir)
        finally:
            source.close()
    print(json.dumps(manifest, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
