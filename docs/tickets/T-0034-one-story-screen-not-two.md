---
id: T-0034
title: Delete the app's own story-reading view; the permalink is the only one
status: BUILT
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

## Built, on top of T-0035 in the same branch

Two of the three things this ticket's own investigation said had to be
true for the deletion to be free — "sharing already used the permalink"
and "there is no in-story feature that only the app's view provides" —
turned out to be wrong in ways worth recording so the next person doesn't
trust that sentence at face value.

**Share was never actually reachable from the permalink.** `shareStory()`
itself was correct — it read `s.permalink`, not an in-app URL — but its
only caller anywhere in the app was `#storyView`'s own share-bar button.
Deleting the view would have deleted the only button that called it,
leaving no way to share a story from the one surface this ticket makes
canonical. Ported a `shareStory()` to `build_digest.py`'s
`STORY_PAGE_TEMPLATE` — same `navigator.share()`-with-`alert()`-fallback
pattern, now genuinely reachable since it's a real button on the page
everyone lands on.

**Listen was a real, in-app-only feature — the "no feature is app-only"
premise was checked, and was wrong.** The Web Speech API "🔊 Listen"
button existed solely inside `#storyView`; the permalink template had no
equivalent, no `<script>` tag at all before this change. Ported the full
thing — `htmlToText()`, the pause/resume state machine, the
`pagehide`-triggered cancel — to `build_digest.py`, with the story's own
headline/lede/truth/prob/poss/lies embedded as escaped JS string literals
via `jsEsc()`. Verified by rendering a fixture story and actually clicking
Listen in a browser, not by reading the diff: speech synthesis started,
paused, and resumed correctly.

**The beats engagement ladder loses real reach, permanently, and that's
bigger than "upper rungs go dormant."** `BEAT_REQS` (`digest/index.html`)
gates rung 1 ("Briefed") on `depth: 1` — a section opened — and rung 2
("Read It") on `lies: true` — the Lies hold-to-reveal actually used.
Both signals came exclusively from code inside `#storyView`
(`toggleSection()`, `revealLies()`) that has no equivalent on the
permalink, which shows Lies ungated and has no per-section open/close
state to track at all. `beatIdx()` picks the *highest* rung whose
requirements are met, so a reader who reads three stories now jumps
straight from "Skimmed" to "Following It" (rung 3) — "Briefed" and "Read
It" aren't skipped occasionally, they're unreachable, forever, for every
reader, starting now. Rungs 4–6 ("On the Beat," "Carrying It," "Witness")
were already gated on `depth`/`lies` too, so they were already
unreachable the moment items 1–2 became unreachable. This was surfaced to
the editor directly before building anything (a "port the tracking" vs.
"accept the cap" vs. "stop and rescope" choice), with the added context
that recreating this instrumentation on a page meant to be a stateless,
addressable, PWA-shaped surface would mean rebuilding SPA-style session
tracking on top of it — which is the opposite of what "no app state is
fine, this should be a PWA" asks for. Editor's call: accept it. Deleted
the now-dead functions (`beatsRecordOpen`, `beatsRecordDepth`,
`beatsRecordLies`, and the entire beat-toast-on-close mechanism —
`showBeatToast`, `beatsToastCopy`, `beatsShouldToast`, `beatsMarkToast`,
plus the `#beatToast` markup and CSS — all of it only ever called from the
functions this ticket deletes) rather than leave them as inert scar
tissue. `beatsRecordRead` (story count) still fires on every real link
tap, so "Following It" (3 stories, 2 sessions) is still reachable, and the
"Your beats" panel and its rung explainer still render correctly for
whatever a reader already has.

**A real crash bug, found by tracing every remaining reference to
`currentStoryIndex` and `#storyView` rather than trusting the deletion was
clean.** `buildFeedbackMailto()` called
`document.getElementById('storyView').classList.contains('active')`
unconditionally — once the element doesn't exist, that's
`null.classList`, thrown on every single page load, since it's called
from init. Fixed by removing the now-impossible in-story branch entirely,
along with the sibling `updateFeedbackBtn()` check that happened to be
null-guarded already and so degraded silently instead of throwing. Also
found and fixed the same class of leftover in `openBackstoryModal()` —
pre-existing dead code (zero callers, unrelated to this ticket) that
referenced `currentStoryIndex` after this ticket's edits removed that
variable's declaration; deleted rather than patched, since nothing calls
it.

