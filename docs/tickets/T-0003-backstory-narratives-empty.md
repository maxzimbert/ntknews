---
id: T-0003
title: Every Backstory narrative is empty
status: DECIDED
tags: [backstory, defect]
anchor: digest/data/backstory.json
---

## What

`digest/data/backstory.json` holds 21 library rows. All 21 have an empty
`narrative`. The tab renders rows that open to "No narrative yet." No
Register 3 rewrite pass has ever been run.

The wiring is fine and is no longer the problem. The generator, the data file
and the app all agree on `digest/data/backstory.json` (guarded by T-0007), and
`todays_pairings` now carries six entries.

## Why

This reads to a visitor as an out-of-date product, which is the opposite of the
impression the Backstory tab exists to create. It is not a broken feature — it
is an unpopulated one, and the distinction matters because the fix is a
content-generation run, not a code change.

Worth stating plainly because the previous documentation got this wrong in both
directions: for months a README described a 21-row library with per-story
pairings as shipped when none of it was in the app, and `docs/state.md` as
recently as 2026-09-15 described six standing rows when 21 had landed. The
structure is now real. The prose inside it is not.

**Scope decided 2026-09-17 by the editor: only rows that appear in
`todays_pairings`.** Register 4 specifies Opus for first drafts, so 21 rewrites
is a real spend on rows a reader may never open. Writing the paired rows first
means every narrative that exists is one a reader can reach from today's
digest, and the library fills in as rows actually get used.

The check reflects that decision: it fails when a row is paired *today* and has
no narrative. A row nobody has paired is not a defect.

Note the interaction with T-0012 — seven rows are unreachable by the
classifier, so they will never become paired and will never be written under
this scope. That is a consequence to accept knowingly, not a reason to widen
the scope.

## Check

```sh
python3 - <<'PYCHK'
import json, sys
d = json.load(open('digest/data/backstory.json'))
rows = {r['id']: r for r in d.get('rows', [])}
paired = sorted({p['row'] for p in d.get('todays_pairings', [])})
def text(r):
    n = (rows.get(r) or {}).get('narrative') or ''
    return (''.join(n) if isinstance(n, list) else n).strip()
empty = [r for r in paired if not text(r)]
if empty:
    sys.exit('%d of %d rows paired today have no narrative: %s'
             % (len(empty), len(paired), empty))
PYCHK
```
