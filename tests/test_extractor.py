# -*- coding: utf-8 -*-
"""
Tests for :mod:`wparc.cmds.extractor.Project` — the CLI wrapper around
the wpapi primitives.

Each method is exercised in isolation by mocking the corresponding
function in :mod:`wparc.wpapi.crawler`.
"""
from unittest.mock import patch

import pytest

from wparc.cmds.extractor import Project
from wparc.exceptions import DomainValidationError


class TestProjectInit:
    def test_default_verify_ssl(self):
        p = Project()
        assert p.verify_ssl is True

    def test_explicit_verify_ssl(self):
        assert Project(verify_ssl=False).verify_ssl is False


class TestProjectDump:
    @patch("wparc.cmds.extractor.collect_data")
    def test_dump_propagates_parameters(self, mock_collect):
        mock_collect.return_value = {"routes_processed": 5, "routes_skipped": 1}
        p = Project(verify_ssl=True)
        result = p.dump(
            domain="example.com",
            all_routes=True,
            https=True,
            timeout=120,
            page_size=50,
            retry_count=3,
        )
        mock_collect.assert_called_once_with(
            "example.com",
            get_unknown=True,
            force_https=True,
            verify_ssl=True,
            timeout=120,
            page_size=50,
            retry_count=3,
            auth=(None, None),
            proxy=None,
            rate_limit_delay=0.0,
            workers=1,
        )
        assert result == {"routes_processed": 5, "routes_skipped": 1}

    @patch("wparc.cmds.extractor.collect_data")
    def test_dump_passes_instance_verify_ssl(self, mock_collect):
        p = Project(verify_ssl=False)
        p.dump("example.com", False, False, timeout=10)
        kwargs = mock_collect.call_args.kwargs
        assert kwargs["verify_ssl"] is False

    @patch("wparc.cmds.extractor.collect_data")
    def test_dump_normalises_domain(self, mock_collect):
        p = Project()
        p.dump("HTTP://Example.com/", True, True)
        # validate_domain lowercases and strips the trailing slash.
        assert mock_collect.call_args.args[0] == "example.com"

    @patch("wparc.cmds.extractor.collect_data")
    def test_dump_rejects_invalid_domain(self, mock_collect):
        p = Project()
        with pytest.raises(DomainValidationError):
            p.dump("invalid..domain.com", True, True)


class TestProjectGetfiles:
    @patch("wparc.cmds.extractor.collect_files")
    def test_getfiles_default_workers(self, mock_collect):
        mock_collect.return_value = {
            "downloaded": 10,
            "failed": 0,
            "skipped": 0,
            "total": 10,
        }
        p = Project()
        result = p.getfiles("example.com")
        mock_collect.assert_called_once_with("example.com", verify_ssl=True, workers=5, resume=True)
        assert result["downloaded"] == 10

    @patch("wparc.cmds.extractor.collect_files")
    def test_getfiles_custom_workers(self, mock_collect):
        p = Project()
        p.getfiles("example.com", workers=10, resume=False)
        kwargs = mock_collect.call_args.kwargs
        assert kwargs["workers"] == 10
        assert kwargs["resume"] is False


class TestProjectPing:
    @patch("wparc.cmds.extractor.ping")
    def test_ping_returns_endpoint_dict(self, mock_ping):
        mock_ping.return_value = {
            "url": "https://example.com/wp-json/",
            "routes_count": 42,
        }
        p = Project()
        result = p.ping("example.com", https=True, timeout=10)
        mock_ping.assert_called_once_with(
            "example.com",
            force_https=True,
            verify_ssl=True,
            timeout=10,
            auth=(None, None),
            proxy=None,
            rate_limit_delay=0.0,
        )
        assert result["routes_count"] == 42

    @patch("wparc.cmds.extractor.ping")
    def test_ping_disable_https(self, mock_ping):
        p = Project()
        p.ping("example.com", https=False)
        kwargs = mock_ping.call_args.kwargs
        assert kwargs["force_https"] is False


class TestProjectAnalyze:
    @patch("wparc.cmds.extractor.generate_routes_yaml")
    @patch("wparc.cmds.extractor.test_unknown_routes")
    @patch("wparc.cmds.extractor.analyze_routes")
    def test_analyze_no_unknown_routes(self, mock_analyze, mock_test, mock_gen):
        """If there are no unknown routes, we don't probe or emit YAML."""
        mock_analyze.return_value = {
            "url": "https://example.com/wp-json/",
            "total_routes": 5,
            "known_routes": {},
            "unknown_routes": [],
            "statistics": {},
            "wpjson": {},
        }
        p = Project()
        result = p.analyze("example.com", https=True)
        mock_test.assert_not_called()
        mock_gen.assert_not_called()
        assert "yaml_update" not in result

    @patch("wparc.cmds.extractor.generate_routes_yaml")
    @patch("wparc.cmds.extractor.test_unknown_routes")
    @patch("wparc.cmds.extractor.analyze_routes")
    def test_analyze_with_unknown_routes(self, mock_analyze, mock_test, mock_gen):
        """Unknown routes trigger probing and YAML generation."""
        mock_analyze.return_value = {
            "url": "https://example.com/wp-json/",
            "total_routes": 5,
            "known_routes": {},
            "unknown_routes": ["/custom/v1/items"],
            "statistics": {},
            "wpjson": {"routes": {"/custom/v1/items": {}}},
        }
        mock_test.return_value = {"public-list": ["/custom/v1/items"]}
        mock_gen.return_value = "public-list:\n- /custom/v1/items"

        p = Project()
        result = p.analyze("example.com", https=True)

        mock_test.assert_called_once()
        mock_gen.assert_called_once_with({"public-list": ["/custom/v1/items"]})
        assert result["yaml_update"] == "public-list:\n- /custom/v1/items"
        assert result["categorized_routes"] == {"public-list": ["/custom/v1/items"]}

    @patch("wparc.cmds.extractor.analyze_routes")
    def test_analyze_rejects_invalid_domain(self, mock_analyze):
        p = Project()
        with pytest.raises(DomainValidationError):
            p.analyze("invalid..domain.com", https=True)
        mock_analyze.assert_not_called()

    @patch("wparc.cmds.extractor.test_unknown_routes")
    @patch("wparc.cmds.extractor.generate_routes_yaml")
    @patch("wparc.cmds.extractor.analyze_routes")
    def test_analyze_no_https_uses_http(self, mock_analyze, mock_gen, mock_test):
        mock_analyze.return_value = {
            "url": "http://example.com/wp-json/",
            "total_routes": 0,
            "known_routes": {},
            "unknown_routes": ["/x"],
            "statistics": {},
            "wpjson": {"routes": {"/x": {}}},
        }
        mock_test.return_value = {}
        mock_gen.return_value = ""
        p = Project()
        p.analyze("example.com", https=False)
        # base_url passed to test_unknown_routes must use http://
        args = mock_test.call_args.args
        assert args[2] == "http://example.com/wp-json"
