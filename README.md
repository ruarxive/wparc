# wparc: WordPress API Crawler and Backup Tool

**wparc** (WordPress Archive) is a powerful command-line tool for backing up and archiving public data from WordPress websites using the WordPress REST API. It provides a simple, efficient way to extract posts, pages, media metadata, comments, and other content from any WordPress site that has the REST API enabled.

## What is wparc?

wparc connects to WordPress sites via their `/wp-json/` REST API endpoint (available by default in WordPress 4.7+) and extracts all publicly accessible data. Unlike traditional backup tools that require database access or FTP credentials, wparc only needs the site URL and works entirely through the public API.

**Key capabilities:**
- Extract all public WordPress content (posts, pages, media, comments, etc.)
- Download media files (images, videos, documents)
- Analyze and discover WordPress API routes
- Generate structured, machine-readable backups (JSONL format)
- Work with any WordPress site without special permissions

## Main features

* **Data extraction**: Dump all WordPress REST API routes and data
* **Media download**: Download all media files referenced in the API
* **Route analysis**: Analyze and categorize WordPress API routes, automatically test unknown routes, and generate YAML updates
* **Smart pagination**: Automatically detects and uses WordPress pagination headers (X-WP-TotalPages, X-WP-Total) for accurate progress tracking
* **Progress tracking**: Shows "page X of Y" progress when pagination headers are available
* **SSL verification**: Secure by default with configurable SSL verification
* **Configurable**: Customize timeout, page size, retry count, and more
* **Type-safe**: Full type hints for better IDE support and code quality
* **Error handling**: Comprehensive error handling with custom exceptions and actionable error messages

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

Python version 3.6 or greater is required. Python 3.9+ is recommended for best performance and compatibility.

### System Requirements

- Python 3.6+
- Internet connection for downloading data
- Sufficient disk space (depends on site size - typically 100MB to several GB)
- Write permissions in the current directory (for creating output folders)

## Usage

### Quick Start

Here's a typical workflow for backing up a WordPress site:

```bash
# Step 1: Verify the site's REST API is accessible
wparc ping example.com

# Step 2: Analyze available routes (optional, but recommended)
wparc analyze example.com --verbose

# Step 3: Dump all data from the WordPress site
wparc dump example.com --verbose

# Step 4: Download all media files
wparc getfiles example.com --verbose
```

### Basic Commands

**Get help:**
```bash
wparc --help
# Or get help for a specific command
wparc ping --help
wparc dump --help
```

**Ping a WordPress site** (verify API accessibility):
```bash
wparc ping example.com
```

**Dump all data** from a WordPress site:
```bash
wparc dump example.com
```

**Download media files** (requires dump to be run first):
```bash
wparc getfiles example.com
```

**Analyze WordPress API routes** and test unknown routes:
```bash
wparc analyze example.com
```

### Command Options

#### Ping Command

The `ping` command verifies that a WordPress site's REST API is accessible and returns basic information about available endpoints. This is useful as a first step to check if a site supports the WordPress REST API before attempting to dump data.

**Syntax:**
```bash
wparc ping <domain> [OPTIONS]
```

**Options:**
- `-v, --verbose`: Enable verbose output with detailed logging information
- `--https`: Force HTTPS protocol (default: True, use `--no-https` to disable)
- `--no-verify-ssl`: Disable SSL certificate verification (not recommended for security)
- `--timeout INTEGER`: Request timeout in seconds (default: 360)

**What it does:**
- Connects to the WordPress REST API endpoint (`/wp-json/`)
- Verifies the API is accessible and responding
- Counts total available routes
- Returns endpoint URL and route count

**Examples:**

Basic ping to check if API is accessible:
```bash
wparc ping example.com
```

Ping with HTTPS and verbose output to see detailed connection information:
```bash
wparc ping example.com --https --verbose
```

Ping a site with self-signed SSL certificate (development/testing only):
```bash
wparc ping localhost --no-verify-ssl --no-https
```

