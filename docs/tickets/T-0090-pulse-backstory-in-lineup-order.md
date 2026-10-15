---
id: T-0090
title: Pulse's Backstory tab shows the Lineup's stories in Lineup order, each with its category
status: DECIDED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-15. Measured on main that day: the Backstory tab in Pulse has two lists, and
neither is the Lineup. TODAY'S PAIRINGS (`pairingsHtml`) reads the published `backstory.json`, so it shows
the last publish, not the Lineup being edited. CATEGORIES (`catListAll`) lists every local category in the
order it was created, then published ones, with no tie to today's stories. A story with no category filed
does not appear on the tab at all, which is how the gas story went out unfiled on 2026-10-15 (T-0089).

Wanted: the tab opens on today's Lineup, in Lineup order, one entry per story with the category it is filed
under (or "none filed", visibly), and the category list below it. Reordering the Lineup reorders this.

## Why

The editor works story by story in Lineup order. A Backstory tab in another order makes the editor hunt for
the story in hand, and hides the unfiled ones, which are the ones that need attention. The reader page now
follows digest order (T-0088); Pulse should show the editor the same order before publishing.

## Check

```sh
manual: reorder two stories in Lineup; the Backstory tab lists them in the new order, and a story with no category says so
```
