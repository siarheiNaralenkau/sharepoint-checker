# SharePoint Tenant Checker

A Python CLI utility that discovers SharePoint Online sites across a tenant, validates
project folder structures against configurable rules, and produces consolidated reports
delivered by email and/or Microsoft Teams.

## Features

- Tenant-wide site discovery via Microsoft Graph API (prefix or all-visible mode)
- Validates mandatory subfolders inside project folders matching a naming convention
- Validates mandatory files inside selected subfolders
- Generates JSON, CSV, and HTML reports
- Sends consolidated notifications to Microsoft Teams (webhook) and/or email
- Read-only, config-driven, deterministic
- Ready for migration to Azure Function (timer + HTTP triggers)

## Requirements

- Python 3.12+
- A Microsoft Entra ID app registration with delegated `Sites.Read.All` permission
- A Microsoft 365 account with access to the SharePoint sites you want to check

## Installation

```bash
python -m venv .venv
source .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Authentication Setup

The tool authenticates **as your Microsoft 365 account** using the Device Code Flow — fully
compatible with SSO and MFA. No passwords or client secrets are required.

**One-time setup** (follow [docs/entra-app-setup-delegated.md](docs/entra-app-setup-delegated.md)):

1. Register an app in Microsoft Entra ID and enable **Allow public client flows**.
2. Add the **delegated** permission `Sites.Read.All` and grant consent.
3. Set `tenant_id`, `client_id`, and `delegated_auth.token_cache_path` in your config file.
4. Run `sp-checker auth-login` once — authenticate in a browser with your Microsoft account and MFA. A refresh token is saved locally and reused silently on all subsequent runs.

Re-run `sp-checker auth-login` when the refresh token expires (~90 days, or as set by your tenant policy).

## Configuration

Copy the template and edit it:

```bash
cp config/checker-config.yaml config/my-config.yaml
```

Minimal configuration for delegated auth:

```yaml
tenant_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
client_id: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"

delegated_auth:
  token_cache_path: "~/.sp-checker-token-cache.json"

discovery:
  mode: "prefix"
  site_prefixes:
    - "MyProjectSites"

sharepoint:
  library_name: "Shared Documents"
  project_folder_regex: "^Project-[A-Za-z0-9]+-.+$"

rules:
  required_folders:
    - "Planning"
    - "Reports"
  required_files:
    Planning:
      - "project-charter.docx"
```

### All configuration fields

| Field | Description |
|---|---|
| `tenant_id` | Microsoft Entra Directory (tenant) ID |
| `client_id` | App registration Application (client) ID |
| `delegated_auth.token_cache_path` | Path where MSAL stores the refresh token (default: `~/.sp-checker-token-cache.json`) |
| `discovery.mode` | `prefix` — search by keyword; `all-visible` — enumerate all visible sites |
| `discovery.site_prefixes` | Site name prefixes to search for (used in `prefix` mode) |
| `discovery.include_site_url_patterns` | Regex patterns — only sites whose URL matches are included |
| `discovery.exclude_site_url_patterns` | Regex patterns — sites whose URL matches are skipped |
| `sharepoint.library_name` | Document library name (default: `Shared Documents`) |
| `sharepoint.root_folder` | Root folder path within the library (default: `/`) |
| `sharepoint.project_folder_regex` | Regex that project folder names must match |
| `rules.required_folders` | Subfolder names that must exist in every project folder |
| `rules.required_files` | Map of subfolder name → list of filenames that must exist |
| `execution.max_parallel_sites` | Number of sites processed concurrently (default: `4`) |
| `execution.page_size` | Graph API page size (default: `200`) |
| `reporting.output_dir` | Directory for report files (default: `./out`) |
| `reporting.formats` | Report formats to generate: `json`, `csv`, `html` |
| `reporting.teams.enabled` | Send summary to a Teams incoming webhook |
| `reporting.email.enabled` | Send summary by email |

## Environment Variables

No environment variables are required for the delegated auth flow. Optional variables for notifications:

```bash
# Microsoft Teams incoming webhook URL
export SP_CHECKER_TEAMS_WEBHOOK="https://your-tenant.webhook.office.com/webhookb2/..."

