# Contributing to wparc

Thank you for your interest in contributing to **wparc** — the WordPress
API crawler and backup tool. This document explains how to set up a
development environment, run the test suite, and submit changes.

## Code of Conduct

This project follows the [Contributor Covenant][covenant]. By
participating you agree to abide by its terms.

[covenant]: https://www.contributor-covenant.org/

## Development Setup

wparc targets **Python 3.8+**. A clean checkout, virtualenv, and the
`dev` extras are enough to get started:

```bash
git clone https://github.com/ruarxive/wparc.git
cd wparc
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running the Tests

The full test suite is plain `pytest`:

```bash
pytest
pytest --cov=wparc --cov-report=term-missing
```

The current coverage is **~80 %**; please add tests for new code.
Coverage gates per-module are not enforced, but please try to keep
new modules above 70 %.

## Code Style

- **Format** with [black](https://black.readthedocs.io) at line-length 100.
- **Lint** with `flake8 --max-line-length=100`.
- **Type-check** with `mypy --ignore-missing-imports`.

All three are enforced in CI.

```bash
black wparc/ tests/
flake8 wparc/ tests/ --max-line-length=100
mypy wparc/ --ignore-missing-imports
```

## Project Layout

```
wparc/
├── __init__.py
├── __main__.py            # python -m wparc entry point
├── core.py                # Typer CLI commands
├── cmds/extractor.py      # Project wrapper
├── wpapi/                 # HTTP and parsing logic
│   ├── _common.py         # shared helpers (session, progress bar, SSL)
│   ├── dump.py            # route dumping
│   ├── routes.py          # route analysis
│   ├── media.py           # media downloads + checkpoint
│   ├── download.py        # low-level file download
│   ├── resources.py       # package resource helpers
│   └── index/             # SQLite indexer
│   └── warc/              # WARC exporter
├── utils.py               # domain validation
├── exceptions.py          # exception hierarchy
└── data/known_routes.yml  # route catalogue
```

## Submitting Changes

1. Fork the repo and create a topic branch:
   ```bash
   git checkout -b fix/your-bug-name
   ```
2. Make your change with tests.
4. Run the full test/lint suite locally.
5. Open a pull request describing:
   - what the change does,
   - which issue it fixes (if any),
   - how it was tested.

CI must be green before review.

## Reporting Security Issues

**Please do not file public issues for security bugs.** Email the
maintainer (see `SECURITY.md`) with details and reproduction steps.