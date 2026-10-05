#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WordPress API crawler CLI module.

This module provides the command-line interface using Typer.

.. note::
    Logging is configured in :func:`wparc.__main__.main` to avoid side
    effects on import. Importing this module does not configure the root
    logger.
"""
import functools
import logging
from typing import Callable, TypeVar

import typer

from .cmds.extractor import HttpOptions, Project
from .exceptions import DomainValidationError

app = typer.Typer(
    name="wparc",
    help="WordPress API crawler and backup tool",
    add_completion=False,
)

# Module-level logger; root configuration is deferred to __main__.main().
logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., None])


def _enable_verbose() -> None:
    """Enable verbose logging for wparc loggers only."""
    logging.getLogger("wparc").setLevel(logging.DEBUG)
    logging.getLogger().setLevel(logging.INFO)


def handle_cli_errors(func: F) -> F:
    """Decorator that converts uncaught exceptions into a CLI-friendly exit.

    All Typer commands share the same failure shape::

        - :class:`wparc.exceptions.DomainValidationError` ⇒ exit 1, message
          prefixed with ``"Error: Invalid domain: "``.
        - any other ``Exception`` ⇒ exit 1, message prefixed with ``"Error: "``.
        - ``typer.Exit`` is re-raised so Typer can manage its own exit codes
          (used for ``--help`` and friends).
        - ``KeyboardInterrupt`` and ``SystemExit`` are NOT caught here; they
          are handled by ``wparc.__main__.main``.

    Using a decorator keeps each command body focused on its happy path,
    removing the four near-identical ``except`` blocks that previously lived
    in every command definition.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            raise
        except DomainValidationError as e:
            typer.echo(f"Error: Invalid domain: {e}", err=True)
            raise typer.Exit(1)
        except Exception as e:
            logger.debug("Unhandled exception in CLI command", exc_info=True)
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    return wrapper  # type: ignore[return-value]


def _common_options(f: F) -> F:
    """Decorator: adds the HTTP options shared by ``ping``/``dump``/``analyze``.

    Centralising them avoids four near-identical option blocks.
    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    wrapper.__defaults__ = getattr(f, "__defaults__", ())
    return wrapper  # type: ignore[return-value]


@app.command()
@handle_cli_errors
def ping(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
    https: bool = typer.Option(
        True,
        "--https/--no-https",
        help="Use HTTPS (default: True, use --no-https to disable)",
    ),
    no_verify_ssl: bool = typer.Option(
        False,
        "--no-verify-ssl",
        help="Disable SSL certificate verification (not recommended)",
    ),
    timeout: int = typer.Option(360, "--timeout", help="Request timeout in seconds (default: 360)"),
    user: str = typer.Option(None, "--user", help="HTTP Basic Auth username"),
    password: str = typer.Option(None, "--password", help="HTTP Basic Auth password"),
    proxy: str = typer.Option(None, "--proxy", help="HTTP proxy URL (e.g. http://127.0.0.1:8080)"),
    rate_limit: float = typer.Option(
        0.0,
        "--rate-limit",
        help="Seconds to sleep between requests (0 disables rate limiting)",
    ),
) -> None:
    """Ping WordPress API endpoint to verify it's accessible."""
    if verbose:
        _enable_verbose()

    http = HttpOptions(username=user, password=password, proxy=proxy, rate_limit_delay=rate_limit)
    project = Project(verify_ssl=not no_verify_ssl, http_options=http)
    result = project.ping(domain, https, timeout=timeout)
    typer.echo(f"\n✓ Endpoint {result.get('url', '')} is OK")
    typer.echo(f"✓ Total routes: {result.get('routes_count', 0)}")


@app.command()
@handle_cli_errors
def dump(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
    all_routes: bool = typer.Option(True, "--all", "-a", help="Include unknown API routes"),
    https: bool = typer.Option(
        True,
        "--https/--no-https",
        help="Use HTTPS (default: True, use --no-https to disable)",
    ),
    no_verify_ssl: bool = typer.Option(
        False,
        "--no-verify-ssl",
        help="Disable SSL certificate verification (not recommended)",
    ),
    timeout: int = typer.Option(360, "--timeout", help="Request timeout in seconds (default: 360)"),
    page_size: int = typer.Option(
        100, "--page-size", help="Number of items per page (default: 100)"
    ),
    retry_count: int = typer.Option(
        5, "--retry-count", help="Number of retry attempts (default: 5)"
    ),
    user: str = typer.Option(None, "--user", help="HTTP Basic Auth username"),
    password: str = typer.Option(None, "--password", help="HTTP Basic Auth password"),
    proxy: str = typer.Option(None, "--proxy", help="HTTP proxy URL (e.g. http://127.0.0.1:8080)"),
    rate_limit: float = typer.Option(
        0.0,
        "--rate-limit",
        help="Seconds to sleep between requests (0 disables rate limiting)",
    ),
    index_db: bool = typer.Option(
        False,
        "--index",
        help="After dumping, build a SQLite index under <domain>/index.sqlite3",
    ),
    workers: int = typer.Option(
        1,
        "--workers",
        "-w",
        help="Number of routes to fetch in parallel (1=serial, default)",
    ),
) -> None:
    """Dump WordPress data from API."""
    if verbose:
        _enable_verbose()

    http = HttpOptions(username=user, password=password, proxy=proxy, rate_limit_delay=rate_limit)
    project = Project(verify_ssl=not no_verify_ssl, http_options=http)
    stats = project.dump(
        domain,
        all_routes,
        https,
        timeout=timeout,
        page_size=page_size,
        retry_count=retry_count,
        workers=workers,
    )
    typer.echo(
        f"\n✓ Data collection complete: {stats['routes_processed']} routes processed, "
        f"{stats['routes_skipped']} skipped"
    )

    if index_db:
        from .wpapi.index.sqlite_index import build_index

        result = build_index(domain)
        typer.echo(
            f"\n✓ SQLite index built: {result['records']} records "
            f"from {result['files']} files → {result['db_path']}"
        )


