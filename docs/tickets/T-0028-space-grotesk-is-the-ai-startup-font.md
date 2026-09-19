---
id: T-0028
title: Space Grotesk reads as generic AI-startup type; swap to Overpass, and two templates never loaded either font at all
status: VERIFIED
tags: [digest, defect]
anchor: ntk-pulse/build_digest.py:311
---

## What

Verified 2026-09-19. `'Space Grotesk'` is the UI-chrome sans (kickers, labels,
nav, timestamps, big numbers — never body copy, never headlines in the app
itself) in three places: `index.html` (2 refs + the Google Fonts `<link>`),
`digest/index.html` (87 refs + the link — this file serves `/today`,
`/backstory`, `/me`, and every frozen dated edition), and
`ntk-pulse/build_digest.py`'s `STORY_PAGE_TEMPLATE` (build_digest.py:311,
7 refs) and `ARCHIVE_TEMPLATE` (build_digest.py:607, 2 refs). Decided: replace
it everywhere with Overpass, an OFL-licensed Google Fonts family drawn
directly from the FHWA Highway Gothic road-sign alphabet — matches the
editor's stated direction and drops in on the same Google Fonts `<link>`
mechanism already in place, no self-hosting.

Found while auditing this, not part of the original ask: `STORY_PAGE_TEMPLATE`
and `ARCHIVE_TEMPLATE` declare `font-family: 'Space Grotesk'` /
`'Source Serif 4'` in their `<style>` blocks but their `<head>` never includes
a Google Fonts `<link>` at all — confirmed live on
`ntknews.org/digest/2026-09-18/three-guys-and-a-200-subscription-broke-into-openai-it-took/`
and `ntknews.org/digest/archive/`: `document.querySelectorAll('link[href*=fonts.googleapis]')`
returns empty on both, so every story permalink page and the whole archive
index render in Georgia/system-sans fallback today, regardless of which font
name is in the CSS. Also on `STORY_PAGE_TEMPLATE` specifically,
`.story-hero-headline` is set to Space Grotesk 700 — unlike `digest/index.html`,
where headlines are always Source Serif 4. Decide while touching this file:
either match the app (Source Serif 4 headline) or leave it Overpass
deliberately, but don't leave it as an unexamined inconsistency.

Out of scope: `digest/v2/` (inert, do-not-edit per `CLAUDE.md`), and the
unrouted orphans (`ntknews-index.html`, `ntknews-momtest.html`,
`ntk-desk/desk.html`, `rss-scanner/index.html`).

## Why

Space Grotesk is one of the most common defaults on AI-product landing pages
right now; the editorial voice this whole product is built around (plain,
non-hyped, closure over engagement) is undercut by chrome that visually
matches the thing it's implicitly distancing itself from. Low cost to fix —
it's a font-family swap, not a rebuild — which is exactly why it was worth
just shipping rather than relitigating.

The missing `<link>` is the more expensive finding: it means today's
`Space Grotesk` swap, if done by search-and-replace alone, would silently do
nothing on permalinks and the archive, the same class of silent-failure this
project has been burned by before (regex substitutions that no-op, fixes that
look sufficient on the page you tested and aren't on the ones you didn't).
Fixing it here costs nothing extra — same lines are being touched for the font
swap anyway — but skipping it would leave two live, reader-facing page types
still rendering fallback fonts after this ticket claims VERIFIED.

National Park Typeface and a Highway-Gothic-adjacent LA civic-lettering
direction were discussed and explicitly deferred, not folded in: they're
display-weight ideas for a single accent element (a big number, a wordmark),
not a system-wide label font — carved/display type doesn't hold up at the
9–16px tracked-out sizes this role actually needs. That stays a separate,
later, "does this feel right once we see it" decision.

## Check

```sh
# No live surface still references Space Grotesk.
! grep -l "Space Grotesk\|Space+Grotesk" index.html digest/index.html ntk-pulse/build_digest.py

# Overpass is loaded via a working Google Fonts link in all three.
grep -q "Overpass" index.html && grep -q "fonts.googleapis" index.html
grep -q "Overpass" digest/index.html && grep -q "fonts.googleapis" digest/index.html
grep -q "Overpass" ntk-pulse/build_digest.py

# Both templates in build_digest.py now carry the Google Fonts link
# (previously zero matches for either — that absence is the bug).
awk '/^STORY_PAGE_TEMPLATE/,/^def build_story_page/' ntk-pulse/build_digest.py | grep -q "fonts.googleapis"
awk '/^ARCHIVE_TEMPLATE/,/^def rebuild_archive/' ntk-pulse/build_digest.py | grep -q "fonts.googleapis"

# Fixture run: the generated permalink HTML actually contains the link,
# not just the source template (per CLAUDE.md: run generated Python output,
# don't just read the script).
python3 -c "
import sys; sys.path.insert(0, 'ntk-pulse')
from build_digest import build_story_page
html = build_story_page(
    {'headline': 'Test Story', 'lede': 'x', 'sections': {}, 'slug': 'test'},
    'images/test.jpg', 'https://ntknews.org/digest/images/test.jpg',
    'https://ntknews.org/digest/2026-09-19/test/')
assert 'fonts.googleapis' in html, 'permalink HTML has no font link'
assert 'Overpass' in html, 'permalink HTML does not reference Overpass'
print('OK')
"
```
