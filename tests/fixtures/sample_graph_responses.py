"""Reusable Graph API response fixtures for unit tests."""

SITES_SEARCH_RESPONSE = {
    "value": [
        {
            "id": "epam.sharepoint.com,site1-guid,web1-guid",
            "name": "EPAMSAPSEProjects",
            "webUrl": "https://epam.sharepoint.com/sites/EPAMSAPSEProjects",
            "displayName": "EPAM SAP SE Projects",
        }
    ]
}

DRIVES_RESPONSE = {
    "value": [
        {"id": "drive1", "name": "Shared Documents", "driveType": "documentLibrary"},
        {"id": "drive2", "name": "Site Assets", "driveType": "documentLibrary"},
    ]
}

ROOT_CHILDREN_RESPONSE = {
    "value": [
        {"id": "folder1", "name": "Project-SAP-Leadership", "folder": {"childCount": 4}},
        {"id": "folder2", "name": "Project-MXG-Core", "folder": {"childCount": 2}},
        {"id": "doc1", "name": "readme.txt", "file": {}},
    ]
}

PROJECT_CHILDREN_FULL = {
    "value": [
        {"id": "pf1", "name": "Planning", "folder": {"childCount": 2}},
        {"id": "pf2", "name": "Risks", "folder": {"childCount": 0}},
        {"id": "pf3", "name": "Reports", "folder": {"childCount": 1}},
        {"id": "pf4", "name": "Architecture", "folder": {"childCount": 3}},
    ]
}

PROJECT_CHILDREN_MISSING_ARCH = {
    "value": [
        {"id": "pf1", "name": "Planning", "folder": {"childCount": 2}},
        {"id": "pf2", "name": "Risks", "folder": {"childCount": 0}},
        {"id": "pf3", "name": "Reports", "folder": {"childCount": 1}},
    ]
}

PLANNING_CHILDREN_FULL = {
    "value": [
        {"id": "f1", "name": "project-charter.docx", "file": {}},
        {"id": "f2", "name": "roadmap.xlsx", "file": {}},
    ]
}

PLANNING_CHILDREN_MISSING = {
    "value": [
        {"id": "f1", "name": "project-charter.docx", "file": {}},
    ]
}

REPORTS_CHILDREN_FULL = {
    "value": [
        {"id": "f3", "name": "weekly-status.xlsx", "file": {}},
        {"id": "f4", "name": "status-summary.pptx", "file": {}},
    ]
}
