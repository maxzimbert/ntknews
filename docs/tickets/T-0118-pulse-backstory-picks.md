---
id: T-0118
title: Pulse's Backstory review says which pages need the editor and offers picks, the way punch up does
status: DECIDED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html:5300
---

## What

Scoped with the editor 2026-11-10. The full scope is `docs/briefs/opus-5-5-backstory-second-brain.md`, Part B.
It depends on T-0117, which produces the scopes, the left-out milestones and the self-review this shows.

Read in code 2026-11-10 (`bsc2Html`, `bsc2Card`, `bsc2ResearchList`), not in a browser:

- The review lists every component for every story with the same weight. Nothing says which page is ready
  and which needs a decision.
- A milestone the build dropped appears only as a count in a note ("1 milestone(s) still broke a rule and
  were left out"). It cannot be restored.
- No editor action is recorded, so decisions per page cannot be counted. The only trace on the edition of
  2026-11-10 is `by: editor` on 4 milestones across 2 stories.

The pattern to copy is punch up in the Lineup (`punchUpHeadline`, `ntk-pulse/pulse.html:2615`): one button,
three candidates, click one or dismiss.

Wanted:

1. A summary above the stories: how many pages are ready, need the editor, or are held, each count linking
   to its stories. Story order does not change (T-0090).
2. Each page opens with one line: the scope chosen and why.
3. Picks, at most three each plus dismiss, on:
   - scope: the two runner-up scopes; a click rebuilds on that scope;
   - milestones: connected documents the build left out, each addable in one click; a flagged milestone
     shows keep or remove;
   - It starts in: the other milestones that could carry it.
4. Each self-review concern sits on its component with the recommended fix as a pick.
5. A pick is saved in `bs_edits`, survives a rebuild and ships.
6. Every editor action is logged with the draft: story, component, action, time.
7. A held page shows Ship anyway.

## Why

The editor, 2026-11-10: "I can decide between a few recommendations (like what you do for punch up in Pulse
lineup). So if that model works for Backstory, I am onboard with that."

The editor reviews Backstory after a digest build, when judgment is most spent. Ten open components times
seven stories is the wrong ask at that hour. A choice among three is one the editor has said is easy.

Ruled out: reordering the stories worst first. The Backstory list follows the digest's order on purpose
(T-0090), so the summary links instead.

Ruled out: new free-text controls. Direct the research, revise by prompt, edit words and remove already
exist and stay as they are.

The action log is here because the brief's measure, editor decisions per page, cannot be taken without it.

## Check

```sh
[ -f scripts/test_pulse_backstory.js ] || { echo "OPEN: scripts/test_pulse_backstory.js does not exist"; exit 1; }
out=$(node scripts/test_pulse_backstory.js) || { echo "OPEN: the Pulse Backstory tests fail"; exit 1; }
for want in \
  "summary: counts pages ready, needing the editor, and held" \
  "picks: at most three scope picks, and picking one rebuilds on it" \
  "picks: a left-out milestone can be added in one action" \
  "picks: It starts in offers the other milestones" \
  "picks: a pick survives a rebuild" \
  "log: an editor action is recorded with story, component and action"
do
  echo "$out" | grep -qF "ok   $want" || { echo "OPEN: no passing test: $want"; exit 1; }
done
```

The tests cannot judge the screen. Before this is promoted, the editor also looks at staging Pulse after
Generate Jefferson on a full Lineup: it should be plain within a few seconds which pages need a decision,
and a page that needs one should be settled by clicking picks alone.
