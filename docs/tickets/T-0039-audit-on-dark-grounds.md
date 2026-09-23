---
id: T-0039
title: Finish the Type Bench audit on the app as it is — black grounds, in-app story view, four accents
status: BUILT
tags: [digest, chore]
anchor: digest/index.html:2185
---

## What

Measured 2026-09-23 against `main` (bf194da), after the editor reversed
T-0034 and T-0035 on seeing PR #16's deploy preview.

Most of the Type Bench audit had already shipped under T-0028, T-0029 and
T-0036: the ten-step type scale, two radii, capital labels cut from 43 to 15,
the archive redesign and its 1.92:1 fix, the ↑↓↔ Backstory glyphs, the
mobile hero reorder, the ornamental statistics and taxonomy tags, the
landing page's extra arrows, one headline face, Newsreader and Overpass.
What was left, and what this ticket builds:

1. **The certainty ladder inside the app's story view.** The permalink and
   landing page drew Truths → Probabilities → Possibilities → Lies as one
   descending ramp; the in-app `#storyView` still drew four equal rows,
   each with its own accent dot (blue, purple, teal, terracotta) and an
   Overpass label. Now the same ramp as the permalink: Newsreader small
   caps, ink stepping back in value, Lies in italic `#A33421`. The rows sit
   on white, the same ground the permalink's values were measured against.
   The accordion and Lies hold-to-reveal are kept — the beats ladder reads
   both (T-0015, T-0025).
2. **`— 30 —` closes the Digest list**, replacing "Carry on regardless."
   The permalink already ended with it.
3. **Purple retired.** Its uses were the Probabilities dot (gone with the
   ladder), the Backstory detail's no-photo fallback (now ink), the
   "Carrying It" beats rung (now a light teal, pairing with Witness the way
   Read It / Following It pair on blue), and Pulse's overlay swatch picker
   and Recraft colour steering. Teal, blue, amber and terracotta stay.
   Onboarding's literal `#725ABF` card is left alone — onboarding is out of
   scope until it gets its own epic.
4. **Listen and Share on the story permalink.** A reader who arrives from a
   shared link lands on the static page, not the app, and had neither.
   Ported from PR #16 (where it was verified), with its comments rewritten.
   Re-verified on a fixture render of a real story: Listen starts, pauses,
   resumes; no console errors.
5. **Dead `.pill` / `.section-pills` CSS deleted** — no markup or script
   applies either class. The permalink's end mark moved from 14px (off
   scale) to 13px.

Verified in the browser on the worktree build: the story view's hero is
still black, the four section titles compute to the ramp's colours in
Newsreader, Lies reveal still works, closing a story still records to
`ntk_beats_v1`, no console errors. Unverified: the Netlify deploy preview,
and the real `/digest/YYYY-MM-DD/slug/` address-bar push (routing is off
when the app is served from a sub-path locally; that code is unchanged).

## Why

The audit was right about what to fix and wrong about one premise: it
recorded "nothing but ntknews.org should be dark" as the editor's direction,
and T-0029 carried that forward as settled. Built and seen live (PR #16),
the editor rejected it — the black around the /digest hero and the story
hero is the product's look, and accessibility contrast is not the priority
it would need to be to justify a re-theme. Once the app stays dark, most of
the audit's colour argument stops applying: every accent already reads on
ink. The two-step "cream step" accents are only needed where cream grounds
exist, which the archive and permalink already handle.

The other half of PR #16 was worse than a taste call. T-0034 deleted the
in-app story view on the grounds that it duplicated the permalink. It did
duplicate the *content*, but the view is also where the beats ladder gets
its signals (section opens, the Lies hold-to-reveal) and where the
recognition toasts fire on close — deleting it made two rungs permanently
unreachable and silenced every toast. And the thing it was trying to reach
already existed: `navOverlay()` pushes the story's permalink into the
address bar while the reader stays in the app, so the app already had "one
URL per story" without giving up the SPA. Static pages remain what shared
links and reloads land on, because they carry the OG tags the app lacks.

T-0034's real concern — two templates drifting apart — is handled by the
check below rather than by deleting a surface: both must carry the ladder
and the end mark.

## Check

```sh
# The in-app story view draws the ladder, not four accent dots.
test "$(grep -cE 'class="story-section[^"]*sec-[1-4]' digest/index.html)" -eq 4
! grep -qE 'class="section-dot" style=' digest/index.html

# Both reading surfaces carry the same ladder and the same end mark.
grep -q '\.sec-4 \.section-title' digest/index.html
grep -q '\.sec-4 \.section-title' ntk-pulse/build_digest.py
grep -q '&mdash; 30 &mdash;' digest/index.html
grep -q '&mdash; 30 &mdash;' ntk-pulse/build_digest.py

# The in-app story view still exists — it feeds the beats ladder.
grep -q 'id="storyView"' digest/index.html
grep -qE 'function closeStory\(' digest/index.html

# Purple is gone outside onboarding.
test "$(grep -c '725ABF' digest/index.html)" -le 1
! grep -q '725ABF' ntk-pulse/pulse.html ntk-pulse/build_digest.py index.html

# A shared-link reader can listen and share.
grep -q 'function toggleListen' ntk-pulse/build_digest.py
grep -q 'function shareStory' ntk-pulse/build_digest.py
```
