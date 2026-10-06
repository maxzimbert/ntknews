---
id: T-0077
title: Story pages get one LISTEN · SHARE · BACK action bar and the logo at top left
status: BUILT
tags: [digest, feature]
anchor: digest/index.html:1810
---

## What

Measured 2026-10-06 against `main`. Both story surfaces, the in-app
`#storyView` and the static permalink from `ntk-pulse/build_digest.py`, put
the NTK logo at the right of the header (`margin-left: auto`). `/digest` and
`/today` already have it at left. Both also ended in loose controls: the app
in a `.share-bar` of three coloured buttons, the permalink in two in-page
buttons plus a text "Back to today's digest" link.

Built on branch `T-0077-permalink-nav`, from the handoff in
`design_handoff_ntk_permalink_nav/`:

1. Logo moved to the left in both headers. The real SVG logo is kept; the
   handoff mock's "NTK" text pill was wrong and was not used.
2. One `.action-bar` on both surfaces: LISTEN · SHARE · BACK, fixed to the
   bottom, 22px stroke icons over 10px / 600 / `.1em` labels. Chrome values
   are the app's own `.bottom-nav` (64px, `#1A1419`, 1px `rgba(234,217,197,.1)`
   border, 5px gap, safe-area inset). The handoff's values (72px, `#261F23`)
   were a guess its README said to replace.
3. Resting colour is `rgba(234,217,197,.6)`, not the tab bar's `.3`. In the
   tab bar `.3` means "inactive tab"; here nothing is selected, and `.3`
   would read as disabled. Pressed is `--blue`.
4. Desktop (not designed in the handoff): the bar is centred at 640px, the
   permalink's column width. Editor's call, open to change.
5. Listen's label cycles Listen / Pause / Resume in place of the old emoji
   text. Share falls back to copying the link (label flips to "Copied") where
   `navigator.share` is missing, which includes the Claude Code preview pane and
   most desktop browsers; it used to `alert()`, which the pane swallows.
6. Hero images get `object-position: 50% 25%` in both templates.

Checked in the browser on a local build: bar is 64px at the bottom at 375px
wide, labels compute to 10px / 600 / 1px, logo left edge 20px on both
surfaces, Listen cycles its label, Back closes the story view, bar sits
centred at 640px on a 1440px screen. **Unverified:** a real iPhone (safe
area, `:active` colour), the Netlify deploy preview, and whether heads
survive the crop. That last one needs ten recent stories rendered at 390x844
and 1440x900 and looked at. A person has to do that look.

**Plan B for faces**, only if the CSS default is not enough: detect faces at
build time with OpenCV's bundled Haar cascade in `build_digest.py`, write the
centre as `object-position` inline; fall back to `50% 25%` when none found;
an optional per-story `focal: "x,y"` override; per-breakpoint `aspect-ratio`
so the crop box is predictable; generate the 1200x630 OG image from the same
point. Free and local, but adds an OpenCV dependency to the build.

## Why

The permalink is where a shared link lands, and the app's story view is where
the beats ladder gets its signals. Design-system §9 says the two must render
the same design, so the bar and logo move on both or the surfaces drift, which
is the failure T-0034 was about. Two navs on purpose: the app's four-tab bar
moves between sections, this bar acts on one story and leaves it.

Ruled out: shipping the handoff's values as written (they contradicted the
app's real tab bar); the tab bar's `.3` resting colour (reads as disabled
when no item is active); face detection first (dependency cost for a problem
one CSS line may already solve, and nobody has looked at real crops yet).

T-0039's check still has to hold: both surfaces keep `toggleListen` and
`shareStory`, the ladder and the end mark.

## Check

```sh
# One bar on both surfaces, same three actions.
grep -q 'class="action-bar"' digest/index.html
grep -q 'class="action-bar"' ntk-pulse/build_digest.py
test "$(grep -c 'class="action-item"' digest/index.html)" -eq 3
test "$(grep -c 'class="action-item"' ntk-pulse/build_digest.py)" -eq 3

# The old loose controls are gone.
! grep -q 'class="share-bar"' digest/index.html
! grep -q 'story-actions' ntk-pulse/build_digest.py
! grep -q 'back-footer' ntk-pulse/build_digest.py

# Logo is no longer pushed right on either surface.
! grep -A4 '\.story-header-logo' digest/index.html | grep -q 'margin-left: auto'
! grep '\.story-header-logo' ntk-pulse/build_digest.py | grep -q 'margin-left: auto'

# Share copies the link when there is no share sheet.
grep -q 'function copyShareLink' digest/index.html
grep -q 'function copyShareLink' ntk-pulse/build_digest.py

# Hero crop biased toward faces.
grep -q 'object-position: 50% 25%' digest/index.html
grep -q 'object-position: 50% 25%' ntk-pulse/build_digest.py

# manual: the editor looks at ten recent stories at 390x844 and 1440x900 and no head is cropped. If any are, build Plan B.
```
