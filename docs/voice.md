# Voice & selection — the rules that write the digest

**Verified against the repo 2026-09-23.** This is a consolidation, not a new
source of truth — every rule below lives somewhere else first (a prompt
string in `pulse.html`, a rubric in a pipeline script, a locked decision in
`docs/decisions.md`, an unwired prompt file in `editorial/prompts/`). This
doc exists so those four things can be read as one system instead of hunted
across seven files. Where this doc and the code disagree, **the code wins** —
update this file, not the other way around.

Status flags used throughout:
- **LIVE** — this prompt/rule fires in production, on a schedule or on
  publish.
- **EDITOR-TRIGGERED** — real code, real prompt, but only runs when someone
  in Pulse clicks a button. Never scheduled.
- **WRITTEN, NOT WIRED** — the prompt file exists and is well-developed, but
  nothing in the repo calls it yet.

This is a collab doc between Max and Claude. Edit it directly — it isn't
generated from anything, so there's no regeneration step to fight.

---

## 1. The register ladder

The editorial vision's own name for "how deep and how plain, depending on
where the reader is." Locked as a decision in
[`docs/decisions.md`](decisions.md), not itself written into any prompt as
literal text — Registers 1 and 2 are a standard the edited output is held to,
not a rubric the model is shown.

**The Escalation Rule, which governs all five:** register only rises with
depth inside a story. It never falls back down once it's climbed.

| Register | Covers | Reading level | Status |
|---|---|---|---|
| 1 | Headlines, ledes, first sentences | Grade 3-4 | Standard only — not literal prompt text |
| 2 | Section bodies (Truths/Probabilities/Possibilities/Lies) | Grade 6-7 | Standard only — not literal prompt text |
| 3 | Backstory standing narrative (the live, empty feature) | Grade 8-10 | **LIVE** — `ntk-pulse/pulse.html:1214`, `makeBackstoryPrompt()` |
| 4 | Lifetimes — the 50-year containment essay per Backstory row | — | **WRITTEN, NOT WIRED** — `editorial/prompts/register4-lifetimes.md` |
| 5A | Backstory classifier — tags a story to a row's sub-genre | — | **LIVE** — `editorial/build_pairings.py`, called from `.github/workflows/pulse-publish.yml:52` |
| 5B | Pairing lines — one sentence linking today's story to a row | — | **LIVE** — same script, same workflow step |

**Register 1's Prime Directive:** simplify the syntax, never the reader.
Three named failure modes to avoid:
- **The Kindergarten Teacher** — performed enthusiasm.
- **The Explainer-Splainer** — "let's break it down."
- **The Euphemizer** — softening the stakes instead of the sentence.

**The civilian anchor** (Register 1): every headline uses a brand name,
dollar figure, named institution, or cultural touchstone the reader already
owns. No years as anchors. One anchor, then stop.

**Write for the pause** (Register 2): two to four sentences per Truths item.
First sentence lands the fact, second gives it room to land.

⚠ **Open discrepancy, found while writing this doc (2026-09-22).**
`docs/backstory.md` still frames Register 5A/5B as "the plan... not wired to
anything," verified 2026-09-15. `build_pairings.py` was committed
2026-09-17 and is called from `pulse-publish.yml`, `continue-on-error: true`.
That means Registers 5A/5B are actually live and `docs/backstory.md` is
stale on this one point. Worth a ticket to correct the doc rather than
trusting either file blind — see `docs/decisions.md`'s own note on how
version drift happens here.

### Register 4 in detail (written, not wired)

Structured on a fixed three-part spine — not a template, the paragraphs
shouldn't announce which question they're answering:
1. **What held this before.** Name the mechanism concretely — institution,
   bargain, legal settlement, set of habits.
2. **What broke it.** A change in conditions or a decision with unseen
   consequences. Not a villain.
3. **Who was never inside it.** Every American containment arrangement
   excluded someone; name them specifically. Not an afterthought, not an
   apology — it's the reason the arrangement can't simply be restored.

