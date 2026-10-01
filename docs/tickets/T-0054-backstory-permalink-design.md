---
id: T-0054
title: Backstory permalink pages are a thin version of the 4C design
status: VERIFIED
tags: [backstory, feature]
anchor: editorial/build_backstory_pages.py:1
---

## What

Measured 2026-10-01: `backstory/<row>/index.html` (T-0046, T-0053) had the
header logo and a plain-text indicator line, a single "Begins" line, a bare
case list and a light "In the digest" list. The handoff design
(`design_handoff_backstory/`, screen 4C) specifies a top bar with the page
URL, an indicator drawn as a line chart with a direction label, a Beginnings
spine, the case list, and a dark "In the digest" panel with an amber label.

Built here: all of those, from data already in `backstory.json`. Percentage
indicators draw as an SVG; non-percentage ones fall back to text rather than
invent a scale. Terra is used only for the "worse" direction and the end dot.

Not built, because the data does not exist yet (unverified against any
later schema): the stakes paragraph and "Read the backstory" link (no
narrative, no stakes field), multi-year Beginnings (one `start_line` per
row; needs T-0050 / `instances[]`), pull-quotes (T-0045), object pages
(T-0048), the narrative essay. Terra/teal contrast on cream was not
re-checked, as the handoff asks; unverified.

## Why

The editor wants the Claude Design UI live on the Backstory pages. Rendering
placeholder copy from the prototype was ruled out: the handoff says its
quotes and figures are sample content. Only fields that already exist in the
real data are rendered. Fire rows still show only elapsed time, as before.

## Check

```sh
set -e
f=backstory/media/index.html
[ -f "$f" ] || { echo "no $f"; exit 1; }
grep -q '<svg' "$f"
grep -q '\.digest {' "$f"
```
