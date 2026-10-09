# Locked decisions

Choices that were argued through and settled. The reasoning is recorded so it
can be **re-examined** — not so it can be ignored, and not so it can be quietly
reversed by a change that seemed convenient at the time.

If you're about to do something on this list, that's fine. Say so out loud
first, and say why the original reasoning no longer holds.

Consolidated 2026-09-15 from the session READMEs in
`~/Desktop/NTK/ReadMes (post 9:10)/`.

---

## Product

**State, not stream.** Always current, never rewards a refresh. Like
Memeorandum or Drudge in *currency* — explicitly not in pull-to-refresh
mechanics.

**No unread counts, ever.** The audience is news-avoidant by definition and
lapses by design. Backlog-as-debt is the exact mechanism of the avoidance.

**The digest must end.** 4–10 cards with a defined last card. Closure is the
product promise.

*Range corrected 2026-09-18, by the editor.* It read 6–10 and was recorded as
locked. It never was: eight was a ballpark target that hardened into a floor
through repetition in the docs, not through a decision. What is actually load
bearing is the **defined last card**, not the count. A four-story edition still
ends, and ending is the entire promise. The ceiling is the real constraint,
because an edition that does not fit one sitting stops being finishable.

This surfaced because a check fired, which is the system working: T-0018
compared the landing page's claim against a four-story edition and went STALE.
The threshold it enforced was wrong. The check was right to fire.

**Sessions per day is an anti-metric.** If it rises, the thing they were
avoiding has been rebuilt. North star is completion rate plus self-reported
caught-up confidence.

**Design assumption:** the reader did not read yesterday and will not read
tomorrow.

---

## Editorial

**The four sections are lanes, and the lane rules decide ownership.**
Already happened and verifiable → Truths. Most likely next step, 60%+ →
Probabilities. Lower-probability but evidence-tethered → Possibilities. An
identifiable claim that doesn't survive scrutiny → Lies.

**Registers map to depth, not audience.** Register 1 (headlines, ledes, first
sentences) is Grade 3–4. Register 2 (bodies) is Grade 6–7. Register 3
(Backstory) is Grade 8–10. The **Escalation Rule**: register only rises with
depth inside a story, never falls.

**Prime Directive of Register 1:** simplify the syntax, never the reader.
Three named failure modes to avoid — the Kindergarten Teacher (performed
enthusiasm), the Explainer-Splainer ("let's break it down"), and the Euphemizer
(softening stakes instead of sentences).

**The civilian anchor.** Every headline uses a brand name, dollar figure, named
institution, or cultural touchstone the reader already owns. No years as
anchors. One anchor, then stop.

**Write for the pause.** Two to four sentences per Truths item. First sentence
lands the fact, second gives it room.

**Lies stays prosecutorial.** The progress-bias work deliberately left it
alone — diluting it with a "who's fixing this" angle would blunt the one
section meant to be uncompromising.

**Possibilities is bounded by the adjacent possible.** First-order (one direct
combination away from the source articles) ordered before second-order, and
second-order items must name their dependency explicitly. Any scenario
requiring an element not already present in the source articles — a technology
that doesn't exist, an actor with no precedent — is definitionally out.

**Attribution is parenthetical only.** `([Source](URL))`. Naming the outlet
narratively *as well* is double attribution, except when a sentence is
genuinely comparing what different outlets reported.

**Em-dash discipline is prompt-only, on purpose.** Converting an em dash to a
period requires judgment a regex can't supply. Do not "fix" this with a regex.

**Correction, 2026-09-17.** This decision was recorded as though a prompt rule
existed. It did not — there was no em-dash instruction anywhere in `pulse.html`.
Measured output: 33 em dashes across 7 published stories, 24 in a single one.

Worse, the prompts contained 82 em dashes of their own, including throughout
the VOICE worked examples the model is explicitly told to study. It was not
ignoring a rule; it was copying the exemplar faithfully.

