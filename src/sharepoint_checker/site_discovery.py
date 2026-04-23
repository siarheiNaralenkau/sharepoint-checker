from __future__ import annotations

import logging

from .graph_client import GraphClient
from .models.config_models import DiscoveryConfig
from .models.result_models import DiscoveredSite

logger = logging.getLogger(__name__)

_SITE_FIELDS = "id,name,webUrl,displayName,siteCollection"


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
        logger.info("Discovered %d site(s)", len(sites))
        for site in sites:
            logger.info("  Site — displayName: %r  siteId: %s", site.display_name or site.site_name, site.site_id)
        return sites

    async def _discover_by_prefix(self) -> list[dict]:
        keywords = self._config.site_prefixes
        if not keywords:
            logger.warning("prefix mode configured but no site_prefixes — falling back to all-visible")
            return await self._discover_all()

        seen: dict[str, dict] = {}
        for keyword in keywords:
            logger.info("Searching sites with keyword %r", keyword)
            url = self._client.url("/sites")
            items = await self._client.get_paginated(url, {"search": keyword, "$select": _SITE_FIELDS})
            for item in items:
                seen[item["id"]] = item

        return list(seen.values())

    async def _discover_all(self) -> list[dict]:
        logger.info("Enumerating all visible sites")
        url = self._client.url("/sites")
        return await self._client.get_paginated(url, {"search": "*", "$select": _SITE_FIELDS})

    @staticmethod
    def _to_site(raw: dict) -> DiscoveredSite:
        return DiscoveredSite(
            site_id=raw["id"],
            site_name=raw.get("name", ""),
            site_url=raw.get("webUrl", ""),
            display_name=raw.get("displayName"),
        )
