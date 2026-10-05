# Backstory

Backstory is the tab that pairs each digest story with the long argument it
belongs to. The design is Part 2 (per-story pairings against a fixed 21-row
library) and it is **live**. The Part 1 design (six hand-kept conflict rows)
was replaced 2026-09-16.

Status verified against the repo 2026-09-29. Open work lives in
`docs/tickets/`; the tickets named below are the source of truth for whether a
piece is done.

---

## Update, 2026-10-05 — what changed since this file was last verified

This file's build plan below is the 2026-09 plan; read this section first, then the decisions in
`docs/decisions.md` ("Backstory objects ...").

- **The row page (4C) is real.** Beginnings are a vertical timeline of 3 to 6 dated entries (year at
  the left, one sentence), closing on the row's own "since ..." line marked **WE ARE HERE**. The
  case is every Beginning's object plus one or two later ones. Data lives in the row's
  `beginnings` field (not `instances[]`, which is left empty on purpose: its old reader treats it
  as episodes) and in each object's `about`, `source_url` and `object_id`.
- **The object page (4D)** is short: header, two to four sentences, source line, and a **View the
  primary document** button that opens the original in a new tab. Both the static twin
  (`editorial/build_backstory_pages.py`) and the in-app overlay (`digest/index.html`) render it; keep
  them in step.
- **The matrix grew to 384 objects and 334 carry a primary-source link** (column O, "Source URL").
  50 do not (T-0071). `editorial/check_links.py` checks every link and writes
  `editorial/object-links-health.json`; a dead link makes an object ineligible (T-0068).
- **Selection and text.** `editorial/build_backstory.py` selects; text is written, validated by
  `editorial/merge_object_notes.py` and stored in `editorial/object-notes.json`;
  `editorial/object-selection.json` is the generated list of what is chosen. Rebuilding after a
  matrix change can change the picks, and any newly chosen object needs text. Run the builds from a
  copy of the repo you control, and commit the regenerated `digest/data/backstory.json` and
  `backstory/`.
- **Open, and the next effort:** the timeline's geometry (T-0073), choosing "It starts in" to fit the
  story (T-0074), the page-bottom visibility bug (T-0075), the categories themselves (T-0076).

## The decisions

**Part 2 — per-story pairings — is the design, and it is live.** Confirmed 2026-09-15.

**The six live Part 1 rows are replaced, not migrated.** Confirmed 2026-09-16.
Their ids don't match Part 2's (`bs-gaza` vs `gaza`, `bs-iran` vs
`us-israel-iran`), so `build_backstory.py`'s preserve-by-id logic would match
nothing anyway. Every narrative is empty, so nothing is lost — **but that stops
being true the moment a narrative is written.** Do the replacement before any
Register 4 work, not after.

**Free for now, possibly paid later.** No gating is built and none should be
built yet. Note the live disagreement in the project's own documents: the
roadmap says $5/mo for the narrative layer, while
`README-digest-assembly-and-acquisition` argues backstory is the most
commoditized good on the internet in 2026 and that continuity and identity are
the defensible thing to charge for. That deserves its own conversation.

**What it is, in the editor's words (2026-09-16):**

> Words, content etc on Backstory should be summoned/generated from whatever
> stories are covered by the Digest. It becomes less of an Atomic Clock
> tracking current shooting wars and distant cold wars and instead becomes a
> destination for readers who want to go deeper into the origins of current
> events and conflicts that dominated the headlines.

This settles the framing question. The seven conflict rows do not disappear —
they stop being *the surface* and become part of the vocabulary, surfacing only
when a digest story pairs to them. Duration still leads, but reading as "this
argument is 71 years old" rather than "day 1,071 of a war."

Part 1 is what happens to be deployed. It is not the target; it's the thing
currently occupying the tab.

---

## What Part 2 is

A museum exhibition inside the news product. Not an encyclopedia, not an answer
engine. The daily digest covers what happened today. Backstory covers **why
today looks like this** — the decades-long argument that today's story is one
episode of.

The organizing move: **duration is the headline.** A row leads with elapsed
time, not a photo or a hed. Short durations mean a conflict is actively
burning. Long durations mean a fault line is being *held* — contained by some
mechanism, at some cost, with someone left outside the containment.

**Backstory is generated fresh from each day's digest.** It is not a standing
list the reader scrolls.

