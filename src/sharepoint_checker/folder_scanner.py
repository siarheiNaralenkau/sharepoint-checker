from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from .graph_client import GraphClient

logger = logging.getLogger(__name__)


@dataclass
class DriveItem:
    item_id: str
    name: str
    is_folder: bool
    parent_path: str = ""
    web_url: str = ""

    @property
    def full_path(self) -> str:
        return f"{self.parent_path}/{self.name}".lstrip("/")


class FolderScanner:
    def __init__(self, client: GraphClient) -> None:
        self._client = client

    async def list_root_folders(self, drive_id: str, root_folder: str = "/") -> list[DriveItem]:
        """Lists immediate children of the root folder, returning folders only."""
        if root_folder.strip("/") == "":
            url = self._client.url(f"/drives/{drive_id}/root/children")
        else:
            path = root_folder.strip("/")
            url = self._client.url(f"/drives/{drive_id}/root:/{path}:/children")

        items = await self._client.get_paginated(url, {"$select": "id,name,folder,file,webUrl"})
        return [self._to_item(i, "") for i in items if "folder" in i]

    async def list_folder_children(
        self, drive_id: str, folder_id: str, parent_path: str = ""
    ) -> list[DriveItem]:
        """Lists immediate children (folders and files) of a folder."""
        url = self._client.url(f"/drives/{drive_id}/items/{folder_id}/children")
        items = await self._client.get_paginated(url, {"$select": "id,name,folder,file"})
        return [self._to_item(i, parent_path) for i in items]

    async def list_subfolder_children(
        self, drive_id: str, project_folder_id: str, subfolder_name: str, project_path: str
    ) -> list[DriveItem]:
        """Lists children of a named subfolder inside a project folder."""
        url = self._client.url(
            f"/drives/{drive_id}/items/{project_folder_id}:/{subfolder_name}:/children"
        )
        try:
            items = await self._client.get_paginated(url, {"$select": "id,name,folder,file"})
        except Exception as exc:
            logger.debug("Could not list %s/%s: %s", project_path, subfolder_name, exc)
            return []

        parent = f"{project_path}/{subfolder_name}"
        return [self._to_item(i, parent) for i in items]

    @staticmethod
    def _to_item(raw: dict, parent_path: str) -> DriveItem:
        return DriveItem(
            item_id=raw["id"],
            name=raw["name"],
            is_folder="folder" in raw,
            parent_path=parent_path,
            web_url=raw.get("webUrl", ""),
        )
