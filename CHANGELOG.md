# Changelog

All notable changes to this project will be documented in this file.

## 1.0.9 (2026-10-05)

### Added
- **SQLite indexer** (`wparc index <domain>`): builds a single-table
  SQLite database over a previous dump, with promoted columns for
  WordPress keys (`id`, `slug`, `date`, `modified`, `status`, `link`,
  `title`, `type`, `author`, `parent`) and an `extras` JSON column
  for everything else. `--index` flag on `wparc dump` builds the
  index in-line.
- **WARC 1.1 export** (`wparc warc <domain>`): produces a
  gzipped-by-default WARC archive compatible with `metawarc`, `warc`,
  and the Common Crawl pipeline. CLI flag `--no-compress` for
  uncompressed output.
- **Parallel route dumping** (`wparc dump --workers N`): routes are
  fetched concurrently via `ThreadPoolExecutor`; `--workers 1`
  (default) keeps the original serial behaviour.
- **HTTP Basic Auth** (`--user` / `--password`): threaded through
  every wpapi function (`ping`, `dump`, `analyze`, `_test_route`).
- **HTTP proxy** (`--proxy`): threads through all wpapi functions.
- **Rate-limit** (`--rate-limit`): seconds to sleep between requests.
- **Exponential backoff** in `dump_route_list`: `min(2^rc * 0.25, 8)` s
  between retries (capped at 8 s).
- **API doc script** (`make_api_doc.py`): generates a Markdown API
  reference from docstrings.
- **MkDocs** configuration (`mkdocs.yml`) and `docs/` directory with
  command-by-command pages.

### Performance
- Added `lru_cache(maxsize=1)` wrapper around `known_routes.yml`
  loading (saves ~100 ms per `dump`/`analyze` call).
- Replaced duplicated `requests.get(...)` calls with shared constants
  in `wparc.wpapi._common`: `USER_AGENT`, `DEFAULT_TIMEOUT`,
  `DEFAULT_CHUNK_SIZE`, `REQUEST_HEADER` (now immutable).
- `make_session()` factory with `HTTPAdapter` and `Retry` policy
  available for future connection-pool use.

### Changed
- **DRY refactor**: all duplicated `_TqdmFallback`, `tqdm`,
  `urllib3_warnings_suppressed`, `_get_ssl_warning_context`,
  `USER_AGENT` strings (4 modules) consolidated into
  `wparc/wpapi/_common.py`.
- CLI error-handling consolidated into a single `handle_cli_errors`
  decorator (`wparc/core.py`).
- `dump_route_dict` now returns `bool` instead of raising (failures
  are logged + counted as `routes_skipped`).
- `dump_route_list` now returns `bool` (True if any rows were written).
- `_handle_unknown_route` extracted from `collect_data` for clarity.
- `_is_paginated_endpoint` extracted as a reusable helper.
- `_load_known_routes` extracted as a module-level helper in
  `routes.py`; `dump.py` reuses the cached value instead of
  re-parsing YAML.
- `Project.dump`/`getfiles`/`ping`/`analyze` accept an optional
  `HttpOptions` dataclass.
- `Project.getfiles(workers=N, resume=...)` exposes the parallel
  download knob.

### Fixed
- `_partial_downloaded files are removed on failure
  (`get_file` now calls `_remove_partial()` in every except branch).
- `CheckpointError` and `FileDownloadError` are now actually raised
  by their intended call sites (`save_checkpoint` and
  `_download_file_task` respectively).
- Corrupt checkpoint JSON is moved aside (`.wparc_checkpoint.json.corrupt`)
  and a fresh in-memory checkpoint is loaded.
- `urllib3.enable_warnings()` (removed in urllib3 v2) is now called
  defensively only if available.
- `validate_domain` uses `ipaddress.ip_address()` for strict IPv4/IPv6
  validation; previously the regex accepted `:::::` and `999.999.999.999`.
- `_version` drift between `pyproject.toml` and `wparc/__init__.py`
  (both now at `1.0.8`).
- CLI removed `add_completion=True` (was completing in shells; not
  useful for a sub-process CLI).
- `__licence__` typo → `__license__`.
- Black `[tool.black] target-version` mismatch with `requires-python`.
- `lxml` removed from `requirements.txt` and `dependencies` (was
  unused).

### Security
- `User-Agent` unified to a single immutable constant (was duplicated
  in 6 modules).
- `REQUEST_HEADER` wrapped in `MappingProxyType` to prevent accidental
  mutation.
- Default `--no-verify-ssl` no longer suppresses warnings globally.

### Documentation
- `CONTRIBUTING.md`, `SECURITY.md` added.
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request,question}.md`
  and `.github/PULL_REQUEST_TEMPLATE.md` added.
- Full MkDocs site under `docs/` with command-by-command reference.

### Tests
- **185 tests** (up from 33); **82 % line coverage** (up from 42 %).
- `wparc.core` coverage 69 % → **74 %** (new flag-driven tests).
- New modules with full coverage:
  `wparc.wpapi.index.sqlite_index` (95 %), `wparc.wpapi.warc.writer`
  (97 %), `wparc.cmds.extractor` (100 %).
- **+9 CLI tests** in `tests/test_cli.py` covering `--workers`, `--index`,
  `--user/--password/--proxy/--rate-limit`, `--no-resume`, the new
  `index` and `warc` commands, and the `handle_cli_errors` decorator.
- **+7 tests** for `scripts/build_api_doc.py` covering the script
  runner, signature rendering, Typer defaults collapse, and the
  re-export filter.

