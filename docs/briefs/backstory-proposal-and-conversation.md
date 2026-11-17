# Brief: Backstory by proposal and conversation

Written 2026-11-17 from a planning conversation with the editor, for an Opus 5.5 build session. Read `CLAUDE.md`
first; it wins over this file. Then the contract at the top of `docs/backstory.md`, `docs/architecture.md`
("Backstory: build, review, publish") and `docs/decisions.md` from 2026-10-28 on, including the entry dated
2026-11-17 that records this direction.

Tickets: **T-0123** (first ship) and **T-0124** (second ship). Build T-0123 first and put it on staging for the
editor before starting T-0124.

This brief **replaces** `docs/briefs/opus-5-5-backstory-second-brain.md` and tickets T-0117 and T-0118, now
discarded. Read the "What we tried" section below before reusing anything from them.

---

## The problem

A Backstory that does not fit its story is either **scoped wrong** or **missing material** (`docs/decisions.md`,
2026-10-28). Both are judgment calls, and so far the system has tried to make them by machinery: guess a scope,
test the guess, warn the editor. The editor, 2026-11-17: "we've overengineered the warnings on backstory. I think
backstory broadly might be too complex now." And: "we are on the right track that backstory production falls apart
due to scoping issues or library issues. But I don't think we have solved that yet."

## The direction

Settle the scope and the library **in conversation**, in Pulse, then build the page once.

1. **Generate Jefferson makes a proposal for each story and builds a first page from it.** Every story has a
   Backstory from that moment on: the editor, 2026-11-17, "there's no publish with no backstory. Pulse builds
   backstory when Jefferson is generated." The proposal is one scope, the best shot, in this order:
   - **Category** (the row), as categories work today;
   - **It starts in**: a year;
   - **Beginnings**: three to six, each a year and the document that defends it, no prose;
   - **Objects**: the documents in the case, beginnings' documents plus up to two later ones;
   - **What the library lacks**: one line, or nothing.
2. **A conversation sits under each proposal.** The editor says what is off. Each turn, the assistant answers in
   a sentence or two and changes the proposal. The proposal on screen is always the current state, so the editor
   reads it, not the transcript. "As many chats as it takes to complete the conversation to get backstory right."
3. **The editor presses Build** when the proposal is settled ("I decide; button I press is fine"). The page is
   rewritten from the settled proposal: title, contest, stakes, chart, beginning lines, We are here, the notes
   on each document.
4. **After Build**, the editor line edits directly, and directs research and changes. In the first ship that is
   today's controls. In the second, the same conversation carries on after Build and replaces them.

**Most proposals should need no conversation.** The editor reviews Backstory after a digest build, when judgment
is most spent (2026-11-10). A good first proposal, accepted by doing nothing, is the main way this saves time. The
editor expects some back and forth on scope, beginnings and objects; that is the point of the conversation, not a
failure of it.

## The assistant in the conversation

**Model.** Opus 5.5 (`claude-opus-5-5`) for the proposal and the conversation, the editor's choice 2026-11-17.
Sonnet 5.5 writes the page's prose at Build, as today. Haiku 5.5 for small jobs (search terms, refreshing We are
here). Put the conversation model in one constant so it can be changed.

**What it sees each turn.** The story's headline, description and Truths; the current proposal; the conversation
so far; the library (the Object Matrix, approved candidates, research finds, the editor's Are.na library, as
`bsxLibrary` builds it today); the names of recent categories.

**What it can do.** Whatever gets the Backstory right, as the editor specifies it:
- search the library first, and the web when the library lacks something or the editor asks;
- put what it finds straight into the proposal, where the editor sees it and can say drop it;
- change the category, It starts in, beginnings and objects;
- never add to the Object Matrix: a document joins the matrix only on the editor's explicit approval, at
  publish, from live Pulse, as today.

**Historian, at full strength.** The editor, 2026-11-17: "I also want you to be god mode in terms of your historian
and historicizer power." The assistant reasons as a historian, from its own knowledge, not only from what the
library happens to hold: it names the events that made today's story possible, then finds the document that
defends each one. Write its method into a committed prompt file, `editorial/prompts/backstory-historian.md`,
that Pulse loads, distilled from these sources (read them; quote nothing long):

- `editorial/prompts/register4-lifetimes.md`: the containment structure (what held this before, what broke it,
  who was never inside it) and the freshen test (does this event change any of the three?).
