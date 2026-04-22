from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

class DelegatedAuthConfig(BaseModel):
    token_cache_path: str = "~/.sp-checker-token-cache.json"

class DiscoveryConfig(BaseModel):
    mode: str = "all-visible"
    site_prefixes: list[str] = Field(default_factory=list)
    display_name_patterns: list[str] = Field(default_factory=list)


class SharePointConfig(BaseModel):
    library_name: str = "Shared Documents"
    root_folder: str = "/"
    project_folder_regex: str = r"^Project-[A-Za-z0-9]+-.+$"


class RulesConfig(BaseModel):
    required_folders: list[str] = Field(default_factory=list)
    required_files: dict[str, list[str]] = Field(default_factory=dict)


class ExecutionConfig(BaseModel):
    max_parallel_sites: int = 4
    page_size: int = 200
    retry_attempts: int = 5
    retry_backoff_seconds: float = 2.0


class EmailConfig(BaseModel):
    enabled: bool = False
    recipients: list[str] = Field(default_factory=list)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user_env: Optional[str] = None
    smtp_password_env: Optional[str] = None
    from_address: Optional[str] = None


class TeamsConfig(BaseModel):
    enabled: bool = False
    webhook_env: str = "SP_CHECKER_TEAMS_WEBHOOK"


class ReportingConfig(BaseModel):
    output_dir: str = "./out"
    formats: list[str] = Field(default_factory=lambda: ["json", "csv", "html"])
    only_failures_in_notification: bool = False
    email: EmailConfig = Field(default_factory=EmailConfig)
    teams: TeamsConfig = Field(default_factory=TeamsConfig)


class CheckerConfig(BaseModel):
    tenant_id: str
    client_id: str
    client_secret_env: str = "SP_CHECKER_CLIENT_SECRET"  # kept for backward compat
    client_certificate_path: Optional[str] = None
    delegated_auth: Optional[DelegatedAuthConfig] = None  # None = use app-only flow
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    sharepoint: SharePointConfig = Field(default_factory=SharePointConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
