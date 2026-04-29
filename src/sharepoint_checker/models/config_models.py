from __future__ import annotations

from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator


class DelegatedAuthConfig(BaseModel):
    token_cache_path: str = "~/.sp-checker-token-cache.json"


class DiscoveryConfig(BaseModel):
    mode: str = "prefix"
    site_prefixes: list[str] = Field(default_factory=list)


class RulesConfig(BaseModel):
    leadership_folder_regex: str = r"^Project SAP-[A-Za-z]+ leadership$"
    roaster_folder_name: list[str] = Field(default_factory=lambda: ["Roaster"])

    @field_validator("roaster_folder_name", mode="before")
    @classmethod
    def parse_pipe_separated(cls, v: Union[str, list]) -> list[str]:
        if isinstance(v, str):
            return [name.strip() for name in v.split("|") if name.strip()]
        return v


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
    client_secret_env: str = "SP_CHECKER_CLIENT_SECRET"
    client_certificate_path: Optional[str] = None
    delegated_auth: Optional[DelegatedAuthConfig] = None
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
