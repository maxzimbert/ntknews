---
id: T-0025
title: Nothing in the app says what a beat is, what the chip means, or how to reach the next rung
status: DECIDED
tags: [digest, feature]
anchor: digest/index.html:4244
---

## What

Two surfaces show a reader their status and neither explains it.

The **beat scale** on Profile renders seven coloured pills — Skimmed, Briefed,
Read It, Following It, On the Beat, Carrying It, Witness — as a static legend.
They are not interactive. A reader has no way to learn what any of them means.

The **chip** in the digest header shows one label and links to Profile. On a
first encounter it is an unexplained word in the corner of the screen.

Wanted, per the editor 2026-09-18:

- Tapping a rung on the scale opens a small explainer, one to three sentences.
- Tapping the chip explains what it means the first time. After that has been
  seen, tapping it says what would reach the next rung.

## Why

`docs/backlog.md` already records the diagnosis: *"A working no-account
localStorage implementation is live. What's missing is legibility — a reader
can't tell what it is or how it works."* This is that ticket.

The second half is the harder half and the reason to do them together. "How
you reach the next rung" is the first thing in this system that tells a reader
what to *do*, and it is one register away from a quest log. The Expertise
briefing's whole argument is that the product recognises behaviour that was
already happening rather than manufacturing it: *"a portrait, not a
scoreboard."* So the copy describes the behaviour a status is made of, and
never issues an instruction. "Witness goes to readers who followed a subject
across months and passed it on" is a description. "Read 3 more stories to
reach Witness!" is a scoreboard, and it would also be the Kindergarten Teacher
failure mode named in `docs/decisions.md`.

The next-rung text is generated from the same `beatIdx` thresholds the ladder
scores with, not written out by hand. Copy that describes thresholds is copy
that goes quietly wrong the next time they move, and they moved twice on
2026-09-18 alone.

Deliberately not included: any surface on the story cards themselves. The
briefing's open question 09 is explicit that per-story status "turns reading
into performance."

## Check

```sh
python3 - <<'PY'
import re, sys
s = open('digest/index.html', encoding='utf-8').read()

# Every rung is reachable, not just decorative.
m = re.search(r'BEATS_SCALE\.map\([\s\S]{0,600}?\)\.join', s)
if not m or 'onclick' not in m.group(0):
    sys.exit('the beat scale pills are still a static legend')

# There is copy for all seven, and it is not the toast copy reused.
m = re.search(r'(?:function|var|const)\s+beatsExplain[\s\S]*?\n\}', s)
if not m: sys.exit('no explainer copy for the beat scale')
covered = {int(n) for n in re.findall(r'idx\s*===\s*(\d+)', m.group(0))}
missing = sorted(set(range(7)) - covered)
if missing: sys.exit('rungs with no explainer: %s' % missing)

# The chip explains itself, then explains what is next.
m = re.search(r'id="beatChip"[^>]*onclick="([^"]+)"', s)
if not m: sys.exit('the chip has no click handler')
if 'switchTab' in m.group(1) and 'beat' not in m.group(1).lower():
    sys.exit('tapping the chip still only switches tabs')
if 'beatsNextRung' not in s:
    sys.exit('nothing derives what would reach the next rung')

# ...derived from the scorer, not hand-written thresholds.
m = re.search(r'function beatsNextRung\([\s\S]*?\n\}', s)
if not m: sys.exit('beatsNextRung not found')
if 'beatIdx' not in m.group(0):
    sys.exit('beatsNextRung does not consult beatIdx, so its copy can drift from the scoring')
PY
```
