# -*- coding: utf-8 -*-
"""
Shared low-level helpers for :mod:`wparc.wpapi` sub-modules.

This module centralises constants and helpers that used to be duplicated
across :mod:`wparc.wpapi.dump`, :mod:`wparc.wpapi.media`,
:mod:`wparc.wpapi.routes`, and :mod:`wparc.wpapi.download`.

It is intentionally tiny and side-effect-free at import time so that
importing it does not configure logging or urllib3.

Contents
--------
- :data:`DEFAULT_TIMEOUT` — default HTTP timeout in seconds.
- :data:`DEFAULT_CHUNK_SIZE` — default download chunk size in bytes.
- :data:`USER_AGENT` — single source of truth for the User-Agent header.
- :data:`REQUEST_HEADER` — pre-built headers dict for HTTP requests.
- :data:`TQDM_AVAILABLE` — whether :mod:`tqdm` is importable.
- :class:`_TqdmFallback` — minimal stand-in used when :mod:`tqdm` is missing.
- :func:`tqdm` — always-callable factory returning either tqdm or the fallback.
- :func:`urllib3_warnings_suppressed` — context manager that silences
  ``InsecureRequestWarning`` and reliably restores it on exit.
- :data:`DEFAULT_POOL_SIZE` / :data:`DEFAULT_RETRY_TOTAL` /
  :data:`DEFAULT_RETRY_BACKOFF` — connection-pool defaults.
- :func:`make_session` — factory that builds a connection-pooled session.
- :func:`get_ssl_warning_context` — returns the right context manager
  based on the ``verify_ssl`` flag.
"""
import contextlib
from types import MappingProxyType as _MappingProxyType
from typing import Any, Iterator, Optional

import requests
import urllib3

# ---- HTTP defaults -----------------------------------------------------------

DEFAULT_TIMEOUT: int = 360
"""Default request timeout in seconds."""

DEFAULT_CHUNK_SIZE: int = 1024 * 1024
"""Default chunk size for streamed downloads (1 MiB)."""

DEFAULT_POOL_SIZE: int = 10
"""Default number of connections kept alive in the pool."""

DEFAULT_RETRY_TOTAL: int = 3
"""Default total retry attempts for connection-level failures."""

DEFAULT_RETRY_BACKOFF: float = 0.5
"""Default exponential backoff factor (seconds)."""

USER_AGENT: str = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/67.0.3396.99 Mobile Safari/537.36"
)
"""The single, canonical User-Agent string for all wparc HTTP requests.

Consolidates the six copies that used to live in ``dump.py``, ``routes.py``
and ``download.py``. Some WordPress sites filter requests by UA, so this
must remain a stable identifier.
"""

REQUEST_HEADER: dict = {"User-Agent": USER_AGENT}
"""Pre-built headers dict, suitable for ``requests.get(headers=...)``.

A frozen ``MappingProxyType`` view is used at runtime so accidental
mutation in any wpapi module raises ``TypeError`` instead of silently
silently affecting every other module that imports this constant.
"""

# Wrap in MappingProxyType to make accidental mutation fail loudly.
REQUEST_HEADER = _MappingProxyType(REQUEST_HEADER)


def make_session(
    pool_size: int = DEFAULT_POOL_SIZE,
    retry_total: int = DEFAULT_RETRY_TOTAL,
    retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    verify_ssl: bool = True,
) -> requests.Session:
    """Build a configured :class:`requests.Session` with connection pooling.

    The session applies:

    - a ``HTTPAdapter`` with the given ``pool_size`` (default 10) so that
      multiple HTTPS handshakes are not paid for on every request,
    - a ``Retry`` policy that retries idempotent verbs (``GET``/``HEAD``)
      up to ``retry_total`` times with exponential backoff,
    - the canonical ``User-Agent`` header.

    Each call returns a fresh session; callers are expected to close it
    (typically via a ``with`` block).
    """
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    try:
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
    except ImportError:
        # ``requests`` always pulls urllib3 in, so this is a safety net.
        return session

    retry = Retry(
        total=retry_total,
        backoff_factor=retry_backoff,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
    )
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=pool_size,
        pool_maxsize=pool_size,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Stash verify_ssl on the session so callers can read it without
    # patching individual requests.
    session.verify = verify_ssl
    return session


