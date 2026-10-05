# -*- coding: utf-8 -*-
"""
Tests for :mod:`wparc.wpapi.dump` — the route dump / pagination / data
collection primitives.
"""
import json
from unittest.mock import Mock, mock_open, patch

import pytest
import requests

from wparc.wpapi import dump, routes

# Default YAML returned by the loader mock so each test that exercises
# ``collect_data`` does not have to spell out the full dict.
DEFAULT_KNOWN_ROUTES = {
    "public-list": [],
    "public-dict": [],
    "protected": [],
    "useless": [],
}


def _patch_yaml_load(routes_dict=None):
    """Return a context manager that patches the cached loader.

    The cached ``_load_known_routes`` in :mod:`wparc.wpapi.routes` is the
    single source of truth now; we patch it directly instead of mocking
    yaml.safe_load.
    """
    return patch(
        "wparc.wpapi.routes._load_known_routes",
        return_value=routes_dict or DEFAULT_KNOWN_ROUTES,
    )


# Per-module autouse fixture: invalidate the known_routes cache before
# every test so our mocked YAML is actually read.
@pytest.fixture(autouse=True)
def _clear_known_routes_cache():
    routes._load_known_routes.cache_clear()
    yield
    routes._load_known_routes.cache_clear()


class TestIsPaginatedEndpoint:
    def test_paginated_returns_true(self):
        route_data = {"endpoints": [{"args": {"page": {}, "per_page": {}}}]}
        assert dump._is_paginated_endpoint(route_data) is True

    def test_non_paginated_returns_false(self):
        route_data = {"endpoints": [{"args": {}}]}
        assert dump._is_paginated_endpoint(route_data) is False

    def test_list_args_returns_false(self):
        """WP sometimes stores ``args`` as a list of dicts."""
        route_data = {"endpoints": [{"args": []}]}
        assert dump._is_paginated_endpoint(route_data) is False

    def test_no_endpoints_returns_false(self):
        assert dump._is_paginated_endpoint({"endpoints": []}) is False
        assert dump._is_paginated_endpoint({}) is False


class TestHandleUnknownRoute:
    @patch("wparc.wpapi.dump.dump_route_list")
    @patch("wparc.wpapi.dump.get_self_url")
    def test_paginated_unknown_routed_to_list(self, mock_get_url, mock_dump_list):
        mock_get_url.return_value = "http://x/items"
        mock_dump_list.return_value = True
        route_data = {
            "_links": {"self": {"href": "http://x/items"}},
            "endpoints": [{"args": {"page": {}, "per_page": {}}}],
        }
        result = dump._handle_unknown_route(
            route="/custom/v1/items",
            route_data=route_data,
            filepath="/tmp/data",
            verify_ssl=True,
            timeout=10,
            page_size=100,
            retry_count=3,
        )
        assert result is True
        mock_dump_list.assert_called_once()

    @patch("wparc.wpapi.dump.dump_route_dict")
    @patch("wparc.wpapi.dump.get_self_url")
    def test_non_paginated_unknown_routed_to_dict(self, mock_get_url, mock_dump_dict):
        mock_get_url.return_value = "http://x/settings"
        mock_dump_dict.return_value = True
        route_data = {
            "_links": {"self": {"href": "http://x/settings"}},
            "endpoints": [{"args": {}}],
        }
        result = dump._handle_unknown_route(
            route="/custom/settings",
            route_data=route_data,
            filepath="/tmp/data",
            verify_ssl=True,
            timeout=10,
            page_size=100,
            retry_count=3,
        )
        assert result is True
        mock_dump_dict.assert_called_once()

    @patch("wparc.wpapi.dump.get_self_url")
    def test_no_endpoints_returns_false(self, mock_get_url):
        result = dump._handle_unknown_route(
            route="/empty",
            route_data={"endpoints": []},
            filepath="/tmp/data",
            verify_ssl=True,
            timeout=10,
            page_size=100,
            retry_count=3,
        )
        assert result is False
        mock_get_url.assert_not_called()

    @patch("wparc.wpapi.dump.get_self_url")
    def test_no_self_url_returns_false(self, mock_get_url):
        mock_get_url.return_value = None
        route_data = {
            "_links": {},
            "endpoints": [{"args": {"page": {}, "per_page": {}}}],
        }
        result = dump._handle_unknown_route(
            route="/no-url",
            route_data=route_data,
            filepath="/tmp/data",
            verify_ssl=True,
            timeout=10,
            page_size=100,
            retry_count=3,
        )
        assert result is False