- Today's digest has *N* stories.
- Backstory shows *N* entries — one per story — each pairing that story to one
  of 21 fixed underlying rows, plus one sentence saying why it's there today.
- A conflict untouched by today's news does not appear. Accepted tradeoff.

**On thin days the correct behavior is a smaller Backstory, not a padded one.**
Do not build a fallback that shows the full row list. That was an earlier
design and it was explicitly replaced.

### The two data layers — don't confuse them

Confusing these is the most likely way to reintroduce the abandoned standing-
list design.

1. **The row library.** Fixed, edited a few times a year. 21 rows total. This
   is *inventory*.
2. **Today's pairings.** Generated daily, published with the digest. This is
   the *product surface*.

### The 21 rows

**Still Counting (7)** — hardcoded in `build_backstory.py`, no JSON source:
US–Canada trade war · US–Israel–Iran · Venezuela (post-Maduro) ·
Israel–Hezbollah/Lebanon · Gaza · Sudan civil war · Ukraine–Russia

**Lifetimes-class (14)** — in `editorial/backstory-rows.json`:
Climate · The Media · Immigration · Faith · Taiwan · Government · Order ·
America Abroad · Power · Work · Family · Equality · Korea · The Bomb

The name "Lifetimes" was dropped from UI copy. Don't resurrect it.

Naming decisions already settled, so they aren't re-litigated:

- **Equality**, not "Race" — anchored at *Brown v. Board*, and it holds
  abortion and bodily autonomy. The working rule: *Equality is about civil
  rights, Family is about children.*
- **Family**, not "Sex" — anchored at Nixon's 1971 veto of the Comprehensive
  Child Development Act. Scoped to children and parenting.
- **Immigration** anchored at the 1965 Immigration and Nationality Act, not the
  1986 law — 1965 is when the fault line opened.
- **Government** anchored at Prop 13, chosen over airline deregulation for
  being more legible. An explicit A/B call.