Fixed by writing the rule (VOICE RULES 8, plus a line in GLOBAL's structural
rules) **and** rewriting the worked examples to contain none, so the
instruction and the demonstration agree. Punctuation only; wording preserved.

The 52 em dashes in SEC_PROMPTS' instructional text were left alone
deliberately — rewriting editorial instructions to fix a formatting tic risks
damaging meaning for an unproven gain. **Measure the next digest before
touching them.** If output em dashes do not drop sharply, that is the evidence
for a bounded deterministic pass, which is the thing this decision was
originally written to prevent.

**Bold-spacing and section self-labeling get both a prompt rule and a
deterministic code fix** (`fixBoldSpacing`, `stripSectionSelfLabel` in
`pulse.html`) — because testing proved the prompt rule alone was insufficient.
The lesson generalizes: **don't assume a prompt-only rule works without testing
it against real generation.**

---

## Architecture

**Cluster keys are NOT stable identity.** The representative article
`cluster.py` picks can change every run as the 6-hour window rolls. Anything
matching stories across runs uses URL overlap (primary) or fuzzy title matching
(fallback) — never an exact key comparison. This has caused real,
hard-to-diagnose bugs more than once.

**Publish sends the whole lineup state, not an increment.** `build_digest.py`
regenerates the content blocks from scratch each time. There is no "add one
story" path. Don't build one without first solving what happens to the other
stories already live.

**No approval gate between Lineup and Publish.** Explicitly decided against a
checkbox or review step — the intent was to let real failure modes surface
rather than smoothing them over during the testing window.
*Worth re-examining:* defect #2 in `docs/state.md` is exactly the kind of
failure this was meant to expose. It surfaced. The question is now live again.

**`lineup_promote.py` only adds.** It never removes or reshuffles. The
"challenger" mechanism — letting a better story automatically displace a worse
one — was deliberately scoped out and tabled. It is the single largest deferred
piece of work in the project. Don't build it as a side effect of something else.

**Full automation of Draft / Enrich / Generate is deferred.** Repeatedly and
deliberately. Treat any temptation to "just automate one more step" as a signal
to stop and scope it properly.

**Permalink pages must be static.** No discoverability tradeoff is acceptable.
A crawler never executes JS, so content has to sit in raw HTML.

**Static permalinks are shells, not a second product.** Decided 2026-09-29.
A static page carries the full text and its meta tags so crawlers, link
previews and agents can read it, and hands the reader off to the app. Reader
behaviour (navigation, tabs, the beats ladder, Backstory pairing, anything
that feeds expertise) lives in `digest/index.html` only. Static pages are
warranted per surface, not by default: dated digest stories are permanent
public record and get them; Backstory is a relationship between tab and
stories, so a crawlable page per row is a later question, not a first
build. If a static page grows its own features, that is the v2 duplication
again.

**Images are decoded to real files at build time.** `og:image` cannot be a
base64 data URI — virtually no crawler resolves one, and meta tag attributes
aren't built to hold hundreds of KB. Everything *else* on the landing page
stays embedded as base64, deliberately, so the page has zero external file
dependencies.

**The RSS User-Agent presents as a real browser, not a bot.** It used to be a
transparent `NTKPulseBot/…` string. Most bot detection now blocks
self-identified bots regardless of intent. This is an acknowledged tradeoff,
not an oversight.

**Archive starts from launch day forward.** No backfill from git history —
technically reconstructable, but not worth it.

---

## Images and illustration

**No AI-generated hero imagery of real public figures.** Synthetic media of an
identifiable official is a real risk, not a style preference. Wikimedia Commons
search exists for exactly this case.

**No AI slop generally**, and **no live polling/odds feature** — the latter
directly contradicts the product's own anti-horse-race stance, which triage's
rubric lists as a pablum-killer. A competitor doing both is a documented
instance of a deliberately different choice, not a reason to reconsider.

