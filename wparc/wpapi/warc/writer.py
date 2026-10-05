# -*- coding: utf-8 -*-
"""
WARC export for wparc dumps.

This module converts the JSONL dumps produced by :mod:`wparc.wpapi.dump`
into a single WARC (``application/warc``) or WARC.gz archive, one
``response`` record per JSONL row.

The WARC version used is 1.1, which is the format consumed by the
``metawarc`` and ``warc`` Python libraries as well as by the Common
Crawl processing pipeline.

The implementation deliberately uses only the Python standard library
so that no third-party WARC library is required.

Headers are constructed deterministically:
- ``WARC-Type``: ``response``
- ``WARC-Target-URI``: ``{source_file}#{row_id}``  (or slug if id absent)
- ``Content-Type``: ``application/json; charset=utf-8``
- ``Content-Length``: byte length of the JSON payload
"""
import datetime
import gzip
import json
import logging
import os
from typing import Dict, Optional, Tuple

DEFAULT_FILENAME = "dump.warc.gz"
DEFAULT_DATA_SUBDIR = "data"
DEFAULT_JSONL_EXT = ".jsonl"

WARC_VERSION = "WARC/1.0"
CRLF = b"\r\n"


def _warc_date(now: Optional[datetime.datetime] = None) -> str:
    """Format a UTC timestamp in the WARC-Date profile."""
    ts = now or datetime.datetime.now(datetime.timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _open_output(path: str, compress: bool):
    """Return a text-mode write handle, optionally wrapped in gzip."""
    if compress:
        return gzip.open(path, "wt", encoding="utf-8")
    return open(path, "w", encoding="utf-8")


def _record_id(prefix: str, source_file: str, row_id) -> str:
    """Build a deterministic WARC-Record-ID string."""
    return f"<{prefix}:{os.path.basename(source_file)}:{row_id}>"


def _target_uri(source_file: str, record: Dict) -> str:
    """Return a human-meaningful URI for the record."""
    rid = record.get("id")
    if rid is not None:
        suffix = str(rid)
    else:
        suffix = record.get("slug") or "unknown"
    return f"{os.path.basename(source_file)}#{suffix}"


def _build_headers(
    source_file: str,
    record: Dict,
    payload: bytes,
) -> Tuple[bytes, bytes]:
    """Return ``(head_bytes, block_separator)`` for one WARC record."""
    warc_date = _warc_date()
    record_id = _record_id("wparc", source_file, record.get("id", "noid"))
    target_uri = _target_uri(source_file, record)

    headers = [
        WARC_VERSION.encode(),
        b"WARC-Type: response",
        f"WARC-Date: {warc_date}".encode(),
        f"WARC-Record-ID: {record_id}".encode(),
        f"WARC-Target-URI: {target_uri}".encode(),
        b"Content-Type: application/json; charset=utf-8",
        f"Content-Length: {len(payload)}".encode(),
    ]
    head = CRLF.join(headers) + CRLF + CRLF
    return head, payload


def _iter_records(domain: str, data_subdir: str, jsonl_ext: str):
    """Yield ``(source_path, record)`` tuples from the dump directory."""
    data_dir = os.path.join(domain, data_subdir)
    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith(jsonl_ext):
            continue
        source_path = os.path.join(data_dir, filename)
        with open(source_path, "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield source_path, json.loads(line)
                except json.JSONDecodeError as exc:
                    logging.warning(f"Skipping malformed JSON in {source_path}: {exc}")


def _write_record(stream, source_file: str, record) -> None:
    """Serialize a single record into ``stream``.

    Falls back to wrapping non-dict scalars under ``{"value": ...}``
    so the JSON encoder always succeeds.
    """
    if not isinstance(record, dict):
        record = {"value": record}
    payload = json.dumps(record, ensure_ascii=False).encode("utf-8")
    head, payload = _build_headers(source_file, record, payload)
    stream.buffer.write(head)
    stream.buffer.write(payload)
    stream.buffer.write(CRLF + CRLF)


def export_warc(
    domain: str,
    output_filename: str = DEFAULT_FILENAME,
    data_subdir: str = DEFAULT_DATA_SUBDIR,
    jsonl_ext: str = DEFAULT_JSONL_EXT,
    compress: bool = True,
) -> Dict[str, int]:
    """Export all ``*.jsonl`` files under ``<domain>/<data_subdir>/`` to WARC.

    Args:
        domain: Path used as the wparc output directory.
        output_filename: Destination filename (``.warc`` or ``.warc.gz``).
        data_subdir: Subdirectory holding the JSONL dumps.
        jsonl_ext: File extension to scan.
        compress: When True (default), write gzipped WARC. Set False to
            produce an uncompressed ``.warc`` file.

    Returns:
        ``{"records": int, "output_path": str}``
    """
    data_dir = os.path.join(domain, data_subdir)
    output_path = os.path.join(domain, output_filename)

    if not os.path.isdir(data_dir):
        raise FileNotFoundError(
            f"Data directory not found: {data_dir}. " "Run `wparc dump <domain>` first."
        )

    opener = _open_output
    record_count = 0

    with opener(output_path, compress) as stream:
        # First write a WARC info record.
        info = {
            "software": "wparc",
            "format": "WARC File Format 1.1",
            "description": (f"WARC export of wparc dump under {domain}"),
        }
        payload = json.dumps(info).encode("utf-8")
        info_headers = [
            WARC_VERSION.encode(),
            b"WARC-Type: warcinfo",
            f"WARC-Date: {_warc_date()}".encode(),
            b"WARC-Filename: " + output_filename.encode("utf-8"),
            b"Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(payload)}".encode(),
        ]
        stream.buffer.write(CRLF.join(info_headers) + CRLF + CRLF)
        stream.buffer.write(payload)
        stream.buffer.write(CRLF + CRLF)

        for source_path, record in _iter_records(domain, data_subdir, jsonl_ext):
            _write_record(stream, source_path, record)
            record_count += 1

    return {"records": record_count, "output_path": output_path}
