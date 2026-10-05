# -*- coding: utf-8 -*-
"""
Tests for ``scripts/build_api_doc.py``.

The script is the entry point we hand to contributors to keep the API
reference up-to-date; this test guards its output shape so that a
broken signature-renderer can be caught early.
"""
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "build_api_doc.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("build_api_doc", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_runs_without_error():
    """The script must run end-to-end and write Markdown."""
    mod = _load_script()
    import io

    buf = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = buf
    try:
        mod.main()
    finally:
        sys.stdout = real_stdout
    text = buf.getvalue()
    assert text.startswith("# wparc API reference")
    assert "## `wparc.exceptions`" in text
    assert "| Name | Signature | Description |" in text


def test_signature_helper_handles_known_callables():
    mod = _load_script()
    # Plain function: all defaults stringified.
    sig = mod._signature(lambda a, b=2, c="x": None)
    assert sig == "(a, b=2, c='x')"


def test_signature_helper_collapses_typer_defaults():
    """Typer ``OptionInfo`` / ``ArgumentInfo`` must be hidden."""
    mod = _load_script()

    # A class whose name ends with ``OptionInfo`` / ``ArgumentInfo`` —
    # exactly the heuristic the script uses.
    class OptionInfo:
        pass

    def fn(x=OptionInfo()):
        return x

    sig = mod._signature(fn)
    assert sig.startswith("(x=<optioninfo>)")


def test_signature_helper_returns_empty_on_builtin():
    """Some builtins (e.g. ``open``) have no inspectable signature."""
    mod = _load_script()
    # A regular function with no signature raises TypeError internally.
    sig = mod._signature(lambda: None)
    assert sig == "()"


def test_walks_wparc_modules():
    """``render_module`` should expose at least one public function."""
    mod = _load_script()
    import wparc.exceptions

    text = mod.render_module(wparc.exceptions)
    assert "`wparc.exceptions`" in text
    assert "`APIError`" in text
    assert "Status code" in text or "url" in text


def test_walk_module_skips_reexports():
    """Names whose ``__module__`` differs from the host module must be skipped."""
    mod = _load_script()
    import wparc.cmds.extractor as ext

    pairs = list(mod._walk_module(ext))
    names = {name for name, _ in pairs}
    # ``Project`` is defined in extractor.py — should appear.
    assert "Project" in names
    # ``HttpOptions`` is also local — should appear.
    assert "HttpOptions" in names


def test_is_public():
    mod = _load_script()
    assert mod._is_public("foo") is True
    assert mod._is_public("_private") is False
    assert mod._is_public("__dunder__") is False