Then close on where the argument stands now, without resolving it. Both
sides of the row's "contest" argued at their strongest — evenhandedness on
interpretation, never on verifiable fact. 600-900 words. Opus for first
drafts (the fifty-year synthesis is worth the one-time cost); Sonnet for
freshening against new material, gated by the **freshen test**: does this
event change what the old mechanism was, what broke it, or who was outside
it? If not, most news is just an instance — it belongs in the episode list,
not a narrative rewrite.

---

## 2. Candidate / topic / story selection for digest inclusion

Three stages, each with its own rule set, each paying for the next.

### Ledger — kills increments before selection ever sees them
`ntk-pulse/ledger.py:63-87` · **LIVE**, `pulse.yml` every 4 hours

Every new item is classed:
- **DEVELOPMENT** — evidently adds a new actor, number, document, or
  on-record quote, or changes the state of play.
- **INCREMENT** — restates the ledger with trivial delta: fresh prose, same
  knowledge.
- **RECYCLED** — aggregation of aggregation ("reports say," roundup
  framing), adds nothing.

Judged only on headline + RSS summary, never the full body — "if they show
nothing new, it's an INCREMENT even if the full article might contain more."
A different angle on known facts is still an INCREMENT unless it introduces
a new fact. Contradiction-flagging is strict: only a genuine reversal,
denial, or correction counts, not a routine new development.

### Promotion — Stream to Lineup
`ntk-pulse/lineup_promote.py` · **LIVE**, `pulse-scan.yml` every 20 minutes

- Corroboration bar: **2+ independent publishers** promotes automatically.
- **Progress-singleton exception:** a 1-publisher story can promote if
  `triage.progress_coded == True` *and* its best source tier is ≤2. Both
  required. Exists because wire services converge hardest on disaster, so a
  strict publisher-count bar structurally punishes "a fix in motion" —
  exactly what NTK is biased toward surfacing.
- Roundup filter: titles matching roundup/recap/"weekly in review"/"best of"
  patterns are never eligible, checked before dedup.
- Dedup is URL-overlap first (canonicalized, tracking params stripped),
  falling back to entity+cosine title similarity only when no URLs are
  recorded yet.
- Strictly additive — never removes or reorders an existing lineup entry;
  assembly.py's next full run supersedes it.

### Assembly — the real editorial selection
`ntk-pulse/assembly.py` · **LIVE**, `pulse.yml` every 4 hours

Explicit design stance: *not* top-N by corroboration. "Sorting by
corroboration produces a digest that is accurate, defensible, and grim every
single day." Fills **slots** by reader relationship instead (Plan A):
Unavoidable, Money & me, Body & mind, Work & machines, The group chat,
Elsewhere but here, Flex, The close.

Hard exclusions before any slot sees a candidate: triage verdict `NO`, or
ledger class `INCREMENT`/`RECYCLED`.

Set constraints enforced after slot-filling:
- **Doom-stack cap** — max 2 items with `emotional_load ≥ 4`.
- **Topic cap** — max 2 items sharing the same top-4 entities.
- Min 3 fully self-explainable items (`explainability == 5`).
- Min 2 items not led by a politician.
- Min 1 item with `actionability ≥ 4`.

Ranking score is deliberately **not** publisher-count-dominant:
`pulse_score + new_facts×1.5 + conversational_currency×0.6 +
actionability×0.4 + explainability×0.3` — this is what lets a
single-publisher drug approval beat a fifteen-publisher process story.

Edition size: 8-10 weekday, 4-6 weekend/holiday. Lint is reported, never
auto-enforced — the editor sees the failure and decides.

### Triage — the scoring inputs everything above reads
`ntk-pulse/triage.py:34-87` · **LIVE**, both schedules (Haiku, cached)

- Verdict YES/MAYBE/NO — NO is "pablum: statements without acts, horse-race
  framing, celebrity churn, process increments, press-release rewrites."
- Four 1-5 axes: `emotional_load`, `explainability`, `actionability`,
  `conversational_currency`.
- `progress_coded`: true only if a named actor/institution is doing
  something concrete about a problem, not just issuing a statement or
  promise. "When in doubt, false — a false positive costs more than a false
  negative" (this gates the progress-singleton promotion path above).

---

## 3. Headline writing

