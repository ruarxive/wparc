# -*- coding: utf-8 -*-
"""
Tests for custom exceptions.
"""
import pytest

from wparc.exceptions import (
    WparcException,
    DomainValidationError,
    APIError,
    SSLVerificationError,
    FileDownloadError,
    MediaFileNotFoundError,
    CheckpointError,
)


class TestExceptions:
    """Tests for custom exceptions."""

    def test_wparc_exception(self):
        """Test base exception."""
        with pytest.raises(WparcException):
            raise WparcException("Test error")

    def test_domain_validation_error(self):
        """Test domain validation error."""
        error = DomainValidationError("invalid", "Invalid format")
        assert "invalid" in str(error)
        assert "Invalid format" in str(error)
        assert error.domain == "invalid"
        assert error.reason == "Invalid format"

    def test_api_error(self):
        """Test API error."""
        error = APIError("http://example.com", status_code=404)
        assert "404" in str(error)
        assert "Suggestion" in str(error)

        error = APIError("http://example.com", status_code=500)
        assert "500" in str(error)
        assert "Suggestion" in str(error)

    def test_ssl_verification_error(self):
        """Test SSL verification error."""
        error = SSLVerificationError("https://example.com")
        assert "SSL verification failed" in str(error)
        assert "Suggestion" in str(error)

    def test_file_download_error(self):
        """Test file download error."""
        error = FileDownloadError("http://example.com/file.jpg", "Connection timeout")
        assert "Failed to download" in str(error)
        assert "Suggestion" in str(error)

    def test_media_file_not_found_error(self):
        """Test media file not found error."""
        error = MediaFileNotFoundError("/path/to/file.jsonl")
        assert "Media file not found" in str(error)
        assert "Suggestion" in str(error)

    def test_checkpoint_error(self):
        """Test checkpoint error."""
        error = CheckpointError("Failed to save")
        assert "Checkpoint error" in str(error)
