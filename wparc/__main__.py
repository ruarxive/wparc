#!/usr/bin/env python
"""The main entry point. Invoke as `wparc` or `python -m wparc`.

This module is the CLI bootstrap. It configures the root logger exactly
once, before Typer takes over. Importing :mod:`wparc.core` or
:mod:`wparc.wpapi` does NOT configure logging, so the library can be
embedded inside other applications without hijacking their loggers.
"""
import logging
import os
import sys
import traceback

import typer

from .core import app


def _configure_logging() -> None:
    """Configure root logger for wparc CLI usage."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


def main() -> None:
    """Main entry point."""
    _configure_logging()
    # Honour WPARC_DEBUG=1 to enable verbose tracebacks on unhandled errors.
    debug = os.environ.get("WPARC_DEBUG", "").lower() in ("1", "true", "yes")
    try:
        app()
    except KeyboardInterrupt:
        typer.echo("\nCtrl-C pressed. Aborting", err=True)
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        if debug:
            traceback.print_exc()
        typer.echo(f"Unexpected error: {e}", err=True)
        if debug:
            typer.echo(
                "\nSet WPARC_DEBUG=0 (or unset) to suppress tracebacks.",
                err=True,
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
