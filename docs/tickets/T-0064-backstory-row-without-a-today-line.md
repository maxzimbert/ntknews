---
id: T-0064
title: A Backstory row whose story has no pairing line loses its TODAY block
status: VERIFIED
tags: [backstory, defect]
anchor: digest/index.html:3225
---

## What

Reported 2026-10-01 from a screenshot of the staged Backstory tab: the second
row (the Natalie Harp story, paired to The Media) had no TODAY label or
sentence. Cause, measured the same day: its entry in `todays_pairings` has
`line: ""`. The publish run logged "1 with no line" (`build_pairings.py:289`);
the pairing-line step returned nothing for that story, and the script tolerates
that on purpose. The tab skipped the whole TODAY block when the line was empty.
This was live on production from T-0057 on, not introduced by the overlay work.

Now the tab falls back to the story's own headline when there is no line. The
in-page "In the digest" lists and the static pages already did this
(`line or headline`).

## Why

A row with no TODAY sentence reads as a broken row and loses the tap target
into the story. The headline is the honest fallback, and the design handoff
describes the TODAY slot as the story's headline in quotes. Not fixed: why the
model returned no line for one story; re-running the publish workflow would
spend another classifier call and might not change it, so it was not done.
If this recurs often, make `build_pairings.py` retry a missing line once.

## Check

```sh
set -e
grep -q "r.pairline || r.headline" digest/index.html
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' digest/index.html > "${TMPDIR:-/tmp}/t0064.js"
node --check "${TMPDIR:-/tmp}/t0064.js"
```
