from __future__ import annotations

import json
import logging
from pathlib import Path

from ..models.result_models import RunSummary

logger = logging.getLogger(__name__)


def _format_site(site, generated_time: str) -> dict:
    return {
        "display_name": site.report_display_name,
        "leadership_folder": site.leadership_folder,
        "status": site.overall_status.value,
        "failure_reason": site.failure_reason or "",
        "site_url": site.site_url,
        "roaster_folder": site.roaster_found,
        "roaster_has_files": site.roaster_has_files,
        "roaster_last_modified": site.roaster_last_modified or "",
        "generated_time": generated_time,
    }


def write_json_report(summary: RunSummary, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    local_dt = summary.started_at.astimezone()
    date_str = local_dt.strftime("%d-%m-%Y_%H-%M-%S")
    generated_time = local_dt.strftime("%d/%m/%Y %H:%M:%S")
    path = out / f"SAP SE Account - Roaster Review - {date_str}.json"

    sites = [s for s in summary.site_results if s.leadership_folder is not None]

    data = {
        "site_results": [_format_site(s, generated_time) for s in sites],
        "generated_time": generated_time,
    }

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("JSON report written to %s (%d site(s) after filtering)", path, len(sites))
    return path