# ---- tqdm compatibility ------------------------------------------------------
try:
    from tqdm import tqdm as _tqdm_real  # type: ignore

    TQDM_AVAILABLE: bool = True
except ImportError:  # pragma: no cover - exercised only without tqdm
    TQDM_AVAILABLE = False
    _tqdm_real = None  # type: ignore


class _TqdmFallback:
    """Minimal tqdm-compatible progress bar.

    Implements only the surface that wparc uses:

    - Context-manager protocol (``__enter__`` / ``__exit__``)
    - ``update(n=1)``
    - Iteration protocol (``__iter__``)

    Used as a silent no-op when :mod:`tqdm` is not installed.
    """

    def __init__(
        self,
        iterable: Optional[Any] = None,
        total: Optional[int] = None,
        desc: str = "",
        unit: str = "",
        **kwargs: Any,
    ) -> None:
        self.iterable = iterable
        self.total = total
        self.desc = desc
        self.unit = unit
        self.n = 0

    def __enter__(self) -> "_TqdmFallback":
        return self

    def __exit__(self, *args: Any) -> bool:
        return False

    def __iter__(self) -> Iterator[Any]:
        if self.iterable is None:
            return iter(())
        return iter(self.iterable)

    def update(self, n: int = 1) -> None:
        self.n += n

    def close(self) -> None:
        """No-op for API parity with tqdm."""
        return None


def tqdm(iterable: Optional[Any] = None, **kwargs: Any) -> Any:
    """Return a tqdm progress bar or a no-op fallback.

    Acts as a thin factory so callers can write::

        bar = tqdm(total=10, desc="working")
        bar.update(1)

    regardless of whether tqdm is installed.
    """
    if _tqdm_real is None:
        return _TqdmFallback(iterable=iterable, **kwargs)
    return _tqdm_real(iterable=iterable, **kwargs)


# ---- urllib3 SSL-warning helpers --------------------------------------------


@contextlib.contextmanager
def urllib3_warnings_suppressed() -> Iterator[None]:
    """Silence ``urllib3.exceptions.InsecureRequestWarning``.

    Used while making requests with ``verify=False`` so the CLI output
    is not polluted with warnings. Warnings are always re-enabled on
    exit, even when the wrapped code raises.

    .. note::
        ``urllib3.disable_warnings`` toggles a *process-global* flag,
        and ``urllib3`` v2 removed the historical ``enable_warnings``
        helper. The state cannot be cleanly restored to its pre-block
        value, so we simply re-call ``disable_warnings`` for the
        specific ``InsecureRequestWarning`` class on the way out as
        a no-op safety net. The global warning filter is unaffected.
    """
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except (AttributeError, Exception):
        # If urllib3 version doesn't support this, fall back silently.
        pass
    try:
        yield
    finally:
        # Best-effort re-disable on exit. ``urllib3`` v2 dropped the
        # ``enable_warnings`` symbol entirely, so we only call it if
        # it actually exists. This keeps behaviour stable across
        # urllib3 v1 and v2.
        enable = getattr(urllib3, "enable_warnings", None)
        if callable(enable):
            try:
                enable()
            except Exception:
                pass


def get_ssl_warning_context(verify_ssl: bool) -> contextlib.AbstractContextManager:
    """Return the appropriate SSL-warning context manager.

    When ``verify_ssl`` is ``False`` we temporarily suppress
    ``InsecureRequestWarning``; otherwise we yield a null context.

    This helper avoids the duplicated two-line ``if not verify_ssl`` check
    that previously lived in every wpapi sub-module.
    """
    if not verify_ssl:
        return urllib3_warnings_suppressed()
    return contextlib.nullcontext()
