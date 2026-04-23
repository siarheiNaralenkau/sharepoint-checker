from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


class DiscoveredSite(BaseModel):
    site_id: str
    site_name: str
    site_url: str
    display_name: Optional[str] = None


class SiteCheckResult(BaseModel):
    site_name: str
    site_url: str
    site_id: str
    drive_id: Optional[str] = None
    leadership_folder: Optional[str] = None
    roster_found: bool = False
    roster_has_files: bool = False
    failure_reason: Optional[str] = None
    overall_status: CheckStatus = CheckStatus.FAIL
    error: Optional[str] = None


class RunSummary(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    site_results: list[SiteCheckResult] = []
    total_sites: int = 0
    pass_count: int = 0
    fail_count: int = 0
    overall_status: CheckStatus = CheckStatus.PASS
    config_path: Optional[str] = None
