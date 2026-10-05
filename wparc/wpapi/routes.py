# -*- coding: utf-8 -*-
"""
WordPress API route analysis module.

Provides functions to discover, categorize, and test WordPress API routes.
"""
import functools
import logging
import time
from typing import Dict, List, Optional, Set, Tuple

import requests

import yaml

from ..exceptions import APIError, SSLVerificationError
from ._common import (
    DEFAULT_TIMEOUT,
    REQUEST_HEADER,
    TQDM_AVAILABLE,
    get_ssl_warning_context,
    tqdm,
)
from .resources import get_resource_filename

# Backwards-compatible alias retained for any downstream import
# (e.g. tests or external scripts that historically imported
# ``_get_ssl_warning_context`` from ``wparc.wpapi.routes``).
_get_ssl_warning_context = get_ssl_warning_context  # noqa: F841 - re-exported


def _rate_limit_sleep(delay: float) -> None:
    """Sleep ``delay`` seconds when rate-limiting is requested."""
    if delay > 0:
        time.sleep(delay)


def _proxies(proxy: Optional[str]) -> Optional[Dict[str, str]]:
    """Map a proxy URL to the shape ``requests`` expects (or None)."""
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


@functools.lru_cache(maxsize=1)
def _load_known_routes() -> Dict[str, List[str]]:
    """Load and cache ``data/known_routes.yml``.

    Parsing the YAML once per process saves ~100 ms on every ``dump``
    and ``analyze`` invocation, both of which used to call
    ``yaml.safe_load`` on a 1 180-line file.

    The cache is invalidated automatically when the package is
    reinstalled (the on-disk file changes); otherwise it lives for the
    lifetime of the Python process.
    """
    path = get_resource_filename("wparc", "data/known_routes.yml")
    with open(path, "r", encoding="utf8") as f:
        return yaml.safe_load(f) or {}


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


