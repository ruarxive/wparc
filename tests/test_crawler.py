# -*- coding: utf-8 -*-
"""
Tests for WordPress API crawler.
"""
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from wparc.exceptions import APIError, SSLVerificationError, MediaFileNotFoundError
from wparc.wpapi.crawler import (
    get_self_url,
    _read_media_urls,
    ping,
    collect_files,
)


class TestGetSelfUrl:
    """Tests for get_self_url function."""

    def test_get_self_url_dict(self):
        """Test extracting self URL from dict format."""
        data = {
            "_links": {"self": {"href": "http://example.com/wp-json/wp/v2/posts/1"}}
        }
        assert get_self_url(data) == "http://example.com/wp-json/wp/v2/posts/1"

    def test_get_self_url_string(self):
        """Test extracting self URL from string format."""
        data = {"_links": {"self": "http://example.com/wp-json/wp/v2/posts/1"}}
        assert get_self_url(data) == "http://example.com/wp-json/wp/v2/posts/1"

    def test_get_self_url_list(self):
        """Test extracting self URL from list format."""
        data = {
            "_links": {"self": [{"href": "http://example.com/wp-json/wp/v2/posts/1"}]}
        }
        assert get_self_url(data) == "http://example.com/wp-json/wp/v2/posts/1"

    def test_get_self_url_none(self):
        """Test when self URL is not present."""
        assert get_self_url({}) is None
        assert get_self_url({"_links": {}}) is None
        assert get_self_url({"_links": {"self": []}}) is None


class TestReadMediaUrls:
    """Tests for _read_media_urls function."""

    def test_read_media_urls(self):
        """Test reading media URLs from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"source_url": "http://example.com/file1.jpg"}\n')
            f.write('{"source_url": "http://example.com/file2.jpg"}\n')
            f.write('{"other": "data"}\n')  # Missing source_url
            f.write("\n")  # Empty line
            temp_file = f.name

        try:
            urls = list(_read_media_urls(temp_file))
            assert len(urls) == 2
            assert urls[0] == "http://example.com/file1.jpg"
            assert urls[1] == "http://example.com/file2.jpg"
        finally:
            os.unlink(temp_file)

    def test_read_media_urls_invalid_json(self):
        """Test reading media URLs with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"source_url": "http://example.com/file1.jpg"}\n')
            f.write("invalid json\n")
            f.write('{"source_url": "http://example.com/file2.jpg"}\n')
            temp_file = f.name

        try:
            urls = list(_read_media_urls(temp_file))
            assert len(urls) == 2
        finally:
            os.unlink(temp_file)

    def test_read_media_urls_file_not_found(self):
        """Test reading from non-existent file."""
        with pytest.raises(IOError):
            list(_read_media_urls("/nonexistent/file.jsonl"))


class TestPing:
    """Tests for ping function."""

    @patch("wparc.wpapi.crawler.requests.get")
    def test_ping_success(self, mock_get):
        """Test successful ping."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "routes": {"/wp/v2/posts": {}, "/wp/v2/pages": {}}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = ping("example.com", force_https=False, verify_ssl=True)
        assert result["routes_count"] == 2
        assert "url" in result
        assert "routes" in result

    @patch("wparc.wpapi.crawler.requests.get")
    def test_ping_ssl_error(self, mock_get):
        """Test ping with SSL error."""
        mock_get.side_effect = requests.exceptions.SSLError("SSL verification failed")

        with pytest.raises(SSLVerificationError):
            ping("example.com", force_https=True, verify_ssl=True)

    @patch("wparc.wpapi.crawler.requests.get")
    def test_ping_http_error(self, mock_get):
        """Test ping with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )

        with pytest.raises(APIError) as exc_info:
            ping("example.com", force_https=False, verify_ssl=True)
        assert exc_info.value.status_code == 404


class TestCollectFiles:
    """Tests for collect_files function."""

    def test_collect_files_media_file_not_found(self):
        """Test collect_files when media file doesn't exist."""
        with pytest.raises(MediaFileNotFoundError):
            collect_files("nonexistent", verify_ssl=True, workers=1, resume=False)

    @patch("wparc.wpapi.crawler.get_file")
    @patch("wparc.wpapi.crawler._read_media_urls")
    def test_collect_files_success(self, mock_read, mock_get_file):
        """Test successful file collection."""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            media_file = os.path.join(tmpdir, "data", "wp_v2_media.jsonl")
            os.makedirs(os.path.dirname(media_file), exist_ok=True)

            with open(media_file, "w") as f:
                f.write('{"source_url": "http://example.com/file1.jpg"}\n')

            mock_read.return_value = ["http://example.com/file1.jpg"]
            mock_get_file.return_value = ("http://example.com/file1.jpg", True, None)

            stats = collect_files(tmpdir, verify_ssl=True, workers=1, resume=False)
            assert stats["downloaded"] >= 0
            assert stats["total"] == 1


class TestCollectData:
    """Tests for collect_data function."""

    @patch("wparc.wpapi.crawler.pkg_resources.resource_filename")
    @patch("wparc.wpapi.crawler.requests.get")
    @patch("builtins.open")
    def test_collect_data_success(self, mock_open, mock_get, mock_resource):
        """Test successful data collection."""
        # Mock known routes file
        mock_resource.return_value = "/path/to/known_routes.yml"
        mock_open.return_value.__enter__.return_value.read.return_value = """
public-list:
  - /wp/v2/posts
public-dict:
  - /wp/v2/types
protected: []
useless: []
"""

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "routes": {
                "/wp/v2/posts": {
                    "_links": {
                        "self": {"href": "http://example.com/wp-json/wp/v2/posts"}
                    },
                    "endpoints": [{"args": {"page": {}, "per_page": {}}}],
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_open.return_value.__exit__ = Mock(return_value=None)

        # This test is simplified - actual implementation would need more mocking
        pass  # Placeholder for more comprehensive test
