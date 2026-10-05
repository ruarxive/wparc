# SQLite index

`wparc index <domain>` produces a single-file SQLite database over the
dump. Useful when the JSONL files get large (gigabytes) and you want
to query without parsing JSON on every search.

See [the `index` command reference](../commands/index.md) for the
schema and example queries.

## When to use it

- 10⁴+ records — JSONL `grep` is slow because every record needs to be
  parsed.
- You want to expose the dump as an API or feed it into a notebook.
- You need to deduplicate records across endpoints (e.g. find posts
  with the same `slug` in `/wp/v2/pages` and `/wp/v2/posts`).

## When **not** to use it

- Small dumps — the indexer still copies every record, so on 100-row
  dumps it costs more than it saves.
- Streams — the SQLite database is monolithic; for streaming analyses
  use the raw JSONL.

## Reading the index from Python

```python
import sqlite3
conn = sqlite3.connect("example.com/index.sqlite3")
for row in conn.execute(
    "SELECT id, slug, date FROM records WHERE date IS NOT NULL"
):
    print(row)
conn.close()
```