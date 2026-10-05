---
id: T-0068
title: Matrix links are checked for life, and an object whose link is dead is not chosen
status: VERIFIED
tags: [backstory, feature]
anchor: editorial/check_links.py
---

## What

Split out of T-0065 on 2026-10-02; built 2026-10-05. Two pieces:

1. **`editorial/check_links.py`** fetches every `Source URL` in the matrix and records the
   last-checked date and a status in `editorial/object-links-health.json`, beside the matrix, so
   the xlsx stays hand-edited. Statuses: `live`; `dead` (404 or 410 that a browser-like request
   confirms, a host that does not resolve, an error page served with a 200, or three failures
   in a row); `blocks_scripts` (403, 401, 429, a bot challenge, a dropped connection or a TLS
   handshake the checker cannot complete: NOT dead); `paywall`; `moved`; `unreachable`.
   A live page can carry a `note`: today 11 do, each a matrix year that appears nowhere on the
   page, which is how a link to the wrong document shows up.
2. **The eligibility rule** in `editorial/build_backstory.py`: an object is chosen only if it has
   a link the checker has not found dead. A host that merely refuses scripts keeps its objects.

First run, 2026-10-05, 320 distinct links: 307 live, 12 blocks_scripts, 1 paywall (Foreign
Affairs), 0 dead after one real find was fixed (below).

Not built, deliberately: a scheduled run. The checker is run by hand
(`python3 editorial/check_links.py`) and the check below fails when the health file is more than
60 days old, so it cannot be forgotten. A weekly GitHub Action that commits the file is the next
step if hand runs get skipped. The remaining objects without a link are T-0071.

## Why

The product sends readers off NTK to a link, so a dead link is the failure readers see. Archives
refuse scripts, so a checker that treats every non-200 as dead deletes good objects, and one that
cries wolf trains people to ignore it. Three things found while building it, so nobody repeats
them:

- state.gov answers a script with 404 and a browser with 403, and its blocked pages say
  "Technical Difficulties ... forbidden" with a 200. Any 404 is therefore re-asked with a
  browser-like request before the link is called dead, and that page text is read as a block.
- A genuinely dead link existed on the live Bomb page: New START's old state.gov path redirects to
  State's "website modernization" page, which returns 404. Replaced with govinfo's record of
  Senate Treaty Document 111-5 (the 24 MB, 563-page PDF behind it is why the record page is
  linked, not the PDF).
- Python's urllib in older versions does not follow HTTP 308, and this machine's TLS cannot
  complete a handshake with some hosts (pulitzercenter.org); neither means the link is bad.

Ruled out: a database for link health (T-0066); a generated file is enough.

## Check

```sh
python3 - <<'PY'
import json, sys, openpyxl
from datetime import datetime, timezone, timedelta
from pathlib import Path
p = Path("editorial/object-links-health.json")
if not p.exists():
    sys.exit("OPEN: no link-health file yet")
h = json.loads(p.read_text())
ws = openpyxl.load_workbook("editorial/NTK_Backstory_Object_Matrix.xlsx", read_only=True)["Objects"]
rows = list(ws.iter_rows(values_only=True))
u = rows[0].index("Source URL")
urls = {r[u] for r in rows[1:] if r[u]}
missing = [x for x in urls if x not in h]
if missing:
    sys.exit(f"STALE: {len(missing)} linked objects have no health record, e.g. {missing[0]}")
old = datetime.now(timezone.utc) - timedelta(days=60)
stale = [x for x in urls if datetime.fromisoformat(h[x]["checked"]) < old]
if stale:
    sys.exit(f"STALE: {len(stale)} links not checked in 60 days; run editorial/check_links.py")
d = json.load(open("digest/data/backstory.json"))
dead = [(r["id"], o["title"]) for r in d["rows"] for o in r.get("objects", [])
        if h.get(o.get("source_url"), {}).get("status") == "dead"]
if dead:
    sys.exit(f"STALE: a reader is sent to a dead link: {dead[0]}")
PY
grep -q "def load_health" editorial/build_backstory.py
```