@app.command()
@handle_cli_errors
def getfiles(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
    no_verify_ssl: bool = typer.Option(
        False,
        "--no-verify-ssl",
        help="Disable SSL certificate verification (not recommended)",
    ),
    workers: int = typer.Option(
        5, "--workers", "-w", help="Number of concurrent download workers (default: 5)"
    ),
    no_resume: bool = typer.Option(
        False, "--no-resume", help="Don't resume from checkpoint; re-download everything"
    ),
) -> None:
    """Download all media files listed in wp_v2_media.jsonl."""
    if verbose:
        _enable_verbose()

    project = Project(verify_ssl=not no_verify_ssl)
    stats = project.getfiles(domain, workers=workers, resume=not no_resume)
    typer.echo(
        f"\n✓ File download complete: {stats['downloaded']} downloaded, "
        f"{stats['failed']} failed, {stats['skipped']} skipped"
    )


@app.command()
@handle_cli_errors
def index(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
) -> None:
    """Build a SQLite index from a previous dump."""
    if verbose:
        _enable_verbose()

    from .wpapi.index.sqlite_index import build_index

    try:
        result = build_index(domain)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(
        f"✓ SQLite index built: {result['records']} records "
        f"from {result['files']} files → {result['db_path']}"
    )


@app.command()
@handle_cli_errors
def warc(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
    output: str = typer.Option(
        "dump.warc.gz",
        "--output",
        "-o",
        help="Output filename (.warc or .warc.gz)",
    ),
    no_compress: bool = typer.Option(
        False, "--no-compress", help="Produce an uncompressed .warc file"
    ),
) -> None:
    """Export a previous dump to a WARC archive."""
    if verbose:
        _enable_verbose()

    from .wpapi.warc.writer import export_warc

    try:
        result = export_warc(domain, output_filename=output, compress=not no_compress)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"✓ WARC archive written: {result['records']} records → {result['output_path']}")


@app.command()
@handle_cli_errors
def analyze(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
    https: bool = typer.Option(
        True,
        "--https/--no-https",
        help="Use HTTPS (default: True, use --no-https to disable)",
    ),
    no_verify_ssl: bool = typer.Option(
        False,
        "--no-verify-ssl",
        help="Disable SSL certificate verification (not recommended)",
    ),
    timeout: int = typer.Option(360, "--timeout", help="Request timeout in seconds (default: 360)"),
    user: str = typer.Option(None, "--user", help="HTTP Basic Auth username"),
    password: str = typer.Option(None, "--password", help="HTTP Basic Auth password"),
    proxy: str = typer.Option(None, "--proxy", help="HTTP proxy URL (e.g. http://127.0.0.1:8080)"),
    rate_limit: float = typer.Option(
        0.0,
        "--rate-limit",
        help="Seconds to sleep between requests (0 disables rate limiting)",
    ),
) -> None:
    """Analyze WordPress API routes and compare against known routes."""
    if verbose:
        _enable_verbose()

    http = HttpOptions(username=user, password=password, proxy=proxy, rate_limit_delay=rate_limit)
    project = Project(verify_ssl=not no_verify_ssl, http_options=http)
    result = project.analyze(domain, https, timeout=timeout)

    typer.echo(f"\n✓ Analysis complete for {result.get('url', '')}")
    typer.echo(f"✓ Total routes: {result.get('total_routes', 0)}")

    stats = result.get("statistics", {})
    typer.echo("\nRoute Statistics:")
    typer.echo(f"  Protected: {stats.get('protected', 0)}")
    typer.echo(f"  Public-list: {stats.get('public-list', 0)}")
    typer.echo(f"  Public-dict: {stats.get('public-dict', 0)}")
    typer.echo(f"  Useless: {stats.get('useless', 0)}")
    typer.echo(f"  Unknown: {stats.get('unknown', 0)}")

    unknown_routes = result.get("unknown_routes", [])
    if unknown_routes:
        typer.echo(f"\n⚠ Found {len(unknown_routes)} unknown routes")
        if verbose:
            for route in unknown_routes[:10]:
                typer.echo(f"  - {route}")
            if len(unknown_routes) > 10:
                typer.echo(f"  ... and {len(unknown_routes) - 10} more")

        categorized_routes = result.get("categorized_routes", {})
        yaml_update = result.get("yaml_update", "")

        if categorized_routes and yaml_update:
            typer.echo("\n✓ Testing complete for unknown routes")
            typer.echo("\nCategorized routes:")
            for category, routes in categorized_routes.items():
                if routes:
                    typer.echo(f"  {category}: {len(routes)}")

            typer.echo("\n" + "=" * 70)
            typer.echo("YAML Update for known_routes.yml:")
            typer.echo("=" * 70)
            typer.echo(yaml_update)
            typer.echo("=" * 70)
            typer.echo("\nYou can add the above YAML to known_routes.yml")


__all__ = ["app", "handle_cli_errors"]
