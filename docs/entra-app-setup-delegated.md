# Microsoft Entra ID App Registration — Delegated Authentication (MFA-compatible)

This guide configures **sharepoint-checker** to authenticate as your own Microsoft 365 account using the **Device Code Flow**. It is fully compatible with SSO and MFA via Microsoft Authenticator — no password is required, and no MFA exemptions are needed.

## How it works

```
First run (once):
  sp-checker auth-login
    → prints a short code + URL
    → you open the URL, enter the code, approve in Authenticator
    → MSAL saves a refresh token to a local cache file

Every subsequent run:
  sp-checker run / dry-run
    → reads the cache file silently
    → exchanges the refresh token for a fresh access token
    → no browser, no phone prompt
```

The refresh token typically stays valid for **90 days** (EPAM tenant policy may differ). When it expires, re-run `sp-checker auth-login` once to refresh it.

## How this differs from app-only and ROPC

| | App-only | ROPC (password) | Device Code (this guide) |
|---|---|---|---|
| Identity | The app itself | Service account | Your Microsoft 365 account |
| MFA compatible | Yes (no user involved) | **No** | **Yes** |
| Admin consent needed | Global Admin | SharePoint Admin | User self-consent or SharePoint Admin |
| Sites accessible | All sites in tenant | Sites the service account can access | Sites your account can access |
| Re-authentication | Never (client secret) | Never (password in env) | Every ~90 days |

---

## Prerequisites

- Your Microsoft 365 account must have access to the SharePoint sites you want to check (Site Member or above).
- An account with the **Application Administrator** role in Entra ID to create the app registration. This can be a different person — your own account is only needed in Steps 6 and 8.

---

## Step 1 — Create the App Registration

