# SharePoint Checker — Validation Flow

This document describes the complete discovery and validation logic executed during
`sp-checker run`. Every step maps to one or more Microsoft Graph API requests and a
clear pass/fail decision.

---

## Overview

The checker works site-by-site. Each site is processed independently (up to
`execution.max_parallel_sites` concurrently) and produces a single
`SiteCheckResult` with an `overall_status` of **PASS** or **FAIL**.

```
for each discovered site:
  1. Resolve drive
  2. Find leadership folder (regex match at root level)
  3. Verify leadership folder has children
  4. Find Roaster folder among children
  5. Verify Roaster contains at least one file
  → PASS or FAIL with a specific failure_reason
```

---

## Step-by-step

### Step 1 — Site discovery

**Graph API request:**

```
GET /sites?search=<keyword>&$select=id,name,webUrl,displayName,siteCollection
```

Issued once per entry in `discovery.site_prefixes`. Results are deduplicated by site
ID across keywords. All sites returned by the Graph search are passed to Step 2 —
no additional name or URL filtering is applied.

**Config fields:**

| Field | Default | Description |
|---|---|---|
| `discovery.mode` | `prefix` | `prefix` searches by keyword; `all-visible` enumerates everything visible to the authenticated user |
| `discovery.site_prefixes` | `["EPAM SAP SE"]` | Search keyword(s) sent to the Graph `/sites?search=` endpoint |

**Outcome:** a deduplicated list of `DiscoveredSite` objects passed into the
per-site checks below.

---

### Step 2 — Resolve drive

**Graph API request:**

```
GET /sites/<site_id>/drives?$top=200
```

The checker takes the **first drive** returned. No filtering by name is done.

**Failure condition:** if the drives list is empty, the site is marked **FAIL**
with `failure_reason = "No drives found for site <site_id>"`.

---

### Step 3 — Find leadership folder

**Graph API request:**

```
GET /drives/<drive_id>/root/children?$select=id,name,folder,file,webUrl&$top=200
```

Lists all immediate children of the drive root. Only items with a `"folder"` key
are considered. The checker scans each folder name against
`rules.leadership_folder_regex`. The **first match** is used.

The matched folder's `webUrl` (its direct SharePoint path) is stored as the site
link in the report so users can navigate straight to it.

**Config fields:**

| Field | Default | Description |
|---|---|---|
| `rules.leadership_folder_regex` | `^Project SAP-[A-Za-z]+ leadership$` | Regex applied to root-level folder names |

**Pattern breakdown:**

| Segment | Meaning | Example |
|---|---|---|
| `^Project SAP-` | Literal prefix | `Project SAP-` |
| `[A-Za-z]+` | One or more letters, any case | `MxG`, `CSD`, `AbCdEf` |
| ` leadership$` | Space then literal suffix | ` leadership` |

Full example match: `Project SAP-MxG leadership`

**Failure condition:** if no root folder matches the regex, the site is marked
**FAIL** with `failure_reason = "No folder matching '<regex>' found at root"`.

---

### Step 4 — Verify leadership folder is not empty

**Graph API request:**

```
GET /drives/<drive_id>/items/<leadership_folder_id>/children?$select=id,name,folder,file&$top=200
```

The full child list (both folders and files) is fetched.

**Failure condition:** if the list is empty, the site is marked **FAIL** with
`failure_reason = "Leadership folder '<name>' is empty"`.

---

### Step 5 — Find Roaster folder

The child list from Step 4 is reused (no extra request). The checker looks for a
subfolder whose name matches `rules.roaster_folder_name` (case-insensitive).

**Config fields:**

| Field | Default | Description |
|---|---|---|
| `rules.roaster_folder_name` | `Roaster` | Exact name (case-insensitive) of the required subfolder |

**Failure condition:** if no subfolder with that name exists, the site is marked
**FAIL** with `failure_reason = "'Roaster' folder not found inside '<leadership_folder>'"`.

---

### Step 6 — Verify Roaster contains files

**Graph API request:**

```
GET /drives/<drive_id>/items/<roaster_folder_id>/children?$select=id,name,folder,file&$top=200
```

Only items **without** a `"folder"` key count as files. Sub-folders inside Roaster
are ignored.

**Failure condition:** if no files are found, the site is marked **FAIL** with
`failure_reason = "'Roaster' folder contains no files"`.

---

### Step 7 — PASS

If all six steps complete without a failure, `overall_status` is set to **PASS**.

---

## All possible failure statuses

