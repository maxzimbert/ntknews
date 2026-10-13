---
id: T-0086
title: A Backstory milestone can carry several objects, and the 3-to-6 Beginnings limit is re-decided for editor-outlined categories
status: PROPOSED
tags: [backstory, decision]
anchor: editorial/categories.py
---

## What

Raised by the editor 2026-10-13: the page they want is milestones that connect to the category name, each
with objects that elaborate on it. Measured on main (5c29038): a category record has `objects` and
`beginnings`, and every Beginning is one object (`beginnings[].object_id`, validated in
`editorial/categories.py` and `validateCat` in `ntk-pulse/pulse.html`). There is no milestone that holds
more than one object. `docs/backstory.md` sets Beginnings at 3 to 6 dated entries, and Compose trims a
page to six objects; the editor's Trump outline has eight milestones.

## Why

T-0085 lets the editor find several sources per milestone, but the page can show only one of them as the
milestone and the rest as loose objects. The two-level shape changes the published record, both
validators, `backstory.json`, and the reader page, so it is a schema decision, not a Pulse tweak.

Open, for the editor: (1) whether a milestone holds one Beginning line and several objects, or each object
keeps its own line; (2) whether an editor-outlined category may exceed six Beginnings, and the new cap;
(3) whether the T-0083 rework, if it merges, already settles this.

## Check

```sh
manual: decide the three open questions above, then replace this check with one against the schema
```
