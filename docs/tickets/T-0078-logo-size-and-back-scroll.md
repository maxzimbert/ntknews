---
id: T-0078
title: Logo is 28px on every surface, and Back from a story returns to where you were in the list
status: VERIFIED
tags: [digest, defect]
anchor: digest/index.html:114
---

## What

Found by the editor on prod after T-0077 shipped. Measured 2026-10-06.

1. **Logo size.** `/today`, `/digest`, `/backstory` and `/me` draw the logo at
   28px tall (`.ntk-logo-img`). The in-app story view and the static permalink
   drew it at 20px (`.ntk-logo-img-sm`), and the landing page (`index.html`) at
   44px (`.logo-wrap img`). The landing page's SVG is a different file from the
   app's but has the same `viewBox` (201.75 x 100.5), so the same pixel height is
   the same visible size. All five are now 28px.
2. **Back lost the scroll position.** `openStory()` called `window.scrollTo(0,0)`,
   and the tab view is `display:none` while a story is open, which makes the
   browser clamp the page scroll to 0 before the history entry is written. Back
   (`closeStory` -> `history.back()` -> `popstate`) therefore landed at the top.
   `openStory` now records `window.scrollY` first, resets the story overlay's own
   scroll instead of the window's, and `closeStory` restores the saved value. It
   restores again a frame later and 60ms later, because the browser applies its
   own saved scroll for the history entry after `popstate` and would otherwise
   win.

Checked in the browser on a local build: with the Digest tab scrolled to 316px,
opening a story and pressing Back lands at 316px, URL back to `/digest`. Logo
computes to 28px on the Digest tab, the story view and the landing page.
Editor confirmed both on the Netlify deploy preview 2026-10-06. **Unverified:** a real iPhone (Safari restores scroll differently), Back via the
browser's own back button or swipe, and the static permalink's logo in a render.

## Why

T-0077 moved the logo to the left but kept the story surfaces' smaller size,
which made the brand mark change size mid-session. A reader who taps into a story
and presses Back to find their place has lost it if the list jumps to the top;
for a digest of a few dozen stories that is the difference between "carry on" and
"start again", and the product's promise is that the digest ends.

Ruled out: `history.scrollRestoration = 'manual'`, which would also stop reloads
restoring scroll anywhere in the app. The delayed re-apply is uglier but local to
closing a story.

## Check

```sh
# One logo height across surfaces.
grep -A2 '\.ntk-logo-img {' digest/index.html | grep -q 'height: 28px'
grep -A2 '\.ntk-logo-img-sm {' digest/index.html | grep -q 'height: 28px'
grep -q 'ntk-logo-img-sm {{ height: 28px' ntk-pulse/build_digest.py
grep -q 'logo-wrap img{height:28px' index.html

# Back restores the list's scroll.
grep -q 'scrollBeforeStory' digest/index.html
grep -q 'keepScroll' digest/index.html

# manual: on a phone, scroll the Digest tab, open a story, press Back, and land where you were.
```
