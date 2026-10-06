---
id: T-0074
title: "It starts in" is one fixed year per row, so most of today's pairings leap from the story to an origin that does not fit it
status: DECIDED
tags: [backstory, feature]
anchor: editorial/backstory-rows.json
---

## What

Raised by the editor 2026-10-05. The row-and-story selection ("Today") is good. The weak part is
the origin the reader is sent to. Every row has exactly one `start_date` and `start_line`
(`editorial/backstory-rows.json`), and the pairing line is written to sit under it, so the origin
cannot move to suit the story. Measured on the 2026-10-05 edition, `digest/data/backstory.json`
`todays_pairings`:

| Story | Row / sub-genre | Origin the row offers |
|---|---|---|
| Utah to let AI prescribe acne drugs with no doctor checking | Government / regulation and the administrative state | June 1978, California voters cap their property taxes |
| Sam Altman says "bad things will happen" from AI | Work / automation and AI displacement | October 1973, the oil shock |
| Diesel at $6.53, a farm tax break as the fix | Climate / regional economic disruption | June 1988, a scientist tells Congress the planet is warming |
| Saudi Arabia rebuilds the coalition that lost to the Houthis | America Abroad / military intervention | April 1975, the last helicopter leaves Saigon |
| A lab worker dies in Siberia, five regions locked down | The Bomb / proliferation | August 1945, the first use of a nuclear weapon |

The editor's own examples of the jump, the thing to fix: going from diesel prices today to the start
of the government's formal knowledge of a warming planet, or from Utah's plan to let AI prescribe
acne medication to the 1978 California Prop 13 start point. Both are rows chosen correctly and
origins that are too far from the story. Today's table shows five of six leaping further than the
story justifies. (An earlier version of this ticket described these two examples as the fit that was
wanted. That was backwards, corrected 2026-10-06.)

Direction, not a design: the classifier already assigns each story a sub-genre and the matrix
already tags every object with one. A row would carry several vetted origins, keyed by sub-genre
and ranked, and the pairing step would choose among them using the story's own Truths and then
write the "Today" line to match. The original design already specified "a fixed, editorially-ranked
list of 5 to 8 possible beginnings" per row with rotation per device
(`design_handoff_backstory/README.md`, 4A); the rotation was never built.

## Why

The product's promise is that today's story is one episode of a long argument. When the origin
is a decade-old jump from the story, the reader sees the pairing as forced, and a forced pairing
is worse than none because the reader is the person most likely to notice it. Constraints from
the work so far, so the next session does not rediscover them:

- Origins must come from a vetted list, not be invented per story. A model choosing among listed
  origins is checkable; a model inventing a year is the T-0045 failure.
- A row's 3 to 6 timeline Beginnings (T-0069) are already a dated lineage drawn from the matrix;
  a story-specific origin may be one of them, or a sub-genre-specific entry added to them.
- The fixed one-per-row `start_date` also drives the elapsed-time number and "We are here" on
  the row page; changing what the row page marks has to be decided deliberately.
- Classifier confidence is already recorded per pairing (`confidence`, `needs_review`).

Not decided: where per-sub-genre origins live (`backstory-rows.json` or the matrix), how many per
sub-genre, and whether a story with no good origin should be shown no origin at all (T-0064
already lets a row render without a Today line).

## The goal, in the editor's words (2026-10-06)

The Backstory work should read the Truths, sort the story through the row and the sub-genre, and
use that to pair the TODAY composition, which is already good and stays as it is, with a much more
salient "It starts in YYYY" bookend. This is the whole job. It is not about Pulse's category.

Measured the same day: the classifier and the pairing step see the headline plus the lede (14 to 20
words) or, failing that, the first 220 characters of the Truths (about 35 words). Today's six
stories carry 317 to 464 words of Truths. The origin is then always the row's single `start_line`.

