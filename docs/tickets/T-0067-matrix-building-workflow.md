---
id: T-0067
title: How the Object Matrix grows today, and where that work was left
status: VERIFIED
tags: [backstory, decision]
anchor: editorial/NTK_Backstory_Object_Matrix.xlsx
---

## What

A record of the 2026-10-01 and 02 session that took the matrix from 345 objects
with no links to 384 objects with 339 links, so the next session does not have
to rediscover how. Measured 2026-10-02.

**The flow, as built**

1. **Candidates sheet**, `editorial/NTK_Backstory_Candidates.xlsx`: the matrix's
   14 columns plus Status, Source URL, Why it's here, Approve and Notes.
   Research goes here, never straight into the matrix. The editor marks Approve
   (Y or N) and writes notes; approved rows are copied into the `Objects` sheet of
   `NTK_Backstory_Object_Matrix.xlsx` and deleted from the sheet. 19 candidates
   are still unapproved. Lowell mill women is held: the NPS pages quote only
   Harriet Hanson Robinson's 1898 recollection, not the 1836 declaration.
2. **Matrix**, `editorial/NTK_Backstory_Object_Matrix.xlsx`, sheet `Objects`:
   384 objects sorted by Sort Date. Column O, "Source URL", holds the link a
   reader leaves NTK for. Nothing is hosted on NTK.
3. **Link backfill.** `editorial/backfill_links.py` links Supreme Court cases
   (Oyez, matched on the citation in Oyez's own term lists, with a Library of
   Congress PDF when Oyez has no match) and statutes (govinfo, with the
   public-law number found in the PDF) and writes
   `editorial/object-links-report.json`. Everything else (Hofstadter items,
   Presidential papers, letters, speeches) went to parallel research agents,
   36 and then 11 objects at a time, writing to scratch files only.
4. **Independent checking.** Every returned link was re-fetched and its page text
   checked for the author or title words, by the lead and not by the agent that
   found it. Only `verified` links were written. `probable` links, and anything a
   script could not open, went to `editorial/NTK_Backstory_Link_Review.xlsx` for
   the editor. The editor edits it in Numbers, which saves a separate
   `.numbers` file; a script reads edits from that file with the
   `numbers-parser` package, or the editor saves a copy as xlsx.
5. **The doubt rule.** The editor's rule: where there is a doubt, a link does not
   graduate. Applied 2026-10-02 to five links (T-0065).

**State.** 339 of 384 objects are linked (88.3%). The 45 without a link are on
the review sheet's "No link yet" tab with what was tried. The matrix change
was merged 2026-10-05 (#63) and the Backstory pages that use it went live the same
day (#64, T-0069). The merge and content-check scripts
used for the research passes lived in the session's scratch directory and were
not kept. T-0068 replaces them with a real link checker.

## Why

What a future session would otherwise get wrong:

- **Hofstadter page and volume numbers cannot be used to link.** The matrix
  carries volume and page for 216 of 217 Hofstadter items, but they match a
  three-volume edition (volume 1 runs to 1776, volume 3 to 1981). The scans on
  Internet Archive are the 1958, 1969 and 1973 two-volume editions, with
  different pagination and nothing after 1957, and they are restricted lending
  copies that need a borrow and a login. Tested 2026-10-02 and ruled out. The
  numbers remain useful as a plain citation.
- **Many archives refuse scripts.** Founders Online is JavaScript-rendered, and
  loc.gov, state.gov and the Marshall Foundation return 403. A page that cannot
  be fetched is `probable`, not dead. A link checker must treat "blocks scripts"
  as its own status.
- **Research agents hit a cap of 200 web searches per session.** It silently
  turned later objects into "not found". Slices of about 11 stayed inside it, and
  the second pass still found only 20 of 87.
- **Rejected as sources:** Wikipedia, retail and book-listing pages, flashcard
  and homework sites, unz.com (editor's call), Internet Archive lending copies,
  and lookalike domains (a search returned a copycat of Oyez). Project Gutenberg
  links use the read-online form, `/cache/epub/N/pgN-images.html`. Oyez is
  preferred over Justia and Wikipedia where both carry a case.
- **A name match is not an identity.** "Brown v. Board" matched Brown II until an
  audit of the matches caught it. Check every fuzzy match against the citation.
- **Direction of travel.** The editor intends this candidates-to-matrix
  graduation to become a proper database eventually (T-0066). Keep a staging
  area the editor approves from when that happens.
- **A rebuild changes the live site.** `build_backstory.py` is not run in CI, but
  its `pick()` takes the two earliest pre-1981 objects per row, so a rebuild now
  swaps Wheatley and Abigail Adams into Equality and Red Jacket into Faith. See
  T-0062 before anyone rebuilds.

## Check

```sh
set -e
test -f editorial/backfill_links.py
python3 - <<'PY'
import openpyxl
ws = openpyxl.load_workbook("editorial/NTK_Backstory_Object_Matrix.xlsx", read_only=True)["Objects"]
header = next(ws.iter_rows(max_row=1, values_only=True))
assert len(header) > 14 and header[14] == "Source URL", header
PY
```
