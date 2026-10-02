---
id: T-0048
title: The object page is short, an 'About this' and one outbound link, and its URL is stable
status: DECIDED
tags: [backstory, feature]
anchor: editorial/build_backstory.py:82
---

## What

Rewritten 2026-10-02. This ticket first asked for four new fields per object
from the 4D design (two context paragraphs, a pull-quote, "where it stands
now", an outbound link). Measured 2026-09-28: every object had only
`{title, author, year, source}`.

Decided with the editor 2026-10-02: nothing is hosted on NTK, but an object page
stays, short and simple, to answer the "About this" call to action on the row
page before it. Draft acceptance criteria, for the editor to change:

- A header line from the matrix: title, author, year, source.
- **About this**: two or three plain sentences using only facts found in the
  fetched source, at the Backstory reading level, no em dashes. Generated once
  per object and cached, flagged `verified: false` until the editor
  spot-checks a sample (about 20, not all).
- One outbound link, opening in a new tab, to a primary-source host checked
  live recently (T-0065).
- Back returns to the row. No pull-quote and no "where it stands now".
- The permalink uses a stable object ID, not the position in the row's list.

Dropped: `context`, `stands_now`, `object_type` and the pull-quote (T-0045).

## Why

The first cost the editor would not accept was a reader landing on a bare
outbound link with no framing, so the page stays. The long version was dropped
because it is a writing job of two paragraphs per object that cannot be
hand-reviewed at 384 objects and cannot be written from model recall without
the T-0045 failure.

The positional route `/backstory/<row>/objects/<n>/` (T-0059) breaks whenever
the selected set changes, because n is a list index. Pre-launch is the cheap
time to switch. Changing it will make T-0059's check go STALE
(`test -f backstory/media/objects/1/index.html`); update that check
deliberately in the same change rather than weakening it.

Cost: one grounded generation pass per object, cached. The pilot measures it
before the batch runs.

## Check

```sh
python3 - <<'PY'
import json, sys
d = json.load(open("digest/data/backstory.json"))
held = [r for r in d["rows"] if r["stratum"] == "held" and r["objects"]]
if not held:
    sys.exit("no held rows with objects to check")
missing = [f"{r['id']}: {o['title']} -> {f}" for r in held for o in r["objects"]
           for f in ("about", "source_url", "object_id") if not o.get(f)]
if missing:
    sys.exit(f"OPEN: {len(missing)} object fields missing, e.g. {missing[0]}")
PY
```