What stays: the TODAY line and the fixed `start_date` for the elapsed-time number. The row choice is
mostly good, but not always (see the examples: one of three differs). What changes: (1) the steps read the full Truths; (2) each row, and each
sub-genre within it, carries several vetted origins (year, one sentence), the natural source being the
matrix, whose objects already carry a sub-genre and a year and whose Beginnings entries are written
in exactly this form; (3) the pairing step chooses the origin that best bookends this story's
argument, says why, and falls back to the row's current origin when it is not confident.

Related, not the cause: Pulse's category (World, Tech, ...) and its Backstory row dropdown are
independent and the pairing step never reads the category. Choosing a row in Pulse records no
sub-genre (`build_pairings.py` writes `subgenre: None` for an editor tag), so an override cannot
steer the origin today. A control to see and change the chosen origin in Pulse is a later phase.

## The editor's three examples, 2026-10-06 (the first test cases)

| Story (TODAY line) | System chose | Editor would have |
|---|---|---|
| "A $6.53 diesel price gets answered with a tax break the president cannot actually authorize alone." | Climate, origin 1988 (a scientist tells Congress the planet is warming) | **America Abroad**, origin **2025**: President Trump used military force to strike Iran in June 2025 |
| "A state is letting software write prescriptions nobody with a license has to check." | Government, origin 1978 (California voters cap property taxes) | Government, origin **2024**: the Utah Office of Artificial Intelligence Policy opened within the state Department of Commerce in July 2024 |
| "A coalition that lost this war once is rebuilding it with more jets and the same strait to retake." | America Abroad, origin 1975 (the last helicopter leaves Saigon) | America Abroad, origin **2014**: Houthi forces took over the Yemeni capital and civil war began |

What they show:

- **The wanted origin is the story's proximate cause, 1 to 11 years back, not the row's deep start.**
  The long lineage already lives on the row page's Beginnings timeline; the bookend on the Thread is
  the event that makes today's story happen. Two different jobs for two screens.
- **The row choice is not always right.** Diesel went to Climate; the editor reads it as foreign
  policy (a war, a strait, a price). So reading the full Truths has to improve the row and
  sub-genre too, not only the origin.
- **The matrix does not hold any of the three origins.** Checked 2026-10-06 against the 384
  objects: no June 2025 Iran strike (only the 1980 hostage rescue and the 2015 nuclear deal), nothing
  on the Utah AI office, nothing on Yemen or the Houthis. Only 4 objects are dated 2024 or later and
  about 2 to 5 a year from 2010 to 2023. The matrix is the source of origins, so it needs a recent
  layer: for each sub-genre, the events of the last decade that stories keep tracing back to, each a
  primary document with a verified link, added through the candidates workflow (T-0067). An origin
  is then a matrix object, can use its generated one-sentence line, and its object page is where
  "About this" lands.

## Acceptance

1. The origin is chosen from the story's full Truths plus its row and sub-genre, and always from a
   vetted list: every held row has at least two origins, and every pairing records which origin it
   chose. When confidence is low it falls back to the row's current `start_line`.
2. The TODAY line is no worse than today's. Compare a week of output before and after.
3. For a day's stories, the editor judges the year and line salient for at least five of six, and
   none absurd. A fixed set of stories, each with the origin the editor accepts, becomes a test.
4. Later: Pulse shows the chosen origin before publish and lets the editor pick another from the list.

## Check

```sh
python3 - <<'PY'
import json, sys
d = json.load(open("digest/data/backstory.json"))
rows = {r["id"]: r for r in d["rows"]}
bad = []
for r in d["rows"]:
    if r["stratum"] == "held" and len(r.get("origins") or []) < 2:
        bad.append(f"{r['id']}: {len(r.get('origins') or [])} origins (need 2)")
for p in d.get("todays_pairings", []):
    ids = {o.get("id") for o in rows.get(p["row"], {}).get("origins", [])}
    chosen = (p.get("origin") or {}).get("id")
    if chosen not in ids:
        bad.append(f"{p['row']}: the pairing's origin {chosen!r} is not in the row's list")
if bad:
    sys.exit("OPEN: %d problems, e.g. %s" % (len(bad), bad[0]))
PY
```

Criteria 2 and 3 are the editor's judgement and are not in the check.