class TestDumpRouteList:
    """``dump_route_list`` paginates a list endpoint to a JSONL file."""

    @patch("wparc.wpapi.dump.requests.get")
    def test_writes_paginated_jsonl(self, mock_get, tmp_path):
        page1 = Mock(json=lambda: [{"id": 1}, {"id": 2}])
        page1.status_code = 200
        page1.headers = {"X-WP-TotalPages": "3", "X-WP-Total": "5"}
        page1.raise_for_status = Mock()

        page2 = Mock(json=lambda: [{"id": 3}, {"id": 4}])
        page2.status_code = 200
        page2.headers = {}
        page2.raise_for_status = Mock()

        page3 = Mock(json=lambda: [{"id": 5}])
        page3.status_code = 200
        page3.headers = {}
        page3.raise_for_status = Mock()

        page4 = Mock(json=lambda: [])
        page4.status_code = 200
        page4.headers = {}
        page4.raise_for_status = Mock()

        mock_get.side_effect = [page1, page2, page3, page4]

        dump.dump_route_list(
            url="http://example.com/wp-json/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=2,
            retry_count=1,
        )
        outfile = tmp_path / "wp_v2_posts.jsonl"
        assert outfile.exists()
        rows = [json.loads(line) for line in outfile.read_text().splitlines() if line]
        assert rows == [{"id": i} for i in range(1, 6)]

    @patch("wparc.wpapi.dump.requests.get")
    def test_breaks_on_dict_response(self, mock_get, tmp_path):
        # Some endpoints return a single dict (non-list). We must stop
        # without writing any rows.
        page = Mock(json=lambda: {"not": "a list"})
        page.status_code = 200
        page.headers = {}
        page.raise_for_status = Mock()
        mock_get.return_value = page

        dump.dump_route_list(
            url="http://x/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=100,
            retry_count=1,
        )
        # An empty JSONL file is still written (the outer write is
        # unconditional), but it must contain zero rows.
        outfile = tmp_path / "wp_v2_posts.jsonl"
        if outfile.exists():
            assert outfile.read_text() == ""

    @patch("wparc.wpapi.dump.requests.get")
    def test_breaks_on_non_200_status(self, mock_get, tmp_path):
        page = Mock()
        page.status_code = 404
        page.headers = {}
        page.raise_for_status = Mock()
        mock_get.return_value = page

        dump.dump_route_list(
            url="http://x/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=100,
            retry_count=1,
        )
        # Same: non-200 → no rows written.
        outfile = tmp_path / "wp_v2_posts.jsonl"
        if outfile.exists():
            assert outfile.read_text() == ""

    @patch("wparc.wpapi.dump.requests.get")
    def test_retries_on_failure(self, mock_get, tmp_path):
        # Two failures, then a success.
        success = Mock(json=lambda: [{"id": 1}])
        success.status_code = 200
        success.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "1"}
        success.raise_for_status = Mock()
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("first"),
            requests.exceptions.ConnectionError("second"),
            success,
        ]
        dump.dump_route_list(
            url="http://x/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=10,
            retry_count=3,
        )
        assert mock_get.call_count == 3

    @patch("wparc.wpapi.dump.requests.get")
    def test_aborts_after_max_retries(self, mock_get, tmp_path):
        # All attempts fail.
        mock_get.side_effect = requests.exceptions.ConnectionError("nope")
        dump.dump_route_list(
            url="http://x/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=10,
            retry_count=2,
        )
        # Two attempts only.
        assert mock_get.call_count == 2

    @patch("wparc.wpapi.dump.requests.get")
    def test_handles_invalid_json(self, mock_get, tmp_path):
        page = Mock()
        page.status_code = 200
        page.headers = {}
        page.json.side_effect = ValueError("not json")
        page.raise_for_status = Mock()
        mock_get.return_value = page
        dump.dump_route_list(
            url="http://x/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=10,
            retry_count=1,
        )
        outfile = tmp_path / "wp_v2_posts.jsonl"
        # Invalid JSON triggers an early break, so the JSONL must be
        # empty (or not exist).
        if outfile.exists():
            assert outfile.read_text() == ""


