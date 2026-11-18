---
id: T-0126
title: The editor can pin a hand-built cluster as a standing topic that collects across days
status: PROPOSED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Proposed 2026-11-17, not decided. The editor named slow-moving topics he wants NTK to make clear: affordability,
corruption, cyber attacks, social media, climate change. Today nothing in the pipeline can hold one across days:

- `window.json` holds about a day of items (616 on 2026-11-17) and forgets; `clusters.json` is rebuilt from it every
  run.
- The ledger (`ledger.py`) classes restatements as INCREMENT and assembly drops them; triage drops "process
  increments". A slow topic is mostly increments, so the material is filtered out by design. Example: "Companies get
  billions in tariff refunds. Consumers are left with the bill." sat in the 2026-11-17 Stream and had no route to
  the Lineup.
- Pulse already lets the editor shape clusters by hand: merge clusters, pull articles out into a new one, add a URL,
  rescan the Stream for matches (local, no model call), and search by terms (the window, then two EventRegistry
  calls). But a manual cluster has no name, lives only in that browser, and is dropped after 5 days unused
  (`MANUAL_TTL_DAYS`).

The proposal: a **pin** on a manual cluster turns it into a named standing topic. It does not expire; rescan offers
each day's matching items; pulling it into the Lineup makes a story like any other, whose headline takes the
need-to-know shape (T-0125). No change to `cluster.py`, the ledger or triage.

## Why

From the same conversation as T-0125. The editor wants NTK to go from a news digest to a need-to-know digest:
"statements of the obvious, forcefully" about slow, constant topics, alongside the day's headlines, so a reader can
get clear on the news. A standing topic is where that statement comes from on a day with no single event: the
standing truth plus the pile of evidence since it was last told.

The editor, on this proposal: "this is close but I am not sure it's right." Open questions, unanswered:
- Is a topic a cluster at all? A cluster is a pile of articles about one event; a topic is a condition with a
  standing truth, and may want its statement stored with it, not just its articles.
- Browser-only storage (like the Lineup) or a file in the repo the pipeline can fill (triage tagging each item to a
  topic, close to free inside the Haiku call it already makes)?
- How a topic card fits the 4 to 10 ceiling: one rotating slot, or only when the pile has grown enough.
- What the reader sees: a card in the edition only, or later a topic page (which must still end).

Decisions this touches, said out loud: "Do not rebuild the Story Ledger inside Pulse as persistent cross-day
memory" and the Desk's retirement (`docs/decisions.md`). This is cross-day memory. The difference argued for: the
editor names and curates each topic by hand, it holds a pile, not a diff between runs, and the automatic clustering
is untouched, which is where the Desk went wrong. That argument has not been accepted; it needs the editor's
decision before anything is built.

Cost, if built as proposed: none for collecting (rescan is local; search is the two EventRegistry calls it already
makes). Writing a topic card costs what one Generate Jefferson story costs.

## Check

```sh
echo "manual: proposed; the editor decides whether a standing topic is a pinned cluster, and where it lives"
exit 1
```