**The digest overlay is a digest-view-only CSS treatment.** The story view
renders the same image plain. That absence is the signal telling a reader
they've moved from the digest screen to the story screen. Baking a
duotone/wash into the stored pixels was explicitly rejected because it would
apply everywhere the image renders and erase that distinction.

**Overlay color is picked by hand, not by category.** A fixed formula
(Lies → terracotta, etc.) was considered and rejected: there's one image per
story, and a formula makes it *less* arresting, not more.

**Recraft model and style are separate axes.** Style presets are V2/V3 only —
sending one with a V4/V4.1 model returns a 400. Enforced in code, not just in
the UI. Size is sent as an aspect-ratio string, never hardcoded pixels, because
valid dimensions differ per model.

---

## Retired and rejected

### The Lifetimes / Still Counting two-strata framework

**Retired 2026-09-17, by the editor.** Backstory is pairings — one entry per
digest story, pairing it to a row. Within that model a row is just a row, and
sorting the 21 into two classes explains nothing about how any of it behaves.

This was already half-decided: the Part 2 README records that the "Lifetimes"
naming was dropped and says not to resurrect it in UI copy. The framework
survived anyway in the docs, in `build_backstory.py`'s `FIRE` list, and in how
problems were described — T-0012 was first written as "the seven Still Counting
rows are unreachable," which reads as a design question about two classes of
row when it is a data gap in seven of them.

**What follows:** describe rows by the property that matters — whether a row
carries sub-genres, whether it has a narrative, whether it got paired today.
Not by which stratum it came from. The vocabulary still exists in
`build_backstory.py` and `docs/backstory.md`; that is a cleanup, not a blocker,
and nothing depends on it.



**The Desk is retired.** Its persistent-clustering-and-ledger architecture was
solving the wrong problem — Max wanted right-now awareness, not persistent-
memory diffing. **Do not tune its clustering further.** The impulse to "just
adjust one more threshold" is precisely what triggered the decision to abandon
it.

**Do not rebuild the Story Ledger inside Pulse as persistent cross-day memory.**
v1 is stateless by design. (Note: a *different* ledger concept — the claim
layer in `README-digest-assembly-and-acquisition.md` — is a live proposal, not
this.)

**`pulse-proxy.js` is not adopted.** A local Node proxy conflicts with the
actual workflow. If direct Recraft calls ever hit a real CORS wall, the correct
fix is a Netlify function matching the existing proxy pattern.

**Don't treat friend-cohort completion metrics as cold-audience validation.**
They measure format, not need.

---

## Settled

**Goal A — public understanding of news.** Decided 2026-09-16, resolving the
tension recorded in `README-digest-assembly-and-acquisition` §6.

In the editor's own terms: get something out the door to a friend group, learn
from feedback, surveys and usage data, iterate, and pursue marketing TBD.

**Why this matters downstream:** Goal A makes reaching people *through* other
surfaces a legitimate outcome rather than a consolation prize, and it
deprioritizes the institution-building instruments — accounts, membership,
paywalls — that Goal B would have required first. Ship-and-learn beats
audience-architecture. When a feature can be built free and gated later, build
it free.

**Publish-time integrity gate: warn, with a choice.** Decided 2026-09-16.
When the Today overview doesn't match the lineup shipping with it, Pulse should
raise a dialog offering two paths — regenerate Today now, or publish with the
current Today anyway. Not a hard block, not a silent pass.

This is a deliberate softening of the earlier "no approval gate" decision
above. The reasoning still holds — gates smooth over failure modes worth
seeing — but this failure has now shipped twice silently, and a dialog that
names the problem while leaving the editor in control satisfies both concerns.

**`ntk-production.html` deleted.** 2026-09-16. Its prompt system was a strict
subset of Pulse's, missing five rules (double-attribution, bold-vs-italic
subheads, bold-spacing, section self-labeling, banned signpost verbs). Nothing
was lost. `pulse.html` is now the only copy.

---

