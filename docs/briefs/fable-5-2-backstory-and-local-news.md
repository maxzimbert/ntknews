# Brief for Fable 5.2: Backstory production and editing, and local news on /today

Written 2026-11-10 for a fresh session. Read `CLAUDE.md` first; it wins over this file where they differ.
The editor is Max Zimbert. He wants pushback, plain cost tradeoffs, and small ships over plans.

Two jobs, in this order of value:

1. **Backstory**: make production and editing better. Propose, try on real stories, show evidence.
2. **Local news on /today**: it is mediocre at best. The causes are diagnosed below; fix them.

---

## Part 1. Backstory

### What it is

Backstory is the history that shows how the digest's news came to be the news. Each story in the digest
gets its own Backstory page: an "It starts in" year, dated milestones (Beginnings) defended by primary
documents (Objects), a trend line, and "We are here". It is written for an AP-level reader (/today is
middle-school register, /digest high school). The full contract is at the top of `docs/backstory.md`:
ten components, each scoped from the story's headline, description and Truths, each proposed by the
system and reviewed by the editor (accept by default, revise by prompt, or remove).

### The frame: a misfit is one of two problems

Recorded in `docs/decisions.md` (2026-10-28), after composing two stories by hand:

> A Backstory that does not fit the news is either **scoped wrong** or **missing material**.

- **Wrong scope.** The library has the history, but the page asked the wrong question. The example: the
  ballroom-donors story was filed under a category holding three gift-law objects. Widening the scope to
  *private money and the presidency* found four or five verified objects already in the matrix (the
  emoluments clause, Citizens United). Nothing needed to be researched; the question needed to be widened.
- **Missing material.** No scope can fix it because the library does not hold the history. The example:
  Israel's 2026 election was filed under Power and opened in 1764 Virginia. The library held one Israel
  document (Camp David), so no composition could fit.

The two have different fixes, and mixing them up wastes money:

- *Scope* is fixed per story, from the shared library, **with no web search** (T-0110).
- *Material* is researched **only when the library is thin** for the story's subject, and every find joins
  the shared library so no subject is searched twice (T-0111). Searches are budgeted and counted. The
  editor's constraint: do not pay for the same web searches over and over.

Diagnosing which problem a weak page has, before spending anything, is the core skill this system needs.

### How we got here: what was tried, and what happened

Rough chronology. The reasoning for each step is in `docs/decisions.md`; search it for the date.