class TestDumpRouteListNewOptions:
    """Verify auth/proxy/rate_limit_delay parameters are threaded through."""

    @patch("wparc.wpapi.dump.time.sleep")
    @patch("wparc.wpapi.dump.requests.get")
    def test_auth_proxy_passed_to_request(self, mock_get, _mock_sleep, tmp_path):
        """auth + proxy must reach the underlying ``requests.get`` call."""
        page = Mock(json=lambda: [{"id": 1}])
        page.status_code = 200
        page.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "1"}
        page.raise_for_status = Mock()
        mock_get.return_value = page

        dump.dump_route_list(
            url="http://x/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=10,
            retry_count=1,
            auth=("user", "pw"),
            proxy="http://127.0.0.1:8080",
            rate_limit_delay=0.0,
        )

        mock_get.assert_called_once()
        call = mock_get.call_args
        assert call.kwargs["auth"] == ("user", "pw")
        assert call.kwargs["proxies"] == {
            "http": "http://127.0.0.1:8080",
            "https": "http://127.0.0.1:8080",
        }

    @patch("wparc.wpapi.dump.time.sleep")
    @patch("wparc.wpapi.dump.requests.get")
    def test_no_proxy_means_no_proxies_kwarg(self, mock_get, _mock_sleep, tmp_path):
        page = Mock(json=lambda: [{"id": 1}])
        page.status_code = 200
        page.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "1"}
        page.raise_for_status = Mock()
        mock_get.return_value = page

        dump.dump_route_list(
            url="http://x/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=10,
            retry_count=1,
            proxy=None,
        )
        assert mock_get.call_args.kwargs["proxies"] is None

    @patch("wparc.wpapi.dump.time.sleep")
    @patch("wparc.wpapi.dump.requests.get")
    def test_rate_limit_delay_calls_sleep(self, mock_get, mock_sleep, tmp_path):
        page = Mock(json=lambda: [{"id": 1}])
        page.status_code = 200
        page.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "1"}
        page.raise_for_status = Mock()
        mock_get.return_value = page

        dump.dump_route_list(
            url="http://x/wp/v2/posts",
            route="/wp/v2/posts",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
            page_size=10,
            retry_count=1,
            rate_limit_delay=0.5,
        )
        # Sleep must be called with the requested delay.
        mock_sleep.assert_any_call(0.5)


class TestDumpRouteDict:
    """``dump_route_dict`` saves a single non-paginated endpoint to JSON."""

    @patch("wparc.wpapi.dump.requests.get")
    def test_writes_dict_response(self, mock_get, tmp_path):
        page = Mock()
        page.status_code = 200
        page.text = '{"name":"site"}'
        page.raise_for_status = Mock()
        mock_get.return_value = page
        dump.dump_route_dict(
            url="http://x/wp/v2/settings",
            route="/wp/v2/settings",
            filepath=str(tmp_path),
            verify_ssl=True,
            timeout=10,
        )
        outfile = tmp_path / "wp_v2_settings.json"
        assert outfile.read_text() == '{"name":"site"}'

    @patch("wparc.wpapi.dump.requests.get")
    def test_request_exception_is_caught(self, mock_get, tmp_path):
        # dump_route_dict historically re-raised on RequestException; we
        # accept either propagate or return-early behaviour.
        mock_get.side_effect = requests.exceptions.ConnectionError("net")
        try:
            dump.dump_route_dict(
                url="http://x/wp/v2/settings",
                route="/wp/v2/settings",
                filepath=str(tmp_path),
                verify_ssl=True,
                timeout=10,
            )
        except requests.exceptions.ConnectionError:
            pass
        # Either way, no output file is created.
        assert not (tmp_path / "wp_v2_settings.json").exists()


