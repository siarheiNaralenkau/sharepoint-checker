# Microsoft Graph API — Postman Request Examples

This document lists every HTTP request the application generates during a normal run,
with real response shapes, so each one can be reproduced and tested independently in Postman.

All requests go to `https://graph.microsoft.com/v1.0`.

---

## Authentication

Every request requires a bearer token in the `Authorization` header.

### Get a token via Postman OAuth 2.0

In Postman → **Authorization** tab:

| Field | Value |
|---|---|
| Type | OAuth 2.0 |
| Grant Type | Authorization Code (with PKCE) |
| Auth URL | `https://login.microsoftonline.com/<tenant_id>/oauth2/v2.0/authorize` |
| Token URL | `https://login.microsoftonline.com/<tenant_id>/oauth2/v2.0/token` |
| Client ID | `<client_id>` |
| Scope | `https://graph.microsoft.com/Sites.Read.All` |
| Code Challenge Method | SHA-256 |
| Callback URL | `https://oauth.pstmn.io/v1/browser-callback` |

> Add `https://oauth.pstmn.io/v1/browser-callback` as a Redirect URI on the app registration
> (**Entra admin center → Authentication → Add a platform → Web**) before using this.

### Get a token from the MSAL cache file

Open `~/.sp-checker-token-cache.json` and copy the JWT from the `"secret"` field
under `"AccessToken"`. Tokens are valid for ~1 hour.

```json
{
  "AccessToken": {
    "some-key": {
      "secret": "eyJ0eXAiOiJKV1Qi..."
    }
  }
}
```

Use this value as `Bearer <secret>` in the Authorization header.

---

## Common headers (all requests)

```
Authorization: Bearer <access_token>
Accept: application/json
ConsistencyLevel: eventual
```

---

## 1. Site Discovery

### 1a. Enumerate all visible sites (`mode: all-visible`)

```
GET https://graph.microsoft.com/v1.0/sites?search=*&$select=id,name,webUrl,displayName,siteCollection&$top=200
```

**Response shape:**

```json
{
  "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#sites",
  "@odata.nextLink": "https://graph.microsoft.com/v1.0/sites?search=*&$select=id,name,webUrl,displayName,siteCollection&$top=200&$skiptoken=s!MTA7...",
  "value": [
    {
      "createdDateTime": "2020-06-02T16:54:53Z",
      "description": "This is the default global community for everyone in the EPAM network.",
      "id": "epam.sharepoint.com,1cd1bfee-ad2a-46b9-bb03-503d0f2c0204,80b4b20d-031a-4332-9e45-a5e7a0f05dec",
      "lastModifiedDateTime": "2023-09-21T15:49:44Z",
      "name": "",
      "displayName": "EPAM All Company",
      "webUrl": "https://epam.sharepoint.com/sites/EPAMAllCompany",
      "root": {},
      "siteCollection": {
        "hostname": "epam.sharepoint.com"
      }
    }
  ]
}
```

> **Note:** Without `$select`, the search endpoint omits `webUrl`. The `$select` parameter is
> required to get it. The `name` field is consistently empty for root site collections —
> use `displayName` for identification and filtering.

If `@odata.nextLink` is present in the response, the application issues a second GET to that
URL automatically (pagination loop) until all pages are consumed.

---

### 1b. Search by keyword (`mode: prefix`)

Issued once per entry in `discovery.site_prefixes`.

```
GET https://graph.microsoft.com/v1.0/sites?search=EPAM+SAP&$select=id,name,webUrl,displayName,siteCollection&$top=200
```

Response shape is identical to 1a.

---

## 2. Resolve Document Library

Issued once per discovered site to find the drive ID for `sharepoint.library_name`.

```
GET https://graph.microsoft.com/v1.0/sites/<site_id>/drives?$top=200
```

**Example site_id:** `epam.sharepoint.com,1cd1bfee-ad2a-46b9-bb03-503d0f2c0204,80b4b20d-031a-4332-9e45-a5e7a0f05dec`

**Response shape:**

```json
{
  "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#drives",
  "value": [
    {
      "createdDateTime": "2020-06-02T16:54:53Z",
      "description": "",
      "id": "b!7r_RHCqtmUawA1A9DywCBg2ysFAaA...",
      "lastModifiedDateTime": "2026-04-21T15:06:39Z",
      "name": "Shared Documents",
      "webUrl": "https://epam.sharepoint.com/sites/EPAMSAPSEProjects/Shared%20Documents",
      "driveType": "documentLibrary",
      "owner": { "user": { "displayName": "SharePoint App" } }
    }
  ]
}
```

The application matches the drive by `name` (case-insensitive) against `sharepoint.library_name`
from config (default: `"Shared Documents"`). The `id` of the matched drive is used in all
subsequent file/folder requests.

---

## 3. List Root Folder Children

Lists immediate children of the configured `sharepoint.root_folder` (default `/`).

### Root of the drive

```
GET https://graph.microsoft.com/v1.0/drives/<drive_id>/root/children?$select=id,name,folder,file&$top=200
```

### Specific sub-path (when `root_folder` is not `/`)

```
GET https://graph.microsoft.com/v1.0/drives/<drive_id>/root:/<root_folder_path>:/children?$select=id,name,folder,file&$top=200
```

**Example drive_id:** `b!7r_RHCqtmUawA1A9DywCBg2ysFAaA...`

**Response shape:**

```json
{
  "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#drives('<drive_id>')/items",
  "value": [
    {
      "createdDateTime": "2022-01-10T09:00:00Z",
      "id": "01ABCDEF1234567890ABCDEF",
      "lastModifiedDateTime": "2026-04-20T12:00:00Z",
      "name": "Project-SAP-Alpha",
      "folder": { "childCount": 5 }
    },
    {
      "id": "01ABCDEF1234567890ABCDE0",
      "name": "README.md",
      "file": { "mimeType": "text/plain" }
    }
  ]
}
```