Ping with custom timeout for slow connections:
```bash
wparc ping slow-site.com --timeout 600
```

**Expected Output:**
```
✓ Endpoint https://example.com/wp-json/ is OK
✓ Total routes: 45
```

**Use Cases:**
- Quick health check before running a full dump
- Verifying REST API is enabled on a WordPress site
- Testing connectivity and SSL configuration
- Discovering how many routes are available

#### Dump Command

The `dump` command extracts all data from a WordPress site's REST API and saves it to local JSONL files. This is the primary command for backing up WordPress content including posts, pages, media metadata, comments, users, and other API endpoints.

**Syntax:**
```bash
wparc dump <domain> [OPTIONS]
```

**Options:**
- `-v, --verbose`: Enable verbose output showing detailed progress and operations
- `-a, --all`: Include unknown API routes in the dump (default: True). Set to `--no-all` to only dump known routes
- `--https`: Force HTTPS protocol (default: True, use `--no-https` to disable)
- `--no-verify-ssl`: Disable SSL certificate verification (not recommended for security)
- `--timeout INTEGER`: Request timeout in seconds (default: 360). Increase for slow sites or large datasets
- `--page-size INTEGER`: Number of items per page (default: 100). Lower values use less memory but more requests
- `--retry-count INTEGER`: Number of retry attempts for failed requests (default: 5)

**What it does:**
- Discovers all available WordPress REST API routes
- Iterates through paginated endpoints (posts, pages, media, etc.)
- Downloads all data and saves to JSONL files (one JSON object per line)
- Creates organized directory structure: `<domain>/data/`
- Shows progress with pagination information when available
- Handles errors gracefully with automatic retries

**Examples:**

Basic dump of all data from a WordPress site:
```bash
wparc dump example.com
```

Dump with verbose output to see detailed progress:
```bash
wparc dump example.com --verbose
```

Dump only known routes (skip unknown/custom routes):
```bash
wparc dump example.com --no-all
```

Dump from a large site with custom settings for better performance:
```bash
wparc dump large-site.com --timeout 600 --page-size 50 --retry-count 3
```

Dump from a development site with self-signed certificate:
```bash
wparc dump dev.local --no-verify-ssl --no-https
```

Dump with HTTP instead of HTTPS (for local development):
```bash
wparc dump localhost --no-https
```

**Expected Output:**
```
Processing route: /wp/v2/posts
Processing page 1 of 5 (100 items per page)
Processing page 2 of 5 (100 items per page)
...
✓ Data collection complete: 45 routes processed, 2 skipped
```

**Output Files:**
After completion, you'll find files in `<domain>/data/`:
- `wp-json.json` - Main API index with all routes
- `wp_v2_posts.jsonl` - All posts (one JSON object per line)
- `wp_v2_pages.jsonl` - All pages
- `wp_v2_media.jsonl` - Media metadata (use `getfiles` to download actual files)
- `wp_v2_comments.jsonl` - Comments
- `wp_v2_users.jsonl` - Users (public data only)
- Additional route files as discovered

**Note**: The dump command automatically uses WordPress pagination headers (`X-WP-TotalPages` and `X-WP-Total`) when available to show accurate progress like "Processing page 1 of 5". This provides better visibility into the extraction progress for large sites.

**Use Cases:**
- Full site backup before migration or updates
- Content archival and preservation
- Data analysis and research
- Creating local copies for development
- Extracting content for static site generation

#### Getfiles Command

The `getfiles` command downloads all media files (images, videos, documents, etc.) that were referenced in the media metadata collected by the `dump` command. It reads from `wp_v2_media.jsonl` and downloads each file to the local filesystem, preserving the original directory structure.

**Syntax:**
```bash
wparc getfiles <domain> [OPTIONS]
```

**Options:**
- `-v, --verbose`: Enable verbose output showing download progress and file details
- `--no-verify-ssl`: Disable SSL certificate verification (not recommended for security)

