from __future__ import annotations

import csv
import logging
from pathlib import Path

from ..models.result_models import RunSummary

logger = logging.getLogger(__name__)

_HEADERS = [
    "run_id",
    "site_name",
    "site_url",
    "leadership_folder",
    "roster_found",
    "roster_has_files",
    "overall_status",
    "failure_reason",
    "error",
]


def write_csv_report(summary: RunSummary, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "run-summary.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_HEADERS)
        writer.writeheader()
        for site in summary.site_results:
            writer.writerow({
                "run_id": summary.run_id,
                "site_name": site.site_name,
                "site_url": site.site_url,
                "leadership_folder": site.leadership_folder or "",
                "roster_found": site.roster_found,
                "roster_has_files": site.roster_has_files,
                "overall_status": site.overall_status.value,
                "failure_reason": site.failure_reason or "",
                "error": site.error or "",
            })

    logger.info("CSV report written to %s", path)
    return path
