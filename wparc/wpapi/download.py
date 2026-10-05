# -*- coding: utf-8 -*-
"""
File download module.

Provides functions to download files from URLs using requests or aria2.

.. note::
    ``DEFAULT_TIMEOUT``, ``DEFAULT_CHUNK_SIZE``, ``REQUEST_HEADER`` and
    the SSL-warning context manager now live in
    :mod:`wparc.wpapi._common`. Importing them from there ensures all
    wpapi modules share a single source of truth.
"""
import os
import subprocess
from typing import Optional, Tuple

import requests

from ._common import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    REQUEST_HEADER,
    get_ssl_warning_context,
    urllib3_warnings_suppressed,
)


def _remove_partial(filepath: str) -> None:
    """Remove a partially downloaded file if it exists.

    Used to clean up after a failed download so the next attempt can
    re-download the file from scratch instead of seeing the stale
    artefact and skipping it as already-downloaded.
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        # Best-effort cleanup; never raise from cleanup.
        pass


def get_file(
    url: str,
    filename: str,
    aria2: bool = False,
    aria2path: Optional[str] = None,
    verify_ssl: bool = True,
    progress_bar=None,
) -> Tuple[str, bool, Optional[str]]:
    """
    Download a file from URL to local filesystem.

    Args:
        url: URL to download from
        filename: Local filename to save to
        aria2: Whether to use aria2 for downloading
        aria2path: Path to aria2 executable
        verify_ssl: Whether to verify SSL certificates (default: True)
        progress_bar: Optional tqdm progress bar for individual file

    Returns:
        Tuple of (url, success, error_message)
    """
    if os.path.exists(filename):
        if progress_bar is not None:
            progress_bar.update(1)
        return (url, True, None)

    dirpath = os.path.dirname(filename)
    os.makedirs(dirpath, exist_ok=True)
    basename = os.path.basename(filename)

    if not aria2:
        try:
            with get_ssl_warning_context(verify_ssl):
                page = requests.get(
                    url,
                    headers=REQUEST_HEADER,
                    stream=True,
                    verify=verify_ssl,
                    timeout=DEFAULT_TIMEOUT,
                )
            page.raise_for_status()

            total_size = int(page.headers.get("content-length", 0))
            downloaded = 0

            with open(filename, "wb") as f:
                for chunk in page.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_bar and total_size > 0:
                            # Update progress for individual file if provided
                            pass  # Main progress bar handles this

            if progress_bar is not None:
                progress_bar.update(1)
            return (url, True, None)
        except requests.exceptions.SSLError as e:
            error_msg = f"SSL verification failed: {e}"
            _remove_partial(filename)
            if progress_bar is not None:
                progress_bar.update(1)
            return (url, False, error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            _remove_partial(filename)
            if progress_bar is not None:
                progress_bar.update(1)
            return (url, False, error_msg)
    else:
        if aria2path is None:
            raise ValueError("aria2path is required when aria2=True")

        # Use subprocess instead of os.system to prevent command injection
        cmd = [aria2path, "--retry-wait=10"]
        if len(dirpath) > 0:
            cmd.extend(["-d", dirpath, "--out", basename])
        else:
            cmd.extend(["--out", basename])
        cmd.append(url)

        try:
            subprocess.run(cmd, check=True, timeout=DEFAULT_TIMEOUT)
            if progress_bar is not None:
                progress_bar.update(1)
            return (url, True, None)
        except subprocess.CalledProcessError as e:
            error_msg = f"aria2 failed: {e}"
            _remove_partial(filename)
            if progress_bar is not None:
                progress_bar.update(1)
            return (url, False, error_msg)
        except subprocess.TimeoutExpired:
            error_msg = "aria2 timeout"
            _remove_partial(filename)
            if progress_bar is not None:
                progress_bar.update(1)
            return (url, False, error_msg)


__all__ = [
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_TIMEOUT",
    "REQUEST_HEADER",
    "get_file",
    "urllib3_warnings_suppressed",
    "_remove_partial",
]
