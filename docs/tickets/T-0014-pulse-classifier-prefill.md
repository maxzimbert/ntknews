---
id: T-0014
title: Pulse cannot show the classifier's proposed row before publish
status: PROPOSED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

The second half of Slice 5: run `classifier-backstory.md` from inside Pulse so
the editor sees the row the classifier *would* pick, pre-filled and
overridable, rather than choosing from a blank dropdown.

Needs three things Pulse does not have: a model argument on `ai()` (hardcoded
to `claude-sonnet-5`), a fetch of the prompt out of `editorial/prompts/`, and a
browser port of `build_vocabulary()`.

## Why

T-0010 gives the editor the ability to override an assignment. It does not tell
them what they are overriding, so catching a collision still means publishing
first and looking afterwards.

Held separate deliberately. The manual control has to work whether or not this
call succeeds — a pre-fill that fails silently and leaves every dropdown blank
would be worse than no pre-fill, because the blank would read as "no collision."
Build T-0010 first, use it, then decide whether the round trip earns the
plumbing.

Cost is not the obstacle: the classifier is Haiku over eight headlines, a
fraction of a cent per publish.

## Check

```sh
grep -q "classifier-backstory.md" ntk-pulse/pulse.html
```
