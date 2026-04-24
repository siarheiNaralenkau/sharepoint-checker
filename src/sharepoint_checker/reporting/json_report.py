from __future__ import annotations

import json
import logging
from pathlib import Path

from ..models.result_models import RunSummary

logger = logging.getLogger(__name__)


def _format_site(site) -> dict:
    return {
        "display_name": site.display_name or site.site_name,
        "site_id": site.site_id,
        "leadership_folder": site.leadership_folder,
        "roaster_folder": site.roster_found,
        "roaster_has_files": site.roster_has_files,
        "status": site.overall_status.value,
        "failure_reason": site.failure_reason or "",
    }


def write_json_report(summary: RunSummary, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "run-summary.json"

    data = {
        "run_id": summary.run_id,
        "site_results": [_format_site(s) for s in summary.site_results],
    }

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("JSON report written to %s", path)
    return path
