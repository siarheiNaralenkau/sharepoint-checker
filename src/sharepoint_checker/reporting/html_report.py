from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, BaseLoader

from ..models.result_models import RunSummary, CheckStatus

logger = logging.getLogger(__name__)

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SharePoint Checker Report — {{ summary.run_id }}</title>
<style>
  body { font-family: Segoe UI, Arial, sans-serif; margin: 2rem; color: #222; }
  h1 { color: #0078d4; }
  h2 { color: #333; border-bottom: 1px solid #ddd; padding-bottom: .3rem; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; font-size: .9rem; }
  th { background: #0078d4; color: white; padding: .5rem .75rem; text-align: left; }
  td { padding: .4rem .75rem; border-bottom: 1px solid #eee; vertical-align: top; }
  .pass-row td { background: #dff6dd; }
  .fail-row td { background: #fde7e9; }
  .pass-row:hover td { background: #c8f0c5; }
  .fail-row:hover td { background: #f9cccf; }
  .pass { color: #107c10; font-weight: bold; }
  .fail { color: #d83b01; font-weight: bold; }
  .error { color: #a80000; font-weight: bold; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
  .stat-card { background: #f3f2f1; border-radius: 6px; padding: 1rem; text-align: center; }
  .stat-value { font-size: 2rem; font-weight: bold; }
  .stat-label { font-size: .8rem; color: #605e5c; }
  a { color: #0078d4; }
  .yes { color: #107c10; }
  .no { color: #d83b01; }
  .site-id { font-size: .75rem; color: #605e5c; word-break: break-all; }
</style>
</head>
<body>
<h1>SharePoint Structure Checker Report</h1>
<p><strong>Run ID:</strong> {{ summary.run_id }}<br>
<strong>Started:</strong> {{ summary.started_at }}<br>
<strong>Completed:</strong> {{ summary.completed_at }}<br>
<strong>Overall Status:</strong> <span class="{{ summary.overall_status.value | lower }}">{{ summary.overall_status.value }}</span></p>

<h2>Summary</h2>
<div class="summary-grid">
  <div class="stat-card"><div class="stat-value">{{ summary.total_sites }}</div><div class="stat-label">Sites Checked</div></div>
  <div class="stat-card"><div class="stat-value pass">{{ summary.pass_count }}</div><div class="stat-label">Passed</div></div>
  <div class="stat-card"><div class="stat-value fail">{{ summary.fail_count }}</div><div class="stat-label">Failed</div></div>
</div>

<h2>Site Results</h2>
<table>
  <thead>
    <tr>
      <th>Site</th>
      <th>Leadership Folder</th>
      <th>Roster Found</th>
      <th>Roster Has Files</th>
      <th>Status</th>
      <th>Failure Reason</th>
    </tr>
  </thead>
  <tbody>
  {% for site in summary.site_results %}
  {% set row_class = 'pass-row' if site.overall_status.value == 'PASS' else 'fail-row' %}
    <tr class="{{ row_class }}">
      <td>
        {% if site.site_url %}<a href="{{ site.site_url }}" target="_blank">{% endif %}
        {{ site.display_name or site.site_name }}
        {% if site.site_url %}</a>{% endif %}
        <div class="site-id">{{ site.site_id }}</div>
      </td>
      <td>{{ site.leadership_folder or "—" }}</td>
      <td class="{{ 'yes' if site.roster_found else 'no' }}">{{ "Yes" if site.roster_found else "No" }}</td>
      <td class="{{ 'yes' if site.roster_has_files else 'no' }}">{{ "Yes" if site.roster_has_files else "No" }}</td>
      <td class="{{ site.overall_status.value | lower }}">{{ site.overall_status.value }}</td>
      <td>{{ site.failure_reason or site.error or "" }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</body>
</html>
"""


def write_html_report(summary: RunSummary, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "run-summary.html"

    env = Environment(loader=BaseLoader(), autoescape=True)
    tmpl = env.from_string(_TEMPLATE)
    html = tmpl.render(summary=summary, CheckStatus=CheckStatus)
    path.write_text(html, encoding="utf-8")
    logger.info("HTML report written to %s", path)
    return path
