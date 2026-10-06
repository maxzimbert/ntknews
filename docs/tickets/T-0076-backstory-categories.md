---
id: T-0076
title: Backstory's categories (rows) need another editorial pass, starting with where technology and AI stories land
status: BUILT
tags: [backstory, decision]
anchor: editorial/backstory-rows.json
---

## What

Named by the editor 2026-10-05 as part of the next effort: "improving Backstory categories."
Nothing is decided here; this records the state so the pass starts from facts.

The library is 21 rows: 14 in `editorial/backstory-rows.json` (Climate, The Media, Immigration,
Faith, Taiwan, Government, Order, America Abroad, Power, Work, Family, Equality, Korea, The Bomb)
and 7 hand-coded "Still Counting" conflict rows in `editorial/build_backstory.py`. Each held row
has a fixed `start_date` and a list of sub-genres, and the classifier assigns every story one
sub-genre. Facts worth having in front of you:

- No row is about technology or AI. Stories about it are filed under whichever row's argument
  they touch: 2026-10-05's Utah AI-prescribing story went to Government (regulation and the
  administrative state), Sam Altman's to Work (automation and AI displacement). Related
  sub-genres exist elsewhere: Family "children and technology", The Media "platforms and
  attention".
- 7 of the 48 sub-genres have fewer than two linked matrix objects (T-0071), so any new row or
  sub-genre needs matrix content with verified links before it can show a Beginnings timeline.
- `docs/decisions.md` records settled names and anchors (Equality not Race, Family not Sex,
  Government anchored at Prop 13) and two deferred rows (India-Pakistan as a 22nd, Surveillance
  as a row rather than a sub-genre under Order). Re-opening any of them is a decision, not a
  tidy-up.
- A row's start date is the year "We are here" marks and drives its elapsed time, so changing a
  category also changes those; see T-0074, which is the closely related question of which origin
  a story should be shown.

## Why

The categories decide what the product can say about a story. A story with no good home gets
a forced pairing (T-0074's examples), and the cheapest fix is often a better category, not a
better origin line. Open questions for the editor, not defaults: add rows, split a row, or only
add sub-genres; and who owns the matrix content a new row needs.

## Check

The editor decides the category changes; what is checkable is that the provisional-row machinery
holds its rules. A provisional row never has an indicator, never has sub-genres, is never in
`backstory-rows.json`, and a provisional pairing points at a row that exists.

```sh
python3 - <<'PY'
import json, sys
bs = json.load(open("digest/data/backstory.json"))
rows = {r["id"]: r for r in bs["rows"]}
fixed = {r["id"] for r in json.load(open("editorial/backstory-rows.json"))["rows"]}
store = json.load(open("ntk-pulse/data/provisional-rows.json"))["rows"]
bad = []
for r in bs["rows"]:
    if r.get("stratum") == "provisional":
        if r.get("indicator"): bad.append(r["id"] + ": has an indicator")
        if r.get("subgenres"): bad.append(r["id"] + ": has sub-genres")
        if r["id"] in fixed: bad.append(r["id"] + ": is in backstory-rows.json")
for r in store:
    if r.get("promotion", {}).get("ready") and r["status"] == "provisional":
        bad.append(r["id"] + ": marked promotion-ready without an editor decision")
for p in bs.get("todays_pairings", []):
    if p["row"] not in rows: bad.append(p["story_id"] + ": row " + p["row"] + " does not exist")
    if p.get("provisional") and rows[p["row"]].get("stratum") != "provisional":
        bad.append(p["story_id"] + ": provisional pairing on a non-provisional row")
if bad:
    sys.exit("OPEN: %d problems, e.g. %s" % (len(bad), bad[0]))
PY
```

## Parked idea, raised by the editor 2026-10-06 (not for action)

Rows are what a reader can build expertise in, but on the front end a story could be shown as one of
three broad kinds: Foreign Policy, Civil Rights, or The Government and the Economy. A radical
simplification of what the reader sees, keeping the rows underneath. Recorded so it is not lost; no
decision, and it would touch how rows are named and grouped on the Thread and the Backstory tab.

## Measured 2026-10-06: where poor row fit comes from

Three of the six stories on the 2026-10-05 edition fit their row poorly (diesel under Climate,
Altman under Work, the Siberia lab death under The Bomb). Findings, with the limits stated:

- **Confidence does not flag them.** The classifier scored those three 0.74, 0.68 and 0.72. The review
  threshold is 0.55, so none was flagged. The existing signal cannot find a bad row.
- **Input explains some of it.** The classifier sees the headline plus 14 to 35 words. Re-reading with
  the full Truths (by hand, so indicative only; `editorial/research/origins-2026-10-06/classify-full-truths.json`)
  moves three of six: Siberia to The Media (information and misinformation), diesel to Work (housing
  and cost of living) or Government (taxes), Altman to Government (regulation) at about 0.5.
- **Vocabulary explains the rest.** Altman has no good row: nothing in the Truths is about jobs, and the
  nearest sub-genres are weak. The editor reads diesel as America Abroad; on the Truths alone that
  scores about 0.4, because the war is the cause and the argument is prices and blame. That row is an
  editorial call a classifier will not make from the text.
- **Pairing steps still need the Truths.** `build_pairings.py` now sends the Truths to the classifier;
  the pairing-line writer still sees the summary.

Next, in the order agreed with the editor: a "row doesn't fit" control in Pulse and a gaps queue; then
Beginnings and "We are here" built around the story's origin; then what a provisional category may show
without a verified indicator. Each held row has `stakes` (about two sentences) and one hand-typed
`indicator` with a direction label and an `as_of` date; nothing computes or refreshes the direction,
and Power's indicator is unverified. The seven Still Counting rows have neither.

## Built 2026-10-06 (on PR #72)

Pulse's "no row fits" now asks for a category name. The story is filed under a provisional row built
from it, not under the nearest misfit. Rules are in `docs/decisions.md` ("Backstory is built from
the story's own subject"). Hand-drafted contest and stakes were used in the test, because there is
no API key locally; the drafting call, its validator and the whole publish path have not run live.
