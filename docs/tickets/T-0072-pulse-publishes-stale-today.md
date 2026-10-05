---
id: T-0072
title: Pulse publishes the Today overview it happens to hold, even mid-generation or from weeks ago
status: BUILT
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html:2129
---

## What

2026-10-05. The editor generated Today from the Lineup, waited, and published. The six stories
on the digest were that day's. The Today tab's lead essay was the previous one: the published
`lineup-publish.json` carried `today.generatedAt` 2026-09-24 and the text of an earlier edition.
`ntknews.org/today` served exactly that, so it kept showing the old essay through any number of
hard refreshes until the editor generated the overview again in Pulse and published a second time.
Later, Pulse's own Today tab also showed the old text on first view and the new one only after a
hard refresh.

`publishToDigest()` sent `TODAY_OV.text` whatever its state. Nothing checked that Generate Today
had finished, that it had not failed, or that the text was from today. A failed generation is
stored as the text `[Generation failed: ...]` and would have been published as the essay.

Built 2026-10-05, in `ntk-pulse/pulse.html`:

- `todayPreflight()` runs before the existing story preflight (T-0022). It **blocks** publishing,
  with an alert, while Generate Today is running or after it failed. It **warns** in the existing
  confirm dialog when there is no overview, no generation time, or an overview generated on an
  earlier day, naming the date.
- A saved `busy: true` is cleared on page load. A reload kills any generation in flight, so the flag
  was always stale, and it could leave the button reading "Generating..." for good.

## Why

Blocked versus warned follows T-0022: where publishing would silently ship the wrong thing there is
no real choice to offer (running, failed); where it is the editor's call the dialog makes it visible
(stale, missing).

Ruled out as the cause: caching and the deploy. The live site's version tag matched the publish
commit and its HTML held the six published headlines. Not established: why Pulse's Today tab showed
old text on first load. The editor worked in one tab and waited after clicking Generate Today, so a
publish during a slow generation is the likely path but not proven. The guard closes that path and
the stale-text path whatever the display bug turns out to be; if the display bug recurs, look at how
`render()` reads `TODAY_OV` against what `saveToday()` stored.

Pulse is served from GitHub Pages, so a merge to main is the deploy and an open Pulse tab needs a
hard refresh to pick up the change.

## Check

```sh
set -e
node - <<'JS'
const fs = require('fs');
const s = fs.readFileSync('ntk-pulse/pulse.html', 'utf8');
const i = s.indexOf('function todayPreflight'), j = s.indexOf('\n}\n', i) + 3;
if (i < 0) { console.error('todayPreflight is missing'); process.exit(1); }
const run = (ov) => new Function('TODAY_OV', 'now', s.slice(i, j) + '; return todayPreflight(now);')(ov, new Date('2026-10-05T21:25:00Z'));
const fresh = '2026-10-05T21:20:00Z';
const cases = [
  [{text: 'old', generatedAt: '2026-09-24T19:57:53Z', busy: true}, r => r.block.length === 1],
  [{text: '[Generation failed: 429]', generatedAt: fresh, busy: false}, r => r.block.length === 1],
  [{text: '', generatedAt: null, busy: false}, r => !r.block.length && r.warn.length === 1],
  [{text: 'old', generatedAt: '2026-09-24T19:57:53Z', busy: false}, r => !r.block.length && /Sep 24/.test(r.warn[0] || '')],
  [{text: 'fresh', generatedAt: fresh, busy: false}, r => !r.block.length && !r.warn.length],
];
cases.forEach(([ov, ok], n) => { if (!ok(run(ov))) { console.error('case ' + (n + 1) + ' failed'); process.exit(1); } });
if (!s.includes('TODAY_OV.busy = false;')) { console.error('stale busy flag is not cleared on load'); process.exit(1); }
JS
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' ntk-pulse/pulse.html > "${TMPDIR:-/tmp}/t0072.js"
node --check "${TMPDIR:-/tmp}/t0072.js"
```
