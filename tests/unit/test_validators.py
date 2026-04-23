import pytest
from sharepoint_checker.validators import NamingValidator


class TestNamingValidator:
    def setup_method(self):
        self.val = NamingValidator(r"^Project SAP-[A-Za-z]+ leadership$")

    def test_valid_names(self):
        assert self.val.is_project_folder("Project SAP-MxG leadership")
        assert self.val.is_project_folder("Project SAP-CSD leadership")
        assert self.val.is_project_folder("Project SAP-AbCdEf leadership")

    def test_invalid_names(self):
        assert not self.val.is_project_folder("Documents")
        assert not self.val.is_project_folder("project SAP-MxG leadership")   # lowercase 'p'
        assert not self.val.is_project_folder("Project SAP- leadership")       # empty identifier
        assert not self.val.is_project_folder("Project SAP-MxG-leadership")   # dash instead of space

    def test_filter(self):
        names = ["Project SAP-MxG leadership", "Documents", "Project SAP-CSD leadership", "Archive"]
        result = self.val.filter_project_folders(names)
        assert result == ["Project SAP-MxG leadership", "Project SAP-CSD leadership"]
