# -*- coding: utf-8 -*-
"""
Package resource management utilities.

Provides functions to locate package data files across different Python
versions, using importlib.resources with fallback to pkg_resources.
"""
import logging

try:
    from importlib.resources import files

    _IMPORTLIB_RESOURCES_AVAILABLE = True
    _USE_FILES_API = True
except ImportError:
    # Fallback for Python < 3.9
    try:
        from importlib.resources import path as resource_path

        _IMPORTLIB_RESOURCES_AVAILABLE = True
        _USE_FILES_API = False
    except ImportError:
        # Final fallback to pkg_resources for very old Python versions
        _IMPORTLIB_RESOURCES_AVAILABLE = False
        _USE_FILES_API = False


def get_resource_filename(package: str, resource: str) -> str:
    """
    Get the filesystem path to a package resource.

    Uses importlib.resources when available (Python 3.9+), falls back to
    importlib.resources.path (Python 3.7-3.8), or pkg_resources for older
    versions.

    Args:
        package: Package name (e.g., 'wparc')
        resource: Resource path relative to package
            (e.g., 'data/known_routes.yml')

    Returns:
        Filesystem path to the resource
    """
    if _IMPORTLIB_RESOURCES_AVAILABLE:
        try:
            if _USE_FILES_API:
                # Python 3.9+: use files() API
                return str(files(package) / resource)
            else:
                # Python 3.7-3.8: use path() context manager
                with resource_path(package, resource) as p:
                    path_str = str(p)
                return path_str
        except Exception as e:
            logging.warning(
                f"Failed to get resource using importlib.resources: {e}"
            )
            # Fall through to pkg_resources fallback
    # Fallback to pkg_resources for older Python versions or if importlib fails
    try:
        import pkg_resources

        return pkg_resources.resource_filename(package, resource)
    except Exception as e:
        logging.error(f"Failed to get resource filename: {e}")
        raise
