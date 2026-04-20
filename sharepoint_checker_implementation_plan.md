# SharePoint Tenant Checker - Implementation Plan

## 1. Goal
Build a Python command-line utility that:
- discovers SharePoint Online sites across the tenant by department prefix or scans all sites visible to the application,
- inspects project folders matching a naming convention such as `Project-${XYZ}-${StreamName}`,
- validates mandatory subfolders,
- validates mandatory files inside selected folders,
- produces a full pass/fail inventory for every checked site and folder,
- sends a consolidated report to email and/or Microsoft Teams,
- can later be wrapped with minimal changes into an Azure Function with timer and HTTP triggers.

---

## 2. Recommended target architecture

### 2.1 Runtime choice
- **Language:** Python 3.12+
- **Execution mode now:** CLI utility
- **Execution mode later:** Azure Function wrapper
- **Microsoft integration:** Microsoft Graph API
- **Auth model:** Microsoft Entra application registration using client credentials flow

This architecture is aligned with Microsoft Graph as the API surface for SharePoint sites and content, including site discovery and folder/file traversal. Microsoft Graph supports listing sites, searching sites, and listing folder children via drive items. Azure Functions supports both timer triggers and HTTP triggers for the future serverless migration.

### 2.2 High-level flow
1. Acquire app token from Microsoft Entra using client credentials.
2. Discover candidate sites across the tenant.
3. Filter sites by department prefix and optional include/exclude rules.
4. For each site:
   1. Resolve the target document library.
   2. Enumerate project folders under the configured root.
   3. Filter project folders by naming pattern.
   4. Validate required subfolders.
   5. Validate required files.
5. Aggregate all results into a full inventory.
6. Persist run outputs locally and optionally to storage.
7. Send consolidated report to email and/or Teams webhook/channel.
8. Exit with a deterministic status code.

---

## 3. Why this option is the right final choice

A Python CLI backed by Microsoft Graph is the best fit because the scope now includes **tenant-wide site discovery**, **multi-site iteration**, and **consolidated reporting**. Those requirements are significantly easier to model, test, and scale in code than in a large Power Automate flow. Microsoft Graph provides the primitives needed for both site discovery and content traversal, while the client credentials flow is the correct service-to-service authentication model for scheduled background execution. 

---

## 4. Functional requirements

### 4.1 Site discovery
The tool must support two discovery modes:
- `prefix` mode: discover only sites whose name, URL, or metadata matches a configured department prefix.
- `all-visible` mode: enumerate all sites visible to the application and then filter in code.

### 4.2 Folder validation
For each matching project folder:
- verify existence of all mandatory subfolders,
- list all missing mandatory folders,
- mark folder structure check as `PASS` only if none are missing.

### 4.3 File validation
For selected folders:
- verify existence of all mandatory files,
- allow exact filename match first,
- optionally support wildcard or regex later,
- list all missing mandatory files,
- mark file validation check as `PASS` only if none are missing.

### 4.4 Reporting
The tool must generate:
- full inventory per site and per project folder,
- per-project status,
- per-site summary,
- tenant-wide consolidated summary,
- machine-readable output (`json`),
- human-readable output (`html` and/or `csv`).

### 4.5 Invocation
The tool must support:
- manual local CLI execution,
- weekly scheduled execution from scheduler or CI,
- later migration to Azure Function timer trigger and HTTP trigger.

---

## 5. Non-functional requirements
- **Read-only operation** against SharePoint content.
- **Deterministic output** for the same input/configuration.
- **Config-driven rules** without code changes.
- **Structured logging** for troubleshooting.
- **Retry with backoff** for transient Graph/API failures.
- **Pagination support** for site and folder enumeration.
- **Bounded concurrency** to avoid unnecessary throttling.
- **Clear exit codes** for scheduler/automation integration.

---

## 6. Authentication and permissions

### 6.1 Auth model
Use **Microsoft Entra app registration** with **OAuth 2.0 client credentials flow**. This flow is designed for daemon/service-to-service scenarios where the application authenticates with its own identity rather than impersonating a user. citeturn582668search1turn582668search10

