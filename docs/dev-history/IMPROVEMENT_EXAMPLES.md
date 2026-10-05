# Code Improvement Examples

This document provides specific code examples showing how to improve various parts of the codebase.

## 1. Improved Error Handling

### Current Code (`crawler.py` - `ping` function)
```python
def ping(domain, force_https=False):
    prefix = 'https' if force_https else 'http'
    url = prefix + '://' + domain + '/wp-json/'
    wptext = requests.get(url, headers=REQUEST_HEADER, timeout=DEFAULT_TIMEOUT)
    try:
        wpjson = wptext.json()
        allroutes = list(wpjson['routes'].keys())
        print('Endpoint %s is OK' % (url))
        print('Total routes %d' % (len(allroutes)))
    except:
        print('Endpoint %s is invalid' % (url))
```

### Improved Version
```python
def ping(domain: str, force_https: bool = False) -> None:
    """
    Ping WordPress API endpoint to verify it's accessible.
    
    Args:
        domain: Domain name (e.g., 'example.com')
        force_https: Force HTTPS instead of HTTP
        
    Raises:
        ValueError: If domain is invalid
        requests.RequestException: If connection fails
    """
    if not domain or not domain.strip():
        raise ValueError("Domain cannot be empty")
    
    domain = domain.strip().lower()
    prefix = 'https' if force_https else 'http'
    url = f"{prefix}://{domain}/wp-json/"
    
    try:
        response = requests.get(
            url, 
            headers=REQUEST_HEADER, 
            timeout=DEFAULT_TIMEOUT,
            verify=True  # Enable SSL verification by default
        )
        response.raise_for_status()
        
        wpjson = response.json()
        
        if 'routes' not in wpjson:
            logging.warning(f"Unexpected response format from {url}")
            return
            
        allroutes = list(wpjson['routes'].keys())
        logging.info(f'Endpoint {url} is OK')
        logging.info(f'Total routes: {len(allroutes)}')
        
    except requests.exceptions.SSLError as e:
        logging.error(f"SSL error connecting to {url}: {e}")
        raise
    except requests.exceptions.Timeout:
        logging.error(f"Timeout connecting to {url}")
        raise
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error to {url}: {e}")
        raise
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error {e.response.status_code} from {url}")
        raise
    except (KeyError, ValueError) as e:
        logging.error(f"Invalid response format from {url}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error pinging {url}: {e}")
        raise
```

## 2. Improved File Handling

### Current Code (`crawler.py` - `collect_files`)
```python
def collect_files(domain):
    if not os.path.exists(os.path.join(domain, 'data', 'wp_v2_media.jsonl ')):
        print("Not found wp_v2_media.jsonl")
        return
    objects = []
    f = open(os.path.join(domain, 'data', 'wp_v2_media.jsonl '), 'r', encoding='utf8')
    for row in f:
        object = json.loads(row)
        objects.append(object['source_url'])
    f.close()
```

### Improved Version
```python
def collect_files(domain: str) -> None:
    """
    Download all media files listed in wp_v2_media.jsonl.
    
    Args:
        domain: Domain name used as output directory
        
    Raises:
        FileNotFoundError: If media file list doesn't exist
        ValueError: If JSON file is malformed
    """
    media_file = os.path.join(domain, 'data', 'wp_v2_media.jsonl')
    
    if not os.path.exists(media_file):
        raise FileNotFoundError(f"Media file list not found: {media_file}")
    
    urls = []
    try:
        with open(media_file, 'r', encoding='utf8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if 'source_url' in obj:
                        urls.append(obj['source_url'])
                    else:
                        logging.warning(f"Line {line_num}: Missing 'source_url' field")
                except json.JSONDecodeError as e:
                    logging.warning(f"Line {line_num}: Invalid JSON - {e}")
                    continue
    except IOError as e:
        logging.error(f"Error reading {media_file}: {e}")
        raise
    
    if not urls:
        logging.warning("No URLs found in media file")
        return
    
    logging.info(f"Found {len(urls)} media files to download")
    for url in urls:
        try:
            logging.info(f'Downloading file: {url}')
            parsed = urlparse(url)
            filepath = os.path.join(domain, 'files', parsed.path.lstrip('/'))
            get_file(url, filepath)
        except Exception as e:
            logging.error(f"Failed to download {url}: {e}")
            continue
```

