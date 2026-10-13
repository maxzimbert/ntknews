#!/usr/bin/env bash
# Build the staging site from a checkout of the `staging` branch.
#
#   bash scripts/stage_build.sh SRC_DIR OUT_DIR SHA
#
# Used by scripts/stage.sh (from the laptop) and by the staging repo's own deploy workflow
# (scripts/staging-pages.yml, which runs in maxzimbert/ntknews-staging), so the two cannot drift.
set -euo pipefail
SRC=$1; OUT=$2; SHA=$3

git -C "$SRC" archive HEAD | tar -x -C "$OUT"
rm -rf "$OUT/.github"

# GitHub Pages serves this copy from a subpath (/ntknews-staging/) with none
# of Netlify's rewrites, so root-absolute links and fetches and production's
# absolute permalinks would all leave the staged site. Point them back at it,
# in the staged copy only. /backstory, /today and /me are Netlify rewrites of
# the app shell, so they become the shell itself.
BASE=/ntknews-staging
find "$OUT/digest" "$OUT/backstory" "$OUT/index.html" \( -name '*.html' -o -name '*.json' \) -print0 \
  | xargs -0 perl -pi -e '
      s#https://ntknews\.org/#https://maxzimbert.github.io/ntknews-staging/#g;
      s#href="/(?:backstory|today|me)"#href="'$BASE'/digest/index.html"#g;
      s#href="/(?!/|ntknews-staging/)#href="'$BASE'/#g;
      s#fetch\(\x27/digest/#fetch(\x27'$BASE'/digest/#g;
    '

# Pages runs Jekyll unless told not to. Any .md with front matter and a stray
# "{{" (a ticket quoting CSS, say) fails the whole build, and nothing here needs
# Jekyll. Found 2026-10-06: T-0078 broke every staging build.
touch "$OUT/.nojekyll"

# The staging repo deploys itself (Pages source: GitHub Actions) and checks every five minutes whether
# the staging branch has moved, so a staging run started from Pulse reaches the site with no laptop.
# Its only workflow is this one; nothing from this repo's .github runs there.
mkdir -p "$OUT/.github/workflows"
cp "$SRC/scripts/staging-pages.yml" "$OUT/.github/workflows/deploy.yml"
echo "$SHA" > "$OUT/.staged-sha"
