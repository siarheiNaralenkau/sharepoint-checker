from __future__ import annotations

from ..utils.patterns import is_project_folder


class NamingValidator:
    def __init__(self, regex: str) -> None:
        self._regex = regex

    def is_project_folder(self, name: str) -> bool:
        return is_project_folder(name, self._regex)

    def filter_project_folders(self, names: list[str]) -> list[str]:
        return [n for n in names if self.is_project_folder(n)]
