from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from . import __version__
from .auth import AuthError
from .config import ConfigError, load_config
from .orchestration.run_checker import run_checker
from .reporting import (
    send_email_notification,
    send_teams_notification,
    write_xlsx_report,
    write_html_report,
    write_json_report,
)
from .utils.logging import configure_logging

app = typer.Typer(
    name="sp-checker",
    help="SharePoint Online tenant-wide folder/file structure validator.",
    no_args_is_help=True,
)

_CONFIG_OPT = Annotated[
    Path,
    typer.Option("--config", "-c", help="Path to checker-config.yaml", exists=True),
]


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"sp-checker {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    pass


@app.command()
def run(
    config_path: _CONFIG_OPT = Path("config/checker-config.yaml"),
    output_dir: Annotated[
        Optional[Path],
        typer.Option("--output-dir", "-o", help="Override output directory"),
    ] = None,
    site_prefix: Annotated[
        Optional[str],
        typer.Option("--site-prefix", help="Override site prefix filter"),
    ] = None,
    log_level: Annotated[
        str,
        typer.Option("--log-level", help="Logging level"),
    ] = "INFO",
    notify: Annotated[
        bool,
        typer.Option("--notify/--no-notify", help="Send notifications after run"),
    ] = True,
) -> None:
    """Run the SharePoint structure checker."""
    configure_logging(log_level)
    logger = logging.getLogger(__name__)

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        typer.echo(f"[CONFIG ERROR] {exc}", err=True)
        raise typer.Exit(2)

    if output_dir:
        config.reporting.output_dir = str(output_dir)
    if site_prefix:
        config.discovery.site_prefixes = [site_prefix]

    try:
        summary = asyncio.run(run_checker(config, config_path=str(config_path)))
    except AuthError as exc:
        typer.echo(f"[AUTH ERROR] {exc}", err=True)
        raise typer.Exit(3)
    except ConfigError as exc:
        typer.echo(f"[CONFIG ERROR] {exc}", err=True)
        raise typer.Exit(2)
    except Exception as exc:
        logger.exception("Unexpected error during run")
        typer.echo(f"[RUNTIME ERROR] {exc}", err=True)
        raise typer.Exit(4)

    out_dir = Path(config.reporting.output_dir)
    formats = config.reporting.formats
    report_path = None

    if "json" in formats:
        write_json_report(summary, out_dir)
    if "xlsx" in formats:
        write_xlsx_report(summary, out_dir)
    if "html" in formats:
        report_path = write_html_report(summary, out_dir)

    if notify:
        rc = config.reporting
        if rc.teams.enabled:
            asyncio.run(
                send_teams_notification(
                    summary,
                    webhook_env=rc.teams.webhook_env,
                    only_failures=rc.only_failures_in_notification,
                )
            )
        if rc.email.enabled:
            send_email_notification(summary, rc.email, report_path=report_path)

    typer.echo(
        f"Run {summary.run_id}: {summary.total_sites} site(s) — "
        f"{summary.pass_count} PASS / {summary.fail_count} FAIL — "
        f"overall {summary.overall_status.value}"
    )

    if summary.fail_count > 0:
        raise typer.Exit(1)


@app.command(name="validate-config")
def validate_config(
    config_path: _CONFIG_OPT = Path("config/checker-config.yaml"),
) -> None:
    """Validate configuration file without running."""
    configure_logging("WARNING")
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        typer.echo(f"[INVALID] {exc}", err=True)
        raise typer.Exit(2)

    typer.echo(
        f"[OK] Config valid — tenant: {config.tenant_id}, "
        f"mode: {config.discovery.mode}, "
        f"leadership_regex: {config.rules.leadership_folder_regex}"
    )


@app.command(name="dry-run")
def dry_run(
    config_path: _CONFIG_OPT = Path("config/checker-config.yaml"),
    log_level: Annotated[str, typer.Option("--log-level")] = "INFO",
) -> None:
    """Discover sites and show what would be checked, without reading content."""
    configure_logging(log_level)

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        typer.echo(f"[CONFIG ERROR] {exc}", err=True)
        raise typer.Exit(2)

    try:
        summary = asyncio.run(
            run_checker(config, config_path=str(config_path), dry_run=True)
        )
    except AuthError as exc:
        typer.echo(f"[AUTH ERROR] {exc}", err=True)
        raise typer.Exit(3)
    except Exception as exc:
        typer.echo(f"[RUNTIME ERROR] {exc}", err=True)
        raise typer.Exit(4)

    typer.echo(f"[dry-run] Would check {summary.total_sites} site(s)")


@app.command(name="auth-login")
def auth_login(
    config_path: _CONFIG_OPT = Path("config/checker-config.yaml"),
) -> None:
    """Authenticate via device code flow (MFA-compatible). Run once to cache credentials."""
    configure_logging("WARNING")
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        typer.echo(f"[CONFIG ERROR] {exc}", err=True)
        raise typer.Exit(2)

    if not config.delegated_auth:
        typer.echo(
            "[ERROR] 'delegated_auth' is not configured in checker-config.yaml. "
            "Add the 'delegated_auth' section to use device code flow.",
            err=True,
        )
        raise typer.Exit(2)

    from .auth import AuthError, TokenProvider
    try:
        TokenProvider(config).login_device_code()
    except AuthError as exc:
        typer.echo(f"[AUTH ERROR] {exc}", err=True)
        raise typer.Exit(3)
