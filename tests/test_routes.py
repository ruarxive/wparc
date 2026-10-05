# -*- coding: utf-8 -*-
"""
Tests for :mod:`wparc.wpapi.routes` — route analysis and probing.

These tests focus on the public helpers (``ping``, ``generate_routes_yaml``)
and on the private ``_test_route`` heuristic that decides whether an
unknown route is ``protected`` / ``public-list`` / ``public-dict`` / ``useless``.
"""
from unittest.mock import Mock, patch

import pytest
import requests

from wparc.wpapi import routes


# Invalidate the known_routes cache before every test that mocks yaml.safe_load.
@pytest.fixture(autouse=True)
def _clear_known_routes_cache():
    routes._load_known_routes.cache_clear()
    yield
    routes._load_known_routes.cache_clear()


class TestGetSelfUrl:
    def test_handles_dict_format(self):
        data = {"_links": {"self": {"href": "http://x/wp-json/wp/v2/posts/1"}}}
        assert routes.get_self_url(data) == "http://x/wp-json/wp/v2/posts/1"

    def test_handles_string_format(self):
        data = {"_links": {"self": "http://x/wp-json/wp/v2/posts/1"}}
        assert routes.get_self_url(data) == "http://x/wp-json/wp/v2/posts/1"

    def test_handles_list_format(self):
        data = {"_links": {"self": [{"href": "http://x/wp-json/posts/1"}]}}
        assert routes.get_self_url(data) == "http://x/wp-json/posts/1"

    def test_returns_none_for_missing_keys(self):
        assert routes.get_self_url({}) is None
        assert routes.get_self_url({"_links": {}}) is None

    def test_returns_none_for_empty_list(self):
        assert routes.get_self_url({"_links": {"self": []}}) is None


class TestPing:
    @patch("wparc.wpapi.routes.requests.get")
    def test_ping_returns_route_count(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"routes": {"/a": {}, "/b": {}}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        result = routes.ping("example.com", force_https=True, verify_ssl=True)
        assert result["routes_count"] == 2
        assert result["routes"] == ["/a", "/b"]

    @patch("wparc.wpapi.routes.requests.get")
    def test_ping_unexpected_format_returns_empty(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"not_routes": True}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        assert routes.ping("example.com") == {}

    @patch("wparc.wpapi.routes.requests.get")
    def test_ping_handles_ssl_error(self, mock_get):
        from wparc.exceptions import SSLVerificationError

        mock_get.side_effect = requests.exceptions.SSLError("ssl boom")
        with pytest.raises(SSLVerificationError):
            routes.ping("example.com")

    @patch("wparc.wpapi.routes.requests.get")
    def test_ping_handles_request_exception(self, mock_get):
        from wparc.exceptions import APIError

        mock_get.side_effect = requests.exceptions.ConnectionError("net")
        with pytest.raises(APIError):
            routes.ping("example.com")

    @patch("wparc.wpapi.routes.requests.get")
    def test_ping_handles_invalid_json(self, mock_get):
        from wparc.exceptions import APIError

        mock_response = Mock()
        mock_response.json.side_effect = ValueError("not json")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        with pytest.raises(APIError):
            routes.ping("example.com")


class TestAnalyzeRoutes:
    @patch("wparc.wpapi.routes.requests.get")
    def test_categorises_known_and_unknown(self, mock_get):
        # Build a fake WP-JSON payload.
        wpjson = {
            "routes": {
                "/wp/v2/posts": {"_links": {"self": {"href": "http://x/posts"}}},
                "/wp/v2/users/me": {"_links": {"self": {"href": "http://x/me"}}},
                "/custom/v1/items": {"_links": {"self": {"href": "http://x/items"}}},
            }
        }
        # Clear the known_routes cache so our mocked YAML is actually read.
        routes._load_known_routes.cache_clear()
        with patch("wparc.wpapi.routes.yaml.safe_load") as yaml_load:
            yaml_load.return_value = {
                "public-list": ["/wp/v2/posts"],
                "protected": ["/wp/v2/users/me"],
                "public-dict": [],
                "useless": [],
            }
            mock_response = Mock()
            mock_response.json.return_value = wpjson
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            with patch("wparc.wpapi.routes.TQDM_AVAILABLE", False):
                result = routes.analyze_routes("example.com")
        assert result["total_routes"] == 3
        assert result["statistics"]["public-list"] == 1
        assert result["statistics"]["protected"] == 1
        assert result["statistics"]["unknown"] == 1
        assert result["unknown_routes"] == ["/custom/v1/items"]

    @patch("wparc.wpapi.routes.requests.get")
    def test_handles_unexpected_response_format(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"not_routes": True}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        with patch("wparc.wpapi.routes.TQDM_AVAILABLE", False):
            result = routes.analyze_routes("example.com")
        assert result["total_routes"] == 0
        assert result["unknown_routes"] == []


class TestTestRoute:
    """Covers the private _test_route heuristic."""

    def test_regex_route_is_useless(self):
        # "regex" routes (?P<) are categorised useless without HTTP.
        route_data = {"endpoints": []}
        assert routes._test_route("/foo/(?P<id>\\d+)", route_data, "") == "useless"

    def test_route_with_no_endpoints_returns_none(self):
        assert routes._test_route("/foo", {"endpoints": []}, "") is None

    @patch("wparc.wpapi.routes.requests.get")
    def test_paginated_route_returning_list_is_public_list(self, mock_get):
        route_data = {
            "_links": {"self": {"href": "http://x/list"}},
            "endpoints": [{"args": {"page": {}, "per_page": {}}}],
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1}]
        mock_get.return_value = mock_response
        result = routes._test_route("/wp/v2/posts", route_data, "http://x")
        assert result == "public-list"

    @patch("wparc.wpapi.routes.requests.get")
    def test_paginated_route_returning_401_is_protected(self, mock_get):
        route_data = {
            "_links": {"self": {"href": "http://x/me"}},
            "endpoints": [{"args": {"page": {}, "per_page": {}}}],
        }
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        result = routes._test_route("/wp/v2/users/me", route_data, "http://x")
        assert result == "protected"

    @patch("wparc.wpapi.routes.requests.get")
    def test_dict_response_is_dict_returned(self, mock_get):
        """A non-paginated dict endpoint must end up as ``public-dict``."""
        route_data = {
            "_links": {"self": {"href": "http://x/settings"}},
            "endpoints": [{"args": {}}],
        }
        # The function probes the route twice (paginated probe + raw probe)
        # but the paginated probe is skipped because the args dict lacks
        # ``page`` / ``per_page``.
        raw_resp = Mock()
        raw_resp.status_code = 200
        raw_resp.json.return_value = {"site": "x"}
        mock_get.return_value = raw_resp
        result = routes._test_route("/settings", route_data, "http://x")
        assert result == "public-dict"


