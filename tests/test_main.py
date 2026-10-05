# -*- coding: utf-8 -*-
"""
Tests for the ``python -m wparc`` entry point and logging config.

Covers C8 (logging.basicConfig no longer runs on import) and C14
(``WPARC_DEBUG`` env var enables tracebacks).
"""
import logging
from unittest.mock import patch

import pytest


class TestLoggingNotConfiguredOnImport:
    """Importing core/wpapi must not call ``logging.basicConfig``.

    The library should be importable from a context where the host
    application owns the root logger.
    """

    def test_import_core_does_not_configure_root(self):
        # Reset any previous basicConfig to detect side effects.
        root = logging.getLogger()
        previous_handlers = list(root.handlers)
        previous_level = root.level
        root.handlers.clear()
        try:
            import importlib

            import wparc.core

            importlib.reload(wparc.core)
            # After re-import, root should have no handlers attached by us.
            assert logging.getLogger().handlers == []
            # And wparc.core should expose its own module logger.
            assert isinstance(wparc.core.logger, logging.Logger)
        finally:
            # Restore host handlers/level.
            for h in previous_handlers:
                root.addHandler(h)
            root.setLevel(previous_level)


class TestMainEntryPoint:
    def test_keyboard_interrupt_exit_code(self, monkeypatch, capsys):
        monkeypatch.setenv("WPARC_DEBUG", "")
        from wparc.__main__ import main

        # Simulate Typer raising KeyboardInterrupt on first user interaction.
        with patch("wparc.__main__.app") as mock_app:
            mock_app.side_effect = KeyboardInterrupt()
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 130

    def test_unhandled_exception_debug_off(self, monkeypatch, capsys):
        monkeypatch.setenv("WPARC_DEBUG", "")
        from wparc.__main__ import main

        with patch("wparc.__main__.app") as mock_app:
            mock_app.side_effect = RuntimeError("kaboom")
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "kaboom" in captured.err
        assert "Traceback" not in captured.err

    def test_unhandled_exception_debug_on(self, monkeypatch, capsys):
        monkeypatch.setenv("WPARC_DEBUG", "1")
        # Re-import to pick up the new env var (we read it in main()).
        from wparc.__main__ import main

        with patch("wparc.__main__.app") as mock_app:
            mock_app.side_effect = RuntimeError("kaboom")
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "kaboom" in captured.err
        # Traceback from the underlying RuntimeError must appear in stderr.
        assert "Traceback" in captured.err
