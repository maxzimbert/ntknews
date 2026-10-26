---
id: T-0096
title: Pulse warns before publishing a Today overview that mentions a story no longer in the lineup
status: VERIFIED
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html
---

## What

The 2026-10-15 18:36Z edition shipped a Today overview with a bullet about Ukraine's missile-warning gap,
marked `[STORY: b6aeca271d24cf9b | Ukraine warning gap]`. That story was not among the five published: the
overview was generated while it was in the lineup, and it was dropped afterwards. The reader page turns an
unknown marker into plain text, so there was no dead link, but readers got a paragraph about a story that is
not in the digest. T-0001's check caught it and went STALE, correctly. Pulse's Today guard (`todayPreflight`,
T-0072) checked only that the overview was finished and generated today.

Fixed: `todayPreflight` takes the lineup's keys and warns, at publish, when the overview mentions a story no
longer in the lineup, naming it and saying to run Generate Today again. A warning, not a block, like the
rest of the Today guard. Tested by running the function: a dropped story is named, a full lineup gives no
warning, and T-0072's own check (which calls it without keys) still passes.

Also in this change: T-0029's direction check read arrow glyphs that only the old detail modal drew, so it
went STALE when T-0094 removed that modal. It now reads `bpIndicator()`, the Backstory page readers get,
which prints the direction as a word; the check fails if that word is removed.

Not fixed by this change: the edition already live. T-0001 stays STALE until the next publish carries an
overview whose stories are all in the lineup.

## Why

The overview is the first thing a reader sees and the piece that promises the rest of the edition. A paragraph
pointing at a story that is not there breaks that promise quietly, with nothing on the page to say so.

## Check

```sh
node -e "
const s=require('fs').readFileSync('ntk-pulse/pulse.html','utf8');
const i=s.indexOf('function todayPreflight'), j=s.indexOf('\n}\n', i)+3;
const f=new Function('TODAY_OV','now','keys', s.slice(i,j)+'; return todayPreflight(now, keys);');
const ov={text:'A. [STORY: aaa | Gas] B. [STORY: bbb | Dropped story]', generatedAt:new Date().toISOString()};
const w=f(ov, undefined, ['aaa']).warn.join(' '), ok=f(ov, undefined, ['aaa','bbb']).warn.length;
process.exit(/Dropped story/.test(w) && ok===0 ? 0 : 1);" && grep -q "todayPreflight(undefined, LINEUP.map" ntk-pulse/pulse.html
```
