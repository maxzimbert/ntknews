---
id: T-0120
title: Pulse carries the editor's past Backstory judgment into each new build
status: PROPOSED
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html:4806
---

## What

Set aside by the editor on 2026-11-10 as a task for later, after T-0117 to T-0119.

Read in code 2026-11-10: Pulse keeps the editor's rejections (`rejected` in
`editorial/research-ledger.json`) and each story's own edits (`bs_edits` on the Lineup story). Nothing
carries a judgment from one story to the next. A scope the editor widened, a kind of document the editor
keeps removing, a line the editor rewrote: each is forgotten when the story leaves the Lineup. Unverified:
whether any other store holds this.

Proposed: a standing record of what the editor directed, removed, picked and rewrote, and a selection from
it given to every build as examples of the editor's call. T-0118's action log is the raw material.

## Why

The editor, 2026-11-10, asked for the build to work "as though you were my second brain and knowledge base."
T-0117 and T-0118 make the build decide more and ask less. This is the part that makes its decisions move
toward the editor's over time. The editor also expects it to steady the build: "maybe that helps mitigate
variance."

Not decided: what is recorded, how much reaches a prompt, and what it costs in tokens per build. Wait for a
few weeks of T-0118's action log before designing it, so the design is drawn from what the editor actually
does.

## Check

manual: not decided. When it is, the check is that a direction the editor gave on one story changes the
first build of a later story on the same subject.
