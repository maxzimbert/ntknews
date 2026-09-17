---
id: T-0009
title: The strategy corpus lives in files no agent can open
status: PROPOSED
tags: [corpus, chore]
anchor: CLAUDE.md
---

## What

Six documents the READMEs treat as authoritative are outside this repo, in
formats a cold session cannot read: the v14 editorial prompt system, the
Editorial Standards Memo (the "Constitution"), the Story Selection Brief, the
Roadmap, the SWOT, and `NTK_MomTest_Tracker.numbers`.

Canonical-vs-mirror is already settled — the repo copy becomes the real one,
and a `.docx` gets generated *from* it when a human needs one to read. Never
re-imported over it. What remains is conversion order and fidelity per
document.

## Why

The source of truth pointed outside itself, which is the same failure as
documentation that asserts a fix that was never written, only slower and with
higher stakes.

The Mom Test tracker is the sharpest case and probably the first thing to move.
Every marketing, funder and hiring conversation turns on audience evidence, and
right now the answer to "what do we know about our readers" is a Numbers file
no session can open. That is the only real audience evidence NTK has.

This is plausibly worth more than the ticketing system it was filed alongside.
Ticketing prevents future drift; this unlocks every downstream ask. They are
different problems and this one may be first in line.

Fidelity, roughly: prompts and standards want to be Markdown where they can be
diffed and where a check can assert the live `pulse.html` copy matches; the Mom
Test data wants to be CSV; the SWOT and Roadmap want to be Markdown.

## Check

```sh
test -f docs/corpus/momtest.csv
```