- `docs/backstory.md`, "Running alongside: object curation": two documents on opposite sides of the same question,
  close in time (Jefferson and Hamilton on the Bank; Plessy and Harlan's dissent).
- `docs/backstory.md`, "The 21 rows": a contest holds two live answers without taking a side.
- `editorial/research/american_politics_fault_lines.md` and tickets T-0060 and T-0061: the post-1974 fault lines
  and the voices the matrix lacks (women and minority voices before 1981).
- `~/Desktop/NTK/history-brand-document.md` and `history-brand-voice.md`, outside the repo: the editor's own
  history newsletter. Take its **method**: the parallel that is then honestly complicated, precedent read for
  templates as well as warnings, primary sources linked. **Not its viewpoint**: that newsletter states a political
  view, and NTK takes no side (`docs/voice.md`). Do not copy these files into the repo; they are the editor's.

**Two things the historian cannot override.** A document on the page must be a real link that has been fetched
(CLAUDE.md rule 8), and a news report stands in only from the 91 approved publishers. And the editor's words win
over every rule (`docs/decisions.md`, 2026-11-02).

**Categories.** Keep them as they work today. One standing instruction: when naming a category, look at the recent
ones first and prefer one that already exists at the right breadth. The editor, 2026-11-17: when the same category
comes up often, "our conversations and proposal work can ensure there's variety and nuance."

## Rules carried over

- **Every story has a Backstory, always.** A story can change without its Backstory changing, and usually will.
  A built page is never stripped at publish (T-0122, on `main`).
- **When a story changes after its page was built**, Haiku reads the page against the revised story and
  refreshes We are here alone, leaving the rest. If the history itself moved, it says so in one line; rebuilding
  is the editor's choice. This was built on the T-0117 branch (commit `ab4a21fa`); take it from there.
- **A beginning must connect to the story** (it names the words in the story it ties to, tested with
  `catTiesOk`), and **is never dropped over sentence length**: rewritten once, then kept and flagged. Both are on
  the T-0117 branch (`8ae09ecf`); take only these.
- **Warnings: two only.** A document link that does not load, and "the story changed since this was built".
  Every other warning, chip and note about Backstory in Pulse goes. The editor will revisit this once he is
  inspecting real builds.

## What we tried, and what not to reuse

T-0117 (on branch `claude/t-0117-backstory-build-decides-3d1bae`, merged only into `staging`) had the build pick
among three scopes, review its own page, hold weak pages until the editor clicked Ship anyway, and flag problems.
The editor judged it overengineered. **Do not merge that branch.** Take only the three pieces named above. The
holds, the verdicts, Ship anyway, the three scopes and their flags do not come back. T-0118's punch-up style picks
are replaced by the conversation.

## How it ships

- **Branch from `main`**, `T-0123-backstory-conversation`.
- **Rebuild `staging` from `main`** before merging this branch into it, so T-0117 is not on staging when the editor
  inspects. `scripts/stage.sh` says how: "Removing one: rebuild staging from main and merge the ones you still
  want." Nothing else on staging is in use.
- **Staging first.** Publish staging with `bash scripts/stage.sh` and stop for the editor. No PR to `main` until he
  has inspected it and said so.
- **Tests by running.** A new `scripts/test_pulse_conversation.js` in the manner of
  `scripts/test_pulse_categories.js`, with stand-in model replies. The tickets' checks name the lines they expect.
  `node --check` on every script block in `pulse.html`.

## Cost

Measure and report; do not guess. Look up current prices for Opus 5.5, Sonnet 5.5 and Haiku 5.5 before reporting.

- **Every story, every day:** one Opus proposal plus today's build calls.
- **Each conversation turn:** one Opus call, plus a web search when one runs.
- **Build:** one or two Sonnet calls.
- **A changed story:** one Haiku call.

The editor's live key is in his browser only. Run everything you can with stand-in replies, then say exactly what
he should click in staging Pulse to see it work on a real Lineup.

## Out of scope

- The chart's method (sought at Build as today; the editor can ask for another in the conversation).
- Link and quote checking before publish (T-0119) and remembering the editor's judgment (T-0120).
- **The same conversation for the Lineup.** The editor, 2026-11-17, wants something like this for slow-moving big
  news ("affordability, corruption, cyber attacks, social media, climate change") so he can follow it as NTK
  digests. Not now. Build the conversation so it could be reused there, and say what it would take.
