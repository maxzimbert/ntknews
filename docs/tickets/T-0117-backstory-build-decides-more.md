---
id: T-0117
title: The Backstory build chooses a scope, tests that each milestone connects, reviews its own page, and holds a weak one
status: BUILT
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html:4966
---

## What

Scoped with the editor 2026-11-10. The full scope is `docs/briefs/opus-5-5-backstory-second-brain.md`, Part A.

Measured 2026-11-10 on the seven pages published at commit `845a14fb` (`digest/data/backstory.json`):

- 2 pages shipped with 2 milestones (Nvidia, the Carter farm). The contract says 3 to 6.
- The California billionaire-tax page shipped 3 milestones that do not connect to the story (the 1892
  Populist platform, Citizens United, the 2017 tax act) with `thin: null`. Thin is a count, so it passed.
- 4 chosen milestones across 3 stories were dropped by `bsxEnforce` for a sentence that broke a length or
  number rule.
- 3 milestones open with an outlet as the subject ("Bloomberg reported that…"). One is dated two days
  before its story.
- 2 document notes are filler ("…is a case decided by the U.S. Supreme Court. The decision is dated…").
- 5 of 7 builds ran a web search because they were thin.
- On the Hegseth page the build connected nothing; all 3 milestones are `by: editor`.

Wanted, in `bsxTerms`, `bsxCompose`, `bsxCheck`, `bsxShape`, `bsxEnforce`, `bsxRun`:

1. The naming call returns three scopes (narrow, middle, wide), each with its terms. The composer picks one
   and says why; the other two are kept on the page as picks.
2. Every milestone names the words in the story it ties to (`catTiesOk`). One with no tie is not placed.
3. Thin means fewer than three connected milestones.
4. A thin build rebuilds on the wider scope from the library before any web search.
5. A sentence that breaks a rule is rewritten once more, then kept and flagged. Never dropped.
6. No milestone opens with an outlet or a document as its subject, and none is dated within 45 days of the
   story.
7. A document note with no fact beyond title, author and date is left blank and flagged.
8. One self-review call returns `ready` or `needs you`, with up to three concerns, each on one component.
9. A weak page is held: it does not publish unless the editor clicks Ship anyway. `backstory_draft.py apply`
   reports it as held.

## Why

The editor, 2026-11-10: "I am having a hard time deciding a lot of the backstory … especially after I have
done a digest build. So the problem to solve is empowering you in Pulse to get as close to the bullseye as
possible, do as much thinking and deciding on my behalf."

The contract already says doing nothing accepts a page. That only works when the default is good and the
system is honest about when it is not. On 2026-11-10 neither held: below-contract pages reached readers with
no one having chosen that, and the one wrong-scope page was reported as fine.

Item 9 narrows "doing nothing accepts" for weak pages only. The editor chose it over shipping with a warning.
The cost is that a wrong self-review can hold a good page, and a held page means a story with no Backstory.
That is why the summary in T-0118 must make a held page loud.

Scope picks replace an earlier idea of asking the editor to choose a scope before the build. That was one
more decision for a person who is asking for fewer.

The editor's words still win: nothing the editor directed, typed or picked is repaired, flagged weak or held
(`docs/decisions.md`, 2026-11-02).

Cost: one more Sonnet call per story, about seven a day. Item 4 should cut searches. Whether the total is
flat is unverified; measure it on the fixtures, three builds each (the 2026-10-09 lesson: one run cannot
separate a change from run-to-run difference).

## Built, 2026-11-10 (staging only)

On branch `claude/t-0117-backstory-build-decides-3d1bae`, merged into `staging`. Not on `main`; no PR yet.

- `ntk-pulse/pulse.html`: `bsxTerms` names three scopes (`bsxScopes`); the library is shortlisted per scope and
  merged (`bsxScopeShortlist`); the composer picks one and says why (`scope`, `scope_picks` on the page).
  `bsxShape` places a model's milestone only when its `ties_to` passes `catTiesOk` and it is not within 45 days of
  the story; the rest go to `left_out` with the reason. Thin is fewer than three placed. `bsxBuild` widens once
  before `bsxResearch`. `bsxReline` rewrites a still-broken line once more; `bsxEnforce` flags, never drops, and
  blanks a filler note (`bsxNoteFiller`). `bsxOpensWithSource` is the new event rule. `bsxSelfReview` is the one
  Sonnet review call. `bsxHold` sets `held`/`weak` and honours `bs_edits.ship_anyway`; `bsxPatch` re-holds after
  every edit. The review shows the held box with **ship anyway**, the scope line, the self-review, flags and left out.
  Picks are not built (T-0118).
- `editorial/backstory_draft.py apply`: a held page ships nothing and is logged "held: weak, not released"; the
  review-only fields (`scopes`, `review`, `left_out`, `weak`, `held` and the rest) are not shipped to readers.
- `scripts/test_pulse_backstory.js`: 19 tests, the BSX block run in node with stand-in replies, on
  `editorial/fixtures/backstory-2026-11-10.json` (the seven stories and pages at `845a14fb`). Each core test was
  mutation-checked: disabling the tie test, the widen, the flag, Ship anyway, the editor filter or the 45-day rule
  each makes its test fail; disabling the hold in Python turns this check back to OPEN.
