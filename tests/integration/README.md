# Integration Tests

Integration tests require a real Microsoft Entra app registration with access to a
sandbox SharePoint Online tenant. They are **not** run in CI by default.

## Prerequisites

1. An Entra app registration with `Sites.Read.All` permission (application permission, admin-consented).
2. The following environment variables set:

```
SP_CHECKER_CLIENT_SECRET=<client-secret>
```

3. A `config/integration-config.yaml` pointing to your sandbox tenant and at least one
   test site with a known folder structure.

## Running

```bash
pytest tests/integration/ -v --tb=short
```

## Expected sandbox structure

| Site | Library | Project Folder | Expected outcome |
|------|---------|---------------|-----------------|
| EPAMSAPSEProjectsTest | Shared Documents | Project-SAP-Full | PASS |
| EPAMSAPSEProjectsTest | Shared Documents | Project-SAP-MissingFolders | FAIL (missing folders) |
| EPAMSAPSEProjectsTest | Shared Documents | Project-SAP-MissingFiles | FAIL (missing files) |
