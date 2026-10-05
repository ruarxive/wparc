# `wparc getfiles`

Downloads all media files referenced in the dump. Requires
`<domain>/data/wp_v2_media.jsonl` (produced by `wparc dump`).

## Synopsis

```bash
wparc getfiles <domain> [OPTIONS]
```

## Options

- `-v, --verbose` — debug logging
- `--no-verify-ssl` — skip certificate verification
- `-w, --workers INTEGER` — concurrent download workers (default: 5)
- `--no-resume` — re-download files even when a checkpoint already has them

## Checkpointing

The downloader persists progress to `.wparc_checkpoint.json`. By
default subsequent runs skip already-downloaded files. Pass
`--no-resume` to force re-downloading.

## Output

Files land under `<domain>/files/...`, mirroring the original
WordPress directory structure (e.g. `wp-content/uploads/2024/01/`).

## Examples

```bash
# Standard
wparc getfiles example.com

# Faster with more workers
wparc getfiles example.com --workers 10

# Force re-download
wparc getfiles example.com --no-resume
```