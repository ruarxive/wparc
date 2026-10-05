# -*- coding: utf-8 -*-
"""
WordPress API data dump module.

Provides functions to dump WordPress API route data to JSONL/JSON files
and orchestrate full data collection.
"""
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, Set, Tuple

import requests

from ..exceptions import APIError, SSLVerificationError
from ..utils import format_duration
from ._common import (
    DEFAULT_TIMEOUT,
    TQDM_AVAILABLE,
    get_ssl_warning_context,
    tqdm,
)
from .routes import get_self_url

# Local module-level configuration -------------------------------------------------
WP_DEFAULT_PAGESIZE = 100
RETRY_COUNT = 5

# Backwards-compatible re-exports so existing imports of these names from
# ``wparc.wpapi.dump`` (e.g. ``from wparc.wpapi.dump import TQDM_AVAILABLE``,
# used in tests) keep working after the consolidation in :mod:`wparc.wpapi._common`.
TQDM_AVAILABLE = TQDM_AVAILABLE  # noqa: F841 - re-exported for back-compat
_get_ssl_warning_context = get_ssl_warning_context  # noqa: F841 - re-exported


def _rate_limit_sleep(delay: float) -> None:
    """Sleep ``delay`` seconds when rate-limiting is requested."""
    if delay > 0:
        time.sleep(delay)


def dump_route_list(
    url: str,
    route: str,
    filepath: str,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    page_size: int = WP_DEFAULT_PAGESIZE,
    retry_count: int = RETRY_COUNT,
    auth: Optional[Tuple[str, str]] = None,
    proxy: Optional[str] = None,
    rate_limit_delay: float = 0.0,
) -> bool:
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
        auth: Optional HTTP Basic Auth tuple ``(user, password)``.
        proxy: Optional HTTP proxy URL.
        rate_limit_delay: Seconds to sleep between successful page fetches.

    Returns:
        True if any rows were written, False if the route was empty or
        every retry failed. Failures are logged, never raised.
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
                page_url = f"{url}?page={page}&order=asc&orderby=id" f"&per_page={page_size}"
                from ._common import REQUEST_HEADER

                with get_ssl_warning_context(verify_ssl):
                    resp = requests.get(
                        page_url,
                        headers=REQUEST_HEADER,
                        timeout=timeout,
                        verify=verify_ssl,
                        auth=auth,
                        proxies=({"http": proxy, "https": proxy} if proxy else None),
                    )
                resp.raise_for_status()
                break
            except KeyboardInterrupt:
                logging.info("Interrupted by user")
                raise
            except requests.exceptions.RequestException as e:
                if rc == retry_count:
                    logging.error(
                        f"Failed to fetch page {page} after " f"{retry_count} retries: {e}"
                    )
                    return False
                # Exponential backoff between retries (capped at 8 s).
                backoff = min(2**rc * 0.25, 8.0)
                logging.warning(f"Retry {rc}/{retry_count} for page {page} in {backoff:.1f}s: {e}")
                time.sleep(backoff)
                continue

        if resp is None:
            logging.error("Failed to retrieve data after retries")
            return False

        if resp.status_code != 200:
            logging.debug("- HTTP status code is %d, expected 200" % (resp.status_code))
            break

        # Extract pagination headers from first successful response
        if page == 1:
            total_pages_str = resp.headers.get("X-WP-TotalPages")
            total_records_str = resp.headers.get("X-WP-Total")
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
        else:
            logging.warning(f"Unexpected response type: {type(data)}")
            break

        # Respect rate-limit between successful pages.
        _rate_limit_sleep(rate_limit_delay)

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
        return bool(outdata)
    except IOError as e:
        logging.error(f"Error writing to {outfile}: {e}")
        return False


