"""WARC export for wparc dumps.

The :mod:`wparc.wpapi.warc.writer` module converts a ``<domain>/data/``
directory of JSONL files into a single WARC archive (``*.warc.gz``)
suitable for ingestion by the ``metawarc``, ``warc`` or Common Crawl
toolchains.

The export uses only the standard library; no third-party WARC library
is required. Records are emitted as ``response`` entries, one per JSONL
row, with a synthetic HTTP/1.1 envelope that mirrors the row's id and
``link``/``slug`` fields.
"""
