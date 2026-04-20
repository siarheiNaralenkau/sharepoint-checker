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
- Microsoft Entra app registration with `Sites.Read.All` application permission (admin-consented)

## Installation

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install the package
pip install -e ".[dev]"
```

## Configuration

Copy and edit the example configuration:

```bash
cp config/checker-config.yaml config/my-config.yaml
```

Key fields:

| Field | Description |
|-------|-------------|
| `tenant_id` | Microsoft Entra tenant ID |
| `client_id` | App registration client ID |
| `client_secret_env` | Name of env var holding the client secret |
| `discovery.mode` | `prefix` (search by keyword) or `all-visible` |
| `discovery.site_prefixes` | Site name prefixes to search for |
| `sharepoint.library_name` | Document library name (default: `Shared Documents`) |
| `sharepoint.project_folder_regex` | Regex that matches project folder names |
| `rules.required_folders` | List of mandatory subfolder names |
| `rules.required_files` | Map of folder → list of mandatory filenames |
| `reporting.formats` | Output formats: `json`, `csv`, `html` |
| `reporting.teams.enabled` | Enable Teams webhook notification |
| `reporting.email.enabled` | Enable email notification |

## Environment Variables

```bash
# Required — client secret for app registration
export SP_CHECKER_CLIENT_SECRET="your-secret-here"

# Optional — Teams incoming webhook
export SP_CHECKER_TEAMS_WEBHOOK="https://..."

# Optional — SMTP credentials for email
export SP_CHECKER_SMTP_USER="noreply@example.com"
export SP_CHECKER_SMTP_PASSWORD="smtp-password"
```

Or copy `.env.example` to `.env` and populate it (use a tool like `direnv` or `dotenv`).

## Usage

### Validate config

```bash
sp-checker validate-config --config config/checker-config.yaml
```

### Dry run (site discovery only, no content read)

```bash
sp-checker dry-run --config config/checker-config.yaml
```

### Full run

```bash
sp-checker run --config config/checker-config.yaml
```

### Override output directory or site prefix

```bash
sp-checker run --config config/checker-config.yaml \
  --output-dir ./reports \
  --site-prefix EPAMSAPSEProjects
```

### Disable notifications for a single run

```bash
sp-checker run --config config/checker-config.yaml --no-notify
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0`  | Completed — no validation failures |
| `1`  | Completed — validation failures found |
| `2`  | Configuration error |
| `3`  | Authentication / authorization error |
| `4`  | Runtime / system error |

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
    auth.py                 # MSAL token provider
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
  tests/
    unit/                   # Unit tests (mocked Graph responses)
    integration/            # Integration tests (real tenant)
    fixtures/               # Shared Graph API response fixtures
```

## Migrating to Azure Function

The core orchestration in `run_checker.py` exposes a single `run_checker(config) -> RunSummary` coroutine that is framework-agnostic. To wrap it:

**Timer trigger (weekly):**
```python
import azure.functions as func
import asyncio
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

## Authentication Setup

1. Register an application in Microsoft Entra (Azure AD).
2. Add the **application permission** `Sites.Read.All` (not delegated).
3. Grant admin consent for the permission.
4. Create a client secret (or upload a certificate for production).
5. Set `tenant_id` and `client_id` in config; put the secret in `SP_CHECKER_CLIENT_SECRET`.

> For production, prefer a **certificate credential** over a client secret. Set
> `client_certificate_path` in the config and omit `client_secret_env`.