## 3. Improved CLI Structure

### Current Code (`core.py`)
```python
@click.group()
def cli1():
    pass

@cli1.command()
@click.option('--domain', '-d', default=None, help='URL of the Yandex.Disk public resource')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output. Print additional info')
def getfiles(domain, verbose):
    """s public resource files"""
    if verbose:
        enableVerbose()
    if domain is None:
        print('Domain name required, for example "example.com"')
        return
    acmd = Project()
    acmd.getfiles(domain)
    pass
```

### Improved Version
```python
@click.group()
@click.version_option(version=wparc.__version__)
def cli():
    """
    WordPress API crawler and backup tool.
    
    Extract data and media files from WordPress websites using the REST API.
    """
    pass


@cli.command()
@click.option(
    '--domain', '-d',
    required=True,
    help='Domain name (e.g., example.com)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--output-dir', '-o',
    default=None,
    help='Output directory (default: domain name)'
)
def getfiles(domain: str, verbose: bool, output_dir: str) -> None:
    """
    Download all media files listed in wp_v2_media.jsonl.
    
    This command requires that the 'dump' command has been run first
    to generate the media file list.
    
    Example:
        wparc getfiles --domain example.com
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        project = Project()
        project.getfiles(domain, output_dir=output_dir)
    except Exception as e:
        logging.error(f"Error downloading files: {e}")
        raise click.ClickException(str(e))
```

## 4. Improved Retry Logic

### Current Code (`crawler.py` - `dump_route_list`)
```python
rc = 0
while True:
    if rc == RETRY_COUNT:
        resp = None
        logging.debug('- end of iteration %s after 5 retries' % (route))
        break
    rc += 1
    try:
        resp = requests.get(url + '?page=%d&order=asc&orderby=id&per_page=%d' % (page, WP_DEFAULT_PAGESIZE), headers=REQUEST_HEADER, timeout=DEFAULT_TIMEOUT)
        break
    except KeyboardInterrupt:
        print('- timeout on data retrieval')
```

### Improved Version
```python
import time
from typing import Optional

def _fetch_with_retry(
    url: str,
    max_retries: int = RETRY_COUNT,
    retry_delay: float = 1.0
) -> Optional[requests.Response]:
    """
    Fetch URL with retry logic.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Response object or None if all retries failed
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url,
                headers=REQUEST_HEADER,
                timeout=DEFAULT_TIMEOUT,
                verify=True
            )
            response.raise_for_status()
            return response
            
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                logging.warning(
                    f"Timeout (attempt {attempt}/{max_retries}), "
                    f"retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logging.error(f"Timeout after {max_retries} attempts")
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                logging.warning(
                    f"Request failed (attempt {attempt}/{max_retries}): {e}, "
                    f"retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logging.error(f"Request failed after {max_retries} attempts: {e}")
                
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            raise
            
    return None


def dump_route_list(url: str, route: str, filepath: str) -> None:
    """
    Dump paginated route data to JSONL file.
    
    Args:
        url: Base URL for the route
        route: Route path (for logging)
        filepath: Output directory path
    """
    outfile = os.path.join(
        filepath,
        route.strip('/').replace('/', '_') + '.jsonl'
    )
    
    page = 0
    outdata = []
    
    while True:
        page += 1
        page_url = (
            f"{url}?page={page}&order=asc&orderby=id"
            f"&per_page={WP_DEFAULT_PAGESIZE}"
        )
        
        logging.info(f'Processing page {page} of {route}')
        
        resp = _fetch_with_retry(page_url)
        if resp is None:
            logging.error(f'Failed to fetch page {page} after retries')
            break
            
        if resp.status_code != 200:
            logging.debug(
                f'HTTP status {resp.status_code} for page {page}, '
                f'expected 200'
            )
            break
            
        try:
            data = resp.json()
        except ValueError as e:
            logging.error(f'Invalid JSON response for page {page}: {e}')
            break
            
        if isinstance(data, dict):
            logging.debug(f'Received dict response, end of pagination')
            break
        elif isinstance(data, list):
            if len(data) == 0:
                logging.debug(f'Empty page {page}, end of pagination')
                break
            logging.debug(f'Extracted {len(data)} records from page {page}')
            outdata.extend(data)
            if len(data) < WP_DEFAULT_PAGESIZE:
                logging.debug(f'Returned data length less than {WP_DEFAULT_PAGESIZE}. Stopping')
                break
        else:
            logging.warning(f'Unexpected response type: {type(data)}')
            break
    
    # Write all collected data
    try:
        with open(outfile, 'w', encoding='utf8') as f:
            for row in outdata:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
        logging.info(f'Written {len(outdata)} records to {outfile}')
    except IOError as e:
        logging.error(f'Error writing to {outfile}: {e}')
        raise
```