def ping(
    domain: str,
    force_https: bool = True,
    verify_ssl: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    auth: Optional[Tuple[str, str]] = None,
    proxy: Optional[str] = None,
    rate_limit_delay: float = 0.0,
) -> Dict:
    """
    Ping WordPress API endpoint to verify it's accessible.

    Args:
        domain: Domain name (e.g., 'example.com')
        force_https: Force HTTPS instead of HTTP (default: True)
        verify_ssl: Whether to verify SSL certificates (default: True)
        timeout: Request timeout in seconds
        auth: Optional HTTP Basic Auth tuple ``(user, password)``.
        proxy: Optional HTTP proxy URL.
        rate_limit_delay: Seconds to sleep after a successful response.

    Returns:
        Dictionary with endpoint information

    Raises:
        APIError: If API request fails
        SSLVerificationError: If SSL verification fails
    """
    prefix = "https" if force_https else "http"
    url = prefix + "://" + domain + "/wp-json/"

    try:
        with get_ssl_warning_context(verify_ssl):
            wptext = requests.get(
                url,
                headers=REQUEST_HEADER,
                timeout=timeout,
                verify=verify_ssl,
                auth=auth,
                proxies=_proxies(proxy),
            )
        wptext.raise_for_status()

        wpjson = wptext.json()
        if "routes" not in wpjson:
            logging.warning(f"Unexpected response format from {url}")
            return {}

        allroutes = list(wpjson["routes"].keys())
        logging.info("Endpoint %s is OK" % (url))
        logging.info("Total routes %d" % (len(allroutes)))
        _rate_limit_sleep(rate_limit_delay)
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
    auth: Optional[Tuple[str, str]] = None,
    proxy: Optional[str] = None,
    rate_limit_delay: float = 0.0,
) -> Dict:
    """
    Analyze WordPress API routes and compare against known routes.

    Args:
        domain: Domain name (e.g., 'example.com')
        force_https: Force HTTPS instead of HTTP (default: True)
        verify_ssl: Whether to verify SSL certificates (default: True)
        timeout: Request timeout in seconds
        auth: Optional HTTP Basic Auth tuple ``(user, password)``.
        proxy: Optional HTTP proxy URL.
        rate_limit_delay: Seconds to sleep after a successful response.

    Returns:
        Dictionary with analysis results

    Raises:
        APIError: If API request fails
        SSLVerificationError: If SSL verification fails
    """
    prefix = "https" if force_https else "http"
    url = prefix + "://" + domain + "/wp-json/"

    # Load known routes (cached at module level).
    try:
        known_routes = _load_known_routes()
    except IOError as e:
        logging.error(f"Error reading known routes file: {e}")
        raise

    # Fetch routes from WordPress API
    try:
        with get_ssl_warning_context(verify_ssl):
            wptext = requests.get(
                url,
                headers=REQUEST_HEADER,
                timeout=timeout,
                verify=verify_ssl,
                auth=auth,
                proxies=_proxies(proxy),
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

        # Convert known routes to sets for O(1) lookups
        protected_set: Set = set(known_routes.get("protected", []))
        public_list_set: Set = set(known_routes.get("public-list", []))
        public_dict_set: Set = set(known_routes.get("public-dict", []))
        useless_set: Set = set(known_routes.get("useless", []))

        # Categorize routes
        known_routes_dict: Dict[str, str] = {}
        unknown_routes_list: List = []
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
                if route in protected_set:
                    known_routes_dict[route] = "protected"
                    statistics["protected"] += 1
                elif route in public_list_set:
                    known_routes_dict[route] = "public-list"
                    statistics["public-list"] += 1
                elif route in public_dict_set:
                    known_routes_dict[route] = "public-dict"
                    statistics["public-dict"] += 1
                elif route in useless_set:
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
            "wpjson": wpjson,
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
    auth: Optional[Tuple[str, str]] = None,
    proxy: Optional[str] = None,
    rate_limit_delay: float = 0.0,
) -> Optional[str]:
    """
    Test a route and determine its category.

    Args:
        route: Route path (e.g., '/wp/v2/posts')
        route_data: Route data from wpjson['routes'][route]
        base_url: Base URL for the WordPress site
        verify_ssl: Whether to verify SSL certificates
        timeout: Request timeout in seconds
        auth: Optional HTTP Basic Auth tuple ``(user, password)``.
        proxy: Optional HTTP proxy URL.
        rate_limit_delay: Seconds to sleep between probes.

    Returns:
        Category string: 'protected', 'public-list', 'public-dict',
        'useless', or None
    """
    if "?P<" in route:
        return "useless"

    endpoints = route_data.get("endpoints", [])
    if len(endpoints) == 0:
        return None

    endpoint = endpoints[0]
    args = endpoint.get("args", {})

    # Check if it's a paginated list endpoint
    if isinstance(args, dict) and "page" in args and "per_page" in args:
        route_url = get_self_url(route_data)
        if route_url:
            try:
                with get_ssl_warning_context(verify_ssl):
                    resp = requests.get(
                        f"{route_url}?per_page=1&page=1",
                        headers=REQUEST_HEADER,
                        timeout=timeout,
                        verify=verify_ssl,
                        auth=auth,
                        proxies=_proxies(proxy),
                    )
                if resp.status_code == 401 or resp.status_code == 403:
                    return "protected"
                elif resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, list):
                            _rate_limit_sleep(rate_limit_delay)
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
        with get_ssl_warning_context(verify_ssl):
            resp = requests.get(
                route_url,
                headers=REQUEST_HEADER,
                timeout=timeout,
                verify=verify_ssl,
                auth=auth,
                proxies=_proxies(proxy),
            )

        if resp.status_code == 401 or resp.status_code == 403:
            return "protected"

        if any(char.isdigit() for char in route.split("/")[-1]) and len(route.split("/")) > 3:
            if resp.status_code == 200:
                try:
                    data = resp.json()
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
    auth: Optional[Tuple[str, str]] = None,
    proxy: Optional[str] = None,
    rate_limit_delay: float = 0.0,
) -> Dict[str, list]:
    """
    Test unknown routes and categorize them.

    Args:
        unknown_routes: List of unknown route paths
        wpjson: WordPress API JSON response containing routes
        base_url: Base URL for the WordPress site
        verify_ssl: Whether to verify SSL certificates
        timeout: Request timeout in seconds
        auth: Optional HTTP Basic Auth tuple ``(user, password)``.
        proxy: Optional HTTP proxy URL.
        rate_limit_delay: Seconds to sleep between probes.

    Returns:
        Dictionary mapping category -> list of routes
    """
    categorized: Dict[str, list] = {
        "protected": [],
        "public-list": [],
        "public-dict": [],
        "useless": [],
    }

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
            category = _test_route(
                route,
                route_data,
                base_url,
                verify_ssl,
                timeout,
                auth=auth,
                proxy=proxy,
                rate_limit_delay=rate_limit_delay,
            )

            if category and category in categorized:
                categorized[category].append(route)
            else:
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
