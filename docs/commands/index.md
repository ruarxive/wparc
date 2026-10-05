# `wparc index`

Builds a SQLite database (`<domain>/index.sqlite3`) over the JSONL
files in `<domain>/data/`. Each JSONL row becomes a row in a single
`records` table.

## Synopsis

```bash
wparc index <domain> [-v]
```

You can also build the index as part of dumping:

```bash
wparc dump example.com --index
```

## Schema

```sql
CREATE TABLE records (
    rowid           INTEGER PRIMARY KEY AUTOINCREMENT,
    id              TEXT,
    slug            TEXT,
    date            TEXT,
    date_gmt        TEXT,
    modified        TEXT,
    modified_gmt    TEXT,
    status          TEXT,
    link            TEXT,
    title           TEXT,
    type            TEXT,
    author          TEXT,
    parent          TEXT,
    source_file     TEXT NOT NULL,
    extras          TEXT NOT NULL
);
```

All values are stored as TEXT — id columns are stringified so numeric
ids and string slugs live side-by-side. Any key not in the promoted
list above is JSON-encoded into `extras`.

Indexes are created on `id`, `date`, and `source_file`.

## Example queries

```bash
# Find a specific post by id
sqlite3 example.com/index.sqlite3 \
    "SELECT id, slug, source_file FROM records WHERE id='42'"

# Top 10 most recent posts
sqlite3 example.com/index.sqlite3 \
    "SELECT id, slug, date FROM records WHERE date IS NOT NULL ORDER BY date DESC LIMIT 10"

# All extras for a record
sqlite3 example.com/index.sqlite3 \
    "SELECT extras FROM records WHERE id='42'"
```

## Programmatically

```python
from wparc.wpapi.index.sqlite_index import build_index

stats = build_index("example.com")
# {"files": 12, "records": 1842, "db_path": "example.com/index.sqlite3"}
```