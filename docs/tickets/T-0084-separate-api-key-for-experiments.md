---
id: T-0084
title: Experiments and branch runs spend from their own Anthropic key, with a spend limit, in a separate Console workspace
status: DECIDED
tags: [infra, chore]
anchor: .github/workflows/pulse-publish.yml
---

## What

Backlog, not urgent. Today there is one Anthropic key for everything. Measured 2026-10-12 on main
(3a1cae5): the repo has exactly one Actions secret, `ANTHROPIC_API_KEY`, referenced by
`pulse-publish.yml` (3), `pulse.yml` (2), `desk.yml` (2), `pulse-scan.yml` (1) and `newscast.yml` (1).
Pulse holds its own copy in the editor's browser (`SETTINGS.antKey`, 6 uses: `ai()`, `aiSearch()`).
A workflow dispatched on a branch (`gh workflow run pulse-publish.yml --ref <branch>`) runs with the
same secret as a production publish.

Make a second key in its own Console workspace with a monthly spend limit, store it as a second
secret (for example `ANTHROPIC_API_KEY_LAB`), and have every run that is not a production run use it:
branch dispatches of `pulse-publish.yml` (select the secret by `github.ref`), the spine-lab style
workflows, and any rerun made to test a change.

## Why

The credit ran out twice in four days, both times from experiments, not from the product:

- 2026-10-09: 11 demo publish runs on `demo-auto-categories` between 17:53 and 19:57 UTC, then the
  spine lab build (about 1.86M input tokens and 83 web searches in one run). The balance hit zero
  mid-evening; the next demo run failed every call with HTTP 400 "credit balance is too low" and still
  showed green.
- 2026-10-12: the T-0083 branch's second run (about 1.0M input tokens, 52 searches) ran out mid-run.
  Every story's Backstory step failed and the run wrote empty pairings to the branch. On main, the
  same failure would have replaced a good Backstory with an empty one (T-0083 now keeps the previous
  file when that happens, but a spent balance also stops the digest's own Haiku calls).

A shared balance means a lab run can take down the next production publish, and the Console cannot
show which spend was the product and which was a test, so the editor could not tell why usage spiked
(he asked on 2026-10-12). Web search is most of the cost: search results are fed back into the
model's context, so one research call reads hundreds of thousands of tokens. T-0083 cut research to
six searches per call for the same reason.

Downstream impact, to plan before doing it:

- The stack keeps one key per service: Anthropic (Actions secret and Pulse's browser setting),
  Netlify's function env (`NEWSAPI_KEY`, `EXA_API_KEY` in `netlify/functions/news.js`), Recraft
  (`SETTINGS.recraftKey` in Pulse) and the GitHub token Pulse publishes with (`SETTINGS.ghToken`).
  Only the Anthropic key changes here, but every place it is read has to be decided.
- Pulse has one key field. Either it stays the production key (and the ask box, compose and revise
  keep spending from production), or it gains a second field for experiments. Staging Pulse and
  production Pulse share localStorage (same github.io origin), so a key set on one is set on both.
- Workflows on schedules (`pulse.yml`, `pulse-scan.yml`, `newscast.yml`) stay on the production key.
- Never commit either key.

Ruled out: lowering the production key's own limit, which caps the product along with the tests;
running experiments locally, which needs the key on the laptop (no key is set there today).

## Check

```sh
# a branch or lab run cannot reach the production key: pulse-publish chooses the lab secret off main
grep -q "ANTHROPIC_API_KEY_LAB" .github/workflows/pulse-publish.yml \
  || { echo "OPEN: pulse-publish.yml has no lab key for branch runs"; exit 1; }
echo "manual: the lab key's workspace has a monthly spend limit set in the Anthropic Console"
```
