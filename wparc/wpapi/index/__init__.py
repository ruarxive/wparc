"""SQLite indexing for wparc dumps.

Provides :func:`build_index` which scans ``<domain>/data/*.jsonl`` and
writes a single ``index.sqlite3`` database with a ``records`` table that
mirrors the union of all row shapes. This makes post-dump queries
trivially fast (``SELECT ... WHERE id = 123``) and supports browsing the
whole archive without re-parsing the JSONL files.

The module is intentionally tiny and depends only on the Python
standard library so that the index can be built on any environment
where wparc was used to dump.
"""
