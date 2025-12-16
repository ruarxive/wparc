# -*- coding: utf-8 -*-
"""
WordPress API crawler module.

This module provides functions to crawl and extract data from WordPress REST API endpoints.
It supports downloading media files, dumping API routes, and pinging WordPress sites.
"""
import json
import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, Generator, Tuple
import yaml
import requests
from urllib.parse import urlparse

try:
    from importlib.resources import files
    _IMPORTLIB_RESOURCES_AVAILABLE = True
    _USE_FILES_API = True
except ImportError:
    # Fallback for Python < 3.9
    try:
        from importlib.resources import path as resource_path
        _IMPORTLIB_RESOURCES_AVAILABLE = True
        _USE_FILES_API = False
    except ImportError:
        # Final fallback to pkg_resources for very old Python versions
        import pkg_resources
        _IMPORTLIB_RESOURCES_AVAILABLE = False
        _USE_FILES_API = False

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
import urllib3

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

    # Fallback progress indicator - identity function that returns the iterable
    class _TqdmFallback:
        """Fallback for tqdm when not available."""

        def __init__(self, iterable=None, **kwargs):
            self.iterable = iterable
            self.total = kwargs.get("total", None)
            self.desc = kwargs.get("desc", "")
            self.unit = kwargs.get("unit", "")
            self.n = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def __iter__(self):
            return iter(self.iterable) if self.iterable else iter([])

        def update(self, n=1):
            self.n += n

    def tqdm(iterable=None, **kwargs):
        return _TqdmFallback(iterable, **kwargs)


from ..exceptions import (
    APIError,
    SSLVerificationError,
    MediaFileNotFoundError,
)
from ..utils import format_duration

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_resource_filename(package: str, resource: str) -> str:
    """
    Get the filesystem path to a package resource.
    
    Uses importlib.resources when available (Python 3.9+), falls back to
    importlib.resources.path (Python 3.7-3.8), or pkg_resources for older versions.
    
    Args:
        package: Package name (e.g., 'wparc')
        resource: Resource path relative to package (e.g., 'data/known_routes.yml')
        
    Returns:
        Filesystem path to the resource
    """
    if _IMPORTLIB_RESOURCES_AVAILABLE:
        try:
            if _USE_FILES_API:
                # Python 3.9+: use files() API
                return str(files(package) / resource)
            else:
                # Python 3.7-3.8: use path() context manager
                # Note: For zip packages, the path is only valid within the context,
                # but for regular filesystem packages (common case), it remains valid
                with resource_path(package, resource) as p:
                    path_str = str(p)
                return path_str
        except Exception as e:
            logging.warning(f"Failed to get resource using importlib.resources: {e}")
            # Fall through to pkg_resources fallback
    # Fallback to pkg_resources for older Python versions or if importlib fails
    try:
        import pkg_resources
        return pkg_resources.resource_filename(package, resource)
    except Exception as e:
        logging.error(f"Failed to get resource filename: {e}")
        raise

REQUEST_HEADER = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/67.0.3396.99 Mobile Safari/537.36"
    )
}
WP_DEFAULT_PAGESIZE = 100
DEFAULT_TIMEOUT = 360
RETRY_COUNT = 5
DEFAULT_CHUNK_SIZE = 1024 * 1024
DEFAULT_WORKERS = 5  # Default number of concurrent download workers
CHECKPOINT_FILE = ".wparc_checkpoint.json"


