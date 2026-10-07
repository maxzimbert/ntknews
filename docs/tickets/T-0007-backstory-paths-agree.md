---
id: T-0007
title: The Backstory generator writes the file the app reads
status: VERIFIED
tags: [backstory, defect]
anchor: editorial/build_backstory.py:31
---

## What

Three places name the Backstory data file and all three must agree on
`digest/data/backstory.json`: the generator's output path, Pulse's read of what
published, and the app's fetch. Verified passing 2026-09-17. Amended 2026-10-07:
Pulse's own Backstory publish (the disabled `GH_BACKSTORY_PATH` write) was
removed with the legacy Backstory editor (T-0079), so the Pulse leg of the check
is now its read of the published file, not a publish path. The property is the
same: no reader and writer pointing at different files.

## Why

This is a regression guard for the structural failure that ran unnoticed for
the entire life of the feature: `build_backstory.py` wrote to
`digest/v2/data/` — the inert tree, served to nobody — while
`digest/index.html` fetched `/digest/data/`. The generator and the reader
pointed at different files and no artifact connected them, so nothing could
notice. It was found by reading, not by failing.

`digest/v2/` is deliberately retained so old reader-facing URLs still resolve,
which means the wrong path will always be a live, writable directory. It will
never error. That is precisely why this needs a check rather than a comment.

The check asserts agreement across all three, not the correctness of any one,
because any single path being right is not the property that matters.

## Check

```sh
grep -q "../digest/data/backstory.json" ntk-pulse/pulse.html
grep -q "'digest', 'data', 'backstory.json'" editorial/build_backstory.py
grep -q "/digest/data/backstory.json" digest/index.html
```
