from __future__ import annotations

import logging
from typing import Optional

from .graph_client import GraphClient

logger = logging.getLogger(__name__)


class LibraryNotFoundError(Exception):
    pass


class LibraryResolver:
    def __init__(self, client: GraphClient) -> None:
        self._client = client

    async def resolve_drive_id(self, site_id: str, library_name: str) -> str:
        """Returns the drive ID for the named document library within the site."""
        url = self._client.url(f"/sites/{site_id}/drives")
        drives = await self._client.get_paginated(url)
        logger.debug("Site %s has %d drive(s)", site_id, len(drives))

        for drive in drives:
            if drive.get("name", "").lower() == library_name.lower():
                drive_id = drive["id"]
                logger.debug("Resolved library %r -> drive %s", library_name, drive_id)
                return drive_id

        available = [d.get("name", "?") for d in drives]
        raise LibraryNotFoundError(
            f"Library {library_name!r} not found in site {site_id}. "
            f"Available: {available}"
        )
