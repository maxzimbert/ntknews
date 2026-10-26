---
id: T-0088
title: The Backstory tab lists today's stories in the digest's order, not newest thread first
status: VERIFIED
tags: [digest, defect]
anchor: digest/index.html
---

## What

Reported by the editor 2026-10-15: on ntknews.org/backstory the Cologne robot story came first, though it is
last in the digest; Ukraine-Russia, first in the digest, was not first. `fetchBackstory()` in
`digest/index.html` sorted the cards by `bsrDaysSince(start_date)`, shortest first, so the thread that
started most recently led. That sort has been there since 2026-09-16 (c3024ed9) and was invisible while
every row was a fixed row with an old start date; automatic categories start "today" (`p-robots-and-law`,
2026-10-15), which pushed them to the top. Measured that day: `todays_pairings` was in digest order and the
page reordered it.

Fixed: the cards sort by each story's position in the digest itself (`findStoryIndexByKey`), so the order
is the editor's Lineup order however the pairings file is written. A paired story not in today's digest
goes last. Checked in a local preview against the live 2026-10-15 data: digest and Backstory both read
Ukraine-Russia, Inflation, Power, Order, The Media, Government, Robots.

## Why

The digest order is an editorial decision: the editor ranks the day. A second surface that re-ranks the
same stories by a property the reader cannot see says the order means nothing. No decision in
`docs/decisions.md` chose "newest thread first"; it came in with the first slice of the row library.

## Check

```sh
python3 - <<'PY'
import re, sys
s = open('digest/index.html', encoding='utf-8').read()
m = re.search(r'function fetchBackstory\(\)\{[\s\S]*?\n\}', s)
if not m: sys.exit('fetchBackstory not found')
b = m.group(0)
if 'findStoryIndexByKey' not in b: sys.exit('Backstory cards are not ordered by the digest')
if 'bsrDaysSince' in b: sys.exit('Backstory cards are ordered by thread age')
PY
```
