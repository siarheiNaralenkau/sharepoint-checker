from __future__ import annotations

import json
import logging
from pathlib import Path

from ..models.result_models import RunSummary

logger = logging.getLogger(__name__)


def _format_site(site, run_id: str) -> dict:
    return {
        "display_name": site.display_name or site.site_name,
        "status": site.overall_status.value,
        "site_url": site.site_url,
        "leadership_folder": site.leadership_folder,
        "roaster_folder": site.roster_found,
        "roaster_has_files": site.roster_has_files,
        "failure_reason": site.failure_reason or "",
        "reporting_datetime": run_id,
    }


def write_json_report(summary: RunSummary, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "run-summary.json"

    sites = [s for s in summary.site_results if s.leadership_folder is not None]

    data = {
        "site_results": [_format_site(s, summary.run_id) for s in sites],
        "reporting_datetime": summary.run_id,
    }

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("JSON report written to %s (%d site(s) after filtering)", path, len(sites))
    return path