# SMTP credentials for email notifications
export SP_CHECKER_SMTP_USER="noreply@example.com"
export SP_CHECKER_SMTP_PASSWORD="smtp-password"
```

Copy `.env.example` to `.env` and populate it. Load it before running the tool:

```bash
export $(grep -v '^#' .env | xargs)
```

## Usage

### Authenticate (first time and after token expiry)

```bash
sp-checker auth-login --config config/my-config.yaml
```

The terminal prints a URL and a short code. Open the URL in a browser, enter the code, and
sign in with your Microsoft 365 account (including MFA approval). The refresh token is saved
to `delegated_auth.token_cache_path` and reused automatically on all future runs.

### Validate config

```bash
sp-checker validate-config --config config/my-config.yaml
```

### Dry run (site discovery only, no content read)

```bash
sp-checker dry-run --config config/my-config.yaml
```

### Full run

```bash
sp-checker run --config config/my-config.yaml
```

### Override output directory or site prefix

```bash
sp-checker run --config config/my-config.yaml \
  --output-dir ./reports \
  --site-prefix MyProjectSites
```

### Disable notifications for a single run

```bash
sp-checker run --config config/my-config.yaml --no-notify
```

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Completed — no validation failures |
| `1` | Completed — validation failures found |
| `2` | Configuration error |
| `3` | Authentication / authorization error — re-run `auth-login` if the token has expired |
| `4` | Runtime / system error |

## Output Files

Reports are written to `reporting.output_dir` (default `./out`):

- `run-summary.json` — full machine-readable inventory
- `run-summary.csv` — flat table, one row per project folder
- `run-summary.html` — human-readable HTML report

## Running Tests

```bash
pytest tests/unit/ -v
```

Integration tests require a real sandbox tenant — see [tests/integration/README.md](tests/integration/README.md).

## Project Structure

```
sharepoint-checker/
  src/sharepoint_checker/
    cli.py                  # CLI entry point (typer)
    config.py               # Config loader and validator
    auth.py                 # MSAL token provider (device code + app-only)
    graph_client.py         # Async Graph API client (httpx + tenacity)
    site_discovery.py       # Tenant-wide site discovery
    library_resolver.py     # Resolve document library drive ID
    folder_scanner.py       # Enumerate project folders and contents
    validators/
      naming_validator.py   # Project folder name regex filter
      folder_validator.py   # Required subfolder presence check
      file_validator.py     # Required file presence check
    models/
      config_models.py      # Pydantic config schema
      result_models.py      # Pydantic result/report schema
    reporting/
      json_report.py        # JSON output
      csv_report.py         # CSV output
      html_report.py        # HTML report (Jinja2)
      teams_notifier.py     # Microsoft Teams webhook notification
      email_notifier.py     # SMTP email notification
    orchestration/
      run_checker.py        # Main orchestration (asyncio)
    utils/
      logging.py            # Structured logging setup
      retry.py              # Retry helpers (tenacity)
      patterns.py           # Regex helpers
  config/
    checker-config.yaml     # Configuration template
  docs/
    entra-app-setup-delegated.md   # Entra ID app registration guide (delegated auth)
    entra-app-setup.md             # Entra ID app registration guide (app-only auth)
  tests/
    unit/                   # Unit tests (mocked Graph responses)
    integration/            # Integration tests (real tenant)
    fixtures/               # Shared Graph API response fixtures
```

## Migrating to Azure Function

The core orchestration in `run_checker.py` exposes a single `run_checker(config) -> RunSummary`
coroutine that is framework-agnostic. To wrap it:

**Timer trigger (weekly):**
```python
import azure.functions as func
from sharepoint_checker.config import load_config
from sharepoint_checker.orchestration.run_checker import run_checker

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 8 * * MON", arg_name="timer")
async def weekly_check(timer: func.TimerRequest) -> None:
    config = load_config("config/checker-config.yaml")
    await run_checker(config)
```

**HTTP trigger (manual):**
```python
@app.route(route="run-check", methods=["POST"])
async def http_check(req: func.HttpRequest) -> func.HttpResponse:
    config = load_config("config/checker-config.yaml")
    summary = await run_checker(config)
    return func.HttpResponse(summary.model_dump_json(), mimetype="application/json")
```

> For Azure Function deployments, use the app-only auth flow (client secret or certificate)
> instead of device code flow — a timer-triggered function cannot complete browser-based
> authentication. See [docs/entra-app-setup.md](docs/entra-app-setup.md) for setup instructions.
