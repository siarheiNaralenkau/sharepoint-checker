# Microsoft Entra ID App Registration Guide

This guide walks through registering an Entra ID (Azure AD) application for **sharepoint-checker** and granting it the permissions it needs to read SharePoint sites, document libraries, folders, and files across your Microsoft 365 tenant.

The tool uses **app-only authentication** (OAuth 2.0 client credentials flow). It never acts on behalf of a user — it authenticates as the application itself. This requires Application-type Graph permissions and Global/SharePoint admin consent.

---

## Prerequisites

- An active Microsoft 365 tenant with SharePoint Online.
- A user account that has one of the following roles:
  - **Global Administrator**, or
  - **Application Administrator** + **SharePoint Administrator** (to grant admin consent for SharePoint permissions).
- Access to the [Azure Portal](https://portal.azure.com) or [Microsoft Entra admin center](https://entra.microsoft.com).

---

## Step 1 — Create the App Registration

1. Open the [Microsoft Entra admin center](https://entra.microsoft.com) and sign in.
2. Navigate to **Identity → Applications → App registrations**.
3. Click **New registration**.
4. Fill in the form:
   - **Name**: `sharepoint-checker` (or any descriptive name)
   - **Supported account types**: `Accounts in this organizational directory only (Single tenant)`
   - **Redirect URI**: leave blank (not needed for app-only auth)
5. Click **Register**.

After registration you land on the app's **Overview** page. Keep this page open — you will copy values from it in Step 4.

---

## Step 2 — Collect Tenant ID and Client ID

From the **Overview** page, copy and save these two values:

| Value | Field on the Overview page | Config key |
|---|---|---|
| **Directory (tenant) ID** | `Directory (tenant) ID` | `tenant_id` in `checker-config.yaml` |
| **Application (client) ID** | `Application (client) ID` | `client_id` in `checker-config.yaml` |

---

## Step 3 — Configure a Credential

The tool supports two credential types. Choose **one**.

### Option A — Client Secret (simpler, suitable for dev/test)

1. In the left sidebar, go to **Certificates & secrets**.
2. Select the **Client secrets** tab and click **New client secret**.
3. Set a **Description** (e.g., `sp-checker-secret`) and choose an **Expiry** period.
   > Note the expiry date — rotate the secret before it expires to avoid downtime.
4. Click **Add**.
5. **Copy the secret Value immediately** — it is shown only once.
6. Store it in the environment variable `SP_CHECKER_CLIENT_SECRET` (see Step 5).

### Option B — Certificate (recommended for production)

Certificates do not expire on a fixed schedule and are more secure than secrets.

1. Generate a self-signed certificate or use one from your PKI:
   ```bash
   openssl req -x509 -newkey rsa:2048 -keyout sp-checker.key \
     -out sp-checker.crt -days 730 -nodes \
     -subj "/CN=sharepoint-checker"
   # Combine into PEM for MSAL
   cat sp-checker.key sp-checker.crt > sp-checker.pem
   ```
2. In the left sidebar, go to **Certificates & secrets → Certificates** tab.
3. Click **Upload certificate**, select `sp-checker.crt`, and click **Add**.
4. In `checker-config.yaml`, set `client_certificate_path` to the absolute path of `sp-checker.pem` and remove or leave blank `client_secret_env`.

---

## Step 4 — Grant API Permissions

The tool calls Microsoft Graph API with read-only access. It needs one Application permission.

1. In the left sidebar, go to **API permissions**.
2. Click **Add a permission → Microsoft Graph → Application permissions**.
3. Search for and select:

   | Permission | Type | Reason |
   |---|---|---|
   | `Sites.Read.All` | Application | Read all SharePoint site collections, their drives (document libraries), folders, and files |

4. Click **Add permissions**.
5. Click **Grant admin consent for \<your tenant\>** and confirm.

   The status column for `Sites.Read.All` must show a green **Granted for \<tenant\>** checkmark before the tool can authenticate.

   > **Why `Sites.Read.All` is sufficient**: this single permission covers all Graph endpoints the tool uses — site search (`/sites?search=…`), site enumeration (`/sites`), listing drives (`/sites/{id}/drives`), and browsing drive items (`/drives/{id}/…`). No write permissions are needed.

---

## Step 5 — Set Environment Variables

Set the following variables in the environment where `sp-checker` runs. Copy `.env.example` to `.env` and fill in the values (`.env` is git-ignored).

### Required

```bash
# Client secret (Option A only — omit if using a certificate)
SP_CHECKER_CLIENT_SECRET=<paste the secret value from Step 3A>
```

### Optional — Notifications

```bash
# Microsoft Teams incoming webhook URL
SP_CHECKER_TEAMS_WEBHOOK=https://<tenant>.webhook.office.com/webhookb2/...

# SMTP credentials for email notifications
SP_CHECKER_SMTP_USER=noreply@your-domain.com
SP_CHECKER_SMTP_PASSWORD=<smtp password>
```

To load the `.env` file before running the tool:

```bash
# Linux / macOS / Git Bash
export $(grep -v '^#' .env | xargs)

# PowerShell
Get-Content .env | Where-Object { $_ -notmatch '^#' } |
  ForEach-Object { $k,$v = $_ -split '=',2; [System.Environment]::SetEnvironmentVariable($k,$v) }
```

---

## Step 6 — Update checker-config.yaml

Open `config/checker-config.yaml` and fill in the values collected above:

```yaml
tenant_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # Directory (tenant) ID from Step 2
client_id: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"   # Application (client) ID from Step 2
client_secret_env: "SP_CHECKER_CLIENT_SECRET"        # env var name from Step 5 (Option A)

# --- Certificate auth (Option B) — uncomment and remove client_secret_env ---
# client_certificate_path: "/absolute/path/to/sp-checker.pem"
```

Leave all other settings at their defaults or adjust them for your environment.

---

## Step 7 — Verify the Setup

Run the built-in config validation and a dry run (site discovery only, no content read):

```bash
# 1. Validate the config file
sp-checker validate-config -c config/checker-config.yaml

# 2. Authenticate and discover sites (no SharePoint content is read)
sp-checker dry-run -c config/checker-config.yaml --log-level DEBUG
```

A successful dry run logs discovered site names and exits with code `0`. If authentication fails, the error message will indicate whether the problem is the secret, the tenant ID, or missing admin consent.

---

## Troubleshooting

| Error | Likely cause | Fix |
|---|---|---|
| `AADSTS700016: Application not found` | Wrong `tenant_id` or `client_id` | Re-copy both values from the Overview page |
| `AADSTS7000215: Invalid client secret` | Secret value is wrong or has expired | Rotate the secret in Entra ID, update the env var |
| `Token acquisition failed [invalid_client]` | Certificate path wrong or cert not uploaded to Entra | Verify `client_certificate_path` and the uploaded `.crt` |
| `GraphApiError 403 Forbidden` on `/sites` | Admin consent not granted | Return to **API permissions** and click **Grant admin consent** |
| `GraphApiError 403 Forbidden` on `/drives` | Permission granted but not yet propagated | Wait 1–2 minutes and retry; Entra propagation can be slow |
| `GraphApiError 404` on a specific site | App lacks access to that site's content | `Sites.Read.All` should cover all sites — verify consent was granted at tenant level, not just for one site |

---

## Security Notes

- **Least privilege**: `Sites.Read.All` gives read-only access to **all** site collections in the tenant. If you need to restrict access to specific sites only, use [SharePoint site-level app permissions](https://learn.microsoft.com/en-us/sharepoint/dev/solution-guidance/security-apponly-azureacs) instead of Graph application permissions — but this requires separate configuration per site and is not directly supported by this tool.
- **Secret rotation**: set a calendar reminder to rotate the client secret before its expiry date. Use certificates (Option B) in production to avoid manual rotation.
- **Secrets in CI/CD**: inject `SP_CHECKER_CLIENT_SECRET` as a masked secret variable (GitHub Actions secret, Azure DevOps variable group, etc.) — never hard-code it in config files or commit it to git.
- The `checker-config.yaml` file contains `tenant_id` and `client_id` which are **not** secrets, but avoid committing files that may contain actual secret values.