**A regression this ticket's own change would have introduced: swipe vs.
tap on a real link.** Turning `.story-card` from a `<div onclick>` into a
real `<a href>` means the browser can fire a synthetic click after a
touch-drag ends on top of it — exactly the gesture "swipe right to mark
read, stay on the list" performs. Without a guard, a firm swipe could
navigate away instead of just dimming the card. Fixed with a `justSwiped`
flag set whenever a drag moves past a small threshold, checked and
cleared in a `click` listener that calls `preventDefault()` — a tap with
no real movement still navigates normally.

**Read state wasn't actually restored on load — only tracked going
forward.** Moving `readStories` to `localStorage` (keyed
`ntk_read_<today's date>`, via `readStoriesKey()` / `loadReadStories()` /
`saveReadStories()`) was necessary but not sufficient: `buildDigest()`'s
card template didn't check `readStories` when generating each card's
initial classes, so a story marked read, then the page reloaded, rendered
as unread again — dims, progress count and Moment-of-Then circles all
reset even though the underlying data was correct. Caught by testing the
actual reload, not by reading the persistence code and assuming it was
wired all the way through. Fixed: `buildDigest()` now applies
`read-dimmed`/`.filled` from `readStories` at render time, and calls
`updateProgress()` once at the end to sync the progress bar and Moment of
Then count — guarded so it can't re-fire the `digest_complete` analytics
event or re-run the completion animation if a reader who already finished
today's digest simply reloads the page.

**Cleanup.** ~200 lines of CSS that existed only for `#storyView` —
`.story-header`, `.story-hero*`, `.section-*`, `.lies-*`, `.share-bar`,
`.share-btn*`, and (confirmed via the same dead-reference sweep) the
`.ntk-pullquote`/`.ntk-stat*` visual-component styles, since nothing in
the app injects `s.truth`/`s.prob`/`s.poss`/`s.lies` into the DOM anymore
— the identical class names stay alive and necessary in
`build_digest.py`'s own copy, untouched. The now-fully-unused
`--purple` CSS custom property was also removed. `.today-item` and the
`[STORY: key | label]` onramp links in Today's overview prose are real
`<a href>` elements now too, for the same reason the digest cards are.

Two more purple leaks were caught on review of the deploy preview and
fixed under T-0035's commits in this same branch (an onboarding card's
literal `#725ABF` fill, and confirming the Backstory domain cards' tint —
already correct, reading `BEATS_SCALE`'s recalibrated color, not a second
miss) — noted here since they surfaced during this ticket's review pass,
recorded in full under T-0035.

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

# Story cards are real links to the permalink, not click handlers.
grep -q 'class="story-card' digest/index.html
! grep -q 'onclick="openStory' digest/index.html

# Read state persists to localStorage, keyed per edition, and the render
# applies it — not just tracks it going forward.
grep -q 'function readStoriesKey' digest/index.html
grep -q 'readStories.has(i)' digest/index.html

# Listen and Share made it onto the one surviving reading surface.
grep -q 'id="listenBtn"' ntk-pulse/build_digest.py
grep -q 'function shareStory' ntk-pulse/build_digest.py

# The crash this ticket's own deletion would have caused is gone —
# nothing left references the deleted #storyView element unconditionally.
! grep -q "getElementById('storyView')" digest/index.html
```

Manual, beyond what a check can prove — done during this build, not
deferred: rendered a fixture story through `build_story_page()` and
clicked Listen for real in a browser (speech synthesis started, paused,
resumed); clicked a live digest card with navigation intercepted and
confirmed `markStoryRead` fired and `localStorage` updated before the
navigation would have happened; reloaded with a story already marked read
and confirmed the card, progress bar, and Moment of Then circle all
restored correctly, not reset to zero.
