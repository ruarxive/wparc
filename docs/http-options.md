# HTTP options

`ping`, `dump`, `analyze` accept a shared set of HTTP flags. They are
threaded through every wpapi function as plain Python parameters.

| Flag | Type | Default | Effect |
|---|---|---|---|
| `--https / --no-https` | bool | `True` | Force HTTPS for the API root |
| `--no-verify-ssl` | bool | `False` | Skip TLS certificate validation |
| `--timeout` | int | 360 | Per-request timeout in seconds |
| `--user` | str | `None` | HTTP Basic Auth username |
| `--password` | str | `None` | HTTP Basic Auth password |
| `--proxy` | str | `None` | HTTP proxy URL, e.g. `http://127.0.0.1:8080` |
| `--rate-limit` | float | 0.0 | Seconds to sleep between requests |

`dump`, `analyze`, and `ping` also accept these; `getfiles` and
`warc` only consume a subset.

## Programmatic usage

The same options are exposed as :class:`wparc.cmds.extractor.HttpOptions`:

```python
from wparc.cmds.extractor import HttpOptions, Project

project = Project(
    verify_ssl=True,
    http_options=HttpOptions(
        username="bob",
        password="hunter2",
        proxy="http://127.0.0.1:8080",
        rate_limit_delay=0.5,
    ),
)
project.dump("example.com", all_routes=True, https=True)
```

## Security notes

- `--user/--password` put credentials in the process argv; they are
  visible to other local users via `/proc/<pid>/cmdline`. Prefer
  environment variables in production.
- `--no-verify-ssl` disables certificate checks; treat as unsafe on
  untrusted networks.
- `--proxy` accepts any URL the underlying HTTP library supports;
  ensure the URL is `http://` or `https://` as appropriate.