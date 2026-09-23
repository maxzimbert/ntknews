---
id: T-0035
title: Move the app off dark grounds; give the surviving accents their light step
status: BUILT
tags: [digest, chore]
anchor: digest/index.html:887
---

## What

Filed 2026-09-23 to replace a dangling reference — T-0029's own text cited
"T-0031" as the tracked home for this work, in commit messages and in its
own ticket file, and no such file existed. Rewritten again the same day
after actually investigating the code: the original scope here ("retire
three of five accents," "finish the ladder in the app") turned out to be
partly wrong, caught before writing any code rather than after.

**What's real:**

1. **Move the app off dark grounds.** ~21 in-scope selectors — `background:
   var(--dark)` plus several hardcoded dark hexes (`.today-view`,
   `.profile-view`, `.beats-sheet`, `.bottom-nav`, the onboarding image
   frame) — each carrying its own cream-on-dark text that needs inverting,
   not just the background. `ntknews.org`'s hero keeps its dark ground;
   nothing else does.

   **Excluded on purpose:** `.story-header`, `.story-hero`,
   `.story-hero-wrap`, `.share-bar` — all scoped to `#storyView`, which
   T-0034 deletes outright. Re-theming a view about to be deleted is effort
   spent twice for nothing.

2. **Terracotta is not the "arbitrary accent" the audit described — checked
   before writing this, not assumed.** Its only live uses are a real,
   consistent semantic pattern: *worse / warning / lies* — the Backstory
   "worse" indicator, its "unverified" marker, and the Lies section's own
   locked/hold-to-reveal button all use it that way on purpose. The
   editor's call: keep it doing that job. It gets `--coral-deep`
   (`#A33421`, already built for the landing-page and permalink ladder) so
   it keeps working once those panels sit on cream instead of ink.

3. **Purple genuinely goes — outside `#storyView`.** Its only remaining live
   use in scope is `.bsr-detail-photo`'s fallback fill (shown when a
   Backstory entry has no photo) — a plain placeholder color, not a
   semantic one. Swapped to a neutral grey (`#5A5754`, already in use
   elsewhere as a scale-neutral).

   One more use turned up mid-implementation that item 4 below should have
   caught and didn't: `#storyView`'s Probabilities row renders a
   `.section-dot` with `background:var(--purple)` inline — a real instance
   of the four-hue ladder, just confined to the view T-0034 is deleting.
   It stays on the still-dark `#storyView` ground (excluded per item 1,
   same as `.story-hero`), where all five original accents already pass,
   so it's not a contrast bug — left untouched rather than re-themed twice
   for a view about to go away.

4. **Mostly not real: the "four raw hues in the app" finding.**
   `.pill.truth/.prob/.poss/.lies` and `.section-pills`
   (`digest/index.html:875-890`, since deleted) were dead CSS — no markup
   or JS anywhere in the file ever applied those classes. The one live
   four-hue instance is the `#storyView` section dots noted in item 3,
   already excluded and already fine on their dark ground. So the honest
   fix here is deleting the unused rules, not "finishing a ladder" that
   was never rendering outside the view being deleted.

5. **A sixth, previously-uninventoried defect, found by sweeping contrast
   on every tab rather than trusting the original inventory.** The Profile
   tab's `BEATS_SCALE` array (`digest/index.html:2670`) — a separate,
   unrelated 7-rung "how deep into a subject you've gone" scale (Skimmed →
   Witness), not the four-section ladder — feeds its bright hexes straight
   into inline `style="color:...;"` on `.beat-pill` buttons and the beat
   info sheet. Six of seven rungs measured under 4.5:1 once `.beats-sheet`
   moved to cream (worst: "On the Beat" at 1.4:1). Same fix as everywhere
   else — hue kept, lightness brought down to clear 4.5:1 — including for
   the rung that happens to be purple ("Carrying It"): that hue's job here
   is identifying one rung in an ordered progression, not the decorative
   or semantic role item 3 is retiring purple from, so recalibrating it in
   place rather than picking a replacement hue was the smaller, more
   honest change.

6. **Sync `ntk-pulse/pulse.html`'s palette to match.** Confirmed live and
   in daily use, not assumed: `NTK_SWATCHES` (the featured-photo overlay
   swatch picker, including the No. 1 story) and `NTK_BRAND_COLORS`
   (Recraft AI image-generation colour steering, **on by default** for
   every story) both still offer all five original accents. Drop both to
   blue/amber/teal, matching the app exactly — editor's decision. Without
   this, every photo published after this ticket keeps getting tinted and
   AI-generated toward colours the app just retired.

## Found on review, after the first PR pass

The editor caught two more purple instances a plain "no `var(--purple)`
outside `#storyView`" check couldn't see, because neither used the CSS
variable: a literal `#725ABF` fill behind an onboarding card's placeholder
emoji (swapped to blue, the one surviving accent not already used across
the five onboarding cards) and `.beat-domain-card`'s tint/border, which
reads its color from `BEATS_SCALE`'s "Carrying It" rung — already
recalibrated to `#664CBA` earlier in this ticket, so no change needed
there, just confirmation it wasn't a second miss.

Also requested on review: the `— 30 —` end mark shipped on the static
story permalink (`build_digest.py`) but never made it into the SPA. Added
in two places — replacing "Carry on regardless." at the bottom of the
Digest tab's story list (light-ground `.end-mark`, ink-on-cream, matching
`.mot-footer-text`'s existing colour so it reads as the same element, not
a new one) and after `#storyView`'s four sections, in the same relative
position as the permalink template (dark-ground `#storyView .end-mark`
override, since the shared light-ground rule would be invisible there).
While matching the permalink's own CSS, caught a leftover `'Source Serif
4'` in `build_digest.py`'s `.end-mark` rule — missed by the T-0036 font
backfill — and fixed it to `'Newsreader'` to match every other live
selector.

