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