def get_file(
    url: str,
    filename: str,
    aria2: bool = False,
    aria2path: Optional[str] = None,
    verify_ssl: bool = True,
    progress_bar: Optional[tqdm] = None,
) -> Tuple[str, bool, Optional[str]]:
    """
    Download a file from URL to local filesystem.

    Args:
        url: URL to download from
        filename: Local filename to save to
        aria2: Whether to use aria2 for downloading
        aria2path: Path to aria2 executable
        verify_ssl: Whether to verify SSL certificates (default: True)
        progress_bar: Optional tqdm progress bar for individual file

    Returns:
        Tuple of (url, success, error_message)
    """
    if os.path.exists(filename):
        if progress_bar:
            progress_bar.update(1)
        return (url, True, None)

    dirpath = os.path.dirname(filename)
    os.makedirs(dirpath, exist_ok=True)
    basename = os.path.basename(filename)

    if not aria2:
        try:
            page = requests.get(
                url,
                headers=REQUEST_HEADER,
                stream=True,
                verify=verify_ssl,
                timeout=DEFAULT_TIMEOUT,
            )
            page.raise_for_status()

            total_size = int(page.headers.get("content-length", 0))
            downloaded = 0

            with open(filename, "wb") as f:
                for chunk in page.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_bar and total_size > 0:
                            # Update progress for individual file if provided
                            pass  # Main progress bar handles this

            if progress_bar:
                progress_bar.update(1)
            return (url, True, None)
        except requests.exceptions.SSLError as e:
            error_msg = f"SSL verification failed: {e}"
            if progress_bar:
                progress_bar.update(1)
            return (url, False, error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if progress_bar:
                progress_bar.update(1)
            return (url, False, error_msg)
    else:
        if aria2path is None:
            raise ValueError("aria2path is required when aria2=True")

        # Use subprocess instead of os.system to prevent command injection
        cmd = [aria2path, "--retry-wait=10"]
        if len(dirpath) > 0:
            cmd.extend(["-d", dirpath, "--out", basename])
        else:
            cmd.extend(["--out", basename])
        cmd.append(url)

        try:
            subprocess.run(cmd, check=True, timeout=DEFAULT_TIMEOUT)
            if progress_bar:
                progress_bar.update(1)
            return (url, True, None)
        except subprocess.CalledProcessError as e:
            error_msg = f"aria2 failed: {e}"
            if progress_bar:
                progress_bar.update(1)
            return (url, False, error_msg)
        except subprocess.TimeoutExpired:
            error_msg = "aria2 timeout"
            if progress_bar:
                progress_bar.update(1)
            return (url, False, error_msg)


def _read_media_urls(media_file: str) -> Generator[str, None, None]:
    """
    Generator that yields URLs from wp_v2_media.jsonl file.

    Args:
        media_file: Path to the media file

    Yields:
        URL strings from the media file
    """
    try:
        with open(media_file, "r", encoding="utf8") as f:
            for line_num, row in enumerate(f, 1):
                row = row.strip()
                if not row:
                    continue
                try:
                    obj = json.loads(row)
                    if "source_url" in obj:
                        yield obj["source_url"]
                except json.JSONDecodeError as e:
                    logging.warning(f"Line {line_num}: Invalid JSON in media file: {e}")
                    continue
    except IOError as e:
        logging.error(f"Error reading {media_file}: {e}")
        raise


def _load_checkpoint(domain: str) -> set:
    """
    Load checkpoint of already downloaded files.

    Args:
        domain: Domain name used as output directory

    Returns:
        Set of file paths that have been downloaded
    """
    checkpoint_path = os.path.join(domain, CHECKPOINT_FILE)
    if not os.path.exists(checkpoint_path):
        return set()

    try:
        with open(checkpoint_path, "r", encoding="utf8") as f:
            data = json.load(f)
            return set(data.get("downloaded_files", []))
    except (IOError, json.JSONDecodeError) as e:
        logging.warning(f"Error loading checkpoint: {e}. Starting fresh.")
        return set()


def _save_checkpoint(domain: str, downloaded_files: set) -> None:
    """
    Save checkpoint of downloaded files.

    Args:
        domain: Domain name used as output directory
        downloaded_files: Set of file paths that have been downloaded
    """
    checkpoint_path = os.path.join(domain, CHECKPOINT_FILE)
    try:
        data = {"downloaded_files": list(downloaded_files), "last_updated": time.time()}
        with open(checkpoint_path, "w", encoding="utf8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logging.warning(f"Error saving checkpoint: {e}")


def _download_file_task(
    url: str, domain: str, verify_ssl: bool, checkpoint: set
) -> Tuple[str, bool, Optional[str]]:
    """
    Task function for downloading a single file.

    Args:
        url: URL to download
        domain: Domain name used as output directory
        verify_ssl: Whether to verify SSL certificates
        checkpoint: Set of already downloaded files

    Returns:
        Tuple of (url, success, error_message)
    """
    parsed = urlparse(url)
    filepath = os.path.join(domain, "files", parsed.path.lstrip("/"))

    # Check if already downloaded
    if filepath in checkpoint or os.path.exists(filepath):
        return (url, True, None)

    try:
        result = get_file(url, filepath, verify_ssl=verify_ssl)
        if result[1]:  # Success
            checkpoint.add(filepath)
        return result
    except Exception as e:
        return (url, False, str(e))


def collect_files(
    domain: str,
    verify_ssl: bool = True,
    workers: int = DEFAULT_WORKERS,
    resume: bool = True,
) -> Dict[str, int]:
    """
    Collect and download all media files listed in wp_v2_media.jsonl.

    Uses concurrent downloads for better performance and supports resume capability.

    Args:
        domain: Domain name used as output directory
        verify_ssl: Whether to verify SSL certificates (default: True)
        workers: Number of concurrent download workers (default: 5)
        resume: Whether to resume from checkpoint (default: True)

    Returns:
        Dictionary with statistics: {'downloaded': int, 'failed': int, 'skipped': int, 'total': int}
    """
    media_file = os.path.join(domain, "data", "wp_v2_media.jsonl")
    if not os.path.exists(media_file):
        raise MediaFileNotFoundError(media_file)

    # Load checkpoint if resuming
    checkpoint = _load_checkpoint(domain) if resume else set()

    # Collect all URLs first
    urls = list(_read_media_urls(media_file))
    total = len(urls)

    if total == 0:
        logging.warning("No media URLs found in file.")
        return {"downloaded": 0, "failed": 0, "skipped": 0, "total": 0}

    # Filter out already downloaded files
    if resume and checkpoint:
        urls_to_download = []
        skipped = 0
        for url in urls:
            parsed = urlparse(url)
            filepath = os.path.join(domain, "files", parsed.path.lstrip("/"))
            if filepath in checkpoint or os.path.exists(filepath):
                skipped += 1
            else:
                urls_to_download.append(url)
        urls = urls_to_download
        logging.info(
            f"Resuming: {skipped} files already downloaded, {len(urls)} remaining"
        )
    else:
        skipped = 0

    if not urls:
        logging.info("All files already downloaded.")
        return {"downloaded": 0, "failed": 0, "skipped": skipped, "total": total}

    downloaded = 0
    failed = 0
    failed_urls = []
    start_time = time.time()

    # Create progress bar
    if TQDM_AVAILABLE:
        pbar = tqdm(total=len(urls), desc="Downloading files", unit="file")
    else:
        pbar = None
        logging.info(
            f"Starting download of {len(urls)} files with {workers} workers..."
        )

    # Use ThreadPoolExecutor for concurrent downloads
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all download tasks
        future_to_url = {
            executor.submit(
                _download_file_task, url, domain, verify_ssl, checkpoint
            ): url
            for url in urls
        }

        # Process completed downloads
        for future in as_completed(future_to_url):
            url, success, error_msg = future.result()
            if success:
                downloaded += 1
            else:
                failed += 1
                failed_urls.append((url, error_msg))
                logging.debug(f"Failed to download {url}: {error_msg}")

            if pbar:
                pbar.update(1)

    if pbar:
        pbar.close()

    # Save checkpoint periodically
    if resume:
        _save_checkpoint(domain, checkpoint)

    # Print statistics
    elapsed = time.time() - start_time
    logging.info("=" * 60)
    logging.info("Download Statistics:")
    logging.info(f"  Total files: {total}")
    logging.info(f"  Downloaded: {downloaded}")
    logging.info(f"  Skipped (already exists): {skipped}")
    logging.info(f"  Failed: {failed}")
    logging.info(f"  Time elapsed: {format_duration(elapsed)}")
    if downloaded > 0:
        logging.info(f"  Average speed: {downloaded / elapsed:.2f} files/sec")
    logging.info("=" * 60)

    if failed > 0:
        logging.warning(f"{failed} files failed to download. Check logs for details.")

    return {
        "downloaded": downloaded,
        "failed": failed,
        "skipped": skipped,
        "total": total,
    }


def get_self_url(data: Dict) -> Optional[str]:
    """
    Extract self URL from WordPress API response data.

    Args:
        data: Dictionary containing _links information

    Returns:
        Self URL string or None if not found
    """
    if "_links" not in data.keys():
        return None
    if "self" not in data["_links"].keys():
        return None
    if isinstance(data["_links"]["self"], dict):
        return data["_links"]["self"]["href"]
    elif isinstance(data["_links"]["self"], str):
        return data["_links"]["self"]
    elif isinstance(data["_links"]["self"], list):
        if len(data["_links"]["self"]) == 0:
            return None
        return data["_links"]["self"][0]["href"]
    return None


def dump_route_list(
    url: str,
    route: str,
    filepath: str,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    page_size: int = WP_DEFAULT_PAGESIZE,
    retry_count: int = RETRY_COUNT,
) -> None:
    """
    Dump paginated route data to JSONL file.

    Args:
        url: Base URL for the route
        route: Route path (for logging)
        filepath: Output directory path
        verify_ssl: Whether to verify SSL certificates (default: True)
    """
    outfile = os.path.join(filepath, route.strip("/").replace("/", "_") + ".jsonl")
    page = 0
    outdata = []
    total_pages = None
    total_records = None

    while True:
        page += 1
        rc = 0
        resp = None

        while rc < retry_count:
            rc += 1
            try:
                page_url = (
                    f"{url}?page={page}&order=asc&orderby=id&per_page={page_size}"
                )
                resp = requests.get(
                    page_url, headers=REQUEST_HEADER, timeout=timeout, verify=verify_ssl
                )
                resp.raise_for_status()
                break
            except KeyboardInterrupt:
                logging.info("Interrupted by user")
                raise
            except requests.exceptions.RequestException as e:
                if rc == retry_count:
                    logging.error(
                        f"Failed to fetch page {page} after {retry_count} retries: {e}"
                    )
                    return
                logging.warning(f"Retry {rc}/{retry_count} for page {page}: {e}")
                continue

        if resp is None:
            logging.error("Failed to retrieve data after retries")
            return

        if resp.status_code != 200:
            logging.debug("- HTTP status code is %d, expected 200" % (resp.status_code))
            break

        # Extract pagination headers from first successful response
        if page == 1:
            total_pages_str = resp.headers.get('X-WP-TotalPages')
            total_records_str = resp.headers.get('X-WP-Total')
            if total_pages_str:
                try:
                    total_pages = int(total_pages_str)
                except (ValueError, TypeError):
                    logging.debug(f"Invalid X-WP-TotalPages header: {total_pages_str}")
            if total_records_str:
                try:
                    total_records = int(total_records_str)
                except (ValueError, TypeError):
                    logging.debug(f"Invalid X-WP-Total header: {total_records_str}")

        # Update logging to show progress with total pages if available
        if total_pages:
            logging.info("Processing page %d of %d for %s" % (page, total_pages, route))
        else:
            logging.info("Processing page %d of %s" % (page, route))

        try:
            data = resp.json()
        except ValueError as e:
            logging.error(f"Invalid JSON response for page {page}: {e}")
            break

        if isinstance(data, dict):
            logging.debug("- end of iteration %s" % (route))
            break
        elif isinstance(data, list):
            logging.debug(" - extracted %d records" % (len(data)))
            if len(data) == 0:
                break
            else:
                outdata.extend(data)
                logging.debug(" - num records %d less than %d" % (len(data), page_size))
#                if len(data) < page_size:
#                    break
        else:
            logging.warning(f"Unexpected response type: {type(data)}")
            break

        # Break if we've reached the total number of pages (when header is available)
        if total_pages and page >= total_pages:
            break

    # Summary logging after completion
    pages_processed = page - 1 if page > 0 else 0
    if total_records is not None:
        logging.info(
            "Completed %s: %d total records across %d page%s"
            % (route, total_records, pages_processed, "s" if pages_processed != 1 else "")
        )
    elif pages_processed > 0:
        logging.info(
            "Completed %s: %d record%s across %d page%s"
            % (
                route,
                len(outdata),
                "s" if len(outdata) != 1 else "",
                pages_processed,
                "s" if pages_processed != 1 else "",
            )
        )

    try:
        with open(outfile, "w", encoding="utf8") as f:
            for row in outdata:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except IOError as e:
        logging.error(f"Error writing to {outfile}: {e}")
        raise


def dump_route_dict(
    url: str,
    route: str,
    filepath: str,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
) -> None:
    """
    Dump non-paginated route data to JSON file.

    Args:
        url: URL for the route
        route: Route path (for logging)
        filepath: Output directory path
        verify_ssl: Whether to verify SSL certificates (default: True)
    """
    outfile = os.path.join(filepath, route.strip("/").replace("/", "_") + ".json")
    try:
        resp = requests.get(url, timeout=timeout, verify=verify_ssl)
        resp.raise_for_status()
        if resp.status_code == 200:
            with open(outfile, "w", encoding="utf8") as f:
                f.write(resp.text)
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        raise
    except IOError as e:
        logging.error(f"Error writing to {outfile}: {e}")
        raise


def ping(
    domain: str,
    force_https: bool = True,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict:
    """
    Ping WordPress API endpoint to verify it's accessible.

    Args:
        domain: Domain name (e.g., 'example.com')
        force_https: Force HTTPS instead of HTTP (default: True)
        verify_ssl: Whether to verify SSL certificates (default: True)
        timeout: Request timeout in seconds

    Returns:
        Dictionary with endpoint information

    Raises:
        APIError: If API request fails
        SSLVerificationError: If SSL verification fails
    """
    prefix = "https" if force_https else "http"
    url = prefix + "://" + domain + "/wp-json/"

    try:
        wptext = requests.get(
            url, headers=REQUEST_HEADER, timeout=timeout, verify=verify_ssl
        )
        wptext.raise_for_status()

        wpjson = wptext.json()
        if "routes" not in wpjson:
            logging.warning(f"Unexpected response format from {url}")
            return {}

        allroutes = list(wpjson["routes"].keys())
        logging.info("Endpoint %s is OK" % (url))
        logging.info("Total routes %d" % (len(allroutes)))
        return {"url": url, "routes_count": len(allroutes), "routes": allroutes}
    except requests.exceptions.SSLError as e:
        raise SSLVerificationError(url, str(e))
    except requests.exceptions.HTTPError as e:
        raise APIError(url, status_code=e.response.status_code, message=str(e))
    except requests.exceptions.RequestException as e:
        raise APIError(url, message=str(e))
    except (KeyError, ValueError) as e:
        raise APIError(url, message=f"Invalid response format: {e}")
    except Exception as e:
        raise APIError(url, message=f"Unexpected error: {e}")


def analyze_routes(
    domain: str,
    force_https: bool = True,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict:
    """
    Analyze WordPress API routes and compare against known routes.

    Args:
        domain: Domain name (e.g., 'example.com')
        force_https: Force HTTPS instead of HTTP (default: True)
        verify_ssl: Whether to verify SSL certificates (default: True)
        timeout: Request timeout in seconds

    Returns:
        Dictionary with analysis results containing:
        - total_routes: Total number of routes found
        - known_routes: Dict mapping route -> category
        - unknown_routes: List of routes not in any known category
        - statistics: Dict with counts per category

    Raises:
        APIError: If API request fails
        SSLVerificationError: If SSL verification fails
    """
    prefix = "https" if force_https else "http"
    url = prefix + "://" + domain + "/wp-json/"
    known_routes_filename = _get_resource_filename("wparc", "data/known_routes.yml")

    # Load known routes
    try:
        with open(known_routes_filename, "r", encoding="utf8") as f:
            known_routes = yaml.load(f, Loader=Loader)
    except IOError as e:
        logging.error(f"Error reading known routes file: {e}")
        raise

    # Fetch routes from WordPress API
    try:
        wptext = requests.get(
            url, headers=REQUEST_HEADER, timeout=timeout, verify=verify_ssl
        )
        wptext.raise_for_status()
        wpjson = wptext.json()
        if "routes" not in wpjson:
            logging.warning(f"Unexpected response format from {url}")
            return {
                "url": url,
                "total_routes": 0,
                "known_routes": {},
                "unknown_routes": [],
                "statistics": {
                    "protected": 0,
                    "public-list": 0,
                    "public-dict": 0,
                    "useless": 0,
                    "unknown": 0,
                },
            }

        allroutes = list(wpjson["routes"].keys())
        total_routes = len(allroutes)

        # Categorize routes
        known_routes_dict = {}
        unknown_routes_list = []
        statistics = {
            "protected": 0,
            "public-list": 0,
            "public-dict": 0,
            "useless": 0,
            "unknown": 0,
        }

        # Create progress bar
        if TQDM_AVAILABLE:
            pbar = tqdm(total=total_routes, desc="Analyzing routes", unit="route")
        else:
            pbar = None
            logging.info(f"Analyzing {total_routes} routes...")

        try:
            for route in allroutes:
                if route in known_routes.get("protected", []):
                    known_routes_dict[route] = "protected"
                    statistics["protected"] += 1
                elif route in known_routes.get("public-list", []):
                    known_routes_dict[route] = "public-list"
                    statistics["public-list"] += 1
                elif route in known_routes.get("public-dict", []):
                    known_routes_dict[route] = "public-dict"
                    statistics["public-dict"] += 1
                elif route in known_routes.get("useless", []):
                    known_routes_dict[route] = "useless"
                    statistics["useless"] += 1
                else:
                    unknown_routes_list.append(route)
                    statistics["unknown"] += 1

                if pbar:
                    pbar.update(1)
        finally:
            if pbar:
                pbar.close()

        return {
            "url": url,
            "total_routes": total_routes,
            "known_routes": known_routes_dict,
            "unknown_routes": unknown_routes_list,
            "statistics": statistics,
            "wpjson": wpjson,  # Include wpjson for route testing
        }
    except requests.exceptions.SSLError as e:
        raise SSLVerificationError(url, str(e))
    except requests.exceptions.HTTPError as e:
        raise APIError(url, status_code=e.response.status_code, message=str(e))
    except requests.exceptions.RequestException as e:
        raise APIError(url, message=str(e))
    except (KeyError, ValueError) as e:
        raise APIError(url, message=f"Invalid response format: {e}")
    except Exception as e:
        raise APIError(url, message=f"Unexpected error: {e}")


def _test_route(
    route: str,
    route_data: Dict,
    base_url: str,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[str]:
    """
    Test a route and determine its category.

    Args:
        route: Route path (e.g., '/wp/v2/posts')
        route_data: Route data from wpjson['routes'][route]
        base_url: Base URL for the WordPress site
        verify_ssl: Whether to verify SSL certificates
        timeout: Request timeout in seconds

    Returns:
        Category string: 'protected', 'public-list', 'public-dict', 'useless', or None if cannot determine
    """
    # Check if route has regex patterns (usually useless)
    if "?P<" in route:
        return "useless"

    # Check endpoint definitions
    endpoints = route_data.get("endpoints", [])
    if len(endpoints) == 0:
        return None

    endpoint = endpoints[0]
    args = endpoint.get("args", {})

    # Check if it's a paginated list endpoint
    if isinstance(args, dict) and "page" in args and "per_page" in args:
        # Try to make a request to verify it's public-list
        route_url = get_self_url(route_data)
        if route_url:
            try:
                resp = requests.get(
                    f"{route_url}?per_page=1&page=1",
                    headers=REQUEST_HEADER,
                    timeout=timeout,
                    verify=verify_ssl,
                )
                if resp.status_code == 401 or resp.status_code == 403:
                    return "protected"
                elif resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, list):
                            return "public-list"
                    except ValueError:
                        pass
            except requests.exceptions.RequestException:
                pass

    # Try to fetch the route to determine category
    route_url = get_self_url(route_data)
    if not route_url:
        return None

    try:
        resp = requests.get(
            route_url, headers=REQUEST_HEADER, timeout=timeout, verify=verify_ssl
        )

        # Check if protected (requires authentication)
        if resp.status_code == 401 or resp.status_code == 403:
            return "protected"

        # Check if it's an individual item endpoint (useless)
        # These usually have patterns like /wp/v2/posts/(?P<id>[\d]+)
        # But we already checked for ?P< above, so check for numeric-like patterns
        if any(char.isdigit() for char in route.split("/")[-1]) and len(route.split("/")) > 3:
            # Could be an individual item endpoint, check response
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # If it's a single object (dict) and not a list, it's likely useless
                    if isinstance(data, dict) and "id" in data:
                        return "useless"
                except ValueError:
                    pass

        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, list):
                    return "public-list"
                elif isinstance(data, dict):
                    return "public-dict"
            except ValueError:
                pass

    except requests.exceptions.RequestException:
        # If request fails, try to determine from endpoint definition
        if isinstance(args, dict) and "page" in args and "per_page" in args:
            return "public-list"
        elif isinstance(args, dict):
            return "public-dict"

    return None


def test_unknown_routes(
    unknown_routes: list,
    wpjson: Dict,
    base_url: str,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, list]:
    """
    Test unknown routes and categorize them.

    Args:
        unknown_routes: List of unknown route paths
        wpjson: WordPress API JSON response containing routes
        base_url: Base URL for the WordPress site
        verify_ssl: Whether to verify SSL certificates
        timeout: Request timeout in seconds

    Returns:
        Dictionary mapping category -> list of routes
    """
    categorized = {
        "protected": [],
        "public-list": [],
        "public-dict": [],
        "useless": [],
    }

    # Create progress bar
    if TQDM_AVAILABLE:
        pbar = tqdm(total=len(unknown_routes), desc="Testing routes", unit="route")
    else:
        pbar = None
        logging.info(f"Testing {len(unknown_routes)} unknown routes...")

    try:
        for route in unknown_routes:
            if route not in wpjson.get("routes", {}):
                if pbar:
                    pbar.update(1)
                continue

            route_data = wpjson["routes"][route]
            category = _test_route(route, route_data, base_url, verify_ssl, timeout)

            if category and category in categorized:
                categorized[category].append(route)
            else:
                # If cannot determine, default to useless (safer)
                categorized["useless"].append(route)

            if pbar:
                pbar.update(1)
    finally:
        if pbar:
            pbar.close()

    return categorized


def generate_routes_yaml(categorized_routes: Dict[str, list]) -> str:
    """
    Generate YAML update for known_routes.yml file.

    Args:
        categorized_routes: Dictionary mapping category -> list of routes

    Returns:
        YAML string in the same format as known_routes.yml
    """
    yaml_lines = []
    categories = ["protected", "public-list", "public-dict", "useless"]

    for category in categories:
        routes = categorized_routes.get(category, [])
        if routes:
            yaml_lines.append(f"{category}:")
            for route in sorted(routes):
                yaml_lines.append(f"- {route}")

    return "\n".join(yaml_lines)


def collect_data(
    domain: str,
    get_unknown: bool = True,
    force_https: bool = True,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    page_size: int = WP_DEFAULT_PAGESIZE,
    retry_count: int = RETRY_COUNT,
) -> Dict[str, int]:
    """
    Collect all data from WordPress API.

    Args:
        domain: Domain name to crawl
        get_unknown: Include unknown API routes
        force_https: Force HTTPS protocol (default: True)
        verify_ssl: Whether to verify SSL certificates (default: True)
        timeout: Request timeout in seconds
        page_size: Number of items per page
        retry_count: Number of retry attempts

    Returns:
        Dictionary with statistics: {'routes_processed': int, 'routes_skipped': int, 'total_routes': int}

    Raises:
        APIError: If API request fails
        SSLVerificationError: If SSL verification fails
    """
    prefix = "https" if force_https else "http"
    known_routes_filename = _get_resource_filename("wparc", "data/known_routes.yml")

    try:
        with open(known_routes_filename, "r", encoding="utf8") as f:
            known_routes = yaml.load(f, Loader=Loader)
    except IOError as e:
        logging.error(f"Error reading known routes file: {e}")
        raise

    url = prefix + "://" + domain + "/wp-json/"

    try:
        wptext = requests.get(
            url, headers=REQUEST_HEADER, timeout=timeout, verify=verify_ssl
        )
        wptext.raise_for_status()
        wpjson = wptext.json()
    except requests.exceptions.SSLError as e:
        raise SSLVerificationError(url, str(e))
    except requests.exceptions.HTTPError as e:
        raise APIError(url, status_code=e.response.status_code, message=str(e))
    except requests.exceptions.RequestException as e:
        raise APIError(url, message=str(e))
    except ValueError as e:
        raise APIError(url, message=f"Invalid JSON response: {e}")

    allroutes = list(wpjson["routes"].keys())
    total_routes = len(allroutes)
    logging.info("Total routes %d" % (total_routes))

    os.makedirs(os.path.join(domain, "data"), exist_ok=True)

    try:
        with open(
            os.path.join(domain, "data", "wp-json.json"), "w", encoding="utf8"
        ) as f:
            f.write(json.dumps(wpjson, ensure_ascii=False))
    except IOError as e:
        logging.error(f"Error writing wp-json.json: {e}")
        raise

    routes_processed = 0
    routes_skipped = 0
    start_time = time.time()

    # Create progress bar for routes
    if TQDM_AVAILABLE:
        pbar = tqdm(total=total_routes, desc="Processing routes", unit="route")
    else:
        pbar = None

    for route in allroutes:
        try:
            if route in known_routes["public-list"]:
                route_url = get_self_url(wpjson["routes"][route])
                if route_url is None:
                    logging.warning(f"Could not get URL for route {route}, skipping")
                    routes_skipped += 1
                    continue
                logging.info("Dump objects route %s" % (route))
                dump_route_list(
                    url=route_url,
                    route=route,
                    filepath=os.path.join(domain, "data"),
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                    page_size=page_size,
                    retry_count=retry_count,
                )
                routes_processed += 1
            elif route in known_routes["public-dict"]:
                route_url = get_self_url(wpjson["routes"][route])
                if route_url is None:
                    logging.warning(f"Could not get URL for route {route}, skipping")
                    routes_skipped += 1
                    continue
                logging.info("Dump dict route %s" % (route))
                dump_route_dict(
                    url=route_url,
                    route=route,
                    filepath=os.path.join(domain, "data"),
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                )
                routes_processed += 1
            elif route in known_routes["protected"]:
                logging.debug("Route %s is protected. Skip" % (route))
                routes_skipped += 1
            elif route in known_routes["useless"]:
                logging.debug("Route %s is useless. Skip" % (route))
                routes_skipped += 1
            elif "?P" in route:
                logging.info("[!] Route %s is unknown and has regexp. Skip" % (route))
                routes_skipped += 1
            else:
                logging.info("[!] Route %s is unknown." % (route))
                if get_unknown:
                    endpoints = wpjson["routes"][route]["endpoints"]
                    if len(endpoints) > 0:
                        route_url = get_self_url(wpjson["routes"][route])
                        if route_url is None:
                            logging.warning(
                                f"Could not get URL for route {route}, skipping"
                            )
                            routes_skipped += 1
                        else:
                            if (
                                not isinstance(endpoints[0]["args"], list)
                                and "page" in endpoints[0]["args"].keys()
                                and "per_page" in endpoints[0]["args"].keys()
                            ):
                                logging.info("Dump objects route %s" % (route))
                                dump_route_list(
                                    url=route_url,
                                    route=route,
                                    filepath=os.path.join(domain, "data"),
                                    verify_ssl=verify_ssl,
                                    timeout=timeout,
                                    page_size=page_size,
                                    retry_count=retry_count,
                                )
                                routes_processed += 1
                            else:
                                logging.info("Dump dict route %s" % (route))
                                dump_route_dict(
                                    url=route_url,
                                    route=route,
                                    filepath=os.path.join(domain, "data"),
                                    verify_ssl=verify_ssl,
                                    timeout=timeout,
                                )
                                routes_processed += 1
                    else:
                        routes_skipped += 1
                else:
                    routes_skipped += 1
        except Exception as e:
            logging.error(f"Error processing route {route}: {e}")
            routes_skipped += 1
        finally:
            if pbar:
                pbar.update(1)

    if pbar:
        pbar.close()

    # Print statistics
    elapsed = time.time() - start_time
    logging.info("=" * 60)
    logging.info("Data Collection Statistics:")
    logging.info(f"  Total routes: {total_routes}")
    logging.info(f"  Processed: {routes_processed}")
    logging.info(f"  Skipped: {routes_skipped}")
    logging.info(f"  Time elapsed: {format_duration(elapsed)}")
    logging.info("=" * 60)

    return {
        "routes_processed": routes_processed,
        "routes_skipped": routes_skipped,
        "total_routes": total_routes,
    }
