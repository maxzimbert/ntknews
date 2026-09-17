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

Cost is the live constraint: 21 Register 3 rewrites is a real Sonnet spend, and
it is worth deciding whether all 21 are needed or only the rows that appear in
`todays_pairings`.

## Check

```sh
python3 - <<'PY'
import json, sys
d = json.load(open('digest/data/backstory.json'))
rows = d.get('rows', [])
empty = [r.get('id') or r.get('title') or '?' for r in rows
         if not (r.get('narrative') or '').strip()]
if empty:
    sys.exit('%d of %d rows have no narrative' % (len(empty), len(rows)))
PY
```
