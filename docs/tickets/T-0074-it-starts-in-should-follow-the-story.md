---
id: T-0074
title: "It starts in" is one fixed year per row, so most of today's pairings leap from the story to an origin that does not fit it
status: BUILT
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
  about 2 to 5 a year from 2010 to 2023. (Superseded by the decision below: origins are retrieved.) The matrix would need a recent
  layer: for each sub-genre, the events of the last decade that stories keep tracing back to, each a
  primary document with a verified link, added through the candidates workflow (T-0067). An origin
  is then a matrix object, can use its generated one-sentence line, and its object page is where
  "About this" lands.

## Decision, 2026-10-06: origins are retrieved, not added to the matrix

The editor ruled out growing the matrix by hundreds of recent objects. Origins are found per story
by `editorial/build_origins.py`: a model reads the full Truths plus the row and sub-genre and writes
2 to 3 Wikipedia queries; code retrieves article leads and Wikidata dates; a second model chooses
among the retrieved candidates only; code validates (year and quote verbatim in the lead, numbers
traced, year inside the row and not after the story, fit rated direct). Only a story with no candidate at all falls
back to the row's own `start_line`, and records why.
The Portal:Current_events day page for the event's date is read, and its entry and cited outlet are
stored when an entry links to the article or names the event. Wikipedia only finds and dates the
event; it is never linked to a reader. Every origin is `verified: false`.

Runs, 2026-10-06, on the six stories of the 2026-10-05 edition (artefacts in
`editorial/research/origins-2026-10-06/`; the two model steps were done by hand against the same
prompts because no API key exists outside Pulse and Actions, so the live API path is untested).
Run 1 held three of six: a "loose" fit sent Siberia, Altman and Boulder back to the row's fixed line
(1945, 1973, 1974), the very leap this ticket exists to remove. The editor rejected that: every story
has a past. Run 2 changed the rules: the query step reads the Truths first and the row only as a hint
that may be wrong; fit is judged against the Truths (`direct` or `inferred`) and the row's fit is
rated separately (`row_fit`); the row-start year is a flag, not a rejection; evidence may be quoted
from the story's own Truths when they state the origin; a short article is read past its lead.

| Story | Row (row_fit) | Origin, run 2 |
|---|---|---|
| Utah AI prescribing | Government (good) | 2024, Utah AI Policy Act, direct |
| Saudi coalition | America Abroad (good) | 2014, Houthis storm Sanaa, direct (the editor's example) |
| Diesel | Climate (poor) | 2026, the Iran war, direct: the Truths say "the war he started in February". The editor's example was June 2025; it was retrieved too |
| Siberia lab death | The Bomb (poor) | 1979, Sverdlovsk anthrax leak, inferred |
| Altman / OpenAI | Work (poor) | 2025, Raine v. OpenAI, inferred |
| Boulder v. Suncor | Power (good) | 2018, Boulder County sues, direct, quoted from the Truths |

Known limits: search results drift run to run (the script caches a retrieval and replays it); the
candidate cap was raised from 8 to 12 after "2026 Iran war" fell out of the list; the pairing step
rewrites `todays_pairings` and would drop `origin` until `build_origins.py` is wired after it in
`pulse-publish.yml`; there is no Pulse control yet to see or override the origin.

## Acceptance

1. Every pairing carries an `origin`: `retrieved` (passed validation) or `fallback` (the row's own
   line, with the reason). A retrieved origin has an integer year inside the row and not after the
   story, a "When" line, and `verified: false`.
2. The TODAY line is no worse than today's.
3. For a day's stories the editor judges the year and line salient for at least five of six and none
   absurd. The six above, with the origin the editor accepts, become the test set.
4. Wired 2026-10-06: `pulse-publish.yml` runs `build_origins.py --apply` after the pairing step with the
   API key from Actions secrets, `continue-on-error`. The plumbing was tested with a stand-in for the
   model (12 calls for six stories; one story's failed call falls back alone). The real model's answers,
   and a live Actions run, are not yet tested.
5. Later: Pulse shows the chosen origin and the rejected proposal before publish and lets the editor
   pick another.

## Check

```sh
python3 - <<'PY'
import json, sys
d = json.load(open("digest/data/backstory.json"))
rows = {r["id"]: r for r in d["rows"]}
bad = []
for p in d.get("todays_pairings", []):
    o = p.get("origin")
    if not o or o.get("status") not in ("retrieved", "fallback"):
        bad.append(f"{p['story_id']}: no origin"); continue
    if o["status"] == "retrieved":
        y = o.get("year"); start = int(rows[p["row"]]["start_date"][:4])
        if not isinstance(y, int) or y < start:
            bad.append(f"{p['story_id']}: year {y} before row start {start}")
        if not str(o.get("line", "")).startswith("When "):
            bad.append(f"{p['story_id']}: line does not start with When")
        if o.get("verified") is not False:
            bad.append(f"{p['story_id']}: origin is marked verified")
if bad:
    sys.exit("OPEN: %d problems, e.g. %s" % (len(bad), bad[0]))
PY
```

Criteria 2 and 3 are the editor's judgement and are not in the check.
