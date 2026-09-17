---
id: T-0012
title: The seven Still Counting rows are unreachable by the classifier
status: DECIDED
tags: [backstory, defect]
anchor: editorial/build_backstory.py:153
---

## What

`build_backstory.py` creates the seven Still Counting rows with
`subgenres: []`. The classifier assigns a story to a **sub-genre** and
`build_vocabulary()` skips any row with none, so those seven can never be
chosen. A Gaza story cannot reach the Gaza row.

Confirmed by the 2026-09-17 publish: all eight pairings landed on Lifetimes
rows — `power`, `america-abroad`, `government`, `climate`, `media`.

## Why

Seven of twenty-one rows are inert, which is a third of the library, and they
are the seven most likely to match a given day's news — active conflicts are
exactly what a daily digest covers.

It also explains part of the crowding in T-0011. With a third of the
vocabulary unreachable, stories pile onto the rows that remain.

Found while building `build_pairings.py` on 2026-09-16 and recorded in
`docs/backstory.md` as an open design gap rather than a bug — the decision of
what sub-genres these rows should carry is editorial and was never made. That
is still true, and this ticket does not make it.

T-0010's editor assignment reaches these rows manually, which is a workaround
and not a fix: it requires the editor to notice.

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