| When | What was tried | What happened |
|---|---|---|
| Sept | **Fixed rows.** 21 hand-written rows; each digest story paired to one by a classifier. Each row carried one origin year and one narrative. | The narratives were never written (T-0003). Two stories on one row produced identical cards (T-0011). A story's real subject (an AI company, Russia, a county lawsuit) did not fit a fixed row, so "It starts in" leapt centuries (T-0074). |
| 10-02 to 10-05 | **The Object Matrix** (`editorial/NTK_Backstory_Object_Matrix.xlsx`): primary documents only, link-checked, and Beginnings chosen by rule rather than by hand. | It works as a library, but it is American, pre-1981, and thin on tech, elections and foreign subjects (T-0060). The rule-based picks are adequate, not curated. |
| 10-06 | **The story's own subject.** Origins retrieved per story, provisional categories when no row fits, lenses (tech, countries) for Beginnings. | Better fit, but the lenses were thin and the vocabulary multiplied: row, stratum, lens, spine, thread. |
| 10-09 | Automatic categories need two surviving objects. Tried and reverted the same day: dating by event year, a "comparable case elsewhere" relation, not cutting Beginnings at the origin. | Each live run gave thinner pages, and one run each could not separate the change from run-to-run variance. **Lesson: compare several runs, not one.** |
| 10-12 | **One vocabulary**: category, Beginnings, objects, trend line, subjects. Research a category once instead of once per story (the spine lab). | It stuck, and the words are still used. |
| 10-13 | News reports may carry an object when no primary source exists, always labelled. | It stuck, and was widened on 11-02. |
| 10-28 | **The two-problem frame.** Compose per story; research once, into a shared library. | This drove T-0109, T-0110 and T-0111. |
| 10-28 to 10-30 | **A draft before publish** (T-0109): GitHub builds a first draft and Pulse edits it. **A chart per story** (T-0112). | T-0109 was discarded, replaced by building in the browser. T-0112 was built, used once, and parked: its one-page check refused most real series. |
| 10-30 | **The editor types the row** (T-0113). The row shelves the story; it never scopes it. | The direction stuck; the ticket was folded into T-0114. |
| 11-02 | **The contract** (T-0114). Day counters retired everywhere. News from the 91 approved publishers may join the matrix, marked as news. | Live since 11-09. |
| 11-02 | **When the editor directs, the editor's words win.** Guardrails apply only to unsupervised output. | This came from the first test of the review screen: "the guard rails are there to help you when I'm not able to supervise or direct you." Do not re-tighten it. |
| 11-04 | **The editor's Are.na library** (T-0115): 3,096 dated items, ranked after primary documents and before web search, with no reader label. **A thin build searches once on its own**: fewer than 4 milestones means one web search and one rebuild. Subjects searched in the last 30 days are not searched again. | Live since 11-09. |
| 11-09 | **"It starts in" is the proximate cause** (T-0074, #111), not where the history begins. | Live. |

### Where it stands (2026-11-10)

- **Live:** T-0114 (built and reviewed in Pulse, shipped as built) and T-0115 (Are.na). Both pass their
  checks but are not yet promoted to VERIFIED.
- **The editor's loop** (`docs/decisions.md`, "The editor's loop, as built"), in order of reach:
  1. *Direct the research* (the main tool): the editor names what the history should reach.
  2. *Revise* a part by prompt.
  3. *Edit words* directly.
- **Open:**
  - T-0110: compose per story from the shared library, with editing section by section.
  - T-0111: research only when thin, with every find joining the library.
  - T-0086: several objects per milestone.
  - T-0112: per-story visualization, parked.
  - T-0060: the matrix has almost no women or minority voices before 1981.
- **Where the code is:**
  - The build and review happen in the browser: `ntk-pulse/pulse.html`, about 1,400 lines changed by #107.
  - Publish ships what was reviewed: `editorial/backstory_draft.py`.
  - Matrix additions: `editorial/graduate_finds.py`.
  - Are.na: `editorial/arena_pull.py`, `export_library.py` and `arena_search.py`.
  - Start with `docs/architecture.md`, section "Backstory: build, review, publish".

### What to work on

The editor wants Backstory to be **better to produce and quicker to edit**. Ideas worth testing (not
decisions):

- **Diagnose before spending.** When a build comes back weak, does the system say *which* problem it is
  (wrong scope, or missing material) and pick the cheaper fix? Today a thin build searches the web, even
  when a wider scope over the library would have done.
- **The scope question itself.** How does a build turn headline, description and Truths into the question
  the history answers? The ballroom case shows the first scope is often too narrow. Can the system propose
  two or three scopes and let the editor pick one, instead of making the editor write *Direct the research*
  from scratch?
- **Editing effort.** Count how many editor actions a page needs before it ships, on the last week's stories.
  That is the metric to move.
- **Run-to-run variance.** Judge a change by several builds of the same story, not one (the 10-09 lesson).

### Rules that bind this work

- **A matrix link is a primary source.** No Wikipedia, retail pages or lending copies. News is allowed only
  from the 91 publishers in `NTK_SOURCES` (`netlify/functions/news.js`), and only when no primary source
  exists. A link counts as verified only once the page has been fetched and read (CLAUDE.md rule 8). The
  `backstory-source-researcher` agent does this.
- Generated text stays `verified: false` until the editor checks it.
- **Decided; do not re-decide:**
  - No category page for readers.
  - Day counters are retired.
  - The editor's words win over guardrails.
  - Library items never join the matrix.
- **Cost matters.** Name the API and search spend of any proposal per story per day.
- **Two Pulses, one origin.** Staging Pulse (`maxzimbert.github.io/ntknews-staging/`) and prod Pulse share
  one browser `localStorage`. Staging cannot publish. Never test against `ntknews.org`'s copy of Pulse.

---

## Part 2. Local news on /today

### What the editor sees

On 2026-11-10, the "Near Los Angeles" block on /today showed one story, from Oct 20, from a sketchy site.

### How it works

`digest/index.html` (search `fetchLocalAndWeather`) works in four steps:

1. Geolocate the reader.
2. Reverse-geocode to a city (BigDataCloud).
3. Resolve the city to an EventRegistry location: `news.js?mode=resolve-location`.
4. Make two calls to `news.js?mode=local-news`: one for outlets based there (`filterBy=source`) and one
   for articles about there (`filterBy=event`). The client merges them and filters out classifieds by
   title dedup and by URL path.

There is no editorial pass and no model call, and results are cached once a day per browser.

### Diagnosis (run against production on 2026-11-10)

Four separate bugs, each verified by calling the live function:

1. **The wrong place.** `resolve-location` for "Los Angeles" returns *Los Angeles County* first, and the
   client takes `[0]`. With the county URI:
   - outlets based there: **0 results**;
   - articles about there: **7 of 8 are clasificados.laopinion.com transit ads**, plus one
     legalinsurrection.com piece from Oct 21.
2. **The date window is ignored.** `local-news` sends `forceMaxDataTimeWindow: 2`. EventRegistry accepts
   only 7 or 31 for that parameter (check the API docs to confirm), so the window is not applied, and
   results go back three weeks. Use `dateStart` instead.
3. **The classifieds filter misses.** The ads are on a *subdomain* (`clasificados.laopinion.com`), but
   `LOCAL_NONNEWS_PATH` matches only the URL *path*. Title dedup collapses them to one, which still shows.
4. **There is no quality bar.** With the correct city URI (`Los_Angeles`), freshness is fine, but:
   - outlets based there return Hollywood trade press and Breitbart on national stories;
   - articles about there mix real local reporting (LAist, Spectrum News 1, the CBS and ABC locals) with
     Times of India weather pages and sports wire.

   Nothing ranks or filters by outlet.

### What a fix probably involves

These are directions to check, not decisions:

- Pick the location that matches the city itself, not the county or a neighbourhood. Match against the
  geocoded city and state.
- Apply a real date window: today and yesterday, through `dateStart`.
- Filter classifieds and directories by host as well as path.
- **A quality bar.** Options include EventRegistry's source-rank filter, a per-metro allowlist of real
  local outlets (public radio, metro dailies, TV affiliates, nonprofit newsrooms such as LAist or
  CalMatters), and requiring that the article is about the place, not only published from it.
- **Fewer is better.** Show nothing rather than junk, which is the product's closure promise. Three
  good headlines beat five.
- Count the NewsAPI cost: today it is three calls per reader per day. Do not add a per-visitor model call
  without a go-ahead (the reasoning is in the code comment above `LOCAL_KEY`).

### How to know it worked

- Run the same city queries before and after the fix, for at least Los Angeles plus two smaller US cities.
- Show the editor the actual headlines and sources.
- Then write a ticket whose check fails if classifieds or stale items come back.

The work is on `digest/index.html` and `netlify/functions/news.js`, so a Netlify deploy preview can show it
(unlike Pulse).

---

## Where the history lives

This file is a summary. The record is:

- `docs/decisions.md`, especially every entry from 2026-10-02 on;
- `docs/backstory.md`;
- `docs/tickets/T-0110` through `T-0115`;
- `docs/log.md`.

Archived Claude sessions that did the Backstory work, by title:
- Bones for Backstory
- Content for Backstory Beginnings and Objects
- Backstory composition on Pulse prod
- Object matrix retrieval
- Are.na content database with web search
- Pre-publish backstory work in Pulse (still open, and the longest)

They are working transcripts. Where they disagree with `docs/decisions.md`, the decisions file wins.
