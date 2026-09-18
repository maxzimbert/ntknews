---
id: T-0022
title: A story the model refused to write ships as a blank card and a crawlable permalink
status: BUILT
tags: [pulse, defect]
anchor: ntk-pulse/data/lineup-publish.json
---

## What

The 2026-09-18 publish shipped five stories. The fifth, key `21228b1b2cadf96f`,
category Politics, has an empty headline, an empty lede, and all four sections
reading `[INSUFFICIENT SOURCE MATERIAL]` followed by the model's own note that
one source returned a headline only and another was a Cloudflare block page.

That is `GLOBAL` working exactly as written: *"If source articles don't
support an item, write [INSUFFICIENT SOURCE MATERIAL] - do not invent."* The
model refused correctly. Pulse published the refusal.

Measured on production 2026-09-18:

- The digest card renders as `5 05 POLITICS Read →`, 111px tall, no headline,
  no lede.
- `build_digest.py` generated a permalink at `digest/2026-09-18/story/` from
  an empty slug. It returns 200 on ntknews.org, its `<title>` is
  ` — NTK News`, its `og:title` is empty, and its body is the refusal note
  naming Cloudflare.
- Two VERIFIED tickets went STALE on this publish and both trace here: T-0018
  (landing claims 6-10 stories, the digest shipped 5) and T-0013 (one
  published story has no Backstory pairing, because there is no story).

## Why

**How it got there, from the editor, 2026-09-18:** a rushed publish during
testing. That is the accurate account and it matters for scoping, because it
means this was not a pipeline fault and there is no upstream bug to hunt. It
does not change what the ticket is for. The editor rushing is the expected
case, not the exceptional one, and nothing between the model's refusal and a
live crawlable page raised an objection.


`docs/decisions.md` requires permalink pages to be static specifically so
crawlers can index them, and a crawler never executes JS. That decision is
load-bearing and it is why this page is worse than the card: the card is
today, the permalink is permanent and indexable.

The defect is not the refusal, and any fix that makes the model write
something anyway is the wrong fix. `[INSUFFICIENT SOURCE MATERIAL]` is the
guardrail against invention, and the editorial pillars depend on it. The
defect is that nothing between the model and the reader looks at the result.

**Two halves, and the precedent says both.** `docs/decisions.md` records that
bold-spacing and section self-labeling each needed a prompt rule *and* a
deterministic code fix, because testing proved the prompt alone insufficient.
Same shape here:

1. Pulse warns at publish when a story has no headline or when every section
   is `[INSUFFICIENT SOURCE MATERIAL]`, offering the same two paths the
   Today-overview integrity gate already offers, decided 2026-09-16: drop it,
   or ship anyway. Not a hard block.
2. `build_digest.py` emits no card and no permalink for a story with an empty
   headline. A slug that resolves to `story/` is itself the tell that nothing
   checked.

This is the concrete evidence for T-0008, the proposed prepublish integrity
skill, which has been sitting at PROPOSED without a failure to point at.

Remediation before the fix lands: republish from Pulse with the story
removed. The permalink directory needs deleting by hand, since
`build_digest.py` only adds. Done 2026-09-18; `digest/2026-09-18/story/` is
gone and returns 404.

**Built 2026-09-18.** `drop_headless()` in `build_digest.py` removes them once,
before slugs are computed, so the card, the hero, the permalink page, the
archive and `_headlines.json` are all covered by one filter. It skips rather
than raises: one bad story should cost the edition a card, never the publish.
`publishPreflight()` in `pulse.html` names them at the button.

**"Ship it anyway" is deliberately not offered.** The 2026-09-16 Today-overview
decision established warn-with-a-choice, and the two paths there were both
real. Here they would not be: `build_digest.py` now builds nothing for a
headless story, so a button promising to publish one would be lying. The
choice offered instead is real — publish without it, or stop and fix it.

## Check

```sh
python3 - <<'PY'
import json, os, re, sys
d = json.load(open('ntk-pulse/data/lineup-publish.json'))
bad = [s.get('key') or '?' for s in d.get('stories', [])
       if not (s.get('headline') or '').strip()]
if bad:
    sys.exit('published story with no headline: %s' % bad)

for s in d.get('stories', []):
    secs = [(s.get(f) or '') for f in ['truth', 'prob', 'poss', 'lies']]
    if secs and all('INSUFFICIENT SOURCE MATERIAL' in x for x in secs):
        sys.exit('published story with no usable section: %s' % (s.get('key') or '?'))

# Everything above proves today's artifact is clean, which a manual cleanup
# achieves without any guard existing. These two prove the guard is there, so
# the ticket cannot go green on a tidy day. Presence checks, not fixture runs:
# they will not catch a guard that is present and wrong.
b = open('ntk-pulse/build_digest.py', encoding='utf-8').read()
if not re.search(r'(?i)(skip[^\n]*headline|headline[^\n]*skip|if not [^\n]*headline)', b):
    sys.exit('build_digest.py has no guard against a story with an empty headline')
if 'INSUFFICIENT SOURCE MATERIAL' not in open('ntk-pulse/pulse.html', encoding='utf-8').read():
    sys.exit('Pulse never looks for a section the model refused to write')

for day in sorted(os.listdir('digest')):
    p = os.path.join('digest', day, 'story', 'index.html')
    if os.path.exists(p):
        sys.exit('permalink generated from an empty slug: %s' % p)
    p = os.path.join('digest', day)
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', day): continue
    for slug in os.listdir(p):
        f = os.path.join(p, slug, 'index.html')
        if not os.path.exists(f): continue
        t = re.search(r'<title>([^<]*)</title>', open(f, encoding='utf-8').read())
        if t and not t.group(1).replace('NTK News', '').strip(' —-'):
            sys.exit('permalink with an empty title: %s' % f)
PY
```