### Infrastructure
- **CI workflow** (`/.github/workflows/test.yml`) expanded from 3 to
  5 jobs: cross-platform pytest with **coverage gate 75 %**,
  flake8+black, mypy, MkDocs `--strict` build, and a CLI smoke-test
  that exercises `python -m wparc <command> --help` for every
  command.
- **`pyproject.toml`** gained a `docs` extra (`mkdocs>=1.5`,
  `mkdocs-material>=9.4`) for docs-only installs.
- Old analysis documents (`dev/docs/*.md`) moved to
  `docs/dev-history/` and integrated into the MkDocs navigation
  as a historical section.

## 1.0.8 (2026-07-16)

### Security
- Replaced `yaml.load()` with `yaml.safe_load()` to prevent arbitrary code execution from malformed route files
- SSL certificate warnings now only suppressed when `--no-verify-ssl` is explicitly used (previously disabled globally at import time)

### Changed
- Split monolithic `crawler.py` (1200+ lines) into 5 focused modules: `resources`, `download`, `media`, `routes`, `dump`
- Converted route lookups from lists to sets for O(1) membership testing performance
- Migrated to `pyproject.toml`-only build system; removed `setup.py` and `setup.cfg`
- Updated minimum Python version to 3.8 in `pyproject.toml`
- Removed duplicate `main()` entry point; consolidated to `__main__.py` only
- Updated `tox.ini` with correct test paths and modern Python versions
- Updated `requirements-dev.txt` with all development dependencies (black, flake8, mypy, pytest-cov, type stubs)

### Added
- CLI integration tests using `typer.testing.CliRunner` (33 total tests, up from 26)
- `black` code formatting configuration (line-length=100)
- `flake8` linting configuration
- `mypy` type checking with `types-PyYAML` and `types-requests` stubs
- Project structure documentation in README

### Fixed
- Fixed `KeyError` when `known_routes.yml` is missing category keys (now uses `.get()` with safe defaults)
- Fixed broken `TestCollectData` test that referenced removed `pkg_resources` module attribute
- Fixed `.coveragerc` targeting wrong package name (`metawarc` → `wparc`)
- Fixed all flake8 issues: trailing whitespace, line-too-long, unused imports, missing blank lines
- Fixed all mypy errors: `union-attr` on nullable responses, missing type annotations

## 1.0.7 (2025-12-16)

### Added
- Enhanced `analyze` command with automatic route testing and categorization
- Automatic YAML generation for unknown routes to update `known_routes.yml`
- Custom exception classes (`DomainValidationError`, `APIError`, `SSLVerificationError`, `FileDownloadError`, `MediaFileNotFoundError`, `CheckpointError`) for better error handling
- Domain validation utility function with comprehensive validation rules
- Utility functions for formatting bytes and duration (`format_bytes`, `format_duration`)
- Comprehensive test suite with tests for exceptions, utilities, and crawler functionality
- GitHub Actions workflow for automated testing
- Better error messages with actionable suggestions for common issues

### Changed
- Improved `analyze` command output with categorized route statistics
- Enhanced error handling in main entry point with KeyboardInterrupt handling
- Better exception messages with context-specific suggestions

### Fixed
- Removed unused `wparc/cmds/__init__.py` file

## 1.0.5 (2024-12-19)

### Fixed
- Fixed setup.py dependencies: replaced 'click' with 'typer'
- Added missing 'requests' and 'urllib3' dependencies to install_requires

## 1.0.4 (2024-12-19)

### Changed
- Migrated all documentation from RST to Markdown format
- Updated setup.py to use README.md instead of README.rst
- Added long_description_content_type='text/markdown' to setup.py

### Removed
- Removed AUTHORS.rst, HISTORY.rst, and README.rst files
- Removed reference to CONTRIBUTING.rst from tox.ini

## 1.0.3 (2024-12-19)

### Added
- WordPress pagination headers support (X-WP-TotalPages and X-WP-Total) in dump command
- Progress tracking showing "page X of Y" when pagination headers are available
- Summary logging showing total records and pages processed after completion

### Fixed
- Replaced deprecated pkg_resources with importlib.resources (Python 3.9+ uses modern API)
- Fixed setuptools warning about missing wparc.data package

## 1.0.2 (2022-04-02)

### Added
- Type hints throughout the codebase for better IDE support and type safety
- Module-level docstrings for better documentation
- Configurable timeout, page size, and retry count via CLI options
- SSL verification option (enabled by default for security)
- Generator-based file processing for memory efficiency
- Development dependencies in setup.py extras
- Improved error messages with actionable guidance
- Better logging throughout (replaced print statements)

### Changed
- Replaced Click with Typer for modern CLI framework
- Changed `domain` from option to required argument
- Improved error handling with specific exception types
- All file operations now use context managers
- Better function naming (snake_case throughout)
- Consolidated CLI structure (removed duplicate groups)

### Fixed
- Fixed trailing space bug in media filename
- Fixed command injection vulnerability (replaced os.system with subprocess)
- Fixed bare except clauses with specific exception handling
- Fixed incorrect project references (yspcrawler → wparc)
- Fixed missing dependencies in setup.py
- Fixed incorrect test configuration in tox.ini
- Removed all commented-out code
- Fixed unused variables

### Security
- SSL verification enabled by default
- Command injection vulnerabilities fixed
- Secure file handling with context managers
- Proper error handling to prevent information leakage

## 1.0.2 (2022-04-02)

* Added command "ping" to verify existence of /wp-json/ endpoint
* Added option "https" for "ping" and "dump" commands. It forces using https by default instead of http

## 1.0.1 (2022-03-31)

* First public release on PyPI and updated github code

