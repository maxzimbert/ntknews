# Brief for Opus 5.5: Backstory that decides for the editor

Written 2026-11-10 from a scoping conversation with the editor. Read `CLAUDE.md` first; it wins over this
file. Then the contract at the top of `docs/backstory.md`, and `docs/architecture.md`, section "Backstory:
build, review, publish". The history of what was tried is in `docs/briefs/fable-5-2-backstory-and-local-news.md`.

Three tickets carry the work and its checks: **T-0117** (the build decides more), **T-0118** (Pulse offers
picks), **T-0119** (documents checked and described). Build them in that order. T-0120 is a later task; do
not start it.

---

## The problem, in the editor's words

> I am having a hard time deciding a lot of the backstory. The category name (which I think is solved), the
> beginnings/milestones, and objects in the case. Especially after I have done a digest build. So the problem
> to solve is empowering you in Pulse to get as close to the bullseye as possible, do as much thinking and
> deciding on my behalf, as though you were my second brain and knowledge base.

The contract already says doing nothing accepts a page. That fails today for two reasons: the first build is
not good enough to accept unseen, and the review does not say which pages can be trusted.

**The goal.** After a digest build, the editor opens Pulse to seven finished pages. Each one says it is ready,
or names what it is unsure about and offers up to three picks. **The measure is editor decisions per page.**

**The pattern to copy** is punch up in the Lineup (`punchUpHeadline`, `ntk-pulse/pulse.html:2615`): one button,
three candidates, click one or dismiss. The editor, 2026-11-10: "I can decide between a few recommendations
(like what you do for punch up in Pulse lineup). If that model works for Backstory, I am onboard."

---

## Evidence: the edition of 2026-11-10

Seven pages, read from `digest/data/backstory.json` at commit `845a14fb`. The Lineup that built them is
`ntk-pulse/data/lineup-publish.json` at the same commit; use both as fixtures.

| Story | What shipped | The defect |
|---|---|---|
| Nvidia / Megaspeed | 2 milestones | Below the contract (3 to 6). One milestone is "Bloomberg reported that…", dated two days before the story. |
| Carter farm | 2 milestones | Below the contract. One document is a biography web page standing in for 1953. |
| California billionaire tax | 3 milestones, `thin: null` | Wrong scope, not flagged: 1892 Populist platform, Citizens United, 2017 tax act. Nothing on California or on taxing wealth. Two document notes are filler: "…is a case decided by the U.S. Supreme Court. The decision is dated January 21, 2010." |
| Ukraine talks | 3 milestones | 2 of 5 chosen milestones were dropped because the sentence broke a length or number rule. |
| Hegseth impeachment | 3 milestones, all `by: editor` | The build connected none (`thin: "only 0 milestone(s) connect"`). The editor built it by hand. |
| Trump–Biden letter | 5 milestones | Two are "X reported…". Two documents are x.com posts. |
| Mildenhall tankers | 5 milestones | The best page of the day. 1 milestone dropped by a rule. |

Also measured:

- **5 of 7 builds ran a web search** because they were thin (`composed.research`).
- **4 milestones were dropped across 3 stories** by `bsxEnforce` ("still broke a rule and were left out").
- **Almost none of the shipped documents are in `editorial/object-links-health.json`**, last written 2026-10-05.
  A research find is accepted when its URL is one the search returned and it carries a quote
  (`verifyMilestone`, `pulse.html:1641`). The quote is never compared with the page.
- **The Object Matrix has never received a document from Pulse**: `editorial/matrix-additions.json` has 0
  handled, and the ledger has 12 finds with 0 approved.
- **Usage:** about 87k tokens in and 30k out for the day's seven builds, as recorded on the draft.

---

## Part A (T-0117): the build decides more

In `ntk-pulse/pulse.html`: `bsxTerms`, `bsxCompose`, `bsxComposePrompt`, `bsxCheck`, `bsxShape`,
`bsxEnforce`, `bsxRun`. One change in `editorial/backstory_draft.py`.

