---
id: T-0041
title: VOICE_REF has no positive instruction toward warmth, only prohibitions
status: BUILT
tags: [editorial, feature]
anchor: ntk-pulse/pulse.html:836
---

## What

Requested directly by the editor, working hypothesis that Jefferson
output reads mechanical rather than enjoyable/human. Measured
2026-09-23: `VOICE_REF`'s 13 numbered rules are, without exception, bans
— no em dash, no signpost verbs, no hedge phrases, positive-form
statements, parallel construction. There is no rule that asks for
anything, only rules that forbid. The two worked examples (the Norway
headline, the Kash Patel paragraph) already have real personality —
"The Secret Service Wishes He'd Stayed Quiet," "That's not bad luck
anymore. That's a pattern" — but nothing in the numbered rules tells the
model that's a feature to imitate, only a style it happens to be
written in.

Added rule (14) to VOICE_REF: an explicit instruction toward one clause
of real personality per section, paired with a guardrail (humor has to
land on the story's actual absurdity, not decorate around it) and an
explicit pointer back to the Kash Patel example's own personality-riding-
on-fact lines as the target — tying the new instruction to a
demonstration that already embodies it, rather than writing a fresh
example that might itself drift from some other rule.

## Why

`docs/decisions.md`'s own postmortem on the em-dash rule found that
VOICE_REF's worked examples outweigh its abstract rules — the em-dash
ban didn't take until the exemplars themselves were also cleaned of em
dashes, because the model was "copying the exemplar faithfully," not
ignoring the rule. That's the reasoning behind not writing a whole new
example here: the existing Kash Patel example already demonstrates
warmth, so the fix is naming what it's already doing, not inventing a
new demonstration that risks disagreeing with it in some other way.

Considered and rejected: rewriting VOICE_REF's tone wholesale, or adding
a long new worked example. Both are bigger changes to a prompt the
editor has already flagged as possibly overgrown — this stays a single
sentence-clause addition, in the same numbered-rule format as the other
13, so it's one clause to react to and revert if it doesn't work, not a
few hundred new words competing for the model's attention.

This is an editorial-judgment change, not a mechanical one — there is no
code assertion that can confirm output reads as "more human." The check
below is structural only (the clause is present, the file parses); the
real verification is the editor reading real Jefferson output against
it.

## Check

```sh
set -e
awk '/^const VOICE_REF/{f=1} f{print} f&&/`;$/{exit}' ntk-pulse/pulse.html | grep -q "Reward the reader"
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' ntk-pulse/pulse.html > /tmp/t0041-check.js
node --check /tmp/t0041-check.js
rm -f /tmp/t0041-check.js
```

manual: editor generates a real Truths/Probabilities/Possibilities/Lies
set with the new clause in place and confirms it reads warmer without
reading like it's straining for a joke; promote to VERIFIED only on that
confirmation, and revert the clause rather than iterate blind if it
doesn't land in one or two real tries.
