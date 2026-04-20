from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from ..models.config_models import EmailConfig
from ..models.result_models import CheckStatus, RunSummary

logger = logging.getLogger(__name__)


def _build_html_body(summary: RunSummary) -> str:
    status_color = "#107c10" if summary.overall_status == CheckStatus.PASS else "#d83b01"
    lines = [
        f"<h2 style='color:{status_color}'>SharePoint Checker: {summary.overall_status.value}</h2>",
        f"<p><strong>Run ID:</strong> {summary.run_id}<br>",
        f"<strong>Sites checked:</strong> {summary.total_sites}<br>",
        f"<strong>Project folders:</strong> {summary.total_projects}<br>",
        f"<strong>Passed:</strong> {summary.pass_count} &nbsp; <strong>Failed:</strong> {summary.fail_count}</p>",
    ]
    failing = [s for s in summary.site_results if s.fail_count > 0]
    if failing:
        lines.append("<h3>Failing Sites</h3><ul>")
        for site in failing[:20]:
            lines.append(
                f'<li><a href="{site.site_url}">{site.site_name}</a>: '
                f"{site.fail_count} project(s) failed</li>"
            )
        lines.append("</ul>")

    lines.append("<p><em>See attached report for full details.</em></p>")
    return "\n".join(lines)


def send_email_notification(
    summary: RunSummary,
    email_config: EmailConfig,
    report_path: Optional[Path] = None,
) -> bool:
    if not email_config.enabled:
        return False

    smtp_user = os.environ.get(email_config.smtp_user_env or "")
    smtp_password = os.environ.get(email_config.smtp_password_env or "")

    if not email_config.smtp_host:
        logger.warning("Email SMTP host not configured — skipping")
        return False

    subject = f"[SharePoint Checker] {summary.overall_status.value} — {summary.run_id}"
    from_addr = email_config.from_address or smtp_user or "noreply@localhost"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(email_config.recipients)

    html_body = _build_html_body(summary)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if report_path and report_path.exists():
        from email.mime.base import MIMEBase
        from email import encoders

        with report_path.open("rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{report_path.name}"')
        msg.attach(part)

    try:
        with smtplib.SMTP(email_config.smtp_host, email_config.smtp_port) as server:
            server.ehlo()
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, email_config.recipients, msg.as_string())
        logger.info("Email notification sent to %s", email_config.recipients)
        return True
    except Exception as exc:
        logger.error("Failed to send email notification: %s", exc)
        return False
