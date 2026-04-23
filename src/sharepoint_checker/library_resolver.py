from __future__ import annotations

import logging

from .graph_client import GraphClient

logger = logging.getLogger(__name__)


class NoDriveFoundError(Exception):
    pass


class DriveResolver:
    def __init__(self, client: GraphClient) -> None:
        self._client = client

    async def get_first_drive_id(self, site_id: str) -> str:
        """Returns the ID of the first drive found for the site."""
        url = self._client.url(f"/sites/{site_id}/drives")
        drives = await self._client.get_paginated(url)
        logger.debug("Site %s has %d drive(s)", site_id, len(drives))

        if not drives:
            raise NoDriveFoundError(f"No drives found for site {site_id}")

        drive_id = drives[0]["id"]
        logger.debug("Using drive %r -> %s", drives[0].get("name", "?"), drive_id)
        return drive_id