**What it does:**
- Reads media metadata from `<domain>/data/wp_v2_media.jsonl` (created by `dump` command)
- Downloads each media file referenced in the metadata
- Preserves original WordPress directory structure (`wp-content/uploads/...`)
- Supports resumable downloads (can be interrupted and resumed)
- Uses concurrent workers for faster downloads (default: 5 workers)
- Creates checkpoint files to track progress

**Prerequisites:**
- Must run `wparc dump <domain>` first to generate the media metadata file
- Requires the `wp_v2_media.jsonl` file to exist in `<domain>/data/`

**Examples:**

Download all media files after running dump:
```bash
# First, dump the data
wparc dump example.com

# Then download the media files
wparc getfiles example.com
```

Download with verbose output to see progress:
```bash
wparc getfiles example.com --verbose
```

Download from a site with SSL issues (development only):
```bash
wparc getfiles dev.local --no-verify-ssl
```

**Expected Output:**
```
Reading media files from example.com/data/wp_v2_media.jsonl
Found 1,234 media files to download
Downloading: image1.jpg [████████████] 100%
Downloading: video1.mp4 [████████████] 100%
...
✓ File download complete: 1234 downloaded, 0 failed, 0 skipped
```

**Output Structure:**
Files are downloaded to `<domain>/files/wp-content/uploads/` preserving the original WordPress structure:
```
example.com/
└── files/
    └── wp-content/
        └── uploads/
            ├── 2024/
            │   └── 12/
            │       └── image.jpg
            └── 2025/
                └── 01/
                    └── video.mp4
```

**Features:**
- **Resumable**: If interrupted, can resume from checkpoint
- **Concurrent**: Downloads multiple files simultaneously (5 workers by default)
- **Progress Tracking**: Shows download progress for each file
- **Error Handling**: Continues downloading even if some files fail
- **Checkpoint System**: Saves progress to resume later

**Use Cases:**
- Complete site backup including all media files
- Migrating media files to a new server
- Creating offline archives of WordPress sites
- Downloading media for local development environments
- Preserving media assets for archival purposes

#### Analyze Command

The `analyze` command performs a comprehensive analysis of a WordPress site's REST API routes. It compares discovered routes against a database of known routes, identifies unknown routes, automatically tests them to determine their characteristics, and generates YAML updates that can be added to the known routes database.

**Syntax:**
```bash
wparc analyze <domain> [OPTIONS]
```

**Options:**
- `-v, --verbose`: Enable verbose output showing detailed analysis and route testing progress
- `--https`: Force HTTPS protocol (default: True, use `--no-https` to disable)
- `--no-verify-ssl`: Disable SSL certificate verification (not recommended for security)
- `--timeout INTEGER`: Request timeout in seconds (default: 360)

**What it does:**
1. **Route Discovery**: Fetches all available routes from `/wp-json/`
2. **Route Comparison**: Compares against known routes database (`known_routes.yml`)
3. **Route Categorization**: Categorizes routes into:
   - `protected`: Routes requiring authentication (401/403 responses)
   - `public-list`: Public routes returning arrays/lists (e.g., posts, pages)
   - `public-dict`: Public routes returning objects/dictionaries
   - `useless`: Routes that don't provide useful data (individual items, regex patterns)
   - `unknown`: Routes not in the known routes database
4. **Automatic Testing**: Tests unknown routes to determine their category
5. **YAML Generation**: Creates ready-to-use YAML for updating `known_routes.yml`

**Route Categories Explained:**
- **Protected**: Requires authentication, returns 401/403 errors. Not useful for public backups.
- **Public-list**: Returns arrays of items (posts, pages, comments). Useful for bulk data extraction.
- **Public-dict**: Returns single objects/dictionaries. May contain useful site information.
- **Useless**: Individual item endpoints (e.g., `/wp/v2/posts/123`) or regex patterns. Not useful for bulk extraction.

**Examples:**

Basic analysis of a WordPress site:
```bash
wparc analyze example.com
```

Analysis with verbose output to see route testing details:
```bash
wparc analyze example.com --verbose
```

