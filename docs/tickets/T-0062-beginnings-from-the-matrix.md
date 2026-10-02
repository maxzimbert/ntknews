---
id: T-0062
title: Beginnings load from the matrix; "In the digest" carries prior stories (replaces T-0050)
status: DECIDED
tags: [backstory, feature]
anchor: editorial/build_backstory.py:146
---

## What

Decided with the editor 2026-10-01. Two changes to what a Backstory row
shows, replacing T-0050's "Earlier episodes" framing:

1. **Beginnings.** A row's `instances[]` holds its dated lineage: the objects
   from the matrix (T-0060, T-0061) that mark where the argument came from,
   each with year, one sentence and a link to its object page. The 4C page
   renders them as the dotted spine (design 4C, "Beginnings"), marking the
   year the reader came in at. Today `instances[]` is empty on all 21 rows and
   a row has one `start_line`, so the spine has one entry.
2. **In the digest.** What T-0050 called "Earlier episodes" is just the
   existing "In the digest" section extended to prior stories from recent
   digests that touched the row, newest first. This needs past pairings to
   persist: `todays_pairings` is overwritten every publish, so past ones are
   lost today (measured 2026-09-29, reconfirm before building).

Naming hazard: the in-app code (`bsrEpisodesHtml`, `bsrDetailHtml` in
`digest/index.html`) reads `instances[]` as episodes. If `instances[]` becomes
Beginnings, that reader is wrong. The old modal is unreachable since T-0057,
but the field's meaning must be changed deliberately, not by accident.

## Revised 2026-10-02

Decided with the editor, replacing the hand-built parts above:

- **Selection is rules, not hand-picking.** The editor curates the digest in
  Pulse and can do a light edit on Backstory, but will not choose beginnings or
  objects. Code picks them from the matrix by the story's sub-genre, era and
  spread (no repeated author, spread across time), and an `Exclude` flag in the
  matrix is the only override. The matrix has no importance signal, so expect
  adequate picks, not curated ones.
- **An object is eligible only with a verified, live link** (T-0065).
- **Beginnings are year, title, author and link.** No generated sentence unless
  a grounded pilot proves out: ~10 objects generated from the matrix alone and
  again from the fetched source text, compared by hand against the source. The
  model-from-memory failure is documented (T-0045, T-0047).
- `instances[]` is generated from the matrix by `build_backstory.py` and is no
  longer hand-written or preserved across rebuilds, which also removes the
  naming hazard above and ends hand-tagging in Pulse (T-0050).
- `pick()` (two earliest pre-1981, two latest) is superseded. Until the rules
  land, merging more matrix rows into a rebuild silently changes the objects
  shown: the 2026-10-02 simulation moves Equality to Wheatley and Abigail Adams
  and Faith to Red Jacket.

## Why

The editor's view: past stories do not need their own "episodes" concept, and
the lineage is what answers "where does this start." Ruled out: building
T-0050 as written, which tags stories by hand in Pulse into `instances[]`.
Pulse tagging (T-0010) was last tested months ago by the editor's account
(2026-10-01, "I haven't tested pulse tagging in 10 or 62"), so treat it as
unverified until someone runs it.

**Past stories are test cases, by the editor's decision.** Anything stored for
"In the digest" before launch is throwaway. So every persisted past pairing
carries a `test: true` tag (set while the product is pre-launch), and a
purge step removes every tagged entry before a real launch. Both are part of
this ticket, not later work, so test data cannot ship as history. Depends on
T-0060 and T-0061 for content; the object-page route is
`/backstory/<row>/objects/<n>/` (T-0059).

## Check

```sh
python3 - <<'PY'
import json, sys
d = json.load(open("digest/data/backstory.json"))
held = [r for r in d["rows"] if r["stratum"] == "held"]
n = sum(1 for r in held if len(r.get("instances") or []) >= 2)
if n < len(held):
    print(f"{n} of {len(held)} held rows have a multi-entry lineage"); sys.exit(1)
PY
```
