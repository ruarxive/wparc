# -*- coding: utf-8 -*-
"""
Tests for package-level metadata.

Catches C1 (__version__ drift) and L1 (__licence__ typo).
"""
import wparc


class TestPackageMetadata:
    def test_version_is_present(self):
        assert hasattr(wparc, "__version__")
        assert isinstance(wparc.__version__, str)
        assert wparc.__version__  # non-empty

    def test_version_matches_pyproject(self, monkeypatch):
        """__version__ must match the version declared in pyproject.toml.

        Catches the 1.0.7 / 1.0.8 drift bug.
        """
        import re
        from pathlib import Path

        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        assert match is not None, "version not found in pyproject.toml"
        assert wparc.__version__ == match.group(1)

    def test_license_attribute_uses_correct_name(self):
        """__license__ (PEP 8), not the legacy __licence__."""
        assert hasattr(wparc, "__license__")
        assert wparc.__license__ == "MIT"

    def test_author_present(self):
        assert hasattr(wparc, "__author__")
        assert wparc.__author__
