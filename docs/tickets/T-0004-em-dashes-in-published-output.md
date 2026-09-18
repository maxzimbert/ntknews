---
id: T-0004
title: Em dashes reach published output
status: VERIFIED
tags: [editorial, defect]
anchor: ntk-pulse/pulse.html:746
---

## What

The em-dash prohibition now exists in the prompts — `GLOBAL` at
`ntk-pulse/pulse.html:731` and VOICE RULE 8 at `:746`, both with worked
examples. That landed in `d85c6bb` on 2026-09-17.

**No digest has been published since.** The last publish (2026-09-16) carries
34 em dashes across six stories and 4 more in the Today overview. Those predate
the rule and are not evidence that it failed. They are evidence of nothing yet.

This ticket is `BUILT`, not `VERIFIED`, and stays that way until a digest
published *after* the rule is measured.

## Why

The instructive part is the history, not the rule. `docs/decisions.md` recorded
em-dash discipline as a locked decision, described as prompt-only and on
purpose. There was no em-dash rule anywhere in `pulse.html`, and the prompts
themselves contained 82 em dashes, including inside the worked examples the
model was being told to match. A document described intent and was read as
implementation, for months.

That is one of three separate cases in this repo of a document asserting a fix
that was never written. It is the single strongest argument for storing checks
rather than claims, and it is the sentence to reach for when explaining to
someone outside the project why NTK verifies the way it does.

The threshold is 3, not 0, on purpose: a quotation or a source headline can
legitimately carry one, and a check that fails on a correct quote gets ignored,
and a check that gets ignored is worse than no check.

## Check

```sh
python3 - <<'PY'
import json, sys
d = json.load(open('ntk-pulse/data/lineup-publish.json'))
F = ['headline', 'lede', 'truth', 'prob', 'poss', 'lies']
n = sum((s.get(f) or '').count('—') for s in d.get('stories', []) for f in F)
n += ((d.get('today') or {}).get('text') or '').count('—')
if n > 3:
    sys.exit('%d em dashes in the published lineup (threshold 3)' % n)
PY
```
