# Design system — the visual rules that hold across surfaces

**Verified against the repo 2026-09-25.** This is a consolidation, not a new
source of truth — every rule below lives somewhere else first (CSS in
`digest/index.html` or `ntk-pulse/build_digest.py`, a locked decision in
`docs/decisions.md`, a ticket in `docs/tickets/`). This doc exists so those
can be read as one system instead of measured fresh every session. Where
this doc and the code disagree, **the code wins** — update this file, not
the other way around. Same posture as `docs/voice.md`, which does this job
for editorial rules; this one is the visual counterpart.

Give this file to a session before it touches CSS on any consumer surface —
`index.html`, `digest/index.html`, `ntk-pulse/build_digest.py`'s templates,
or `ntk-pulse/pulse.html`. It exists to stop the specific failure mode this
project has already hit twice: a value chosen per-component because it
"looks considered," instead of drawn from the scale below.

---

## 1. Where this came from

[The NTK Type Bench](https://claude.ai/artifact/Dy8k7Ag66Zg2xUrHJHceY3) — a
type and interface audit of every consumer surface, September 2026 — is the
source argument for almost everything below. Read it for the *why*; this
doc only holds the *what*, kept current against the code.

The audit's one wrong premise — that only `ntknews.org`'s landing page
should stay dark — was reversed. See §5 and `docs/decisions.md`. Everything
else it argued for shipped.

## 2. Ground truth: dark stays

**The app is dark. This is not up for casual re-litigation.** `/digest`,
the in-app story view (`#storyView`), and their hero sections all sit on
`var(--dark)` (`#261F23`). `ntknews.org`'s landing page has always been
dark. The only cream/white grounds are the archive, the static story
permalinks' body (dark hero, cream body — see §5), and Pulse's own editor
chrome, which was never part of this system.

Decided 2026-09-23, reversing an earlier direction, after the editor saw a
full cream re-theme live on a deploy preview and rejected it.
WCAG contrast is explicitly **not** a current priority — every accent below
already passes contrast on ink; that's what let this decision stand without
a legibility cost. See `docs/decisions.md` for the full record. **Don't
propose moving the app off dark as a cleanup pass.** Reopen only with a new
reason, and expect to be asked for one.

## 3. Type

Two typefaces, both loaded as variable fonts with Google Fonts:

- **Newsreader** — every editorial surface: headlines, story body, section
  titles, the certainty ladder, the archive, the end mark. Carries a true
  optical-size axis (6–72), so headline and body cuts are genuinely
  different drawings, not one outline scaled.
- **Overpass** — chrome only: nav, buttons, category labels, bylines,
  anything administrative rather than written.

**Ten sizes, one scale, ~1.30 ratio, shared by every consumer surface:**

```
10 · 13 · 16 · 20 · 26 · 34 · 46 · 60 · 76 · 104   (px)
```

No other `font-size` value should appear in `index.html`, `digest/index.html`,
or a template in `ntk-pulse/build_digest.py`. No half-pixel sizes, ever —
`9.5px`, `10.5px`, `12.5px` were the specific tell of a value chosen by eye
instead of drawn from a scale.

**Two radii only:** `3px` for inputs and chips, `999px` for pills. Nothing
between.

**Letter-spacing:** `.1em` on tracked capital labels, `0` everywhere else,
plus a handful of named exceptions inside specific components (the ladder's
small-caps section titles, the end mark) — check the file before adding a
new value rather than picking one.

## 4. Capital labels — the thing to delete first, not add

Uppercase, tracked labels are the single most "AI-generated" tell a page
can carry, and the audit cut them from 44 to 15 in the app alone. **The
default move when a new component needs a heading is not a tracked capital
label.** Reach for one only when it's carrying real data — a category, a
date, a section name — never as decoration on a panel or a card. If you're
about to add a fourteenth, ask whether something is a better fit first:
small caps in Newsreader, an italic credit line, or just a sentence.

## 5. Colour — four accents, each with a job

```
--blue:   #0798F2      --amber:  #F2AE2E
--terra:  #DC6550       --teal:   #01B2A7
```

**Purple is retired.** It had four uses, keyed to nothing, and is gone from
the app, the landing page, and Pulse's overlay-swatch picker and Recraft
colour steering (T-0039). The one exception, deliberately left alone: the
onboarding card carousel, which is out of scope until it gets its own pass
(see §7). Don't reintroduce purple anywhere else.

**Terracotta is Backstory's "worse" signal** — a real, working semantic
pattern, not decoration. Keep it there specifically.

All four already clear contrast against the dark ground (`--dark:
#261F23`), which is the entire reason the app can stay dark without a
legibility cost. They have **not** been recalibrated for a cream ground —
if a future surface needs cream (the archive already does, via its own
darker step), don't reuse these hexes directly; that recalibration was
scoped out with the cream re-theme and never built. Ask before assuming a
cream-safe step exists.

## 6. The certainty ladder

Truths → Probabilities → Possibilities → Lies is **one descending ramp of
confidence, not four equal categories with their own colour.** This is the
single most distinctive visual idea in the product and the thing most
likely to drift back to "four coloured dots" if rebuilt from scratch.

```css
.sec-1 .section-title { color: var(--dark); }              /* Truths */
.sec-2 .section-title { color: rgba(38,31,35,0.82); }       /* Probabilities */
.sec-3 .section-title { color: rgba(38,31,35,0.72); }       /* Possibilities */
.sec-4 .section-title { color: #A33421; font-style: italic; } /* Lies — breaks the pattern */
```

Same ramp, same four values, in both `digest/index.html` (`#storyView`)
and `ntk-pulse/build_digest.py` (the static story permalink template).
Lies is the one deliberate break — italic, terracotta, because it's the
negation of the ladder, not its fourth rung. If you change one, change
both, or the two reading surfaces drift the way T-0034's premise warned
about (see `docs/decisions.md`).

## 7. What's explicitly out of scope right now

Don't touch these as a side effect of other work — each needs its own
deliberate pass, not incidental polish:

- **Onboarding's card carousel** (the emoji placeholders). Known-outdated,
  explicitly not a priority. Gets its own epic later.
- **WCAG/accessibility contrast work.** Not a current priority — see §2.
  This doesn't mean "ignore contrast forever," it means don't propose a
  contrast-driven redesign without being asked.
- **A cream-safe step for the four accents.** Scoped out with the cream
  re-theme (§2). Only the archive currently needs cream-safe colour, and
  it already has its own darker values for that — don't generalize from it.

## 8. The end mark

`— 30 —` (em dash, space, 30, space, em dash) closes both reading
surfaces: the Digest tab's story list in the app, and the bottom of every
static story permalink. Traditional newsroom sign for end of copy —
the product's whole promise is that the digest ends, so this is not
decoration. If a new reading surface gets built, it gets this too.

## 9. Two reading surfaces, one system

The app's own story view (`#storyView` in `digest/index.html`) and the
static story permalink (`ntk-pulse/build_digest.py`'s template) are
**two different files that must render the same design** — same ladder
(§6), same end mark (§8), same type scale (§3). They exist because the
app needs a live view with gestures and a persisted beats ladder, and
a shared link needs a page with proper OG tags that works with no JS
framework running. Don't try to collapse them into one file — that was
tried (T-0034) and reverted; see `docs/decisions.md` for why. When you
change one for a visual reason, check the check block in T-0039
(`docs/tickets/T-0039-audit-on-dark-grounds.md`) — it asserts both stay
in sync, and `bash scripts/rot.sh T-0039` will tell you if you've broken
that.
