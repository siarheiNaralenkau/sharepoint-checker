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
    display_name: Optional[str] = None
    drive_id: Optional[str] = None
    leadership_folder: Optional[str] = None
    roaster_found: bool = False
    roaster_has_files: bool = False
    roaster_last_modified: Optional[str] = None
    failure_reason: Optional[str] = None
    overall_status: CheckStatus = CheckStatus.FAIL
    error: Optional[str] = None

    @property
    def report_display_name(self) -> str:
        """Site display name with the leadership folder suffix stripped.

        SharePoint site titles often embed the leadership folder name
        (e.g. "CSD Area-Project SAP-MxG leadership"). Since the leadership
        folder is shown in a dedicated column, we remove the variable suffix
        but keep the first word of the folder name ("Project") because it is
        part of the site-naming convention.
        """
        name = self.display_name or self.site_name
        if not self.leadership_folder:
            return name
        lf = self.leadership_folder
        if not name.lower().endswith(lf.lower()):
            return name
        first_word = lf.split()[0]
        return name[: len(name) - len(lf) + len(first_word)].rstrip()


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
