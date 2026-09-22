---
id: T-0032
title: Backstory has no per-story pairing, and the story screen exists twice
status: DECIDED
tags: [backstory, feature]
anchor: digest/index.html:3922
---

## What

Two findings, measured 2026-09-22 while removing the story view's top bar
under T-0029.

**1. There is no pairing.** `openBackstoryModal()` at `digest/index.html:3922`
adds a `show` class to a static modal and fires an analytics event. That
modal's entire content is the words "Coming soon." No story object carries a
backstory reference — a story has `key`, `category`, `headline` and
`permalink` and nothing else. The 21 rows in `digest/data/backstory.json` are
keyed by `id` and `title` ("US–Canada trade war", "US–Israel–Iran") with no
field pointing back at a story. So the Backstory button has never opened
anything story-specific, on any surface, ever.

T-0029 removed that button along with the rest of the top bar. Backstory is
currently reachable only from the bottom-nav tab, which opens the whole list.

**2. The story screen is implemented twice, and the two disagree.** Arriving
from the digest gives you `#storyView` inside the app: the bottom nav is
hidden (`openStory()` adds `.hidden` to `#bottomNav`), and you close back into
the tab you came from. Arriving from a shared link gives you a standalone
static page written by `STORY_PAGE_TEMPLATE` in `build_digest.py`: different
markup, different stylesheet, no bottom nav at all, no route back into the app
except the links in the page.

That second finding is the root cause of several things already fixed
separately and expensively: the headline typeface drifted between the two
(T-0029), the permalink never received the type scale, the radii or the
tracking (T-0029), and its accents were still failing contrast on a light
ground years after the app's were set (T-0029). Every fix has to be made
twice, and historically the second one was missed.

## Why

The editor's framing was "I think something bigger is wrong," which is
correct, though not for the reason given — the nav is hidden on *both* paths,
not just the shared-link one. Verified in the browser: opening a story from
the digest sets `#bottomNav` to `display: none`.

Pairing is not a wiring job. `docs/state.md` already records the intended
design as Part 2, per-story pairings, and `docs/backlog.md` still lists
Backstory as open. Deciding which of 21 standing narratives belongs to a given
day's story is an editorial judgment, not a lookup — the same judgment the
four-section framework exists to make — so this needs the editor, not a
heuristic. A category match would be wrong often enough to be worse than
nothing, because a wrong pairing asserts a historical through-line that is not
there.

Sequencing note: if the two story implementations are ever collapsed into one,
do that **before** building pairing, or the pairing gets built twice as well.

## Check

```sh
# A story carries a backstory reference.
grep -qE 'backstory(_id|Id|Key)' ntk-pulse/build_digest.py

# The modal is no longer a placeholder.
! grep -q 'Coming <em>soon' digest/index.html

# Opening Backstory from a story resolves a specific row rather than a list.
manual: open a story, open Backstory, confirm it lands on that story's paired
        narrative and not on the 21-row index
```