Analyze a site with custom plugins that may have unknown routes:
```bash
wparc analyze custom-site.com --verbose
```

Analyze a development site:
```bash
wparc analyze dev.local --no-verify-ssl --no-https
```

**Expected Output:**
```
✓ Analysis complete for https://example.com/wp-json/
✓ Total routes: 45

Route Statistics:
  Protected: 12
  Public-list: 20
  Public-dict: 5
  Useless: 3
  Unknown: 5

⚠ Found 5 unknown routes
Testing routes: 100%|████████████| 5/5 [00:02<00:00,  2.1route/s]
✓ Testing complete for unknown routes

Categorized routes:
  public-list: 3
  protected: 2

======================================================================
YAML Update for known_routes.yml:
======================================================================
protected:
- /wp/v2/users/me
- /wp/v2/settings
public-list:
- /wp/v2/custom-post-type
- /wp/v2/another-route
- /wp/v2/third-route
======================================================================

You can add the above YAML to known_routes.yml
```

**With Verbose Output:**
When using `--verbose`, you'll see additional details:
```
Testing route: /wp/v2/custom-post-type
  Status: 200
  Response type: list
  Category: public-list
Testing route: /wp/v2/users/me
  Status: 401
  Category: protected
...
```

**Using the Generated YAML:**
The command outputs YAML that can be directly added to `wparc/data/known_routes.yml`:
1. Copy the YAML output from the command
2. Open `wparc/data/known_routes.yml` (or your local copy)
3. Add the routes under the appropriate category
4. This helps improve route recognition for future dumps

**Use Cases:**
- Discovering custom WordPress plugins and their API endpoints
- Understanding what data is available from a WordPress site
- Contributing to the known routes database
- Planning data extraction strategies
- Identifying protected vs. public endpoints
- Researching WordPress API capabilities

## Output Structure

After running `wparc dump <domain>`, the following directory structure is created in your current working directory:

```
<domain>/
├── data/
│   ├── wp-json.json          # Main API index with all routes and endpoints
│   ├── wp_v2_posts.jsonl     # All posts (one JSON object per line)
│   ├── wp_v2_pages.jsonl     # All pages
│   ├── wp_v2_media.jsonl     # Media metadata (URLs, titles, descriptions)
│   ├── wp_v2_comments.jsonl  # Comments
│   ├── wp_v2_users.jsonl     # Users (public data only)
│   ├── wp_v2_categories.jsonl # Categories
│   ├── wp_v2_tags.jsonl      # Tags
│   └── ...                   # Other routes discovered from the API
└── files/                    # Media files (created after running getfiles)
    └── wp-content/
        └── uploads/
            ├── 2024/
            │   └── 12/
            │       └── image.jpg
            └── 2025/
                └── 01/
                    └── video.mp4
```

### File Formats

**JSONL Format**: Most data files use JSONL (JSON Lines) format where each line is a valid JSON object. This format is:
- Memory efficient (can process line by line)
- Easy to parse programmatically
- Suitable for large datasets

**Example JSONL file content** (`wp_v2_posts.jsonl`):
```jsonl
{"id":1,"date":"2024-01-01T00:00:00","title":{"rendered":"Hello World"},"content":{"rendered":"<p>Welcome to WordPress!</p>"},"excerpt":{"rendered":"<p>Welcome...</p>"},"author":1,"featured_media":0}
{"id":2,"date":"2024-01-02T00:00:00","title":{"rendered":"Sample Post"},"content":{"rendered":"<p>This is a sample post.</p>"},"excerpt":{"rendered":"<p>This is...</p>"},"author":1,"featured_media":123}
```

**Reading JSONL files**:
```python
import json

with open('example.com/data/wp_v2_posts.jsonl', 'r') as f:
    for line in f:
        post = json.loads(line)
        print(post['title']['rendered'])
```

### Complete Backup Example

Here's a complete example of backing up a WordPress site:

