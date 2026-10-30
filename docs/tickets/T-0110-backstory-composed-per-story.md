---
id: T-0110
title: Each story's Backstory is composed for that story from the shared library, and the editor can edit it section by section
status: BUILT
tags: [backstory, feature]
anchor: editorial/compose_category.py
---

## What

The scope half of the 2026-10-28 decision ("research once, compose per story", `docs/decisions.md`).
Measured on `origin/main` 2026-10-28: a story's Backstory is its category's page, shared by every story
filed there. Only the pairing line and "It starts in" are written per story (`build_pairings.py`,
`build_origins.py`). Beginnings and objects come from the category (`backstory.json` rows), so the
Israel election story showed Power's 1764 to 1974 Beginnings.

Wanted:
1. **A per-story page.** For each Lineup story, a composer picks from the whole library (the matrix,
   approved candidates and T-0111's research finds, across categories and lenses), not only its
   category's objects: "It starts in", 3 to 6 Beginnings before it, any since, and the objects. The
   category is still filed and still groups stories; it no longer fixes what the story shows.
2. **No web search in this step.** The composer reads the library and the story's Truths. When the
   library is too thin to give the story three verified Beginnings, it says so and hands the subject
   to T-0111, rather than stretching an unrelated object to fill.
3. **Section edits in Pulse.** Per section ("We are here", "It starts in", Beginnings, objects, the
   visualization of T-0112): remove an item, edit the text, or nudge with a short note (accurate,
   brief, comprehensive, or the editor's own words: "too narrow, include the 2019 to 2022 elections").
   "We are here" is one line and takes a nudge in the editor's words only. A nudge reruns that section
   only. Two
   kinds of removal, kept apart: **not for this story** sticks on that story's reruns and leaves the
   object available to other stories; **reject** is about the object itself (a bad source, a wrong
   date) and removes it everywhere, as the 2026-10-12 rule on rejections already says.
4. **One category, several paths.** Decided with the editor 2026-10-28: a category can be used by two
   stories that take it two different ways, with distinct or overlapping Beginnings and objects. A
   story about Ra'am's cabinet seat and one about the Nation-State Law can both draw on an Israel
   library and start in different years. The composed page belongs to the story; the category holds
   the library. An object's own text (`about`) is shared, since it describes the document; a
   Beginning's line may be written per story, since it says why that milestone matters here.
5. **No category page for readers** (option C of the 2026-10-28 mock, chosen by the editor). Readers
   see each story's own page; the Backstory tab lists the stories, and two in one category sit side by
   side there and show their differences when opened. A story's page does not point at the other
   stories in its category (no "also in story 1" marks, no "filed under" line). The category is a
   Pulse thing: the library, and where the editor builds it out.
6. **The draft view replaces staging Pulse's per-story Backstory editing**, and later the live one.
   Lineup down the left with a status per story, the story's sections in the middle (objects
   included), the library and research state for a thin story beside it. The reader preview is the
   real reader page drawn with the reader's own code, as T-0091 does for the card, not a separate
   layout. "Redraft changed stories" reruns the draft only for stories whose Lineup entry changed
   since the last draft, so an edit to one story does not pay for five.
7. **Tried on staging** with the two 2026-10-28 cases: the Israel election story should come out
   thin and say why (no Power Beginnings); the ballroom donors story should widen to private money and
   the presidency using the emoluments clause (matrix, Power) and the existing gift-law objects.

Runs inside T-0109's draft, so the editor sees it before publish. Today the reader's category page
(`/backstory/<row>/`) is shared by every story filed there, so a per-story page needs a URL of its own,
the cost the editor accepted 2026-10-06. Settled 2026-10-28 from the mock
(https://claude.ai/artifact/GoNGTmRiM7mHsgQyub6LAa): no category page for readers (item 5). Existing
row URLs must keep resolving (`CLAUDE.md`, rule 3); what they show once no story links to them is
decided at build.

The editor on the hand-composed ballroom donors page (1787 to 2025): "SO MUCH BETTER than what came
previously." It was put together from the matrix with no web search.

**Built 2026-10-28, on branch `T-0110-compose-per-story` (stacked on T-0109) and on staging.**
`editorial/compose_story.py` runs inside the draft, after the pairings and origins: one Haiku call names the
story's history as 8 to 14 search terms, the library is searched with them (a story's own words alone pulled
the 1918 Fourteen Points speech for an Ohio poll that moved six points), and one Sonnet call, no tools, picks
the Beginnings and later objects and writes each Beginning's line. Every line is checked (length, no dash,
banned phrases, every number traceable to the document's record); a pick that fails is dropped and listed.
Fewer than three Beginnings and the page is marked thin with what is missing. Token counts are recorded per
story and per draft (`compose_usage`), so the cost is measured, not guessed. Pulse shows the composed page
in each story's preview with: edit a line, not for this story, reject (everywhere; it also marks every story
whose page uses it), nudge per section with accurate/brief/comprehensive, and "apply edits", which reruns
only the stories with edits pending (`compose_only` in the draft lineup; nothing is chosen again).
Publish carries each story's composed page on its pairing (`todays_pairings[].composed`).
Tested: mock runs on the editor's real staging draft, a one-story rerun that removed an object and left the
other five untouched, publish shipping the rerun draft with all six pages; Pulse's controls in a local copy;
the fingerprint Pulse computes matched the one the editor's own browser computed for all six stories.
Reader side, built 2026-10-30: the app draws a pairing that carries `composed` as the story's own page at
`/backstory/s-<story id>/` (`bsrStoryRow` in `digest/index.html`), and `editorial/build_backstory_pages.py`
builds its static twin and object pages from the same shape (`story_row`; keep the two in step). The card shows
the page's scope, "It starts in" and "We are here"; the page reuses the row page, object pages and chart.
`?draft` on the app lays the branch's current draft over the published file, read-only, under a "not
published" bar, so the editor reads a draft as readers will get it (Pulse: "open in the reader app").
Checked on the editor's real staging draft: seven story pages in the app, an object page, no console errors,
and the static builder wrote all seven pages and their object pages. Not run: a real (non-mock) compose, which
needs the Anthropic key in Actions and so waits for the editor's next Draft Backstory on staging.
Open, for the editor: the library includes approved candidates (35, among them the 1948 Declaration of the
Establishment of the State of Israel and the Oslo Declaration), as `categories.validate` already does. A
comment in Pulse (2026-10-15) says candidates stay out of Backstory until they are in the matrix. Which wins?

