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

**Check narrowed 2026-09-18, and the reason matters.** It originally compared
the landing claim against the *current* edition's story count, and went STALE
the first time an edition shipped four. That was a true failure attached to
the wrong ticket: the copy had not become inaccurate, the digest had gone out
of spec. One assertion covering two independent facts fails ambiguously, and a
check nobody can read an action off is on its way to being ignored. The claim
is now measured against the locked range in `docs/decisions.md`; T-0023 holds
the edition count. The signal moved, it was not dropped.
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

# Measured against the locked decision, not against today's edition. A digest
# outside 6-10 is a real problem and it is T-0023's: the copy does not become
# wrong because one day shipped short.
dec = open('docs/decisions.md', encoding='utf-8').read()
m = re.search(r'\*\*The digest must end\.\*\*\s*(\d+)[–-](\d+) cards', dec)
if not m: sys.exit('the locked story-count range is no longer stated in docs/decisions.md')
lo_d, hi_d = int(m.group(1)), int(m.group(2))
claims = re.findall(r'(\d+)\s*(?:[–-]\s*(\d+))?\s*stories', t)
if not claims:
    sys.exit('the landing page no longer says how many stories a digest carries')
for c in claims:
    lo = int(c[0]); hi = int(c[1]) if c[1] else lo
    if (lo, hi) != (lo_d, hi_d):
        sys.exit('landing claims %s stories; docs/decisions.md locks %d-%d' % (
            '%d-%d' % (lo, hi) if hi != lo else str(lo), lo_d, hi_d))

if re.search(r'>\s*Truth\s*<', s):
    sys.exit('the first section is labeled "Truth" on the landing page and "Truths" in the product')
PY
```
