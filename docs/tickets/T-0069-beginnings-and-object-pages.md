---
id: T-0069
title: A Backstory row page shows 3 to 6 dated Beginnings and the chosen objects behind them, and each object has a short page that sends the reader to the original
status: VERIFIED
tags: [backstory, feature]
anchor: editorial/build_backstory.py:162
---

## What

Decided with the editor 2026-10-05, after a misunderstanding about which Backstory
screen the work was for. Pairing lines and the Pulse category on the list screen
(4A, the Thread) already work and are not part of this. Three changes to the row
page (4C) and the object page (4D):

1. **Beginnings (4C)**: a short vertical timeline of 3 to 6 entries per row, each a
   year and one sentence of what happened, written from the Object Matrix. No link.
   The row's existing "since ..." line closes the timeline as the year the clock starts.
2. **The case (4C)**: every Beginning's object, plus one or two later ones, chosen by
   rule from the matrix (only objects with a verified link, spread across time), so
   5 to 7 per row (3 or 4 on a small row). Each keeps its "About this" link. Editor's
   rule, 2026-10-05: a Beginning that is a digitized primary source with a retrievable
   link must be in The case, so a reader who meets it in the timeline can open it.
3. **Object page (4D)**: the title, author and year, two or three plain sentences about
   the object, and a **View the primary document** button that opens the original in a
   new tab. Not built: pull-quote, "where it stands now", hosted text.

Writing policy, from the generation pilot (`editorial/NTK_Pilot_Generation.xlsx`):
write from the fetched source text when it fits and loads; fall back to the matrix
row alone on any blocker or doubt (blocked page, catalogue page, long document read
only in part). Every generated line is flagged unverified until the editor spot-checks
a sample. Numbers and years in generated text are checked against the matrix and the
source text, and a mismatch is flagged.

Stored in `editorial/object-notes.json`, keyed by object id (the matrix's sort date
plus title); built into `digest/data/backstory.json` as row `beginnings` and per-object
`about`, `source_url` and `object_id`. `instances[]` is left alone: its old reader
treats it as episodes.

## Why

The editor will curate the digest in Pulse but will not hand-pick Backstory objects or
write its text, so selection is code and the text is generated and spot-checked. The
alternatives ruled out: hosting the primary text (copyright varies across the matrix),
and a per-story choice of objects by sub-genre (more machinery than a first view needs;
revisit once the page is judged). Cost: one generation pass over about 150 objects,
cached in the notes file, not run daily.

## Check

```sh
python3 - <<'PY'
import json, sys
d = json.load(open("digest/data/backstory.json"))
held = [r for r in d["rows"] if r["stratum"] == "held"]
bad = []
for r in held:
    b = r.get("beginnings") or []
    ids = {o.get("object_id") for o in r["objects"]}
    if len(b) < 3 and len(r["objects"]) >= 3:
        bad.append(f"{r['id']}: {len(b)} beginnings")
    if r["objects"] and not 3 <= len(r["objects"]) <= 8:
        bad.append(f"{r['id']}: {len(r['objects'])} objects")
    for x in b:
        if x.get("object_id") not in ids:
            bad.append(f"{r['id']}: Beginning {x.get('year')} is not in The case")
    for o in r["objects"]:
        if not (o.get("about") and o.get("source_url")):
            bad.append(f"{r['id']}: {o['title']} lacks about or source_url")
if bad:
    sys.exit("OPEN: %d problems, e.g. %s" % (len(bad), bad[0]))
PY
grep -q "View the primary document" backstory/media/objects/1/index.html
```

## Shipped 2026-10-05

Merged to main as #63 (matrix and links) and #64 (this work); live on ntknews.org the same
minute. The editor looked at staging and spot-checked the generated text sheets before the
merge. Still open, tracked elsewhere: object permalinks are positional (`/objects/<n>/`), so
they are stable only while the selection is frozen in `backstory.json`; and there is no
link checker yet (T-0068). Re-running `build_backstory.py` after the matrix changes will
change which objects are chosen, and any newly chosen object needs its text written
(`editorial/merge_object_notes.py` lists and validates them).
