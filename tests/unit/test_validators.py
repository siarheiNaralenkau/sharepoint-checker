import pytest
from sharepoint_checker.validators import FileValidator, FolderValidator, NamingValidator
from sharepoint_checker.models.result_models import CheckStatus


class TestNamingValidator:
    def setup_method(self):
        self.val = NamingValidator(r"^Project-[A-Za-z0-9]+-.+$")

    def test_valid_names(self):
        assert self.val.is_project_folder("Project-SAP-Leadership")
        assert self.val.is_project_folder("Project-ABC123-My Stream Name")

    def test_invalid_names(self):
        assert not self.val.is_project_folder("Documents")
        assert not self.val.is_project_folder("project-sap-lower")
        assert not self.val.is_project_folder("Project-")
        assert not self.val.is_project_folder("Project-NoStream")

    def test_filter(self):
        names = ["Project-SAP-Stream1", "Documents", "Project-MXG-Core", "Archive"]
        result = self.val.filter_project_folders(names)
        assert result == ["Project-SAP-Stream1", "Project-MXG-Core"]


class TestFolderValidator:
    def setup_method(self):
        self.val = FolderValidator(["Planning", "Risks", "Reports", "Architecture"])

    def test_all_present(self):
        result = self.val.validate(["Planning", "Risks", "Reports", "Architecture", "Extra"])
        assert result.status == CheckStatus.PASS
        assert result.missing_folders == []

    def test_some_missing(self):
        result = self.val.validate(["Planning", "Risks"])
        assert result.status == CheckStatus.FAIL
        assert "Reports" in result.missing_folders
        assert "Architecture" in result.missing_folders

    def test_all_missing(self):
        result = self.val.validate([])
        assert result.status == CheckStatus.FAIL
        assert len(result.missing_folders) == 4

    def test_case_insensitive(self):
        result = self.val.validate(["planning", "RISKS", "reports", "architecture"])
        assert result.status == CheckStatus.PASS


class TestFileValidator:
    def setup_method(self):
        self.val = FileValidator({
            "Planning": ["project-charter.docx", "roadmap.xlsx"],
            "Reports": ["weekly-status.xlsx"],
        })

    def test_all_files_present(self):
        contents = {
            "Planning": ["project-charter.docx", "roadmap.xlsx", "other.txt"],
            "Reports": ["weekly-status.xlsx"],
        }
        result = self.val.validate(contents)
        assert result.status == CheckStatus.PASS
        assert result.missing_files == []

    def test_some_files_missing(self):
        contents = {
            "Planning": ["project-charter.docx"],
            "Reports": [],
        }
        result = self.val.validate(contents)
        assert result.status == CheckStatus.FAIL
        assert "Planning/roadmap.xlsx" in result.missing_files
        assert "Reports/weekly-status.xlsx" in result.missing_files

    def test_folder_not_found_treated_as_empty(self):
        result = self.val.validate({})
        assert result.status == CheckStatus.FAIL
        assert len(result.missing_files) == 3

    def test_case_insensitive_filenames(self):
        contents = {
            "Planning": ["Project-Charter.DOCX", "Roadmap.XLSX"],
            "Reports": ["Weekly-Status.xlsx"],
        }
        result = self.val.validate(contents)
        assert result.status == CheckStatus.PASS
