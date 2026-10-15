---
id: T-0089
title: Before composing a new automatic category, the publish step files the story under an existing category that fits it
status: DECIDED
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

## Check

```sh
manual: publish the 2026-10-15 lineup twice with the gas story unfiled; the second run logs "joins the existing category" and provisional-rows.json gains no new row
```
