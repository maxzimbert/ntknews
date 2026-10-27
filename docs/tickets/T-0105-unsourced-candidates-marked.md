---
id: T-0105
title: Lineup candidates with no sources are marked "0 sources on file" and need a confirm to add
status: VERIFIED
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html:3846
---

## What

Reported by the editor 2026-10-27: a candidate row read "Israel votes in first election since Oct. 7 ... 13 pubs", and expanding it said "No source detail available". Both were true. The "N pubs" is `publisher_count`, written by `lineup_promote.py` at promotion; it is a bare number. The source detail comes from the live 6h stream cluster, else from the `urls` recorded at promotion, and this story had neither (cluster aged out; older entries have no `urls`; T-0082 measured 10 of 67 edition stories with none).

T-0082 stopped such stories being auto-inserted, but left them in the candidates list looking like any other recommendation. Now a candidate with no live cluster items and no recorded `urls` shows "0 sources on file" in place of the pub count, and "+ add" asks for confirmation. The editor can still add it. Not verified in a browser against live data.

## Why

The editor's rule is that what the machine recommends must be sourced. The pub count was the misleading part: it asserted evidence the row could not show. Ruled out: hiding these rows (a real story would vanish silently, and the editor may want to add it and find sources by hand). Related: T-0082.

## Check

```sh
python3 - <<'PY' || exit 1
s=open('ntk-pulse/pulse.html').read()
i=s.index('function candidateHasSources('); j=s.index('{',i); d=0
for k in range(j,len(s)):
    d+={'{':1,'}':-1}.get(s[k],0)
    if d==0: break
fn=s[i:k+1]
open('/tmp/t0105.js','w').write("""
let STREAM={clusters:[{key:'live',items:[{url:'u'}]},{key:'empty',items:[]}]};
let EDITION={_candidates:[{key:'rec',urls:['https://a.com']},{key:'none',urls:[]},{key:'nourls'}]};
"""+fn+"""
const r=k=>candidateHasSources(k);
if(!(r('live')&&r('rec')&&!r('none')&&!r('nourls')&&!r('empty')&&!r('gone'))){console.log('bad');process.exit(1)}
""")
PY
node /tmp/t0105.js || exit 1
grep -q "0 sources on file" ntk-pulse/pulse.html
```
