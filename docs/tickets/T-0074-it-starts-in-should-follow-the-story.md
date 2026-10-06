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

## Check

manual: the editor reads a day's pairings and judges each jump from the story to the origin it
names. A mechanical check would measure the year gap, which would reward the wrong thing.
