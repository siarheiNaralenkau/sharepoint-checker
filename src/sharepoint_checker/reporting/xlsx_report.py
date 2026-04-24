from __future__ import annotations

import logging
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

from ..models.result_models import RunSummary, CheckStatus

logger = logging.getLogger(__name__)

_HEADERS = [
    "run_id",
    "display_name",
    "site_id",
    "leadership_folder",
    "roaster_folder",
    "roaster_has_files",
    "status",
    "failure_reason",
]

_FILL_PASS = PatternFill(fill_type="solid", fgColor="C6EFCE")   # Excel green
_FILL_FAIL = PatternFill(fill_type="solid", fgColor="FFC7CE")   # Excel red
_FONT_HEADER = Font(bold=True, color="FFFFFF")
_FILL_HEADER = PatternFill(fill_type="solid", fgColor="0078D4")  # Microsoft blue
_ALIGN_WRAP = Alignment(wrap_text=True, vertical="top")


def write_xlsx_report(summary: RunSummary, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "run-summary.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "Site Results"

    # Header row
    ws.append(_HEADERS)
    for col_idx, _ in enumerate(_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = _FONT_HEADER
        cell.fill = _FILL_HEADER
        cell.alignment = _ALIGN_WRAP

    # Data rows
    for site in summary.site_results:
        row = [
            summary.run_id,
            site.display_name or site.site_name,
            site.site_id,
            site.leadership_folder or "",
            site.roster_found,
            site.roster_has_files,
            site.overall_status.value,
            site.failure_reason or "",
        ]
        ws.append(row)

        fill = _FILL_PASS if site.overall_status == CheckStatus.PASS else _FILL_FAIL
        row_idx = ws.max_row
        for col_idx in range(1, len(_HEADERS) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.fill = fill
            cell.alignment = _ALIGN_WRAP

    # Column widths
    col_widths = [22, 50, 60, 35, 16, 18, 10, 55]
    for col_idx, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.freeze_panes = "A2"

    wb.save(path)
    logger.info("XLSX report written to %s", path)
    return path
