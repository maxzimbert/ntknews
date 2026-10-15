---
id: T-0091
title: Pulse's Backstory preview looks like the reader's /backstory page
status: DECIDED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-15 with two screenshots. The reader's card on ntknews.org/backstory
(`renderBackstoryTab` in `digest/index.html`) reads top to bottom: TODAY, the pairing line in quotes, IT
STARTS IN <year> in red capitals, the origin in italic serif, a small mark, and the category name in bold
sans at the foot. The same story in Pulse's TODAY'S PAIRINGS list (`pairingsHtml` in
`ntk-pulse/pulse.html`) reads: the category name in bold with the classifier's confidence ("1.00"), "It
starts in 2022" in plain sans, the origin in plain sans, then the pairing line, then the headline, in a grey
bordered box. Same data, different order, labels and type. The category PREVIEW (`catPreviewHtml`) is a third
layout again (Georgia, BEGINNINGS, WE ARE HERE), and the reader's category page (`showBsrPage`) a fourth.

Wanted: Pulse renders today's pairings and each category's preview with the reader's own markup and CSS,
fed Pulse's data. Editor-only facts (confidence, the headline, needs-review flags, draft status) sit outside
the card, in a strip above or beside it, so the card itself is exactly what a reader will see. The way to
get there is to share the render code (one function both pages load), not to copy the look into Pulse,
which would drift again.

Seen in the same screenshots, unverified: Pulse's Ukraine-Russia line ("A private company decided overnight
how much of the war Kyiv could see...") is not the line live on /backstory that day ("A private company's
pricing tier decided what Kyiv could see and strike overnight..."). Pulse caches the published
`backstory.json` for the session (`BSR_PUBLISHED`), so a Pulse tab opened before a later publish shows the
older pairings. The parity work should refetch after a publish or say how old the copy is.

## Why

Approving is the editor's last look. If the preview differs from the page, approval checks the wrong thing,
and every difference becomes a surprise found in production. `docs/design-system.md` governs the reader
page's look; Pulse should borrow it, not restate it.

## Check

```sh
manual: open a category in Pulse and the same category on /backstory side by side; the card and the page match except for draft-only controls
```
