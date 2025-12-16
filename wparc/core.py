#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WordPress API crawler CLI module.

This module provides the command-line interface using Typer.
"""
import logging

import typer

from .cmds.extractor import Project
from .exceptions import DomainValidationError

app = typer.Typer(
    name="wparc",
    help="WordPress API crawler and backup tool",
    add_completion=False,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def _enable_verbose() -> None:
    """Enable verbose logging."""
    logging.getLogger().setLevel(logging.DEBUG)


@app.command()
def ping(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
    https: bool = typer.Option(
        True, "--https/--no-https", help="Use HTTPS (default: True, use --no-https to disable)"
    ),
    no_verify_ssl: bool = typer.Option(
        False,
        "--no-verify-ssl",
        help="Disable SSL certificate verification (not recommended)",
    ),
    timeout: int = typer.Option(
        360, "--timeout", help="Request timeout in seconds (default: 360)"
    ),
) -> None:
    """Ping WordPress API endpoint to verify it's accessible."""
    if verbose:
        _enable_verbose()

    try:
        project = Project(verify_ssl=not no_verify_ssl)
        result = project.ping(domain, https, timeout=timeout)
        typer.echo(f"\n✓ Endpoint {result.get('url', '')} is OK")
        typer.echo(f"✓ Total routes: {result.get('routes_count', 0)}")
    except DomainValidationError as e:
        typer.echo(f"Error: Invalid domain: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def dump(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
    all_routes: bool = typer.Option(
        True, "--all", "-a", help="Include unknown API routes"
    ),
    https: bool = typer.Option(
        True, "--https/--no-https", help="Use HTTPS (default: True, use --no-https to disable)"
    ),
    no_verify_ssl: bool = typer.Option(
        False,
        "--no-verify-ssl",
        help="Disable SSL certificate verification (not recommended)",
    ),
    timeout: int = typer.Option(
        360, "--timeout", help="Request timeout in seconds (default: 360)"
    ),
    page_size: int = typer.Option(
        100, "--page-size", help="Number of items per page (default: 100)"
    ),
    retry_count: int = typer.Option(
        5, "--retry-count", help="Number of retry attempts (default: 5)"
    ),
) -> None:
    """Dump WordPress data from API."""
    if verbose:
        _enable_verbose()

    try:
        project = Project(verify_ssl=not no_verify_ssl)
        stats = project.dump(
            domain,
            all_routes,
            https,
            timeout=timeout,
            page_size=page_size,
            retry_count=retry_count,
        )
        typer.echo(
            f"\n✓ Data collection complete: {stats['routes_processed']} routes processed, "
            f"{stats['routes_skipped']} skipped"
        )
    except DomainValidationError as e:
        typer.echo(f"Error: Invalid domain: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
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
) -> None:
    """Download all media files listed in wp_v2_media.jsonl."""
    if verbose:
        _enable_verbose()

    try:
        project = Project(verify_ssl=not no_verify_ssl)
        stats = project.getfiles(domain)
        typer.echo(
            f"\n✓ File download complete: {stats['downloaded']} downloaded, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )
    except DomainValidationError as e:
        typer.echo(f"Error: Invalid domain: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def analyze(
    domain: str = typer.Argument(..., help="Domain name (e.g., example.com)"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output. Print additional info"
    ),
    https: bool = typer.Option(
        True, "--https/--no-https", help="Use HTTPS (default: True, use --no-https to disable)"
    ),
    no_verify_ssl: bool = typer.Option(
        False,
        "--no-verify-ssl",
        help="Disable SSL certificate verification (not recommended)",
    ),
    timeout: int = typer.Option(
        360, "--timeout", help="Request timeout in seconds (default: 360)"
    ),
) -> None:
    """Analyze WordPress API routes and compare against known routes."""
    if verbose:
        _enable_verbose()

    try:
        project = Project(verify_ssl=not no_verify_ssl)
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
                for route in unknown_routes[:10]:  # Show first 10
                    typer.echo(f"  - {route}")
                if len(unknown_routes) > 10:
                    typer.echo(f"  ... and {len(unknown_routes) - 10} more")
            
            # Test unknown routes and generate YAML update
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
    except DomainValidationError as e:
        typer.echo(f"Error: Invalid domain: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    app()


# For backward compatibility
cli = app
