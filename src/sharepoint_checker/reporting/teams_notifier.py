from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from ..models.result_models import CheckStatus, RunSummary

logger = logging.getLogger(__name__)


def _build_card(summary: RunSummary, only_failures: bool) -> dict:
    status_color = "Good" if summary.overall_status == CheckStatus.PASS else "Attention"
    facts = [
        {"name": "Run ID", "value": summary.run_id},
        {"name": "Sites Checked", "value": str(summary.total_sites)},
        {"name": "Project Folders", "value": str(summary.total_projects)},
        {"name": "Passed", "value": str(summary.pass_count)},
        {"name": "Failed", "value": str(summary.fail_count)},
        {"name": "Overall Status", "value": summary.overall_status.value},
    ]

    failing = [
        f"**{s.site_name}**: {s.fail_count} project(s) failed"
        for s in summary.site_results
        if s.fail_count > 0
    ]
    body_parts = []
    if failing:
        body_parts.append("**Failing sites:**\n" + "\n".join(f"- {l}" for l in failing[:10]))

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0078D4" if summary.overall_status == CheckStatus.PASS else "D83B01",
        "summary": f"SharePoint Checker: {summary.overall_status.value}",
        "sections": [
            {
                "activityTitle": f"SharePoint Tenant Checker — {summary.overall_status.value}",
                "activitySubtitle": f"Run {summary.run_id}",
                "facts": facts,
                "markdown": True,
            },
            *(
                [{"text": "\n\n".join(body_parts), "markdown": True}]
                if body_parts
                else []
            ),
        ],
    }


async def send_teams_notification(
    summary: RunSummary,
    webhook_env: str = "SP_CHECKER_TEAMS_WEBHOOK",
    only_failures: bool = False,
) -> bool:
    webhook_url = os.environ.get(webhook_env)
    if not webhook_url:
        logger.warning("Teams webhook not configured (env: %s) — skipping", webhook_env)
        return False

    card = _build_card(summary, only_failures)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(webhook_url, json=card)
            response.raise_for_status()
        logger.info("Teams notification sent (status %d)", response.status_code)
        return True
    except Exception as exc:
        logger.error("Failed to send Teams notification: %s", exc)
        return False
