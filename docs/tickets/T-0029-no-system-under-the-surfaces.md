---
id: T-0029
title: There is no design system under the consumer surfaces, and the measurable failures that follow from it
status: VERIFIED
tags: [digest, chore]
anchor: digest/index.html:60
---

## What

Measured 2026-09-19, from a type and interface audit of every consumer surface
(ntknews.org, /today, /digest, /backstory, /me, story permalinks, archive).
The finding underneath all the others is that no system exists: values were
chosen per component rather than drawn from a scale.

| Dimension | Shipping | This ticket |
|---|---|---|
| Distinct `font-size` values, app | 21 | 10 |
| Distinct `font-size` values, landing | 21 | 10 (same scale) |
| Distinct `border-radius` values | 10 | 2 |
| Distinct `letter-spacing` values | 9 | 4 (.1em, 0, and two gentle text steps) |
| `text-transform: uppercase` rules, app | 43 | 15 |
| Brand accent colours | 5 | 5 &mdash; deferred, see T-0031 |

Eight of the twenty-one app sizes sit between 9 px and 13 px, including
`9.5px`, `10.5px` and `12.5px`. The replacement scale is a ~1.30 ratio:
10 · 13 · 16 · 20 · 26 · 34 · 46 · 60 · 76 · 104. Every existing size maps to
its nearest step; worst drift is 6 px on one Backstory numeral, and 2 px or
less everywhere else.

Four defects follow from the same absence and are fixed here:

1. **A live contrast failure.** `digest/archive/index.html` sets the date line
   in teal on cream at **1.92:1**. Every accent passes on the ink ground and
   fails on cream — amber 1.40, teal 1.92, blue 2.25, terracotta 2.53,
   purple 3.88. The palette was tuned against dark and reused against light.
2. **Direction encoded by colour alone.** `digest/index.html:3213` renders
   `&rarr;` for every Backstory indicator; only the accent distinguishes
   worse / better / contested, and a right-pointing arrow reads as *flat*,
   contradicting two of the three states.
3. **The mobile hero shows the example before the thing it exemplifies.** At
   375 px the lead image and story card reorder above the headline, leaving
   ~200 px of empty ground before the proposition.
4. **The archive was never designed.** Default blue underlined links and
   browser bullets, emitted by `ARCHIVE_TEMPLATE` in `build_digest.py`.

**Deferred to T-0031, deliberately.** The editor settled on 2026-09-20 that
dark grounds stay on ntknews.org only. Measured while starting it: the app is
not dark in four places, it is dark throughout — eighteen `background:
var(--dark)` rules plus hardcoded darks on `.today-view`, `.profile-view` and
the Backstory panel, with cream-on-dark text carried in `rgba(234,217,197,…)`
literals that each have to be inverted by hand. That is a re-theme of a
4,000-line file, not a token swap, and it is the one item here that cannot be
proven correct by measurement. Bundling it would let the riskiest change gate
twelve safe ones.

It also changes what the accent fix means. On the ink ground every accent
already passes; the contrast failures are real only where cream grounds exist
today, which is the archive. So this ticket fixes the archive's live 1.92:1
failure and leaves the app's accents alone, and T-0031 carries the re-theme
and the two-step accents together, because separately either one makes the app
worse.

Not in scope, and deliberately: the `mailto:` Subscribe action needs an email
provider decision; the site-level OG card needs artwork; the onboarding
overlay's emoji are a knowing placeholder ("there's no art department") and
were left alone.

## Why

The audit's own conclusion is that almost none of this is taste. Twenty-one
font sizes, ten radii, forty-four capital labels and a 1.92:1 date line are
measurements, and a reader does not need to understand typography to be
harmed by them. Fixing the measurable layer first is also what makes a
typeface change legible later: a new face judged through the old spacing gets
blamed for problems it did not cause.

The colour finding is the one that would have been got wrong by instinct.
Darkening all five accents to pass on cream was tested and **fails**: forced
into the narrow lightness band legibility requires, amber and terracotta
collapse to 1.9 ΔE for a deuteranope and 10.9 for normal vision, and teal
drops below the chroma floor and reads grey. The hues are only 30° apart at
the warm end and 27° apart at the cool end; at full lightness they separate by
brightness, and that crutch disappears when they must be dark. Hence two
calibrated steps per accent rather than one darker hex, and fewer accents.

The palette itself is not a mistake — it is a deliberate throwback to Yahoo
News Digest's cover posters, which is also the only other product that shared
NTK's promise of a digest that ends. The accents pass colourblind separation
as a set (worst adjacent pair 15.9 ΔE). They were never recalibrated for a
light ground, which is a much cheaper problem than a bad palette.

Ordering matters and is load-bearing: **the light-ground move and the
two-step accent change must ship together.** Every accent currently passes on
dark and fails on cream, so shipping light grounds alone would make the app
less legible, not more.

## Check

```sh
# The scale: no size outside the ten steps, in either consumer file.
test -z "$(grep -ohE 'font-size: *[0-9.]+px' index.html digest/index.html \
  | grep -oE '[0-9.]+' | sort -u \
  | grep -vxE '10|13|16|20|26|34|46|60|76|104')"

# Radii collapse to two tokens.
test "$(grep -ohE 'border-radius: *[0-9.]+px' digest/index.html \
  | grep -oE '[0-9.]+' | sort -u | wc -l | tr -d ' ')" -le 2

# The half-pixel sizes are gone for good.
! grep -qE 'font-size: *[0-9]+\.5px' index.html digest/index.html

# Capital labels are cut by at least half.
test "$(grep -c 'text-transform: *uppercase' digest/index.html)" -le 22

# The archive date line clears 4.5:1 on cream (it shipped at 1.92:1).
! grep -q '#01B2A7' digest/archive/index.html

# Backstory direction is no longer colour-alone.
grep -qE 'uarr|darr|harr' digest/index.html

# The two ornamental statistics and the four empty taxonomy tags are gone.
! grep -qE '>1807<|fw-card-meta' index.html

# Only the primary call to action keeps an arrow (the other match is a comment).
test "$(grep -c '→' index.html)" -le 2

# One typeface for story headlines, on every surface.
! grep -qE "story-headline|story-hero-headline|featured-hero-headline" \
  <(grep -A2 -E '\.(story-headline|story-hero-headline|featured-hero-headline) *\{' \
    digest/index.html | grep Overpass)
```
