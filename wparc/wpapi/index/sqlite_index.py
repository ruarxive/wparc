# -*- coding: utf-8 -*-
"""
SQLite index builder for wparc dumps.

Reads every ``*.jsonl`` file under ``<domain>/data/`` (each line is one
JSON object) and writes the union of all rows into a single SQLite
database. Common WordPress keys (``id``, ``slug``, ``title``, ``date``)
get dedicated columns; every other top-level key is stored as JSON text
in the ``extras`` column, so no information is lost.

The schema is created on first run and idempotent: re-running the
indexer overwrites existing rows in-place.
"""
import json
import logging
import os
import sqlite3
from typing import Dict, Iterable, Optional

DEFAULT_DB_FILENAME = "index.sqlite3"
DEFAULT_DATA_SUBDIR = "data"
DEFAULT_JSONL_EXT = ".jsonl"

# Columns promoted out of the generic JSON bag. The first three are the
# most useful for queries; the rest are commonly referenced by WordPress
# themes and plugins.
PROMOTED_KEYS = (
    "id",
    "slug",
    "date",
    "date_gmt",
    "modified",
    "modified_gmt",
    "status",
    "link",
    "title",
    "type",
    "author",
    "parent",
)


def _table_columns() -> Iterable[str]:
    """Yield the DDL column list shared by the index schema and inserts."""
    yield "rowid INTEGER PRIMARY KEY AUTOINCREMENT"
    for key in PROMOTED_KEYS:
        # All promoted columns are TEXT so we can store both numeric ids
        # and string slugs in the same column.
        yield f"{key} TEXT"
    yield "source_file TEXT NOT NULL"
    yield "extras TEXT NOT NULL"


def _connect(db_path: str) -> sqlite3.Connection:
    # ``journal_mode=DELETE`` (the default) is used here instead of WAL
    # so that callers opening the database from a separate process see
    # every committed row. WAL would buffer changes in a sidecar file
    # and only flush them at checkpoint time, which is a confusing
    # behaviour for a dump-time index.
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    columns = ", ".join(_table_columns())
    conn.execute(f"CREATE TABLE IF NOT EXISTS records ({columns})")
    conn.execute("CREATE INDEX IF NOT EXISTS records_id_idx ON records(id)")
    conn.execute("CREATE INDEX IF NOT EXISTS records_date_idx ON records(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS records_source_idx ON records(source_file)")


def _coerce(value) -> Optional[str]:
    """Best-effort string coercion for promoted columns."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        # WP wraps ``title`` and similar in ``{"rendered": "..."}``.
        rendered = value.get("rendered")
        if rendered is not None:
            return str(rendered)
    return str(value)


def _row_for(source_file: str, record: Dict) -> tuple:
    """Build a tuple matching the table's column order."""
    out = []
    for key in PROMOTED_KEYS:
        out.append(_coerce(record.get(key)))
    extras = {k: v for k, v in record.items() if k not in PROMOTED_KEYS}
    out.append(source_file)
    out.append(json.dumps(extras, ensure_ascii=False))
    return tuple(out)


def build_index(
    domain: str,
    db_filename: str = DEFAULT_DB_FILENAME,
    data_subdir: str = DEFAULT_DATA_SUBDIR,
    jsonl_ext: str = DEFAULT_JSONL_EXT,
) -> Dict[str, int]:
    """Index all ``*jsonl`` files under ``<domain>/<data_subdir>/``.

    Args:
        domain: Path used as the wparc output directory.
        db_filename: SQLite database filename (created in ``domain/``).
        data_subdir: Subdirectory holding the JSONL dumps.
        jsonl_ext: File extension to scan.

    Returns:
        ``{"files": int, "records": int, "db_path": str}``
    """
    data_dir = os.path.join(domain, data_subdir)
    db_path = os.path.join(domain, db_filename)

    if not os.path.isdir(data_dir):
        raise FileNotFoundError(
            f"Data directory not found: {data_dir}. " "Run `wparc dump <domain>` first."
        )

    conn = _connect(db_path)
    try:
        _ensure_schema(conn)
        files_indexed = 0
        records_indexed = 0

        for filename in sorted(os.listdir(data_dir)):
            if not filename.endswith(jsonl_ext):
                continue
            source_file = os.path.join(data_dir, filename)
            files_indexed += 1
            with open(source_file, "r", encoding="utf8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        logging.warning(f"Skipping malformed JSON in {source_file}: {exc}")
                        continue
                    if not isinstance(record, dict):
                        # JSONL may contain scalars for some endpoints;
                        # index them as JSON in ``extras`` and leave
                        # promoted columns NULL.
                        record = {"value": record}
                    conn.execute(
                        "INSERT INTO records VALUES (NULL, "
                        + ", ".join("?" for _ in range(len(PROMOTED_KEYS) + 2))
                        + ")",
                        _row_for(source_file, record),
                    )
                    records_indexed += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "files": files_indexed,
        "records": records_indexed,
        "db_path": db_path,
    }
