---
id: T-0093
title: The publish and Pulse bots rebase and retry when main moved during their run, instead of losing the run
status: VERIFIED
tags: [infra, defect]
anchor: .github/workflows/pulse-publish.yml
---

## What

Run 38775889460 ("NTK Pulse — Publish to Digest", 2026-10-15 17:16Z) built a full edition and then failed at
its last step: `git push` -> `[rejected] main -> main (fetch first)`. Something reached main during its
four minutes, and the edition was never saved; the editor's next publish a minute later succeeded, so it went
unnoticed. `pulse-publish.yml`, `pulse-scan.yml` and `pulse.yml` all ended in a bare `git push`.
`newscast.yml` already retried with a rebase after the same failure cost it 22 minutes of capture.

Fixed: all three push in a loop of three; on rejection they `git pull --rebase origin main` and try again;
if the rebase conflicts they abort it and fail red, pushing nothing. Tested against a scratch repo: a publish
racing a PR that changed another line of the same file rebased and pushed both; two writes to the same line
aborted cleanly with "rebase conflicted; nothing was pushed". `desk.yml` (retired, `ntk-desk/`) is left as is.

## Why

A publish is the editor's whole day of work, and a rejected push throws it away after every expensive step
(pairings, origins, images) has run and been paid for. Merging PRs while the editor publishes, which this
project now does routinely, makes the race likely. Ruled out: a shared concurrency group with the PR merges,
which GitHub cannot express (a merge is not a workflow run).

## Check

```sh
for f in pulse-publish pulse-scan pulse; do
  awk '/name: Commit/{f=1} f' .github/workflows/$f.yml | grep -q "git pull --rebase origin main" || { echo "$f pushes without a retry"; exit 1; }
done
```
