---
id: T-0018
title: The landing page copy predates the product it describes and breaks three of its own rules
status: VERIFIED
tags: [editorial, feature]
anchor: index.html:379
---

## What

Rewrite the prose on `ntknews.org` against the same eleven rules going into
Pulse's prompts (T-0017). Structure, hero, stat blocks and section order stay
as they are; the page's hero mirrors the current lead story and that wiring is
not touched.

Measured 2026-09-18 against `index.html`:

- Three em dashes in visible copy, against a hard no-em-dash rule that now
  governs every word the product publishes.
- "3-4 stories daily" (`index.html:379`). The live digest ships eight, and
  `docs/decisions.md` fixes the digest at 6-10 cards. The page understates
  the product by half.
- The first section is labeled "Truth". Everywhere else in the product, and
  throughout `docs/decisions.md`, it is "Truths".

## Why

The landing page is the only surface a cold reader meets before deciding
whether to trust the thing, and it is currently the least governed prose in
the project. Every other word NTK publishes runs through a prompt system with
a voice specification, a banned-verb list and a punctuation rule. The
marketing copy runs through none of it, and it shows: the four-section
framework is introduced with "No editor ever built it. NTK did - and every
story runs through all four," which is the exact em-dash-as-unmade-decision
the voice rules now prohibit.

The factual drift matters more than the punctuation. A page that promises
three to four stories and delivers eight is not underselling in a charming
way; it is the first evidence a news-avoidant reader has about whether this
product tells the truth about itself. `docs/decisions.md` records closure as
the product promise and "the digest must end" as a locked decision, so the
number is not a detail to leave stale.

Ruled out: reworking the page's structure, section order or stat trio. That is
a design conversation, not a copy pass, and the hero's coupling to the lead
story means structural edits carry build-time consequences that a prose
rewrite does not.

Not checkable, and stated here instead: whether the rewritten prose is better.
Positive form, parallel construction and word order are judgment. The check
below catches the three measurable regressions; it cannot tell you the page
reads well.

## Check

```sh
python3 - <<'PY'
import html, re, sys
s = open('index.html', encoding='utf-8').read()
t = re.sub(r'(?is)<(script|style|svg)[^>]*>[\s\S]*?</\1>', '', s)
t = html.unescape(re.sub(r'<[^>]+>', ' ', t))

n = t.count('—')
if n: sys.exit('%d em dash(es) in visible landing copy' % n)

d = open('digest/index.html', encoding='utf-8').read()
m = re.search(r'const stories = \[[\s\S]*?\n\];', d)
if not m: sys.exit('published stories array not found in the digest')
live = len(re.findall(r'category:\s*"', m.group(0)))
for claim in re.findall(r'(\d+)\s*(?:[–-]\s*(\d+))?\s*stories', t):
    lo = int(claim[0]); hi = int(claim[1]) if claim[1] else lo
    if not (lo <= live <= hi):
        sys.exit('landing claims %s stories; the digest ships %d' % (
            '%d-%d' % (lo, hi) if hi != lo else str(lo), live))

if re.search(r'>\s*Truth\s*<', s):
    sys.exit('the first section is labeled "Truth" on the landing page and "Truths" in the product')
PY
```
