---
id: T-0016
title: Expertise is keyed to a section of the paper, not to anything a reader could be expert in
status: DECIDED
tags: [pulse, feature]
anchor: digest/index.html:2597
---

## What

`beatsRecordRead(s.category)` keys every beat to the story's section label —
World, Nation, Politics, Money, Tech, Health, Life, Under-Reported, Orienting
(`ntk-pulse/pulse.html:282`). The best sentence the system can construct is
"You're on the beat: Nation," and at four Nation stories a day it constructs it
on day two. With the 2026-09-18 ladder changes it reaches Witness in ten.

**Two fields, decided 2026-09-18 with the editor.**

`subject` — new, and what the ladder keys to. Free-form, proposed by the model
in `draftMeta` alongside the angle the editor already generates, editable in
Pulse. Not a fixed list.

`entity` — published from the `conceptEntity` Pulse already captures. Carries
**no status**. It renders as clippings beneath a subject on Profile: "Anthropic,
4 stories." Nothing to climb.

`category` stays exactly what it is, a place on the page. `beat` stays pipeline
plumbing. Neither is removed.

## Why

**The earlier scoping of this ticket was wrong and the correction is the
useful part.** It proposed a topic field and rejected `conceptEntity` on the
grounds that "the entity is a person or an institution, not a subject, and
clustering entities into domains client-side would mislabel." That reasoning
was about clustering entities *upward* into domains. The editor does not want
that. The ask, in their words, is a reader who is "expert in Apple but not
Tech, or Anthropic but not OpenAI." Entity granularity is the point, and Pulse
has captured it all along — `storyDataExport()` simply drops it.

**Why status and texture are split.** Status needs repetition. Measured with
`scripts/beats-sim.js`: one story every three days reaches Witness in about 40
days, which is the arc the seven rungs were designed for. Most entities appear
in one or two published stories ever, so a ladder keyed to entities would be
unclimbable and the map would fill with permanent Skimmeds. Subjects repeat;
entities do not. This is not a compromise invented here — it is section 05 of
the Expertise briefing, which is already built on regions (the Map) holding
specific moments (the Clippings).

**The known limit, stated rather than papered over.** The editor's fourth
example — expert in "how a banana reaches a market in New York" but not in
tariffs — is neither a subject nor an entity. It is a theme. Whether those two
land in one bucket is decided by how subjects get named, which is an editorial
judgment no mechanism supplies. This design does not solve that case and
should not claim to.

**Free-form was the editor's call, over a fixed vocabulary, and it carries one
real risk: drift.** "AI" and "Artificial Intelligence" become two regions on
the map, and a region that splits in two is a reader's history quietly being
halved. Mitigated rather than argued with: `draftMeta` is shown the subjects
already in use so it reuses instead of reinventing, and subjects normalise on
save (case, whitespace, punctuation). Neither constrains what the editor can
type.

**Cost, named.** This spans Pulse, the publish schema and the digest, and adds
a field to every story. The mitigation is that the field arrives pre-filled
from a step the editor already runs, so the work is correction rather than
authorship.

Sequenced after T-0024, T-0025 and T-0026, which are reader-facing, sit
entirely in `digest/index.html` and need none of this.

## Check

```sh
python3 - <<'PY'
import json, re, sys

p = open('ntk-pulse/pulse.html', encoding='utf-8').read()
if not re.search(r'\bsubject\b', p):
    sys.exit('Pulse has no subject field')
m = re.search(r'async function draftMeta\([\s\S]*?\n\}\n', p)
if not m: sys.exit('draftMeta not found')
if 'subject' not in m.group(0):
    sys.exit('draftMeta does not propose a subject')
if not re.search(r'(?i)(knownSubjects|subjectsInUse|existing subjects)', p):
    sys.exit('draftMeta is not shown the subjects already in use, so the vocabulary will drift')
if not re.search(r'function normali[sz]eSubject\(', p):
    sys.exit('subjects are not normalised on save')

b = open('ntk-pulse/build_digest.py', encoding='utf-8').read()
if 'subject' not in b or 'entity' not in b:
    sys.exit('build_digest.py does not publish subject and entity')

d = open('digest/index.html', encoding='utf-8').read()
m = re.search(r'const stories = \[[\s\S]*?\n\];', d)
if not m: sys.exit('published stories array not found')
block = m.group(0)
cats = len(re.findall(r'category:\s*"', block))
subs = len(re.findall(r'subject:\s*"[^"]+"', block))
if subs != cats:
    sys.exit('%d of %d published stories carry a subject' % (subs, cats))

keyed = re.findall(r'beatsRecord\w+\(\s*(?:stories\[[^\]]+\]\s*\?\s*)?stories\[[^\]]+\]\.(\w+)', d)
keyed += re.findall(r'beatsRecord\w+\(s\.(\w+)', d)
if 'category' in keyed:
    sys.exit('beats are still keyed to the section label')
if 'subject' not in keyed:
    sys.exit('beats are not keyed to the subject')

# Entities are texture. If they ever reach the scorer, the ladder stops meaning
# anything, because most entities appear once and can never be climbed.
m = re.search(r'function beatIdx\([\s\S]*?\n\}', d)
if m and 'entit' in m.group(0).lower():
    sys.exit('beatIdx consults entities; they were decided to carry no status')
PY
```
