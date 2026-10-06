---
id: T-0076
title: Backstory's categories (rows) need another editorial pass, starting with where technology and AI stories land
status: PROPOSED
tags: [backstory, decision]
anchor: editorial/backstory-rows.json
---

## What

Named by the editor 2026-10-05 as part of the next effort: "improving Backstory categories."
Nothing is decided here; this records the state so the pass starts from facts.

The library is 21 rows: 14 in `editorial/backstory-rows.json` (Climate, The Media, Immigration,
Faith, Taiwan, Government, Order, America Abroad, Power, Work, Family, Equality, Korea, The Bomb)
and 7 hand-coded "Still Counting" conflict rows in `editorial/build_backstory.py`. Each held row
has a fixed `start_date` and a list of sub-genres, and the classifier assigns every story one
sub-genre. Facts worth having in front of you:

- No row is about technology or AI. Stories about it are filed under whichever row's argument
  they touch: 2026-10-05's Utah AI-prescribing story went to Government (regulation and the
  administrative state), Sam Altman's to Work (automation and AI displacement). Related
  sub-genres exist elsewhere: Family "children and technology", The Media "platforms and
  attention".
- 7 of the 48 sub-genres have fewer than two linked matrix objects (T-0071), so any new row or
  sub-genre needs matrix content with verified links before it can show a Beginnings timeline.
- `docs/decisions.md` records settled names and anchors (Equality not Race, Family not Sex,
  Government anchored at Prop 13) and two deferred rows (India-Pakistan as a 22nd, Surveillance
  as a row rather than a sub-genre under Order). Re-opening any of them is a decision, not a
  tidy-up.
- A row's start date is the year "We are here" marks and drives its elapsed time, so changing a
  category also changes those; see T-0074, which is the closely related question of which origin
  a story should be shown.

## Why

The categories decide what the product can say about a story. A story with no good home gets
a forced pairing (T-0074's examples), and the cheapest fix is often a better category, not a
better origin line. Open questions for the editor, not defaults: add rows, split a row, or only
add sub-genres; and who owns the matrix content a new row needs.

## Check

manual: the editor decides the category changes. Once decided, a check can assert the new row ids
in `editorial/backstory-rows.json` and that each has at least 3 linked matrix objects.

## Parked idea, raised by the editor 2026-10-06 (not for action)

Rows are what a reader can build expertise in, but on the front end a story could be shown as one of
three broad kinds: Foreign Policy, Civil Rights, or The Government and the Economy. A radical
simplification of what the reader sees, keeping the rows underneath. Recorded so it is not lost; no
decision, and it would touch how rows are named and grouped on the Thread and the Backstory tab.