- `scripts/backstory_rounds.py`: tabulates build rounds from the draft's commit history on a branch.

Measured, with stand-in replies (machinery, not model quality):

- On the shipped 2026-11-10 pages, `bsxHold` holds exactly Nvidia and the Carter farm (2 milestones each) and
  nothing else; Hegseth's three editor milestones are not held.
- `bsxOpensWithSource` flags exactly the 4 shipped lines that open with an outlet or an account (Bloomberg, ABC
  News, CBS News, "Biden's archived account") out of 25, and not "Carter reported to Congress".
- `bsxNoteFiller` flags exactly the 2 filler notes (Citizens United, the 2017 tax act) out of all shipped notes.
- The Bloomberg milestone (link dated 2026-11-08) is not placed for a story of 2026-11-10; a document from
  2026-09-01 is.

Not measured: whether real builds are better. That needs the editor's key, in staging Pulse.

Cost per build, by call count: naming (Haiku), compose (Sonnet), repair if needed, a second line rewrite only
when a line still breaks a rule (Sonnet, short), and the self-review (Sonnet, about 2k tokens in). A thin page adds
one compose on the wider scope with no second naming call; only a page still thin after that searches. Whether the
total is flat against 2026-11-10 (about 87k in, 30k out for seven builds, 5 of 7 searching) is unverified.

**The before-and-after, for the editor.** Today's Lineup in Pulse is still these seven stories, so they can be
rebuilt as they are. About five rounds of seven builds, roughly five days of normal build spend.

1. Before (old code, live Pulse, `maxzimbert.github.io/ntknews/ntk-pulse/pulse.html`): Backstory tab, **Build
   Backstory for every story**, twice. The publish of 2026-11-10 is the third. This writes `main`'s draft; it does
   not publish, and the next edition's stories replace it.
2. After (staging Pulse, `maxzimbert.github.io/ntknews-staging/ntk-pulse/pulse.html`): Backstory tab, **Build
   Backstory for every story**, three times. Writes only the `staging` branch's draft.
3. Then: `python3 scripts/backstory_rounds.py --branch origin/main --since <time of step 1>` and the same with
   `origin/staging`, per page: milestones, flagged, left out, widened, searched, review, held, tokens.

Do not click **ship anyway** in staging on a story whose edition is not yet published: staging and live share one
Lineup, so the choice changes the story's fingerprint and live Pulse's built page stops matching until it is
rebuilt there. **hold it again** removes the choice and restores the fingerprint.

## Check

```sh
[ -f scripts/test_pulse_backstory.js ] || { echo "OPEN: scripts/test_pulse_backstory.js does not exist"; exit 1; }
out=$(node scripts/test_pulse_backstory.js) || { echo "OPEN: the Pulse Backstory tests fail"; exit 1; }
for want in \
  "scope: three scopes are named and the two not chosen are kept as picks" \
  "tie: a milestone that names nothing in the story is not placed" \
  "thin: three milestones that do not connect is a thin page" \
  "thin: a thin build widens over the library before it searches" \
  "length: a milestone whose sentence breaks a rule is kept and flagged" \
  "event: a milestone that opens with an outlet is rewritten or flagged" \
  "recent: a milestone within 45 days of the story is not a milestone" \
  "note: a note with no fact beyond title and date is left blank" \
  "review: a page comes back ready or needs you" \
  "held: a weak page does not ship until the editor ships it anyway" \
  "editor: what the editor directed is never held or flagged"
do
  echo "$out" | grep -qF "ok   $want" || { echo "OPEN: no passing test: $want"; exit 1; }
done
python3 - <<'PY' || exit 1
import json, os, subprocess, sys, tempfile
t = tempfile.mkdtemp(); w = lambda n, d: json.dump(d, open(os.path.join(t, n), 'w'))
page = lambda held: {'v': 2, 'title': 'A', 'here': 'Here', 'beginnings': [], 'case': [], **({'held': True} if held else {})}
w('draft.json', {'stories': [{'story_id': 'a', 'bs_hash': '1', 'composed': page(False)}, {'story_id': 'b', 'bs_hash': '2', 'composed': page(True)}],
                 'ship': {'todays_pairings': [{'story_id': k, 'row': 'gaza'} for k in 'ab']}})
w('lineup.json', {'stories': [{'key': 'a', 'bs_hash': '1'}, {'key': 'b', 'bs_hash': '2'}]})
w('bs.json', {'rows': [{'id': 'gaza'}], 'todays_pairings': []})
r = subprocess.run([sys.executable, 'editorial/backstory_draft.py', 'apply', '--draft', t + '/draft.json', '--lineup', t + '/lineup.json',
                    '--backstory', t + '/bs.json', '--provisional', t + '/p.json'], capture_output=True, text=True)
got = [p['story_id'] for p in json.load(open(t + '/bs.json'))['todays_pairings']]
if got != ['a']:
    print('OPEN: a held page ships at publish: shipped', got); sys.exit(1)
PY
```
