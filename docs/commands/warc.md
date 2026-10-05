# `wparc warc`

Exports a previous dump (`<domain>/data/*.jsonl`) to a WARC 1.1
archive. The resulting file is compatible with the
[`metawarc`][metawarc], [`warc`][warc] and Common Crawl toolchains.

[metawarc]: https://github.com/python/monopolio
[warc]: https://github.com/webrecorder/warc

## Synopsis

```bash
wparc warc <domain> [--output FILE] [--no-compress] [-v]
```

## Options

- `-v, --verbose` — debug logging
- `-o, --output TEXT` — destination filename (default: `dump.warc.gz`)
- `--no-compress` — produce an uncompressed `.warc` (use when CPU is
  scarce or when you want to pipe the file through another tool)

## Record format

The exporter writes a single `warcinfo` record followed by one
`response` record per JSONL row.

| Header | Example value |
|---|---|
| `WARC-Type` | `warcinfo` (first) then `response` |
| `WARC-Target-URI` | `<source_file>#<id>` or `<source_file>#<slug>` |
| `Content-Type` | `application/json; charset=utf-8` |
| `Content-Length` | byte length of the JSON payload |

The full WordPress object lives in the payload as JSON text.

## Examples

```bash
# Default: gzipped
wparc warc example.com

# Custom name
wparc warc example.com --output backup.warc.gz

# Uncompressed (faster, larger)
wparc warc example.com --no-compress --output backup.warc
```