# Proposal: retrieve Backstory objects by the story, not by a label

**Status: proposed 2026-10-15, from a conversation with the editor. Nothing here is built.**
Numbers measured that day on `main` from `editorial/NTK_Backstory_Object_Matrix.xlsx` and
`ntk-pulse/data/backstory-pool.json`.

## The problem

The editor's sense: the Object Matrix is underused. 384 primary documents, 334 with a verified link, and
the pages that reach readers draw on a small part of them. The cause is how an object reaches a story.
Today a story is paired to a *label* (an NTK Row, a sub-genre, or a lens) and the page draws whatever
objects carry that label. Each of the matrix's three labels is the wrong zoom for many stories.

| Column | Distinct values | Distribution | Why it misses |
|---|---|---|---|
| **E, Issue (Theme)** | 22 | median 12 objects; three "Contemporary Challenges" themes hold 205 of 384 (53%) | Themes are textbook eras (Hofstadter's structure). They say *when*, not *what*, so a pairing through them feels distant. |
| **K, NTK Row** | 14 | median 13; Equality alone holds 98 | Too broad to point at one story. Any Equality story could get any of 98 documents. |
| **L, Sub-genre** | 48 | median 4; smallest 1 | Too narrow and too thin. A sub-genre with four objects cannot fill a page, and a story rarely names its sub-genre. |

(The editor's working names were J, K, E. In the file, J is Source, K is NTK Row, L is Sub-genre.)

No better label fixes this, because the problem is pairing *through* a label at all. The proposal is to
skip it: retrieve objects with the story's own words, and let the editor curate the result.

## The workflow the editor described

1. The editor curates the day's stories in Pulse, as now.
2. For each story, the editor types a few **keywords** into a Backstory field.
3. Pulse retrieves matching objects from the matrix (and the approved candidates).
4. The editor **removes** what does not belong and **revises** what is kept (line, About text, source).
5. For anything the matrix lacks, the editor asks for a **web search** for a specific item, as Pulse already
   does on prod (FIND SOURCES and the FOUND BY SEARCH tray, T-0085).

## What already exists

- **The whole pool is already in Pulse.** `backstory-pool.json`: 334 matrix objects and 96 candidates, each with
  title, author, year, row, sub-genre, lenses, note, About text where written, link status.
- **A pool search exists**: "+ Add an object" in a category, a plain substring match over title, author,
  year, lens and sub-genre. One phrase, no ranking.
- **Web search for named items exists**: FIND SOURCES, one search per line, candidates to a tray (T-0085).
- **The Lineup is on the Backstory tab** in Lineup order with each story's category (T-0090), which is where
  a per-story keyword field would sit.
- **Editing an object's source and text exists**: "edit source", Beginning line, About text.

## What is missing

- **Theme (column E) is not in the pool export.** `editorial/export_for_pulse.py` would add it.
- **Ranked, multi-keyword retrieval across every column**: title, author, theme, row, sub-genre, About, note.
  A simple scored match (keyword hits weighted by field, title and About highest) needs no model and costs
  nothing per search. A model re-rank is a possible later step, only if plain matching proves too blunt.
- **A per-story keyword field** and a results list the editor can trim, that feeds the story's category.

## Where to stress-test it

Not on prod, and not on staging either: staging Pulse (`maxzimbert.github.io/ntknews-staging`) shares an
origin, and so browser storage, with the real Pulse (`maxzimbert.github.io/ntknews`). Drafts made on
staging land in the real Pulse's drafts.

The safe place is **a local Pulse** on the editor's Mac, served from a lab branch (`scripts/preview.js`):
its own storage, Publish disabled on any host but the live one (T-0051), no way to touch prod or staging.
Open it in a normal browser; the Claude app's browser pane does not show `prompt()` dialogs, which several
Pulse buttons use.

## The Row index tab

The matrix's second tab, **Row index**, lists the 14 NTK Rows with object counts, Hofstadter vs extension,
earliest and latest year. Its numbers are typed in, not formulas. Proposed: add two tables below it,
**totals by Theme** (22) and **by Sub-genre** (48), each with object count, linked count, earliest and
latest year, written as formulas over the Objects tab so they stay current when the matrix changes. This
shows at a glance where the matrix is thick and where it is thin, which is what retrieval will expose.

## Related, already agreed

**Build out the live-conflict pages.** The seven fire rows (Gaza, Ukraine-Russia, Israel-Hezbollah,
US-Israel-Iran, US-Canada trade, Venezuela, Sudan) have 0 Beginnings and 0 objects; their page shows only
the elapsed time. The pool already holds the material for five of them, dated before each conflict began:

- **Russia**: Budapest Memorandum (1994), NATO-Russia Founding Act (1997), Putin's Munich speech (2007),
  his Crimea address (2014).
- **Israel**: UNSC 242 (1967), Camp David address (1978), the Hamas covenant (1988), Oslo (1993).
- **Lebanon**: Taif (1989), UNSC 1559 (2004), 1701 (2006).
- **Iran**: Algiers Accords (1981), UNSC 598 (1987), JCPOA (2015), the 2018 memorandum.
- **Canada**: Constitution Act (1982), the FTA (1988), USMCA (2018), the 2025 tariff order.

None of these objects has a Beginning line or About text yet: one model call per row, once, a few cents,
marked unverified for the editor. Sudan and Venezuela have nothing in the pool and need a research pass
through the candidates workbook. This is selection by lens, which is a label, but a lens names a country,
which is the right zoom for a conflict.

## Cost

Retrieval as proposed costs nothing per search. Model calls happen only when the editor asks for a web
search or for text to be written, and text for an object is written once. For comparison, the expensive
path today is an automatic category composed at publish (several Sonnet calls with web search each), which
filing every story under a category in Pulse avoids.

Considered and advised against (2026-10-15): moving these steps to a cheaper model such as DeepSeek.
The cost is mostly *when* the model runs, not its price; the research steps depend on a built-in web search
DeepSeek's API does not offer; and DeepSeek models are known to soften China-sensitive subjects, which
Backstory covers (a Taiwan row, a China lens).

## Open questions for the editor

1. Do keywords replace filing a story under a category, or sit beside it (keywords pick the objects, the
   category names the page)?
2. Should retrieved objects ever publish without the editor touching them, or only after a trim?
3. Are candidates (96, not yet in the matrix) searched by default, or only on request?
4. Does a keyword-built page become a standing category the next story can join (T-0089), or stay one
   story's page?
