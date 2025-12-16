# -*- coding: utf-8 -*-
"""
Command extractor module.

This module provides the Project class that wraps WordPress API crawler functions.
"""
from typing import Dict, Optional

from ..wpapi.crawler import (
    analyze_routes,
    collect_data,
    collect_files,
    ping,
    test_unknown_routes,
    generate_routes_yaml,
)
from ..utils import validate_domain


class Project:
    """WordPress API crawler project wrapper."""

    def __init__(self, verify_ssl: bool = True) -> None:
        """
        Initialize Project.

        Args:
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.verify_ssl = verify_ssl

    def dump(
        self,
        domain: str,
        all_routes: bool,
        https: bool,
        verify_ssl: Optional[bool] = None,
        timeout: int = 360,
        page_size: int = 100,
        retry_count: int = 5,
    ) -> Dict[str, int]:
        """
        Dump WordPress data from API.

        Args:
            domain: Domain name to crawl
            all_routes: Include unknown API routes
            https: Force HTTPS protocol
            verify_ssl: Whether to verify SSL certificates (uses instance default if None)
            timeout: Request timeout in seconds
            page_size: Number of items per page
            retry_count: Number of retry attempts

        Returns:
            Dictionary with statistics
        """
        domain = validate_domain(domain)
        verify = verify_ssl if verify_ssl is not None else self.verify_ssl
        return collect_data(
            domain,
            get_unknown=all_routes,
            force_https=https,
            verify_ssl=verify,
            timeout=timeout,
            page_size=page_size,
            retry_count=retry_count,
        )

    def getfiles(
        self,
        domain: str,
        verify_ssl: Optional[bool] = None,
        workers: int = 5,
        resume: bool = True,
    ) -> Dict[str, int]:
        """
        Download all media files listed in wp_v2_media.jsonl.

        Args:
            domain: Domain name used as output directory
            verify_ssl: Whether to verify SSL certificates (uses instance default if None)
            workers: Number of concurrent download workers
            resume: Whether to resume from checkpoint

        Returns:
            Dictionary with statistics
        """
        domain = validate_domain(domain)
        verify = verify_ssl if verify_ssl is not None else self.verify_ssl
        return collect_files(
            domain,
            verify_ssl=verify,
            workers=workers,
            resume=resume,
        )

    def ping(
        self,
        domain: str,
        https: bool,
        verify_ssl: Optional[bool] = None,
        timeout: int = 360,
    ) -> Dict:
        """
        Ping WordPress API endpoint to verify it's accessible.

        Args:
            domain: Domain name (e.g., 'example.com')
            https: Force HTTPS protocol
            verify_ssl: Whether to verify SSL certificates (uses instance default if None)
            timeout: Request timeout in seconds

        Returns:
            Dictionary with endpoint information
        """
        domain = validate_domain(domain)
        verify = verify_ssl if verify_ssl is not None else self.verify_ssl
        return ping(
            domain,
            force_https=https,
            verify_ssl=verify,
            timeout=timeout,
        )

    def analyze(
        self,
        domain: str,
        https: bool,
        verify_ssl: Optional[bool] = None,
        timeout: int = 360,
    ) -> Dict:
        """
        Analyze WordPress API routes and compare against known routes.

        Args:
            domain: Domain name (e.g., 'example.com')
            https: Force HTTPS protocol
            verify_ssl: Whether to verify SSL certificates (uses instance default if None)
            timeout: Request timeout in seconds

        Returns:
            Dictionary with analysis results, including tested unknown routes and YAML update
        """
        domain = validate_domain(domain)
        verify = verify_ssl if verify_ssl is not None else self.verify_ssl
        
        # Get initial analysis
        result = analyze_routes(
            domain,
            force_https=https,
            verify_ssl=verify,
            timeout=timeout,
        )
        
        # Test unknown routes if any are found
        unknown_routes = result.get("unknown_routes", [])
        wpjson = result.get("wpjson", {})
        
        if unknown_routes and wpjson:
            prefix = "https" if https else "http"
            base_url = f"{prefix}://{domain}/wp-json"
            
            # Test each unknown route
            categorized_routes = test_unknown_routes(
                unknown_routes,
                wpjson,
                base_url,
                verify_ssl=verify,
                timeout=timeout,
            )
            
            # Generate YAML update
            yaml_update = generate_routes_yaml(categorized_routes)
            
            # Add to result
            result["categorized_routes"] = categorized_routes
            result["yaml_update"] = yaml_update
        
        return result
