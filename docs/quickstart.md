# Quick start

A typical workflow for backing up a WordPress site:

```bash
# 1. Verify the REST API is reachable
wparc ping example.com

# 2. (Optional) Inspect available routes
wparc analyze example.com --verbose

# 3. Dump everything to JSONL
wparc dump example.com --verbose --workers 4

# 4. Download media files referenced by the dump
wparc getfiles example.com --verbose

# 5. Build a SQLite index for fast queries
wparc index example.com

# 6. Export to WARC for the metawarc / warc ecosystem
wparc warc example.com --output example.warc.gz
```

## Resulting layout

```
example.com/
├── data/
│   ├── wp_v2_posts.jsonl
│   ├── wp_v2_pages.jsonl
│   ├── wp_v2_media.jsonl
│   ├── …
│   └── wp-json.json
├── files/
│   └── wp-content/uploads/…
├── index.sqlite3     # after `wparc index`
└── example.warc.gz    # after `wparc warc`
```

## What's next?

- [Index command](commands/index.md) — SQLite indexing details.
- [WARC command](commands/warc.md) — archive export details.
- [HTTP options](http-options.md) — auth, proxy, rate-limit.