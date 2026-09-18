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

A **subjects tab** in Pulse shows the vocabulary whole: every subject, how many
lineup stories use it, the concepts that turned up beneath each, and rename in
place. Rename is the load-bearing part. With nothing to fold onto, the first
spelling of a subject becomes canonical, and without a rename the only way to
fix a bad one would be to edit every story that used it.

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

**Seeded, then free-form.** The editor expected a drafted starting list and
said so on 2026-09-18: *"part of me thinks you could do it just as well or
better (and faster) than I could do it this one-by-one way."* Seeding and
free-form are not alternatives. `seedSubjects()` writes 21 on first run and
`draftMeta` may still coin a new one when none fits.

The 21 were derived rather than invented: from the Backstory rows, which are
already a considered map of what NTK follows; from the 612 article titles in
the live window, where Trump and the White House, Russia, Anthropic, Iran, the
Pentagon, Medicaid and the DOJ dominate; and from the editorial pillars in
`GLOBAL`. Four Backstory rows were left out on purpose. Order, Power, Equality
and Faith are a historian's categories, right for pairing a story to a long arc
and wrong for a reader, who does not say they follow Power; they say they
follow the courts, or guns, or abortion. Those are in the list instead.

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
import importlib.util, os, re, subprocess, sys, tempfile

def run_js(src, what):
    fd, path = tempfile.mkstemp(suffix='.js')
    os.write(fd, src.encode()); os.close(fd)
    r = subprocess.run(['node', path], capture_output=True, text=True)
    os.unlink(path)
    if r.returncode:
        sys.exit(r.stderr.strip() or (what + ' fixture run failed'))

def grab(text, pat, what):
    m = re.search(pat, text)
    if not m: sys.exit(what + ' not found')
    return m.group(0)

# ── Pulse holds a vocabulary, folds duplicates into it, and drafts into it ──
p = open('ntk-pulse/pulse.html', encoding='utf-8').read()
draft = grab(p, r'async function draftMeta\([\s\S]*?\n\}\n', 'draftMeta')
if '"subject"' not in draft:
    sys.exit('draftMeta does not propose a subject')
if 'knownSubjects()' not in draft:
    sys.exit('draftMeta is not shown the subjects in use, so the vocabulary will drift')

# Folding is the entire defence against drift, so run it rather than read it.
run_js('var LINEUP=[{subject:"Artificial Intelligence"}], SUBJECTS=["Ukraine"];\n'
       + grab(p, r'function knownSubjects\([\s\S]*?\n\}', 'knownSubjects') + '\n'
       + grab(p, r'function normalizeSubject\([\s\S]*?\n\}', 'normalizeSubject') + '\n'
       + 'var cases = ['
       + '["artificial intelligence","Artificial Intelligence","a case variant is not folded onto the existing subject"],'
       + '["  ukraine  ","Ukraine","whitespace and case are not folded"],'
       + '["Housing.","Housing","trailing punctuation is not stripped"],'
       + '["","","an empty subject does not stay empty"]];\n'
       + 'var bad = cases.filter(function(c){ return normalizeSubject(c[0]) !== c[1]; });\n'
       + 'if (bad.length){ console.error(bad.map(function(c){return c[2];}).join("; ")); process.exit(1); }',
       'normalizeSubject')

# ── The pipeline carries both fields through ───────────────────────────────
spec = importlib.util.spec_from_file_location('bd', 'ntk-pulse/build_digest.py')
bd = importlib.util.module_from_spec(spec); spec.loader.exec_module(bd)
block = bd.build_stories_block([{'key': 'k', 'category': 'Tech', 'headline': 'h', 'lede': 'l',
                                 'subject': 'Artificial Intelligence', 'entity': 'Anthropic'}])
for field, val in (('subject', 'Artificial Intelligence'), ('entity', 'Anthropic')):
    if '%s: "%s"' % (field, val) not in block:
        sys.exit('build_digest.py does not publish %s' % field)

# ── The digest keys to the subject, and entities stay texture ──────────────
d = open('digest/index.html', encoding='utf-8').read()
run_js(grab(d, r'function storySubject\([\s\S]*?\n\}', 'storySubject') + '\n'
       + 'if (storySubject({subject:"Ukraine", category:"World"}) !== "Ukraine")'
       + '{ console.error("the section label wins over the subject"); process.exit(1); }\n'
       + 'if (storySubject({subject:"  ", category:"World"}) !== "World")'
       + '{ console.error("an edition published before T-0016 orphans its beats"); process.exit(1); }',
       'storySubject')

for m in re.finditer(r'beatsRecord\w+\(([^;]{0,120})', d):
    if '.category' in m.group(1) and 'storySubject' not in m.group(1):
        sys.exit('a beats call site is still keyed to the section label: ' + m.group(1)[:60])

idx = grab(d, r'function beatIdx\([\s\S]*?\n\}', 'beatIdx')
if 'entit' in idx.lower():
    sys.exit('beatIdx consults entities; they were decided to carry no status')

# ── And a published edition actually carries them ──────────────────────────
block = grab(d, r'const stories = \[[\s\S]*?\n\];', 'the published stories array')
cats = len(re.findall(r'category:\s*"', block))
subs = len(re.findall(r'subject:\s*"[^"]+"', block))
if subs != cats:
    sys.exit('%d of %d published stories carry a subject (publish once from Pulse)' % (subs, cats))
PY
```
