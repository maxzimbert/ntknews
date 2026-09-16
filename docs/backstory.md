# Backstory

**Two incompatible designs currently share this name.** One is live and empty.
The other is the plan and is not wired to anything. Untangling that is the
first job here.

Verified 2026-09-15.

---

## The decision

**Part 2 — per-story pairings — is the plan.** Confirmed 2026-09-15.

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

### Built but misrouted

**`editorial/build_backstory.py:27`**

```python
OUT = os.path.join(ROOT, 'digest', 'v2', 'data', 'backstory.json')
```

It writes into the **inert** `digest/v2/` tree. The app fetches
`/digest/data/backstory.json` (`digest/index.html:2684`). The generator and the
reader point at different files.

**`digest/v2/js/backstory.js`** — the Part 2 render module. Its header comment
carries wiring instructions that were never followed. No HTML file loads it.

### Not built at all

- The **Pulse-side tagging control** — assigns 0–1 rows per story, pre-filled
  by the classifier, editable. This is what would populate `instances[]` and
  give `todays_pairings` a human-reviewed source instead of raw classifier
  output. **Without it, `todays_pairings` has no path to exist in production.**
- A UI for reviewing or swapping the daily classifier + pairing output before
  publish.
- Folding the Backstory publish into the digest's publish action. They were
  agreed to publish together, on one action. The digest publish code has not
  been touched to call `build_backstory.py` or trigger the prompts.

---

## What's actually deployed (Part 1)

`digest/data/backstory.json` holds **six rows** in the Part 1 schema:

```
id, title, start_date, created_at, close_condition, close_condition_met,
black_swan_override, milestone, narrative, updated, last_rewritten_at,
photo, source_material
```

No `objects`, no `instances`, no `indicator`, no `todays_pairings`.

| Row | Start | Narrative |
|---|---|---|
| US–Israel–Iran | 2026-02-28 | empty |
| Venezuela, post-Maduro | 2026-01-03 | empty |
| Israel–Hezbollah, Lebanon | 2023-10-08 | empty |
| Israel–Gaza | 2023-10-07 | empty |
| Sudan civil war | 2023-04-15 | empty |
| Ukraine–Russia | 2022-02-24 | empty |

**All six narratives are empty strings.** The tab renders six rows with day
counters; tapping any of them opens a modal that says "No narrative yet."

`openBsrDetail()` at `digest/index.html:2727` populates kicker, number, title,
milestone, narrative, and photo. There is no code path for the indicator, the
object case, or the episode list.

### Part 1 decisions worth keeping

Some of Part 1 survives into Part 2 and shouldn't be lost:

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

## The path from here

Rough order. Each step is small and verifiable; none of it is decided.

1. **Point `build_backstory.py` at `digest/data/backstory.json`.** One line.
   Until this is fixed, nothing downstream can work.
2. **Run it** and confirm the output carries 21 rows, `todays_pairings: []`,
   four objects per row, and correctly-shaped indicators.
3. **Decide the render path** — wire `digest/v2/js/backstory.js` into
   `digest/index.html` per its own header instructions, or port its logic
   inline. The existing `bsr*` functions and modal markup would be replaced.
   Note the current file has real routing (deep links to `/backstory`, back-
   button support) that must be preserved.
4. **Extend `openBsrDetail`** to render the indicator, object case, and episode
   list. The simplest approach that avoids touching the modal's structural
   HTML: append them into the existing `bsrDetailNarrative` container.
5. **Build the Pulse tagging control.** The real blocker. Nothing produces
   `todays_pairings` in production without it.
6. **Fold the Backstory publish into the digest publish action.**

### Before step 1

The Part 1 rows currently live are real reader-facing content, however empty.
Decide what happens to them — migrated into the Still Counting set, or dropped.
Six of the seven Still Counting rows match them by name.

---

## Also unresolved

- **Free or paid.** Explicitly deferred. Do not assume either.
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
