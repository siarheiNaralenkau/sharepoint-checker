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
  4. Find Roster folder among children
  5. Verify Roster contains at least one file
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
GET /drives/<drive_id>/root/children?$select=id,name,folder,file&$top=200
```

Lists all immediate children of the drive root. Only items with a `"folder"` key
are considered. The checker scans each folder name against
`rules.leadership_folder_regex`. The **first match** is used.

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

### Step 5 — Find Roster folder

The child list from Step 4 is reused (no extra request). The checker looks for a
subfolder whose name matches `rules.roster_folder_name` (case-insensitive).

**Config fields:**

| Field | Default | Description |
|---|---|---|
| `rules.roster_folder_name` | `Roster` | Exact name (case-insensitive) of the required subfolder |

**Failure condition:** if no subfolder with that name exists, the site is marked
**FAIL** with `failure_reason = "'Roster' folder not found inside '<leadership_folder>'"`.

---

### Step 6 — Verify Roster contains files

**Graph API request:**

```
GET /drives/<drive_id>/items/<roster_folder_id>/children?$select=id,name,folder,file&$top=200
```

Only items **without** a `"folder"` key count as files. Sub-folders inside Roster
are ignored.

**Failure condition:** if no files are found, the site is marked **FAIL** with
`failure_reason = "'Roster' folder contains no files"`.

---

### Step 7 — PASS

If all six steps complete without a failure, `overall_status` is set to **PASS**.

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
          └─ match found → leadership_folder
                │
                ▼
          GET leadership_folder children
                ├─ empty ───────────────────────► FAIL  "Leadership folder '<name>' is empty"
                └─ children present
                      │
                      ▼
                roster_folder_name in children?
                      ├─ No ──────────────────► FAIL  "'Roster' not found inside '<leadership>'"
                      └─ Yes → roster_folder
                            │
                            ▼
                      GET roster children (files only)
                            ├─ no files ──────► FAIL  "'Roster' folder contains no files"
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

2.  GET /sites/<site_id>/drives?$top=200
        → find drive ID (first drive)

3.  GET /drives/<drive_id>/root/children?$select=id,name,folder,file&$top=200
        → list root; find leadership folder by regex

4.  GET /drives/<drive_id>/items/<leadership_folder_id>/children?$select=id,name,folder,file&$top=200
        → verify non-empty; find Roster subfolder

5.  GET /drives/<drive_id>/items/<roster_folder_id>/children?$select=id,name,folder,file&$top=200
        → verify at least one file present
```

Steps 2–5 run per site, up to `execution.max_parallel_sites` sites at a time.

---

## Result fields

Each `SiteCheckResult` exposes:

| Field | Type | Description |
|---|---|---|
| `site_name` | `str` | Site name returned by Graph |
| `site_url` | `str` | Full SharePoint URL |
| `drive_id` | `str \| None` | ID of the resolved drive |
| `leadership_folder` | `str \| None` | Name of the matched leadership folder |
| `roster_found` | `bool` | Whether the Roster subfolder was found |
| `roster_has_files` | `bool` | Whether at least one file exists in Roster |
| `failure_reason` | `str \| None` | Human-readable explanation of the first failure |
| `overall_status` | `PASS \| FAIL \| ERROR` | Final verdict |
| `error` | `str \| None` | Set on unexpected exceptions (not validation failures) |

---

## Configuring the patterns

Both name patterns are set in the YAML config and have sensible defaults:

```yaml
rules:
  leadership_folder_regex: "^Project SAP-[A-Za-z]+ leadership$"
  roster_folder_name: "Roster"
```

To match a different naming convention, update `leadership_folder_regex` — it is
a standard Python `re` pattern anchored with `^` and `$`.

To change the required subfolder name, update `roster_folder_name`. The comparison
is case-insensitive, so `"roster"`, `"ROSTER"`, and `"Roster"` all match.
