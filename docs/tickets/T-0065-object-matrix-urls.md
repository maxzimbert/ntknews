---
id: T-0065
title: Almost no matrix object has a link to its primary source, and nothing can be shown without one
status: DECIDED
tags: [backstory, feature]
anchor: editorial/NTK_Backstory_Object_Matrix.xlsx
---

## What

Measured 2026-10-02 on `editorial/NTK_Backstory_Object_Matrix.xlsx`, sheet
`Objects`: 384 objects, 39 with a value in column O ("Source URL", added the
same day for the rows T-0060 added). By what the `Source` column cites:
203 Hofstadter anthology items (0 linked), 75 other (34 linked), 57 Supreme
Court cases cited by volume and page (3 linked), 30 statutes (2 linked), 19
Presidential papers (0 linked). Of the 39 links, 0 are on a retail, wiki or
Q&A host.

Decided 2026-10-02 with the editor: nothing is hosted on NTK, so a tap on an
object leaves NTK for the original. That makes the link the content. An object
without a verified link cannot be shown, which makes this the gating work for
the rules-based Backstory (T-0062) and the object page (T-0048).

Plan, in tiers, so coverage can be reported before anything is built on it:

1. Cases and statutes cited by citation: derive the link from the citation by
   script, then fetch each and confirm the page names the right case or act.
2. Presidential papers: look each up on a primary host.
3. Hofstadter items and "other": search and fetch, row by row, Equality and
   Work first.
4. A link checker that records last-checked and status in a generated file
   beside the matrix, and an eligibility rule: an object with no live link is
   not shown.

## Why

Hosting was the alternative. It was ruled out by the editor: the matrix mixes
public-domain texts with in-copyright ones (Crenshaw, Coates, Alexander,
Krugman, Anton), and one rule for all objects is simpler and safer than a split.
The cost accepted: a reader lands on someone else's page with no framing from
NTK, so the row's stakes paragraph and the story's pairing line carry that job.

What counts as a primary source: the document itself or a library, archive,
court or government record of it (Library of Congress, National Archives,
govinfo, Oyez, Founders Online, a court's own site), or a reputable
publication's own copy. Not accepted: Wikipedia, retail pages (Amazon,
AbeBooks, eBay), flashcard and homework sites. A retail page was already
rejected once, 2026-10-02, when it stood in for a book. The 2026-10-01
T-0060 session also found Justia and Oyez differ in how readable they are for
the intended reader; prefer Oyez over Justia where both carry a case, and
Oyez does not carry every case (it has no `Cherokee Nation v. Georgia`, which
links to the Library of Congress scan instead).

Paywalled hosts (The Atlantic, Harper's, The New York Times) will appear. The
link checker should record a paywall as its own status, not a dead link.

## Check

```sh
python3 - <<'PY'
import openpyxl, sys
ws = openpyxl.load_workbook("editorial/NTK_Backstory_Object_Matrix.xlsx", read_only=True)["Objects"]
rows = list(ws.iter_rows(values_only=True))
h = rows[0]; data = rows[1:]
u = h.index("Source URL") if "Source URL" in h else None
urls = [r[u] for r in data if u is not None and r[u]]
deny = ("wikipedia.org", "amazon.", "abebooks.", "ebay.", "goodreads.",
        "scribd.", "studocu.", "coursehero.", "quizlet.")
bad = [x for x in urls if any(d in x for d in deny)]
if bad:
    print(f"{len(bad)} links on a retail or wiki host, e.g. {bad[0]}"); sys.exit(1)
pct = 100 * len(urls) / len(data)
if pct < 90:
    print(f"{len(urls)} of {len(data)} objects have a link ({pct:.0f}%), target 90%"); sys.exit(1)
PY
```
