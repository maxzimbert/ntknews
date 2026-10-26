---
id: T-0097
title: Each Lineup story on Pulse's Backstory tab has a keyword search that ranks the Object Matrix by the story's own words and subject
status: VERIFIED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Asked for by the editor 2026-10-15, from `docs/proposals/object-matrix-retrieval.md`. Each story in the
Backstory tab's Lineup (T-0090) gets a keyword field beside its category selector. The keywords, plus the
story's subject ("Executive Power", "Work and Wages"), run a ranked search over the Object Matrix: title,
author, About text, Beginning line, row, sub-genre, theme and lenses, title and About weighted highest. The
editor adds what fits to the story's category. No model call; a search costs nothing.

Matrix only. The editor, 2026-10-15: candidates stay out of Backstory until they are moved off the
candidates sheet and into the matrix.

Measured on `main` 2026-10-15 before this change:
- The only pool search in Pulse is "+ Add an object" inside a category: one phrase, a substring match over
  title, author, year, lens and sub-genre, unranked, candidates included (`pulse.html`, `cat-find`).
- `backstory-pool.json` has no theme (column E, "Issue (Theme)"; 22 values) on any of its 430 objects.
- The automatic composer gathers matrix objects only through a shared lens or sub-genre
  (`compose_category.pool_for`) and runs a web search whenever fewer than 6 objects are picked. The 8
  composed categories live on the site hold 2 to 6 matrix objects each; at least 7 of them searched.

Built 2026-10-15 on branch `T-0097-matrix-keyword-search`:
- `matrixSearch()` in the CATS block of `pulse.html`: keyword words count in full, subject words at half,
  a whole phrase found in a title or About adds more; two forms of one word match on a shared prefix of six
  letters or more ("manufacturing" finds "Manufactures"; "policing" does not find "policy"). Tested in
  `scripts/test_pulse_categories.js`, including a run with the matrix-only filter removed, which fails.
- On the Lineup: a keyword field and "find in matrix" beside each story's category. Under a category Pulse
  edits, each hit has "add"; under a fixed row or no filing, ticked hits start a new draft category with the
  story filed under it. Adding uses the same function as the category editor's "+ Add an object"
  (`catAddFromPool`), so an object with no stored text gets it written in one call, as before.
- `export_for_pulse.py` carries Theme; all 334 matrix objects have one. No other pool field changed.
- Exercised in a local Pulse (`scripts/preview.js`): search, add, start-a-category and the editor's own add
  path, no console errors. Not yet used by the editor on the live Pulse.

Seen while testing, not fixed: plain matching cannot find an object whose title does not carry the words and
which has no About text yet. "Iran nuclear deal" does not find the Joint Comprehensive Plan of Action. 216 of
334 matrix objects have no About text; writing it (priced, tabled 2026-10-15) would make them findable.

Not in this change, recorded so they are not lost: using the same ranking inside the publish-time composer
before its web search; the composer's use of unapproved candidates whose link loads
(`compose_category.eligible`), which the editor's rule above contradicts; and the 6-object search trigger.

## Why

The matrix holds 334 linked primary documents and the pages readers get draw on a small part of them,
because an object reaches a story only through a label: a row (median 13 objects, Equality alone 98), a
sub-genre (median 4) or a theme (textbook eras). Each is the wrong zoom for most stories. Searching with the
story's own words skips the label. The editor's aim is fewer web searches: every matrix object that fits a
story is one the composer does not have to search for, and a matrix object's facts were checked once
instead of found fresh each time.

Ruled out for now: a model re-rank of the results (costs per search; try plain scoring first) and
pre-writing text for every matrix object (priced at about $3.50 for 273 objects on the Batch API, sample
approved by the editor, tabled 2026-10-15 because it improves text more than it cuts searches).

## Check

```sh
python3 - <<'PY' || exit 1
import json, sys
o = [x for x in json.load(open("ntk-pulse/data/backstory-pool.json"))["objects"] if x["pool"] == "matrix"]
sys.exit(0 if o and sum(1 for x in o if x.get("theme")) >= 0.9 * len(o) else 1)
PY
node -e "
const fs=require('fs'), s=fs.readFileSync('ntk-pulse/pulse.html','utf8');
const m=s.match(/\/\* CATS:BEGIN \*\/([\s\S]*?)\/\* CATS:END \*\//);
const f=new Function(m[1]+'; return matrixSearch;')();
const objs=JSON.parse(fs.readFileSync('ntk-pulse/data/backstory-pool.json','utf8')).objects;
const a=f(objs,'Dred Scott',''), b=f(objs,'tariff','Work and Wages'), c=f(objs,'','Executive Power');
const ok=a.length && /dred scott/i.test(a[0].o.title)
  && b.length>=3 && b.every(h=>h.o.pool==='matrix')
  && c.length>=3;
process.exit(ok?0:1);" && grep -q 'class="bsr-lu-kw"' ntk-pulse/pulse.html
```
