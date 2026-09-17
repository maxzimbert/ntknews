---
id: T-0007
title: The Backstory generator writes the file the app reads
status: VERIFIED
tags: [backstory, defect]
anchor: editorial/build_backstory.py:31
---

## What

Three places name the Backstory data file and all three must agree on
`digest/data/backstory.json`: the generator's output path, Pulse's publish
path, and the app's fetch. Verified passing 2026-09-17.

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
grep -q "GH_BACKSTORY_PATH = 'digest/data/backstory.json'" ntk-pulse/pulse.html
grep -q "'digest', 'data', 'backstory.json'" editorial/build_backstory.py
grep -q "/digest/data/backstory.json" digest/index.html
```
