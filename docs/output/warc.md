# WARC export

`wparc warc <domain>` packs every JSONL row into a single WARC 1.1
archive. The resulting file is suitable for the
[`metawarc`][metawarc], [`warc`][warc], and Common Crawl toolchains.

See [the `warc` command reference](../commands/warc.md) for the full
record format and examples.

[metawarc]: https://github.com/webrecorder/warc
[warc]: https://github.com/webrecorder/warc

## When to use it

- Interop with existing web-archiving tooling (WARC is the canonical
  format for crawlers).
- Feeding a dump into processing pipelines that consume WARC (Common
  Crawl derivatives, Internet Archive, etc.).
- Producing a single artefact that's easier to store, share, and
  ingest than thousands of separate JSONL files.

## When **not** to use it

- Random-access queries — the SQLite index is faster.
- Streaming updates — WARC is append-only.

## Reading the WARC from Python

The standard library is enough:

```python
import gzip
with gzip.open("example.warc.gz", "rt", encoding="utf-8") as f:
    while True:
        line = f.readline()
        if not line:
            break
        if line.startswith("WARC-Type: response"):
            # Skip headers; next non-empty chunk is the payload.
            payload = ""
            # (Read until two consecutive CRLF separators, etc.)
            ...
```

Or use the [`warcy`][warcy] or [`warc`][warc] libraries:

[warcy]: https://pypi.org/project/warcy/
[warc]: https://github.com/webrecorder/warc

```python
import warc
with warc.open("example.warc.gz") as f:
    for record in f:
        print(record.url, record.content_type)
        payload = record.payload.read()
        ...
```