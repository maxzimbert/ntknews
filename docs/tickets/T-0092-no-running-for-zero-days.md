---
id: T-0092
title: A new category with no origin found shows no "Running for 0 days" on its card
status: VERIFIED
tags: [digest, defect]
anchor: digest/index.html
---

## What

Seen by the editor 2026-10-15 on ntknews.org/backstory: the Cologne robot story's card read RUNNING FOR /
0 days under the category Robots and Law. Measured that day in the published `backstory.json`: the
category `p-robots-and-law` is provisional with `start_date` 2026-10-15, the day it was created
(`build_pairings.py` uses the creation date when a category has no start), and the story's origin was
`status: fallback`: `build_origins.py` chose none ("none of which is an event that made this case possible").
The card (`bsrCardHtml`) falls through, for any row without a found origin or a `start_line`, to "Running
for" plus the days since `start_date`. That branch is meant for the seven fire rows (Gaza, Ukraine-Russia,
Sudan...), whose start dates are real; for a provisional category it counts from the day the category was
made.

Fixed: a provisional row with no origin and no `start_line` shows nothing in that slot. Fire rows keep
"Running for"; held rows keep "It starts in". Checked by running `bsrCardHtml` on the robot record (no
"Running for", TODAY kept), Gaza with no origin ("Running for 3 yrs, 0 mo") and Power (It starts in 1974).
Pulse draws the same card (T-0091), so its preview changes with it.

## Why

"0 days" tells a reader the story has no history, which is the opposite of Backstory's claim, and a reader
who notices one wrong number stops trusting the rest. The editor's first read was that "Running for" was
outdated code to remove; it is not, it is the fire rows' design (T-0049). The bug was only that new
categories reached it.

Not fixed here: why no origin was found. The origin step's own note names what it would search for (the 2016
German sexual offence law reform); a category with a thin origin is T-0083's ground.

## Check

```sh
python3 - <<'PY' > /tmp/t0092.js || exit 1
import re
s = open('digest/index.html', encoding='utf-8').read()
js = re.search(r'/\* BSR-CARD:BEGIN[^*]*\*/([\s\S]*?)/\* BSR-CARD:END \*/', s)
if not js: raise SystemExit(1)
print("var document={createElement:function(){var o={set textContent(v){o.innerHTML=String(v)}};return o;}};")
print(js.group(1))
print("""var p=bsrCardHtml({id:'p-x',title:'X',stratum:'provisional',start_date:new Date().toISOString().slice(0,10),pairline:'t',origin:{status:'fallback'}},'#',0);
var f=bsrCardHtml({id:'gaza',title:'Gaza',stratum:'fire',start_date:'2023-10-07',pairline:'t'},'#',0);
if (/Running for/.test(p) || !/Running for/.test(f)) process.exit(1);""")
PY
node /tmp/t0092.js
```
