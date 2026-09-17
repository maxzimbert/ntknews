---
id: T-0010
title: Pulse has no control to review or override a story's Backstory row
status: DECIDED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html:1905
---

## What

Backstory Slice 5, specified in `docs/backstory.md`: a control in Pulse's
certification flow that pre-fills the classifier's row assignment and lets the
editor override it before publish.

Today the classifier runs in CI *after* the publish button
(`pulse-publish.yml`, the "Build Backstory pairings" step), so the editor never
sees a row assignment before it ships. `todays_pairings` is raw model output.

## Why

**The failure this exists to prevent has now happened.** On 2026-09-17 three of
eight stories classified to `power` and two to `america-abroad`. The Backstory
card leads with the row's title, day count and milestone — all properties of
the row, not the story — so three cards rendered identically apart from one
sentence. The editor read it as "the new pairings didn't come through." They
had; they were just indistinguishable.

The classifier assigns each story independently and has no view of what the
others got. Nothing can catch a collision, because nothing is looking at the
set. A human reviewing the assignments sees it immediately and moves one story
to `government`.

**Two things fall out of this beyond the collision:**

Stories whose sub-genre does not map are **silently dropped**
(`build_pairings.py:207`) — the story count in does not have to equal the
entry count out, despite the roll-up spec saying it does. An editor assignment
cannot be dropped.

The seven Still Counting rows are created with `subgenres: []` and are
therefore unreachable by the classifier (T-0012). An editor assignment reaches
them, which makes this a partial fix for that too.

**Scope.** This ticket is the override and the collision warning — the part
that satisfies the recorded acceptance criterion. Running the classifier inside
Pulse so the editor sees the *proposed* assignment before publishing is
T-0014, kept separate because it needs an API call, a prompt fetch and model
plumbing, and because the manual control has to work whether or not that call
succeeds.

## Check

```sh
# Pulse writes the assignment into the published payload
grep -q "backstory_row" ntk-pulse/pulse.html
# and the generator honors it rather than re-classifying
grep -q "backstory_row" editorial/build_pairings.py
# an assignment survives a mock run end to end
python3 - <<'PY'
import json, subprocess, shutil, tempfile, os, sys, pathlib
root = pathlib.Path('.')
lp = json.loads((root/'ntk-pulse/data/lineup-publish.json').read_text())
bs = json.loads((root/'digest/data/backstory.json').read_text())
if not lp.get('stories'): sys.exit('no stories to test with')
target = lp['stories'][0]['key']
row = 'gaza'   # a Still Counting row: unreachable by the classifier
bak_lp = json.dumps(lp); bak_bs = (root/'digest/data/backstory.json').read_text()
lp['stories'][0]['backstory_row'] = row
(root/'ntk-pulse/data/lineup-publish.json').write_text(json.dumps(lp))
try:
    r = subprocess.run([sys.executable,'editorial/build_pairings.py','--mock'],
                       capture_output=True, text=True)
    if r.returncode: sys.exit('build_pairings --mock failed:\n'+r.stderr[-800:])
    out = json.loads((root/'digest/data/backstory.json').read_text())
    got = {p['story_id']: p['row'] for p in out.get('todays_pairings', [])}
    if got.get(target) != row:
        sys.exit('editor assignment lost: %s -> %r, expected %r'
                 % (target, got.get(target), row))
finally:
    (root/'ntk-pulse/data/lineup-publish.json').write_text(bak_lp)
    (root/'digest/data/backstory.json').write_text(bak_bs)
PY
```
