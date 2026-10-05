# wparc API reference (auto-generated)

This page is generated from public function and class signatures plus their leading docstring paragraph. Run `python scripts/build_api_doc.py > docs/api/auto.md` to regenerate.

## `wparc`

wparc: WordPress API Crawler and Backup Tool

## `wparc.__main__`

The main entry point. Invoke as `wparc` or `python -m wparc`.

| Name | Signature | Description |
|---|---|---|
| `main` | `()` | Main entry point. |

## `wparc.cmds`

Command modules for wparc.

## `wparc.core`

WordPress API crawler CLI module.

| Name | Signature | Description |
|---|---|---|
| `analyze` | `(domain=<argumentinfo>, verbose=<optioninfo>, https=<optioninfo>, no_verify_ssl=<optioninfo>, timeout=<optioninfo>, user=<optioninfo>, password=<optioninfo>, proxy=<optioninfo>, rate_limit=<optioninfo>)` | Analyze WordPress API routes and compare against known routes. |
| `dump` | `(domain=<argumentinfo>, verbose=<optioninfo>, all_routes=<optioninfo>, https=<optioninfo>, no_verify_ssl=<optioninfo>, timeout=<optioninfo>, page_size=<optioninfo>, retry_count=<optioninfo>, user=<optioninfo>, password=<optioninfo>, proxy=<optioninfo>, rate_limit=<optioninfo>, index_db=<optioninfo>, workers=<optioninfo>)` | Dump WordPress data from API. |
| `getfiles` | `(domain=<argumentinfo>, verbose=<optioninfo>, no_verify_ssl=<optioninfo>, workers=<optioninfo>, no_resume=<optioninfo>)` | Download all media files listed in wp_v2_media.jsonl. |
| `handle_cli_errors` | `(func)` | Decorator that converts uncaught exceptions into a CLI-friendly exit. |
| `index` | `(domain=<argumentinfo>, verbose=<optioninfo>)` | Build a SQLite index from a previous dump. |
| `ping` | `(domain=<argumentinfo>, verbose=<optioninfo>, https=<optioninfo>, no_verify_ssl=<optioninfo>, timeout=<optioninfo>, user=<optioninfo>, password=<optioninfo>, proxy=<optioninfo>, rate_limit=<optioninfo>)` | Ping WordPress API endpoint to verify it's accessible. |
| `warc` | `(domain=<argumentinfo>, verbose=<optioninfo>, output=<optioninfo>, no_compress=<optioninfo>)` | Export a previous dump to a WARC archive. |

## `wparc.data`

Data package for wparc.

## `wparc.exceptions`

Custom exceptions for wparc.

| Name | Signature | Description |
|---|---|---|
| `APIError` | `(url, status_code=None, message=None)` | Raised when WordPress API request fails. |
| `CheckpointError` | `(message)` | Raised when checkpoint operations fail. |
| `DomainValidationError` | `(domain, reason='Invalid domain format')` | Raised when domain name validation fails. |
| `FileDownloadError` | `(url, reason=None)` | Raised when file download fails. |
| `MediaFileNotFoundError` | `(filepath)` | Raised when media file list is not found. |
| `SSLVerificationError` | `(url, reason=None)` | Raised when SSL verification fails. |
| `WparcException` | `` | Base exception for all wparc errors. |

## `wparc.utils`

Utility functions for wparc.

| Name | Signature | Description |
|---|---|---|
| `format_bytes` | `(bytes_count)` | Format bytes count as human-readable string. |
| `format_duration` | `(seconds)` | Format duration in seconds as human-readable string. |
| `validate_domain` | `(domain)` | Validate and normalize a domain name. |

## `wparc.wpapi`
