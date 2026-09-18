---
id: T-0016
title: A beat is keyed to the section label, so "On the Beat: Nation" is the best the ladder can say
status: DECIDED
tags: [pulse, feature]
anchor: digest/index.html:2597
---

## What

`beatsRecordRead(s.category)` keys every Expertise beat to the story's
section label. The vocabulary is Pulse's `CATEGORIES` — World, Nation,
Politics, Money, Tech, Health, Life, Under-Reported, Orienting
(`ntk-pulse/pulse.html:282`), carried into the digest by `build_digest.py:144`.

The 2026-09-18 edition is Nation x4, World x2, Tech x1, Life x1. So the
strongest sentence the system can produce about a committed reader is
"You're on the beat: Nation," and at four stories a day it can produce it on
day two.

The decision is to add a topic to the story record in Pulse, publish it
alongside `category`, and key beats to it. The section label stays what it
is — a place on the page. Nothing here is built.

## Why

The Expertise briefing's entire argument rests on the beat being a subject a
reader followed: "You've followed housing policy through eight stories and
gone into the history more than once." Housing is not a section. Keying to
the section label produces a status that is simultaneously trivial to earn
and meaningless to hold, and no amount of better copy on top of it fixes
that.

Two cheaper routes were considered and rejected on 2026-09-18.

Retuning the thresholds against the existing labels would slow the ladder
down without making it say anything truer; "On the Beat: Nation" is not a
claim about a reader no matter how many stories it takes. Deriving a topic
from `conceptEntity` — which Pulse already resolves per story as a Wikipedia
title — needs no new editor work, but the entity is a person or an
institution, not a subject, and clustering entities into domains client-side
would mislabel quietly and constantly. A wrong beat is worse than a coarse
one: it is the product telling a reader something false about themselves.

The cost is real and should be named. This touches the publish schema, so it
is the first change since the ticketing system that spans Pulse, the
pipeline and the digest at once. It also adds a field the editor has to set
or approve per story, which runs against the standing preference for fewer
gates in the Lineup-to-Publish path recorded in `docs/decisions.md`. The
mitigation is to draft it with the angle in `draftMeta` and let the editor
correct it, not to add a required step.

Sequenced behind T-0015 on purpose. T-0015 fixes what the ladder says and
what it counts, entirely inside `digest/index.html`, and is reviewable in one
deploy preview. This one changes what it counts against.

## Check

```sh
python3 - <<'PY'
import re, sys

p = open('ntk-pulse/pulse.html', encoding='utf-8').read()
if not re.search(r'const TOPICS\s*=\s*\[', p):
    sys.exit('Pulse has no topic vocabulary separate from CATEGORIES')

b = open('ntk-pulse/build_digest.py', encoding='utf-8').read()
if 'topic' not in b:
    sys.exit('build_digest.py does not publish a topic')

d = open('digest/index.html', encoding='utf-8').read()
m = re.search(r'const stories = \[[\s\S]*?\n\];', d)
if not m: sys.exit('published stories array not found')
block = m.group(0)
cats = len(re.findall(r'category:\s*"', block))
tops = len(re.findall(r'topic:\s*"[^"]+"', block))
if tops != cats:
    sys.exit('%d of %d published stories carry a topic' % (tops, cats))

m = re.search(r'function beatsRecordRead\([\s\S]*?\n\}', d)
if not m: sys.exit('beatsRecordRead not found')
callers = re.findall(r'beatsRecord\w+\(\s*stories\[[^\]]+\]\s*\?\s*stories\[[^\]]+\]\.(\w+)', d)
callers += re.findall(r'beatsRecord\w+\(s\.(\w+)\)', d)
if 'category' in callers:
    sys.exit('beats are still keyed to the section label')
if 'topic' not in callers:
    sys.exit('beats are not keyed to the topic')
PY
```
