# -*- coding: utf-8 -*-
"""
WordPress API crawler module.

This module provides functions to crawl and extract data from WordPress
REST API endpoints. It supports downloading media files, dumping API
routes, and pinging WordPress sites.

.. note::
    This module re-exports functionality from specialized sub-modules:
    - :mod:`wparc.wpapi.download` — file download utilities
    - :mod:`wparc.wpapi.media` — media file collection
    - :mod:`wparc.wpapi.routes` — route analysis and testing
    - :mod:`wparc.wpapi.dump` — data dump and collection
    - :mod:`wparc.wpapi.resources` — package resource management
"""
from .download import get_file
from .dump import collect_data, dump_route_dict, dump_route_list
from .media import collect_files, read_media_urls
from .resources import get_resource_filename
from .routes import (
    analyze_routes,
    generate_routes_yaml,
    get_self_url,
    ping,
    test_unknown_routes,
)

__all__ = [
    "analyze_routes",
    "collect_data",
    "collect_files",
    "dump_route_dict",
    "dump_route_list",
    "generate_routes_yaml",
    "get_file",
    "get_resource_filename",
    "get_self_url",
    "ping",
    "read_media_urls",
    "test_unknown_routes",
]