**Moved into Pulse 2026-10-30, by the editor's call:** "I am ok to call browser from pulse. I would like to keep
github out of it." Each story's page is composed in the browser with the editor's Anthropic key (`bsxCompose`,
`bsxRun` in `ntk-pulse/pulse.html`) and saved into `backstory-draft.json` through GitHub's API; every edit,
nudge, approval and research runs there too, with no workflow run (a run took ~30 seconds, most of it GitHub).
GitHub keeps only the first draft of a Lineup (`backstory-draft.yml`: classifier, new categories, origins), which
is the code publish runs and whose link checks need a server; when it lands, Pulse composes each page.
`editorial/compose_story.py` is retired; the prompts and checks moved unchanged.

## Why

Of the two failures the editor named, one (Presidential Private Donors too narrow) is a scope error
the library could already fix: four or five verified matrix objects fit the wider subject and sat in
other categories. Composing per story fixes it without a single search, so it is the cheap half.

Ruled out: making categories finer (a category per story is the 2026-10-06 per-story pages again, with
none of the reuse) or broader (Power is already broad, and that is the Israel failure). Ruled out:
letting the composer search when it is short. That is how searches repeat; T-0111 owns search.

Unverified: the cost of the composer per story. It is a model call without tools over a pool of 443
objects, so it should be far cheaper than a research call; measure it on staging before claiming so.

## Check

```sh
python3 - <<'PY'
import json, os, sys
p = 'ntk-pulse/data/backstory-draft.json'
if not os.path.exists(p):
    print('no draft yet, so no story has a composed page'); sys.exit(1)
d = json.load(open(p))
stories = d.get('stories') or []
bad = [s.get('story_id') for s in stories if not s.get('composed') or 'beginnings' not in s['composed']]
if not stories or bad:
    print('stories without a composed per-story page:', bad or 'no stories'); sys.exit(1)
pulse = open('ntk-pulse/pulse.html', encoding='utf-8').read()
i = pulse.find('async function bsxCompose(')
src = pulse[i:pulse.find('\n}\n', i)] if i >= 0 else ''
if not src:
    print('Pulse has no story composer'); sys.exit(1)
if 'web_search' in src or 'bsxResearch' in src:
    print('the per-story composer can search the web; search belongs to T-0111'); sys.exit(1)
# Every Backstory helper Pulse calls must exist: a deleted bscReaderUrl made every composed preview throw, so the
# tab stopped drawing and its buttons did nothing (2026-10-30).
import re
defined = set(re.findall(r'(?:function\s+|(?:const|let|var)\s+)(bs[A-Za-z0-9_]*)\b', pulse))
called = set(re.findall(r'(?<![.\w\'"])(bs[A-Za-z0-9_]*)\s*\(', pulse))
missing = sorted(called - defined)
if missing:
    print('Pulse calls Backstory functions that do not exist: ' + ', '.join(missing)); sys.exit(1)
PY
```
