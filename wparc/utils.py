# -*- coding: utf-8 -*-
"""
Utility functions for wparc.

This module provides utility functions for validation, formatting, and other common operations.
"""
import re
from urllib.parse import urlparse

from .exceptions import DomainValidationError


def validate_domain(domain: str) -> str:
    """
    Validate and normalize a domain name.

    Args:
        domain: Domain name to validate

    Returns:
        Normalized domain name

    Raises:
        DomainValidationError: If domain is invalid
    """
    if not domain:
        raise DomainValidationError(domain, "Domain cannot be empty")

    domain = domain.strip().lower()

    # Remove protocol if present
    if domain.startswith(("http://", "https://")):
        parsed = urlparse(domain)
        domain = parsed.netloc or parsed.path

    # Remove trailing slash
    domain = domain.rstrip("/")

    # Basic domain validation regex
    # Allows: example.com, www.example.com, subdomain.example.com, localhost, 127.0.0.1
    domain_pattern = re.compile(
        r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$|"  # Standard domain
        r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$|"  # Single label (localhost, etc.)
        r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$|"  # IPv4
        r"^\[?[0-9a-f:]+]?$"  # IPv6 (basic check)
    )

    if not domain_pattern.match(domain):
        raise DomainValidationError(
            domain,
            "Invalid domain format. Expected format: example.com or www.example.com",
        )

    # Additional checks
    if len(domain) > 253:  # Max domain length per RFC
        raise DomainValidationError(domain, "Domain name too long (max 253 characters)")

    if ".." in domain:
        raise DomainValidationError(domain, "Domain cannot contain consecutive dots")

    return domain


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes count as human-readable string.

    Args:
        bytes_count: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    count = float(bytes_count)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if count < 1024.0:
            return f"{count:.2f} {unit}"
        count /= 1024.0
    return f"{count:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds as human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1h 23m 45s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours = int(minutes // 60)
    mins = int(minutes % 60)

    if hours < 24:
        return f"{hours}h {mins}m {secs}s"

    days = int(hours // 24)
    hrs = int(hours % 24)
    return f"{days}d {hrs}h {mins}m"
