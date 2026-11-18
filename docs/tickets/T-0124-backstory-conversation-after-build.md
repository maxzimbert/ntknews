---
id: T-0124
title: After Build, the same Backstory conversation carries on and replaces Direct the research
status: BUILT
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html:5294
---

## What

The second ship of `docs/briefs/backstory-proposal-and-conversation.md`. Starts only after the editor has inspected
T-0123 on staging.

After T-0123, a built page still has today's three controls (`bsc2Html`): Direct the research, revise one part by
prompt, edit words. Wanted: the conversation that settled the proposal carries on under the built page, and asking
in it does what the first two controls did (research, then re-choose; revise a named part). Edit words stays as it
is. Then the first two controls are removed.

*Changed by the editor, 2026-11-17, when this ship started:* "please make sure I can still remove things, line edit,
revise". Only Direct the research is replaced. Revise on each part, edit words and remove all stay.

## Why

The editor, 2026-11-17: "It's one conversation before and, perhaps, one after. As many chats as it takes to complete
the conversation to get backstory right." One place to talk about a page, instead of three controls with
different reaches, is simpler to use and to keep. Split from T-0123 so the editor can inspect the proposal and
conversation sooner.

## Built (2026-11-17, branch `claude/t-0124-conversation-after-build`, on staging only)

- A message after Build goes to `bspAfter` (in the `BSX` block): the proposal is read off the page (`bspFromPage`, so a
  revise, removal or pin since Build holds), Opus answers with the proposal as it now stands plus `parts` notes. A
  change to the history rebuilds the page from it (`bspBuild`), keeping the title, stakes, We are here and every
  line and note already there; a note on the title, the stakes or We are here runs that part's revise (`bsxRevise`)
  and is recorded in `bs_edits.modify` as the revise box records it. Same uncapped web search and Are.na pass.
- One thread: `d.chat` carries on; Build adds a "page built" marker. The review screen's Direct the research box is
  now TALK IT THROUGH: the proposal (with the tickable missing events), the whole conversation, the send box, and
  the research list. Revise, edit words, remove, make it a milestone and add to the Object Matrix are unchanged.
- Fixed on the way (it was in T-0123 too): revising one part on a page built from a proposal also "repaired" an
  agreed contest that broke the Whether rule. Agreed category, contest and It starts in are now never repaired by a
  revise of another part.
- T-0114's check now looks for the conversation, revise and remove on the review screen instead of DIRECT THE
  RESEARCH (dated in the check).

Measured: `node scripts/test_pulse_conversation.js` passes 22 lines with stand-in replies; each T-0124 piece was seen to
fail its test when removed (six mutations). Not measured: real model replies. Cost per message after Build: one Haiku,
one Opus with search, and, when the history changes, one Sonnet build (about $0.02 to $0.05); a part rewrite is one
Sonnet call (about $0.01 to $0.02).

## Check

```sh
[ -f scripts/test_pulse_conversation.js ] || { echo "OPEN: scripts/test_pulse_conversation.js does not exist"; exit 1; }
out=$(node scripts/test_pulse_conversation.js) || { echo "OPEN: the conversation tests fail"; exit 1; }
for want in \
  "after: asking for research after Build searches and re-chooses the beginnings" \
  "after: asking to change one part after Build changes that part alone" \
  "after: the conversation before and after Build is one thread"
do
  echo "$out" | grep -qF "ok   $want" || { echo "OPEN: no passing test: $want"; exit 1; }
done
grep -q "DIRECT THE RESEARCH" ntk-pulse/pulse.html && { echo "OPEN: Direct the research is still a separate control"; exit 1; }
exit 0
```
