---
id: T-0119
title: A Backstory document's link and quote are checked before publish, its note is written from the document, and staging never marks one for the Object Matrix
status: DECIDED
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html:4967
---

## What

Scoped with the editor 2026-11-10. The full scope is `docs/briefs/opus-5-5-backstory-second-brain.md`, Part C.

Measured 2026-11-10:

- `editorial/object-links-health.json` was last written 2026-10-05. Of the documents on the seven pages
  published at commit `845a14fb`, almost none are in it: research finds and library items are never
  link-checked.
- A research find is accepted when its URL is one the search returned and it carries a quote
  (`verifyMilestone`, `ntk-pulse/pulse.html:1641`). The quote is never compared with the page.
- That edition shipped two x.com posts, one Bloomberg article behind a paywall, and a Justia copy of a court
  opinion as documents.
- Two document notes on the billionaire-tax page are filler. The composer is given a matrix object's title,
  author and date, and is told to use only those facts (`BSX_RULES.about`), so it has nothing to say.
- The Object Matrix has never received a document from Pulse: `editorial/matrix-additions.json` has 0
  handled, and `editorial/research-ledger.json` has 12 finds with 0 approved.
- The matrix is written only by `graduate_finds.py` in `pulse-publish.yml`, which runs on `main`. Staging
  cannot reach it directly. But `bsxApprove` writes `approved_by: "editor"` into the ledger on whichever
  branch Pulse is served from, and a merge could carry that mark to `main`.

Wanted:

1. When the draft is saved, a GitHub workflow fetches every document on the draft's pages, confirms the link
   loads and that the recorded quote appears on the page, and writes the result beside the draft on the same
   branch. Pulse shows a failure as a flag on the document. A page that cannot be read is "not checked",
   never passed.
2. A document with no note gets one written from the document itself, the first time it is chosen. Saved
   once, on the branch Pulse is served from, unverified until the editor ships a page carrying it.
3. In staging Pulse, approving a document adds it to the page and does not mark it for the matrix.
4. No batch of notes for the whole matrix.

## Why

A Backstory page's claim is that each milestone is defended by a document the reader can open. A link that
does not load, or a quote that is not on the page, breaks that claim in front of the reader, and nothing
catches it today (CLAUDE.md rule 8: an agent's "verified" is a claim until the page has been fetched and
read).

The check runs before publish, not during it, because publish must never fail on Backstory (T-0013) and
because a flag the editor sees in Pulse can be acted on.

Staging, the editor, 2026-11-10: "I think staging should not write into matrix. But when this moves from
staging to prod, then yeah it can write things into the matrix." The matrix is the library of record; test
approvals should not be able to reach it by any route.

Ruled out: writing notes for all 384 matrix objects at once. Generated text is unverified until the editor
has checked it (CLAUDE.md rule 9), so a batch hands the editor hundreds of items to review. The editor,
2026-11-10: "I do not want 300+ objects coming into matrix." Writing a note when a document is first chosen
puts it on a page the editor is already reviewing.

Cost: the link and quote check is free. A note is one fetch and one model call per new document, once. Which
API tool reads a page is unverified; confirm it in the documentation before building.

## Check

```sh
ls .github/workflows/ | grep -qi "backstory" || { echo "OPEN: no workflow checks the Backstory draft's documents"; exit 1; }
[ -f scripts/test_pulse_backstory.js ] || { echo "OPEN: scripts/test_pulse_backstory.js does not exist"; exit 1; }
out=$(node scripts/test_pulse_backstory.js) || { echo "OPEN: the Pulse Backstory tests fail"; exit 1; }
for want in \
  "links: a document whose link failed is flagged on the page" \
  "links: a page that could not be read is not checked, never passed" \
  "note: a document with no note is described from the document, once" \
  "staging: approving a document does not mark it for the Object Matrix"
do
  echo "$out" | grep -qF "ok   $want" || { echo "OPEN: no passing test: $want"; exit 1; }
done
python3 - <<'PY' || exit 1
import json, sys
d = json.load(open('digest/data/backstory.json'))
bad = [o.get('source_url') for p in d.get('todays_pairings', []) for o in ((p.get('composed') or {}).get('case') or [])
       if (o.get('link_check') or {}).get('status') not in ('ok', 'not checked')]
if bad:
    print('OPEN: %d published document(s) carry no passing link check, e.g. %s' % (len(bad), bad[0])); sys.exit(1)
PY
```
