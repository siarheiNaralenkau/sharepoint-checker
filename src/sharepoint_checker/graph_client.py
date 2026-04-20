from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from .auth import TokenProvider
from .utils.retry import GraphApiError, ThrottledError, build_retry_decorator

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    """Async Microsoft Graph API client with retry and pagination support."""

    def __init__(
        self,
        token_provider: TokenProvider,
        page_size: int = 200,
        retry_attempts: int = 5,
        retry_backoff_seconds: float = 2.0,
    ) -> None:
        self._token_provider = token_provider
        self._page_size = page_size
        self._retry = build_retry_decorator(retry_attempts, retry_backoff_seconds)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> GraphClient:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        token = self._token_provider.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "ConsistencyLevel": "eventual",
        }

    async def _raw_get(self, url: str, params: Optional[dict] = None) -> dict:
        assert self._client is not None, "GraphClient must be used as async context manager"
        logger.debug("GET %s params=%s", url, params)
        response = await self._client.get(url, headers=self._headers(), params=params)

        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", "30"))
            raise ThrottledError(retry_after)

        if response.status_code >= 400:
            try:
                body = response.json()
                message = body.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise GraphApiError(response.status_code, message)

        return response.json()

    async def get(self, url: str, params: Optional[dict] = None) -> dict:
        decorated = self._retry(self._raw_get)
        return await decorated(url, params)

    async def get_paginated(self, url: str, params: Optional[dict] = None) -> list[dict]:
        """Fetches all pages using @odata.nextLink."""
        all_items: list[dict] = []
        req_params = dict(params or {})
        req_params.setdefault("$top", self._page_size)

        next_url: Optional[str] = url
        first = True
        while next_url:
            data = await self.get(next_url, req_params if first else None)
            first = False
            all_items.extend(data.get("value", []))
            next_url = data.get("@odata.nextLink")

        return all_items

    # ------------------------------------------------------------------ helpers

    def url(self, path: str) -> str:
        return f"{GRAPH_BASE}{path}"
