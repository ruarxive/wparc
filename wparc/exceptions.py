# -*- coding: utf-8 -*-
"""
Custom exceptions for wparc.

This module defines custom exceptions for better error handling and user feedback.
"""
from typing import Optional


class WparcException(Exception):
    """Base exception for all wparc errors."""

    pass


class DomainValidationError(WparcException):
    """Raised when domain name validation fails."""

    def __init__(self, domain: str, reason: str = "Invalid domain format"):
        self.domain = domain
        self.reason = reason
        message = (
            f"Invalid domain '{domain}': {reason}. "
            f"Please provide a valid domain name (e.g., 'example.com' or 'www.example.com')."
        )
        super().__init__(message)


class APIError(WparcException):
    """Raised when WordPress API request fails."""

    def __init__(
        self, url: str, status_code: Optional[int] = None, message: Optional[str] = None
    ):
        self.url = url
        self.status_code = status_code
        self.message = message or "API request failed"

        error_msg = f"WordPress API error for {url}"
        if status_code:
            error_msg += f" (HTTP {status_code})"
        error_msg += f": {self.message}"

        if status_code == 404:
            error_msg += "\n  Suggestion: Check if the WordPress REST API is enabled on this site."
        elif status_code == 403:
            error_msg += "\n  Suggestion: The API endpoint may be protected. Try checking site permissions."
        elif status_code == 500:
            error_msg += "\n  Suggestion: Server error. The site may be experiencing issues. Try again later."
        elif status_code == 401:
            error_msg += "\n  Suggestion: Authentication required. This endpoint may need credentials."

        super().__init__(error_msg)


class SSLVerificationError(WparcException):
    """Raised when SSL verification fails."""

    def __init__(self, url: str, reason: Optional[str] = None):
        self.url = url
        self.reason = reason
        message = f"SSL verification failed for {url}"
        if reason:
            message += f": {reason}"
        message += "\n  Suggestion: If you trust this site, you can use --no-verify-ssl (not recommended for production)."
        super().__init__(message)


class FileDownloadError(WparcException):
    """Raised when file download fails."""

    def __init__(self, url: str, reason: Optional[str] = None):
        self.url = url
        self.reason = reason
        message = f"Failed to download {url}"
        if reason:
            message += f": {reason}"
        message += "\n  Suggestion: Check your internet connection and verify the URL is accessible."
        super().__init__(message)


class MediaFileNotFoundError(WparcException):
    """Raised when media file list is not found."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        message = f"Media file not found: {filepath}"
        message += "\n  Suggestion: Run 'wparc dump <domain>' first to generate the media file list."
        super().__init__(message)


class CheckpointError(WparcException):
    """Raised when checkpoint operations fail."""

    def __init__(self, message: str):
        super().__init__(f"Checkpoint error: {message}")