### 6.2 Graph permissions
For tenant-wide discovery and read-only checking, start with application permissions based on least privilege. The practical baseline is usually:
- `Sites.Read.All`

Microsoft Graph permissions guidance explicitly recommends requesting the least privileged permissions required. citeturn582668search0

### 6.3 Secret strategy
Recommended order:
1. certificate credential,
2. if certificate is not possible for the prototype, client secret stored in secure local env or secret store,
3. never commit credentials into source control.

### 6.4 Technical user note
Your requirement says “accessible by technical user”, but for the actual implementation a **service principal / app identity** is better than a human technical account for recurring execution. Keep the technical user only for validation, setup, and functional comparison if needed.

---

## 7. Microsoft Graph usage model

### 7.1 Site discovery APIs
Use one of the following:
- `GET /sites?$filter=siteCollection/root ne null` for root-level discovery where appropriate,
- `GET /sites` for organizational enumeration,
- `GET /sites?search={keyword}` for keyword-based site discovery.

Graph supports both listing and searching sites in the tenant. citeturn427329search0turn427329search1

### 7.2 Site content traversal
After resolving site IDs:
- resolve libraries/lists for the site,
- identify the target document library,
- use drive items to walk folder contents.

Graph supports listing site lists and listing folder children via drive items. citeturn427329search4turn427329search2

### 7.3 Core content APIs to implement
- site discovery
- list libraries for a site
- resolve drive or target list
- list root children
- list children of project folder
- resolve folder/file by path where needed

Graph supports retrieving drive items by path or ID and listing folder children. citeturn427329search10turn427329search2

---

## 8. Proposed project structure

```text
sharepoint-checker/
  README.md
  pyproject.toml
  .env.example
  config/
    checker-config.yaml
  src/sharepoint_checker/
    __init__.py
    cli.py
    config.py
    auth.py
    graph_client.py
    site_discovery.py
    library_resolver.py
    folder_scanner.py
    validators/
      __init__.py
      folder_validator.py
      file_validator.py
      naming_validator.py
    models/
      __init__.py
      config_models.py
      result_models.py
    reporting/
      __init__.py
      json_report.py
      csv_report.py
      html_report.py
      teams_notifier.py
      email_notifier.py
    orchestration/
      run_checker.py
    utils/
      logging.py
      retry.py
      patterns.py
  tests/
    unit/
    integration/
    fixtures/
```

---

## 9. Configuration model

Use YAML for readability and future non-developer maintainability.

Example:

```yaml
tenant_id: "<tenant-id>"
client_id: "<client-id>"
client_secret_env: "SP_CHECKER_CLIENT_SECRET"

discovery:
  mode: "prefix"            # prefix | all-visible
  site_prefixes:
    - "EPAMSAPSEProjects"
  search_keywords:
    - "EPAMSAPSEProjects"
  include_site_url_patterns:
    - "/sites/EPAMSAPSEProjects"
  exclude_site_url_patterns: []

sharepoint:
  library_name: "Shared Documents"
  root_folder: "/"
  project_folder_regex: "^Project-[A-Za-z0-9]+-.+$"

rules:
  required_folders:
    - "Planning"
    - "Risks"
    - "Reports"
    - "Architecture"
  required_files:
    Planning:
      - "project-charter.docx"
      - "roadmap.xlsx"
    Reports:
      - "weekly-status.xlsx"
      - "status-summary.pptx"

execution:
  max_parallel_sites: 4
  page_size: 200
  retry_attempts: 5
  retry_backoff_seconds: 2

reporting:
  output_dir: "./out"
  formats: ["json", "csv", "html"]
  only_failures_in_notification: false
  email:
    enabled: true
    recipients:
      - "pm@example.com"
  teams:
    enabled: true
    webhook_env: "SP_CHECKER_TEAMS_WEBHOOK"
```

---

## 10. Domain model

### 10.1 Core entities
- `DiscoveredSite`
- `ProjectFolder`
- `FolderCheckResult`
- `FileCheckResult`
- `ProjectCheckResult`
- `SiteCheckResult`
- `RunSummary`

### 10.2 Suggested result schema

