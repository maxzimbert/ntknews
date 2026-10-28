---
id: T-0111
title: Backstory research runs only when the library is thin, every find joins the shared library, and no subject is searched twice
status: DECIDED
tags: [backstory, feature]
anchor: editorial/compose_category.py:174
---

## What

The material half of the 2026-10-28 decision (`docs/decisions.md`). Measured on `origin/main`
2026-10-28:
- Web search runs in two places: `compose_category.find_milestones` at publish (`call_search`, up to
  8 searches per call) and Pulse's ask box (`aiSearch`, 5 per call).
- `compose_category.py` searches whenever it picked fewer than six objects, "always asked, not only
  when the matrix is thin".
- What search finds is stored as `custom_objects` inside the one category that found it. 21 such
  objects sit across 9 categories in `ntk-pulse/data/provisional-rows.json`. The shared pool
  (`ntk-pulse/data/backstory-pool.json`: 334 matrix, 109 candidates) does not include them, so another
  category or story on the same subject cannot use them and searches again.

Wanted:
1. **A research ledger** (`editorial/research-ledger.json`): one entry per subject searched (a lens
   plus a topic, for example `israel` / coalition politics), the date, the searches spent, and the
   objects found. Every find that passes the existing checks (link returned by the search, primary
   source, link checker) goes into the shared pool as a candidate, labelled unreviewed, and is usable
   by any story.
2. **Search only on a gap.** Research runs when T-0110's composer reports a story short of three
   verified Beginnings, and only for a subject the ledger has not searched recently. A subject already
   searched is not searched again unless the editor asks for it in Pulse.
3. **A budget.** Each draft run has a cap on search calls, and reports what it spent: searches, and
   subjects skipped because the ledger already had them.
4. **The editor's rejections stick** (the 2026-10-12 publishing rule): a rejected find stays in the
   ledger as rejected and is never proposed again.
5. **Tried on staging** with the Israel election story: one research pass for Israeli coalition
   politics (the 1948 declaration, which was fetched and checked 2026-10-28 on Avalon, is one find
   it should reach), then a second Israel story in a later draft uses the ledger with no new search.

## Why

The editor's constraint, 2026-10-28: do not spend on the same web searches over and over. Today's code
repeats them by construction: a find is kept only where it was found, and search runs whether or not
the library could already answer. The Israel election failure is a gap in the library, and filling it
once serves every later Israel story.

Ruled out: searching per story at publish (the cost grows with every edition, and results drift
between runs, the same reason `build_origins.py` has `--reuse`). Ruled out: writing finds straight
into the matrix. The matrix rule stands (`docs/decisions.md`, 2026-10-02): finds are candidates until
the editor approves them, and the 2026-10-13 rule on labelled news sources applies unchanged.

Unmeasured: the cost of one research call. Count it on staging (searches and tokens per call) before
setting the cap. Do not quote a price from memory.

## Check

```sh
python3 - <<'PY'
import json, os, sys
bad = []
if not os.path.exists('editorial/research-ledger.json'):
    bad.append('no research ledger, so nothing records what was already searched')
pool = json.load(open('ntk-pulse/data/backstory-pool.json'))
found = [o for o in pool['objects'] if o.get('found_by') == 'search']
if not found:
    bad.append('no search find is in the shared pool; finds still stay inside one category')
src = open('editorial/compose_category.py', encoding='utf-8').read()
if 'always asked, not only when the matrix is thin' in src:
    bad.append('compose_category.py still searches whether or not the library is thin')
if bad:
    print('\n'.join(bad)); sys.exit(1)
PY
```
