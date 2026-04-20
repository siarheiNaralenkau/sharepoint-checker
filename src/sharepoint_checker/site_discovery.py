from __future__ import annotations

import logging
from typing import AsyncIterator

from .graph_client import GraphClient
from .models.config_models import DiscoveryConfig
from .models.result_models import DiscoveredSite
from .utils.patterns import matches_any

logger = logging.getLogger(__name__)


class SiteDiscovery:
    def __init__(self, client: GraphClient, config: DiscoveryConfig) -> None:
        self._client = client
        self._config = config

    async def discover(self) -> list[DiscoveredSite]:
        mode = self._config.mode
        if mode == "prefix":
            raw = await self._discover_by_prefix()
        elif mode == "all-visible":
            raw = await self._discover_all()
        else:
            raise ValueError(f"Unknown discovery mode: {mode!r}")

        sites = [self._to_site(s) for s in raw]
        sites = self._apply_filters(sites)
        logger.info("Discovered %d site(s) after filtering", len(sites))
        return sites

    async def _discover_by_prefix(self) -> list[dict]:
        keywords = self._config.search_keywords or self._config.site_prefixes
        if not keywords:
            logger.warning("prefix mode configured but no keywords/prefixes — falling back to all-visible")
            return await self._discover_all()

        seen: dict[str, dict] = {}
        for keyword in keywords:
            logger.info("Searching sites with keyword %r", keyword)
            url = self._client.url("/sites")
            items = await self._client.get_paginated(url, {"search": keyword})
            for item in items:
                seen[item["id"]] = item

        return list(seen.values())

    async def _discover_all(self) -> list[dict]:
        logger.info("Enumerating all visible sites")
        url = self._client.url("/sites")
        return await self._client.get_paginated(url, {"$filter": "siteCollection/root ne null"})

    def _apply_filters(self, sites: list[DiscoveredSite]) -> list[DiscoveredSite]:
        include = self._config.include_site_url_patterns
        exclude = self._config.exclude_site_url_patterns

        filtered: list[DiscoveredSite] = []
        for site in sites:
            if exclude and matches_any(site.site_url, exclude):
                logger.debug("Excluding site %s (matched exclude pattern)", site.site_url)
                continue
            if include and not matches_any(site.site_url, include):
                logger.debug("Skipping site %s (no include pattern matched)", site.site_url)
                continue
            filtered.append(site)

        return filtered

    @staticmethod
    def _to_site(raw: dict) -> DiscoveredSite:
        return DiscoveredSite(
            site_id=raw["id"],
            site_name=raw.get("name", ""),
            site_url=raw.get("webUrl", ""),
            display_name=raw.get("displayName"),
        )
