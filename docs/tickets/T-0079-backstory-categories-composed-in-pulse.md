---
id: T-0079
title: Backstory categories are composed, reviewed, revised and saved inside Pulse, and the Lineup publish carries them
status: BUILT
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-07 after two days of one-off fixes. The bones of Backstory are in place
(categories, a chart of progress or regression, Beginnings, Objects) and the system around them is not:
a category can only be added by editing files, and Pulse cannot create one, review what was written,
send revisions, or save hand edits. The goal, in the editor's words: in Pulse, set a category for a
story; when a category is new, the system composes its text, Beginnings and Objects from the Lens list
and the Matrix; the editor reads it, sends revisions, edits by hand, and saves it on the Backstory tab;
the Lineup publish button then sends the whole package. Work in one Pulse tab must be recognised in the
others. This replaces the "no row fits" button.

Measured 2026-10-07 on main (92cba51):

- Pulse carries one per-story field for this, `backstory_category` (a name), and one button, "no row fits"
  (2 occurrences in `ntk-pulse/pulse.html`). There is no category record in the publish payload
  (`backstory_categories`: 0 occurrences), no way to see or edit a category's text in Pulse, and the
  Backstory tab's own list is the legacy localStorage array that drives nothing.
- The one editor-made category, AI (`p-ai`), was composed by hand by an agent, not by the system. Its
  five Beginnings: three come from the China lens (Taiwan Relations Act 1979, PNTR 2000, Anti-Secession
  Law 2005) and two from the tech lens (Telecommunications Act 1996, PATRIOT Act 2001). The story filed
  under it (Altman) mentions China, Chinese or Taiwan 0 times across its four sections. The China lens
  was applied because the editor's framing of the stakes mentioned China, and the tech lens had only two
  linked matrix objects, so the pool was padded to reach the three-object minimum.
- Tech has 2 linked objects in the matrix and 10 candidates in `NTK_Backstory_Candidates.xlsx`
  (tab "Lens candidates"), none yet approved.
- The editor's complaint about the AI page: the intro sentences are janky and cumbersome, and the
  Beginnings are China and Taiwan centric when the digest story never touches them.

## Why

The product's claim is that the reader can see how today's news sits inside a longer story. That claim
fails visibly when the Beginnings belong to a different story than the one on the card, and a reader
who notices that stops trusting every other card. It also cannot be fixed one page at a time: two days
were spent adjusting a single page and its pairing examples, and the editor named the cost (time in
back-and-forth, focus split between examples and the system).

Decided 2026-10-07, by default, for the editor to overturn:

- **Compose in Pulse, using the key already in the editor's browser.** Pulse already calls the model
  there for Today generation. It is instant, needs no new secret, and is the first place the real model
  runs on these prompts (nothing has run against the real API so far; every model step to date was
  written by hand). Ruled out: composing in a GitHub Action triggered from Pulse. It needs a token with
  `actions:write` (Pulse's token is scoped to `contents:write` on purpose), adds a minute or two to every
  revision, and puts a commit in history per revision.
- **A category is one self-contained record**: name, contest, stakes, indicator, lenses, Beginnings,
  objects, status (draft or approved), and the revision requests that produced it. It is carried in
  `lineup-publish.json`, so a click of the existing Publish button sends it. The repo, not the browser,
  is the source of truth: Pulse loads published categories from `backstory.json` and keeps unpublished
  drafts in localStorage until published.
- **Pulse composes and checks; CI checks again and is authoritative.** The Python validators run in the
  publish workflow and drop whatever fails, never inventing a replacement. This duplicates the validators
  in two languages. That cost is accepted because the alternative is trusting browser-side output.
- **The lens comes from what the story is about, and the editor can change it.** A lens is applied only
  when the story's own text supports it. A thin lens shows fewer Beginnings and a visible gap in Pulse,
  never padding from an unrelated lens.
- **Candidates are an approve-in-place pool.** Each object shows its link status and an approve toggle;
  composing a category is also reviewing candidates. An object publishes only if it is approved or already
  in the matrix. Graduating candidates into the matrix workbook stays a separate editorial step.
- **Kept as they were:** the 30-day archive rule for editor-made categories, and promotion to a real
  row being the editor's decision (`docs/decisions.md`, "Backstory is built from the story's own
  subject"). This ticket supersedes the provisional-row drafting in `editorial/build_pairings.py`,
  which was model-drafted in CI and never ran against the real API.

Slices, each shipped to staging before the next: (1) data layer: matrix and candidates exported for
Pulse, the category schema, the CI merge and validators; (2) Pulse category panel and compose;
(3) revise and manual edit; (4) publish wiring and the Lineup tab integration (a category dropdown fed by
the shared list); (5) remove "no row fits". The AI page is regenerated by the system as its first test,
not edited by hand.

## Built 2026-10-07 (PR on T-0079-pulse-categories)

All five slices are in one branch. Data layer: `editorial/export_for_pulse.py` writes
`ntk-pulse/data/backstory-pool.json` (334 linked matrix objects and 96 candidates, each with the lenses
it belongs to); `editorial/categories.py` validates a category record; `build_pairings.py` merges the
`backstory_categories` Pulse sends. (Superseded 2026-10-09: step 5C now composes categories with a model; see below.) Pulse: the Backstory tab
is now a category editor (compose, revise, edit, approve, preview); Lineup's row dropdown lists
categories and "+ new category" replaces "no row fits"; Publish carries approved categories. The trend
line needs what is tracked, values, a source with a link, a date and the editor's check, or it is not
drawn. Tested: 15 fixture cases in Python and the same cases in node against the Pulse code; the Pulse
flow (file a story, compose, approve candidates, revise, edit, approve, payload) in a browser with a
stand-in for the model; and the exact payload that flow produced through the CI merge.

Not tested at the time: the real model had not run these prompts. (It has since; see below.)
The AI category on staging still carries the old China-lens Beginnings until it is recomposed and
published, which is why the check below stays OPEN.

## Hybrid, built 2026-10-09 (PR #78)

The editor found the Pulse-first flow too much work and liked the pairing step's output, so categories are
now composed in the publish pipeline and Pulse is the review layer. Step 5C of `build_pairings.py` takes the
stories the classifier flags as misfits (poor fit or confidence under 0.70, at most 3, never editor-filed) and
calls `editorial/compose_category.py`: the model writes the contest, stakes, lenses and sub-genres; chooses
up to 6 objects from the pool (matrix first; choosing none is allowed); searches the web for a chronology of
milestones with primary sources (always, when the pool gives fewer than six); an independent judge call then
keeps only objects that read as part of the story's own history; a trend line is searched for and verified.
Everything is checked again by `categories.py` and `live_checks`. Rules: a category with no objects is never
published (any author); an automatic one needs two; the story keeps its row. Found items carry `ties_to` (a
phrase made of the story's own words), `relation` and `because`, shown in Pulse next to the judge's reason.
Backstory is written for an AP-level reader.

What the real runs showed (Sonnet 5.5, same six stories, runs 37976901200 to 37983677004):

- The credit balance was empty for the first run, which failed every call with HTTP 400 and still showed
  green. The earlier bare 400s were probably the same cause.
- The judge works: it dropped Dartmouth 1955, EO 14110 and EO 14179 under an AI-in-medicine and an Altman
  story, a 2022 import order under fuel prices, and Ebola under a Siberian lab death, each with a reason.
- The checks remove real finds: a repaired line that gains a number the quote lacks, a quote not found on
  the page, a `ties_to` that does not match. Yield swung from 4 and 5 Beginnings (Biosecurity, Fuel Prices) to
  3 and 3 with no AI category, on the same stories. One run each; the revert is not proven to be the cause.
- Classifier misfit flags vary run to run (diesel flagged in some runs only).
- The origin step deleted Beginnings dated in the origin year, which emptied two pages; it now drops only
  those dated after it. A category with zero objects was created once; now it is not.

Tried and reverted 2026-10-09 (commit 11205de, reverted in f5eba6c): dating a milestone by its event year
(kept the document's date apart), a fourth relation "comparable case of the same kind of event" so that an
outbreak elsewhere counts under an outbreak story, and not cutting Beginnings by the origin. The editor's
position stands: a milestone is dated by the event (Sverdlovsk is 1979, though the source is a 1994 paper),
and a category is the history of a theme, so comparable cases before or after one story's origin are fine.
Not yet in the code. Try again after several runs on the same stories show the spread.

Open: event-year dating; comparable cases; retrying one rejected item with its reason (number or quote
failures) the way line length already is; trend lines were found for AI topics but not for Biosecurity or
Fuel Prices; per-story origin override in Pulse; the 96 lens candidates await the editor's Approve column.
The check below stays OPEN until the AI category is recomposed and published without the China lens.

## Check

The check fails until the AI category's lenses are supported by its story, and holds the system's
rules: tests pass, the pool is not stale against the workbooks, the payload carries categories, and
"no row fits" is gone.

```sh
python3 editorial/test_categories.py >/dev/null || { echo "OPEN: the Python category tests fail"; exit 1; }
node scripts/test_pulse_categories.js >/dev/null || { echo "OPEN: the Pulse category tests fail"; exit 1; }
python3 - <<'PY'
import hashlib, json, re, sys
bad = []
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
pool = json.load(open("ntk-pulse/data/backstory-pool.json"))
for key, path in (("matrix_sha256", "editorial/NTK_Backstory_Object_Matrix.xlsx"),
                  ("candidates_sha256", "editorial/NTK_Backstory_Candidates.xlsx"),
                  ("notes_sha256", "editorial/object-notes.json"),
                  ("lenses_sha256", "editorial/lenses.json")):
    if pool.get(key) != sha(path):
        bad.append(f"the pool is stale against {path}; run python3 editorial/export_for_pulse.py")
src = open("ntk-pulse/pulse.html").read()
if "backstory_categories" not in src:
    bad.append("the publish payload does not carry backstory_categories")
if "no row fits" in src:
    bad.append('Pulse still has the "no row fits" button')
bs = json.load(open("digest/data/backstory.json"))
lp = json.load(open("ntk-pulse/data/lineup-publish.json"))
terms = {
    "china": r"\b(China|Chinese|Taiwan|Beijing|Taipei)\b",
    "russia": r"\b(Russia|Russian|Moscow|Kremlin|Putin|Soviet)\b",
    "tech": r"\b(AI|artificial intelligence|chatbot|software|algorithm|internet|online platform|data cent(er|re)s?)\b",
}
store = {r["id"]: r for r in json.load(open("ntk-pulse/data/provisional-rows.json"))["rows"]}
strip = lambda h: re.sub(r"<[^>]+>", " ", h or "")
stories = {s["key"]: " ".join(strip(s.get(k)) for k in ("truth", "prob", "poss", "lies")) for s in lp["stories"]}
for p in bs.get("todays_pairings", []):
    cat = store.get(p["row"])
    if not cat or p["story_id"] not in stories:
        continue
    for lens in cat.get("lenses", []):
        if lens in terms and not re.search(terms[lens], stories[p["story_id"]]):
            bad.append(f"{cat['id']}: lens '{lens}' has no support in the story filed under it ({p['story_id']})")
if bad:
    sys.exit("OPEN: %d problems, e.g. %s" % (len(bad), bad[0]))
PY
```
