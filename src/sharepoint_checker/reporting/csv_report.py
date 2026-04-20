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
    "library_name",
    "project_folder",
    "folder_status",
    "missing_folders",
    "file_status",
    "missing_files",
    "overall_status",
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
            if not site.project_results:
                writer.writerow({
                    "run_id": summary.run_id,
                    "site_name": site.site_name,
                    "site_url": site.site_url,
                    "library_name": site.library_name,
                    "project_folder": "",
                    "folder_status": "",
                    "missing_folders": "",
                    "file_status": "",
                    "missing_files": "",
                    "overall_status": site.overall_status.value,
                    "error": site.error or "",
                })
                continue

            for proj in site.project_results:
                writer.writerow({
                    "run_id": summary.run_id,
                    "site_name": site.site_name,
                    "site_url": site.site_url,
                    "library_name": site.library_name,
                    "project_folder": proj.project_folder,
                    "folder_status": proj.folder_check.status.value,
                    "missing_folders": "; ".join(proj.folder_check.missing_folders),
                    "file_status": proj.file_check.status.value,
                    "missing_files": "; ".join(proj.file_check.missing_files),
                    "overall_status": proj.overall_status.value,
                    "error": proj.error or "",
                })

    logger.info("CSV report written to %s", path)
    return path
