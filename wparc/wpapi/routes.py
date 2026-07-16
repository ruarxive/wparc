# -*- coding: utf-8 -*-
"""
WordPress API route analysis module.

Provides functions to discover, categorize, and test WordPress API routes.
"""
import contextlib
import logging
from typing import Dict, List, Optional, Set

import requests
import urllib3

from ..exceptions import APIError, SSLVerificationError
from .resources import get_resource_filename

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


import yaml

DEFAULT_TIMEOUT = 360


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
        with _get_ssl_warning_context(verify_ssl):
            wptext = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build MRA58N) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/67.0.3396.99 Mobile Safari/537.36"
                    )
                },
                timeout=timeout,
                verify=verify_ssl,
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
        Dictionary with analysis results

    Raises:
        APIError: If API request fails
        SSLVerificationError: If SSL verification fails
    """
    prefix = "https" if force_https else "http"
    url = prefix + "://" + domain + "/wp-json/"
    known_routes_filename = get_resource_filename(
        "wparc", "data/known_routes.yml"
    )

    # Load known routes
    try:
        with open(known_routes_filename, "r", encoding="utf8") as f:
            known_routes = yaml.safe_load(f)
    except IOError as e:
        logging.error(f"Error reading known routes file: {e}")
        raise

    # Fetch routes from WordPress API
    try:
        with _get_ssl_warning_context(verify_ssl):
            wptext = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build MRA58N) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/67.0.3396.99 Mobile Safari/537.36"
                    )
                },
                timeout=timeout,
                verify=verify_ssl,
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
            pbar = tqdm(
                total=total_routes, desc="Analyzing routes", unit="route"
            )
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
                with _get_ssl_warning_context(verify_ssl):
                    resp = requests.get(
                        f"{route_url}?per_page=1&page=1",
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
        with _get_ssl_warning_context(verify_ssl):
            resp = requests.get(
                route_url,
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

        if resp.status_code == 401 or resp.status_code == 403:
            return "protected"

        if (
            any(char.isdigit() for char in route.split("/")[-1])
            and len(route.split("/")) > 3
        ):
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
    categorized: Dict[str, list] = {
        "protected": [],
        "public-list": [],
        "public-dict": [],
        "useless": [],
    }

    if TQDM_AVAILABLE:
        pbar = tqdm(
            total=len(unknown_routes), desc="Testing routes", unit="route"
        )
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
                route, route_data, base_url, verify_ssl, timeout
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
