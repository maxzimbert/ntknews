---
id: T-0013
title: The pairings step fails quietly and the Backstory tab shows yesterday
status: VERIFIED
tags: [pipeline, defect]
anchor: .github/workflows/pulse-publish.yml
---

## What

The "Build Backstory pairings" step in `pulse-publish.yml` is
`continue-on-error: true`. When it fails, the previous `todays_pairings` stay
in place, the digest ships, and nothing says anything. The workflow's own
comment tells you to check the step's log "when the Backstory tab looks like
yesterday" — which requires noticing, and the failure looks exactly like a day
when Backstory simply didn't change much.

## Why

**The `continue-on-error` is correct and should stay.** The digest is the
product; Backstory is additive. A classifier hiccup or a spent API budget must
never block a publish. That reasoning holds.

What is missing is not a gate, it is a **detector**. The right shape is the one
T-0001 already uses for the Today overview: compare what shipped against the
lineup it shipped beside, and fail loudly afterwards rather than blocking
beforehand.

This is exactly the caution recorded in `docs/proposals/ticketing.md` — a step
that fails quietly by design is fine, but a rot detector that fails quietly is
a second layer of prose claims with extra steps. The step stays quiet. The
check gets loud.

Passing as of 2026-09-17: eight pairings, eight stories, all resolving.

## Check

```sh
python3 - <<'PYCHK'
import json, sys
lp = json.load(open('ntk-pulse/data/lineup-publish.json'))
bs = json.load(open('digest/data/backstory.json'))
keys = [s['key'] for s in lp.get('stories', [])]
paired = [p.get('story_id') for p in bs.get('todays_pairings', [])]
missing = [k for k in keys if k not in paired]
stale = [p for p in paired if p not in keys]
bad = []
if missing: bad.append('%d published story(s) have no pairing: %s' % (len(missing), missing))
if stale:   bad.append('%d pairing(s) reference stories not in the lineup: %s' % (len(stale), stale))
if bad: sys.exit('\n'.join(bad))
PYCHK
```
