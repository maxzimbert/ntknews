---
id: T-0021
title: Finishing a digest leaves no trace, so there is nothing for a reading record to be built from
status: PROPOSED
tags: [digest, feature]
anchor: digest/index.html:3417
---

## What

Completing a digest fires `track('digest_complete', {stories_count: total})`
and nothing else. Measured 2026-09-18: no local storage key records a
completed edition, the Profile tab shows domains and rungs only, and the
Moment of Then card resets with the next edition. A reader who finished every
digest for a month has no way to know that, and neither does the product.

The editor's framing, 2026-09-18: *"if I complete a digest, it would be great
to log that digest completion somewhere. It could be the beginning of a
library / trophy bookcase of the subjects and/or topics I am most
knowledgable about."*

This is deliberately not designed here. The ticket exists so the idea, the
constraints and the material already available survive until that
conversation happens.

## Why

**It is not a new idea, and that matters.** The Expertise briefing
(`~/Desktop/NTK/Briefings and narratives/ntk-expertise-narrative-v1.1.html`)
already describes this in section 05, "The Map and the Clippings," and
section 06 ends on an annual Witness Report. Its words, not a paraphrase: the
map should read as *"a portrait, not a scoreboard,"* closer to *"a reading
journal or a reporter's notebook than a progress dashboard,"* and its open
design question 09 is exactly this one. Whoever picks this up should start
from that document rather than from scratch, and should know the vocabulary
it settled: beats, clippings, domain markers, Witness.

**Most of the raw material is already being collected.** `ntk_beats_v1` holds
per-domain stories, sessions, depth, `liesStories` and shares. `readStories`
holds today's set. Story records carry a permalink, a headline and a
category. What is missing is one durable, dated record per finished edition,
and nothing about the current data shape prevents adding it.

**Four decisions already constrain the design, and all four cut the same
way.** `docs/decisions.md` locks: no unread counts, ever; sessions-per-day is
an anti-metric; closure is the product promise and the digest must end; and
the design assumption is that the reader did not read yesterday and will not
read tomorrow. A trophy case that implies a streak, or that makes a missed
day visible as a gap, contradicts all four at once. The briefing's own answer
is that the record is a portrait of what a reader paid attention to, never a
measure of how reliably they showed up. That is the line the design has to
hold.

**One thing that is genuinely open, and should be decided before pixels.**
Whether the unit of the record is the *edition* ("you finished 14 digests")
or the *subject* ("what you have been paying attention to"). The editor's
sentence contains both. They produce different objects: a list of dated
editions is a log and drifts toward a streak, while a shelf of subjects is
the briefing's map and does not. Deciding this first makes the rest of the
design fall out; deciding it late means building twice.

Related: T-0016 changes what a subject even is. Building a shelf of topics on
top of the current section labels would produce a bookcase with four books on
it, three of them called Nation.

## Check

manual: a reader who has finished several editions can see a record of what
they have read, and it does not read as a streak, a scoreboard, or a count of
what they missed.