Generated twice — by triage on ingest, and again in Pulse when an editor
picks a story — same craft rules both places.
`ntk-pulse/triage.py:58-84` · `ntk-pulse/pulse.html:850-851`

- **Fact + consequence with a unit.** Two sentences. No years as anchors, no
  textbook-chapter-title phrasing.
- Write it from what the cluster's articles say *together* — never copy a
  single article's headline verbatim.
- Three moves, in order of how much they help:
  1. **Stronger verb.** "Switches to / announces / reports" are
     administrative; reach for "scraps / ends / kills / drops / blocks"
     *when the sources genuinely support that verb's force.*
  2. **Stakes over mechanism.** Lead with why it matters over how it
     happened, provided the "why" is already stated, not inferred.
  3. **Cut the hedge-phrase.** "Amid concerns about," "in a move that," "for
     [vague] reasons" get replaced with the actual named thing being hedged.
- **The guardrail governing all three:** compression and selection, never
  invention. No superlative unless sources establish it, no rhetorical
  questions, no manufactured urgency, no wordplay. "A flat accurate headline
  always beats a sharp inaccurate one." Under 90 characters.
- If the source cluster is itself a roundup, headline *that fact* ("Weekly
  culture roundup") — never adopt the roundup's own clickbait title.

---

## 4. Headline punch-up

`ntk-pulse/pulse.html:1484-1503` · **EDITOR-TRIGGERED**, the "punch up"
button on a lineup card

Same guardrail as headline writing, applied on demand to a story the editor
is actually about to lead with:

- Governing principle, stated explicitly: "compression and selection, never
  invention."
- "Most true headlines are written at the flattest level — the
  administrative fact, not the stakes. Find the sharpest TRUE sentence
  available, not the first true sentence available."
- Same three moves (stronger verb / stakes over mechanism / cut the
  hedge-phrase), same guardrail (no superlatives, no rhetorical questions,
  no manufactured urgency, no wordplay, under 90 chars).
- Returns exactly 3 alternative headlines as a JSON array; the editor picks
  one or dismisses all three.

---

## 5. Jefferson generation (article writing)

`ntk-pulse/pulse.html:806-951` · **EDITOR-TRIGGERED**, "Generate Jefferson"
in Pulse Step 5. Built from a shared `GLOBAL` + `VOICE_REF` block, then a
section-specific prompt per Truths / Probabilities / Possibilities / Lies /
Today. The file's own comment marks it as the single source of truth — a
duplicate in `ntk-production.html` drifted and was deleted 2026-09-16.

### GLOBAL — who's writing and why

- Voice: journalist-historian, advanced degree, writes for "Jamie" —
  anxious, news-avoidant, assumes outlets are spinning her. Plain
  vocabulary "not because the reader can't handle more, but because
  anything that sounds like showing off reads as exactly the kind of con
  this reader has learned to distrust."
- Four editorial pillars — stable, not up for casual redesign per
  `CLAUDE.md`: authoritarian movements as a pattern of incompetence;
  inequality / immigration / childcare as structural failures; climate /
  privacy / reproductive rights / movement as constitutional stakes;
  America's contradictions as its operating system.
- Tone: "Tuchman and Halberstam, not Lippmann — scene and consequence
  before judgment."
- **Stakes & plot:** every item needs someone whose situation actually
  changes, named specifically; build toward that, don't open with it.
- **Structural rules:** weave sources into unified analysis, never
  summarize separately; citation format `([Source](URL))` is the *only*
  attribution (no "the Times reported..." unless explicitly comparing
  outlets); bold for headlines only, never subheads; **no em dashes
  anywhere, hard rule**.
- **Quality floor**, all four required: Clarity, Stakes, Momentum,
  Aesthetic pleasure.
- **Cross-section boundary:** already happened → Truths only; likely next
  step → Probabilities only; lower-probability → Possibilities only;
  unsupported claim by identifiable actor → Lies only.
- Length: no hard ceiling, but "cut anything that doesn't deepen stakes,
  advance the plot, or pay off a setup" — most land 300-500 words. If
  nothing in the sources supports an item: `[INSUFFICIENT SOURCE
  MATERIAL]`, never invent.

### VOICE_REF — the 13 numbered rules

`ntk-pulse/pulse.html:831-837`. Headline = fact + consequence; every number
needs a unit; one surgical quote max; name the real mechanism; don't open
with the verdict; end with weight not a moral; **banned signpost verbs**
(underscores, highlights, demonstrates, reveals, showcases, reflects,
signals, represents, speaks to, illustrates, emphasizes, spotlights,
exemplifies — "if a report/memo/study/'this' is the subject doing one of
these, nothing happened in the sentence, find the actor"); no em dashes
(with worked period/colon/comma substitutions); vary sentence structure;
positive-form statements; parallel construction for coordinate ideas; keep
modifiers adjacent to what they modify; one tense per summary. Closes with
the **cynic test**: "Does this sound like someone trying to sell me
something, or someone just telling me what happened?"

### Per-section prompts

- **Truths** — required `[HEADLINE]/[LEDE]/[SUBHEAD]` tags first, then 2-3
  causally-connected movements, not isolated items. "Two-Prong" convention:
  consequential stories get one movement for the event, one for the
  pattern, biased toward who's responding/fixing it over just restating the
  problem — but "an invented accountability angle is worse than none."
  400-450 words.
- **Probabilities** — "pattern recognition stated with conviction, not
  hedged speculation" — "will almost certainly," not "might." Each gives
  something to watch in 1-14 days. 2-3 most consequential only. 400-450
  words.
- **Possibilities** — built explicitly on Kauffman/Kottke's "adjacent
  possible": only combinations newly reachable *this week*, not
  speculative leaps requiring an out-of-character actor or nonexistent
  tech. First-order ordered before second-order (doors that open further
  doors). At least one possibility must be generative, not just risk.
  400-450 words.
- **Lies** — false/manipulative narratives *in active circulation by
  identifiable actors*, not honest disagreement. Must name the claim, who
  makes it, why someone would believe it, who benefits, the factual
  reality, and a historical parallel when earned. "Do not dehumanize
  believers, the lie is the target." Register: "a prosecutor laying out a
  case, not a pundit venting." 400-450 words.
- **Today** (the overview) — a compressed pass over the *finished* edition,
  not new writing — fed already-edited Truths/Probabilities/Possibilities,
  Lies excluded entirely. Must follow the Digest's actual story order
  (story 1 = lead) — reordering the overview independent of the Digest is
  explicitly forbidden. Real paragraph breaks are technical (a blank line,
  not a stylistic choice). 200-300 words.
- A shared **visual-marker system** (`[PULLQUOTE:]`, `[STAT:]`) applies
  across all sections, max one of each per section, optional.

---

## Provenance

| Rule set | Lives in | Status |
|---|---|---|
| Register ladder policy | `docs/decisions.md` | Locked decision, partly unimplemented as prompt text |
| Register 3 (Backstory narrative) | `ntk-pulse/pulse.html` `makeBackstoryPrompt()` | LIVE |
| Register 4 (Lifetimes) | `editorial/prompts/register4-lifetimes.md` | WRITTEN, NOT WIRED |
| Register 5A/5B (classifier, pairing lines) | `editorial/prompts/*.md`, run by `editorial/build_pairings.py` | LIVE |
| Candidate selection — ledger | `ntk-pulse/ledger.py` | LIVE |
| Candidate selection — promotion | `ntk-pulse/lineup_promote.py` | LIVE |
| Candidate selection — assembly | `ntk-pulse/assembly.py` | LIVE |
| Candidate selection — triage scoring | `ntk-pulse/triage.py` | LIVE |
| Headline writing | `ntk-pulse/triage.py`, `ntk-pulse/pulse.html` | LIVE |
| Headline punch-up | `ntk-pulse/pulse.html` `punchUpHeadline()` | EDITOR-TRIGGERED |
| Jefferson generation | `ntk-pulse/pulse.html` `GLOBAL`/`VOICE_REF`/`SEC_PROMPTS` | EDITOR-TRIGGERED |

If a rule here stops matching the code, that's this doc rotting, not the
code being wrong — fix the doc, and if the drift was big enough to cost
someone time, add a line to `docs/log.md`.
