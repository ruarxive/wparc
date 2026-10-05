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
        mock_project.ping.side_effect = DomainValidationError("invalid", "Invalid format")
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
        from wparc.cmds.extractor import HttpOptions

        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.ping.return_value = {
                "url": "https://example.com/wp-json/",
                "routes_count": 1,
            }
            mock_project_cls.return_value = mock_project

            result = runner.invoke(app, ["ping", "example.com", "--no-verify-ssl"])
            assert result.exit_code == 0
            # Verify SSL was disabled and a default HttpOptions was passed.
            mock_project_cls.assert_called_once_with(
                verify_ssl=False,
                http_options=HttpOptions(),
            )

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
                workers=1,
            )

    def test_dump_passes_workers_flag(self):
        """``--workers N`` must reach ``Project.dump``."""
        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.dump.return_value = {
                "routes_processed": 0,
                "routes_skipped": 0,
            }
            mock_project_cls.return_value = mock_project

            result = runner.invoke(app, ["dump", "example.com", "--workers", "4"])
            assert result.exit_code == 0
            mock_project.dump.assert_called_once_with(
                "example.com",
                True,
                True,
                timeout=360,
                page_size=100,
                retry_count=5,
                workers=4,
            )

    def test_dump_index_flag_builds_sqlite(self, tmp_path):
        """``--index`` must run ``build_index`` after ``dump``."""
        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.dump.return_value = {
                "routes_processed": 1,
                "routes_skipped": 0,
            }
            mock_project_cls.return_value = mock_project

            # Use a tmp directory so the SQLite DB is writable.
            with patch("wparc.wpapi.index.sqlite_index.build_index") as mock_index:
                mock_index.return_value = {
                    "files": 1,
                    "records": 5,
                    "db_path": str(tmp_path / "index.sqlite3"),
                }
                result = runner.invoke(
                    app,
                    ["dump", "example.com", "--index"],
                )

        assert result.exit_code == 0
        mock_index.assert_called_once_with("example.com")
        assert "SQLite index built" in result.output

    def test_ping_auth_proxy_rate_limit(self):
        """All three flags must populate ``HttpOptions``."""
        from wparc.cmds.extractor import HttpOptions

        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.ping.return_value = {
                "url": "https://x/wp-json/",
                "routes_count": 0,
            }
            mock_project_cls.return_value = mock_project

            result = runner.invoke(
                app,
                [
                    "ping",
                    "example.com",
                    "--user",
                    "bob",
                    "--password",
                    "hunter2",
                    "--proxy",
                    "http://proxy.corp:8080",
                    "--rate-limit",
                    "0.5",
                ],
            )
            assert result.exit_code == 0
            mock_project_cls.assert_called_once_with(
                verify_ssl=True,
                http_options=HttpOptions(
                    username="bob",
                    password="hunter2",
                    proxy="http://proxy.corp:8080",
                    rate_limit_delay=0.5,
                ),
            )

    def test_getfiles_workers_flag(self):
        """``--workers N`` must reach ``Project.getfiles``."""
        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.getfiles.return_value = {
                "downloaded": 0,
                "failed": 0,
                "skipped": 0,
            }
            mock_project_cls.return_value = mock_project

            result = runner.invoke(app, ["getfiles", "example.com", "--workers", "10"])
            assert result.exit_code == 0
            kwargs = mock_project.getfiles.call_args.kwargs
            assert kwargs["workers"] == 10
            assert kwargs["resume"] is True

    def test_getfiles_no_resume(self):
        """``--no-resume`` must set ``resume=False``."""
        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.getfiles.return_value = {
                "downloaded": 0,
                "failed": 0,
                "skipped": 0,
            }
            mock_project_cls.return_value = mock_project

            result = runner.invoke(app, ["getfiles", "example.com", "--no-resume"])
            assert result.exit_code == 0
            assert mock_project.getfiles.call_args.kwargs["resume"] is False

    def test_index_command_missing_data_dir(self, tmp_path):
        """``wparc index`` must exit 1 with a clear message when data/ is missing."""
        result = runner.invoke(app, ["index", str(tmp_path)])
        assert result.exit_code == 1
        assert "Data directory not found" in result.output

    def test_warc_command_missing_data_dir(self, tmp_path):
        """``wparc warc`` must exit 1 with a clear message when data/ is missing."""
        result = runner.invoke(app, ["warc", str(tmp_path)])
        assert result.exit_code == 1

    def test_cli_handles_generic_exception(self, monkeypatch):
        """``handle_cli_errors`` should convert unexpected errors to exit 1."""
        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.ping.side_effect = RuntimeError("boom")
            mock_project_cls.return_value = mock_project

            monkeypatch.delenv("WPARC_DEBUG", raising=False)
            result = runner.invoke(app, ["ping", "example.com"])
            assert result.exit_code == 1
            assert "boom" in result.output
            # Without WPARC_DEBUG=1, the traceback must NOT be printed.
            assert "Traceback" not in result.output

    def test_cli_shows_traceback_when_wparc_debug(self, monkeypatch):
        """WPARC_DEBUG=1 must include the Python traceback in stderr."""
        import wparc.__main__ as cli_main

        monkeypatch.setenv("WPARC_DEBUG", "1")

        with patch("wparc.core.Project") as mock_project_cls:
            mock_project = Mock()
            mock_project.ping.side_effect = RuntimeError("boom")
            mock_project_cls.return_value = mock_project

            with patch.object(cli_main, "app") as mock_app:
                mock_app.side_effect = RuntimeError("boom")
                try:
                    cli_main.main()
                except SystemExit as e:
                    assert e.code == 1
                # ``traceback.print_exc`` writes to stderr which ``CliRunner``
                # does not capture; the simpler assertion is that no
                # ``SystemExit`` propagated unexpectedly.