def dump_route_dict(
    url: str,
    route: str,
    filepath: str,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Optional[Tuple[str, str]] = None,
    proxy: Optional[str] = None,
    rate_limit_delay: float = 0.0,
) -> bool:
    """
    Dump non-paginated route data to JSON file.

    Args:
        url: URL for the route
        route: Route path (for logging)
        filepath: Output directory path
        verify_ssl: Whether to verify SSL certificates (default: True)
        timeout: Request timeout in seconds
        auth: Optional HTTP Basic Auth tuple ``(user, password)``.
        proxy: Optional HTTP proxy URL.
        rate_limit_delay: Seconds to sleep after a successful fetch.

    Returns:
        True on success, False on failure. The function logs the reason
        for the failure and never raises ``RequestException``; callers
        in :func:`collect_data` count failures against
        ``routes_skipped`` instead of crashing the entire dump.
    """
    from ._common import REQUEST_HEADER

    outfile = os.path.join(filepath, route.strip("/").replace("/", "_") + ".json")
    try:
        with get_ssl_warning_context(verify_ssl):
            resp = requests.get(
                url,
                headers=REQUEST_HEADER,
                timeout=timeout,
                verify=verify_ssl,
                auth=auth,
                proxies=({"http": proxy, "https": proxy} if proxy else None),
            )
        resp.raise_for_status()
        if resp.status_code == 200:
            with open(outfile, "w", encoding="utf8") as f:
                f.write(resp.text)
            _rate_limit_sleep(rate_limit_delay)
            return True
        # Non-200 responses are still "no data we can use"; not an error.
        logging.debug("Skipping %s: HTTP %s", url, resp.status_code)
        return False
    except requests.exceptions.RequestException as e:
        # C6: do NOT re-raise — log and report failure so the surrounding
        # ``collect_data`` loop can continue with the next route.
        logging.error(f"Failed to fetch {url}: {e}")
        return False
    except IOError as e:
        logging.error(f"Error writing to {outfile}: {e}")
        return False


def _is_paginated_endpoint(route_data: Dict) -> bool:
    """Return True when the first endpoint advertises ``page`` + ``per_page`` args."""
    endpoints = route_data.get("endpoints", [])
    if not endpoints:
        return False
    args = endpoints[0].get("args", {})
    return not isinstance(args, list) and "page" in args and "per_page" in args


def _handle_unknown_route(
    route: str,
    route_data: Dict,
    filepath: str,
    verify_ssl: bool,
    timeout: int,
    page_size: int,
    retry_count: int,
    auth: Optional[Tuple[str, str]] = None,
    proxy: Optional[str] = None,
    rate_limit_delay: float = 0.0,
) -> bool:
    """Process a route that is not in known_routes.yml.

    Returns True if data was extracted, False otherwise. Mirrors the
    inlined logic that previously lived in :func:`collect_data`.
    """
    logging.info("[!] Route %s is unknown." % (route))
    endpoints = route_data.get("endpoints", [])
    if not endpoints:
        return False
    route_url = get_self_url(route_data)
    if route_url is None:
        logging.warning(f"Could not get URL for route {route}, skipping")
        return False
    if _is_paginated_endpoint(route_data):
        logging.info("Dump objects route %s" % (route))
        return dump_route_list(
            url=route_url,
            route=route,
            filepath=filepath,
            verify_ssl=verify_ssl,
            timeout=timeout,
            page_size=page_size,
            retry_count=retry_count,
            auth=auth,
            proxy=proxy,
            rate_limit_delay=rate_limit_delay,
        )
    logging.info("Dump dict route %s" % (route))
    return dump_route_dict(
        url=route_url,
        route=route,
        filepath=filepath,
        verify_ssl=verify_ssl,
        timeout=timeout,
        auth=auth,
        proxy=proxy,
        rate_limit_delay=rate_limit_delay,
    )


