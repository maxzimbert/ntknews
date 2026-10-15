---
id: T-0091
title: Pulse's Backstory preview looks like the reader's /backstory page
status: DECIDED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-15, with screenshots of Pulse and of ntknews.org/backstory (the screenshots did
not reach the session that wrote this ticket; attach them here or in the PR). Measured on main that day: the
PREVIEW in a Pulse category (`catPreviewHtml`) is a beige box in Georgia with BEGINNINGS and a WE ARE HERE
marker. The reader's card (`renderBackstoryTab` in `digest/index.html`) has a different structure: TODAY with
the pairing line, IT STARTS IN with the origin, a mark, the theme name and a Backstory link, and the
category page (`showBsrPage`) has its own layout. They do not match, so the editor approves something that is
not what readers see.

Wanted: the preview renders the reader's own card and category page, from the same markup and CSS, with the
draft category's data. The best way is to share the render code (one function both pages load), not to copy
the look into Pulse, which would drift again.

## Why

Approving is the editor's last look. If the preview differs from the page, approval checks the wrong thing,
and every difference becomes a surprise found in production. `docs/design-system.md` governs the reader
page's look; Pulse should borrow it, not restate it.

## Check

```sh
manual: open a category in Pulse and the same category on /backstory side by side; the card and the page match except for draft-only controls
```
