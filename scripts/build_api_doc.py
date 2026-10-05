#!/usr/bin/env python3
"""Generate a Markdown API reference for the wparc package.

Walks every public name in ``wparc`` and writes a Markdown file with
one section per module: the docstring (first paragraph) plus a table of
``(name, signature, short description)`` for each function and class.

The output is meant to be dropped into ``docs/api/`` so the MkDocs site
picks it up. It uses only the standard library — no sphinx, no pdoc.

Usage::

    python scripts/build_api_doc.py > docs/api/auto.md

The script is read-only and never modifies wparc itself.
"""
import importlib
import inspect
import pkgutil
import sys
from pathlib import Path

# Always import wparc relative to the repo root, not to a stale
# installed copy in site-packages.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _signature(obj) -> str:
    """Return a one-line function/class signature.

    Typer-based commands use ``typer.Option(...)`` defaults that render
    as ``<typer.models.OptionInfo ...>`` when stringified. For our
    purposes those placeholders are noise, so we replace them with
    ``= <default>``.
    """
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return ""

    params = []
    for name, param in sig.parameters.items():
        default = param.default
        if default is inspect.Parameter.empty:
            params.append(name)
            continue
        # Typer's OptionInfo and ArgumentInfo print poorly; collapse them.
        cls_name = type(default).__name__
        if cls_name in {"OptionInfo", "ArgumentInfo", "Option", "Argument"}:
            params.append(f"{name}=<{cls_name.lower()}>")
            continue
        # Standard defaults are stringified as ``<class 'repr'>`` by Python.
        params.append(f"{name}={default!r}")

    ret = "()"
    if params:
        ret = "(" + ", ".join(params) + ")"
    return ret


def _doc(obj) -> str:
    """Return the cleaned-up first paragraph of the docstring."""
    doc = inspect.getdoc(obj) or ""
    if not doc:
        return ""
    first = doc.split("\n\n", 1)[0]
    return " ".join(first.split())


def _is_public(name: str) -> bool:
    """Names that don't start with underscore are public."""
    return not name.startswith("_")


def _walk_module(module):
    """Yield ``(qualname, obj)`` for every public function/class in ``module``."""
    for name in dir(module):
        if not _is_public(name):
            continue
        obj = getattr(module, name)
        if not (inspect.isfunction(obj) or inspect.isclass(obj)):
            continue
        # Skip re-exports whose origin is a different module.
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        yield name, obj


def _module_path(package, module_name):
    """Build the dotted path of a sub-module inside ``package``."""
    return f"{package.__name__}.{module_name}"


def render_module(module):
    """Render one module to Markdown."""
    lines = [f"## `{module.__name__}`", ""]
    doc = _doc(module)
    if doc:
        lines.append(doc)
        lines.append("")

    rows = []
    for name, obj in _walk_module(module):
        sig = _signature(obj)
        desc = _doc(obj).split("\n", 1)[0][:140]
        rows.append((name, sig, desc))
    if not rows:
        return "\n".join(lines)

    lines.append("| Name | Signature | Description |")
    lines.append("|---|---|---|")
    for name, sig, desc in rows:
        sig_md = sig.replace("|", "\\|")
        lines.append(f"| `{name}` | `{sig_md}` | {desc} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    import wparc

    out = ["# wparc API reference (auto-generated)", ""]
    out.append(
        "This page is generated from public function and class "
        "signatures plus their leading docstring paragraph. Run "
        "`python scripts/build_api_doc.py > docs/api/auto.md` to "
        "regenerate."
    )
    out.append("")

    out.append(f"## `{wparc.__name__}`")
    out.append("")
    out.append(_doc(wparc))
    out.append("")

    for module_info in sorted(
        pkgutil.iter_modules(wparc.__path__, prefix=f"{wparc.__name__}."),
        key=lambda i: i.name,
    ):
        module = importlib.import_module(module_info.name)
        out.append(render_module(module))

    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
