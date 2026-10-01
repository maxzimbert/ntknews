---
id: T-0063
title: The in-app Backstory page replaced the screen instead of overlaying it
status: VERIFIED
tags: [backstory, defect]
anchor: digest/index.html:3270
---

## What

Reported 2026-10-01 by the editor with a screen recording of ntknews.org/backstory
("there's no overlay!"). In T-0059 the row and object pages were a full-window
layer (`#bsrPage`, `inset:0`, opaque cream) that hid the app header, the tab
bar and the list. The recording shows the whole window turning into the Media
page with no sign of the app behind it. In the frames I extracted the page has
no dark NTK logo bar, so it is the in-app layer and not the static twin; I
had checked that it was in-app (same document, no reload) and called that
"inline over the SPA", without checking how it looked.

Now `#bsrPage` is a dimmed backdrop (rgba of the ink colour, 60%) with the
page as a sheet laid over it: bottom-anchored on phones with 44px of the app
left visible above it, a centred card on screens 700px and wider. The
Backstory list and tab bar stay in place underneath. Closing: the "←" link,
tapping the backdrop, or Escape. The URL still pushes `/backstory/<id>/` and
`.../objects/<n>/`; back steps object, row, list. The page behind does not
scroll while it is open.

## Why

The design handoff says push navigation, no modals, but the editor's
expectation is a visible overlay, and the editor's expectation wins over my
reading of the handoff. Cost of the earlier miss: two rounds, because I
verified the mechanism and not the appearance. Verified in a browser at phone
width against localhost by measuring geometry (sheet top 44px, backdrop
colour, list still mounted, body scroll locked, backdrop tap returns to
`/backstory`); the browser pane was not displayed, so no screenshot was
taken. Not yet seen by the editor on a real device.

## Check

```sh
set -e
grep -q "background: rgba(38,31,35,.6)" digest/index.html
grep -q "e.target.id === 'bsrPage'" digest/index.html
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' digest/index.html > "${TMPDIR:-/tmp}/t0063.js"
node --check "${TMPDIR:-/tmp}/t0063.js"
```