- Every row's **contest line** holds two live opposing answers without taking a
  side, and every start-date line is a plain sentence ("since the oil shock,
  October 1973") rather than an institution or acronym. This phrasing
  convention is load-bearing for Register 4.

Deferred, not forgotten: **India–Pakistan** as a 22nd row (fails the "America
is a party" test but is arguably the likeliest place a nuclear weapon gets
used), and **Surveillance** as a standalone row versus its current home as a
sub-genre under Order.

---

## What exists, and where

### Built and correct

| File | State |
|---|---|
| `editorial/backstory-rows.json` | 14 Lifetimes rows with `id, title, start_date, start_line, contest, roots, subgenres`. Good. |
| `editorial/NTK_Backstory_Object_Matrix.xlsx` | 345 primary-source objects, 1761–2026. Good. |
| `editorial/prompts/classifier-backstory.md` | Register 5A. Haiku. One sub-genre per story, no "none" option. Has a built-in calibration set — **rerun it after any prompt edit.** |
| `editorial/prompts/pairing-lines.md` | Register 5B. Sonnet, not Haiku — highest-frequency generated text in the product, ~3,000 lines/year. One line per *story*, not per row. |
| `editorial/prompts/register4-lifetimes.md` | Register 4. Opus for first drafts. 600–900 words per row, structured on the containment thesis. Editor-triggered, never scheduled. |

### Built and live

- **The library.** `digest/data/backstory.json` holds the 21-row library
  (`rows[]`, each with `indicator`, `objects`, `instances`, `narrative`) and
  `todays_pairings[]`, one entry per digest story. `build_backstory.py` and
  `build_pairings.py` both write this path (T-0007).
- **The renderer.** `digest/index.html` (`fetchBackstory`, from line ~3125)
  renders `todays_pairings` merged onto the row, with a detail view that has
  the indicator, object case and episode list.
- **Publish integration.** `pulse-publish.yml` runs `build_pairings.py` after
  `build_digest.py`, `continue-on-error` by design (Slice 4 below, T-0013).
- **The Pulse tagging control.** A per-story row select in the Lineup tab that
  overrides the classifier before publish, with a same-row collision chip
  (T-0010, `ntk-pulse/pulse.html`, `bsrTagControl`).
- **Pulse's old Backstory tab is a dead end on purpose.**
  `BACKSTORY_PUBLISH_DISABLED = true` (`pulse.html`). Its localStorage array
  would overwrite the library; do not re-enable it.

### Not done

- **Narratives.** 0 of 21 rows have one (T-0003, DECIDED). The detail view
  works without them; Slice 6 is the work.
- **`instances[]` is empty on every row**, so "Earlier episodes" never
  renders. Nothing writes it yet. (2026-10-05: left empty on purpose. Beginnings are the new
  `beginnings` field; see the update above.)
- **Classifier pre-fill in Pulse.** The editor sees only explicit tags, not
  what the classifier will choose (T-0014, PROPOSED). Card collisions between
  two classifier picks are still invisible before publish (T-0011).
- **Seven Still Counting rows have no sub-genres**, so the classifier can never
  reach them (T-0012).
- **`digest/v2/js/backstory.js`** is the superseded Part 2 render module. No
  HTML loads it; the logic was ported inline. Inert, do not delete.

---

## Part 1 (retired)

The six-row Part 1 file (US–Israel–Iran, Venezuela, Israel–Hezbollah,
Israel–Gaza, Sudan, Ukraine–Russia; all narratives empty) was replaced by the
21-row library on 2026-09-16 and nothing was migrated. Some of its decisions
survived:

- **The ceasefire principle.** A ceasefire, truce, or "de-escalation" is a
  milestone, never a close condition, unless a row's close condition says
  otherwise.
- **Duration is computed client-side from `start_date`, never stored**, so it
  can't go stale between publishes.
- **Casualty counts alone don't justify `updated: true`.** The question is
  whether the state of play changed.
- **Real HTML citation links**, not markdown.
- **Structure is not fixed.** Every rewrite reorganizes around the most recent
  verified development. The founding event loses its claim on the opening the
  moment something more consequential displaces it.

---

## The build plan

Six slices, each sized to one pull request, each with a condition for being
done. Ordered so the tab never regresses in front of readers — the standing-row
list stays until there is something better to replace it with.

*The ordering constraint that shaped Slice 1 (fixing the output path alone would have swapped six blank rows for twenty-one) is history; Slice 1 is done.*

---

### Slice 1 — Library and schema

**Done.** Library landed, Pulse publish disabled (T-0007).

Point `build_backstory.py` at `digest/data/backstory.json`, run it, and land a
correct 21-row library: `todays_pairings: []`, four auto-picked objects per row
(two pre-1981, two post-1981), correctly-shaped unverified indicators.

Update the renderer minimally to read `todays_pairings` rather than `rows`, and
show an honest empty state — *"Backstory publishes with each digest"* — instead
of a wall of blank rows.

**Also required in this slice — neutralize Pulse's Backstory publish.** This is
not optional cleanup; it is a data-loss hazard.

`pulse.html:328` is `let BACKSTORY = load(LS.backstory, null) || seedBackstory();`
— Pulse's Backstory tab lives entirely in the editor's browser `localStorage`,
seeded from a hardcoded 7-row list. **It never fetches
`digest/data/backstory.json`.** `publishBackstory()` then does a blind
`PUT` of that localStorage array over the whole file.

So the moment Slice 1 writes the 21-row library to that path, one click of
"Publish Backstory" replaces it with seven Part 1 rows and the slice is gone.
The button must be disabled, removed, or repointed before the library lands.
(Pulse's Backstory tab gets its real replacement in Slice 5.)

Note the seed has **seven** rows while the live file has **six** — the two have
already diverged, which is itself evidence that nothing reconciles them.

**Done when:** `digest/data/backstory.json` has 21 rows in Part 2 shape; the
tab shows the empty state; deep-linking to `/backstory` and the back gesture
still work; and no path in Pulse can overwrite the library.

### Slice 2 — Renderer

**Done.** Ported inline into `digest/index.html`, not loaded from `v2/js/`.

Bring in the Part 2 render module. `digest/v2/js/backstory.js` already exists
with wiring instructions in its header, but it lives in the inert tree and
nothing loads it — decide between wiring it as a real script include or porting
its logic inline. Row card is duration + title + pairing line. Detail view adds
the indicator, the object case, and the episode list.

Test against hand-seeded `todays_pairings`, which is how this was tested before.

**Done when:** a seeded pairing renders end to end, card through detail; the
existing routing, `navOverlay` history handling, and modal IDs are preserved.

### Slice 3 — Generation

A script that takes the published lineup, runs `classifier-backstory.md`
(Haiku) to assign exactly one sub-genre per story, then `pairing-lines.md`
(Sonnet) to write one sentence per story, and writes `todays_pairings`.

Run the classifier's built-in calibration set. Two cases specifically: the
electricity-prices story must reach Work (distribution), not Climate (energy);
the Ground Zero air-quality story must reach Government (did an agency tell the
truth), not Climate (surface-matched on "air quality").

**Done when:** a real published digest produces one correct pairing per story,
and the calibration set passes.

**Built 2026-09-16 as `editorial/build_pairings.py`** — prompts read out of the
`.md` files rather than duplicated, `--mock` and `--dry-run` modes, roll-up and
review-threshold applied in code per the classifier's own spec. **Not yet run
against the real models** (no API key in the build environment), so the
plumbing is verified and the output quality is not. Run it with a key and check
the calibration cases before trusting a publish.

**Open design gap found while building it: the seven Still Counting rows are
unreachable by the classifier.** It classifies against sub-genres, and those
rows are created with `subgenres: []` in `build_backstory.py`. So a Gaza story
can reach America Abroad but never `gaza`. That may be correct — the Lifetimes
rows are the argument vocabulary and the conflict rows are editor-assigned in
Slice 5 — but it was never decided, and right now it means seven of twenty-one
rows can only ever surface by hand. Give them sub-genres if they should be
machine-reachable.

### Slice 4 — Publish integration

Fold the Backstory build into the digest publish so both ship on one action, as
was always intended. Today they are separate buttons and separate commits.

**Done when:** one publish updates the digest and Backstory together.

**Done 2026-09-16.** `pulse-publish.yml` runs `editorial/build_pairings.py`
after `build_digest.py`, using the `ANTHROPIC_API_KEY` secret that workflow
already carries. The existing `git add digest/` picks up the rewritten
`backstory.json` with no change to the commit step.

Marked `continue-on-error: true` deliberately. The digest is the product and
Backstory is additive, so a classifier failure or an exhausted API budget must
never block a publish — a failure leaves the previous pairings in place and the
digest ships regardless. **If the Backstory tab looks like yesterday, check
that step's log first;** it fails quietly by design.

### Slice 5 — Pulse tagging control

**Done (T-0010).** Pre-fill from the classifier is still open (T-0014).

A control in Pulse's certification flow that pre-fills the classifier's row
assignment and lets the editor override it before publish. This is what turns
`todays_pairings` from raw model output into reviewed editorial, and what
populates `instances[]`.

**Done when:** a row assignment can be swapped in Pulse and survives a publish.

### Slice 6 — Register 4 narratives

**Not started (T-0003).**

Editor-triggered rewrite for an individual row using `register4-lifetimes.md`
(Opus for first drafts). Not part of the daily publish — a few times a year per
row.

**Done when:** one row has a real narrative rendering in the detail view.

---

### Running alongside: object curation

Not a slice and not blocking. `build_backstory.py` already auto-picks four
objects per row, so the feature works without this. Curation replaces
mechanical picks with good ones — which matters for a museum feature, but is an
upgrade to a working default.

Nine rows nearly pick themselves (Family, Taiwan, Korea, Immigration, The
Media, Faith, Climate, The Bomb, Order — six to thirteen candidates each; scan,
don't deliberate). Five are real editorial work: Equality (64 objects), America
Abroad (58), Government (58), Power (39), Work (36).

The pattern to reach for: two documents on opposite sides of the same question,
close in time. Jefferson and Hamilton on the Bank, twenty-three days apart.
Plessy and Harlan's dissent. Those do the evenhandedness work without the
narrative having to hedge.

See `backstory-matrix-triage.md` in the ReadMes folder for the full breakdown.

---

## Also unresolved

- **A "Coming soon" subscription gate** appeared in a raw fetch of
  `/backstory` in an earlier session. Unconfirmed whether it's a visible wall
  or inert markup. If real, it contradicts the decision that the row list and
  day counters are free.
- **Two things share the name "Backstory"** in the codebase — this tab, and an
  older per-story "Backstory ↓" modal teaser on story cards. Worth renaming
  one.
- **The New START treaty status** feeds The Bomb row's indicator and needs a
  fresh check before that indicator is marked verified. It expired
  2026-02-05; what happened since is unconfirmed.
