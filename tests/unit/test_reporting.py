import json
import csv
import tempfile
from datetime import datetime, timezone

import pytest

from sharepoint_checker.models.result_models import (
    CheckStatus,
    RunSummary,
    SiteCheckResult,
)
from sharepoint_checker.reporting import write_json_report, write_csv_report, write_html_report


def _make_summary(fail: bool = False) -> RunSummary:
    site = SiteCheckResult(
        site_name="EPAMSAPSEProjectsCSDArea",
        site_url="https://epam.sharepoint.com/sites/EPAMSAPSEProjectsCSDArea",
        site_id="site1",
        drive_id="drive1",
        leadership_folder="Project SAP-mMXG-leadership" if not fail else None,
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
    assert data["total_sites"] == 1
    assert data["overall_status"] == "PASS"


def test_csv_report_rows():
    summary = _make_summary(fail=True)
    with tempfile.TemporaryDirectory() as d:
        path = write_csv_report(summary, d)
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["overall_status"] == "FAIL"
    assert "regex" in rows[0]["failure_reason"]


def test_html_report_contains_key_data():
    summary = _make_summary(fail=True)
    with tempfile.TemporaryDirectory() as d:
        path = write_html_report(summary, d)
        html = path.read_text(encoding="utf-8")
    assert "2026-04-20T12:00:00Z" in html
    assert "EPAMSAPSEProjectsCSDArea" in html
    assert "FAIL" in html
