---
id: T-0023
title: Today's edition shipped four stories, below the locked 6-10 floor
status: DECIDED
tags: [editorial, defect]
anchor: docs/decisions.md
---

## What

`docs/decisions.md` locks the digest at **6-10 cards with a defined last
card**. The 2026-09-18 edition shipped four.

The immediate cause is known: five were published, the fifth was a story the
model refused to write for lack of usable sources (T-0022), and the editor
republished with it removed rather than ship a blank card. Four is what was
left.

This ticket is the floor itself, not that incident. Nothing in the pipeline
or in Pulse currently notices that an edition is short.

## Why

The count is not a preference. `docs/decisions.md` ties it directly to the
product promise: the digest must end, closure is what is being sold, and
6-10 with a defined last card is the shape that delivers it. Four is a
different product. It also quietly contradicts the landing page, which now
promises 6-10 to a cold reader in the same breath as "News that ends."

**Split out of T-0018 on 2026-09-18.** That ticket's check originally compared
the landing page's claim against the current edition's count, so a short
digest surfaced as "the landing copy is wrong." The copy was not wrong. Two
independent facts were riding on one assertion, and the failure named the
wrong one. T-0018 now measures the copy against the locked range; this ticket
measures the edition.

**Not obvious, and worth deciding rather than assuming:** whether a short
edition should block a publish, warn, or only be reported after the fact.
`docs/decisions.md` already contains the argument on both sides. "No approval
gate between Lineup and Publish" was chosen deliberately so real failure modes
would surface instead of being smoothed over, and the 2026-09-16 Today-overview
decision softened that to "warn, with a choice" once a failure had shipped
silently twice. A short digest has now shipped once. The same reasoning points
at a warning rather than a block, and at doing it alongside T-0022's guard
rather than as a separate pass over the same publish step.

This ticket stays OPEN until an edition in range is published. That is the
correct behaviour, not noise: a rot detector that goes quiet while the product
is out of spec is worth nothing.

## Check

```sh
python3 - <<'PY'
import json, re, sys
dec = open('docs/decisions.md', encoding='utf-8').read()
m = re.search(r'\*\*The digest must end\.\*\*\s*(\d+)[–-](\d+) cards', dec)
if not m: sys.exit('the locked story-count range is no longer stated in docs/decisions.md')
lo, hi = int(m.group(1)), int(m.group(2))
n = len(json.load(open('ntk-pulse/data/lineup-publish.json')).get('stories', []))
if not (lo <= n <= hi):
    sys.exit('the published edition carries %d stories; docs/decisions.md locks %d-%d' % (n, lo, hi))
PY
```
