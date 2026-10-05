---
id: T-0075
title: At the bottom of the page, the story's Backstory pairing and category cannot be brought fully into view
status: PROPOSED
tags: [digest, defect]
anchor: digest/index.html
---

## What

Reported by the editor 2026-10-05: "when I reach the bottom of the page I'm unable to view the
Backstory and category in the viewport." Not reproduced and not measured. Unknown: which page
(a story in the Digest tab, the Today tab, or a Backstory page), which device and browser, and
whether the lower content is hidden behind the fixed bottom tab bar, clipped by a container that
does not scroll, or pushed below the safe area.

To act on it, this ticket needs a screenshot or screen recording at the bottom of the page, the
device, and the browser. The likely places to look are the fixed bottom tab bar and its padding
on the scroll container, `overflow` on the app shell, and the `bsrPage` overlay's own scroll
(`#bsrPage` is `position: fixed; inset: 0`).

## Why

Recorded so it is not lost between sessions. It is PROPOSED, not DECIDED, because nobody has seen
it fail yet; the first step is a reproduction, and a fix written before one would be a guess in
a 4,600-line file.

## Check

manual: the editor scrolls to the bottom of the affected page on the affected device and confirms
the Backstory pairing and its category are fully visible above the tab bar.