```bash
# 1. Check if the site is accessible
$ wparc ping mysite.com
✓ Endpoint https://mysite.com/wp-json/ is OK
✓ Total routes: 52

# 2. Analyze routes to understand what's available
$ wparc analyze mysite.com --verbose
✓ Analysis complete for https://mysite.com/wp-json/
✓ Total routes: 52
Route Statistics:
  Protected: 15
  Public-list: 28
  Public-dict: 4
  Useless: 3
  Unknown: 2

# 3. Dump all data
$ wparc dump mysite.com --verbose
Processing route: /wp/v2/posts
Processing page 1 of 12 (100 items per page)
...
✓ Data collection complete: 50 routes processed, 2 skipped

# 4. Download media files
$ wparc getfiles mysite.com --verbose
Found 1,234 media files to download
Downloading: image1.jpg [████████████] 100%
...
✓ File download complete: 1234 downloaded, 0 failed, 0 skipped

# Result: Complete backup in mysite.com/ directory
$ ls -lh mysite.com/
data/  files/
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

## Common Workflows

### Complete Site Backup

The most common use case - creating a complete backup of a WordPress site:

```bash
# Step 1: Verify connectivity
wparc ping example.com

# Step 2: Extract all data
wparc dump example.com --verbose

# Step 3: Download all media files
wparc getfiles example.com --verbose
```

### Quick Content Analysis

Analyze what content is available without downloading everything:

```bash
# Get route statistics
wparc analyze example.com --verbose

# Check specific route counts
wparc ping example.com
```

### Large Site Backup

For sites with thousands of posts or slow connections:

```bash
# Use smaller page size and longer timeout
wparc dump large-site.com \
  --timeout 900 \
  --page-size 25 \
  --retry-count 10 \
  --verbose
```

### Development Site Backup

For local development sites or sites with self-signed certificates:

```bash
# Disable SSL verification (development only!)
wparc dump dev.local --no-verify-ssl --no-https

# Download media files
wparc getfiles dev.local --no-verify-ssl
```

### Incremental Backup Strategy

For regular backups, you can run dump multiple times - it will overwrite existing files:

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y-%m-%d)
wparc dump example.com --verbose > backup-$DATE.log 2>&1
wparc getfiles example.com --verbose >> backup-$DATE.log 2>&1
```

### Discovering Custom Endpoints

Find and document custom WordPress plugin endpoints:

```bash
# Analyze and get YAML for unknown routes
wparc analyze custom-site.com --verbose > analysis.txt

# The output will include YAML that can be added to known_routes.yml
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

### Domain Validation Errors

If you see domain validation errors, ensure you're using a valid domain format:

- Valid: `example.com`, `www.example.com`, `subdomain.example.com`
- Invalid: `http://example.com` (protocol will be stripped automatically)
- Invalid: `example.com/` (trailing slash will be removed automatically)

### Error Messages

wparc provides detailed error messages with actionable suggestions:

**DomainValidationError**: Invalid domain format
```
Error: Invalid domain 'example..com': Domain cannot contain consecutive dots
```
**Solution**: Check the domain name format. Valid formats: `example.com`, `www.example.com`, `subdomain.example.com`

**APIError**: WordPress API request failed
```
WordPress API error for https://example.com/wp-json/ (HTTP 404)
Suggestion: Check if the WordPress REST API is enabled on this site.
```
**Solution**: 
- Verify the site is accessible: `curl https://example.com/wp-json/`
- Check if REST API is disabled by plugins or theme
- Ensure WordPress version is 4.7+ (REST API was introduced in 4.7)

**SSLVerificationError**: SSL certificate verification failed
```
SSL verification failed for https://example.com/wp-json/: certificate verify failed
Suggestion: If you trust this site, you can use --no-verify-ssl (not recommended for production).
```
**Solution**: 
- For production sites: Fix SSL certificate issues on the server
- For development/testing: Use `--no-verify-ssl` flag (not recommended for production)

**FileDownloadError**: File download failed
```
Failed to download https://example.com/wp-content/uploads/image.jpg: Connection timeout
Suggestion: Check your internet connection and verify the URL is accessible.
```
**Solution**: 
- Check internet connectivity
- Verify the media file URL is accessible
- Try downloading manually to verify the file exists
- Check if the site requires authentication for media files

