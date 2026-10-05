# -*- coding: utf-8 -*-
"""
Media file download module.

Provides functions to read media URLs from JSONL files and download
them concurrently with checkpoint/resume support.

.. note::
    ``TQDM_AVAILABLE``, ``tqdm`` and the SSL-warning helper now live in
    :mod:`wparc.wpapi._common`. Importing them from there ensures a single
    source of truth across all wpapi modules.
"""
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Generator, Optional, Set, Tuple
from urllib.parse import urlparse

from ..exceptions import CheckpointError, FileDownloadError, MediaFileNotFoundError
from ..utils import format_duration
from ._common import TQDM_AVAILABLE, tqdm
from .download import get_file

DEFAULT_WORKERS = 5
CHECKPOINT_FILE = ".wparc_checkpoint.json"

# Backwards-compatible re-export so existing imports of this from ``wparc.wpapi.media``
# (e.g. tests using ``patch("wparc.wpapi.media.TQDM_AVAILABLE", False)``) keep working
# after the move to :mod:`wparc.wpapi._common`.
TQDM_AVAILABLE = TQDM_AVAILABLE  # noqa: F841 - re-exported for back-compat


def read_media_urls(media_file: str) -> Generator[str, None, None]:
    """
    Generator that yields URLs from wp_v2_media.jsonl file.

    Args:
        media_file: Path to the media file

    Yields:
        URL strings from the media file
    """
    try:
        with open(media_file, "r", encoding="utf8") as f:
            for line_num, row in enumerate(f, 1):
                row = row.strip()
                if not row:
                    continue
                try:
                    obj = json.loads(row)
                    if "source_url" in obj:
                        yield obj["source_url"]
                except json.JSONDecodeError as e:
                    logging.warning(f"Line {line_num}: Invalid JSON in media file: {e}")
                    continue
    except IOError as e:
        logging.error(f"Error reading {media_file}: {e}")
        raise


def load_checkpoint(domain: str) -> Set[str]:
    """
    Load checkpoint of already downloaded files.

    If the checkpoint file is corrupt (invalid JSON), it is moved aside to
    ``.wparc_checkpoint.json.corrupt`` and a fresh in-memory checkpoint
    is returned. A :class:`CheckpointError` is logged so the user can
    investigate.

    Args:
        domain: Domain name used as output directory

    Returns:
        Set of file paths that have been downloaded
    """
    checkpoint_path = os.path.join(domain, CHECKPOINT_FILE)
    if not os.path.exists(checkpoint_path):
        return set()

    try:
        with open(checkpoint_path, "r", encoding="utf8") as f:
            data = json.load(f)
            return set(data.get("downloaded_files", []))
    except json.JSONDecodeError as e:
        # Corrupt JSON: rename to .corrupt and start fresh. This is a hard
        # error from the user's perspective (their checkpoint is unusable),
        # so we surface it via CheckpointError for logging purposes.
        corrupt_path = checkpoint_path + ".corrupt"
        logging.error(f"Checkpoint file is corrupt ({e}); moving to {corrupt_path}")
        try:
            os.rename(checkpoint_path, corrupt_path)
        except OSError as rename_err:
            logging.warning(f"Could not rename corrupt checkpoint: {rename_err}")
        return set()
    except IOError as e:
        raise CheckpointError(f"Failed to read checkpoint file {checkpoint_path}: {e}") from e


