# -*- coding: utf-8 -*-
"""
Tests for CLI commands using Typer's test runner.
"""
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from wparc.core import app

runner = CliRunner()


class TestCliRunner:
    """Tests for CLI commands via Typer test runner."""

    @patch("wparc.core.Project")
    def test_ping_command(self, mock_project_cls):
        """Test ping command with successful response."""
        mock_project = Mock()
        mock_project.ping.return_value = {
            "url": "https://example.com/wp-json/",
            "routes_count": 42,
        }
        mock_project_cls.return_value = mock_project

        result = runner.invoke(app, ["ping", "example.com"])
        assert result.exit_code == 0
        assert "OK" in result.output
        assert "42" in result.output

    @patch("wparc.core.Project")
    def test_ping_domain_error(self, mock_project_cls):
        """Test ping command with invalid domain."""
        from wparc.exceptions import DomainValidationError

        mock_project = Mock()
        mock_project.ping.side_effect = DomainValidationError(
            "invalid", "Invalid format"
        )
        mock_project_cls.return_value = mock_project

        result = runner.invoke(app, ["ping", "invalid..domain"])
        assert result.exit_code == 1
        assert "Invalid domain" in result.output

    @patch("wparc.core.Project")
    def test_dump_command(self, mock_project_cls):
        """Test dump command with successful response."""
        mock_project = Mock()
        mock_project.dump.return_value = {
            "routes_processed": 45,
            "routes_skipped": 2,
        }
        mock_project_cls.return_value = mock_project

        result = runner.invoke(app, ["dump", "example.com"])
        assert result.exit_code == 0
        assert "complete" in result.output
        assert "45" in result.output

    @patch("wparc.core.Project")
    def test_getfiles_command(self, mock_project_cls):
        """Test getfiles command with successful response."""
        mock_project = Mock()
        mock_project.getfiles.return_value = {
            "downloaded": 100,
            "failed": 3,
            "skipped": 5,
        }
        mock_project_cls.return_value = mock_project

        result = runner.invoke(app, ["getfiles", "example.com"])
        assert result.exit_code == 0
        assert "complete" in result.output
        assert "100" in result.output

    @patch("wparc.core.Project")
    def test_analyze_command(self, mock_project_cls):
        """Test analyze command with successful response."""
        mock_project = Mock()
        mock_project.analyze.return_value = {
            "url": "https://example.com/wp-json/",
            "total_routes": 45,
            "statistics": {
                "protected": 10,
                "public-list": 20,
                "public-dict": 5,
                "useless": 5,
                "unknown": 5,
            },
            "unknown_routes": [],
        }
        mock_project_cls.return_value = mock_project

        result = runner.invoke(app, ["analyze", "example.com"])
        assert result.exit_code == 0
        assert "Analysis complete" in result.output
        assert "45" in result.output

    def test_ping_no_verify_ssl_flag(self):
        """Test that --no-verify-ssl flag is accepted."""
        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.ping.return_value = {
                "url": "https://example.com/wp-json/",
                "routes_count": 1,
            }
            mock_project_cls.return_value = mock_project

            result = runner.invoke(
                app, ["ping", "example.com", "--no-verify-ssl"]
            )
            assert result.exit_code == 0
            # Verify SSL was disabled
            mock_project_cls.assert_called_once_with(verify_ssl=False)

    def test_dump_with_options(self):
        """Test dump command with various options."""
        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.dump.return_value = {
                "routes_processed": 10,
                "routes_skipped": 0,
            }
            mock_project_cls.return_value = mock_project

            result = runner.invoke(
                app,
                [
                    "dump",
                    "example.com",
                    "--timeout",
                    "600",
                    "--page-size",
                    "50",
                    "--retry-count",
                    "3",
                ],
            )
            assert result.exit_code == 0
            mock_project.dump.assert_called_once_with(
                "example.com",
                True,  # all_routes (default)
                True,  # https (default)
                timeout=600,
                page_size=50,
                retry_count=3,
            )
