---
id: T-0095
title: Pulse lists the categories the last publish made, and an archived category comes back when a story fits it
status: VERIFIED
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-15: after the 20:00Z publish created Spyware and Military execution policy,
neither was in Pulse's category list, so their thin Beginnings and objects could not be built out. Measured
that day: both were in `ntk-pulse/data/provisional-rows.json` on Pages, and a fresh load of Pulse listed all
eight categories. Pulse read that file once, at page load (`loadCatData()`); a tab opened before the publish
never saw what it made.

Also measured: the 30-day archive did not let a category come back. `apply_categories` marks a category with
no story in 30 days `archived`; Pulse listed only `provisional` ones, so an archived category vanished from
the list and the row dropdowns; and T-0089's matcher offered only live categories. Archived meant gone.

Fixed: the Backstory tab re-reads `provisional-rows.json` when its copy is over a minute old. Archived
categories are listed last ("archived (no story in 30 days): file a story to bring it back") and appear in
both row dropdowns; filing a story under one copies it into the editor's categories, so the next publish
sends it and CI makes it live again. The publish step offers archived categories to unfiled stories too,
and a match brings the category back. Tested: `test_compose_category.py` (an archived category is offered,
joining it makes it live, nothing composed; both fail on the old code); in a local Pulse, a stale copy was
re-read once and not again within the minute, an archived category was listed and offered, and filing a
story under it put it in the next publish.

## Why

Automatic categories are drafted with thin Beginnings on purpose and the editor builds them out; a category
the editor cannot open cannot be built out. And the archive is meant to keep the list tidy, not to throw away
a page the editor improved: a subject that goes quiet for a month (a court case between rulings) should
return with its history when it is news again, instead of a near-duplicate being composed.

## Check

```sh
python3 editorial/test_compose_category.py > /tmp/t0095.log 2>&1 || { grep FAIL /tmp/t0095.log; exit 1; }
grep -q "^ok   joining it brings it back" /tmp/t0095.log
python3 - <<'PY'
import re, sys
s = open('ntk-pulse/pulse.html', encoding='utf-8').read()
r = re.search(r'function renderBackstory\(root\)\{[\s\S]*?\n\}', s)
if not r or 'loadCatData()' not in r.group(0): sys.exit('the Backstory tab never re-reads the categories')
if "r.status==='archived'" not in s: sys.exit('archived categories are not listed')
PY
```
