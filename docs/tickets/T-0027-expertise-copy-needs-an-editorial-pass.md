---
id: T-0027
title: Every line of Expertise copy is a placeholder written by the person who wrote the code
status: PROPOSED
tags: [editorial, chore]
anchor: digest/index.html:2620
---

## What

Four surfaces now speak to the reader and every line in them was drafted
alongside the mechanism rather than written as editorial:

- `beatsToastCopy` — seven rungs, the orientation toast
- `beatsExplain` — seven rungs, the explainer sheet
- `beatsNextRung` — assembled from `BEAT_REQS` at runtime
- `visitMoment` — four returning-reader lines, plus the standing
  "Three stories in" orientation card

The editor's note, 2026-09-18, on merging T-0024/25/26: *"the copy you wrote
will need work but we can save it for later."* Recorded so it is not mistaken
for settled.

## Why

The mechanism is the part that needed proving and it is proven; the words are
the part that needed taste and have not had any. Shipping them was right,
because a surface nobody can see cannot be judged, and now every one of these
can be read in place on a preview.

The constraints are already written down and should not be rediscovered. The
register ladder in `docs/decisions.md` puts Register 1 at Grade 3-4 and names
three failure modes to avoid: the Kindergarten Teacher, the Explainer-Splainer
and the Euphemizer. The Expertise briefing adds that recognition should read
as *"a steady colleague pausing to acknowledge something real"*, and that the
reader "did not do something to trigger it; NTK recognised something that was
already true". T-0026 adds that a longer absence gets a warmer line and that
the gap is never the subject.

The hardest line is the one generated from `BEAT_REQS`, because it is assembled
rather than written and drifts toward a quest log the moment it lists
requirements. If it cannot be made to sound like a person, the honest move is
to say less rather than to list thresholds more fluently.

Not a blocker on T-0016. That ticket changes what a beat is *about*, and
rewriting the copy before subjects exist would mean writing it twice: "you are
on the beat: Nation" and "you have been following housing policy for four
months" do not want the same sentence.

## Check

manual: the editor has read every line in `beatsToastCopy`, `beatsExplain`,
`beatsNextRung` and `visitMoment` in place, and each one sounds like NTK
rather than like a product describing itself.
