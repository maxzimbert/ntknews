---
id: T-0099
title: Each live-conflict page shows the history before its clock started (Beginnings and their objects) under the day count
status: BUILT
tags: [backstory, feature]
anchor: editorial/fire-rows.json
---

## What

Measured 2026-10-21 on main (30834b20): the seven live-conflict rows (US–Canada trade, US–Israel–Iran,
Venezuela, Israel–Hezbollah, Gaza, Sudan, Ukraine–Russia) had 0 Beginnings, 0 objects, no stakes and no
trend line. Their page showed only "X years, Y months since". Gaza and Ukraine–Russia each had a story
paired to them that day, so readers clicked through to a counter.

Built on `T-0099-live-conflict-pages`: `editorial/fire-rows.json` lists, per conflict, hand-picked objects
(matrix first, then candidates), the stakes, and the object that marks the day the clock starts where
one exists (Putin's address of 24 February 2022; the 3 January 2026 announcement of Maduro's capture).
`build_backstory.py` shows an object only if it is in the matrix or approved in the candidates workbook,
its link is live, and it has text; fewer than three and the page keeps its day count alone. The pages
render the history under the counter (`build_backstory_pages.py`, `digest/index.html`).

29 Beginnings in all, 3 to 6 per conflict. Two objects are already in the matrix (the 1980 hostage-rescue
report, the JCPOA). The rest are candidates in `NTK_Backstory_Candidates.xlsx` ("Lens candidates"):
21 researched and link-checked on 2026-10-06/07, and 8 found for this ticket (4 Sudan, 4 Venezuela)
with four web searches, each link fetched and read (two UN press releases read in a browser: the site
refuses scripted fetches). Three UN links were moved from the docs.un.org viewer to the UN PDFs.
Text for all 31 objects is in `object-notes.json`, written by Claude, `verified: false`.

Also in this branch: the three inflation categories merged into one, "Inflation and cost of living"
(`p-inflation-and-cost-of-living`); the other two are `status: "merged"`, cannot be republished from an
old Pulse draft, and their pages forward to the merged one. And `build_backstory.py` no longer drops the
categories from `backstory.json` when it is rerun.

## Why

The live conflicts are where the news lands most, and their pages had nothing behind the counter. The
material was already in the library: the proposal of 2026-10-15 (`docs/proposals/object-matrix-retrieval.md`)
listed it by country. The editor asked for few web searches and for the Object Matrix to carry the
pages; four searches were spent, all on Sudan and Venezuela, which the library did not cover.

Not done, and worth knowing: no trend lines yet; Gaza's nearest history (the 2005 disengagement, the
2007 Hamas takeover) and the 2025 strikes on Iran are not in the library, so those pages stop at 1993 and
2018. The candidates publish only after the editor approves them (the existing rule: a candidate is not
published until approved), so the pages fill when the Approve column is filled.

## Check

```sh
python3 - <<'PY'
import json, sys
d = json.load(open("digest/data/backstory.json"))
pool = {o["id"]: o for o in json.load(open("ntk-pulse/data/backstory-pool.json"))["objects"]}
fire = [r for r in d["rows"] if r["stratum"] == "fire"]
bad = []
for r in fire:
    b, objs = r.get("beginnings") or [], r.get("objects") or []
    if len(b) < 3:
        bad.append(f"{r['id']}: {len(b)} Beginnings")
    ids = {o["object_id"] for o in objs}
    for x in b:
        if x["object_id"] not in ids:
            bad.append(f"{r['id']}: Beginning {x['year']} has no object in the case")
    for o in objs:
        p = pool.get(o["object_id"]) or {}
        if not (o.get("about") and o.get("source_url") and p.get("approved")):
            bad.append(f"{r['id']}: {o['title'][:40]} lacks text or a link, or is not approved")
    if not r.get("stakes"):
        bad.append(f"{r['id']}: no stakes")
if len(fire) != 7 or bad:
    sys.exit("OPEN: %d problems, e.g. %s" % (len(bad), bad[0] if bad else "not 7 live-conflict rows"))
print("all 7 live-conflict pages show their history")
PY
```
