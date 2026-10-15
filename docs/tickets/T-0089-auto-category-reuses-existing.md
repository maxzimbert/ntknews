---
id: T-0089
title: Before composing a new automatic category, the publish step files the story under an existing category that fits it
status: BUILT
tags: [backstory, defect]
anchor: editorial/build_pairings.py
---

## What

Measured 2026-10-15 from three publishes of the same lineup. The gas-price story was published with no
category filed (`backstory_row` empty), so step 5C treated it as a misfit and composed a category from the
name the classifier proposed. A story joins an existing category only when the proposed name's slug matches
exactly (`slug(name) in existing`, `auto_categories`). Three runs proposed three names, so
`ntk-pulse/data/provisional-rows.json` now holds `p-cost-of-living`, `p-inflation` and
`p-inflation-and-cost-of-living` for one subject, plus the editor's own "Energy prices"
(`p-economy-and-affordability`). The editor had approved Cost of Living in Pulse before the third publish;
approving a category does not file a story under it, and 5C never looked at it.

Each composed category costs several model calls with web search, and each becomes a public page.

## Why

Categories are meant to accumulate: a reader builds expertise in a subject across days. A new near-duplicate
per publish splits that history across pages and multiplies spend. Decided, for the editor to overturn: 5C
first offers the classifier the categories that already exist (approved by the editor, or automatic and not
archived), with their contest lines, and files the story under one when it fits; it composes only when none
does. A story the editor filed is still never touched. Pulse should also warn on publish when a story has no
category but an approved category exists that it was composed from.

Ruled out: fuzzy matching on names. "Inflation" and "Cost of Living" share no words; the match has to be by
meaning, which means the classifier.

Built 2026-10-15: before composing, `auto_categories` offers each misfit story the categories live that day
(the editor's and earlier automatic ones) in one Haiku call, `match_existing`, which answers an id from the
list or null; an id outside the list is ignored. A match joins the story to that category and composes
nothing. Cost: one short Haiku call per misfit story, at most three per publish, against a composition's
several Sonnet calls with web search. Not built: the Pulse publish warning; T-0090 now shows unfiled stories
at the top of the Backstory tab, which covers most of it.

Not verified against the real model: the editor's next publish is the test.

## Check

```sh
python3 editorial/test_compose_category.py > /tmp/t0089.log 2>&1 || { grep FAIL /tmp/t0089.log; exit 1; }
grep -q "^ok   it joins the existing category under a different proposed name" /tmp/t0089.log
# manual: on the next live publish with a misfit story, the log reads "joins the existing category ... (matched by subject)" when one fits
```