def collect_data(
    domain: str,
    get_unknown: bool = True,
    force_https: bool = True,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    page_size: int = WP_DEFAULT_PAGESIZE,
    retry_count: int = RETRY_COUNT,
    auth: Optional[Tuple[str, str]] = None,
    proxy: Optional[str] = None,
    rate_limit_delay: float = 0.0,
    workers: int = 1,
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
        auth: Optional ``(user, password)`` tuple for HTTP Basic Auth.
        proxy: Optional HTTP proxy URL.
        rate_limit_delay: Seconds to sleep between successive HTTP requests.
        workers: Number of routes to dump in parallel via a
            ``ThreadPoolExecutor`` (default 1 = serial). WP-JSON is
            I/O-bound so threading scales well; values above 8 rarely
            help and may anger the WordPress server.

    Returns:
        Dict with stats:
            {'routes_processed': int, 'routes_skipped': int, 'total_routes': int}

    Raises:
        APIError: If API request fails
        SSLVerificationError: If SSL verification fails
    """
    prefix = "https" if force_https else "http"

    # Load known routes (cached at module level via routes._load_known_routes).
    try:
        from .routes import _load_known_routes

        known_routes = _load_known_routes()
    except IOError as e:
        logging.error(f"Error reading known routes file: {e}")
        raise

    url = prefix + "://" + domain + "/wp-json/"

    from ._common import REQUEST_HEADER

    try:
        with get_ssl_warning_context(verify_ssl):
            wptext = requests.get(
                url,
                headers=REQUEST_HEADER,
                timeout=timeout,
                verify=verify_ssl,
                auth=auth,
                proxies={"http": proxy, "https": proxy} if proxy else None,
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

    _rate_limit_sleep(rate_limit_delay)

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
        with open(os.path.join(domain, "data", "wp-json.json"), "w", encoding="utf8") as f:
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

    # Collect (callable, kwargs) tuples for routes that actually need a dump.
    jobs = []
    for route in allroutes:
        try:
            if route in public_list:
                route_url = get_self_url(wpjson["routes"][route])
                if route_url is None:
                    logging.warning(f"Could not get URL for route {route}, skipping")
                    routes_skipped += 1
                    continue
                jobs.append(
                    (
                        _run_dump_route_list,
                        dict(
                            url=route_url,
                            route=route,
                            filepath=os.path.join(domain, "data"),
                            verify_ssl=verify_ssl,
                            timeout=timeout,
                            page_size=page_size,
                            retry_count=retry_count,
                            auth=auth,
                            proxy=proxy,
                            rate_limit_delay=rate_limit_delay,
                        ),
                    )
                )
            elif route in public_dict:
                route_url = get_self_url(wpjson["routes"][route])
                if route_url is None:
                    logging.warning(f"Could not get URL for route {route}, skipping")
                    routes_skipped += 1
                    continue
                jobs.append(
                    (
                        _run_dump_route_dict,
                        dict(
                            url=route_url,
                            route=route,
                            filepath=os.path.join(domain, "data"),
                            verify_ssl=verify_ssl,
                            timeout=timeout,
                            auth=auth,
                            proxy=proxy,
                            rate_limit_delay=rate_limit_delay,
                        ),
                    )
                )
            elif route in protected:
                logging.debug("Route %s is protected. Skip" % (route))
                routes_skipped += 1
            elif route in useless:
                logging.debug("Route %s is useless. Skip" % (route))
                routes_skipped += 1
            elif "?P" in route:
                logging.info("[!] Route %s is unknown and has regexp. Skip" % (route))
                routes_skipped += 1
            else:
                if get_unknown:
                    ok = _handle_unknown_route(
                        route=route,
                        route_data=wpjson["routes"][route],
                        filepath=os.path.join(domain, "data"),
                        verify_ssl=verify_ssl,
                        timeout=timeout,
                        page_size=page_size,
                        retry_count=retry_count,
                        auth=auth,
                        proxy=proxy,
                        rate_limit_delay=rate_limit_delay,
                    )
                    if ok:
                        routes_processed += 1
                    else:
                        routes_skipped += 1
                else:
                    routes_skipped += 1
        except Exception as e:
            logging.error(f"Error processing route {route}: {e}")
            routes_skipped += 1

    # Execute the jobs in parallel when ``workers > 1``.
    if workers > 1 and jobs:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_job = {executor.submit(fn, **kwargs): fn for fn, kwargs in jobs}
            for future in as_completed(future_to_job):
                try:
                    ok = future.result()
                except Exception as e:
                    logging.error(f"Worker failed: {e}")
                    ok = False
                if ok:
                    routes_processed += 1
                else:
                    routes_skipped += 1
                if pbar:
                    pbar.update(1)
    else:
        # Serial path — covers workers <= 1 and avoids thread overhead.
        for fn, kwargs in jobs:
            try:
                ok = fn(**kwargs)
            except Exception as e:
                logging.error(f"Error processing {kwargs.get('route', '?')}: {e}")
                ok = False
            if ok:
                routes_processed += 1
            else:
                routes_skipped += 1
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


# Worker entry points used by the parallel executor. They isolate the
# work-item payload from pickling the entire ``wparc.wpapi.dump``
# module into each thread (which would re-parse YAML and re-import
# urllib3 in every work-item).


def _run_dump_route_list(**kwargs) -> bool:
    """Worker entry point: dump a paginated list route."""
    return dump_route_list(**kwargs)


def _run_dump_route_dict(**kwargs) -> bool:
    """Worker entry point: dump a single-dict route."""
    return dump_route_dict(**kwargs)
