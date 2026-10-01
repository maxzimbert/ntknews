#!/usr/bin/env bash
# Publish the `staging` branch to maxzimbert/ntknews-staging (GitHub Pages).
#
#   bash scripts/stage.sh
#
# The `staging` branch of this repo is main plus whichever PRs are being tried
# together. This script refreshes it from main (so Pulse's bot-committed data
# in ntk-pulse/data/ is current), then force-pushes a single-commit copy of it
# to the staging repo with .github/ removed, so no bots, crons or publish
# workflow ever run there. Pulse's Publish button is separately disabled on
# any host but the live one (T-0051).
#
# Adding a PR to staging:  git checkout staging && git merge origin/<branch>
# Removing one: rebuild staging from main and merge the ones you still want.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
ROOT=$(pwd)

STAGING_REPO=maxzimbert/ntknews-staging

git fetch -q origin
git show-ref --verify -q refs/remotes/origin/staging \
  || { echo "no origin/staging branch - create it from main first"; exit 1; }

WT=$(mktemp -d); OUT=$(mktemp -d)
cleanup(){ cd "$ROOT"
           git worktree remove --force "$WT" 2>/dev/null || true
           rm -rf "$WT" "$OUT"
           git worktree prune
           git branch -D stage-tmp -q 2>/dev/null || true; }
trap cleanup EXIT

git worktree add -q -B stage-tmp "$WT" origin/staging
if ! git -C "$WT" merge -q -m "Merge origin/main into staging" origin/main; then
  echo "merging main into staging conflicts. Resolve on the staging branch, push it, rerun."
  exit 1
fi
git -C "$WT" push -q origin HEAD:staging

git -C "$WT" archive HEAD | tar -x -C "$OUT"
rm -rf "$OUT/.github"

SHA=$(git -C "$WT" rev-parse --short HEAD)
cd "$OUT"
git init -q -b main
git add -A
git -c user.name="$(git -C "$WT" config user.name)" \
    -c user.email="$(git -C "$WT" config user.email)" \
    commit -q -m "staging @ $SHA ($(date -u +%Y-%m-%dT%H:%MZ))"
git remote add origin "https://github.com/$STAGING_REPO.git"
git push -q --force origin main

echo "staged $SHA -> https://maxzimbert.github.io/ntknews-staging/ntk-pulse/pulse.html"
