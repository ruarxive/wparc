# -*- coding: utf-8 -*-
"""
Tests for utility functions.
"""
import pytest

from wparc.exceptions import DomainValidationError
from wparc.utils import validate_domain, format_bytes, format_duration


class TestValidateDomain:
    """Tests for domain validation."""

    def test_valid_domain(self):
        """Test valid domain names."""
        assert validate_domain("example.com") == "example.com"
        assert validate_domain("www.example.com") == "www.example.com"
        assert validate_domain("subdomain.example.com") == "subdomain.example.com"
        assert validate_domain("localhost") == "localhost"
        assert validate_domain("127.0.0.1") == "127.0.0.1"

    def test_domain_with_protocol(self):
        """Test domain with protocol prefix."""
        assert validate_domain("http://example.com") == "example.com"
        assert validate_domain("https://www.example.com") == "www.example.com"

    def test_domain_normalization(self):
        """Test domain normalization."""
        assert validate_domain("EXAMPLE.COM") == "example.com"
        assert validate_domain("  example.com  ") == "example.com"
        assert validate_domain("example.com/") == "example.com"

    def test_invalid_domain(self):
        """Test invalid domain names."""
        with pytest.raises(DomainValidationError):
            validate_domain("")

        with pytest.raises(DomainValidationError):
            validate_domain("invalid..domain.com")

        with pytest.raises(DomainValidationError):
            validate_domain("a" * 254)  # Too long


class TestFormatBytes:
    """Tests for byte formatting."""

    def test_format_bytes(self):
        """Test byte formatting."""
        assert format_bytes(0) == "0.00 B"
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1024 * 1024) == "1.00 MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"
        assert format_bytes(500) == "500.00 B"
        assert format_bytes(1536) == "1.50 KB"


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(0) == "0s"
        assert format_duration(30) == "30s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3661) == "1h 1m 1s"
        assert format_duration(90000) == "1d 1h 0m"


class TestValidateDomainEdgeCases:
    """Additional edge cases for IP and port handling introduced in Phase 3."""

    def test_valid_ipv4(self):
        assert validate_domain("127.0.0.1") == "127.0.0.1"
        assert validate_domain("192.168.0.1") == "192.168.0.1"

    def test_valid_ipv6(self):
        assert validate_domain("::1") == "::1"
        assert validate_domain("2001:db8::1") == "2001:db8::1"

    def test_bracketed_ipv6(self):
        # URI-style IPv6 literal: [::1]
        assert validate_domain("[::1]") == "::1"

    def test_rejects_garbage_ipv6(self):
        # The old regex accepted ":::::" as valid IPv6; ipaddress() rejects it.
        with pytest.raises(DomainValidationError):
            validate_domain(":::::")

    def test_rejects_garbage_ipv4(self):
        with pytest.raises(DomainValidationError):
            validate_domain("999.999.999.999")

    def test_rejects_hostname_with_port(self):
        # ``example.com:8080`` is a hostname + port, not a valid domain.
        with pytest.raises(DomainValidationError):
            validate_domain("example.com:8080")
