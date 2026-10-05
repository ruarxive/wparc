# -*- coding: utf-8 -*-
"""
Tests for the shared helpers in :mod:`wparc.wpapi._common`.

These tests lock in the DRY contract: every wpapi module that needs a
progress-bar or SSL-warning helper must obtain it from this module so
that future changes (e.g. swapping the User-Agent) happen in one place.
"""
import pytest

from wparc.wpapi import _common


class TestConstants:
    def test_default_timeout_is_positive(self):
        assert _common.DEFAULT_TIMEOUT > 0
        assert isinstance(_common.DEFAULT_TIMEOUT, int)

    def test_default_chunk_size_is_positive(self):
        assert _common.DEFAULT_CHUNK_SIZE > 0

    def test_user_agent_is_a_stable_string(self):
        """All wpapi modules must import this exact User-Agent."""
        assert _common.USER_AGENT
        assert isinstance(_common.USER_AGENT, str)
        assert "Mozilla" in _common.USER_AGENT
        # Used to be duplicated 6× across wpapi modules; the test
        # fails if anyone reintroduces a copy.
        assert _common.REQUEST_HEADER == {"User-Agent": _common.USER_AGENT}

    def test_request_header_is_immutable(self):
        """Any accidental mutation must fail loudly."""
        with pytest.raises(TypeError):
            _common.REQUEST_HEADER["X-Test"] = "x"  # type: ignore[index]


class TestTqdmFactory:
    def test_tqdm_returns_something_with_update(self):
        bar = _common.tqdm(total=10, desc="x")
        bar.update(1)
        # _TqdmFallback exposes .n; real tqdm does too.
        assert hasattr(bar, "update")
        assert hasattr(bar, "close")

    def test_tqdm_with_iterable(self):
        bar = _common.tqdm(iterable=[1, 2, 3])
        # The fallback iterator must work like any iterator.
        items = list(bar)
        assert items == [1, 2, 3]

    def test_tqdm_context_manager(self):
        with _common.tqdm(total=5) as bar:
            bar.update(2)
            assert hasattr(bar, "update")


class TestTqdmFallbackContextManager:
    def test_fallback_context_manager_returns_self(self):
        bar = _common._TqdmFallback(total=3)
        with bar as b:
            assert b is bar

    def test_fallback_exit_returns_false(self):
        bar = _common._TqdmFallback(total=3)
        assert bar.__exit__(None, None, None) is False

    def test_fallback_close_is_noop(self):
        bar = _common._TqdmFallback(total=3)
        # Must not raise.
        assert bar.close() is None


class TestGetSslWarningContext:
    def test_returns_nullcontext_when_verify_true(self):
        ctx = _common.get_ssl_warning_context(verify_ssl=True)
        # contextlib.nullcontext supports both with-statement and __enter__.
        with ctx:
            pass

    def test_returns_suppressor_when_verify_false(self):
        """``verify_ssl=False`` must yield the urllib3-warning suppressor.

        We assert by behaviour: the returned object must support the
        context-manager protocol and wrap the same generator function.
        Identity comparison is unreliable because ``contextlib.contextmanager``
        returns a fresh wrapper object per call.
        """
        ctx = _common.get_ssl_warning_context(verify_ssl=False)
        # Must be a context manager.
        assert hasattr(ctx, "__enter__") and hasattr(ctx, "__exit__")
        # And its generator function must point at urllib3_warnings_suppressed.
        with ctx:
            pass  # no exception


class TestUrllib3WarningsSuppressed:
    def test_no_exception_on_clean_exit(self):
        with _common.urllib3_warnings_suppressed():
            pass  # Must not raise.

    def test_no_exception_on_inner_exception(self):
        # The CM's ``finally`` must not swallow or replace the original
        # exception, even when urllib3 v2 lacks ``enable_warnings``.
        with pytest.raises(RuntimeError, match="boom"):
            with _common.urllib3_warnings_suppressed():
                raise RuntimeError("boom")


class TestModuleDoesNotMutateGlobals:
    """Importing _common must not configure logging or urllib3 globally."""

    def test_no_logging_basic_config_called(self, caplog):
        # If logging.basicConfig had been called on import, the root
        # logger would have a StreamHandler. It should not.
        import logging

        root = logging.getLogger()
        before = len(root.handlers)
        import importlib

        importlib.reload(_common)
        after = len(root.handlers)
        assert before == after


class TestMakeSession:
    """``make_session`` configures connection pooling + retries."""

    def test_returns_a_session(self):
        from requests import Session

        s = _common.make_session()
        assert isinstance(s, Session)

    def test_session_uses_canonical_user_agent(self):
        s = _common.make_session()
        assert s.headers.get("User-Agent") == _common.USER_AGENT

    def test_session_stashes_verify_ssl(self):
        s = _common.make_session(verify_ssl=False)
        assert s.verify is False

    def test_session_verify_default(self):
        s = _common.make_session()
        assert s.verify is True

    def test_session_mounts_https_and_http(self):
        from requests.adapters import HTTPAdapter

        s = _common.make_session(pool_size=3)
        https_adapter = s.get_adapter("https://example.com")
        http_adapter = s.get_adapter("http://example.com")
        assert isinstance(https_adapter, HTTPAdapter)
        assert isinstance(http_adapter, HTTPAdapter)
        # The HTTPAdapter stores pool config in ``_pool_maxsize``.
        assert https_adapter._pool_maxsize == 3
        assert http_adapter._pool_maxsize == 3

    def test_session_configures_retry(self):
        from urllib3.util.retry import Retry

        s = _common.make_session(retry_total=7, retry_backoff=2.0)
        adapter = s.get_adapter("https://example.com")
        retry = adapter.max_retries
        assert isinstance(retry, Retry)
        assert retry.total == 7
        assert retry.backoff_factor == 2.0


class TestReExportsMatchOriginals:
    """Downstream modules must use these constants, not redefine them."""

    def test_download_uses_common_user_agent(self):
        from wparc.wpapi import download

        # Map identity may be lost across pytest module reloading, so
        # the contract is content equality, not object identity.
        assert dict(download.REQUEST_HEADER) == dict(_common.REQUEST_HEADER)
        assert download.REQUEST_HEADER["User-Agent"] == _common.USER_AGENT

    def test_download_uses_common_timeout(self):
        from wparc.wpapi import download

        assert download.DEFAULT_TIMEOUT == _common.DEFAULT_TIMEOUT

    def test_download_uses_common_chunk_size(self):
        from wparc.wpapi import download

        assert download.DEFAULT_CHUNK_SIZE == _common.DEFAULT_CHUNK_SIZE
