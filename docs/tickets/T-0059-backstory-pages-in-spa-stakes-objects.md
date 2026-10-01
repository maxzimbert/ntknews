---
id: T-0059
title: Backstory row and object pages open inside the app; rows get a stakes paragraph; objects link to a 4D page
status: VERIFIED
tags: [backstory, feature]
anchor: digest/index.html:3270
---

## What

Editor feedback 2026-10-01 on staging, in four parts:

1. Tapping a Backstory item opened a static page. It now opens the page
   inside the app (`showBsrPage()`, container `#bsrPage`): row page (4C) and
   object page (4D), each pushing its static URL (`/backstory/<id>/`,
   `/backstory/<id>/objects/<n>/`), so the address bar is a permalink and a
   reload lands on the static twin. Back steps object, row, list. The 4C/4D
   markup exists twice (JS in `digest/index.html`, Python in
   `editorial/build_backstory_pages.py`); keep them in step.
2. The tab row's footer hairline is now a centred dash, dot, dash mark so it
   reads differently from the full-width row rule.
3. Held rows carry a `stakes` paragraph (draft, written 2026-10-01 for the
   editor to edit): source of truth `editorial/backstory-rows.json`, passed
   through `build_backstory.py`, shown on the 4C page. The long-form essay is
   a separate feature (Rhymes) and out of scope here.
4. Case objects link to a hosted 4D page at `/backstory/<id>/objects/<n>/`
   (route proposed in T-0048). Today an object has only `{title, author,
   year, source}`, so the page shows those. `context`, `quote`, `where_now`
   and `source_url` render automatically when T-0045 / T-0048 supply them.

## Why

The handoff specifies in-app push navigation and object pages. A page that
renders thinly but links correctly was preferred to leaving objects as dead
text. Not built: pull-quotes (T-0045), object context and outbound links
(T-0048), multi-year Beginnings (T-0050). The stakes copy has not had a
second reader; treat it as a draft.

Verified against localhost: tab to row to object and back returns to the
list with the URL following (`/backstory/media/`, then `/objects/2/`, then
`/backstory`).

## Check

```sh
set -e
grep -q "function showBsrPage" digest/index.html
grep -q 'class="bt-mark"' digest/index.html
python3 - <<'PY'
import json
d = json.load(open("digest/data/backstory.json"))
held = [r for r in d["rows"] if r["stratum"] == "held"]
assert held and all(r.get("stakes") for r in held), "a held row has no stakes"
PY
grep -q 'class="stakes"' backstory/media/index.html
test -f backstory/media/objects/1/index.html
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' digest/index.html > "${TMPDIR:-/tmp}/t0059.js"
node --check "${TMPDIR:-/tmp}/t0059.js"
```