| `overall_status` | `failure_reason` | Cause |
|---|---|---|
| `FAIL` | `No drives found for site <site_id>` | The site has no accessible document libraries |
| `FAIL` | `No folder matching '<regex>' found at root` | No root-level folder matches `leadership_folder_regex` |
| `FAIL` | `Leadership folder '<name>' is empty` | The matched leadership folder has no children at all |
| `FAIL` | `'Roaster' folder not found inside '<leadership>'` | No subfolder named `roaster_folder_name` exists inside the leadership folder |
| `FAIL` | `'Roaster' folder contains no files` | The Roaster subfolder exists but contains no files (only sub-folders or is empty) |
| `PASS` | *(empty)* | All checks passed |
| `ERROR` | *(empty — see `error` field)* | An unexpected exception occurred (Graph API error, network timeout, etc.) |

> Sites that never reached Step 3 (i.e. `leadership_folder` is `null`) are included
> in the **CSV** and **HTML** reports but excluded from the **XLSX** report, which
> shows only sites where a leadership folder was found.

---

## Decision tree

```
Site discovered
    │
    ▼
GET /sites/<id>/drives
    ├─ empty list ──────────────────────────────► FAIL  "No drives found"
    └─ drives present → use drives[0]
          │
          ▼
    GET root children
          ├─ no folder matches leadership_regex ─► FAIL  "No folder matching '<regex>' found at root"
          └─ match found → leadership_folder (webUrl stored as site link)
                │
                ▼
          GET leadership_folder children
                ├─ empty ───────────────────────► FAIL  "Leadership folder '<name>' is empty"
                └─ children present
                      │
                      ▼
                roaster_folder_name in children?
                      ├─ No ──────────────────► FAIL  "'Roaster' not found inside '<leadership>'"
                      └─ Yes → roaster_folder
                            │
                            ▼
                      GET roaster children (files only)
                            ├─ no files ──────► FAIL  "'Roaster' folder contains no files"
                            └─ files present
                                  │
                                  ▼
                                PASS
```

---

## Graph API request sequence per site

```
1.  GET /sites?search=<keyword>&$select=id,name,webUrl,displayName,siteCollection
        → discover sites (once per keyword, shared across all sites)

1b. GET /sites/<site_id>?$select=id,webUrl          [only when webUrl missing from step 1]
        → resolve missing site URL

2.  GET /sites/<site_id>/drives?$top=200
        → find drive ID (first drive)

3.  GET /drives/<drive_id>/root/children?$select=id,name,folder,file,webUrl&$top=200
        → list root; find leadership folder by regex; capture its webUrl as report link

4.  GET /drives/<drive_id>/items/<leadership_folder_id>/children?$select=id,name,folder,file&$top=200
        → verify non-empty; find Roaster subfolder

5.  GET /drives/<drive_id>/items/<roaster_folder_id>/children?$select=id,name,folder,file&$top=200
        → verify at least one file present
```

Steps 2–5 run per site, up to `execution.max_parallel_sites` sites at a time.

---

## Result fields

Each `SiteCheckResult` exposes:

| Field | Type | Description |
|---|---|---|
| `site_name` | `str` | Raw site name from Graph (often empty; use `display_name`) |
| `site_url` | `str` | Direct URL to the leadership folder (falls back to site root if folder not yet found) |
| `site_id` | `str` | Graph site ID (`hostname,guid,guid`) |
| `display_name` | `str \| None` | Human-readable site display name from Graph `displayName` |
| `drive_id` | `str \| None` | ID of the resolved drive |
| `leadership_folder` | `str \| None` | Name of the matched leadership folder |
| `roaster_found` | `bool` | Whether the Roaster subfolder was found |
| `roaster_has_files` | `bool` | Whether at least one file exists in Roaster |
| `failure_reason` | `str \| None` | Human-readable explanation of the first failure |
| `overall_status` | `PASS \| FAIL \| ERROR` | Final verdict |
| `error` | `str \| None` | Set on unexpected exceptions (not validation failures) |

---

## Report formats

| Format | Sites included | Notes |
|---|---|---|
| **JSON** (`run-summary.json`) | Only sites where `leadership_folder` is not null | Slim output, one object per site |
| **CSV** (`run-summary.csv`) | All discovered sites | Full audit trail, plain text |
| **XLSX** (`run-summary.xlsx`) | Only sites where `leadership_folder` is not null | Color-coded rows (green = PASS, red = FAIL), clickable URL |
| **HTML** (`run-summary.html`) | All discovered sites | Color-coded rows, hyperlinked site names |

---

## Configuring the patterns

Both name patterns are set in the YAML config and have sensible defaults:

```yaml
rules:
  leadership_folder_regex: "^Project SAP-[A-Za-z]+ leadership$"
  roaster_folder_name: "Roaster"
```

To match a different naming convention, update `leadership_folder_regex` — it is
a standard Python `re` pattern anchored with `^` and `$`.

To change the required subfolder name, update `roaster_folder_name`. The comparison
is case-insensitive, so `"roaster"`, `"ROASTER"`, and `"Roaster"` all match.
