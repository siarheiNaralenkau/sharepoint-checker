from __future__ import annotations

import csv
import logging
from pathlib import Path

from ..models.result_models import RunSummary

logger = logging.getLogger(__name__)

_HEADERS = [
    "display_name",
    "status",
    "site_url",
    "leadership_folder",
    "roaster_folder",
    "roaster_has_files",
    "failure_reason",
    "reporting_datetime",
]


def write_csv_report(summary: RunSummary, output_dir: str | Path) -> Path:
    """Writes all discovered sites (no filtering) to a CSV file."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "run-summary.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_HEADERS)
        writer.writeheader()
        for site in summary.site_results:
            writer.writerow({
                "display_name": site.display_name or site.site_name,
                "status": site.overall_status.value,
                "site_url": site.site_url or "",
                "leadership_folder": site.leadership_folder or "",
                "roaster_folder": site.roaster_found,
                "roaster_has_files": site.roaster_has_files,
                "failure_reason": site.failure_reason or "",
                "reporting_datetime": summary.run_id,
            })

    logger.info("CSV report written to %s (%d site(s))", path, len(summary.site_results))
    return path
