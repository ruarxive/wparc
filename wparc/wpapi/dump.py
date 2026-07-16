# -*- coding: utf-8 -*-
"""
WordPress API data dump module.

Provides functions to dump WordPress API route data to JSONL/JSON files
and orchestrate full data collection.
"""
import contextlib
import json
import logging
import os
import time
from typing import Dict, Set

import requests
import urllib3
import yaml

from ..exceptions import APIError, SSLVerificationError
from ..utils import format_duration
from .resources import get_resource_filename
from .routes import get_self_url

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

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


DEFAULT_TIMEOUT = 360
WP_DEFAULT_PAGESIZE = 100
RETRY_COUNT = 5


def _get_ssl_warning_context(verify_ssl: bool):
    """Return context manager suppressing SSL warnings when verify_ssl is False."""
    if not verify_ssl:
        return urllib3_warnings_suppressed()
    return contextlib.nullcontext()


@contextlib.contextmanager
def urllib3_warnings_suppressed():
    """Context manager to temporarily suppress urllib3 InsecureRequestWarning."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        yield
    finally:
        urllib3.enable_warnings()


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
        timeout: Request timeout in seconds
        page_size: Number of items per page
        retry_count: Number of retry attempts
    """
    outfile = os.path.join(
        filepath, route.strip("/").replace("/", "_") + ".jsonl"
    )
    page = 0
    outdata = []
    total_pages = None
    total_records = None

    user_agent = (
        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build MRA58N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/67.0.3396.99 Mobile Safari/537.36"
    )

    while True:
        page += 1
        rc = 0
        resp = None

        while rc < retry_count:
            rc += 1
            try:
                page_url = (
                    f"{url}?page={page}&order=asc&orderby=id"
                    f"&per_page={page_size}"
                )
                with _get_ssl_warning_context(verify_ssl):
                    resp = requests.get(
                        page_url,
                        headers={"User-Agent": user_agent},
                        timeout=timeout,
                        verify=verify_ssl,
                    )
                resp.raise_for_status()
                break
            except KeyboardInterrupt:
                logging.info("Interrupted by user")
                raise
            except requests.exceptions.RequestException as e:
                if rc == retry_count:
                    logging.error(
                        f"Failed to fetch page {page} after "
                        f"{retry_count} retries: {e}"
                    )
                    return
                logging.warning(
                    f"Retry {rc}/{retry_count} for page {page}: {e}"
                )
                continue

        if resp is None:
            logging.error("Failed to retrieve data after retries")
            return

        if resp.status_code != 200:
            logging.debug(
                "- HTTP status code is %d, expected 200" % (resp.status_code)
            )
            break

        # Extract pagination headers from first successful response
        if page == 1:
            total_pages_str = resp.headers.get("X-WP-TotalPages")
            total_records_str = resp.headers.get("X-WP-Total")
            if total_pages_str:
                try:
                    total_pages = int(total_pages_str)
                except (ValueError, TypeError):
                    logging.debug(
                        f"Invalid X-WP-TotalPages header: {total_pages_str}"
                    )
            if total_records_str:
                try:
                    total_records = int(total_records_str)
                except (ValueError, TypeError):
                    logging.debug(
                        f"Invalid X-WP-Total header: {total_records_str}"
                    )

        # Update logging to show progress with total pages if available
        if total_pages:
            logging.info(
                "Processing page %d of %d for %s"
                % (page, total_pages, route)
            )
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
        else:
            logging.warning(f"Unexpected response type: {type(data)}")
            break

        # Break if we've reached the total number of pages
        if total_pages and page >= total_pages:
            break

    # Summary logging
    pages_processed = page - 1 if page > 0 else 0
    if total_records is not None:
        logging.info(
            "Completed %s: %d total records across %d page%s"
            % (
                route,
                total_records,
                pages_processed,
                "s" if pages_processed != 1 else "",
            )
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
        timeout: Request timeout in seconds
    """
    outfile = os.path.join(
        filepath, route.strip("/").replace("/", "_") + ".json"
    )
    try:
        with _get_ssl_warning_context(verify_ssl):
            resp = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Linux; Android 6.0; "
                        "Nexus 5 Build MRA58N) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/67.0.3396.99 Mobile Safari/537.36"
                    )
                },
                timeout=timeout,
                verify=verify_ssl,
            )
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
        Dict with stats:
            {'routes_processed': int, 'routes_skipped': int, 'total_routes': int}

    Raises:
        APIError: If API request fails
        SSLVerificationError: If SSL verification fails
    """
    prefix = "https" if force_https else "http"
    known_routes_filename = get_resource_filename(
        "wparc", "data/known_routes.yml"
    )

    try:
        with open(known_routes_filename, "r", encoding="utf8") as f:
            known_routes = yaml.safe_load(f)
    except IOError as e:
        logging.error(f"Error reading known routes file: {e}")
        raise

    url = prefix + "://" + domain + "/wp-json/"

    user_agent = (
        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build MRA58N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/67.0.3396.99 Mobile Safari/537.36"
    )

    try:
        with _get_ssl_warning_context(verify_ssl):
            wptext = requests.get(
                url,
                headers={"User-Agent": user_agent},
                timeout=timeout,
                verify=verify_ssl,
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

    # Convert to sets for O(1) lookups with safe defaults
    public_list: Set = set(known_routes.get("public-list", []))
    public_dict: Set = set(known_routes.get("public-dict", []))
    protected: Set = set(known_routes.get("protected", []))
    useless: Set = set(known_routes.get("useless", []))

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

    if TQDM_AVAILABLE:
        pbar = tqdm(total=total_routes, desc="Processing routes", unit="route")
    else:
        pbar = None

    for route in allroutes:
        try:
            if route in public_list:
                route_url = get_self_url(wpjson["routes"][route])
                if route_url is None:
                    logging.warning(
                        f"Could not get URL for route {route}, skipping"
                    )
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
            elif route in public_dict:
                route_url = get_self_url(wpjson["routes"][route])
                if route_url is None:
                    logging.warning(
                        f"Could not get URL for route {route}, skipping"
                    )
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
            elif route in protected:
                logging.debug("Route %s is protected. Skip" % (route))
                routes_skipped += 1
            elif route in useless:
                logging.debug("Route %s is useless. Skip" % (route))
                routes_skipped += 1
            elif "?P" in route:
                logging.info(
                    "[!] Route %s is unknown and has regexp. Skip" % (route)
                )
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
                                logging.info(
                                    "Dump objects route %s" % (route)
                                )
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
                                logging.info(
                                    "Dump dict route %s" % (route)
                                )
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