def save_checkpoint(domain: str, downloaded_files: Set[str]) -> None:
    """
    Save checkpoint of downloaded files.

    Args:
        domain: Domain name used as output directory
        downloaded_files: Set of file paths that have been downloaded

    Raises:
        CheckpointError: If writing the checkpoint fails for any reason.
            Previously this was silently swallowed; callers now surface
            the failure so a failed save cannot be mistaken for success.
    """
    checkpoint_path = os.path.join(domain, CHECKPOINT_FILE)
    data = {
        "downloaded_files": sorted(downloaded_files),
        "last_updated": time.time(),
    }
    try:
        with open(checkpoint_path, "w", encoding="utf8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        raise CheckpointError(f"Failed to write checkpoint file {checkpoint_path}: {e}") from e


def _download_file_task(
    url: str,
    domain: str,
    verify_ssl: bool,
    checkpoint: Set[str],
) -> Tuple[str, bool, Optional[str]]:
    """
    Task function for downloading a single file.

    Wraps unexpected errors in :class:`FileDownloadError` so the resulting
    tuple carries a consistent, actionable error message.

    Args:
        url: URL to download
        domain: Domain name used as output directory
        verify_ssl: Whether to verify SSL certificates
        checkpoint: Set of already downloaded files

    Returns:
        Tuple of (url, success, error_message)
    """
    parsed = urlparse(url)
    filepath = os.path.join(domain, "files", parsed.path.lstrip("/"))

    # Check if already downloaded
    if filepath in checkpoint or os.path.exists(filepath):
        return (url, True, None)

    try:
        result = get_file(url, filepath, verify_ssl=verify_ssl)
        if result[1]:  # Success
            checkpoint.add(filepath)
        return result
    except FileDownloadError as e:
        # Already wrapped; preserve the actionable message.
        return (url, False, str(e))
    except Exception as e:
        # Wrap unexpected exceptions in FileDownloadError so the user
        # gets the same "Suggestion: ..." footer regardless of error class.
        try:
            raise FileDownloadError(url, str(e)) from e
        except FileDownloadError as wrapped:
            return (url, False, str(wrapped))


def collect_files(
    domain: str,
    verify_ssl: bool = True,
    workers: int = DEFAULT_WORKERS,
    resume: bool = True,
) -> Dict[str, int]:
    """
    Collect and download all media files listed in wp_v2_media.jsonl.

    Uses concurrent downloads for better performance and supports resume
    capability.

    Args:
        domain: Domain name used as output directory
        verify_ssl: Whether to verify SSL certificates (default: True)
        workers: Number of concurrent download workers (default: 5)
        resume: Whether to resume from checkpoint (default: True)

    Returns:
        Dict with statistics:
            {'downloaded': int, 'failed': int, 'skipped': int, 'total': int}
    """
    media_file = os.path.join(domain, "data", "wp_v2_media.jsonl")
    if not os.path.exists(media_file):
        raise MediaFileNotFoundError(media_file)

    # Load checkpoint if resuming
    checkpoint = load_checkpoint(domain) if resume else set()

    # Collect all URLs first
    urls = list(read_media_urls(media_file))
    total = len(urls)

    if total == 0:
        logging.warning("No media URLs found in file.")
        return {"downloaded": 0, "failed": 0, "skipped": 0, "total": 0}

    # Filter out already downloaded files
    if resume and checkpoint:
        urls_to_download = []
        skipped = 0
        for url in urls:
            parsed = urlparse(url)
            filepath = os.path.join(domain, "files", parsed.path.lstrip("/"))
            if filepath in checkpoint or os.path.exists(filepath):
                skipped += 1
            else:
                urls_to_download.append(url)
        urls = urls_to_download
        logging.info(f"Resuming: {skipped} files already downloaded, " f"{len(urls)} remaining")
    else:
        skipped = 0

    if not urls:
        logging.info("All files already downloaded.")
        return {"downloaded": 0, "failed": 0, "skipped": skipped, "total": total}

    downloaded = 0
    failed = 0
    start_time = time.time()

    # Create progress bar
    if TQDM_AVAILABLE:
        pbar = tqdm(total=len(urls), desc="Downloading files", unit="file")
    else:
        pbar = None
        logging.info(f"Starting download of {len(urls)} files with {workers} workers...")

    # Use ThreadPoolExecutor for concurrent downloads
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {
            executor.submit(_download_file_task, url, domain, verify_ssl, checkpoint): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            url, success, error_msg = future.result()
            if success:
                downloaded += 1
            else:
                failed += 1
                logging.debug(f"Failed to download {url}: {error_msg}")

            if pbar:
                pbar.update(1)

    if pbar:
        pbar.close()

    # Save checkpoint
    if resume:
        try:
            save_checkpoint(domain, checkpoint)
        except CheckpointError as e:
            # Don't fail the entire download just because we couldn't
            # persist progress; surface the error so the user knows
            # resume on next run may re-download some files.
            logging.error(f"Could not persist download checkpoint: {e}")

    # Print statistics
    elapsed = time.time() - start_time
    logging.info("=" * 60)
    logging.info("Download Statistics:")
    logging.info(f"  Total files: {total}")
    logging.info(f"  Downloaded: {downloaded}")
    logging.info(f"  Skipped (already exists): {skipped}")
    logging.info(f"  Failed: {failed}")
    logging.info(f"  Time elapsed: {format_duration(elapsed)}")
    if downloaded > 0:
        logging.info(f"  Average speed: {downloaded / elapsed:.2f} files/sec")
    logging.info("=" * 60)

    return {
        "downloaded": downloaded,
        "failed": failed,
        "skipped": skipped,
        "total": total,
    }
