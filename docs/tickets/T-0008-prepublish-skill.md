---
id: T-0008
title: A prepublish skill that integrity-checks the lineup before it ships
status: BUILT
tags: [process, feature]
anchor: ntk-pulse/data/lineup-publish.json
---

## What

A `.claude/skills/prepublish/` skill: run against `lineup-publish.json` before
the publish button, report blockers. First pass would be the checks already
written as tickets — T-0001's onramp resolution, T-0004's em-dash count — plus
image presence per story and a `today.generatedAt` freshness bound.

## Why

Recommended as the first skill to build because its failure has already shipped
three times, and because writing it is the fastest way to learn what a check
block actually needs to contain.

The honest scoping note matters more than the feature. A skill is good at
bounded, verifiable work with a clear done condition. It is not good at taste.
`prepublish` can count em dashes and resolve keys. It cannot tell you whether
the lede lands, and a version that pretends to judge that would be worse than
none, because it would be trusted.

Held at `PROPOSED` deliberately: the checks it would run now exist as tickets
and run on a schedule, so the marginal value is convenience at the moment of
publishing, not coverage. Worth building when the ticket checks have proven
themselves and the shape is known — not before.

**Built 2026-09-18, and the condition above was met the hard way.** The
2026-09-18 edition shipped a story with no headline and four
`[INSUFFICIENT SOURCE MATERIAL]` sections, which turned two VERIFIED checks
STALE and put a blank crawlable permalink on the site (T-0022). The shape was
no longer hypothetical.

One thing the original scoping missed: **publishing happens in a browser**, so
a Claude skill cannot gate it. The gate is `publishPreflight()` in
`pulse.html`, at the button. This skill is the deeper pass, run deliberately
against a downloaded export before clicking, or against the published file
afterwards to find out what got through. Complementary, not duplicate.

Two warnings were narrowed by measurement rather than taste. Flagging any
section that cites no source fired on 22 of 48 sections across the last two
editions, because Probabilities, Possibilities and Lies argue from sourced
facts instead of re-citing them; Truths carried a citation in 12 of 12. So
only Truths is checked. A warning that fires on the normal case is one nobody
reads, which is worse than not having it.

## Check

```sh
test -f .claude/skills/prepublish/SKILL.md
test -f scripts/prepublish.py
# it has to run, and it has to fail on an edition that should not ship
python3 scripts/prepublish.py > /dev/null
python3 - <<'PY'
import json, subprocess, sys, tempfile
d = json.load(open('ntk-pulse/data/lineup-publish.json'))
d['stories'].append({'key': 'fixture', 'category': 'Politics', 'headline': '', 'lede': ''})
f = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
json.dump(d, f); f.close()
r = subprocess.run(['python3', 'scripts/prepublish.py', f.name], capture_output=True, text=True)
if r.returncode == 0: sys.exit('prepublish passed an edition with a headless story')
if 'BLOCKER' not in r.stdout: sys.exit('prepublish did not report a blocker')
PY
```
