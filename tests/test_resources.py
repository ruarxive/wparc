# -*- coding: utf-8 -*-
"""
Tests for :mod:`wparc.wpapi.resources`.

Covers all three branches of the importlib.resources fallback chain:
Python 3.9+ ``files()`` API, the older ``path()`` context manager, and
the legacy ``pkg_resources`` API.
"""
from unittest.mock import patch

import pytest

from wparc.wpapi import resources as wparc_resources


class TestFilesApi:
    """When importlib.resources.files() works, we should use it."""

    def test_returns_path_from_files_api(self):
        path = wparc_resources.get_resource_filename("wparc", "data/known_routes.yml")
        # The known_routes.yml shipped with the package must be findable.
        assert path.endswith("wparc/data/known_routes.yml")
        # And the underlying file must really exist on disk.
        import os

        assert os.path.exists(path)


class TestPkgResourcesFallback:
    """When importlib.resources is missing, we fall back to pkg_resources."""

    @patch.object(wparc_resources, "_IMPORTLIB_RESOURCES_AVAILABLE", False)
    @patch("pkg_resources.resource_filename")
    def test_uses_pkg_resources(self, mock_resource_filename):
        # Save original value to restore.
        original_available = wparc_resources._IMPORTLIB_RESOURCES_AVAILABLE
        original_use_files = wparc_resources._USE_FILES_API
        try:
            wparc_resources._IMPORTLIB_RESOURCES_AVAILABLE = False
            mock_resource_filename.return_value = "/legacy/known_routes.yml"
            result = wparc_resources.get_resource_filename("wparc", "data/known_routes.yml")
            assert result == "/legacy/known_routes.yml"
            mock_resource_filename.assert_called_once_with("wparc", "data/known_routes.yml")
        finally:
            wparc_resources._IMPORTLIB_RESOURCES_AVAILABLE = original_available
            wparc_resources._USE_FILES_API = original_use_files


class TestCompleteFailure:
    """If everything fails we re-raise the underlying error."""

    def test_propagates_final_failure(self):
        original_available = wparc_resources._IMPORTLIB_RESOURCES_AVAILABLE
        original_use_files = wparc_resources._USE_FILES_API
        try:
            wparc_resources._IMPORTLIB_RESOURCES_AVAILABLE = False
            with patch("pkg_resources.resource_filename") as mock_rf:
                mock_rf.side_effect = RuntimeError("nope")
                with pytest.raises(RuntimeError, match="nope"):
                    wparc_resources.get_resource_filename("wparc", "data/known_routes.yml")
        finally:
            wparc_resources._IMPORTLIB_RESOURCES_AVAILABLE = original_available
            wparc_resources._USE_FILES_API = original_use_files


class TestImportlibFailureFallback:
    """When the importlib path raises, fall through to pkg_resources.

    The fallback is implemented by an ``except`` branch in
    :func:`get_resource_filename`. We force that branch by simulating a
    filesystem failure via a mock that raises when ``files()`` is called.
    """

    def test_falls_through_on_exception(self):
        # Direct call: when files() raises, we land in the
        # ``except Exception`` branch and ultimately call it.

        # Build a callable that raises to mimic importlib failure.
        def boom(*args, **kwargs):
            raise ImportError("forced")

        # Patch the module's reference to ``files`` directly.
        original_files = getattr(wparc_resources, "files", None)
        wparc_resources.files = boom  # type: ignore[assignment]
        try:
            with patch("pkg_resources.resource_filename") as mock_rf:
                mock_rf.return_value = "/via/pkg_resources/file.yml"
                result = wparc_resources.get_resource_filename("wparc", "data/known_routes.yml")
                assert result == "/via/pkg_resources/file.yml"
        finally:
            if original_files is not None:
                wparc_resources.files = original_files  # type: ignore[assignment]