Only items containing the `"folder"` key are treated as project folders. Items with `"file"` are ignored at this level.

---

## 4. List Project Folder Children

Issued for each project folder to check for required subfolders and files.

```
GET https://graph.microsoft.com/v1.0/drives/<drive_id>/items/<project_folder_id>/children?$select=id,name,folder,file&$top=200
```

Response shape is identical to §3.

---

## 5. List Subfolder Children

Issued for each required subfolder (from `rules.required_files`) to check for mandatory files.

```
GET https://graph.microsoft.com/v1.0/drives/<drive_id>/items/<project_folder_id>:/<subfolder_name>:/children?$select=id,name,folder,file&$top=200
```

**Example subfolder_name:** `Planning`

**Response shape:**

```json
{
  "value": [
    {
      "id": "01ABCDEF...",
      "name": "project-charter.docx",
      "file": { "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }
    },
    {
      "id": "01ABCDEF...",
      "name": "roadmap.xlsx",
      "file": { "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }
    }
  ]
}
```

A 404 response from this endpoint means the subfolder does not exist — the application
records it as a missing-subfolder failure rather than raising an error.

---

## Full request sequence for one site

```
1.  GET /sites?search=EPAM+SAP+SE&$select=id,name,webUrl,displayName,siteCollection&$top=200
        → discover sites by keyword

1b. GET /sites/<site_id>?$select=id,webUrl          [only if webUrl was missing in step 1]
        → resolve missing site URL (see §6 below)

2.  GET /sites/<site_id>/drives?$top=200
        → find the default drive ID

3.  GET /drives/<drive_id>/root/children?$select=id,name,folder,file&$top=200
        → list root; find leadership folder by regex

4.  GET /drives/<drive_id>/items/<leadership_folder_id>/children?$select=id,name,folder,file&$top=200
        → check non-empty; find Roster subfolder

5.  GET /drives/<drive_id>/items/<roster_folder_id>/children?$select=id,name,folder,file&$top=200
        → verify at least one file
```

Steps 2–5 are repeated in parallel (up to `execution.max_parallel_sites` sites at a time).

---

## 6. Resolving the SharePoint Site URL

### The problem

The Graph `/sites?search=` endpoint does **not** reliably return `webUrl` even when it is
explicitly included in `$select`. The field is simply absent from the response object:

```json
{
  "id": "epam.sharepoint.com,52129f7d-...,b3e5aca0-...",
  "name": "",
  "displayName": "EPAM SAP SE Projects, CSD Area-Project SAP-WTF leadership",
  "siteCollection": { "hostname": "epam.sharepoint.com" }
}
```

This is a known Graph API behaviour: the search index does not always expose `webUrl`.

### Fix — direct site lookup by ID

When `webUrl` is missing after the search, fetch it with a direct GET using the site ID:

```
GET https://graph.microsoft.com/v1.0/sites/<site_id>?$select=id,webUrl
```

**Example site_id:**
`epam.sharepoint.com,52129f7d-bff1-4e07-a73f-2b5496970d0f,b3e5aca0-8b46-4747-b70c-44d5c3ddc960`

**Response shape:**

```json
{
  "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#sites(id,webUrl)/$entity",
  "id": "epam.sharepoint.com,52129f7d-bff1-4e07-a73f-2b5496970d0f,b3e5aca0-8b46-4747-b70c-44d5c3ddc960",
  "webUrl": "https://epam.sharepoint.com/sites/EPAMSAPSEProjectsCSDArea-ProjectSAP-WTFleadership"
}
```

This endpoint **always** returns `webUrl` for any site the authenticated user can access.

### All fields for a site

To see every available field, omit `$select`:

```
GET https://graph.microsoft.com/v1.0/sites/<site_id>
```

**Response includes:**

| Field | Example value |
|---|---|
| `id` | `epam.sharepoint.com,52129f7d-...,b3e5aca0-...` |
| `displayName` | `EPAM SAP SE Projects, CSD Area-Project SAP-WTF leadership` |
| `name` | `EPAMSAPSEProjectsCSDArea-ProjectSAP-WTFleadership` |
| `webUrl` | `https://epam.sharepoint.com/sites/EPAMSAPSEProjectsCSDArea-ProjectSAP-WTFleadership` |
| `createdDateTime` | `2023-01-15T09:00:00Z` |
| `lastModifiedDateTime` | `2026-04-20T14:32:00Z` |

### Postman collection — three useful requests

#### 6a. Search (may omit webUrl)

```
GET https://graph.microsoft.com/v1.0/sites?search=EPAM+SAP+SE&$select=id,name,webUrl,displayName,siteCollection&$top=200
```

Use this to get site IDs. Copy an `id` value from the response for the requests below.

#### 6b. Resolve URL by site ID

```
GET https://graph.microsoft.com/v1.0/sites/epam.sharepoint.com,52129f7d-bff1-4e07-a73f-2b5496970d0f,b3e5aca0-8b46-4747-b70c-44d5c3ddc960?$select=id,webUrl
```

Paste the full site ID (including the hostname and both GUIDs) into the URL. Returns `webUrl`.

#### 6c. Full site details

```
GET https://graph.microsoft.com/v1.0/sites/epam.sharepoint.com,52129f7d-bff1-4e07-a73f-2b5496970d0f,b3e5aca0-8b46-4747-b70c-44d5c3ddc960
```

Returns all site metadata — useful for exploring what fields the API exposes.

> **Note on site ID format:** Graph site IDs always follow the pattern
> `<hostname>,<site-collection-guid>,<web-guid>`. All three parts separated by commas
> are required when using the ID directly in a URL path.