class TestCollectData:
    """``collect_data`` orchestrates the full route extraction."""

    @patch("wparc.wpapi.routes._load_known_routes")
    @patch("wparc.wpapi.dump.open", new_callable=lambda: mock_open(read_data=""))
    @patch("wparc.wpapi.dump.requests.get")
    def test_full_dump_with_known_routes(self, mock_get, _mock_file, mock_yaml):
        mock_yaml.return_value = {
            "public-list": ["/wp/v2/posts"],
            "public-dict": ["/wp/v2/types"],
            "protected": [],
            "useless": [],
        }

        root = Mock()
        root.json.return_value = {
            "routes": {
                "/wp/v2/posts": {
                    "_links": {"self": {"href": "http://x/wp/v2/posts"}},
                    "endpoints": [{"args": {"page": {}, "per_page": {}}}],
                },
                "/wp/v2/types": {
                    "_links": {"self": {"href": "http://x/wp/v2/types"}},
                    "endpoints": [{"args": {}}],
                },
            }
        }
        root.status_code = 200
        root.raise_for_status = Mock()
        root.headers = {}

        posts_page = Mock()
        posts_page.json.return_value = [{"id": 1}, {"id": 2}]
        posts_page.status_code = 200
        posts_page.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "2"}
        posts_page.raise_for_status = Mock()

        types_page = Mock()
        types_page.json.return_value = {"post": "Post"}
        types_page.status_code = 200
        types_page.raise_for_status = Mock()
        types_page.text = '{"post":"Post"}'

        mock_get.side_effect = [root, posts_page, types_page]

        with patch("wparc.wpapi.dump.os.makedirs"):
            with patch("wparc.wpapi.dump.TQDM_AVAILABLE", False):
                stats = dump.collect_data(
                    "example.com", get_unknown=False, force_https=True, verify_ssl=True
                )
        assert stats["routes_processed"] == 2
        assert stats["routes_skipped"] == 0
        assert stats["total_routes"] == 2

    @patch("wparc.wpapi.routes._load_known_routes")
    @patch("wparc.wpapi.dump.open", new_callable=lambda: mock_open(read_data=""))
    @patch("wparc.wpapi.dump.requests.get")
    def test_protected_routes_are_skipped(self, mock_get, _mock_file, mock_yaml):
        mock_yaml.return_value = {
            "public-list": [],
            "public-dict": [],
            "protected": ["/wp/v2/users/me"],
            "useless": [],
        }
        root = Mock()
        root.json.return_value = {
            "routes": {
                "/wp/v2/users/me": {
                    "_links": {"self": {"href": "http://x/me"}},
                    "endpoints": [{"args": {}}],
                }
            }
        }
        root.status_code = 200
        root.raise_for_status = Mock()
        root.headers = {}
        mock_get.return_value = root
        with patch("wparc.wpapi.dump.os.makedirs"):
            with patch("wparc.wpapi.dump.TQDM_AVAILABLE", False):
                stats = dump.collect_data("example.com", get_unknown=False)
        assert stats["routes_processed"] == 0
        assert stats["routes_skipped"] == 1

    @patch("wparc.wpapi.routes._load_known_routes")
    @patch("wparc.wpapi.dump.open", new_callable=lambda: mock_open(read_data=""))
    @patch("wparc.wpapi.dump.requests.get")
    def test_useless_regex_routes_skipped(self, mock_get, _mock_file, mock_yaml):
        mock_yaml.return_value = DEFAULT_KNOWN_ROUTES
        root = Mock()
        root.json.return_value = {
            "routes": {
                "/wp/v2/posts/(?P<id>\\d+)": {
                    "_links": {"self": {"href": "http://x/posts/x"}},
                    "endpoints": [{"args": {}}],
                }
            }
        }
        root.status_code = 200
        root.raise_for_status = Mock()
        root.headers = {}
        mock_get.return_value = root
        with patch("wparc.wpapi.dump.os.makedirs"):
            with patch("wparc.wpapi.dump.TQDM_AVAILABLE", False):
                stats = dump.collect_data("example.com", get_unknown=False)
        assert stats["routes_skipped"] == 1

    @patch("wparc.wpapi.routes._load_known_routes")
    @patch("wparc.wpapi.dump.open", new_callable=lambda: mock_open(read_data=""))
    @patch("wparc.wpapi.dump.requests.get")
    def test_unknown_routes_with_get_unknown(self, mock_get, _mock_file, mock_yaml):
        mock_yaml.return_value = DEFAULT_KNOWN_ROUTES
        root = Mock()
        root.json.return_value = {
            "routes": {
                "/custom/v1/list": {
                    "_links": {"self": {"href": "http://x/list"}},
                    "endpoints": [{"args": {"page": {}, "per_page": {}}}],
                }
            }
        }
        root.status_code = 200
        root.raise_for_status = Mock()
        root.headers = {}

        list_page = Mock()
        list_page.json.return_value = [{"id": 1}]
        list_page.status_code = 200
        list_page.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "1"}
        list_page.raise_for_status = Mock()

        mock_get.side_effect = [root, list_page]
        with patch("wparc.wpapi.dump.os.makedirs"):
            with patch("wparc.wpapi.dump.TQDM_AVAILABLE", False):
                stats = dump.collect_data("example.com", get_unknown=True)
        assert stats["routes_processed"] == 1

    @patch("wparc.wpapi.routes._load_known_routes")
    @patch("wparc.wpapi.dump.open", new_callable=lambda: mock_open(read_data=""))
    @patch("wparc.wpapi.dump.requests.get")
    def test_ssl_error_raises_custom_exception(self, mock_get, _mock_file, mock_yaml):
        from wparc.exceptions import SSLVerificationError

        mock_yaml.return_value = DEFAULT_KNOWN_ROUTES
        mock_get.side_effect = requests.exceptions.SSLError("ssl boom")
        with patch("wparc.wpapi.dump.os.makedirs"):
            with pytest.raises(SSLVerificationError):
                dump.collect_data("example.com")

    @patch("wparc.wpapi.routes._load_known_routes")
    @patch("wparc.wpapi.dump.open", new_callable=lambda: mock_open(read_data=""))
    @patch("wparc.wpapi.dump.requests.get")
    def test_http_error_raises_api_error(self, mock_get, _mock_file, mock_yaml):
        from wparc.exceptions import APIError

        mock_yaml.return_value = DEFAULT_KNOWN_ROUTES
        response = Mock()
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=Mock(status_code=404)
        )
        mock_get.return_value = response
        with patch("wparc.wpapi.dump.os.makedirs"):
            with pytest.raises(APIError):
                dump.collect_data("example.com")


