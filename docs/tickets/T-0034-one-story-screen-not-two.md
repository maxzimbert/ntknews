---
id: T-0034
title: Delete the app's own story-reading view; the permalink is the only one
status: DECIDED
tags: [digest, chore]
anchor: digest/index.html:2165
---

## What

Measured 2026-09-22, prompted by the editor asking why the share button
can't just send the URL it already sends.

**Sharing already works.** `shareStory()` at `digest/index.html:3898` reads
`const shareUrl = s.permalink || window.location.href` and hands that to
`navigator.share()`. It has always sent the static permalink, never an
in-app URL. Nothing to build there.

**The duplication is the other direction.** A story card in the digest list
is `<div class="story-card" onclick="openStory(i)">` — a click handler, not
a link. Tapping a story opens `#storyView`, a second, independent reading
implementation inside the app: its own header, its own hero, its own four
section rows, its own share bar, ~36 CSS selectors, and the `openStory()` /
`closeStory()` functions that drive it. The permalink page a story's own
Share button already points to renders the same content, already carries
working OG/Twitter tags, and — as of T-0029 — is on the same type scale,
radii and certainty ladder as everywhere else. `#storyView` is the one that
duplicates a page which already exists and already works.

**The fix is deletion, not addition:**

1. Story cards become real `<a href="{permalink}">` elements. Tapping one
   is a normal navigation to the page `shareStory()` already sends.
2. Delete `#storyView`, `openStory()`, `closeStory()`, and the CSS that
   exists only for them.
3. Move read-tracking off in-memory state and onto something that survives
   a real navigation.

That third point is not a new requirement this change invents — it exposes
one that already exists. `readStories` (`digest/index.html:2358`) is
`let readStories = new Set()`: pure in-memory, zero persistence, reset by
any reload. The "0 of 4 read" counter, the swipe-to-read dimming, and the
"you came back" orientation moment (`n === 3` at `digest/index.html:3644`)
all key off it. Today that fragility is masked because reading happens
inside one unbroken SPA session. The moment tapping a story is a real
navigation away from the list, every one of those breaks on the very first
read unless the state moves to `localStorage`, keyed per edition so it
resets when the day's stories do.

Checked and ruled out as scope: there is no next/prev-story navigation
inside `#storyView` to preserve — every `currentStoryIndex + 1` hit is
analytics, not navigation. Nothing is lost there.

**Supersedes T-0033.** That ticket asked what job the app's empty story
header should do. With one reading surface instead of two, the question
dissolves — there is no separate in-app header left to design. Closed as
discarded, not answered.

## Why

Named directly by the editor: no use case for a second implementation, and
the app was already sending the good one out the door every time someone
hit Share. Confirmed in code rather than assumed — three things had to be
true for this to be free rather than a regression, and all three checked
out: sharing already used the permalink, the permalink already carries
proper meta tags (the app carries none, at all, anywhere), and there is no
in-story feature that only the app's view provides.

This is also why T-0029's fixes kept having to be made twice — the two
implementations drifted (different headline typeface, missing type scale,
stale contrast values) because every change had two places to land and the
second one was easy to forget. Collapsing to one surface removes the
mechanism that produced that drift, not just the current instance of it.

Verifying this by hand, beyond the check below, before promoting to
VERIFIED: tap a story from `/digest` and confirm the address bar navigates
to its real permalink URL rather than an in-app view; then reload `/digest`
and confirm that story still shows as read. `readStories` has no
persistence today, so that second half is the one behavior this ticket
depends on that a grep cannot prove, and the one most likely to regress
silently if the persistence work is skipped.

## Check

```sh
# The app no longer renders or drives its own story-reading view.
! grep -q 'id="storyView"' digest/index.html
! grep -qE 'function (openStory|closeStory)\(' digest/index.html
```
