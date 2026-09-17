---
id: T-0001
title: The Today overview ships with onramp keys that do not resolve
status: DECIDED
tags: [pulse, defect]
anchor: ntk-pulse/build_digest.py:197
---

## What

Pulse sends whatever `today` object is in its state at publish time. Nothing
compares `today.generatedAt` against the lineup shipping beside it, and nothing
validates the `[STORY: key | label]` markers against `stories[].key`.

Measured 2026-09-17 against the published editions themselves:

| Edition | Markers | Stories | Dead |
|---|---|---|---|
| 2026-09-14 | 7 | 1 | **7** |
| 2026-09-16 | 7 | 6 | **1** — `4d7682928697e42e`, "Kennedy Center closes" |

The 2026-09-16 overview was generated at 20:44Z the same day, so this is not a
staleness problem in that instance. It is narrower and more ordinary: **a story
was cut from the lineup after the overview was written, and its onramp shipped
anyway.** The 2026-09-14 failure was the extreme version of the same thing — a
seven-story overview over a one-story digest.

The live SPA still carries the 09-16 text, so a reader today reads "the board's
response was to close the building" pointing at a story that isn't there.

## Why

The expensive part is that it is invisible. `renderTodayOverviewHtml()`'s
`idx === -1` guard works exactly as designed: it degrades a dead onramp to
plain text rather than emitting a broken link. So nothing errors, nothing
alarms, and the reader just encounters a sentence about a story they cannot
find. The guard is correct, and it is the reason nobody noticed.

The absence of a publish-time gate was deliberate — recorded in
`docs/decisions.md`, chosen so real failure modes would surface rather than be
swallowed by an approval step. That reasoning held: the failure did surface.
The decision has paid for itself and can now be revisited on those terms.

**The fix shape is Max's call and is not settled:** fail hard and refuse the
publish; warn and continue; or auto-regenerate the overview against the lineup.
The check is deliberately indifferent to which — it asserts the outcome, so any
of the three satisfies it.

**A caution earned writing this ticket.** The first version of this check
reported 7 of 7 dead on the 09-16 publish. It was wrong: the marker format is
`[STORY: key | label]` and the regex never stripped the label. Six of seven
resolved fine. A check that overstates is the same class of defect as a
document that overstates, and the only reason it got caught is that the output
was read rather than trusted. Run checks against real data before believing
them.

## Check

```sh
python3 - <<'PY'
import json, re, sys

def markers(text):
    return [r.split('|')[0].strip()
            for r in re.findall(r'\[STORY:\s*([^\]]+)\]', text or '')]

bad = []

# What will ship next
d = json.load(open('ntk-pulse/data/lineup-publish.json'))
keys = {s.get('key') for s in d.get('stories', [])}
dead = [r for r in markers((d.get('today') or {}).get('text')) if r not in keys]
if dead:
    bad.append('lineup-publish.json: %d dead onramp(s) %s' % (len(dead), dead))

# What readers see right now
s = open('digest/index.html', encoding='utf-8').read()
m = re.search(r'const todayOverview = "(.*?)";\n', s, re.S)
if m:
    live = set(re.findall(r'"key"\s*:\s*"([0-9a-f]{16})"', s)) | \
           set(re.findall(r'key:\s*"([0-9a-f]{16})"', s))
    dead = [r for r in markers(m.group(1)) if r not in live]
    if dead:
        bad.append('digest/index.html: %d dead onramp(s) %s' % (len(dead), dead))

if bad:
    sys.exit('\n'.join(bad))
PY
```
