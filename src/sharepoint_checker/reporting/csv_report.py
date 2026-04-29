from __future__ import annotations

import csv
import logging
from pathlib import Path

from ..models.result_models import RunSummary

logger = logging.getLogger(__name__)

_HEADERS = [
    "display_name",
    "leadership_folder",
    "status",
    "failure_reason",
    "site_url",
    "roaster_folder",
    "roaster_has_files",
    "roaster_last_modified",
    "generated_time",
]


def write_csv_report(summary: RunSummary, output_dir: str | Path) -> Path:
    """Writes all discovered sites (no filtering) to a CSV file."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    local_dt = summary.started_at.astimezone()
    date_str = local_dt.strftime("%d-%m-%Y_%H-%M-%S")
    generated_time = local_dt.strftime("%d/%m/%Y %H:%M:%S")
    path = out / f"SAP SE Account - Roaster Review - {date_str}.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_HEADERS)
        writer.writeheader()
        for site in summary.site_results:
            writer.writerow({
                "display_name": site.report_display_name,
                "leadership_folder": site.leadership_folder or "",
                "status": site.overall_status.value,
                "failure_reason": site.failure_reason or "",
                "site_url": site.site_url or "",
                "roaster_folder": site.roaster_found,
                "roaster_has_files": site.roaster_has_files,
                "roaster_last_modified": site.roaster_last_modified or "",
                "generated_time": generated_time,
            })

    logger.info("CSV report written to %s (%d site(s))", path, len(summary.site_results))
    return path
