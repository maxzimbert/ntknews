---
id: T-0036
title: Source Serif 4 is unclaimed; switch every editorial surface to Newsreader
status: VERIFIED
tags: [digest, chore]
anchor: index.html:39
---

## What

The audit's Section V argued Source Serif 4 "is not wrong, it is unclaimed
— the face that arrives when a thoughtful person needs a reasonable serif
and does not want to think further." T-0029 fixed the *inconsistency*
(three surfaces disagreeing on typeface) but kept Source Serif 4 itself.
The editor decided 2026-09-23: switch to Newsreader.

Newsreader was carried into every place Source Serif 4 was, and nowhere
else — Overpass stays the chrome face, untouched. Verified by static
analysis and by generating live output, not by reading the source:

- `index.html` (landing) and `digest/index.html` (the app): Google Fonts
  link and every `font-family: 'Source Serif 4'` declaration.
- `ntk-pulse/build_digest.py`: both `STORY_PAGE_TEMPLATE` and
  `ARCHIVE_TEMPLATE` — confirmed by actually calling `build_story_page()`
  and formatting `ARCHIVE_TEMPLATE`, not by reading the template string.
- Backfilled onto 25 already-published files nothing regenerates: 20 story
  permalinks, 4 frozen full editions, the archive index.

The weight/style set requested (`ital,opsz,wght@0,6..72,300;…,400;…,600;
1,6..72,300;…,400;…,600`) was derived by mapping every selector that pairs
with the family, not assumed — normal 300/400/600 everywhere, and italic
needed at all three weights (the landing page's certainty-ladder Lies label
is italic while inheriting weight 600 from `.story-row-label`, which a
narrower request would have silently synthetic-italicised).

One bug caught mid-backfill, not before: the backfill script hardcoded its
root path instead of reading the one passed on the command line, so a
"dry run" against a scratch copy silently patched the real tree instead.
Caught by re-verifying the live tree afterward rather than trusting the
script's own report of what it did — 4 files (the frozen editions) turned
out incompletely patched, missing an escaped-quote occurrence
(`\'Source Serif 4\'` inside a JS template string) the same as one already
found and fixed in `digest/index.html` under T-0029. Fixed directly; full
repo sweep afterward confirmed zero remaining occurrences in every in-scope
file, and zero touched in `digest/v2/` or the orphan pages, both correctly
out of scope.

## Why

Named directly: "switch to newsreader." No purchase involved — Newsreader
is SIL Open Font Licence, same delivery mechanism (Google Fonts link) as
every other swap this project has made. The audit's case for it: a true
optical-size axis from 6 to 72, so the headline cut and the body cut are
different drawings rather than one outline scaled — the one feature that
most separates a set publication from a generated one, and something
almost no free face carries.

## Check

```sh
# No live surface still references Source Serif 4.
! grep -rl "Source Serif 4\|Source+Serif+4" index.html digest/index.html \
  ntk-pulse/build_digest.py digest/2026-*/*/index.html digest/2026-*/index.html \
  digest/archive/index.html 2>/dev/null | grep -q .

# Newsreader is loaded via a working Google Fonts link.
grep -q "family=Newsreader" index.html
grep -q "family=Newsreader" digest/index.html
grep -q "family=Newsreader" ntk-pulse/build_digest.py

# digest/v2 (inert) was not touched.
git diff --stat main -- digest/v2/ | grep -q . && exit 1 || exit 0
```