1. Open the [Microsoft Entra admin center](https://entra.microsoft.com) and sign in with an Application Administrator account.
2. Navigate to **Identity → Applications → App registrations**.
3. Click **New registration**.
4. Fill in:
   - **Name**: `sharepoint-checker`
   - **Supported account types**: `Accounts in this organizational directory only (Single tenant)`
   - **Redirect URI**: leave blank
5. Click **Register**.

---

## Step 2 — Collect Tenant ID and Client ID

From the app's **Overview** page, copy:

| Value | Field | Config key |
|---|---|---|
| **Directory (tenant) ID** | `Directory (tenant) ID` | `tenant_id` in `checker-config.yaml` |
| **Application (client) ID** | `Application (client) ID` | `client_id` in `checker-config.yaml` |

---

## Step 3 — Enable Public Client Flows

Device Code Flow is a public client flow and must be explicitly enabled.

1. In the left sidebar, go to **Authentication**.
2. Scroll to **Advanced settings**.
3. Set **Allow public client flows** to **Yes**.
4. Click **Save**.

> No client secret or certificate is needed. The app is identified by its client ID alone.

---

## Step 4 — Grant Delegated API Permissions

1. In the left sidebar, go to **API permissions**.
2. Click **Add a permission → Microsoft Graph → Delegated permissions**.
3. Search for and select:

   | Permission | Type | Purpose |
   |---|---|---|
   | `Sites.Read.All` | Delegated | Read SharePoint sites, document libraries, folders, and files on behalf of the signed-in user |

4. Click **Add permissions**.

### Granting consent

With delegated permissions, consent can be granted in two ways — try Option A first:

**Option A — User self-consent**: If your tenant allows users to consent to read permissions, the consent prompt appears automatically the first time you run `sp-checker auth-login` (Step 8). You approve it in the browser during the device code flow. No admin involvement is needed.

**Option B — Admin consent**: If self-consent is blocked by tenant policy, click **Grant admin consent for \<tenant\>** on the API permissions page. For delegated permissions, a **SharePoint Administrator** or **Cloud Application Administrator** can grant this — a Global Administrator is not required.

After consent, the `Sites.Read.All` row must show a green **Granted for \<tenant\>** checkmark.

---

## Step 5 — Update checker-config.yaml

Open `config/checker-config.yaml` and set the IDs from Step 2. Remove or comment out any credential fields — no secret or password is needed:

```yaml
tenant_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # Directory (tenant) ID
client_id: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"   # Application (client) ID

# No client_secret_env or client_certificate_path needed for device code flow

delegated_auth:
  token_cache_path: "~/.sp-checker-token-cache.json"   # where MSAL stores the refresh token
```

> The token cache file contains your refresh token. Keep it out of git (add to `.gitignore` if stored inside the project directory).

---

## Step 6 — Apply the Code Changes

The current `auth.py` implements app-only flow. Replace it with the device code flow implementation below. The changes also touch `config_models.py` and `cli.py`.

### config_models.py — add `DelegatedAuthConfig`

```python
class DelegatedAuthConfig(BaseModel):
    token_cache_path: str = "~/.sp-checker-token-cache.json"


class CheckerConfig(BaseModel):
    tenant_id: str
    client_id: str
    client_secret_env: str = "SP_CHECKER_CLIENT_SECRET"   # kept for backward compat
    client_certificate_path: Optional[str] = None
    delegated_auth: Optional[DelegatedAuthConfig] = None   # None = use app-only flow
    # ... rest unchanged
```

### auth.py — device code flow with MSAL token cache

```python
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import msal

from .models.config_models import CheckerConfig

logger = logging.getLogger(__name__)

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
DELEGATED_SCOPES = ["https://graph.microsoft.com/Sites.Read.All"]


class AuthError(Exception):
    pass


class TokenProvider:
    def __init__(self, config: CheckerConfig) -> None:
        self._config = config

        if config.delegated_auth:
            self._cache_path = Path(config.delegated_auth.token_cache_path).expanduser()
            self._cache = msal.SerializableTokenCache()
            if self._cache_path.exists():
                self._cache.deserialize(self._cache_path.read_text())
            self._app: msal.ClientApplication = msal.PublicClientApplication(
                config.client_id,
                authority=f"https://login.microsoftonline.com/{config.tenant_id}",
                token_cache=self._cache,
            )
        else:
            self._cache = None
            self._app = self._build_confidential_app()

    # ------------------------------------------------------------------ app-only

    def _build_confidential_app(self) -> msal.ConfidentialClientApplication:
        authority = f"https://login.microsoftonline.com/{self._config.tenant_id}"
        if self._config.client_certificate_path:
            with open(self._config.client_certificate_path, "rb") as f:
                cert_data = f.read()
            return msal.ConfidentialClientApplication(
                self._config.client_id,
                authority=authority,
                client_credential={"private_key": cert_data},
            )
        secret_env = self._config.client_secret_env
        secret = os.environ.get(secret_env)
        if not secret:
            raise AuthError(
                f"Client secret not found in environment variable '{secret_env}'."
            )
        return msal.ConfidentialClientApplication(
            self._config.client_id,
            authority=authority,
            client_credential=secret,
        )

    # ------------------------------------------------------------------ token

    def get_token(self) -> str:
        if self._config.delegated_auth:
            return self._get_delegated_token()
        return self._get_app_only_token()

    def _get_app_only_token(self) -> str:
        result = self._app.acquire_token_for_client(scopes=GRAPH_SCOPE)
        if "access_token" not in result:
            error = result.get("error", "unknown")
            description = result.get("error_description", "No description")
            raise AuthError(f"Token acquisition failed [{error}]: {description}")
        return result["access_token"]

    def _get_delegated_token(self) -> str:
        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(
                scopes=DELEGATED_SCOPES,
                account=accounts[0],
            )
            if result and "access_token" in result:
                self._persist_cache()
                return result["access_token"]

        raise AuthError(
            "No valid token found in cache. "
            "Run 'sp-checker auth-login -c <config>' to authenticate."
        )

    # ------------------------------------------------------------------ login

    def login_device_code(self) -> None:
        """Interactive device code flow. Call once; saves the refresh token to disk."""
        flow = self._app.initiate_device_flow(scopes=DELEGATED_SCOPES)
        if "user_code" not in flow:
            raise AuthError(
                f"Failed to start device code flow: {flow.get('error_description', flow)}"
            )

        # Prints: "To sign in, use a web browser to open https://microsoft.com/devicelogin
        #          and enter the code XXXXXXXXX to authenticate."
        print(flow["message"])

        result = self._app.acquire_token_by_device_flow(flow)  # blocks until user authenticates
        if "access_token" not in result:
            raise AuthError(
                f"Authentication failed: {result.get('error_description', result)}"
            )

        self._persist_cache()
        account = self._app.get_accounts()[0]
        print(f"Authenticated as: {account.get('username', '(unknown)')}")
        print(f"Token cache saved to: {self._cache_path}")

    def _persist_cache(self) -> None:
        if self._cache and self._cache.has_state_changed:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(self._cache.serialize())
```

### cli.py — add the `auth-login` command

Add this command alongside the existing `run`, `validate-config`, and `dry-run` commands:

```python
@app.command(name="auth-login")
def auth_login(
    config_path: _CONFIG_OPT = Path("config/checker-config.yaml"),
) -> None:
    """Authenticate via device code flow (MFA-compatible). Run once to cache credentials."""
    configure_logging("WARNING")
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        typer.echo(f"[CONFIG ERROR] {exc}", err=True)
        raise typer.Exit(2)

    if not config.delegated_auth:
        typer.echo(
            "[ERROR] 'delegated_auth' is not configured in checker-config.yaml. "
            "Add the 'delegated_auth' section to use device code flow.",
            err=True,
        )
        raise typer.Exit(2)

    from .auth import AuthError, TokenProvider
    try:
        TokenProvider(config).login_device_code()
    except AuthError as exc:
        typer.echo(f"[AUTH ERROR] {exc}", err=True)
        raise typer.Exit(3)
```

---

## Step 7 — Protect the Token Cache

Add the cache file to `.gitignore`:

```
# Token cache (contains refresh token — never commit)
*.sp-checker-token-cache.json
.sp-checker-token-cache.json
```

On Unix/macOS, restrict file permissions after the first login:

```bash
chmod 600 ~/.sp-checker-token-cache.json
```

---

## Step 8 — Authenticate (First Time)

With the code changes applied and the config updated, run:

```bash
sp-checker auth-login -c config/checker-config.yaml
```

The terminal prints something like:

```
To sign in, use a web browser to open https://microsoft.com/devicelogin
and enter the code ABCD12345 to authenticate.
```

1. Open `https://microsoft.com/devicelogin` in any browser.
2. Enter the code shown in the terminal.
3. Sign in with your Microsoft 365 account.
4. Approve the MFA prompt in Microsoft Authenticator.
5. The terminal confirms: `Authenticated as: siarhei_naralenkau@epam.com` and saves the cache.

---

## Step 9 — Run the Tool

All subsequent invocations use the cached token silently:

```bash
sp-checker dry-run -c config/checker-config.yaml
sp-checker run -c config/checker-config.yaml
```

No browser interaction is needed until the refresh token expires.

---

## Token Expiry and Renewal

| Event | What happens | Action needed |
|---|---|---|
| Access token expires (~1 hour) | MSAL auto-renews using the refresh token | Nothing — fully transparent |
| Refresh token expires (~90 days) | `sp-checker run` prints the AUTH ERROR message | Re-run `sp-checker auth-login` |
| IT revokes your session | Same AUTH ERROR | Re-run `sp-checker auth-login` |
| You change your password / MFA device | Same AUTH ERROR | Re-run `sp-checker auth-login` |

> EPAM's tenant session policy may set a shorter refresh token lifetime than 90 days. If you notice frequent expiry, check with IT what the session lifetime is configured to.

---

## Scheduled / CI Runs

Device code flow requires a human to click once per refresh-token cycle. For scheduled automation:

1. Run `sp-checker auth-login` on your local machine to get a fresh cache file.
2. Base64-encode the cache and store it as a pipeline secret:
   ```bash
   # Encode
   base64 -w 0 ~/.sp-checker-token-cache.json > token_cache.b64
   # Paste the contents of token_cache.b64 into your CI secret (e.g. SP_CHECKER_TOKEN_CACHE)
   ```
3. In the CI job, decode the secret back to a file before running:
   ```bash
   echo "$SP_CHECKER_TOKEN_CACHE" | base64 -d > ~/.sp-checker-token-cache.json
   sp-checker run -c config/checker-config.yaml
   ```
4. Re-upload the secret when the refresh token expires (see table above).

---

## Troubleshooting

| Error | Likely cause | Fix |
|---|---|---|
| `No valid token found in cache` | Cache file missing or empty | Run `sp-checker auth-login` |
| `AADSTS70016: Pending…` timeout | You waited too long in the browser | Run `auth-login` again and authenticate within ~15 minutes |
| `AADSTS65001: No consent` | Permission was not consented | Grant consent in the portal (Step 4 Option B) |
| `AADSTS7000218: request must be confidential` | Public client flows not enabled | Set **Allow public client flows** to Yes (Step 3) |
| `GraphApiError 403` on `/sites` | Your account cannot access those sites | Ask a site owner to add your account as a Site Member |
| Sites missing from results | Your account is not a member of those sites | Same as above |
| Token expires in less than 90 days | Tenant session lifetime policy | Note the actual lifetime; re-run `auth-login` on that schedule |
