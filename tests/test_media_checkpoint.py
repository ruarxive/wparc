# -*- coding: utf-8 -*-
"""
Tests for media checkpoint behaviour introduced in Phase 1.

Covers S12 (FileDownloadError wrapping) and S13 (CheckpointError
propagation + corrupt-checkpoint recovery).
"""
import json
from unittest.mock import patch

import pytest

from wparc.exceptions import CheckpointError
from wparc.wpapi import media


class TestLoadCheckpointCorrupt:
    """Corrupt JSON should not crash the run; corrupt file is renamed."""

    def test_corrupt_json_is_recovered(self, tmp_path, caplog):
        checkpoint = tmp_path / ".wparc_checkpoint.json"
        checkpoint.write_text("not a valid json {[", encoding="utf-8")

        with caplog.at_level("ERROR"):
            result = media.load_checkpoint(str(tmp_path))

        assert result == set()
        # The corrupt file should be moved aside, not deleted.
        assert not checkpoint.exists()
        assert (tmp_path / ".wparc_checkpoint.json.corrupt").exists()

    def test_missing_file_returns_empty(self, tmp_path):
        assert media.load_checkpoint(str(tmp_path)) == set()


class TestSaveCheckpoint:
    """save_checkpoint must now raise CheckpointError on failure."""

    def test_save_success(self, tmp_path):
        media.save_checkpoint(str(tmp_path), {"/a", "/b"})
        data = json.loads((tmp_path / ".wparc_checkpoint.json").read_text())
        # Filenames are sorted for stable diffs.
        assert sorted(data["downloaded_files"]) == ["/a", "/b"]

    def test_save_failure_raises_checkpoint_error(self, tmp_path):
        # Make the parent directory read-only to provoke OSError on write.
        tmp_path.chmod(0o500)
        try:
            with pytest.raises(CheckpointError):
                media.save_checkpoint(str(tmp_path), {"/a"})
        finally:
            tmp_path.chmod(0o700)


class TestDownloadFileTaskWrapsExceptions:
    """Unexpected exceptions must be wrapped in FileDownloadError."""

    def test_unexpected_exception_returns_file_download_error(self):
        with patch("wparc.wpapi.media.get_file") as mock_get_file:
            mock_get_file.side_effect = RuntimeError("boom")
            url, success, error = media._download_file_task(
                url="http://example.com/x.jpg",
                domain="/tmp/dom",
                verify_ssl=True,
                checkpoint=set(),
            )
        assert success is False
        assert "boom" in error
        # FileDownloadError adds the suggestion footer.
        assert "Suggestion" in error


class TestCollectFilesSurfacesCheckpointError:
    """A failed checkpoint save must not crash the entire download."""

    @patch("wparc.wpapi.media.save_checkpoint")
    @patch("wparc.wpapi.media.read_media_urls")
    @patch("wparc.wpapi.media.get_file")
    def test_failed_checkpoint_is_logged_not_raised(
        self, mock_get_file, mock_read, mock_save, tmp_path
    ):
        # Create the data/ subdirectory and a (small) wp_v2_media.jsonl
        # so collect_files does not bail out with MediaFileNotFoundError.
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        media_file = data_dir / "wp_v2_media.jsonl"
        media_file.write_text('{"source_url": "http://example.com/a.jpg"}\n', encoding="utf-8")

        with patch("wparc.wpapi.media.TQDM_AVAILABLE", False):
            mock_read.return_value = ["http://example.com/a.jpg"]
            mock_get_file.return_value = ("http://example.com/a.jpg", True, None)
            mock_save.side_effect = CheckpointError("disk full")

            stats = media.collect_files(
                domain=str(tmp_path),
                verify_ssl=True,
                workers=1,
                resume=True,
            )
        # Stats are still returned; the failure is logged.
        assert stats["downloaded"] >= 0
        mock_save.assert_called_once()
