from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import msal

from .models.config_models import CheckerConfig
from .utils.retry import GraphApiError

logger = logging.getLogger(__name__)

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
DELEGATED_SCOPES = ["https://graph.microsoft.com/Sites.Read.All"]

class AuthError(Exception):
    pass


class TokenProvider:

    def __init__(self, config: CheckerConfig) -> None:
        self._config = config
        self._cache: Optional[msal.SerializableTokenCache] = None
        self._public_app: Optional[msal.PublicClientApplication] = None
        self._confidential_app: Optional[msal.ConfidentialClientApplication] = None

        if config.delegated_auth:
            self._cache_path = Path(config.delegated_auth.token_cache_path).expanduser()
            cache = msal.SerializableTokenCache()
            if self._cache_path.exists():
                cache.deserialize(self._cache_path.read_text())
            self._cache = cache
            self._public_app = msal.PublicClientApplication(
                config.client_id,
                authority=f"https://login.microsoftonline.com/{config.tenant_id}",
                token_cache=self._cache,
            )
        else:
            self._confidential_app = self._build_confidential_app()

    # ------------------------------------------------------------------ app-only

    def _build_confidential_app(self) -> msal.ConfidentialClientApplication:
        authority = f"https://login.microsoftonline.com/{self._config.tenant_id}"
        if self._config.client_certificate_path:
            with open(self._config.client_certificate_path, "rb") as f:
                cert_data = f.read()
            return msal.ConfidentialClientApplication(
                self._config.client_id,
                authority=authority,
                client_credential={"private_key": cert_data},
            )
        secret_env = self._config.client_secret_env
        secret = os.environ.get(secret_env)
        if not secret:
            raise AuthError(
                f"Client secret not found in environment variable '{secret_env}'."
            )
        return msal.ConfidentialClientApplication(
            self._config.client_id,
            authority=authority,
            client_credential=secret,
        )

    # ------------------------------------------------------------------ token

    def get_token(self) -> str:
        if self._config.delegated_auth:
            return self._get_delegated_token()
        return self._get_app_only_token()

    def _get_app_only_token(self) -> str:
        assert self._confidential_app is not None
        result = self._confidential_app.acquire_token_for_client(scopes=GRAPH_SCOPE)
        if "access_token" not in result:
            error = result.get("error", "unknown")
            description = result.get("error_description", "No description")
            raise AuthError(f"Token acquisition failed [{error}]: {description}")
        return result["access_token"]

    def _get_delegated_token(self) -> str:
        assert self._public_app is not None
        accounts = self._public_app.get_accounts()
        if accounts:
            result = self._public_app.acquire_token_silent(
                scopes=DELEGATED_SCOPES,
                account=accounts[0],
            )
            if result and "access_token" in result:
                self._persist_cache()
                return result["access_token"]

        raise AuthError(
            "No valid token found in cache. "
            "Run 'sp-checker auth-login -c <config>' to authenticate."
        )

    # ------------------------------------------------------------------ login

    def login_device_code(self) -> None:
        """Interactive device code flow. Call once; saves the refresh token to disk."""
        assert self._public_app is not None
        flow = self._public_app.initiate_device_flow(scopes=DELEGATED_SCOPES)
        if "user_code" not in flow:
            raise AuthError(
                f"Failed to start device code flow: {flow.get('error_description', flow)}"
            )

        print(flow["message"])

        result = self._public_app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise AuthError(
                f"Authentication failed: {result.get('error_description', result)}"
            )

        self._persist_cache()
        account = self._public_app.get_accounts()[0]
        print(f"Authenticated as: {account.get('username', '(unknown)')}")
        print(f"Token cache saved to: {self._cache_path}")

    def _persist_cache(self) -> None:
        if self._cache and self._cache.has_state_changed:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(self._cache.serialize())