**The app stays dark, and the in-app story view stays.** Decided
2026-09-23, reversing the 2026-09-20 direction the Type Bench audit and
T-0029 recorded. Seen live on PR #16's deploy preview, the cream re-theme
was rejected: the black around the /digest hero and the story hero is the
product's look, and accessibility contrast is not currently a priority large
enough to override it. Deleting `#storyView` (T-0034) was rejected with it —
that view feeds the beats ladder and fires its toasts, and `navOverlay()`
already gives each story its permalink URL without leaving the app. Don't
re-propose either as cleanup; reopen only with a new reason.

---

**Backstory objects are links to their primary source; nothing is hosted on NTK.** Decided
2026-10-02. The matrix mixes public-domain texts with in-copyright ones, and one rule is simpler and
safer than a split. A tap on an object leaves NTK, in a new tab. Each object keeps a short NTK page
(title, author, year, two to four sentences, and a "View the primary document" button), because a
reader landing cold on a dense primary text needs some framing. Ruled out: hosting the text, a
pull-quote per object (T-0045, discarded), and the long 4D page with context paragraphs and "where
it stands now" (T-0048, cut to the short page). The editor reversed the earlier plan to host.

**Beginnings and objects are chosen by rule, not by hand.** Decided 2026-10-02 and 2026-10-05.
The editor curates the digest in Pulse and will not choose Backstory objects or write their text.
`editorial/build_backstory.py`: an object is eligible only with a link the checker has not found
dead. Beginnings are 3 to 6 objects from before the row's start year, spread across time with no
repeated author, and an opinion and its dissent count as one document. The case is every
Beginning plus one or two later objects (the editor's rule: a Beginning that is a digitised
primary source with a retrievable link must be in The case). The matrix has no importance signal,
so picks are adequate, not curated; an `Exclude` flag is the intended override and is not built.
Object permalinks stay positional (`/objects/<n>/`) until launch because the selection is frozen
in `backstory.json`; stable IDs are the pre-launch task. `pick()` is gone.

**A matrix link must be a primary source, and where there is doubt it does not graduate.**
Decided 2026-10-02. Accepted: the document itself, or a library, archive, court or government
record of it, or a publication's own copy. Rejected: Wikipedia, retail and book-listing pages,
flashcard and homework sites, unz.com, Internet Archive lending copies, lookalike domains (a
search returned a copycat of Oyez), and a page about a document rather than the document.
Project Gutenberg links use the read-online form. Oyez is preferred over Justia and Wikipedia where
both carry a case. Hofstadter's page and volume numbers cannot be used to link: they match a
three-volume edition, while the Internet Archive holds the 1958, 1969 and 1973 two-volume editions
as restricted lending copies.

**Backstory text is written from the fetched source where it fits, from the matrix row alone
otherwise, and is unverified until the editor spot-checks it.** Decided 2026-10-05, after a
16-document pilot (`editorial/NTK_Pilot_Generation.xlsx`). One sentence of what happened per
Beginning, with the year shown beside it; two to four sentences per object page. Grounded writing is
used only when the page loads and is the document (not a catalogue page, not truncated); anything
else falls back to the matrix row, with the instruction to say less. `editorial/merge_object_notes.py`
holds back text with a number or year it cannot trace to the matrix row or the source, a dash, a
banned phrase, or a writer who said it was unsure. Names it cannot trace are a note, not a block.
Everything in `editorial/object-notes.json` carries `verified: false` until promoted.

**The Object Matrix stays an xlsx; candidates graduate into it.** Decided 2026-10-02. Research goes
in `editorial/NTK_Backstory_Candidates.xlsx` (or the link review sheet), the editor approves, and
approved rows are copied in. A database was raised and parked (T-0066).

**Publish-time Today gate, amended 2026-10-05 (T-0072).** The 2026-09-16 decision above says warn
with a choice, never a hard block. Pulse now warns, with the choice, when the Today overview is
missing, has no generation time, or was generated on an earlier day. It does block, with no choice,
in two cases where publishing would ship the wrong thing by construction: Generate Today is still
running, and Generate Today failed (a failure is stored as the text and would ship as the essay).

