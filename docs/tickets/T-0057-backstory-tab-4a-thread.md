---
id: T-0057
title: The in-app Backstory tab is not the 4A thread, and rows have no real permalink
status: VERIFIED
tags: [backstory, feature]
anchor: digest/index.html:3160
---

## What

Reported by the editor 2026-10-01 on staging: the Backstory tab showed
centred white cards, not the 4A thread from the Claude Design handoff, and
tapping a row opened a dark modal with the address bar unchanged.

Now `renderBackstoryTab()` draws 4A: header "Today's stories, and where
they start.", then hairline-ruled rows: TODAY label + the pairing line
(tapping opens that story), terra "It starts in {year}" + `start_line`, and
a footer with the theme name left and a blue "Backstory" link right. The
row's links are real anchors to `/backstory/<id>/` (the static 4C page,
T-0046), so the URL changes and the page is shareable; the dark modal is no
longer reachable from the tab (its code remains, unused). Fire rows have no
`start_line` by design (T-0049) and show elapsed time under "Running for".
Supersedes T-0055 (pushState on the modal), which solved a problem that
real navigation removes.

Not built: the per-device "Another beginning" rotation (rows carry one
beginning each; needs T-0050/`instances`).

## Why

The handoff specifies push navigation, no modals, one 4C page per theme.
Reusing the static page keeps a single implementation of 4C. Verified in a
browser against localhost: 6 rows, hrefs `/backstory/<id>/`, story links
resolve to digest story indexes.

## Check

```sh
set -e
grep -q "Today's stories, and where they start." digest/index.html
grep -q "function bsrHref" digest/index.html
grep -q 'class="bt-cta"' digest/index.html
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' digest/index.html > "${TMPDIR:-/tmp}/t0057.js"
node --check "${TMPDIR:-/tmp}/t0057.js"
```
