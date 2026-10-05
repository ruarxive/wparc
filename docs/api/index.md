# API reference

The Python API is intentionally flat. The typical entry point is
:class:`wparc.cmds.extractor.Project`:

```python
from wparc.cmds.extractor import Project, HttpOptions

project = Project(http_options=HttpOptions(rate_limit_delay=0.5))
project.ping("example.com", https=True)
project.dump("example.com", all_routes=True, https=True, workers=4)
project.getfiles("example.com", workers=10)
project.analyze("example.com", https=True)
```

For lower-level access, the `wparc.wpapi` package re-exports the
helper functions:

```python
from wparc.wpapi import (
    ping, collect_data, collect_files, analyze_routes,
    test_unknown_routes, generate_routes_yaml, get_file,
    read_media_urls, get_self_url, get_resource_filename,
)
```

## Sub-modules

| Module | Purpose |
|---|---|
| `wparc.wpapi.dump` | Dumping WP REST endpoints to JSONL |
| `wparc.wpapi.routes` | Route analysis / categorisation |
| `wparc.wpapi.media` | Media downloads + checkpointing |
| `wparc.wpapi.download` | Low-level file download |
| `wparc.wpapi.resources` | Package-resource helper (wraps importlib.resources) |
| `wparc.wpapi.index.sqlite_index` | Build a SQLite index over a dump |
| `wparc.wpapi.warc.writer` | WARC 1.1 export |
| `wparc.wpapi._common` | Shared constants and helpers |

## Exceptions

All wparc-specific exceptions inherit from `wparc.exceptions.APIError`:

| Class | When raised |
|---|---|
| `DomainValidationError` | Domain input fails validation |
| `APIError` | HTTP error or invalid JSON |
| `SSLVerificationError` | SSL handshake fails with `verify_ssl=True` |
| `MediaFileNotFoundError` | The dump did not contain a media file list |
| `CheckpointError` | Reading or writing the download checkpoint fails |
| `FileDownloadError` | Individual file download fails (see `FileDownloadError.__init__` for `Suggestion:` text) |

## Public dataclass

```python
@dataclass
class HttpOptions:
    username: Optional[str] = None
    password: Optional[str] = None
    proxy: Optional[str] = None
    rate_limit_delay: float = 0.0
```