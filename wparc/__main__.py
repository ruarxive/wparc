#!/usr/bin/env python
"""The main entry point. Invoke as `wparc` or `python -m wparc`."""
import sys

import typer

from .core import app


def main() -> None:
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        typer.echo("\nCtrl-C pressed. Aborting", err=True)
        sys.exit(130)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
