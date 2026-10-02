---
id: T-0045
title: The placard's pull-quote needs a real, sourced generation step
status: DISCARDED
tags: [backstory, feature]
anchor: editorial/build_backstory.py:82
---

## What

Confirmed 2026-09-28. Every object in `digest/data/backstory.json` (built
by `editorial/build_backstory.py` from `editorial/NTK_Backstory_Object_Matrix.xlsx`)
carries `{title, author, year, source}` only — no quote or excerpt field
exists anywhere in the schema. The Backstory redesign's 4B screen ("the
placard," `design_handoff_backstory/Backstory v4.dc.html`) puts a
one-sentence pull-quote from the object front and center in the carousel
card — that's not a cosmetic choice, the editor confirmed it directly:
"I like the quotes... I'd like to keep the quote for the placard."

Measured this session: hand-researching 8 real quotes (Media + Work
rows' objects) via live WebSearch/WebFetch against primary sources
(Project Gutenberg, Cornell LII, Wikisource, congress.gov, Business
Roundtable's own site) took real, non-trivial effort per object, and
caught at least one case where working from memory alone would have
been approximate rather than exact (*Reno v. ACLU*'s "vast democratic
forums" phrasing). That does not scale to 14 held rows × 4 objects
today, let alone as more rows are added. See
`design_handoff_backstory/Backstory v5 (real data).dc.html` for the
worked example and its inline notes on where the schema needs to grow.

## Why

**Acceptance criteria, given directly by the editor:** for the placard
in Backstory, a quote from the row's objects — one sentence, as
memorable as possible, as close to NTK's mission as possible, bonus if
it invites the reader to tap "About this" — chosen by Sonnet 5, placed
in the placard's object carousel.

**The real risk this ticket exists to name:** a model asked to supply a
quote from a historical document, working from its own training
knowledge alone, will produce something *plausible* often enough that
an approximate or wrong quote is genuinely hard to catch by reading —
this session hit that directly on one of eight, and would not have
caught it without independently searching the primary source. Whatever
implements this needs real search/fetch access at generation time, not
a bare model call against memory. This is the same lesson
`docs/decisions.md` already recorded for indicator numbers (Gallup,
BLS, etc.) — ship with an honest `verified: false` until a human
confirms, never silently presented as settled fact. A quote from a
primary source is exactly the same category of claim.

**Two design decisions this ticket deliberately leaves open, to resolve
when the work is picked up, not now:**
1. **Where it lives.** A new `quote` (+ `quote_src`) column in
   `NTK_Backstory_Object_Matrix.xlsx`, generated once per object and
   reviewed before use — matching how objects themselves are already
   hand-curated — or a live generation step inside
   `build_backstory.py`, run on each build. The spreadsheet path is
   cheaper and matches the existing editorial workflow; the live-build
   path stays fresher if objects are added or reordered but needs its
   own search/fetch capability wired into a stdlib-only pipeline
   script, which is a bigger lift than anything else in that file today.
2. **Selection, not just generation, when an object has more than one
   quotable line.** "Chosen by Sonnet 5" implies picking the single
   best candidate against the stated bar (memorable, on-mission,
   invites the tap), not just returning the first quote found — that's
   closer to what punch-up headline generation already does
   (`punchUpHeadline()` in `pulse.html`, three candidates then a pick)
   than to a single deterministic lookup.

**Verification posture:** every quote ships with `verified: false` and
a `quote_src` citation good enough for a human to check in under a
minute, exactly the discipline `IND` in `build_backstory.py` already
enforces for indicator numbers. Never auto-promoted to "verified" by
the generation step itself.

## Check

```sh
set -e
# Nothing is built yet — this DECIDED ticket should report OPEN. The
# check below asserts the eventual shape: real quote fields on real
# objects, sourced, unverified by default, actually reaching the
# placard's data — not the mechanism (spreadsheet vs. build-step) that
# gets it there, since that's still an open decision above.

python3 - <<'PYEOF'
import json, sys
from pathlib import Path

p = Path("digest/data/backstory.json")
if not p.exists():
    sys.exit("digest/data/backstory.json not found")
data = json.loads(p.read_text())
held = [r for r in data["rows"] if r["stratum"] == "held" and r["objects"]]
if not held:
    sys.exit("no held rows with objects to check")

missing_quote = []
missing_src = []
missing_verified_flag = []
too_long = []
for r in held:
    for o in r["objects"]:
        if not o.get("quote"):
            missing_quote.append(f"{r['id']}: {o['title']}")
            continue
        if not o.get("quote_src"):
            missing_src.append(f"{r['id']}: {o['title']}")
        if "verified" not in o:
            missing_verified_flag.append(f"{r['id']}: {o['title']}")
        # crude one-sentence heuristic: no more than one internal
        # terminal punctuation mark before the final character
        body = o["quote"].rstrip('"').rstrip()
        internal = body[:-1].count(".") + body[:-1].count("!") + body[:-1].count("?")
        if internal > 0:
            too_long.append(f"{r['id']}: {o['title']} -> {o['quote']!r}")

if missing_quote:
    sys.exit(f"OPEN: {len(missing_quote)} objects still have no quote field, e.g. {missing_quote[0]}")
if missing_src:
    sys.exit(f"OPEN: {len(missing_src)} quotes have no quote_src, e.g. {missing_src[0]}")
if missing_verified_flag:
    sys.exit(f"OPEN: {len(missing_verified_flag)} quotes have no verified flag, e.g. {missing_verified_flag[0]}")
if too_long:
    sys.exit(f"OPEN: {len(too_long)} quotes look like more than one sentence, e.g. {too_long[0]}")

print(f"{sum(len(r['objects']) for r in held)} objects across {len(held)} held rows all carry a sourced, "
      f"single-sentence, unverified-by-default quote")
PYEOF
```

**Beyond the mechanical check:** the script above confirms the fields
exist, are sourced, and look like one sentence — it cannot confirm
memorable, on-mission, or inviting the tap to "About this," which is
the actual bar the editor gave. Once the mechanical check passes,
promote to VERIFIED only after the editor reads a real sample of
generated quotes against that bar directly — not on the strength of
the fields being populated.

## Discarded 2026-10-02

The editor decided Backstory is automated and rules-based, with no hand-picked
objects and no hand-written text, and that nothing is hosted on NTK. A
single, memorable, on-mission quote chosen per object is a curation task, and
a quote taken from memory is the failure this ticket was written to prevent.
Not built. The short object page (T-0048) carries a grounded 'About this' in
its place. If the placard's quote slot comes back, start from the risk named
above: real fetch at generation time, `verified: false` until a human confirms.
