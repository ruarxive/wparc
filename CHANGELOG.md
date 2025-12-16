# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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

