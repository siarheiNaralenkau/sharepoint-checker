from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from ..auth import TokenProvider
from ..folder_scanner import FolderScanner
from ..graph_client import GraphClient
from ..library_resolver import LibraryNotFoundError, LibraryResolver
from ..models.config_models import CheckerConfig
from ..models.result_models import (
    CheckStatus,
    ProjectCheckResult,
    RunSummary,
    SiteCheckResult,
)
from ..site_discovery import SiteDiscovery
from ..validators import FileValidator, FolderValidator, NamingValidator

logger = logging.getLogger(__name__)


async def _check_site(
    site_id: str,
    site_name: str,
    site_url: str,
    config: CheckerConfig,
    client: GraphClient,
) -> SiteCheckResult:
    library_name = config.sharepoint.library_name
    result = SiteCheckResult(
        site_name=site_name,
        site_url=site_url,
        site_id=site_id,
        library_name=library_name,
    )

    try:
        resolver = LibraryResolver(client)
        drive_id = await resolver.resolve_drive_id(site_id, library_name)
    except LibraryNotFoundError as exc:
        logger.warning("Site %s: %s", site_url, exc)
        result.error = str(exc)
        result.overall_status = CheckStatus.ERROR
        return result
    except Exception as exc:
        logger.error("Site %s: unexpected error resolving library: %s", site_url, exc)
        result.error = str(exc)
        result.overall_status = CheckStatus.ERROR
        return result

    scanner = FolderScanner(client)
    naming_val = NamingValidator(config.sharepoint.project_folder_regex)
    folder_val = FolderValidator(config.rules.required_folders)
    file_val = FileValidator(config.rules.required_files)

    try:
        root_items = await scanner.list_root_folders(drive_id, config.sharepoint.root_folder)
    except Exception as exc:
        logger.error("Site %s: failed to list root folder: %s", site_url, exc)
        result.error = str(exc)
        result.overall_status = CheckStatus.ERROR
        return result

    project_folders = [item for item in root_items if naming_val.is_project_folder(item.name)]
    logger.info("Site %s: found %d project folder(s)", site_url, len(project_folders))

    project_results: list[ProjectCheckResult] = []
    for pf in project_folders:
        proj_result = await _check_project_folder(
            drive_id=drive_id,
            project_folder=pf,
            folder_val=folder_val,
            file_val=file_val,
            scanner=scanner,
            required_files=config.rules.required_files,
        )
        project_results.append(proj_result)

    pass_count = sum(1 for r in project_results if r.overall_status == CheckStatus.PASS)
    fail_count = len(project_results) - pass_count
    overall = CheckStatus.PASS if fail_count == 0 else CheckStatus.FAIL

    result.project_results = project_results
    result.project_count = len(project_results)
    result.pass_count = pass_count
    result.fail_count = fail_count
    result.overall_status = overall
    return result


async def _check_project_folder(
    drive_id: str,
    project_folder,
    folder_val: FolderValidator,
    file_val: FileValidator,
    scanner: FolderScanner,
    required_files: dict[str, list[str]],
) -> ProjectCheckResult:
    try:
        children = await scanner.list_folder_children(
            drive_id, project_folder.item_id, project_folder.name
        )
        subfolder_names = [c.name for c in children if c.is_folder]
        folder_check = folder_val.validate(subfolder_names)

        folder_contents: dict[str, list[str]] = {}
        for folder_name in required_files:
            sub_children = await scanner.list_subfolder_children(
                drive_id, project_folder.item_id, folder_name, project_folder.name
            )
            folder_contents[folder_name] = [c.name for c in sub_children if not c.is_folder]

        file_check = file_val.validate(folder_contents)

        overall = (
            CheckStatus.PASS
            if folder_check.status == CheckStatus.PASS and file_check.status == CheckStatus.PASS
            else CheckStatus.FAIL
        )

        return ProjectCheckResult(
            project_folder=project_folder.name,
            folder_check=folder_check,
            file_check=file_check,
            overall_status=overall,
        )
    except Exception as exc:
        logger.error("Error checking project folder %s: %s", project_folder.name, exc)
        from ..models.result_models import FolderCheckResult, FileCheckResult

        return ProjectCheckResult(
            project_folder=project_folder.name,
            folder_check=FolderCheckResult(
                status=CheckStatus.ERROR,
                required_folders=[],
                found_folders=[],
                missing_folders=[],
            ),
            file_check=FileCheckResult(status=CheckStatus.ERROR, missing_files=[]),
            overall_status=CheckStatus.ERROR,
            error=str(exc),
        )


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
            logger.info("[dry-run] Would process: %s", [s.site_url for s in sites])
            summary.total_sites = len(sites)
            summary.completed_at = datetime.now(timezone.utc)
            return summary

        async def bounded_check(site):
            async with semaphore:
                return await _check_site(
                    site_id=site.site_id,
                    site_name=site.site_name,
                    site_url=site.site_url,
                    config=config,
                    client=client,
                )

        site_results = await asyncio.gather(
            *[bounded_check(site) for site in sites], return_exceptions=False
        )

    total_projects = sum(r.project_count for r in site_results)
    pass_count = sum(r.pass_count for r in site_results)
    fail_count = sum(r.fail_count for r in site_results)
    overall = CheckStatus.PASS if fail_count == 0 else CheckStatus.FAIL

    summary.site_results = list(site_results)
    summary.total_sites = len(site_results)
    summary.total_projects = total_projects
    summary.pass_count = pass_count
    summary.fail_count = fail_count
    summary.overall_status = overall
    summary.completed_at = datetime.now(timezone.utc)

    logger.info(
        "Run complete: %d site(s), %d project(s), %d PASS, %d FAIL — overall %s",
        len(site_results),
        total_projects,
        pass_count,
        fail_count,
        overall.value,
    )

    return summary
