---
id: T-0011
title: Backstory cards are indistinguishable when two stories share a row
status: DECIDED
tags: [digest, defect]
anchor: digest/index.html:2880
---

## What

`renderBackstoryTab()` renders one card per pairing, leading with the row's
title, day count and milestone. All three are properties of the **row**, so
when two stories pair to the same row the cards differ only by the pairline,
in smaller type below.

On 2026-09-17 that produced three cards titled "Power" and two titled "America
Abroad" out of eight.

## Why

Backstory's current design — recorded in `backstory_part_2-chat-readme.md` and
`docs/backstory.md` — is **one entry per digest story**, not a browsable list
of rows. The card's job is to tell a reader why *today's story* has a history.
Right now the story is the one thing the card does not say.

The fix is to lead with the story headline and make the row title subordinate.
That stays inside the current design.

**It must not become the standing list again.** A toggle, a "see all 21"
button, or a two-strata divider were the earlier design and were explicitly
replaced; the Part 2 README opens by telling the next session to stop if it
finds itself rebuilding any of them. Collapsing collided cards into one card
per row would drift back toward that, and would also break the one-card-per-
story contract. Don't.

T-0010 reduces how often collisions happen. It cannot eliminate them — two
stories genuinely belonging to one row is a legitimate day — so this is needed
regardless.

## Check

```sh
python3 - <<'PY'
import re, sys
s = open('digest/index.html', encoding='utf-8').read()
m = re.search(r'function renderBackstoryTab\(\)\{.*?\n\}', s, re.S)
if not m: sys.exit('renderBackstoryTab not found')
body = m.group(0)
if 'r.headline' not in body:
    sys.exit('the card does not render the story headline')
if body.index('r.headline') > body.index('escBsr(r.title)'):
    sys.exit('the row title still leads the card, ahead of the story headline')
PY
```