```json
{
  "run_id": "2026-04-20T12:00:00Z",
  "site_name": "EPAMSAPSEProjectsCSDArea-ProjectSAP-MxGleadership",
  "site_url": "https://epam.sharepoint.com/sites/...",
  "library_name": "Shared Documents",
  "project_folder": "Project-SAP-MxG-leadership",
  "folder_check": {
    "status": "FAIL",
    "missing_folders": ["Architecture"]
  },
  "file_check": {
    "status": "FAIL",
    "missing_files": [
      "Planning/project-charter.docx",
      "Reports/weekly-status.xlsx"
    ]
  },
  "overall_status": "FAIL"
}
```

---

## 11. CLI contract

### 11.1 Commands
```bash
sp-checker run --config ./config/checker-config.yaml
sp-checker run --config ./config/checker-config.yaml --site-prefix EPAMSAPSEProjects
sp-checker run --config ./config/checker-config.yaml --output-dir ./out
sp-checker validate-config --config ./config/checker-config.yaml
sp-checker dry-run --config ./config/checker-config.yaml
```

### 11.2 Exit codes
- `0` = completed, no failures found
- `1` = completed, validation failures found
- `2` = configuration error
- `3` = authentication/authorization error
- `4` = runtime/system error

This makes the CLI easy to schedule and later easy to wrap in HTTP/timer function handlers.

---

## 12. Processing algorithm

### 12.1 End-to-end algorithm
1. Load and validate config.
2. Authenticate to Microsoft Graph.
3. Discover sites.
4. Filter candidate sites by prefix/pattern.
5. For each site:
   1. resolve target document library,
   2. enumerate root folder children,
   3. identify project folders by regex,
   4. for each project folder:
      - list child folders/files,
      - compare against required folders,
      - for configured folders, inspect file children,
      - collect missing items,
      - compute PASS/FAIL.
6. Aggregate all results into site-level and run-level summaries.
7. Write reports.
8. Send notifications.
9. Return exit code.

### 12.2 Concurrency strategy
- parallelize at **site level** only,
- keep project-folder checks within a site mostly sequential at first,
- use small worker pool, e.g. 3–5 concurrent sites,
- add backoff when Graph returns throttling or transient errors.

---

## 13. Reporting design

### 13.1 Output files per run
- `run-summary.json`
- `run-summary.csv`
- `run-summary.html`
- optional `failures-only.csv`

### 13.2 Notification strategy
**Teams/email body should contain:**
- run timestamp,
- number of sites checked,
- number of project folders checked,
- pass count,
- fail count,
- link or attachment to full report,
- top failing sites/projects.

### 13.3 HTML report sections
1. overall summary
2. site-by-site summary table
3. project folder details table
4. missing folders section
5. missing files section

---

## 14. Migration path to Azure Function

The CLI should be written so the core orchestration is not coupled to argparse or local filesystem assumptions.

### 14.1 Design rule
Create one core application service:
- `run_checker(config) -> RunSummary`

### 14.2 CLI wrapper
The CLI only:
- parses args,
- loads config,
- invokes `run_checker`,
- writes outputs,
- sets exit code.

### 14.3 Azure Function wrapper later
Add two thin wrappers:
- **Timer trigger** for weekly scheduled execution,
- **HTTP trigger** for manual execution by PM/admin fronted by Azure auth or internal gateway.

Azure Functions natively supports timer triggers and HTTP triggers, so this wrapping step should be straightforward if the orchestration logic remains framework-independent. 

---

## 15. Implementation phases

### Phase 0 - Preparation
- confirm tenant/app-registration ownership,
- obtain test site URLs,
- obtain sample folder structures,
- define exact mandatory folder/file rules,
- define recipient lists and Teams target.

### Phase 1 - Skeleton
- initialize Python project,
- add CLI skeleton,
- add config loader and validation,
- add structured logging,
- add Graph auth client.

### Phase 2 - Discovery and traversal
- implement site discovery,
- implement site filtering by prefix,
- implement library resolution,
- implement folder traversal,
- implement pagination support.

### Phase 3 - Validation engine
- implement naming filter,
- implement folder validation,
- implement file validation,
- implement result aggregation.

