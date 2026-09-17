---
id: T-0012
title: Seven rows carry no sub-genres and are unreachable by the classifier
status: DECIDED
tags: [backstory, defect]
anchor: editorial/build_backstory.py
---

## What

Seven of the 21 rows are created with `subgenres: []`. The classifier assigns a
story to a **sub-genre**, and `build_vocabulary()` skips any row that has none,
so those seven can never be chosen. A Gaza story cannot reach the Gaza row.

Confirmed by the 2026-09-17 publish: all eight pairings landed on the fourteen
rows that do carry sub-genres.

## Why

A third of the library is inert, and it is the third most likely to match a
given day's news — active conflicts are exactly what a daily digest covers.

It also explains part of the crowding in T-0011. With seven rows unreachable,
stories pile onto the fourteen that remain.

**The rows in question happen to be the ones that were called "Still
Counting", and that framing is retired** (decided 2026-09-17 — see
`docs/decisions.md`). Backstory is pairings now, so a row is just a row. The
two-strata distinction is not why these seven are unreachable and is not part
of the fix. What matters is one property: does a row carry sub-genres or not.

Reframing it that way makes the fix obvious, which the old framing obscured —
it read as a design question about two classes of row, when it is a data gap in
seven of them. **Give the seven sub-genres, the same as the other fourteen.**
That is editorial work: naming the sub-genres a conflict row should attract.

Note the interaction with T-0003: narratives are now written only for rows that
get paired, so an unreachable row is also a row that never gets a narrative.
These seven are invisible twice over.

T-0010's editor assignment reaches them manually, which is a workaround, not a
fix — it requires the editor to notice.

## Check

```sh
python3 - <<'PYCHK'
import json, sys
bs = json.load(open('digest/data/backstory.json'))
bare = [r['id'] for r in bs['rows'] if not r.get('subgenres')]
if bare:
    sys.exit('%d row(s) unreachable by the classifier: %s' % (len(bare), bare))
PYCHK
```
