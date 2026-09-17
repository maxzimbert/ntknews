# Tickets

A ticket is a file. The file holds a **check** that can fail, and a **why**
that a stranger can read. `scripts/rot.sh` runs every check and exits 1 when
something claimed VERIFIED stopped being true.

That is the whole system. Read `docs/proposals/ticketing.md` for the argument
behind it; you don't need to in order to use it.

```bash
bash scripts/rot.sh
```

---

## Writing one

Ask the agent: *"open a ticket for X."* You should not be formatting these by
hand — that is the reason people stop writing tickets by Thursday. The `ticket`
skill in `.claude/skills/ticket/` holds the house format.

## The file

````markdown
---
id: T-0042
title: One line, present tense, says what is wrong or what should exist
status: DECIDED
tags: [pulse, defect]
anchor: ntk-pulse/build_digest.py:197
---

## What

Two or three sentences. What a reader needs to act.

## Why

The part that survives. Why this matters, what was ruled out and on what
grounds, what it cost. A future session writing a funder memo reads this
field, not the check.

## Check

```sh
grep -q "something that is only true once this is done" some/file
```
````

## Status — three states, never collapsed

| Status | Means | rot.sh |
|---|---|---|
| `PROPOSED` | Not decided. Might never happen. | skipped |
| `DECIDED` | The call is made. Nothing is built. | runs the check, expects `OPEN` |
| `BUILT` | Code exists. Nobody confirmed it does the thing. | runs the check, expects `OPEN` |
| `VERIFIED` | A check ran and passed. | **fails the run if the check fails** |
| `DISCARDED` | Decided against. Kept for the reasoning. | skipped |

Most of this project's documented errors were reading one of the middle three
as another. Every README here said "here's what we did" and meant all of them
at once.

`READY` in the output is not a status. It means a `DECIDED` or `BUILT` ticket's
check now passes — go look, and promote it if it's real.

## The check

It has to be able to fail. Roughly in order of strength:

| Form | Example |
|---|---|
| A shell assertion | a constant is present in the proxy |
| A count with a threshold | em dashes in a published digest ≤ 3 |
| A parse | `node --check` on an extracted script block |
| A fixture run | `build_digest.py` against synthetic data |
| A live fetch | `/digest/data/backstory.json` has 21 rows |
| An honest manual | `manual: the editor reads the six pairing lines` |

A ticket that pretends to a check it doesn't have is how we get back to three
documents claiming a fix that was never written. Write `manual:` instead — it
is reported, never passed, and never silently green.

**Check the outcome, not the mechanism**, where you can. T-0001 asserts that no
onramp key is dead. It does not care which of three fixes gets us there.

**Never edit a check to make it pass.** If a VERIFIED check fails, either the
code broke or the claim was always wrong. Both are worth knowing.

## Tags — one area, one kind, no others

Enforced by `rot.sh`, because a vocabulary maintained by discipline drifts and
a drifted vocabulary defeats retrieval.

**Area:** `digest` · `pulse` · `pipeline` · `backstory` · `editorial` ·
`infra` · `corpus` · `process`

**Kind:** `defect` · `feature` · `chore` · `decision`

## Anchor

One `path` or `path:line`. If it stops resolving, something moved and the
ticket needs re-reading — that is the signal that was missing for the whole
life of `build_backstory.py` writing to a tree nothing served.

## The loop

One ticket, one branch (`T-0042-short-slug`), one PR, one Netlify deploy
preview, merge, delete. Put the ID in the commit subject so `git log` answers
"why does this line exist."

If you skipped acceptance criteria going in — and you will, that's the
enthusiastic mode and it isn't worth fighting — the agent derives the check
coming out, from the diff. The question is not *did we meet the criteria*. It
is **what would I check to know this still works six months from now.**
