# `wparc analyze`

Compares discovered WordPress API routes against the bundled
`known_routes.yml` catalogue, identifies unknown routes, automatically
probes them, and prints a ready-to-use YAML snippet for adding to the
catalogue.

## Synopsis

```bash
wparc analyze <domain> [OPTIONS]
```

## Options

- `-v, --verbose` — debug logging and per-route listing
- `--https / --no-https` — force HTTPS
- `--no-verify-ssl` — skip certificate verification
- `--timeout INTEGER` — request timeout in seconds (default: 360)
- `--user / --password` — HTTP Basic Auth
- `--proxy TEXT` — HTTP proxy URL
- `--rate-limit FLOAT` — seconds between probes

## Route categories

| Category | Meaning |
|---|---|
| `protected` | Endpoint requires authentication (401/403) |
| `public-list` | Returns paginated array of items (posts, comments) |
| `public-dict` | Returns a single object (settings, site info) |
| `useless` | Regex/single-item endpoints (e.g. `/wp/v2/posts/123`) |
| `unknown` | Not in `known_routes.yml`; probed automatically |

## Output

The command prints:

1. Statistics (count per category).
2. A list of unknown routes (when `-v`).
3. Categorisation of those unknowns.
4. A YAML snippet ready to paste into `wparc/data/known_routes.yml`.

See [HTTP options](../http-options.md) for the shared flags.