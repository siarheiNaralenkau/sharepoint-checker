from __future__ import annotations

import asyncio
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

        # The Graph search endpoint sometimes omits webUrl even when requested via $select.
        # For any site where it is missing, fall back to a direct GET /sites/<id>.
        sites = await self._resolve_missing_urls(sites)

        logger.info("Discovered %d site(s)", len(sites))
        for site in sites:
            logger.info("  Site — %r  url: %s", site.display_name or site.site_name, site.site_url or "(no url)")
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

    async def _resolve_missing_urls(self, sites: list[DiscoveredSite]) -> list[DiscoveredSite]:
        """Fetches webUrl from GET /sites/<id> for any site where the search did not return it."""
        to_resolve = [s for s in sites if not s.site_url]
        if not to_resolve:
            return sites

        logger.info("Resolving missing webUrl for %d site(s) via direct lookup", len(to_resolve))

        async def resolve_one(site: DiscoveredSite) -> DiscoveredSite:
            try:
                url = self._client.url(f"/sites/{site.site_id}")
                data = await self._client.get(url, {"$select": "id,webUrl"})
                web_url = data.get("webUrl", "")
                if web_url:
                    logger.debug("Resolved webUrl for %r -> %s", site.display_name or site.site_id, web_url)
                    return site.model_copy(update={"site_url": web_url})
            except Exception as exc:
                logger.warning("Could not resolve webUrl for %s: %s", site.site_id, exc)
            return site

        resolved = await asyncio.gather(*[resolve_one(s) for s in to_resolve])
        resolved_map = {s.site_id: s for s in resolved}
        return [resolved_map.get(s.site_id, s) for s in sites]

    @staticmethod
    def _to_site(raw: dict) -> DiscoveredSite:
        return DiscoveredSite(
            site_id=raw["id"],
            site_name=raw.get("name", ""),
            site_url=raw.get("webUrl", ""),
            display_name=raw.get("displayName"),
        )
