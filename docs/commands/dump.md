# `wparc dump`

Extracts all public data from a WordPress site's REST API into
`<domain>/data/*.jsonl`. One JSON object per line.

## Synopsis

```bash
wparc dump <domain> [OPTIONS]
```

## Options

- `-v, --verbose` — debug logging
- `-a / --all / --no-all` — include unknown API routes (default: True)
- `--https / --no-https` — force HTTPS (default: True)
- `--no-verify-ssl` — skip certificate verification
- `--timeout INTEGER` — request timeout in seconds (default: 360)
- `--page-size INTEGER` — items per page (default: 100)
- `--retry-count INTEGER` — retries for failed requests (default: 5)
- `-w / --workers INTEGER` — parallel route fetches (default: 1)
- `--user / --password` — HTTP Basic Auth
- `--proxy TEXT` — HTTP proxy URL
- `--rate-limit FLOAT` — seconds between requests
- `--index` — also build `<domain>/index.sqlite3` after dumping

## Performance

For big sites, prefer `--workers 4` (or higher). The WordPress REST
API is I/O-bound so threading scales well; values above 8 rarely help
and may anger the WordPress server.

## Examples

```bash
# Standard dump
wparc dump example.com

# Parallel + index
wparc dump example.com --workers 4 --index

# Protected endpoint with HTTP Basic Auth
wparc dump example.com --user bob --password secret

# Behind a corporate proxy
wparc dump example.com --proxy http://proxy.corp:8080
```

See [HTTP options](../http-options.md) for the shared flags.