# sharepoint-checker

A Python 3.12+ async CLI utility that validates SharePoint project folder structure across a Microsoft 365 tenant using the Microsoft Graph API.

## Architecture

```
src/sharepoint_checker/
├── cli.py                  # Typer CLI — entry point (sp-checker)
├── config.py               # YAML config loader
├── auth.py                 # MSAL app-only token provider
├── graph_client.py         # Async httpx Graph API client
├── site_discovery.py       # Tenant site enumeration
├── library_resolver.py     # Document library → drive ID
├── folder_scanner.py       # Recursive folder/file enumeration
├── models/                 # Pydantic v2 schemas (config + results)
├── validators/             # Naming, folder, file rule checkers
├── reporting/              # JSON, CSV, HTML, Teams, email outputs
├── orchestration/run_checker.py  # Core async orchestration
└── utils/                  # Logging, retry, regex helpers
```

Entry point: `sp-checker` → `sharepoint_checker.cli:app`

## Commands

```bash
sp-checker run -c config/checker-config.yaml          # full validation run
sp-checker validate-config -c config/checker-config.yaml
sp-checker dry-run -c config/checker-config.yaml      # site discovery only
sp-checker --version
```

## Development Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and fill in secrets before running.

## Running Tests

```bash
pytest                          # all unit tests
pytest tests/unit/              # unit tests only
pytest --cov=sharepoint_checker --cov-report=term-missing
```

Integration tests require a real Entra app registration and sandbox tenant — see `tests/integration/README.md`.

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `SP_CHECKER_CLIENT_SECRET` | Yes | Entra app client secret |
| `SP_CHECKER_TEAMS_WEBHOOK` | No | Teams incoming webhook URL |
| `SP_CHECKER_SMTP_PASSWORD` | No | SMTP password for email |

Never commit `.env` or real secrets.

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success / no validation failures |
| 1 | One or more validation failures found |
| 2 | Configuration error |
| 3 | Authentication error |
| 4 | Runtime / API error |

## Key Conventions

- All Graph API I/O is async (`asyncio` + `httpx`); keep orchestration and I/O layers async.
- Use `tenacity` for retry logic — see `utils/retry.py` for shared decorators.
- All config is validated via Pydantic v2 models in `models/config_models.py`; add new settings there, not ad-hoc.
- Secrets come from environment variables only — never from config files.
- Structured JSON logging via `utils/logging.py`; use `logging.getLogger(__name__)` in every module.
- New reporters go in `reporting/` and must accept a `RunSummary` object.
- New validators go in `validators/` and must return `CheckStatus` + detail strings.

## Dependency Management

Dependencies are managed in `pyproject.toml` (setuptools backend). Do not create a `requirements.txt`.

```bash
pip install -e ".[dev]"   # install with dev extras
```
