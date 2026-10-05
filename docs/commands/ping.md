# `wparc ping`

Verifies that a WordPress site's REST API is reachable and reports
basic information: the resolved URL, route count.

## Synopsis

```bash
wparc ping <domain> [OPTIONS]
```

## Options

- `-v, --verbose` — debug logging
- `--https / --no-https` — force HTTPS (default: True)
- `--no-verify-ssl` — skip certificate verification (not recommended)
- `--timeout INTEGER` — request timeout in seconds (default: 360)
- `--user / --password` — HTTP Basic Auth
- `--proxy TEXT` — HTTP proxy URL
- `--rate-limit FLOAT` — seconds to sleep between requests

## Exit codes

- `0` — endpoint is reachable
- `1` — domain validation, SSL, or transport error

See [HTTP options](../http-options.md) for the shared flags.