---
id: T-0098
title: Each Lineup story on Pulse's Backstory tab can be previewed as the reader will get it, built up from several matrix searches, and given a new category from three suggested names
status: VERIFIED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Asked for by the editor 2026-10-16, after using T-0097's matrix search on the live Pulse. Three additions to
each story on the Backstory tab's Lineup:

1. **Preview.** The story's Backstory as a reader would get it before publish: the reader's own card (T-0091),
   then the category's Beginnings and objects. A fixed row shows what is published for it; a Pulse category
   shows its record as it stands. The Today line and "It starts in" are written at publish, so the preview
   shows the last published ones when the story was already paired there, and says so otherwise.
2. **Kept picks.** Ticking a matrix hit keeps it on the story (`bsPicks`, saved with the Lineup), so the
   editor can search again with other words and tick more, then add them all at once.
3. **Three names.** Starting a category from the kept picks offers three names written from the story,
   its subject and the picks, and a box for the editor's own. One Sonnet call per request, about a tenth of
   a cent; it replaces the browser prompt, which the Claude app's browser pane does not show.

Measured on `main` 2026-10-16 before this change: a ticked hit was lost on the next search (ticks lived in
the DOM only), starting a category asked for a name with `prompt()`, and the Backstory tab had no
per-story preview; the only reader cards were inside a category's editor and in "Today's pairings, as
published".

Built 2026-10-16 on branch `T-0098-backstory-story-preview`, exercised in a local Pulse (no console errors):
preview for a Pulse category, a fixed row (with its last published Today line) and an unfiled story; four
picks kept across two searches and a page reload; three names offered with an existing one dropped; a name
picked creates the category, files the story and adds all four; "add N to" a category; the naming panel's
error path when no key is set. The success path of the name call was run against a stubbed reply, not the
live model.

Also changed while testing, because the first results were wrong:
- **Ranking.** "war powers" ranked Abigail Adams's "Remember the Ladies" first: its About text mentions a war
  and a power. A word in About text now counts less than one in a title or Beginning line, and every word is
  weighted by how rare it is across the matrix, so "guard" outweighs "national". A whole phrase found in About
  still scores. Tested: "war powers" now leads with the war messages and declarations.
- **Saying when the matrix has nothing.** Keywords no matrix object contains are named under the results,
  with a pointer to FIND SOURCES; if a candidate covers one, it is named too ("Privacy Act of 1974 is on the
  candidates sheet: move it into the matrix to use it here"). Measured: the matrix has nothing on "guard",
  "insurrection" or "privacy".

## Why

The editor builds a story's Backstory from the matrix rather than from web search (T-0097, and the aim in
`docs/proposals/object-matrix-retrieval.md`). One query rarely finds everything: a story about a contested
deployment wants objects found by "war powers" and others found by "National Guard". Losing the first set to
run the second made the editor choose between them. The preview answers "what will the reader get" at the
point of filing, instead of after publish, when fixing it means another publish.

The suggested names come from a model because a name has to fit the story, and the cost per request is
negligible. Names already used by a category or row are dropped, so a suggestion never collides with an
existing page.

## Check

```sh
node scripts/test_pulse_categories.js | grep -q "^ok   catNameChoices: three clean names" \
  && node scripts/test_pulse_categories.js | grep -q "^ok   catNameChoices: an existing category name is dropped" \
  && grep -q 'class="mini bsr-lu-prev"' ntk-pulse/pulse.html \
  && grep -q 's.bsPicks' ntk-pulse/pulse.html \
  && grep -q 'class="mini bsr-name-pick"' ntk-pulse/pulse.html
```