1. **Three scopes, one chosen.** The naming call (`bsxTerms`, Haiku) returns three scopes for the story:
   narrow (the story's own subject), middle, wide (the long argument). Each has a two-to-six-word name and its
   own search terms. The library is shortlisted for each; that is local and free. The composer sees the merged
   shortlist, picks one scope, and says why in one sentence. The other two are stored on the page as picks.
   No new model call: this widens an existing one.
2. **Every milestone names its tie to the story.** The composer returns, per milestone, a few words taken from
   the story that the milestone connects to. Test it with `catTiesOk` (`pulse.html:1637`), which research
   finds already pass through. A milestone with no tie is not placed. It is kept on the page as "left out",
   with the reason.
3. **Thin means fewer than three connected milestones.** Not fewer than three of any kind.
4. **A thin build widens before it searches.** It rebuilds once on the next wider scope, from the library.
   It runs the web search only if that is still thin. The 30-day subject rule is unchanged.
5. **A sentence that breaks a rule is rewritten, never dropped.** One more rewrite of that line alone. If it
   still breaks the rule, the milestone stays on the page and is flagged for the editor.
6. **A milestone states the event.** No line may open with an outlet or a document as its subject ("Bloomberg
   reported…", "The filing says…"). No milestone may be dated within 45 days of the story; that is "We are
   here". A document that recent may still sit in the case as a later document.
7. **A document note with no fact beyond its title, author and date is left blank** and flagged. Filler is
   worse than nothing.
8. **The build reviews its own page.** One more Sonnet call reads the finished page against the story, as the
   editor would. It returns `ready` or `needs you`, and up to three concerns, each naming one component and
   the fix it recommends.
9. **A weak page is held.** A page is weak when it has fewer than three milestones, has no "It starts in", has
   a blank title, contest, stakes or "We are here", or the self-review says `needs you` with a concern it
   marks as blocking. A held page does not publish unless the editor clicks **Ship anyway** on it. That
   choice rides with the editor's other edits and survives a rebuild. `backstory_draft.py apply` reports a
   held page as "held: weak, not released". The editor chose this on 2026-11-10 over shipping with a warning;
   it narrows "doing nothing accepts" for weak pages only. Record it in `docs/decisions.md`.

## Part B (T-0118): Pulse offers picks

In the review under each story's preview (`bsc2Html`, `bsc2Card`, `bsc2ResearchList`).

1. **A summary at the top of the Lineup's Backstory:** "5 ready, 2 need you, 1 held", each count linking to
   its stories. Story order does not change (T-0090).
2. **Each page opens with one line:** the scope chosen, and why.
3. **Picks, punch-up style, on the three parts the editor finds hard.** At most three each, plus dismiss.
   - **Scope:** the two runner-up scopes by name. A click rebuilds the page on that scope: one compose call.
   - **Milestones:** connected documents the build left out, each addable in one click. A flagged milestone
     shows keep or remove.
   - **It starts in:** the other milestones that could carry it.
4. **Each concern from the self-review sits on its component** with its recommended fix as a one-click pick.
5. **A pick is saved the way the editor's edits are** (`bs_edits`, on the Lineup story), so it survives a
   rebuild and ships. The editor's choice is never repaired.
6. **Every editor action is logged per page:** story, component, action, time. Store it with the draft. It is
   the only way to count decisions per page.

Do not add controls beyond these. The existing ones (Direct the research, revise by prompt, edit words,
remove) stay as they are.

## Part C (T-0119): documents checked and described

1. **Links and quotes are checked before publish.** When the draft is saved, a GitHub workflow fetches every
   document on the draft's pages, confirms the link loads, and confirms the quoted sentence appears on the
   page where one was recorded. It writes the result beside the draft, on the same branch. Pulse shows a
   failure as a flag on the document. No API cost. A page it cannot read (a PDF with no text layer, a login
   wall) is reported as "not checked", never as passed. Reuse `editorial/check_links.py` where it fits.
2. **A document gets a real note the first time it is chosen.** Notes come out empty because the composer is
   given only the title and date and is told to use only those facts. To write a real one the model must
   read the document: one fetch per new document. Confirm the right API tool in the documentation before
   building; do not guess. The note is saved once per document, on the branch Pulse is served from, and
   marked unverified until the editor has shipped a page carrying it (CLAUDE.md rule 9). It is never written
   to the matrix workbook by Pulse.
3. **Staging never writes the Object Matrix.** The editor, 2026-11-10: "I think staging should not write
   into matrix. But when this moves from staging to prod, then yeah it can." Today the matrix is written only
   by `graduate_finds.py` in `pulse-publish.yml`, which runs on `main`, so staging cannot reach it directly.
   The gap is the approval mark: `bsxApprove` (`pulse.html:4967`) writes `approved_by: "editor"` into the
   ledger on whichever branch Pulse is served from, and a later merge could carry that to `main`. In staging
   Pulse, approving a document must add it to the page and must not mark it for the matrix. The control
   should say so.
4. **No batch.** Do not generate notes for the matrix's 384 objects at once. The editor does not want 300 or
   more items arriving for review.

---

## Out of scope

- The memory of the editor's past judgment (T-0120, later).
- Rows and the chart. The editor considers the category name solved; the chart is parked (T-0112).
- The reader app and the static pages. Nothing here changes what a shipped page looks like.
- The contract's rules. This work enforces them; it does not rewrite them.

## Rules that bind

- **The editor's words win.** Whatever the editor directed, typed or picked is never repaired, flagged as weak
  or held (`docs/decisions.md`, 2026-11-02).
- **Staging first.** Each part lands on the `staging` branch and staging Pulse
  (`maxzimbert.github.io/ntknews-staging/`) for the editor to inspect before any PR to `main`. One PR per part.
- **Two Pulses share one `localStorage`.** A Lineup edited in staging is the Lineup prod sees. Staging cannot
  publish.
- **Test by running.** `node --check` on the extracted script. Behaviour tests in a new
  `scripts/test_pulse_backstory.js`, in the manner of `scripts/test_pulse_categories.js`, with stand-in model
  replies. The tickets' checks name the test lines they expect.
- **Judge by several builds.** The same story built twice gives two different pages. Before showing the editor
  a result, build each of the seven fixture stories three times before the change and three times after, and
  report per page: milestones, flags raised, searches run, tokens. That is about 42 builds, roughly six days
  of normal build spend, once. Ask before spending more than that.
- **Name the cost.** A build is two or three model calls today. Part A adds one per story (the self-review),
  about seven a day, and should cut searches. Part C adds one fetch per new document. Report the measured
  change; the expectation that the total is roughly flat is unverified.
- **Model ids** in Pulse stay as they are (`BSX_SONNET`, `BSX_HAIKU`) unless the editor agrees to a change.

## How to know it worked

On the seven fixture stories, after the change:

- no page ships below the contract without the editor having clicked Ship anyway;
- the billionaire-tax story is either built on a scope that connects or held as weak;
- no milestone opens with "X reported";
- no document note is filler;
- fewer than five of seven builds search the web;
- the action log shows fewer editor actions per page than the edition of 2026-11-10 needed. That edition has
  no log, so the baseline is the `by: editor` marks: 4 milestones across 2 stories.