**Backstory is built from the story's own subject. The fixed library supplies, retrieval fills the gaps, and the editor promotes.**
Decided 2026-10-06 with the editor, after three separate problems turned out to be one: the origin
a story shows, the category it is filed under, and the Beginnings behind it were all fixed per row,
and a story's real subject (an AI company, Russia, a county lawsuit) does not fit a fixed row.
Every story has a past. Rules, in code (`editorial/build_origins.py`, `build_pairings.py`):
- *Origin*: retrieved per story from Wikipedia leads and the Truths, checked, fallback to the row's
  own line only when nothing is found. All origins stay `verified: false`.
- *Category*: when no row fits, the editor names a new one in Pulse ("no row fits"). It becomes a
  provisional row (`ntk-pulse/data/provisional-rows.json`), never an entry in `backstory-rows.json`,
  with a model-drafted contest line and two-sentence stakes that are checked or dropped, a trend
  line only if a sourced, verified indicator exists (never a drafted one), Beginnings from the
  history of its subject (`editorial/lenses.json`: tech, the regions and countries the news keeps returning to, NATO and
  the G20 nations; the most recent three linked objects per lens before the origin, at least three in
  all. Most lenses are thin in the matrix today, which the lens report records as demand), and the story's own origin as
  "We are here". A later story with the same name joins it. No
  story in 30 days archives it. Promotion to a real row is never automatic: it needs 3 stories on 2
  days, 3 linked matrix objects, a sourced indicator, and the editor's approval.
- *Beginnings* (next, not built): drawn from the history of what the story is about, not only the
  row: tech stories from tech history, Russia and China stories from those countries' own histories,
  and so on. The matrix is the library and has almost none of this today (about 7 Soviet/Russian and
  8 China objects, all American documents; no tech history). Gaps are filled by retrieval proposing
  candidates into the staging workbook, link-checked and approved, so the matrix grows on demand
  and not by an exercise in adding hundreds. Story-specific Beginnings need a page per story,
  because row pages are shared. The editor accepts that cost (2026-10-06): the goal is a system
  that is defensible and justifiable, and page count is secondary. Every choice (row, origin, each
  Beginning) should carry the evidence a reader or critic could check.
The classifier never reaches a provisional row (no sub-genres); only an editor tag does.

**Lenses stay a separate list from the matrix, for now.** Decided 2026-10-06 with the editor.
A lens (a country, an alliance, a technology) is a tag on an object like Column E's Issue (Theme),
but on a different axis: Column E says which American argument an object belongs to; a lens says
who or what it is about. The objects themselves follow the same rules as every other: primary
text, a verified outward link, the link checker. What differs is the selection rule: a row's
Beginnings are spread across time before its start year, a lens's are the three nearest before the
story's origin. The data should be one thing and the two rules should live in code. A `Lens` column
in the matrix (blank NTK Row allowed for purely foreign objects; the loader currently skips them) is
the likely end state, and not done yet: it changes the matrix schema, and `editorial/lenses.json`
works meanwhile. New lens objects arrive through the candidates workbook with a `Lens` column, so
they graduate by the path the editor already trusts. The workbook's `Lenses` tab records the
definitions and how thin each lens is.

## Open questions, not defaults

These are genuinely unresolved. Don't assume either way.

1. **Is Backstory free or paid?** Free for now, possibly paid later. See
   `docs/backstory.md` for the live disagreement between the roadmap's $5/mo
   narrative tier and the argument that continuity and identity are the
   defensible thing to charge for.
2. **Do the 14 indicator values get automated** (FRED, NOAA) or stay
   hand-maintained annually? Leaning hand-maintained.
3. **Is "the close" machine-selectable at all?** The most taste-dependent slot;
   may need a curated pool rather than a scorer.
