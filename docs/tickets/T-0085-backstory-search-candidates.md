---
id: T-0085
title: A Backstory revision that names several milestones searches every one and returns candidates (found, named-not-found, news) for the editor to pick, instead of up to three single answers
status: BUILT
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-13 after a live test in Pulse (Pages). In the category "Donald Trump's
corruption" the editor sent one revision listing eight milestones in order: Friedrich Trump's businesses,
Fred Trump and the early Trump Organization, Bonwit Teller, the Central Park Five, discrimination against
Black tenants, Trump University, Atlantic City, and running for president for leverage with NBC over The
Apprentice. Measured on main (5c29038), the system:

- searched three of the eight. `reviseCat` told the model "Up to three" and the code ran
  `(r.find||[]).slice(0,3)`. The other five were dropped before any search.
- returned one document or nothing for each. On Friedrich Trump the model found the right primary items
  (Bennett Sun ad, 9 Dec 1899; Yukon Sun letter, 17 Apr 1900; the 1892-93 Seattle directories; Yukon claim
  records) named in secondary pages, then threw them away because `proposeObject` could answer only
  "one readable document" or `{"none"}`.
- accepted "FHA Investigation Report ... from www.washingtonpost.com" as a primary source. The host check
  was a short deny list (Wikipedia, retail, homework sites), so any news page passed as primary, unlabelled.
- added objects that CI would have dropped at publish: `proposeObject` never stored an `evidence_quote`,
  and `editorial/categories.py` drops any `found_by: "search"` object without one. The Diduck v. Kaszycki
  opinion (a correct Bonwit Teller source) would not have reached a reader.

Built 2026-10-13 on `T-0085-backstory-outline-candidates`:

- the revision prompt asks for one `find` entry per topic the editor names, in order, keeping their
  specifics; up to twelve run, three searches at a time (`searchTopics`).
- each topic is one web-search call (`findCandidates`) returning up to four candidates, each `located`,
  `lead` (named on a page, with the page kept) or `news`. `verifyCandidate` (pure, tested in node) checks
  each: a link the search returned, a page quote, no denied host; a news host is labelled news whatever
  the model called it, and news needs a `why_no_primary`.
- candidates go to a FOUND BY SEARCH tray, grouped by topic in the editor's order. Nothing is on the page
  until the editor clicks Add. A lead offers "search for a copy" or a pasted link. "Search again" per
  topic. The tray is stripped from the publish payload in Pulse and again in CI.
- the panel has a box per research job (2026-10-14, the editor's call): FIND SOURCES in the Beginnings
  zone sends each line straight to a search with no model in between, and a trend-line box in its zone
  runs only the trend-line search. The general revision box no longer routes on keywords ("poll",
  "measure", "figure"), which sent any request containing them to the trend-line search; it handles
  wording and changes across the page, and can still ask for searches.
- a news object carries `source_kind: "news"` through both validators (JS and Python), so the reader page
  can label it. The reader page does not show that label yet.

Not verified: no live run against the real API. The tray and the add buttons were exercised in a local
Pulse with a fixture category (no key, so line and About text were not written).

**Folded into each story's RESEARCH section 2026-10-30, by the editor's call** (T-0110, T-0111). The outline
search (one search per line, three at a time, `findCandidates` unchanged) and its three kinds of candidate
(found, news report, named-not-found with "search for a copy" or "approve with this link") now run per story
in Pulse, beside the research vetoes, in one WAITING FOR YOU list. Nothing reaches the page until the editor
approves it. The category editor's FOUND BY SEARCH tray is unchanged for now; retire it once the per-story
section has been used on real editions.

## Why

The editor's request was an outline: an ordered list of milestones under a category name. The revise box
treated it as a small edit plus three lookups, and the editor had no way to see what the search almost
found. A lead such as the 1899 Bennett Sun ad is exactly what an editor wants to chase; discarding it to
keep the output tidy hid the most useful thing the search produced.

News is allowed because the editor decided it 2026-10-13 (`docs/decisions.md`, "News may carry an object
when no primary source will"). It enters only through the editor's tray: Compose's automatic milestone
search (`proposeMilestones`) still asks for primary sources only, because what it finds is included
without review. The news host list is a list, so an outlet not on it is labelled "found" rather than
"news"; the editor opening each link before adding is the backstop, and the list should grow when that
happens.

Cost: one Sonnet call with up to five web searches per topic. Eight topics is at most 40 searches
($0.40 at $10 per 1,000) plus tokens; an estimate, not measured.

Ruled out: building this into the T-0083 branch's new Backstory tab. The editor is not yet confident
T-0083's approach will hold, so this lands on the shipped panel and can be carried over if T-0083 merges.
The data model change (milestones that each carry several objects) is T-0086.

## Check

```sh
# The candidate logic and the news label hold in both languages, and a revision is not capped at three.
node scripts/test_pulse_categories.js | grep -q "verifyCandidate: a lead keeps the page" || exit 1
node scripts/test_pulse_categories.js > /dev/null || exit 1
python3 editorial/test_categories.py | grep -q "^ok.*labelled news" || exit 1
python3 - <<'PY'
import re, sys
s = open('ntk-pulse/pulse.html').read()
cap = re.search(r"const found=\[\], topics=\(r\.find\|\|\[\]\).*?\.slice\(0,(\d+)\)", s)
zones = 'async function findSources(' in s and 'async function reviseIndicator(' in s
routed = re.search(r"async function reviseCat\(.*?\n\}", s, re.S)
sys.exit(0 if cap and int(cap.group(1)) >= 8 and 'delete x.tray' in s and zones and routed and 'proposeIndicator' not in routed.group(0) else 1)
PY
# manual: on Pages, a revision naming eight milestones shows eight topics in FOUND BY SEARCH
```