## Found while verifying

None of this was in the original inventory. Found by sweeping actual
computed contrast (composited background through the real DOM, not grep)
across every tab, the Backstory detail modal, and an open story — the same
method that caught item 5 above.

**Fixed, same "accent needs its light step" pattern as everywhere else:**
`.card-read-cta`'s blue "Read" label, `.hero-date em` and `.today-date em`'s
amber (needed a new `--amber-deep: #7A5308` token — already established
site-wide in `build_digest.py`'s templates, just never defined in this
file), `.today-onramp`'s teal link, and the Backstory worse/better/contested
indicator (`.bsr-ind-unver`, `.bsr-ind-arrow.dir-*`) — the last one is the
exact live instance item 2 above promised `--coral-deep` for for, just not
caught by the original grep-based inventory.

**A real regression, introduced by this branch and reverted:**
`.share-btn.done` (the story view's "Back" button) isn't nested inside
`.share-bar {}` as its own CSS rule, so the exclusion logic that protects
`#storyView` by selector name missed it — same failure mode as the
`.story-hero-headline`/`.story-hero-lede` leak caught earlier in this same
branch. Its cream-on-dark text got flipped to dark-on-dark, i.e.
invisible. Caught by opening an actual story and reading the button, not by
grep. Re-verified afterward with a systematic diff of every class used in
`#storyView`'s markup against `git show HEAD` — no other leaks.

**Found, real, and deliberately left alone — two pre-existing bugs this
ticket doesn't own:**

- `.bsr-detail-clock`'s text (`.bsr-detail-kicker`, `.bsr-detail-num`) sits
  on `.bsr-detail-photo`, which is either a real photo with a dark scrim or
  (for a Backstory entry with no photo) a solid fallback fill. The text
  color is `var(--ink)` — dark-on-dark — which fails whether the fallback
  is the old purple (2.77:1 / 3.02:1, kicker/number) or the new neutral
  grey (3.71:1 / 2.25:1). Confirmed pre-existing by checking both. Not
  fixed here: the fix is picking a new text color for the whole overlay,
  not swapping which accent it is, and that's a design call this ticket
  wasn't asked to make.
- `.featured-hero-category/-headline/-lede/-cta` (the Digest tab's No. 1
  story card) render on a photo with a per-story color overlay
  (`s.overlayColor`, the same value Pulse's swatch picker sets), not a flat
  panel — a composited-contrast sweep can't score it reliably, and a static
  "-deep" swap could make it worse depending on how dark that story's
  overlay is. Same reasoning as the bullet above: real, but not this
  ticket's fix to make.

## Why

Named by the editor: "I liked what you said about transforming the IA of
T, P, P, L away from four equals and their color... I think that change
was great" — an endorsement that covered the landing page and the
permalink, never the app, and nobody said so out loud.

The correction matters more than the original claim did. Two of the four
things this ticket set out to do (retire terracotta everywhere, convert a
live four-hue app treatment) were not true once checked against the actual
code — one was a working semantic pattern misread as noise, the other was
dead code misread as a live bug. Shipping the original plan would have
broken a real feature (the Backstory worse/better/contested colouring) to
fix a problem that did not exist in the app (it only ever existed in a
permalink template already fixed under T-0029, and in dead CSS). Caught by
reading every remaining usage before writing a line of CSS, not by
assuming the audit's app-wide framing applied uniformly to every instance
of a colour.

The pulse.html finding is the one that would have kept resurfacing
silently: nothing about a code change to `digest/index.html` would ever
have caught that the CMS still steers new photos toward the retired
palette. That only came up because the editor asked the right question
about where else these colours live.

## Check

```sh
# The app has no dark backgrounds left, except where #storyView is
# explicitly excluded above (T-0034 deletes it).
test "$(grep -c 'background: *var(--dark)' digest/index.html)" -eq 4

# Purple's decorative placeholder use is gone. The one remaining
# `var(--purple)` is #storyView's own section dot — excluded per item 1,
# same as its four background selectors, since T-0034 deletes the view.
test "$(grep -c -- 'var(--purple)' digest/index.html)" -eq 1

# Terracotta still exists — it kept its real job — but now has a
# cream-safe step available.
grep -q -- '--coral-deep' digest/index.html

# The dead pill/ladder CSS that was never live is gone.
! grep -qE '\.pill\.(truth|prob|poss|lies)' digest/index.html

# pulse.html's palette matches the app: three accents, not five.
test "$(grep -oE \"hex:'#[0-9A-Fa-f]{6}'\" ntk-pulse/pulse.html | sort -u | wc -l | tr -d ' ')" -eq 3
! grep -q "terracotta\|purple" ntk-pulse/pulse.html

# No literal purple hex left either — the CSS variable check above only
# catches var(--purple); the onboarding card used the hex directly. The
# one remaining hit is the --purple token's own definition, still needed
# because #storyView's section dot references it.
test "$(grep -c '725ABF' digest/index.html)" -eq 1

# The end mark replaced "Carry on regardless." and exists on both the
# Digest tab's list-completion footer and #storyView's own close, matching
# the static permalink template.
! grep -q "Carry on regardless" digest/index.html
test "$(grep -c 'class=\"end-mark\"' digest/index.html)" -eq 2
```