class TestGenerateRoutesYaml:
    def test_emits_only_non_empty_categories(self):
        categorized = {
            "protected": ["/wp/v2/users/me"],
            "public-list": [],
            "public-dict": ["/settings"],
            "useless": [],
        }
        out = routes.generate_routes_yaml(categorized)
        # Only non-empty categories appear.
        assert "public-list:" not in out
        assert "useless:" not in out
        # And the routes are sorted.
        assert out == "protected:\n- /wp/v2/users/me\npublic-dict:\n- /settings"

    def test_empty_input_returns_empty_string(self):
        assert (
            routes.generate_routes_yaml(
                {
                    "protected": [],
                    "public-list": [],
                    "public-dict": [],
                    "useless": [],
                }
            )
            == ""
        )


class TestLoadKnownRoutes:
    """Covers the @lru_cache on the known_routes loader."""

    def test_returns_cached_dict(self):
        # Clearing the cache forces a fresh read from disk, which works
        # because the package ships with ``data/known_routes.yml``.
        routes._load_known_routes.cache_clear()
        result = routes._load_known_routes()
        assert "public-list" in result
        assert "/wp/v2/posts" in result["public-list"]

    def test_is_cached(self):
        routes._load_known_routes.cache_clear()
        first = routes._load_known_routes()
        second = routes._load_known_routes()
        # ``lru_cache`` returns the same object for both calls.
        assert first is second

    def test_cache_clear_invalidates(self):
        first = routes._load_known_routes()
        routes._load_known_routes.cache_clear()
        second = routes._load_known_routes()
        # After clearing, a fresh dict is loaded; it must compare equal
        # in content but be a different object.
        assert first == second
        assert first is not second


class TestTestUnknownRoutes:
    """Covers the batch wrapper around _test_route."""

    @patch("wparc.wpapi.routes._test_route")
    def test_classifies_each_route(self, mock_test_route):
        # /a → protected, /b → public-list, /c → None (fallback to useless),
        # /d → useless.
        mock_test_route.side_effect = ["protected", "public-list", None, "useless"]
        wpjson = {
            "routes": {
                "/a": {},
                "/c": {},
                "/d": {},
                "/b": {},
            }
        }
        result = routes.test_unknown_routes(["/a", "/b", "/c", "/d"], wpjson, "http://x")
        assert result["protected"] == ["/a"]
        assert result["public-list"] == ["/b"]
        # Both /c (None → useless) and /d (explicit "useless") land in useless.
        assert sorted(result["useless"]) == ["/c", "/d"]
        assert result["public-dict"] == []

    @patch("wparc.wpapi.routes._test_route")
    def test_skips_routes_missing_from_wpjson(self, mock_test_route):
        result = routes.test_unknown_routes(["/missing"], {"routes": {}}, "http://x")
        assert result["protected"] == []
        mock_test_route.assert_not_called()
