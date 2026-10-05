---
id: T-0068
title: Nothing checks that matrix links stay alive, and nothing yet shows only objects that have one
status: DECIDED
tags: [backstory, feature]
anchor: editorial/build_backstory.py:146
---

## What

Split out of T-0065 on 2026-10-02. Three pieces, none built:

1. **A link checker** that fetches every `Source URL` in the matrix and records
   the last-checked date and a status in a generated file beside the matrix, so
   the xlsx stays hand-edited. Statuses: live; dead (404, 410, 5xx); blocks
   scripts (403, 429, JavaScript-rendered, which is not dead); paywall; moved.
2. **An eligibility rule** in `build_backstory.py`: an object is shown only if it
   has a link and the checker has not marked it dead, and an `Exclude` flag in the
   matrix is the editor's only override. This replaces `pick()` (two earliest
   pre-1981, two latest per row) and is the base for the rules-based selection in
   T-0062. 7 of 48 sub-genres have fewer than two linked objects today, so it
   needs a fallback to the whole row.
3. **The remaining 45 links**, listed with what was tried on the review sheet's
   "No link yet" tab: Equality 13, America Abroad 8, Government 7, Work 5.

## Why

The product sends readers off NTK to a link, so a dead link is the failure
readers see. Archives refuse scripts (T-0067), so a checker that treats every
non-200 as dead will delete good objects; "blocks scripts" has to be its own
status. Ruled out: a database for link health now (T-0066), since a generated
file is enough. Link checking costs only time. The 45 links cost more research
passes, and the search-cap limits recorded in T-0067 apply.

## Check

```sh
python3 - <<'PY'
import json, sys, openpyxl
from pathlib import Path
p = Path("editorial/object-links-health.json")
if not p.exists():
    sys.exit("OPEN: no link-health file yet")
h = json.loads(p.read_text())
ws = openpyxl.load_workbook("editorial/NTK_Backstory_Object_Matrix.xlsx", read_only=True)["Objects"]
rows = list(ws.iter_rows(values_only=True))
u = rows[0].index("Source URL")
urls = {r[u] for r in rows[1:] if r[u]}
unchecked = [x for x in urls if x not in h]
if unchecked:
    sys.exit(f"OPEN: {len(unchecked)} linked objects have no health record, e.g. {unchecked[0]}")
PY
grep -q "eligible" editorial/build_backstory.py
```
