---
id: T-0055
title: Opening a Backstory row in the app doesn't change the URL
status: VERIFIED
tags: [backstory, feature]
anchor: digest/index.html:3068
---

## What

Measured 2026-10-01: `navOverlay()` in `digest/index.html` pushed a URL only
for stories (`storyPath`); a Backstory row's detail modal pushed history
state with the address bar left at `/backstory`, so a row had no shareable
in-app URL even though `/backstory/<row-id>/` exists as a static page
(T-0046). Now `bsrPath()` returns that path and the modal pushes it, the
same mechanism stories use. Back closes the modal and returns to
`/backstory`. A reload or cold visit is served by the static page, not the
SPA, so `ntkRoute` needs no change.

## Why

The editor wants a row to have a permalink in the SPA as well as a static
page. Ruled out: routing `/backstory/<id>` into the SPA, which would shadow
the static pages and their OG tags. Not browser-tested on a Netlify deploy
preview at the time of writing (unverified); the check is a parse plus a
source assertion.

## Check

```sh
set -e
grep -q "function bsrPath" digest/index.html
grep -q "kind === 'bsr' ? bsrPath(idx)" digest/index.html
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' digest/index.html > "${TMPDIR:-/tmp}/t0055.js"
node --check "${TMPDIR:-/tmp}/t0055.js"
```