**MediaFileNotFoundError**: Media file list not found
```
Media file not found: example.com/data/wp_v2_media.jsonl
Suggestion: Run 'wparc dump <domain>' first to generate the media file list.
```
**Solution**: Run `wparc dump <domain>` before running `wparc getfiles <domain>`

### Common Issues and Solutions

**Issue**: "Connection timeout" errors
```bash
# Solution: Increase timeout
wparc dump example.com --timeout 900
```

**Issue**: "Too many requests" or rate limiting
```bash
# Solution: Reduce page size and increase retry count
wparc dump example.com --page-size 25 --retry-count 10
```

**Issue**: "SSL certificate verify failed" on valid sites
```bash
# Solution: Update certificates (macOS/Linux)
# Or temporarily disable for testing (not recommended)
wparc dump example.com --no-verify-ssl
```

**Issue**: Dump completes but getfiles fails
```bash
# Solution: Check if wp_v2_media.jsonl exists
ls -lh example.com/data/wp_v2_media.jsonl

# If missing, the site may not have media endpoints
# Try running dump again with --verbose to see what routes were processed
```

**Issue**: Out of memory errors on large sites
```bash
# Solution: Use smaller page size
wparc dump example.com --page-size 25
```

**Issue**: Some routes return 401/403 errors
```
# This is normal - protected routes require authentication
# These routes are automatically skipped during dump
# Use analyze command to see which routes are protected
wparc analyze example.com
```

## Tips & Best Practices

### Performance Optimization

**For large sites:**
- Use smaller `--page-size` (25-50) to reduce memory usage
- Increase `--timeout` for slow connections
- Run during off-peak hours to avoid impacting site performance
- Use `--verbose` to monitor progress

**For faster downloads:**
- The `getfiles` command uses 5 concurrent workers by default
- Ensure stable internet connection for best results
- Consider running `getfiles` separately if dump takes a long time

### Data Management

**File organization:**
- Each domain creates its own directory structure
- JSONL files can be processed line-by-line (memory efficient)
- Media files preserve original WordPress directory structure

**Backup strategy:**
- Run regular dumps to capture content changes
- Store backups in version control or cloud storage
- Consider compressing old backups to save space

### Working with Custom WordPress Sites

**Custom post types:**
- Use `analyze` command to discover custom endpoints
- Custom routes are automatically included when using `--all` flag (default)
- Generated YAML from `analyze` can improve future dumps

**Plugin-specific content:**
- Many WordPress plugins expose their data via REST API
- Use `analyze` to discover plugin endpoints
- Some plugin data may require authentication (will be skipped)

### Development Workflow

**Local development:**
```bash
# Backup production site
wparc dump production.com

# Restore to local (requires custom import script)
# Use JSONL files to import data into local WordPress
```

**Testing:**
- Use `ping` command to verify API accessibility
- Use `analyze` to understand available endpoints
- Test with `--verbose` to see detailed operations

### Limitations

**What wparc can do:**
- Extract all public WordPress content
- Download publicly accessible media files
- Work with any WordPress site (4.7+)
- Discover and analyze API routes

**What wparc cannot do:**
- Access private/protected content (requires authentication)
- Extract database structure or settings
- Backup WordPress core files or themes
- Access content behind paywalls or membership plugins
- Extract user passwords or sensitive data

## Security

- **SSL verification enabled by default**: All HTTPS connections verify SSL certificates
- **Secure file operations**: All file operations use secure context managers
- **No command injection**: Safe subprocess usage prevents command injection vulnerabilities
- **Error handling**: Proper error handling prevents information leakage
- **No authentication**: Only accesses publicly available data (no credentials required or stored)

**Security recommendations:**
- Always use `--https` for production sites (default)
- Only use `--no-verify-ssl` for development/testing
- Review downloaded content before using in production
- Keep wparc updated to latest version

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

