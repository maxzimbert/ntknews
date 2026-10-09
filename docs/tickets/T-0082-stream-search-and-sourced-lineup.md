---
id: T-0082
title: Stream has a keyword search held to the publisher bar, and Lineup never auto-fills a story with no source URLs
status: BUILT
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Asked by the editor 2026-10-09, two things.

**Stream search.** A box at the top of Stream: type words or phrases separated by commas, press
Enter, and a new manual cluster is made from every match. Each term is a phrase; any one matches.
Sources are the current window (title match, whole words) plus EventRegistry through a new
`news.js` mode, `keyword-search`, called twice: `pool=ntk` (the 91 `NTK_SOURCES`) and `pool=top`
(ER's top 20% of sources, the same bar as `scan-broad`). 7-day window, 15 per pool, sorted by
relevance. The cluster then behaves like any manual one (suppress, extract, rescan, → lineup).

Measured on main (aa4edc5) before this: Pulse's two existing "search EventRegistry" buttons send
`mode=keyword-search`, which `news.js` did not have, so they fell through to the default branch:
a keyword search with **no publisher filter and no date window**. Those buttons now get the
filtered mode too, since they send the same mode name (they send no `pool`, so they get the NTK
list).

**Sourced Lineup.** After "clear all stories" the empty Lineup bootstraps from `lineup.json`.
Any edition story whose cluster had aged out of the stream went in with `articles: []`. On
2026-10-09, 3 of 67 edition stories had no cluster in the stream and 10 carried no recorded
`urls`. Now: a story falls back to the `urls` that `lineup_promote.py` recorded; a story that
still has no URL is left as a candidate, never auto-inserted. The editor can still add it by
hand. Bootstrap also waits for `clusters.json` to answer, because `lineup.json` can land first
and make every story look sourceless.

Verified 2026-10-09 on localhost: with four edition clusters removed from the stream, one with
a recorded URL and two with none, a cleared Lineup refilled to 8 with 0 sourceless stories; the
URL-less story stayed a candidate. Against production's `news.js` (no mode yet), the search kept
its window results and reported the missing mode instead of using the unfiltered fallback.
Not verified: a real ER call through `keyword-search` (the same query shape was run directly
against ER and returned relevant results), and anything on the Pages Pulse.

## Why

The editor's rule is that what the machine recommends must be sourced. A Lineup slot with no
URLs gives Jefferson nothing to write from and looks like a recommendation. It is also invisible
until generation fails.

The search has a quality bar because "relevant" is not enough. ER's top 20% still admits
Breitbart, Yahoo UK and Mint; that is ER's bar, and the editor asked for "ours or ER's". The
`pool=top` call is the one to tighten if that turns out too loose.

Cost: two ER requests per search (a few ER tokens each).

`news.js` tags this mode's response (`ntkMode`). The reason: Pulse runs on GitHub Pages and
calls the production Netlify function, so a Pulse change can be live (or on staging) before the
function is. Without the tag, that gap silently becomes an unfiltered search. Ruled out:
filtering by source rank in the browser (ER's percentile isn't in the default response).

## Check

```sh
# 1. The function: both pools carry a publisher filter, a 7-day window, OR'd phrases, and the tag.
cat > /tmp/t0082-fn.js <<'JS'
const https=require('https'); const {EventEmitter}=require('events'); let sent;
https.request=(o,cb)=>{const q=new EventEmitter(); q.write=b=>sent=JSON.parse(b); q.setTimeout=()=>{};
  q.end=()=>{const r=new EventEmitter(); r.statusCode=200; r.headers={}; cb(r);
  r.emit('data','{"articles":{"results":[]}}'); r.emit('end');}; return q;};
const fn=require(process.cwd()+'/netlify/functions/news.js');
(async()=>{ for (const pool of ['ntk','top',undefined]){
  const r=await fn.handler({queryStringParameters:{mode:'keyword-search',q:'a b, c',pool}});
  const filtered=(sent.sourceUri||[]).length>0 || sent.endSourceRankPercentile<=20;
  if (!filtered || sent.forceMaxDataTimeWindow>7 || sent.keyword.length!==2 || sent.keywordOper!=='or'
      || JSON.parse(r.body).ntkMode!=='keyword-search'){ console.log('bad', pool, sent); process.exit(1); } }})();
JS
node /tmp/t0082-fn.js || exit 1
# 2. Pulse: a cleared Lineup never auto-fills a story without a URL.
python3 - <<'PY' > /tmp/t0082-lineup.js || exit 1
import re
s=open('ntk-pulse/pulse.html').read()
def fn(name):
    i=s.index('function '+name+'('); j=s.index('{',i); d=0
    for k in range(j,len(s)):
        d+= {'{':1,'}':-1}.get(s[k],0)
        if d==0: return s[i:k+1]
print("let LINEUP=[],LINEUP_MAX=8,STREAM_SETTLED=true,BEAT_TO_CAT={},saveLineup=()=>{};")
print("let STREAM={clusters:[{key:'k1',items:[{url:'https://a.com/1',title:'t',publisher:'p'}]}]};")
print(s[s.index('const MC_STOPWORDS'):s.index('function mcCosine(')]+fn('mcCosine'))   # the similarity helpers reconnect uses
for n in ['findReconnectCandidate','materializeEditionStory','syncEditionToLineup']: print(fn(n))
print("""let EDITION={stories:[{key:'k0',title:'no source anywhere'},{key:'k1',title:'live'},
  {key:'k2',title:'aged out',urls:['https://b.com/2']}]};
syncEditionToLineup();
const bad=LINEUP.filter(l=>!l.articles.some(a=>a.url));
if (bad.length || LINEUP.length!==2 || !EDITION._candidates.some(c=>c.key==='k0')){
  console.log('bad', JSON.stringify(LINEUP.map(l=>[l.key,l.articles.length]))); process.exit(1); }""")
PY
node /tmp/t0082-lineup.js
```
