from __future__ import annotations

from ..models.result_models import CheckStatus, FolderCheckResult


class FolderValidator:
    def __init__(self, required_folders: list[str]) -> None:
        self._required = required_folders

    def validate(self, found_names: list[str]) -> FolderCheckResult:
        found_set = {n.lower() for n in found_names}
        missing = [f for f in self._required if f.lower() not in found_set]
        status = CheckStatus.PASS if not missing else CheckStatus.FAIL
        return FolderCheckResult(
            status=status,
            required_folders=list(self._required),
            found_folders=found_names,
            missing_folders=missing,
        )
