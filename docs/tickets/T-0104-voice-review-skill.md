---
id: T-0104
title: A voice-review skill checks published Today, Digest and Backstory copy against the house rules
status: DECIDED
tags: [editorial, feature]
anchor: docs/voice.md
---

## What

Add a Claude Code skill (`.claude/skills/<name>/SKILL.md`) that reads one day's published copy on
`/today`, `/digest` and `/backstory` and reports where it breaks the house rules. It reports and does
not rewrite, with the exact line and the rule each time. It holds each surface to its own reader:
/today middle school, /digest high school, /backstory AP (`docs/decisions.md`, 2026-10-09).

State on 2026-10-27: the repo has two project skills, `prepublish` and `ticket`. Neither checks prose.
`docs/voice.md` (323 lines) is the rulebook but still gives Backstory as Grade 8-10, which the
2026-10-09 decision replaced. The skill has to take its levels from the decision, or voice.md has to be
corrected first.

## Why

The four sections are written by API prompts inside `ntk-pulse/pulse.html` and the pipeline, not by a
person in a session. Nothing reads the output against `docs/voice.md` after it ships. The em-dash ban,
the civilian anchor, the three named Register 1 failure modes and the per-surface level all rely on
the prompt being obeyed. This repo's history says prompt-only fixes look sufficient and aren't.

Ruled out 2026-10-27: installing Addy Osmani's general writing skill, Clarity (`addyosmani/clarity`,
clarity.addy.ie). Its plain-words and cut-the-padding advice agrees with ours. But a group of its
principles says to take a position and write in first person, a conversational voice. NTK's four
sections require the opposite: evenhanded on interpretation, never on verifiable fact. A generic skill
would also be a second rulebook that sometimes contradicts `docs/voice.md`. Worth borrowing from it:
review mode that critiques and never edits, and the readability-stats script its repo lists under
`scripts/`. That script hasn't been read or run here.

Cost: the skill runs inside a Claude Code session on the editor's plan, not against the Anthropic API
budget. If it is ever wired into CI or the publish workflow it starts spending API money, and that
needs its own decision.

Folding the rules into the generation prompts would fix copy before it ships rather than after. That
is a separate piece of work and doesn't replace an after-the-fact reader. A rule that the prompt
states and the output breaks is exactly what this skill exists to catch.

## Check

```sh
f=$(grep -l "docs/voice.md" .claude/skills/*/SKILL.md 2>/dev/null | grep -v -e /ticket/ -e /prepublish/ | head -1)
[ -n "$f" ] && grep -qi "middle school" "$f" && grep -qi "high school" "$f" && grep -q "AP" "$f"
```
