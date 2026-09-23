---
id: T-0035
title: Move the app off dark grounds, retire three accents, finish the ladder
status: DECIDED
tags: [digest, chore]
anchor: digest/index.html:887
---

## What

This ticket existed only as a dangling reference. T-0029's own text cited
"T-0031" three times as the tracked home for this work — in commit messages
and in its own ticket file — and no such file was ever created. Caught
2026-09-23 while auditing T-0029's shipped state against the original
audit, not by the reference resolving to nothing on its own; `grep` doesn't
flag a citation to a file that was never written. Filed for real now, and
T-0029's references corrected to point here.

Three things, decided together because they are one job:

1. **Move the app off dark grounds.** Not four places — eighteen
   `background: var(--dark)` rules plus hardcoded darks on `.today-view`,
   `.profile-view` and the Backstory panel, per T-0029's own measurement.
   ntknews.org keeps its dark hero; nothing else stays dark.
2. **Retire terracotta and purple as accents; give teal and amber their
   cream step in the app.** Both steps already exist and ship elsewhere —
   `--teal-deep` / `--amber-deep` were built for the archive and story
   permalinks in T-0029, just never wired into the app. This must ship with
   (1), not before or after it: every accent currently passes on dark and
   fails on cream, so light grounds alone would make the app less legible,
   not more.

   Blue is deliberately **not** scoped for removal here. Checked before
   writing this: it has 15 uses in the app, and beyond the Truths pill it is
   the link colour, a CTA border, and the Subscribe button's fill
   (`digest/index.html:91,117,228,347,651,896,946,1054`). The audit's "cut
   to two accents" was about the four-section label set, not every use of
   blue in the product. Whether blue survives as the app's interactive
   colour once the palette is otherwise cream-safe is a separate decision
   nobody has made — flagged here rather than assumed either way.
3. **Finish the certainty ladder.** Built on the landing page and the
   permalink template in T-0029. Never applied to the app itself —
   `digest/index.html:887-890` still paints Truths/Probabilities/
   Possibilities/Lies in four raw hues (`.pill.truth` blue, `.pill.prob`
   purple, `.pill.poss` teal, `.pill.lies` terracotta), the exact four-hue
   treatment the audit's Section VII argued against. Convert to the same
   weight-and-value ramp, coral-deep for Lies — which does remove blue from
   *this one role* even though it stays in its others.

If T-0034 lands first and deletes `#storyView`, item 3 only touches
`.pill` and whatever replaces it — confirm the pill classes' actual call
sites before starting, they may be shared with a surface T-0034 doesn't
touch.

## Why

Named by the editor directly: "I liked what you said about transforming the
IA of T, P, P, L away from four equals and their color... I think that
change was great." That endorsement covered the landing page and the
permalink. It was never extended to the app, and nobody said so out loud —
it just didn't happen, silently, the same way the ticket number silently
didn't exist.

The sequencing constraint is load-bearing, not a preference: T-0029 proved
by validator that darkening all five accents to pass on cream collapses two
of them into each other (1.9 &Delta;E for a deuteranope). Two calibrated
steps per accent is the only fix that holds, and it only matters once the
ground is actually light — building it in isolation, or moving the ground
without it, produces a worse app than doing nothing.

## Check

```sh
# The app's own section colours use the ladder, not four raw hues.
! grep -qE '\.pill\.(truth|prob|poss|lies)\s*\{[^}]*var\(--(blue|purple|teal|terra)\)' digest/index.html

# Dark backgrounds are gone from the app (ntknews.org's hero is index.html,
# untouched by this check).
test "$(grep -c 'background: *var(--dark)' digest/index.html)" -eq 0

# Only the two retained accents remain wired to anything.
! grep -q -- '--purple:' digest/index.html
! grep -q -- '--terra:' digest/index.html
```
