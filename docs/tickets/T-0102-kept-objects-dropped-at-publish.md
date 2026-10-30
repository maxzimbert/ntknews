---
id: T-0102
title: Publishing drops objects the editor kept for a story but never added to a category, and says nothing
status: VERIFIED
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html:3127
---

## What

Measured 2026-10-26 against `origin/main`. On Pulse's Backstory tab, ticking a matrix search
result stores the object on the Lineup story (`s.bsPicks`, built in T-0098). Each tick shows up
under "KEPT FOR THIS STORY", and the reader preview lists it as "KEPT, NOT ADDED YET". An object
only reaches a category when the editor presses **add N to <category>** or **new category from
these**. Nothing in the publish path reads `bsPicks`: `publishToDigest` runs `todayPreflight`,
`publishPreflight` and `rowPreflight`, and none of them looks at kept objects. The **add**
button also never appears for a story filed under a fixed row, which takes its objects from
`backstory-rows.json`.

Decided: publish warns, in the same confirm dialog as the Today overview warning (T-0096), for
every Lineup story that has kept objects not on its category. The warning names the story and the
count. It warns rather than blocks, because leaving a tick behind can be deliberate.

**Re-checked and closed 2026-10-30.** Since T-0110 the objects ticked in the matrix search are the editor's
picks for the story's own page: they travel as `bs_edits.keep`, always reach the case, and publish ships them
with the drafted page. The publish warning still fires for a pick that is on no drafted page (`keptPreflight`
counts a fresh draft's case as reaching the reader). Check run and passing on branch `T-0110-compose-per-story`.

## Why

The editor tested T-0091 and assumed "kept, not added yet" meant the objects would be added at
publish. The label reads that way. The cost is silent: the objects the editor chose by hand for a
story do not reach the reader, and nothing on the published page shows that they are missing.
This is the same failure T-0096 fixed for the Today overview: Pulse holding a state the editor
believes is shipping when it is not. Adding objects on publish was ruled out, because adding moves
an approved category back to draft (`catAddFromPool`) and so would quietly unapprove it at the
moment of shipping. Rewording the label alone was ruled out because a label does not stop a
publish.

## Check

```sh
node - <<'JS'
const fs = require('fs');
const s = fs.readFileSync('ntk-pulse/pulse.html', 'utf8');
const i = s.indexOf('function keptPreflight');
if (i < 0) { console.error('OPEN: keptPreflight does not exist; publish never looks at kept objects'); process.exit(1); }
const j = s.indexOf('\n}\n', i) + 3;
const f = new Function(s.slice(i, j) + '; return keptPreflight;')();
const cats = { ai: { objects: [{ object_id: 'o1' }] } };
const w = (lineup) => f(lineup, cats) || [];
const left = w([{ key: 'a', title: 'Robots write prescriptions', backstoryRow: 'ai', bsPicks: ['o1', 'o2', 'o3'] }]);
const fixed = w([{ key: 'b', title: 'Senate stalls', backstoryRow: 'government', bsPicks: ['o9'] }]);
const done = w([{ key: 'c', title: 'Done', backstoryRow: 'ai', bsPicks: ['o1'] }]);
const none = w([{ key: 'd', title: 'None', backstoryRow: 'ai', bsPicks: [] }, { key: 'e', title: 'Unset', backstoryRow: 'ai' }]);
const bad = [];
if (left.length !== 1 || !/Robots write/.test(left[0]) || !/\b2\b/.test(left[0])) bad.push('two objects left off a Pulse category are not named with their count');
if (fixed.length !== 1 || !/Senate stalls/.test(fixed[0])) bad.push('kept objects on a fixed-row story are not warned about');
if (done.length || none.length) bad.push('warns about a story with nothing left to add');
const p = s.slice(s.indexOf('async function publishToDigest'), s.indexOf('const stories = all.filter', s.indexOf('async function publishToDigest')));
if (!/keptPreflight\(LINEUP/.test(p) || p.indexOf('keptPreflight') > p.indexOf('preflightDialogText')) bad.push('publish does not put the warning in its confirm dialog');
if (bad.length) { console.error(bad.join('\n')); process.exit(1); }
JS
```
