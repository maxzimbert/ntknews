---
id: T-0052
title: There is no place to try unmerged Pulse and Backstory work against the real Pulse state
status: VERIFIED
tags: [infra, feature]
anchor: scripts/stage.sh
---

## What

`scripts/stage.sh` publishes the `staging` branch (main plus PRs being tried
together) to `maxzimbert/ntknews-staging`, served at
`https://maxzimbert.github.io/ntknews-staging/`. Pulse there runs on the same
origin as the live Pulse, so it shares the editor's real `localStorage`
(lineup, keys, vocabulary), which a Netlify preview cannot. Publish is
disabled there (T-0051). The repo has no `.github/`, so no bots or workflows
run on it.

Backlog origin: `docs/backlog.md`, "A staging/dev environment for Pulse."

## Why

Pulse PRs (T-0040, T-0041) had shipped on code review plus post-merge
checking, because Netlify previews are a different origin and open Pulse with
empty storage. Ruled out: serving previews from a `gh-pages` branch of this
repo, which means moving the live Pulse's Pages source off `main`. Ruled out:
retargeting Pulse's publish per host, since staging does not need to publish
and a second publish path is more to keep correct.

Costs and hazards, so nobody rediscovers them: the shared origin is the point
and also the risk. A staged change to how Pulse stores the lineup or
vocabulary writes to the same keys as the real Pulse, so back up
`localStorage` before testing anything that changes storage. Generation and
Recraft calls in staging use the editor's real keys and cost real money. The
staging repo is public and holds a copy of this repo's tracked files.
`staging` needs refreshing from main because the bots commit data every 20
minutes; the script does this each run.

Verified 2026-09-29: deployed with #38 (T-0046), #39 (T-0047) and #45
(T-0051) merged into `staging`; Pages built; Pulse, `/backstory/gaza/` and the
data files all served 200; in a browser on the staged URL, `publishToDigest()`
returned the disabled message with zero fetch calls. The check proves the
deployed copy carries the guard; the browser test is what showed the button
is dead.

## Check

```sh
set -e
U=https://maxzimbert.github.io/ntknews-staging/ntk-pulse/pulse.html
curl -fsS "$U" | grep -q "function pulseMayPublish"
```
