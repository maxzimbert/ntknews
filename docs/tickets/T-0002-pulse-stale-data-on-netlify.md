---
id: T-0002
title: Pulse reads two-day-stale data when served from Netlify
status: DECIDED
tags: [infra, defect]
anchor: netlify.toml:2
---

## What

`netlify.toml`'s build-skip rule excludes `ntk-pulse/data/`. `pulse-scan` and
`pulse` write **only** into that folder, so every bot commit is skipped and
never deploys. Netlify's copy of `clusters.json`, `lineup.json` and
`window.json` freezes until some commit touches a path outside the exclusions —
in practice, only a publish.

Measured 2026-09-16: Netlify's lineup was assembled 09-14T09:39 with 78
entries; GitHub Pages' was 09-16T16:28 with 84.

## Why

This corrupts editorial judgement silently. The tool works. It renders. It
recommends stories. They are just two days worse than the ones available, and
nothing in the interface says so.

It also produced a documented misdiagnosis: `pulse.html` is **byte-identical**
across both hosts, so comparing the HTML and concluding the hosts are
equivalent is the exact mistake that hid this for days. Verifying the artifact
is not verifying the system. That sentence is the reason this whole ticketing
system exists.

**Do not fix this by removing the ignore rule.** It was written to stop a
deploy flood — roughly 72 builds a day — that had already consumed ~250 build
credits. Restoring the flood to fix the staleness trades one real cost for
another.

The real fix is making Pulse fetch its data from GitHub's contents API rather
than by relative path, so it reads the source of truth regardless of which host
served the page. Pulse already does exactly this for backstory
(`GH_BACKSTORY_PATH`, `ntk-pulse/pulse.html:1177`), so the pattern exists in
the file and does not need inventing.

Until then: author in Pulse from GitHub Pages, which deploys every commit.
Note that this conflicts with retiring Pages, which is recommended elsewhere —
Pages cannot be shut off before this ticket closes.

## Check

```sh
if grep -qE "fetch\('data/(clusters|lineup|window)\.json" ntk-pulse/pulse.html; then
  echo "pulse.html still fetches pipeline data by relative path:"
  grep -nE "fetch\('data/(clusters|lineup|window)\.json" ntk-pulse/pulse.html
  exit 1
fi
grep -q "api.github.com/repos" ntk-pulse/pulse.html
```
