import json
import tempfile
from datetime import datetime, timezone

import pytest
from openpyxl import load_workbook

from sharepoint_checker.models.result_models import (
    CheckStatus,
    RunSummary,
    SiteCheckResult,
)
from sharepoint_checker.reporting import write_json_report, write_xlsx_report, write_html_report


def _make_summary(fail: bool = False) -> RunSummary:
    site = SiteCheckResult(
        site_name="EPAMSAPSEProjectsCSDArea",
        site_url="https://epam.sharepoint.com/sites/EPAMSAPSEProjectsCSDArea",
        site_id="epam.sharepoint.com,abc,def",
        display_name="EPAM SAP SE Projects, CSD Area-Project SAP-MxG leadership",
        drive_id="drive1",
        leadership_folder="Project SAP-MxG leadership" if not fail else None,
        roster_found=not fail,
        roster_has_files=not fail,
        failure_reason=None if not fail else "No folder matching regex found at root",
        overall_status=CheckStatus.FAIL if fail else CheckStatus.PASS,
    )
    return RunSummary(
        run_id="2026-04-20T12:00:00Z",
        started_at=datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 4, 20, 12, 1, 0, tzinfo=timezone.utc),
        site_results=[site],
        total_sites=1,
        pass_count=0 if fail else 1,
        fail_count=1 if fail else 0,
        overall_status=CheckStatus.FAIL if fail else CheckStatus.PASS,
    )


def test_json_report_structure():
    summary = _make_summary()
    with tempfile.TemporaryDirectory() as d:
        path = write_json_report(summary, d)
        data = json.loads(path.read_text())

    assert data["run_id"] == "2026-04-20T12:00:00Z"
    assert len(data["site_results"]) == 1
    site = data["site_results"][0]
    assert site["display_name"] == "EPAM SAP SE Projects, CSD Area-Project SAP-MxG leadership"
    assert site["status"] == "PASS"
    assert site["roaster_folder"] is True
    assert site["roaster_has_files"] is True
    assert site["failure_reason"] == ""
    # internal fields must not leak into output
    assert "site_name" not in site
    assert "overall_status" not in site
    assert "roster_found" not in site


def test_json_report_fail_site():
    summary = _make_summary(fail=True)
    with tempfile.TemporaryDirectory() as d:
        path = write_json_report(summary, d)
        data = json.loads(path.read_text())
    site = data["site_results"][0]
    assert site["status"] == "FAIL"
    assert site["roaster_folder"] is False
    assert "regex" in site["failure_reason"]


def test_xlsx_report_rows_and_colors():
    summary = _make_summary(fail=True)
    with tempfile.TemporaryDirectory() as d:
        path = write_xlsx_report(summary, d)
        wb = load_workbook(path)
        ws = wb.active

    headers = [ws.cell(row=1, column=i).value for i in range(1, 9)]
    assert "display_name" in headers
    assert "roaster_folder" in headers
    assert "status" in headers

    data_row = [ws.cell(row=2, column=i).value for i in range(1, 9)]
    assert "FAIL" in data_row

    # FAIL row must have red fill (openpyxl reads 6-char hex back with 00 alpha prefix)
    fill_color = ws.cell(row=2, column=1).fill.fgColor.rgb
    assert fill_color == "00FFC7CE"


def test_xlsx_report_pass_row_green():
    summary = _make_summary(fail=False)
    with tempfile.TemporaryDirectory() as d:
        path = write_xlsx_report(summary, d)
        wb = load_workbook(path)
        ws = wb.active

    fill_color = ws.cell(row=2, column=1).fill.fgColor.rgb
    assert fill_color == "00C6EFCE"


def test_html_report_contains_key_data():
    summary = _make_summary(fail=True)
    with tempfile.TemporaryDirectory() as d:
        path = write_html_report(summary, d)
        html = path.read_text(encoding="utf-8")
    assert "2026-04-20T12:00:00Z" in html
    assert "EPAM SAP SE Projects, CSD Area-Project SAP-MxG leadership" in html
    assert "FAIL" in html
    assert "fail-row" in html
