---
id: T-0074
title: "It starts in" should be the story's proximate cause, not where its history begins
status: BUILT
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-05: the origin a Backstory sends the reader to leaped from today's story to
an event decades away (diesel prices today to a 1988 climate hearing; Utah's AI prescriptions to 1978's
Prop 13). The editor wants "It starts in YYYY" to be the story's proximate cause, the event that made
today's story happen, usually 1 to 11 years back. The long lineage belongs on the timeline; the bookend
is the cause.

**Scope rewritten 2026-11-09.** The ticket was written against the row-level design: one fixed
`start_date` per row in `editorial/backstory-rows.json`, then a per-story origin chosen at publish by
`editorial/build_origins.py` from Wikipedia. Both are gone. Since T-0110 and T-0114 each story's
Backstory is composed in Pulse (`bsxComposePrompt()`, `BSX_RULES` in `ntk-pulse/pulse.html`), its
"It starts in" is one of its own milestones, and the row never shapes the page (`docs/backstory.md`,
"The contract"). That delivered the per-story origin. What it did not deliver was the proximate-cause
rule: `BSX_RULES.starts` asked for "the Milestone where this story's history begins", which points the
composer at the earliest milestone, the very leap this ticket exists to remove. The editor approved the
rewrite on 2026-11-09 ("Yes, both").

The change: `BSX_RULES.starts` now asks for the latest milestone before today that set the story in
motion, usually 1 to 11 years back, and says the earliest milestone opens the timeline but is not
automatically "It starts in". The fallback in `bsxShape` (a pick that is missing or from this year
falls back to the latest earlier milestone) already matched this and is unchanged.
`scripts/voice_review.py`'s `BSX_SHA` is updated in the same change.

## The editor's three test cases (2026-10-06)

| Story (TODAY line) | Origin the editor wants |
|---|---|
| "A $6.53 diesel price gets answered with a tax break the president cannot actually authorize alone." | **2025**: President Trump used military force to strike Iran in June 2025 |
| "A state is letting software write prescriptions nobody with a license has to check." | **2024**: the Utah Office of Artificial Intelligence Policy opened in July 2024 |
| "A coalition that lost this war once is rebuilding it with more jets and the same strait to retake." | **2014**: Houthi forces took over the Yemeni capital and civil war began |

Judged on paper 2026-11-09, not run: the rule now asks for these. Whether the composer can choose them
depends on the library, because "It starts in" must be a milestone with a document. The Object Matrix holds
none of the three (checked 2026-10-06), the Are.na library is mostly 2019 to 2021, so each depends on
Pulse's per-story research finding a document for the event. Typed by the editor, any of the three works
today (`docs/decisions.md`, 2026-11-02: the editor's words win).

Expect existing pages to move when rebuilt. The Russell Brand draft on staging (2026-11-09) starts in
2013, the stage show; under the new rule the composer may pick the 2023 milestone instead.

## Known mismatch, not changed

The contract says "It starts in" is never within the last 45 days (`docs/backstory.md`, component 6). The
code enforces "never this year" (`bsxShape`, the `starts` problem check). Milestones carry a year only, so
45 days cannot be enforced from them. "Never this year" blocks every milestone from the current year, even
one ten months old (the diesel story's February 2026 Iran war, in November), and in early January allows
one from last December. Not trivial to align without milestone
dates, so left for the editor to decide.

## Acceptance

1. `BSX_RULES.starts` asks for the proximate cause, 1 to 11 years back, and says the earliest milestone
   is not automatically "It starts in". (Checked below.)
2. The fallback picks the latest milestone before this year. (Checked below.)
3. The rule is on `staging`, where the editor composes. (Checked below; fails until staging has it.)
4. The editor's three cases, run in Pulse with the stories back in a Lineup, give origins the editor
   accepts. This costs three composer runs (a Sonnet call plus the research step's calls each) and waits
   for the editor's go-ahead. Not in the check; VERIFIED needs it.

## Check

```sh
git fetch -q origin staging 2>/dev/null || true
python3 - <<'PY'
import re, subprocess, sys
def rule(src):
    m = re.search(r"\n  starts:\s*'(.*?)',\n", src)
    return m and m.group(1)
main = open("ntk-pulse/pulse.html").read()
bad = []
r = rule(main)
if not r:
    sys.exit("OPEN: BSX_RULES.starts not found in ntk-pulse/pulse.html")
for need in ("proximate", "latest milestone before today", "1 to 11 years", "not automatically"):
    if need not in r:
        bad.append("rule lacks %r" % need)
if "history begins" in r:
    bad.append("rule still asks where the history begins")
if not re.search(r"begs\.filter\(b=>b\.year<now\)\.slice\(-1\)\[0\]", main):
    bad.append("bsxShape fallback is not the latest earlier milestone")
try:
    stg = subprocess.run(["git", "show", "origin/staging:ntk-pulse/pulse.html"], check=True,
                         capture_output=True, text=True).stdout
    if rule(stg) != r:
        bad.append("staging's BSX_RULES.starts differs from this checkout's")
except subprocess.CalledProcessError:
    bad.append("origin/staging not available")
if bad:
    sys.exit("OPEN: " + "; ".join(bad))
PY
```

Criterion 4 is the editor's judgement and is not in the check.
