---
id: T-0106
title: Manual clusters in Pulse expire after 5 days unused
status: BUILT
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html:3274
---

## What

Manual clusters (merged, extracted, searched, or imported from a URL) are stored only in the editor's browser `localStorage` (`ntk_pulse_manual_clusters_v1`), so nothing ever cleaned them up. Now each carries `lastUsedAt`, and on page load any cluster unused for more than `MANUAL_TTL_DAYS` (5) is dropped. "Used" means changed (items added, rescan, search, merge), expanded, or certified. `saveManual()` stamps `lastUsedAt` on whichever clusters differ from their last-saved signature, so no call site needed editing. Clusters saved before this change have no `lastUsedAt`; their clock starts at first load rather than deleting existing work. Built 2026-10-27; logic tested in node, not run in a real browser against the editor's live localStorage (unverified).

## Why

The editor asked for clutter to clear itself. Certify snapshots title and links into the lineup, so expiry cannot damage a lineup story; this is why deletion needs no lineup guard. Ruled out: server-side expiry (the clusters never leave the browser, so there is nothing to expire there); expiring on `createdAt` (would delete a cluster the editor is actively building on day 6); counting a view as use only via an explicit touch at every call site (easy to miss one; signature diffing in `saveManual` cannot). Expiry runs on load only, so a Pulse tab left open for days keeps its clusters until reload. Expired clusters are deleted with no undo.

## Check

```sh
python3 - <<'PY' || exit 1
s=open('ntk-pulse/pulse.html').read()
def fn(name):
    i=s.index('function '+name+'('); j=s.index('{',i); d=0
    for k in range(j,len(s)):
        d+={'{':1,'}':-1}.get(s[k],0)
        if d==0: return s[i:k+1]
open('/tmp/t0106.js','w').write("""
const store={}; global.localStorage={getItem:k=>store[k]??null,setItem:(k,v)=>store[k]=v};
const LS={manual:'m'}, DAY=86400000, iso=d=>new Date(Date.now()-d*DAY).toISOString();
const MANUAL_TTL_DAYS=5, MANUAL_SIG=new Map();
let MANUAL=[{key:'edit',lastUsedAt:iso(4),items:[]},{key:'old',lastUsedAt:iso(6),items:[]},{key:'legacy',createdAt:iso(30),items:[]}];
"""+fn('manualExpired')+fn('manualSig')+fn('touchManual')+fn('saveManual')+"""
if(!manualExpired(MANUAL[1],Date.now())) throw 'old not expired';
if(manualExpired({lastUsedAt:iso(4)},Date.now())) throw 'fresh expired';
MANUAL.forEach(m=>{if(!m.lastUsedAt)m.lastUsedAt=new Date().toISOString()});
if(manualExpired(MANUAL[2],Date.now())) throw 'legacy not kept';
MANUAL.forEach(m=>MANUAL_SIG.set(m.key,manualSig(m)));
const e=MANUAL[0], before=e.lastUsedAt;
saveManual(); if(e.lastUsedAt!==before) throw 'unchanged was stamped';
e.items.push({id:1}); saveManual(); if(e.lastUsedAt===before) throw 'edit not stamped';
""")
PY
node /tmp/t0106.js || exit 1
grep -q "MANUAL = MANUAL.filter(mc=>!manualExpired" ntk-pulse/pulse.html
```