### Phase 4 - Reporting
- JSON output,
- CSV output,
- HTML report,
- email/Teams notification.

### Phase 5 - Hardening
- retries and backoff,
- throttling handling,
- concurrency tuning,
- config overrides,
- better diagnostics.

### Phase 6 - Operationalization
- scheduler integration,
- secrets hardening,
- packaging for internal use,
- Azure Function wrapper when needed.

---

## 16. Testing strategy

### 16.1 Unit tests
Mock Graph responses for:
- site discovery,
- folder trees,
- missing folders,
- missing files,
- empty sites,
- invalid config,
- throttling retry logic.

### 16.2 Integration tests
Against a sandbox SharePoint area:
- one site with fully valid structure,
- one site with missing folders,
- one site with missing files,
- one site with mixed project folders.

### 16.3 Non-functional tests
- paging over many sites,
- API throttling simulation,
- report generation on large inventories,
- notification fallback when Teams/email fails.

---

## 17. Operational considerations

### 17.1 Logging
Use structured logs with fields such as:
- run_id
- site_url
- site_id
- project_folder
- action
- outcome
- duration_ms
- retry_count

### 17.2 Idempotency
The checker is read-only and report-oriented, so multiple executions should not modify tenant content.

### 17.3 Performance
Start with conservative concurrency and measure:
- average sites scanned per minute,
- average project folders scanned per minute,
- Graph latency and retry counts,
- report generation time.

### 17.4 Failure isolation
A failure in one site should not abort the entire run unless authentication or configuration is invalid.

---

## 18. Key risks and mitigations

### Risk 1 - Permission overreach
**Risk:** broad app permissions may concern security review.
**Mitigation:** begin with read-only permissions, document exact scope, and justify why tenant-wide discovery requires broader visibility than `Sites.Selected` in this prototype.

### Risk 2 - Graph throttling
**Risk:** scanning many sites/folders can hit throttling.
**Mitigation:** bounded concurrency, retry with exponential backoff, caching of resolved site/library metadata.

### Risk 3 - Inconsistent site/library structures
**Risk:** not every site may contain the expected library/root.
**Mitigation:** report these as inventory findings, not hard failures.

### Risk 4 - Rule changes
**Risk:** more streams or departments introduce different templates.
**Mitigation:** keep rules externalized in YAML and support multiple profiles later.

### Risk 5 - Notification delivery issues
**Risk:** email/Teams delivery can fail independently from scanning.
**Mitigation:** store local artifacts first and treat notification as a separate step with its own status.

---

## 19. Deliverables

### Initial deliverables
- Python CLI utility
- YAML configuration file template
- README with local run instructions
- sample HTML/CSV/JSON report
- unit tests for validators and Graph client layer
- integration test checklist

### Optional next deliverables
- Dockerfile
- Azure Function wrapper
- SharePoint list persistence
- simple web dashboard

---

## 20. Recommended libraries

- `httpx` or `requests` for Graph HTTP calls
- `msal` for Microsoft identity token acquisition
- `pydantic` for config/result models
- `PyYAML` for YAML config
- `jinja2` for HTML report templating
- `tenacity` for retry logic
- `typer` or `click` for CLI
- `pytest` for tests

---

## 21. Definition of done for prototype

The prototype is complete when it can:
1. authenticate using app credentials,
2. discover tenant sites by prefix,
3. inspect the configured document library in each discovered site,
4. validate all project folders against fixed rules,
5. generate full pass/fail inventory,
6. produce JSON and CSV outputs,
7. send one consolidated notification,
8. run successfully from CLI with a single command.

---

## 22. Final recommendation

Build the first version as a **Python CLI using Microsoft Graph with app-only authentication**. Keep the orchestration logic framework-agnostic so the same core can later be wrapped with **Azure Function timer and HTTP triggers** for scheduled and manual execution. This gives the cleanest path for your current multi-site SharePoint Online validation use case while preserving a straightforward migration path to managed cloud execution. citeturn427329search0turn427329search1turn427329search2turn582668search1turn427329search3turn582668search2
