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
  tr:hover td { background: #f5f9ff; }
  .pass { color: #107c10; font-weight: bold; }
  .fail { color: #d83b01; font-weight: bold; }
  .error { color: #a80000; font-weight: bold; }
  .skip { color: #797673; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
  .stat-card { background: #f3f2f1; border-radius: 6px; padding: 1rem; text-align: center; }
  .stat-value { font-size: 2rem; font-weight: bold; }
  .stat-label { font-size: .8rem; color: #605e5c; }
  .missing-list { margin: 0; padding-left: 1.2rem; }
  a { color: #0078d4; }
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
  <div class="stat-card"><div class="stat-value">{{ summary.total_projects }}</div><div class="stat-label">Project Folders</div></div>
  <div class="stat-card"><div class="stat-value pass">{{ summary.pass_count }}</div><div class="stat-label">Passed</div></div>
  <div class="stat-card"><div class="stat-value fail">{{ summary.fail_count }}</div><div class="stat-label">Failed</div></div>
</div>

<h2>Site Overview</h2>
<table>
  <thead><tr><th>Site</th><th>Library</th><th>Projects</th><th>Pass</th><th>Fail</th><th>Status</th></tr></thead>
  <tbody>
  {% for site in summary.site_results %}
    <tr>
      <td><a href="{{ site.site_url }}" target="_blank">{{ site.site_name }}</a></td>
      <td>{{ site.library_name }}</td>
      <td>{{ site.project_count }}</td>
      <td class="pass">{{ site.pass_count }}</td>
      <td class="{% if site.fail_count > 0 %}fail{% endif %}">{{ site.fail_count }}</td>
      <td class="{{ site.overall_status.value | lower }}">{{ site.overall_status.value }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>

<h2>Project Folder Details</h2>
<table>
  <thead><tr><th>Site</th><th>Project Folder</th><th>Folder Check</th><th>Missing Folders</th><th>File Check</th><th>Missing Files</th><th>Overall</th></tr></thead>
  <tbody>
  {% for site in summary.site_results %}
    {% for proj in site.project_results %}
    <tr>
      <td>{{ site.site_name }}</td>
      <td>{{ proj.project_folder }}</td>
      <td class="{{ proj.folder_check.status.value | lower }}">{{ proj.folder_check.status.value }}</td>
      <td>
        {% if proj.folder_check.missing_folders %}
        <ul class="missing-list">{% for f in proj.folder_check.missing_folders %}<li>{{ f }}</li>{% endfor %}</ul>
        {% endif %}
      </td>
      <td class="{{ proj.file_check.status.value | lower }}">{{ proj.file_check.status.value }}</td>
      <td>
        {% if proj.file_check.missing_files %}
        <ul class="missing-list">{% for f in proj.file_check.missing_files %}<li>{{ f }}</li>{% endfor %}</ul>
        {% endif %}
      </td>
      <td class="{{ proj.overall_status.value | lower }}">{{ proj.overall_status.value }}</td>
    </tr>
    {% endfor %}
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
