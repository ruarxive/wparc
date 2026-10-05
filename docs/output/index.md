# Output formats

The default dump produces **JSONL** files (one JSON object per line)
under `<domain>/data/`. Each endpoint becomes a file:

| Endpoint | File |
|---|---|
| `/wp/v2/posts` | `wp_v2_posts.jsonl` |
| `/wp/v2/pages` | `wp_v2_pages.jsonl` |
| `/wp/v2/media` | `wp_v2_media.jsonl` |
| `/wp/v2/types` | `wp_v2_types.json` |
| `/wp-json/` root | `wp-json.json` |

Two **post-processing** tools turn the JSONL dump into formats that
are easier to consume downstream:

- [SQLite](sqlite.md) — `wparc index <domain>` builds `index.sqlite3`
  for fast SQL queries.
- [WARC](warc.md) — `wparc warc <domain>` builds a WARC 1.1 archive
  for the `metawarc` / Common Crawl pipelines.

## Programmatic access

```python
# Read the raw JSONL
import json
with open("example.com/data/wp_v2_posts.jsonl") as f:
    for line in f:
        post = json.loads(line)
        ...

# Or use the indexer directly
from wparc.wpapi.index.sqlite_index import build_index
stats = build_index("example.com")
```