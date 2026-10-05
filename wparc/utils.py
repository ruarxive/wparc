# -*- coding: utf-8 -*-
"""
Utility functions for wparc.

This module provides utility functions for validation, formatting, and other common operations.
"""
import ipaddress
import re
from urllib.parse import urlparse

from .exceptions import DomainValidationError

# Regex used for non-IP domains. The IP branches are validated separately
# via :mod:`ipaddress`, which is far stricter than any regex.
_DOMAIN_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9]"
    r"[a-z0-9-]{0,61}[a-z0-9]$|"  # Standard FQDN
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"  # Single-label (e.g. localhost)
)


def _looks_like_ip(value: str) -> bool:
    """Quick heuristic before delegating to ``ipaddress`` (which is slow)."""
    if not value:
        return False
    # IPv4 contains only digits/dots; IPv6 contains a colon and only hex digits.
    if ":" in value:
        return True
    return all(ch.isdigit() or ch == "." for ch in value)


def validate_domain(domain: str) -> str:
    """
    Validate and normalize a domain name.

    Accepts:

    - Standard FQDN: ``example.com``, ``www.example.com``, ``sub.example.com``
    - Single-label: ``localhost``
    - IPv4: ``127.0.0.1``
    - IPv6: ``[::1]``, ``::1``, ``2001:db8::1``

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

    # Strip an IPv6 zone-id or port from the candidate. urlparse() puts
    # the port into ``.port`` and leaves the host clean.
    if ":" in domain and not _looks_like_ip(domain):
        # ``example.com:8080`` would otherwise sneak past the regex below.
        try:
            parsed = urlparse("//" + domain)
            if parsed.port is not None:
                domain = parsed.hostname or domain
        except ValueError:
            pass

    # Remove trailing slash
    domain = domain.rstrip("/")

    # Strip IPv6 brackets if the caller used the URI form.
    if domain.startswith("[") and domain.endswith("]"):
        domain = domain[1:-1]

    # Additional length check (RFC 1035 max).
    if len(domain) > 253:
        raise DomainValidationError(domain, "Domain name too long (max 253 characters)")
    if ".." in domain:
        raise DomainValidationError(domain, "Domain cannot contain consecutive dots")

    # IPs get strict validation from the stdlib (rejects things our
    # regex used to accept, like ``:::::`` or ``999.999.999.999``).
    if _looks_like_ip(domain):
        try:
            ipaddress.ip_address(domain)
        except ValueError as exc:
            raise DomainValidationError(domain, f"Invalid IP address: {exc}") from exc
        return domain

    if not _DOMAIN_PATTERN.match(domain):
        raise DomainValidationError(
            domain,
            "Invalid domain format. Expected format: example.com or www.example.com",
        )

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
