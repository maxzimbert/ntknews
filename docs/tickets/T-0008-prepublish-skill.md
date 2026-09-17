---
id: T-0008
title: A prepublish skill that integrity-checks the lineup before it ships
status: PROPOSED
tags: [process, feature]
anchor: ntk-pulse/data/lineup-publish.json
---

## What

A `.claude/skills/prepublish/` skill: run against `lineup-publish.json` before
the publish button, report blockers. First pass would be the checks already
written as tickets — T-0001's onramp resolution, T-0004's em-dash count — plus
image presence per story and a `today.generatedAt` freshness bound.

## Why

Recommended as the first skill to build because its failure has already shipped
three times, and because writing it is the fastest way to learn what a check
block actually needs to contain.

The honest scoping note matters more than the feature. A skill is good at
bounded, verifiable work with a clear done condition. It is not good at taste.
`prepublish` can count em dashes and resolve keys. It cannot tell you whether
the lede lands, and a version that pretends to judge that would be worse than
none, because it would be trusted.

Held at `PROPOSED` deliberately: the checks it would run now exist as tickets
and run on a schedule, so the marginal value is convenience at the moment of
publishing, not coverage. Worth building when the ticket checks have proven
themselves and the shape is known — not before.

## Check

```sh
test -f .claude/skills/prepublish/SKILL.md
```
