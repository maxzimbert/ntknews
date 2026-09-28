---
id: T-0048
title: 4D (the object page) has no real content model — 4 fields short of the design
status: DECIDED
tags: [backstory, feature]
anchor: editorial/build_backstory.py:82
---

## What

Confirmed 2026-09-28: every object in `digest/data/backstory.json` is
`{title, author, year, source}` — 56 objects across the 14 `held` rows
(counted directly). `source` is a citation string ("Hofstadter, Great
Issues in American History," "521 U.S. 844"), not a URL.

The design (`design_handoff_backstory/README.md`, screen 4D — "the
object page," `Backstory v4.dc.html#4d`) specs a real hosted page per
object: an optional image/scan, an object-type + date line, a title, an
attribution line, **two short paragraphs of context**, **a pull-quote**,
a **"where it stands now"** paragraph, and an **outbound link to the
actual original source** ("Read the full opinion · Library of
Congress"). None of that exists in the schema. Note for whoever picks
this up: `design_handoff_backstory/` is local-only — never committed to
this repo (`git ls-files` confirms zero tracked files there) — so it
won't be present in a fresh checkout; ask the editor for it again if the
design spec is needed and this note is all that's left. `T-0046`'s
`build_backstory_pages.py` doesn't generate any per-object page or link
to one — "The case" on a row's permalink renders each object as plain,
unlinked text today, precisely because there's nowhere to link it to.

## Why

Named directly by the editor after asking "is any action needed" on the
open note left in `Backstory v5 (real data).dc.html` — the answer was
no immediate action (nothing is broken, nothing blocks T-0046 or
T-0047), but the gap was untracked. This ticket exists so it doesn't
stay that way.

**Overlaps with T-0045 on exactly one field, and shouldn't duplicate
it.** T-0045 already covers a real, sourced, one-sentence quote per
object for the placard. 4D's "pull-quote" slot is the same kind of
thing — this ticket should consume T-0045's `quote` field as 4D's
pull-quote once that ships, not commission a second, separate quote-
sourcing pass for the same 56 objects. What 4D actually adds beyond
T-0045: object type + precise date, two paragraphs of real historical
context, a "where it stands now" paragraph, and an outbound URL to the
primary source itself.

**This is a bigger writing lift than T-0045, not just a bigger version
of it.** T-0045 is one verified sentence. This is two paragraphs of
real historical writing plus a closing "where it stands now" per
object — 56 objects' worth. The same risk applies, sharper: a
two-paragraph historical account that's subtly wrong is much harder for
a reader (or an editor skimming for review) to catch than a bad quote.
Whatever writes these needs the same discipline T-0045 already proved
out — real search/fetch against a primary or credible secondary source,
not a model working from its own recall — and should probably lean more
heavily on human drafting or editing than T-0045's shorter, more
mechanically-checkable output.

**Two design decisions, deliberately left open:**
1. **Where the new fields live** — same question as T-0045: a set of
   new columns in `editorial/NTK_Backstory_Object_Matrix.xlsx` (matches
   how objects are already curated) or generated fields in
   `build_backstory.py`'s output. Given the writing-heavy nature of this
   content, the spreadsheet path (hand-drafted or assisted, reviewed
   before use) is probably the better fit even more than it was for
   T-0045 — but that's a call for whoever picks this up.
2. **The actual page and its route** (`/backstory/<row-id>/objects/<n>/`
   or similar, plus wiring "The case" to link there) is real plumbing
   work, the same shape as T-0046 — deliberately not bundled into this
   ticket. This one is the content gap; the generator is its own
   follow-on once there's real content to render.

**Outbound URL needs its own honesty flag**, same posture as
`quote_src`/`verified`: a link to the wrong edition, a paywalled
version, or a dead archive link is a real failure mode for a "read the
original" promise, not a cosmetic one.

## Check

```sh
set -e
# Nothing built yet — correctly reports OPEN. Asserts the eventual
# content shape (all four new fields present, sourced, non-empty) on
# every held-row object, not the mechanism (spreadsheet vs. build step)
# that gets them there.
python3 - <<'PYEOF'
import json, sys
from pathlib import Path

p = Path("digest/data/backstory.json")
data = json.loads(p.read_text())
held = [r for r in data["rows"] if r["stratum"] == "held" and r["objects"]]
if not held:
    sys.exit("no held rows with objects to check")

REQUIRED = ["object_type", "context", "stands_now", "source_url"]
missing = []
for r in held:
    for o in r["objects"]:
        for field in REQUIRED:
            if not o.get(field):
                missing.append(f"{r['id']}: {o['title']} -> missing {field}")

if missing:
    sys.exit(f"OPEN: {len(missing)} object fields still missing, e.g. {missing[0]}")

print(f"all {sum(len(r['objects']) for r in held)} objects across {len(held)} held rows "
      f"carry object_type, context, stands_now, and a source_url")
PYEOF
```

**Beyond the mechanical check:** confirms the fields exist, not that the
writing is any good or that `source_url` actually resolves to the real
object. Promote to VERIFIED only after an editor reads a real sample
against the design's own bar (two short paragraphs, a real pull-quote,
an honest "where it stands now") and a spot-check of `source_url` links
actually confirms they land on the right document.
