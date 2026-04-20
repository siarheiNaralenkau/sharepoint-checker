from __future__ import annotations

from ..models.result_models import CheckStatus, FileCheckResult


class FileValidator:
    def __init__(self, required_files: dict[str, list[str]]) -> None:
        self._required = required_files

    def validate(self, folder_contents: dict[str, list[str]]) -> FileCheckResult:
        """
        folder_contents: mapping of folder_name -> list of file names found.
        Checks only folders listed in required_files config.
        """
        all_missing: list[str] = []

        for folder, required in self._required.items():
            found_names = {n.lower() for n in folder_contents.get(folder, [])}
            for filename in required:
                if filename.lower() not in found_names:
                    all_missing.append(f"{folder}/{filename}")

        status = CheckStatus.PASS if not all_missing else CheckStatus.FAIL
        return FileCheckResult(status=status, missing_files=all_missing)
