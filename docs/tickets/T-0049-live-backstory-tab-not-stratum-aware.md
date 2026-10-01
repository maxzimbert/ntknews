---
id: T-0049
title: The live Backstory tab never learned the fire/held distinction
status: VERIFIED
tags: [backstory, defect]
anchor: digest/index.html:3173
---

## What

Confirmed 2026-09-28, `grep -n "stratum" digest/index.html` returns
nothing — the live in-app Backstory tab (`renderBackstoryTab()`,
`digest/index.html:3173`, and its detail modal, `openBsrDetail()` /
`bsrDetailHtml()`, `digest/index.html:3279-3313`) has no fire/held
branching anywhere. Every row gets the same treatment regardless of
`stratum`, confirmed live on the T-0046 deploy preview: "The Media" (a
`held` row with a real, earned `start_line` — "since Washington stopped
requiring broadcasters to air both sides, August 1987") renders
identically to a `fire` row would — big bare day count, twice, in two
formats ("39 yrs, 1 mo" then "14,300 days"), before the pairing line.
This is the exact confusion the editor originally raised this whole
Backstory thread with.

**Narrower than "rebuild the tab," and worth being precise about what's
already right:** the detail modal (`bsrDetailHtml()`) already has real
machinery this ticket should not touch — an indicator with an honest
"unverified" badge (`bsrIndicatorHtml()`, already correctly reading
`ind.verified`), an objects/"In the record" list, a narrative fallback
that already folds in `start_line` when no narrative exists yet, and an
episodes list (`bsrEpisodesHtml()`) that's already permalink-aware
(`x.permalink ? <a href=...> : <div>`, ready for T-0046's real
`story_permalink` the moment `instances[]` starts accumulating). None of
that needs rebuilding.

**What's actually wrong, specifically:**
1. `renderBackstoryTab()`'s list cards always lead with
   `bsrFormatDuration(days)` + the raw day count — never `r.pairline`
   first, never a stratum check. This is the reverse of what the editor
   specified for fire rows directly ("milestone, day count... in years
   and months") and the reverse of what the new design's 4A does (leads
   with the pairing line, `start_line`-based "It starts in {year}" for
   held rows only).
2. `openBsrDetail()`'s hero number (`bsrDetailNum`) is unconditionally
   `days.toLocaleString() + ' days'` — a bare, unformatted day count
   for every row, held or fire. No "Begins" section separate from the
   narrative-fallback paragraph the way 4C specs it.

## Why

The editor asked directly, after seeing the old list view still live on
a deploy preview that otherwise has T-0046's new work in it: is this
the same code, or something broken in the preview? It's the same
code — T-0046 built the standalone `/backstory/<row-id>/` pages and the
Digest cross-links, and never touched this file. Tracking that gap here
so it doesn't stay invisible the way it just was.

**Scope boundary, deliberately:** this ticket is the stratum-awareness
and list-view leading-element fix only — reusing the reconciled
approach already proven in `Backstory v5 (real data).dc.html` (4A/4C
split by stratum) and already live in `editorial/build_backstory_pages.py`'s
`render_held()`/`render_fire()`. It is not a rewrite of the detail
modal's already-working indicator/objects/episodes rendering, and it is
not the narrative essay (still explicitly out of scope, same as every
other Backstory ticket this session).

**A syntax check on this file needs the app's real verification
workflow, not a naive grep.** `digest/index.html` has multiple
`<script>` tags — small single-line analytics snippets plus the app's
one real inline block — so a simple "grab between the first `<script>`
and `</script>`" extraction (tried while writing this ticket's check)
silently grabs the wrong one. Verify a real change here by loading the
page and exercising it, per `CLAUDE.md` rule 4, not by trying to
`node --check` an extracted fragment.

## Done, 2026-10-01

Both fixed. `renderBackstoryTab()`'s list cards now branch on
`r.stratum`: held rows with a `start_line` lead with a terra "It starts
in {year}" kicker and the (first-letter-capitalized, not
`.toUpperCase()`-mangled) origin sentence; fire rows and any held row
without a `start_line` fall back to the single, non-duplicated
`bsrFormatDuration()` reading. `openBsrDetail()`'s hero number uses the
same years/months formatting for every row now (no more bare
`days.toLocaleString()`), with held rows additionally showing a "since
{year}" line — built as its own block-level element after testing the
inline-span version in a real browser and finding it wrapped
unpredictably at this width. Added a real "Begins" section to
`bsrDetailHtml()` (held rows only), separate from the no-narrative
fallback paragraph, which no longer duplicates `start_line` into itself.

**Verified by actually running the app**, not just the grep check below
— `scripts/preview.js` on localhost, real lineup data, clicked into a
real held row (Media) and confirmed the list card, the hero number, and
the new Begins section all render correctly; confirmed `verified: true`
indicators (post-T-0047) no longer show the "unverified" badge, as
expected. No fire row happened to be paired in today's real lineup to
click through, so that path was verified by calling
`renderBackstoryTab()`/`openBsrDetail()` directly in the browser console
against a synthetic fire-row object — the actual shipped functions, not
a mockup — and confirming the single duration, no kicker, no Begins, no
indicator/objects, exactly as designed. Syntax-checked the real inline
script block (`digest/index.html:2262-4424`, found by locating the
actual matching `</script>`, not a naive first-match grab) with
`node --check`.

## Check

```sh
set -e
grep -q "stratum" digest/index.html || { echo "OPEN: no stratum handling in digest/index.html"; exit 1; }

# The list view must branch: a fire row's card must not show the same
# leading element as a held row's. Weak but real — asserts the function
# body actually references r.stratum, not just that the word appears
# somewhere in the file.
awk '/^function renderBackstoryTab/{f=1} f{print} f&&/^}/{exit}' digest/index.html | grep -q "stratum" \
  || { echo "OPEN: renderBackstoryTab() doesn't branch on stratum"; exit 1; }

awk '/^function openBsrDetail/{f=1} f{print} f&&/^}/{exit}' digest/index.html | grep -q "stratum" \
  || { echo "OPEN: openBsrDetail() doesn't branch on stratum"; exit 1; }

echo "stratum-aware in both the list and the detail view"
```
