---
id: T-0111
title: Backstory research runs only when the library is thin, every find joins the shared library, and no subject is searched twice
status: BUILT
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

**Built 2026-10-29, on branch `T-0110-compose-per-story` and on staging** (`editorial/research_story.py`). Research
runs when the editor presses "research it (1 call)" on a thin page, not on its own: the editor's cost
constraint, and four of six stories came back thin on the first real draft. The subject is the page's scope,
keyed so word order does not matter; a subject searched in the last 30 days is not searched again. At most 3
research calls per draft run. The search and its checks are `compose_category.find_milestones`, unchanged.
Finds go into `editorial/research-ledger.json` and `compose_story.load_library` reads them as library
documents for every story; rejections (`bs_rejected`) are kept in the ledger and keep a find out for good.
Tested with stubbed search replies: one search, the same subject reworded not searched again, a rejected find
kept out, finds in the shared library. Not run against the live model yet.
Not done, on purpose: `compose_category.py` still searches every time it makes a category. Readers still see
category pages until the reader app draws per-story pages (T-0110), so thinning categories now would cost
readers before it saves anything. Change it when the reader side ships; the check's third clause waits on it.
The check's second clause was changed before this was built, from "a find is in backstory-pool.json" to "a
find reaches the library stories compose from": the pool is Pulse's matrix-search index, and the composer
reads the ledger directly.

**Added 2026-10-29, from the editor's first real research runs.** Two runs on the Homeland Security names
story kept 4 documents and the checks turned down 4 (mostly a line a word or two over 25). The editor asked
for, and got:
- *Vetoed finds kept and shown*, each with the check that turned it down, in the story's RESEARCH section.
  "Approve: I checked it" overrules the checks: the find becomes a library document for every story
  (`approved_by: "editor"` in the ledger) and goes on this page. Reject keeps it out for good.
- *Directed research*: a box to point the search ("other hacks of government departments: OPM, FBI, and
  intrusions by Russia, China, Iran"). Only then may a milestone be a "comparable case", labelled as one, and
  the composer is told the editor asked for that history. This is not the "comparable case elsewhere"
  relation reverted on 2026-10-09 (`docs/decisions.md`): that one ran on the automatic path and padded pages;
  this one runs only on the editor's direction. A direction is a subject of its own, not refused because
  the page's subject was researched; the same direction is not searched twice in 30 days.
- A reworded page scope counts as the same subject (half the words shared), so recomposing no longer
  draws a second search, and runs queue instead of cancelling one another (T-0109).

**Moved into Pulse 2026-10-30, by the editor's call** ("keep GitHub out of it"): research, approvals and the
ledger run in the browser (`bsxResearch`, `bsxApprove`, `bsxLedger` in `ntk-pulse/pulse.html`), using Pulse's
existing `verifyMilestone` and text rules. `editorial/research_story.py` is retired. The ledger is still
`editorial/research-ledger.json`, written by Pulse through GitHub's API.

**The Object Matrix, 2026-10-30, the editor's rule: "Only things I have approved."** The matrix is the source of
truth; the research ledger is bookkeeping (what was searched and when, what waits, what was rejected) plus the
finds that passed the checks, usable on pages but not in the matrix. Approving (a vetoed find, an outline
candidate, a lead with the editor's own link, or "approve for the matrix" on a find) marks it
`approved_by: "editor"`. At publish `editorial/graduate_finds.py` adds each approved primary source to the
matrix spreadsheet (NTK Row = the story's fixed category, or blank), records it in
`editorial/matrix-additions.json` (never the ledger, which Pulse may be writing at the same moment), and
`export_for_pulse.py` rebuilds the pool. A news report can be approved onto a page and never enters the
matrix. `build_backstory.load_objects` now keeps a linked row with no NTK Row (none existed before), so such
documents reach the lens Beginnings and the pool. Tested on copies: three approved documents added, a news
report skipped, a second run added nothing, the loader read the new rows. New rows are not link-checked at
publish; `check_links.py` covers them on its next run.

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
# A find in the ledger is a library document for every story, and a rejected one is not (Pulse's composer).
import subprocess
js = r"""
const s=require('fs').readFileSync('ntk-pulse/pulse.html','utf8');
const grab=n=>{const i=s.indexOf('function '+n+'('); return s.slice(i, s.indexOf('\n}\n', i)+2);};
const lib=new Function('POOL','BSR_PUBLISHED','PUBCATS','catSourceKind', grab('bsxLibrary')+'; return bsxLibrary;')(
  {objects:[]}, {rows:[]}, [], ()=>'');
const led={finds:[{id:'custom-test-find',title:'T',year:'1958',url:'https://example.gov/t',researched_for:'test'}],rejected:[]};
const a='custom-test-find' in lib({stories:[]}, led); led.rejected=['custom-test-find'];
const b='custom-test-find' in lib({stories:[]}, led); console.log(JSON.stringify([a,b]));
"""
try:
    a, b = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True).stdout)
    if not a:
        bad.append('a research find does not reach the library other stories compose from')
    if b:
        bad.append('a rejected find is still in the library')
except Exception as e:
    bad.append(f'Pulse cannot load a ledger into its library ({e})')
src = open('editorial/compose_category.py', encoding='utf-8').read()
if 'always asked, not only when the matrix is thin' in src:
    bad.append('compose_category.py still searches whether or not the library is thin')
if bad:
    print('\n'.join(bad)); sys.exit(1)
PY
```
