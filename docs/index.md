# wparc

WordPress API crawler and backup tool — back up the public data of any
WordPress site through its REST API, no DB access required.

## Why wparc?

Most WordPress backup tools assume you have database or FTP access.
wparc only needs the site URL: it walks `/wp-json/`, paginates each
endpoint, and writes JSONL you can search, index, or replay.

## What's in v1.0.8

- **Parallel dumping** via `--workers N` (threaded route fetching).
- **SQLite index** of the dump for ad-hoc queries.
- **WARC export** compatible with `metawarc`, `warc`, Common Crawl.
- **HTTP Basic Auth**, **proxy**, and **rate-limit** support.
- **Exponential backoff** retries on transient network errors.
- Connection pooling through `requests.Session`.
- ~82 % test coverage with 169 tests.

## Next steps

- [Installation](install.md)
- [Quick start](quickstart.md)
- [Commands](commands/index.md)