## 5. Improved Configuration Management

### New File: `wparc/config.py`
```python
"""Configuration management for wparc."""
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class Config:
    """Application configuration."""
    timeout: int = 360
    retry_count: int = 5
    retry_delay: float = 1.0
    page_size: int = 100
    chunk_size: int = 1024 * 1024
    verify_ssl: bool = True
    user_agent: str = (
        'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 '
        'Mobile Safari/537.36'
    )
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create config from environment variables."""
        return cls(
            timeout=int(os.getenv('WPARC_TIMEOUT', 360)),
            retry_count=int(os.getenv('WPARC_RETRY_COUNT', 5)),
            retry_delay=float(os.getenv('WPARC_RETRY_DELAY', 1.0)),
            page_size=int(os.getenv('WPARC_PAGE_SIZE', 100)),
            chunk_size=int(os.getenv('WPARC_CHUNK_SIZE', 1024 * 1024)),
            verify_ssl=os.getenv('WPARC_VERIFY_SSL', 'true').lower() == 'true',
        )
```

## 6. Improved Project Class

### Current Code (`extractor.py`)
```python
class Project:
    """Wordpress API crawler"""

    def __init__(self):
        pass

    def dump(self, domain, all, https):
        collect_data(domain, get_unknown=all, force_https=https)
        pass

    def getfiles(self, domain):
        collect_files(domain)
        pass

    def ping(self, domain, https):
        ping(domain, force_https=https)
```

### Improved Version
```python
from typing import Optional
from .config import Config

class Project:
    """
    WordPress API crawler and backup tool.
    
    This class provides a high-level interface for crawling WordPress
    websites and downloading their content.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize Project with optional configuration.
        
        Args:
            config: Configuration object (uses default if not provided)
        """
        self.config = config or Config.from_env()
    
    def dump(
        self,
        domain: str,
        get_unknown: bool = True,
        force_https: bool = False,
        output_dir: Optional[str] = None
    ) -> None:
        """
        Dump all data from WordPress API.
        
        Args:
            domain: Domain name to crawl
            get_unknown: Include unknown API routes
            force_https: Force HTTPS protocol
            output_dir: Output directory (default: domain name)
            
        Raises:
            ValueError: If domain is invalid
            requests.RequestException: If API access fails
        """
        if not domain or not domain.strip():
            raise ValueError("Domain cannot be empty")
        
        output_dir = output_dir or domain.strip()
        
        try:
            collect_data(
                domain=domain,
                get_unknown=get_unknown,
                force_https=force_https,
                output_dir=output_dir,
                config=self.config
            )
        except Exception as e:
            logging.error(f"Error dumping data from {domain}: {e}")
            raise
    
    def getfiles(
        self,
        domain: str,
        output_dir: Optional[str] = None
    ) -> None:
        """
        Download all media files.
        
        Args:
            domain: Domain name (used to locate media file list)
            output_dir: Output directory (default: domain name)
            
        Raises:
            FileNotFoundError: If media file list doesn't exist
        """
        output_dir = output_dir or domain
        collect_files(domain=domain, output_dir=output_dir, config=self.config)
    
    def ping(self, domain: str, force_https: bool = False) -> dict:
        """
        Ping WordPress API endpoint.
        
        Args:
            domain: Domain name to ping
            force_https: Force HTTPS protocol
            
        Returns:
            Dictionary with endpoint status and route count
            
        Raises:
            requests.RequestException: If ping fails
        """
        return ping(domain=domain, force_https=force_https, config=self.config)
```

These examples demonstrate best practices for:
- Type hints
- Error handling
- Documentation
- Code organization
- Configuration management
- User experience improvements
