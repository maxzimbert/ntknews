---
id: T-0087
title: A rejected automatic category no longer crashes the pairing step and costs every story its Backstory link
status: VERIFIED
tags: [backstory, defect]
anchor: editorial/build_pairings.py
---

## What

Publish of 2026-10-14 18:28Z (run of "NTK Pulse — Publish to Digest", commit cf524d0). The editor published
seven stories; the digest and Today updated, and ntknews.org/backstory kept showing the previous edition's
stories. From the run log:

- Step 5C composed "Consumer Robots" for the Cologne robot story, the checks then rejected it ("only 1
  object(s) survived the checks; an automatic category needs two"), but the story still pointed at
  `p-consumer-robots`. `write_lines` raised `KeyError: 'p-consumer-robots'` and the step exited 1.
- The step is `continue-on-error`, so the run reported success. `backstory.json` kept the old pairings,
  `build_origins.py` found "no stories with a pairing", and the digest logged "0 of 7 stories cross-link
  to Backstory today".
- Separately, the editor's approved category "Economy and affordability" was rejected: its seven objects
  were found by Pulse search before T-0085, which never stored the page quote CI requires for a
  `found_by: "search"` object, so all were dropped and the category had none left. The gas story filed
  under it fell back to the classifier and got the automatic "Cost of Living".

Fixed: `auto_categories` returns a story whose composed category was not created to the row it was
classified to (as it already did when composing fails), and `main` drops, with a log line, any entry
whose row does not exist, so one bad story cannot take the others down. Pulse shows a category's
quote-less found sources with a "Keep them as my sources" button: the editor's own source needs no quote,
and CI still checks each link loads. Against the real record from this publish, Economy goes from rejected
to 6 objects and 6 Beginnings.

The integration test in `editorial/test_compose_category.py` read the live `lineup-publish.json`, so it
broke the moment this publish replaced the story it named. It now reads a pinned copy,
`editorial/fixtures/lineup-altman.json`.

## Why

Backstory is the product's long-memory half, and this failure was silent: a green run, a fresh digest, and
yesterday's pairings on /backstory. `continue-on-error` on these steps is deliberate (the digest must
ship), which makes a crash in them cost a whole day of Backstory with nothing red anywhere. Ruled out:
removing `continue-on-error`, which would let a Backstory bug block the digest. Not done here, and worth a
ticket if it recurs: making the run visibly amber when a Backstory step fails.

## Check

```sh
python3 editorial/test_compose_category.py > /tmp/t0087.log 2>&1 || { tail -5 /tmp/t0087.log; exit 1; }
grep -q "^ok   a rejected automatic category does not crash the pairing step" /tmp/t0087.log
```

Verified 2026-10-15 in production (run 38774404501): "Robots in Public" was rejected, the log reads "the
story keeps its row 'family'", 7 pairings were written, and the digest logged "7 of 7 stories cross-link to
Backstory today". ntknews.org/digest/data/backstory.json carries the seven stories of the 2026-10-15 edition.