class TestParallelCollect:
    """``workers > 1`` must dispatch jobs via ThreadPoolExecutor."""

    @patch("wparc.wpapi.routes._load_known_routes")
    @patch("wparc.wpapi.dump.open", new_callable=lambda: mock_open(read_data=""))
    @patch("wparc.wpapi.dump.requests.get")
    def test_parallel_workers_invokes_executor(self, mock_get, _mock_file, mock_yaml):
        """When ``workers > 1`` we must observe ThreadPoolExecutor usage."""
        mock_yaml.return_value = {
            "public-list": ["/wp/v2/posts"],
            "public-dict": [],
            "protected": [],
            "useless": [],
        }
        root = Mock()
        root.json.return_value = {
            "routes": {
                "/wp/v2/posts": {
                    "_links": {"self": {"href": "http://x/posts"}},
                    "endpoints": [{"args": {"page": {}, "per_page": {}}}],
                }
            }
        }
        root.status_code = 200
        root.raise_for_status = Mock()
        root.headers = {}
        page = Mock(json=lambda: [{"id": 1}])
        page.status_code = 200
        page.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "1"}
        page.raise_for_status = Mock()
        mock_get.side_effect = [root, page]

        with patch("wparc.wpapi.dump.os.makedirs"):
            with patch("wparc.wpapi.dump.TQDM_AVAILABLE", False):
                with patch("wparc.wpapi.dump.ThreadPoolExecutor") as mock_executor_cls:
                    mock_executor = Mock()
                    mock_executor.__enter__ = Mock(return_value=mock_executor)
                    mock_executor.__exit__ = Mock(return_value=None)
                    mock_executor_cls.return_value = mock_executor
                    future = Mock()
                    future.result.return_value = True
                    mock_executor.submit.return_value = future
                    with patch(
                        "wparc.wpapi.dump.as_completed",
                        return_value=[future],
                    ):
                        stats = dump.collect_data("example.com", get_unknown=False, workers=4)
        mock_executor_cls.assert_called_once_with(max_workers=4)
        assert stats["routes_processed"] == 1

    @patch("wparc.wpapi.routes._load_known_routes")
    @patch("wparc.wpapi.dump.open", new_callable=lambda: mock_open(read_data=""))
    @patch("wparc.wpapi.dump.requests.get")
    def test_serial_path_when_workers_is_one(self, mock_get, _mock_file, mock_yaml):
        """``workers=1`` must NOT spawn a ThreadPoolExecutor."""
        mock_yaml.return_value = {
            "public-list": ["/wp/v2/posts"],
            "public-dict": [],
            "protected": [],
            "useless": [],
        }
        root = Mock()
        root.json.return_value = {
            "routes": {
                "/wp/v2/posts": {
                    "_links": {"self": {"href": "http://x/posts"}},
                    "endpoints": [{"args": {"page": {}, "per_page": {}}}],
                }
            }
        }
        root.status_code = 200
        root.raise_for_status = Mock()
        root.headers = {}
        page = Mock(json=lambda: [{"id": 1}])
        page.status_code = 200
        page.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "1"}
        page.raise_for_status = Mock()
        mock_get.side_effect = [root, page]

        with patch("wparc.wpapi.dump.os.makedirs"):
            with patch("wparc.wpapi.dump.TQDM_AVAILABLE", False):
                with patch("wparc.wpapi.dump.ThreadPoolExecutor") as mock_executor_cls:
                    stats = dump.collect_data("example.com", get_unknown=False, workers=1)
        mock_executor_cls.assert_not_called()
        assert stats["routes_processed"] == 1
