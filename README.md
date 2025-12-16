# wparc: a command-line tool to backup public data from WordPress websites using WordPress API

wparc is a command line tool used to backup data from WordPress based websites.
It uses `/wp-json/` API provided by default WordPress installation and extracts all data and media files.

## Main features

* **Data extraction**: Dump all WordPress REST API routes and data
* **Media download**: Download all media files referenced in the API
* **Smart pagination**: Automatically detects and uses WordPress pagination headers (X-WP-TotalPages, X-WP-Total) for accurate progress tracking
* **Progress tracking**: Shows "page X of Y" progress when pagination headers are available
* **SSL verification**: Secure by default with configurable SSL verification
* **Configurable**: Customize timeout, page size, retry count, and more
* **Type-safe**: Full type hints for better IDE support and code quality

## Installation

### Production Installation

```bash
pip install --upgrade pip setuptools
pip install wparc
```

### Development Installation

```bash
git clone https://github.com/ruarxive/wparc.git
cd wparc
pip install -e ".[dev]"
```

### Python version

Python version 3.6 or greater is required.

## Usage

### Basic Commands

```bash
# Get help
wparc --help

# Ping a WordPress site
wparc ping example.com

# Dump all data from a WordPress site
wparc dump example.com

# Download media files (requires dump to be run first)
wparc getfiles example.com
```

### Command Options

#### Ping Command

```bash
wparc ping <domain> [OPTIONS]

Options:
  -v, --verbose          Verbose output
  --https                Force HTTPS protocol
  --no-verify-ssl        Disable SSL certificate verification (not recommended)
  --timeout INTEGER      Request timeout in seconds (default: 360)
```

**Example:**
```bash
wparc ping example.com --https --verbose
```

#### Dump Command

```bash
wparc dump <domain> [OPTIONS]

Options:
  -v, --verbose          Verbose output
  -a, --all             Include unknown API routes (default: True)
  --https                Force HTTPS protocol
  --no-verify-ssl        Disable SSL certificate verification (not recommended)
  --timeout INTEGER      Request timeout in seconds (default: 360)
  --page-size INTEGER    Number of items per page (default: 100)
  --retry-count INTEGER  Number of retry attempts (default: 5)
```

**Example:**
```bash
wparc dump example.com --https --timeout 600 --page-size 50
```

**Note**: The dump command automatically uses WordPress pagination headers (`X-WP-TotalPages` and `X-WP-Total`) when available to show accurate progress like "Processing page 1 of 5". This provides better visibility into the extraction progress for large sites.

#### Getfiles Command

```bash
wparc getfiles <domain> [OPTIONS]

Options:
  -v, --verbose          Verbose output
  --no-verify-ssl        Disable SSL certificate verification (not recommended)
```

**Example:**
```bash
wparc getfiles example.com --verbose
```

## Output Structure

After running `wparc dump <domain>`, the following structure is created:

```
<domain>/
├── data/
│   ├── wp-json.json          # Main API index
│   ├── wp_v2_posts.jsonl     # Posts data
│   ├── wp_v2_pages.jsonl     # Pages data
│   ├── wp_v2_media.jsonl     # Media metadata
│   └── ...                   # Other routes
└── files/                    # Media files (after getfiles)
    └── wp-content/
        └── uploads/
            └── ...
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black wparc/

# Type checking
mypy wparc/

# Linting
flake8 wparc/
```

## Troubleshooting

### SSL Certificate Errors

If you encounter SSL certificate errors, you can temporarily disable verification:

```bash
wparc dump example.com --no-verify-ssl
```

**Warning**: This is not recommended for production use as it makes you vulnerable to man-in-the-middle attacks.

### Timeout Errors

If requests are timing out, increase the timeout:

```bash
wparc dump example.com --timeout 600
```

### Large Sites

For large WordPress sites, you may want to adjust the page size:

```bash
wparc dump example.com --page-size 50
```

The dump command automatically detects pagination information from WordPress API headers, so you'll see progress like "Processing page 1 of 10" when available. This helps you estimate completion time for large extractions.

## Security

- SSL verification is enabled by default
- All file operations use secure context managers
- Command injection vulnerabilities have been fixed
- Proper error handling prevents information leakage

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

See LICENSE file for details.

## Documentation

For detailed information about WordPress REST API endpoints, see [WP_API_ENDPOINTS.md](docs/WP_API_ENDPOINTS.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes.

