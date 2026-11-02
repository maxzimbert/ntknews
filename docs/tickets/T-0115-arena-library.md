---
id: T-0115
title: The editor's Are.na library is a source Backstory draws on, after primary documents and before web search, and a reader sees its items like any other object
status: DECIDED
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html:4524
---

## What

Asked for by the editor 2026-11-02: "everything in Are.na is something I found valuable." The Are.na
account `max-zimcard` was pulled through the v3 API on 2026-11-02 with the editor's token
(`editorial/arena_pull.py`, token in `~/.config/arena/token`, never in the repo): 36 channels, one of
them private, 4,582 blocks. Measured the same day:

- 4,388 of the blocks are links, almost all news and essays: nytimes.com 1,322, latimes.com 214, wsj.com
  199, apnews.com 108. 48 point at a .gov, .edu or archive host. 96% of the dated ones were published
  2019 to 2021.
- `editorial/export_library.py` keeps what a reader can open and what can be placed in time, and writes
  `ntk-pulse/data/arena-library.json`. On URL dates alone: 2,283 kept, 1,675 of them on a paywalled
  outlet; dropped 232 on hosts that are gone or only redirect (BuzzFeed News, apple.news, Twitter), 30
  refused hosts, 63 duplicates, 140 with no title, 1,684 with no date in the URL. `--fetch-dates`
  reads the date from the page's own metadata for the last group and caches it in
  `editorial/arena-dates.json`.
- Pulse's composer chooses from `bsxLibrary()` (`ntk-pulse/pulse.html:4524`): matrix documents with a
  live link, approved candidates, objects categories hold, and research finds. `bsxShortlist()` scores
  that library against the story and sends the top 45 to Sonnet. Are.na items are not in it.

Wanted:
1. `bsxLibrary()` loads `arena-library.json` and adds each item as `kind: 'library'`, with
   `source_kind` from `catSourceKind` (a news host is labelled news, as now).
2. **Ranked second.** The shortlist keeps at most 10 library items for a story, so 2,000 clippings
   cannot crowd out 450 primary documents, and the compose prompt says: prefer a primary document; an
   item from the editor's library comes next; a web search only when neither connects. A paywalled
   item ranks below a free one that connects as well.
3. **Pulse labels it, the reader does not.** The editor's review shows "library" and "paywall" on
   each one. On ntknews.org it is a Beginning or an object like any other.
4. Refresh is by hand: `arena_pull.py`, then `export_library.py --fetch-dates`, then commit the JSON.

**Built so far (2026-11-02, branch `T-0115-arena-library`):** the pull, the search CLI
(`editorial/arena_search.py`) and the export. Not built: items 1 to 3. They change `bsxLibrary`,
`bsxShortlist` and the compose prompt, which T-0113 (PR #104, draft) is also changing in seven
places, so they wait for T-0113 to merge, or are built on top of its branch.

## Why

The editor's saved reading is a better second choice than whatever a web search returns: each item was
chosen by the person whose judgement the product rests on. It saves search spend too: research costs a
web-search call (T-0111), and the library costs nothing per story.

Kept out of the Object Matrix on purpose. The matrix rule is primary sources only (`docs/decisions.md`,
2026-10-02), and `build_backstory.py` treats every matrix row as one. Merged in, clippings would
become eligible by rule wherever primary sources ran thin, with nothing to say they are second
choice. The editor agreed on 2026-11-02.

What this tier can and cannot do: nearly all of it was written 2019 to 2021, and Beginnings are dated
before the story's "It starts in" year. So it will rarely supply a deep origin. It fills the recent end
of a history: the last steps before today, which the matrix (mostly before 1981) is thinnest on.

Ruled out: tagging all 4,582 items to rows and sub-genres up front (paying for items no story will use;
the shortlist already matches by the story's own terms), dating items by when the editor saved them
(that is when it was read, not written), and a reader-facing "from the editor's library" label (the
editor, 2026-11-02: "they don't need something in that screen").

Paywalls are the reader's cost. 1,675 of the 2,283 dated items are on metered or walled outlets. A
reader who taps "View the primary document" on one of those may hit a wall, which cuts against the
product's promise of closure. They are flagged rather than dropped, and the composer prefers a free
item.

The Are.na v2 user record reports 78 channels, but v3 with the owner's token lists 36. The other 42
are probably other people's channels the editor has added blocks to. Unverified.

## Check

```sh
python3 - <<'PY'
import json, os, subprocess, sys
bad = []
p = 'ntk-pulse/data/arena-library.json'
if not os.path.exists(p):
    bad.append('no exported library, so Backstory has nothing of the editor\'s to draw on')
else:
    objs = json.load(open(p))['objects']
    gone = ('buzzfeednews.com', 'apple.news', 'twitter.com', 'wikipedia.org')
    if len(objs) < 1500:
        bad.append(f'the library holds {len(objs)} items, fewer than 1,500')
    if any(any(g in o['url'] for g in gone) for o in objs):
        bad.append('a dead or refused host is in the library')
    if any(not str(o.get('year', '')).isdigit() or not o['url'].startswith('https://') for o in objs):
        bad.append('an item has no year or no https link, and publish would drop it')
js = r"""
const s=require('fs').readFileSync('ntk-pulse/pulse.html','utf8');
const grab=n=>{const i=s.indexOf('function '+n+'('); return i<0?'':s.slice(i, s.indexOf('\n}\n', i)+2);};
const lib=new Function('POOL','BSR_PUBLISHED','PUBCATS','catSourceKind','ARENA', grab('bsxLibrary')+'; return bsxLibrary;')(
  {objects:[]}, {rows:[]}, [], ()=>'news',
  {objects:[{id:'arena-1',title:'Senators question platforms on Section 230',source:'nytimes.com',url:'https://www.nytimes.com/2020/10/28/x.html',year:'2020',date:'2020-10-28',paywall:true,source_kind:'news'}]});
const L=lib({stories:[]}, {finds:[],rejected:[]});
console.log(JSON.stringify(!!L['arena-1'] && L['arena-1'].kind==='library'));
"""
r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
if r.stdout.strip() != 'true':
    bad.append('an Are.na item does not reach the library Pulse composes from, as kind "library"')
for b in bad: print(b)
sys.exit(1 if bad else 0)
PY
```
