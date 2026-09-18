---
id: T-0019
title: The next digest keeps its sentence rhythm after the em-dash ban
status: DECIDED
tags: [editorial, decision]
anchor: ntk-pulse/data/lineup-publish.json
---

## What

After the next Generate Jefferson, measure the published lineup and confirm
two things at once: em dashes dropped, and the prose did not go flat paying
for it.

`scripts/measure-output.py` reports both. Baseline, measured 2026-09-18 on
the lineup published before either rule took effect:

- 34 em dashes across 8 stories
- 31 sections long enough to measure
- 2 of 31 sections (6%) run three or more sentences under nine words
- median sentence-length stdev 13.1, median sentence 22.9 words

## Why

T-0017 asserts that the em-dash ban systematically converts subordination
into parataxis, because its own instruction says a sentence carrying two
ideas "wants to be two sentences," and that this is the mechanical cause of
prose that reads flat. **That assertion is not supported by any measurement
and should not be repeated as though it were.** The baseline above is
pre-ban output: rhythm was already varied, 6% of sections flat, median stdev
13.1. It tells you nothing about what the ban does, because the ban had not
run yet.

The first attempt at this measurement was wrong and the error is worth
recording. The published sections are HTML, and the strip regex targeted
markdown links, so `<a href="...">` blobs counted as words and one sentence
measured 137 words long. The resulting standard deviations ran to 38.8 and
looked like healthy variation. A measurement that produces plausible numbers
from the wrong input is the most expensive kind, because nothing about it
invites a second look.

What this ticket protects: the em-dash decision in `docs/decisions.md` is
explicit that the next digest is the evidence, and that a bounded
deterministic pass becomes the answer only if prompt-only rules fail. Two
rules now govern the same sentences from opposite directions, rule 8 pushing
sentences apart and rule 9 holding them together. If output em dashes fall
and rhythm holds, both worked. If em dashes fall and rhythm collapses, rule 9
lost and the exemplar needs more work, not the rule. If em dashes do not
fall, that is T-0004's answer, not this one.

## Check

```sh
python3 - <<'PY'
import html, json, re, statistics, sys
d = json.load(open('ntk-pulse/data/lineup-publish.json'))
stories = d.get('stories', [])
SEC = ['truth', 'prob', 'poss', 'lies']

# Rhythm on a pre-rule lineup measures nothing. Em dashes date the file:
# above the T-0004 threshold, this digest was written before the rules ran.
dash = sum((s.get(f) or '').count('—')
           for s in stories for f in ['headline', 'lede'] + SEC)
dash += ((d.get('today') or {}).get('text') or '').count('—')
if dash > 3:
    sys.exit('lineup predates the rules (%d em dashes) - regenerate, then re-measure' % dash)

def clean(t):
    t = re.sub(r'\([^()]*<a [^>]*>[^<]*</a>[^()]*\)', '', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()

rows = []
for s in stories:
    for f in SEC:
        lens = [len(x.split()) for x in
                re.split(r'(?<=[.!?])\s+', clean(s.get(f) or '')) if x.strip()]
        if len(lens) < 6: continue
        run = best = 0
        for n in lens:
            run = run + 1 if n < 9 else 0
            best = max(best, run)
        rows.append((best, statistics.pstdev(lens)))
if len(rows) < 10:
    sys.exit('only %d measurable sections - not enough to judge rhythm' % len(rows))

flat = sum(1 for r in rows if r[0] >= 3)
pct = 100 * flat / len(rows)
if pct > 20:
    sys.exit('%d%% of sections run 3+ short sentences (baseline 6%%, ceiling 20%%)' % pct)
sd = statistics.median([r[1] for r in rows])
if sd < 8:
    sys.exit('median sentence-length stdev %.1f (baseline 13.1, floor 8)' % sd)
PY
```
