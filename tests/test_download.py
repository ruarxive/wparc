# -*- coding: utf-8 -*-
"""
Tests for low-level file download (download.py).

Covers the fix for the early-return ``progress_bar.update`` bug and the
partial-file cleanup behaviour.
"""
from unittest.mock import Mock, patch

import requests

from wparc.wpapi import download


class TestGetFileEarlyReturn:
    """Tests for the early-return path when the file already exists."""

    def test_existing_file_calls_progress_bar_update(self, tmp_path):
        """progress_bar.update(1) must be called even when file exists."""
        target = tmp_path / "already.jpg"
        target.write_bytes(b"data")

        progress_bar = Mock()
        result = download.get_file(
            url="http://example.com/already.jpg",
            filename=str(target),
            verify_ssl=True,
            progress_bar=progress_bar,
        )
        assert result[1] is True
        progress_bar.update.assert_called_once_with(1)

    def test_existing_file_no_progress_bar(self, tmp_path):
        """Early-return must not crash when no progress_bar is provided."""
        target = tmp_path / "already.jpg"
        target.write_bytes(b"data")

        result = download.get_file(
            url="http://example.com/already.jpg",
            filename=str(target),
            verify_ssl=True,
            progress_bar=None,
        )
        assert result == ("http://example.com/already.jpg", True, None)


class TestGetFilePartialCleanup:
    """Tests that partial files are removed on error (S20)."""

    @patch("wparc.wpapi.download.requests.get")
    def test_ssl_error_removes_partial_file(self, mock_get, tmp_path):
        target = tmp_path / "will_fail.jpg"

        mock_get.side_effect = requests.exceptions.SSLError("ssl boom")

        progress_bar = Mock()
        result = download.get_file(
            url="https://example.com/file.jpg",
            filename=str(target),
            verify_ssl=True,
            progress_bar=progress_bar,
        )

        assert result[1] is False
        assert "SSL" in result[2]
        assert not target.exists(), "partial file should be cleaned up"
        progress_bar.update.assert_called_once_with(1)

    @patch("wparc.wpapi.download.requests.get")
    def test_request_exception_removes_partial_file(self, mock_get, tmp_path):
        """If the connection dies mid-download, the partial file must be cleaned up."""
        target = tmp_path / "will_fail.jpg"

        # Build a fake response: HEAD succeeds, iter_content yields one chunk,
        # then raises ConnectionError to simulate a broken stream.
        fake_response = Mock()
        fake_response.raise_for_status = Mock()
        fake_response.headers = {"content-length": "100"}

        def fake_iter_content(chunk_size):
            yield b"x"  # first chunk is written to disk
            raise requests.exceptions.ConnectionError("net down")

        fake_response.iter_content = fake_iter_content
        mock_get.return_value = fake_response

        result = download.get_file(
            url="https://example.com/file.jpg",
            filename=str(target),
            verify_ssl=True,
            progress_bar=None,
        )
        assert result[1] is False
        assert "net down" in result[2]
        assert not target.exists(), "partial file should be cleaned up"


class TestRemovePartial:
    """Tests for the private ``_remove_partial`` helper."""

    def test_remove_existing(self, tmp_path):
        target = tmp_path / "x.bin"
        target.write_bytes(b"x")
        download._remove_partial(str(target))
        assert not target.exists()

    def test_remove_missing_is_noop(self, tmp_path):
        # Must not raise on missing files.
        download._remove_partial(str(tmp_path / "nope.bin"))


class TestUserAgentConsistency:
    """The User-Agent header must not contain trailing whitespace or be empty."""

    def test_user_agent_non_empty(self):
        assert download.REQUEST_HEADER.get("User-Agent")
        ua = download.REQUEST_HEADER["User-Agent"]
        assert ua.strip() == ua
        assert len(ua) > 30
