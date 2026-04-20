from __future__ import annotations

import logging
import os
from typing import Optional

import msal

from .models.config_models import CheckerConfig
from .utils.retry import GraphApiError

logger = logging.getLogger(__name__)

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


class AuthError(Exception):
    pass


class TokenProvider:
    """Acquires and caches app-only tokens via client credentials flow."""

    def __init__(self, config: CheckerConfig) -> None:
        self._config = config
        self._app = self._build_app()

    def _build_app(self) -> msal.ConfidentialClientApplication:
        authority = f"https://login.microsoftonline.com/{self._config.tenant_id}"

        if self._config.client_certificate_path:
            cert_path = self._config.client_certificate_path
            logger.info("Using certificate credential from %s", cert_path)
            with open(cert_path, "rb") as f:
                cert_data = f.read()
            credential = {"private_key": cert_data}
            return msal.ConfidentialClientApplication(
                self._config.client_id,
                authority=authority,
                client_credential=credential,
            )

        secret_env = self._config.client_secret_env
        secret = os.environ.get(secret_env)
        if not secret:
            raise AuthError(
                f"Client secret not found in environment variable '{secret_env}'. "
                "Set the variable or configure a certificate path."
            )
        logger.info("Using client secret credential (env: %s)", secret_env)
        return msal.ConfidentialClientApplication(
            self._config.client_id,
            authority=authority,
            client_credential=secret,
        )

    def get_token(self) -> str:
        result = self._app.acquire_token_for_client(scopes=GRAPH_SCOPE)
        if "access_token" not in result:
            error = result.get("error", "unknown")
            description = result.get("error_description", "No description")
            raise AuthError(f"Token acquisition failed [{error}]: {description}")
        return result["access_token"]
