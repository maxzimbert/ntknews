---
id: T-0123
title: Each story's Backstory starts as a proposal the editor settles in conversation with Opus in Pulse, then is built once
status: BUILT
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html:5114
---

## What

Decided with the editor 2026-11-17. The full scope is `docs/briefs/backstory-proposal-and-conversation.md`.

Today (read on `main`, 2026-11-17): Generate Jefferson calls `bsxRun([story.key], {build:true})`
(`ntk-pulse/pulse.html:3104`), which builds the whole page in one pass. Haiku names search terms, the library is
shortlisted, Sonnet writes all ten components, and the checks repair and drop. The editor then reviews through
Direct the research, revise by prompt and edit words. There is no step where the scope and the library are
settled before the prose is written, and no conversation. Pulse uses `BSX_SONNET` and `BSX_HAIKU`; it has no Opus.

Wanted, the first ship:

1. At Generate Jefferson, each story gets a **proposal**, and only the proposal: category, contest (one "Whether"
   sentence), It starts in, three to six beginnings (year and document), objects. Under it, one line on what the
   library lacks. Written by Opus 5.5. No page is written until Build.
2. Under the proposal, a **conversation** with Opus 5.5. Each turn changes the proposal and says what it changed.
   It searches the library first and the web when needed; what it finds goes into the proposal, never into the
   Object Matrix.
3. Its method comes from a committed prompt file, `editorial/prompts/backstory-historian.md`, loaded by Pulse.
4. **Build** writes the page from the settled proposal, keeping what was agreed (Sonnet 5.5 for the prose).
5. **Publish stops** while any story's proposal is unbuilt, naming each one, with no click-through.
6. The conversation is saved with the draft and survives a reload.
7. Carried from the T-0117 branch, nothing else: a beginning must connect to the story; a beginning is never
   dropped over sentence length; a changed story refreshes We are here alone.
8. Two warnings only: a link that does not load, and the story changed since its page was built.

## Why

The editor, 2026-11-17: "we are on the right track that backstory production falls apart due to scoping issues or
library issues. But I don't think we have solved that yet." Scope is a judgment the editor makes better than any
rule, and three rounds of machinery (fixed rows, rule-picked beginnings, T-0117's three scopes and self-review)
each made the page harder to trust and the screen harder to read. A short conversation over a small proposal puts
the judgment where it belongs, before the prose is written.

Ruled out: T-0117 and T-0118 (holds, verdicts, Ship anyway, three scopes, punch-up picks). The editor: "we've
overengineered the warnings." Their reasoning stays in those tickets.

Ruled out: building a first page at Generate Jefferson, beside the proposal. Proposed and corrected the same day; the
editor: "that's what proposal builds. We hash it out in chat. And then you build off the agreed upon chat." Instead,
publish stops until every proposal is built, as the editor put it, "much in the same way publish cannot proceed if
there is no image on a story or there are too few stories." (In today's code those two are click-through warnings;
this one is a stop.)

Opus is the editor's choice for the proposal and the conversation: the scope is the part that has been failing,
and its outputs are short. Its cost runs on every story every day; it is unmeasured, and the build session must
report it.

## Built (2026-11-17, branch `claude/t-0123-backstory-conversation-3ce370`, on staging only)

Not on `main`; no PR until the editor has inspected it in staging Pulse.

- `editorial/prompts/backstory-historian.md`: the historian's method, loaded by Pulse (`bspHistorian`), distilled from
  the sources the brief names. The editor's newsletter files were read for method only and are not in the repo.
- `ntk-pulse/pulse.html`, inside a new `/* BSX:BEGIN */ … /* BSX:END */` block: `BSX_OPUS` (`claude-opus-5-5`, effort
  `high`; Opus 5.5 rejects thinking off, so `bsxModel` sends effort instead), `bspPropose`, `bspTurn`, `bspShape`,
  `bspDiff`, `bspBuild`, `bspReline`, `bspUnbuilt`, `bsxRefreshHere`, the screen (`bspHtml`). `bsxRun` gained
  `propose`, `turn` and `refresh`; `build` writes from the proposal when there is one. `generateStory` proposes.
  `publishToDigest` stops on `bspUnbuilt` right after `todayPreflight`'s block, with an alert and no confirm.
- Carried from the T-0117 branch, nothing else: the tie test at proposal and at Build; a milestone flagged, never
  dropped (`bsxEnforce`, for every build); the changed-story refresh (`ab4a21fa`).
- Warnings removed from the Backstory screens: thin, "outside the usual rule", paywall, build notes, the "will ship
  without one" publish warning (now a stop). Kept: a link that does not load (new chip, from the pool's link status)
  and the story changed since its page was built. The milestone flag is kept in the data (`b.flag`), not shown.
- T-0114's check line on `generateStory` now requires a proposal and no build (dated in the check).

Measured: `node scripts/test_pulse_conversation.js` passes all 14 lines with stand-in replies, and each line was
seen to fail when the code it covers was broken (eleven mutations, 2026-11-17). Not measured: any real model reply,
the real web search, or the cost of a real story; the editor's key is only in his browser. Prompt sizes measured from
the code and the live pool (356 linked documents): a proposal is about 6,000 input tokens, a turn about 7,500 before
search results. Each draft entry now records its own cost by model (`bsp_cost`), shown under the proposal.

## Check

```sh
[ -f scripts/test_pulse_conversation.js ] || { echo "OPEN: scripts/test_pulse_conversation.js does not exist"; exit 1; }
[ -f editorial/prompts/backstory-historian.md ] || { echo "OPEN: the historian's method is not written"; exit 1; }
grep -q "backstory-historian.md" ntk-pulse/pulse.html || { echo "OPEN: Pulse does not load the historian's method"; exit 1; }
grep -q "claude-opus-5-5" ntk-pulse/pulse.html || { echo "OPEN: Pulse has no Opus for the proposal and conversation"; exit 1; }
for gone in "Ship anyway" "held: weak"; do
  grep -q "$gone" ntk-pulse/pulse.html editorial/backstory_draft.py && { echo "OPEN: T-0117's machinery is in the code: $gone"; exit 1; }
done
out=$(node scripts/test_pulse_conversation.js) || { echo "OPEN: the conversation tests fail"; exit 1; }
for want in \
  "proposal: Generate Jefferson leaves every story with a proposal and no page" \
  "proposal: holds a category, a contest, It starts in, beginnings and objects" \
  "publish: an unbuilt proposal stops the publish, with no way through" \
  "proposal: written by the conversation model, Opus" \
  "chat: a turn changes the proposal and says what it changed" \
  "chat: a document found on the web joins the proposal and not the Object Matrix" \
  "chat: the conversation survives a reload" \
  "build: Build writes the page from the settled proposal and keeps what was agreed" \
  "build: a beginning that names nothing in the story is not placed" \
  "build: a beginning is never dropped for its sentence length" \
  "change: a revised story refreshes We are here and keeps the beginnings" \
  "editor: what the editor typed is never rewritten"
do
  echo "$out" | grep -qF "ok   $want" || { echo "OPEN: no passing test: $want"; exit 1; }
done
```
