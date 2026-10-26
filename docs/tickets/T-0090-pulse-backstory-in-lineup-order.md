---
id: T-0090
title: Pulse's Backstory tab shows the Lineup's stories in Lineup order, each with its category
status: VERIFIED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-15. Measured on main that day: the Backstory tab in Pulse has two lists, and
neither is the Lineup. TODAY'S PAIRINGS (`pairingsHtml`) reads the published `backstory.json`, so it shows
the last publish, not the Lineup being edited. CATEGORIES (`catListAll`) lists every local category in the
order it was created, then published ones, with no tie to today's stories. A story with no category filed
does not appear on the tab at all, which is how the gas story went out unfiled on 2026-10-15 (T-0089).

Wanted: the tab opens on today's Lineup, in Lineup order, one entry per story with the category it is filed
under (or "none filed", visibly), and the category list below it. Reordering the Lineup reorders this.

## Why

The editor works story by story in Lineup order. A Backstory tab in another order makes the editor hunt for
the story in hand, and hides the unfiled ones, which are the ones that need attention. The reader page now
follows digest order (T-0088); Pulse should show the editor the same order before publishing.

Built 2026-10-15: TODAY'S LINEUP at the top of the Backstory tab (`bsrLineupHtml`), one row per Lineup story
in Lineup order, with a row/category select (the same options as Lineup's, `bsrRowOptions`), a NONE FILED
chip on an unfiled story, an "open <category>" button, and what the last publish did with it. Tested in a
local Pulse with the 2026-10-15 lineup: order matched, moving the last story to the top moved it here, and
filing the gas story from this list set its `backstoryRow`.

## Check

```sh
python3 - <<'PY'
import re, sys
s = open('ntk-pulse/pulse.html', encoding='utf-8').read()
r = re.search(r'function renderBackstory\(root\)\{[\s\S]*?\n\}', s)
f = re.search(r'function bsrLineupHtml\(\)\{[\s\S]*?\n\}', s)
if not r or 'bsrLineupHtml()' not in r.group(0): sys.exit('the Backstory tab does not show the Lineup')
if not f or 'LINEUP.map(' not in f.group(0) or 'none filed' not in f.group(0): sys.exit('the Lineup list is not in Lineup order or hides unfiled stories')
PY
```
