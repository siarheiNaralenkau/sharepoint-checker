from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from ..auth import TokenProvider
from ..folder_scanner import FolderScanner
from ..graph_client import GraphClient
from ..library_resolver import DriveResolver, NoDriveFoundError
from ..models.config_models import CheckerConfig
from ..models.result_models import CheckStatus, RunSummary, SiteCheckResult
from ..site_discovery import SiteDiscovery
from ..validators import NamingValidator

logger = logging.getLogger(__name__)


async def _check_site(
    site_id: str,
    site_name: str,
    site_url: str,
    display_name: Optional[str],
    config: CheckerConfig,
    client: GraphClient,
) -> SiteCheckResult:
    result = SiteCheckResult(
        site_name=site_name,
        site_url=site_url,
        site_id=site_id,
        display_name=display_name,
    )

    # Step 1: Resolve drive
    try:
        resolver = DriveResolver(client)
        drive_id = await resolver.get_first_drive_id(site_id)
        result.drive_id = drive_id
    except NoDriveFoundError as exc:
        result.failure_reason = str(exc)
        result.overall_status = CheckStatus.FAIL
        return result
    except Exception as exc:
        logger.error("Site %s: unexpected error getting drive: %s", site_url, exc)
        result.error = str(exc)
        result.overall_status = CheckStatus.ERROR
        return result

    scanner = FolderScanner(client)
    naming_val = NamingValidator(config.rules.leadership_folder_regex)

    # Step 2: List root, find leadership folder
    try:
        root_items = await scanner.list_root_folders(drive_id)
    except Exception as exc:
        logger.error("Site %s: failed to list root: %s", site_url, exc)
        result.error = str(exc)
        result.overall_status = CheckStatus.ERROR
        return result

    leadership_matches = [item for item in root_items if naming_val.is_project_folder(item.name)]
    if not leadership_matches:
        result.failure_reason = f"No folder matching {config.rules.leadership_folder_regex!r} found at root"
        result.overall_status = CheckStatus.FAIL
        return result

    leadership_folder = leadership_matches[0]
    result.leadership_folder = leadership_folder.name
    if leadership_folder.web_url:
        result.site_url = leadership_folder.web_url
    logger.info("Site %s: found leadership folder %r", site_url, leadership_folder.name)

    # Step 3: List leadership folder children — must be non-empty
    try:
        children = await scanner.list_folder_children(drive_id, leadership_folder.item_id)
    except Exception as exc:
        logger.error("Site %s: failed to list %r children: %s", site_url, leadership_folder.name, exc)
        result.error = str(exc)
        result.overall_status = CheckStatus.ERROR
        return result

    if not children:
        result.failure_reason = f"Leadership folder {leadership_folder.name!r} is empty"
        result.overall_status = CheckStatus.FAIL
        return result

    # Step 4: Roster folder must be present
    roster_name = config.rules.roaster_folder_name
    roster_matches = [c for c in children if c.is_folder and c.name.lower() == roster_name.lower()]
    if not roster_matches:
        result.failure_reason = f"'{roster_name}' folder not found inside {leadership_folder.name!r}"
        result.overall_status = CheckStatus.FAIL
        return result

    result.roaster_found = True
    roster_folder = roster_matches[0]

    # Step 5: Roster must contain at least one file
    try:
        roster_children = await scanner.list_folder_children(drive_id, roster_folder.item_id)
    except Exception as exc:
        logger.error("Site %s: failed to list Roster children: %s", site_url, exc)
        result.error = str(exc)
        result.overall_status = CheckStatus.ERROR
        return result

    roster_files = [c for c in roster_children if not c.is_folder]
    if not roster_files:
        result.failure_reason = f"'{roster_name}' folder contains no files"
        result.overall_status = CheckStatus.FAIL
        return result

    result.roaster_has_files = True
    result.overall_status = CheckStatus.PASS
    logger.info("Site %s: PASS", site_url)
    return result


async def run_checker(
    config: CheckerConfig,
    config_path: Optional[str] = None,
    dry_run: bool = False,
) -> RunSummary:
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    started_at = datetime.now(timezone.utc)

    logger.info("Starting run %s (dry_run=%s)", run_id, dry_run)

    summary = RunSummary(
        run_id=run_id,
        started_at=started_at,
        config_path=config_path,
    )

    token_provider = TokenProvider(config)
    semaphore = asyncio.Semaphore(config.execution.max_parallel_sites)

    async with GraphClient(
        token_provider=token_provider,
        page_size=config.execution.page_size,
        retry_attempts=config.execution.retry_attempts,
        retry_backoff_seconds=config.execution.retry_backoff_seconds,
    ) as client:
        discovery = SiteDiscovery(client, config.discovery)
        sites = await discovery.discover()
        logger.info("Processing %d site(s)", len(sites))

        if dry_run:
            logger.info("[dry-run] Would process: %s", [s.display_name or s.site_id for s in sites])
            summary.total_sites = len(sites)
            summary.completed_at = datetime.now(timezone.utc)
            return summary

        async def bounded_check(site):
            async with semaphore:
                return await _check_site(
                    site_id=site.site_id,
                    site_name=site.site_name,
                    site_url=site.site_url,
                    display_name=site.display_name,
                    config=config,
                    client=client,
                )

        site_results = await asyncio.gather(
            *[bounded_check(site) for site in sites], return_exceptions=False
        )

    pass_count = sum(1 for r in site_results if r.overall_status == CheckStatus.PASS)
    fail_count = len(site_results) - pass_count
    overall = CheckStatus.PASS if fail_count == 0 else CheckStatus.FAIL

    summary.site_results = list(site_results)
    summary.total_sites = len(site_results)
    summary.pass_count = pass_count
    summary.fail_count = fail_count
    summary.overall_status = overall
    summary.completed_at = datetime.now(timezone.utc)

    logger.info(
        "Run complete: %d site(s), %d PASS, %d FAIL — overall %s",
        len(site_results),
        pass_count,
        fail_count,
        overall.value,
    )

    return summary
