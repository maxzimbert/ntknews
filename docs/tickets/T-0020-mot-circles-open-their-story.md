---
id: T-0020
title: The Moment of Then circles stand for stories but do not open them
status: VERIFIED
tags: [digest, feature]
anchor: digest/index.html:2520
---

## What

The Moment of Then card draws one circle per story in the digest, numbered,
filling teal as each is read. The circles were inert `div`s. They are now
buttons that call `openStory(ci)` and carry the story's headline as their
accessible name.

Measured 2026-09-18 before the change: eight circles, all `div`, no click
handler, no accessible name, and the only route to a story was scrolling back
up the list.

## Why

The circle already means "story number five." A reader who has read six of
eight and wants the two they missed is looking straight at the answer with no
way to act on it, and the card sits at the bottom of the list, furthest from
the cards themselves.

The visual design is unchanged and should stay that way. The button carries
`padding: 0` and `appearance: none` so the measured box stays 39px, the fill,
the 1.08 scale and the pop animation are untouched, and a focus ring was added
because the control is now reachable by keyboard.

Worth naming and not fixed here: the tap target is 36px, under the 44px
usually recommended for touch. Widening it changes the grid's proportions,
which is a visual decision rather than a defect fix, and `docs/decisions.md`
is clear that the design is considered rather than provisional. Raise it with
the card's layout, not inside this change.

**Updated by T-0034.** `openStory()` no longer exists — T-0034 deleted the
app's in-app story view, so every story-opening control, including this
one, navigates to the story's real permalink instead. The claim this
ticket makes ("the circle opens the story it stands for") is still true;
only the mechanism the check looked for changed, from a function call to
a real link with `markStoryRead()` run first. Check updated to match,
status untouched since nothing about the feature regressed.

## Check

```sh
python3 - <<'PY'
import re, sys
s = open('digest/index.html', encoding='utf-8').read()
m = re.search(r'const circle = `([^`]*)`;', s)
if not m: sys.exit('the Moment of Then circle template was not found')
tpl = m.group(1)
for needle, msg in [
    ('<button',          'the circle is not a button'),
    ('stories[ci].permalink', 'the circle does not navigate to the story it stands for'),
    ('markStoryRead(${ci})', 'the circle does not mark its story read before navigating'),
    ('aria-label',       'the circle has no accessible name'),
    ('escAttr(',         'a headline is interpolated into an attribute unescaped'),
]:
    if needle not in tpl: sys.exit(msg)
if not re.search(r'\.mot-circle\s*\{[^}]*padding:\s*0', s):
    sys.exit('.mot-circle does not reset the button padding, so the box will not measure 39px')
if not re.search(r'\.mot-circle:focus-visible\s*\{', s):
    sys.exit('the circle is keyboard-reachable with no focus ring')
PY
```
