---
id: T-0112
title: Each story's Backstory proposes the visualization that fits it, and the editor can revise, nudge, verify or supply one
status: PROPOSED
tags: [backstory, feature]
anchor: editorial/compose_category.py
---

## What

**Parked 2026-10-30 by the editor: "Prod's rule."** For this stage of the product the chart stays one trend line
per category, the simple better-or-worse framing prod already has, and a story's own page (T-0110) shows its
category's trend line. The per-story chart below was built and taken out again before it reached prod; the
code is in the branch history at `84ed2b2d` (`editorial/visual_story.py` and the Pulse VISUALIZATION section).
What the first live use showed, for whoever reopens this: the proposals were good, but the check (both figures
on one original-source page, in one cited passage) refused most real series. Israel's Arab turnout runs to 2022
at the Israel Democracy Institute and the 2026 figure exists only in news reports, so no chart could be drawn.
A two-source chart, each figure checked on its own page, and showing a refused chart to the editor were
proposed and not built.


Raised by the editor 2026-10-28, looking at the hand-composed ballroom donors page in the mock
(https://claude.ai/artifact/GoNGTmRiM7mHsgQyub6LAa): it had no visualization, the better-or-worse
trend line the category pages carry. Measured on `origin/main` that day: the trend line is one series
per category (`docs/decisions.md`, 2026-10-12), proposed by `compose_category.propose_indicator` with a
web search when a category is created, and kept only if every value is checked on the publisher's page.
With per-story pages (T-0110) the series has no category page to sit on, and one series per category
fits only stories that happen to share its subject.

Wanted:
1. **Per-story proposal.** From the story's headline, lede and Truths, propose the one chart that would
   show the reader where today sits in the long run: what to measure, over what span, from which
   publisher. Inside T-0109's draft.
2. **The same sourcing rule.** Every value is read from the publisher's page and checked, as today. A
   proposed series with no source that carries it is shown to the editor as a proposal only, never
   drawn for readers. The chart is better-or-worse in the house style (terracotta is worse,
   `docs/design-system.md`).
3. **Reuse before search.** A series already found and checked for any story or category is reused
   (it joins T-0111's research ledger). Search only when no checked series fits.
4. **Editor zone in Pulse.** Revise (pick another measure), nudge in the editor's words, verify (mark
   each value checked against the source), or supply a series and source of the editor's own. No chart
   is a valid outcome and says why.

**Built 2026-10-29, on branch `T-0110-compose-per-story` and on staging** (`editorial/visual_story.py`, called
by `compose_story.py`). Every draft proposes with one small call and no search: reuse a checked series on
hand (the 19 category trend lines and anything earlier searches found), or name the measure that would fit,
or say no honest chart fits. A search runs only when the editor presses "search for a source (1 call)" in the
story's preview, uses `compose_category.propose_indicator`'s search and check unchanged, and a series that
passes is written to `editorial/research-ledger.json` so the next story reuses it. The editor can supply a
series (unchecked until ticked) or choose no chart, and nudge the section. Tested with stubbed model replies:
search found and checked, reused by a second story with no search, editor's series unchecked, no chart, and a
link the search did not return refused. Not run against the live model yet. The reader's app does not draw
`composed.visual` yet, as for the rest of the composed page (T-0110).

## Why

The trend line is the one place Backstory shows magnitude, not just sequence; dropping it with the
category page would lose it. The editor's example: how much a president and family made in office,
against every president since Washington. That is the kind of comparison a reader cannot get elsewhere
in one look, and also the kind most likely to have no publisher-checked series behind it. Unverified:
whether any source publishes it for all presidents. Wealth estimates exist for some (Forbes and
others) but are estimates, inconsistent in method across eras, and a chart built from them would carry
more certainty than the numbers do. A chart is a claim; the Truths/Lies frame means it is held to the
same standard as a sentence, which is why "no chart, and why" has to be an allowed answer.

Ruled out: drafting values from model knowledge (`docs/decisions.md`, 2026-10-06: never a drafted
indicator). Ruled out: one series per category as the only option, for the reason above.

Cost: a proposal call per story, plus search only on a miss. Measure on staging.

## Check

```sh
python3 - <<'PY'
import json, os, sys
p = 'ntk-pulse/data/backstory-draft.json'
if not os.path.exists(p):
    print('no draft, so no story has a proposed visualization'); sys.exit(1)
stories = json.load(open(p)).get('stories') or []
bad = []
for s in stories:
    v = (s.get('composed') or {}).get('visual')
    if v is None:
        bad.append(f"{s.get('story_id')}: no visualization and no reason"); continue
    if v.get('status') == 'drawn' and not all(x.get('source_url') and x.get('checked') for x in v.get('values') or [{}]):
        bad.append(f"{s.get('story_id')}: a drawn chart has a value with no checked source")
if not stories or bad:
    print('\n'.join(bad) or 'draft has no stories'); sys.exit(1)
PY
```
