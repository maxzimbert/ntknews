---
id: T-0081
title: Running the rot suite rewrites tracked Backstory pages, because T-0046's check builds them in place
status: VERIFIED
tags: [process, defect]
anchor: docs/tickets/T-0046-backstory-permalinks-and-crosslinks.md
---

## What

On 2026-10-08, `bash scripts/rot.sh` on a clean tree left
`backstory/israel-hezbollah/index.html` modified: its `<section class="elapsed">`
went from "2 yrs 11 mo" to "3 yrs 0 mo". The cause was T-0046's check, which ran
`python3 editorial/build_backstory_pages.py` and so rewrote every page under
`backstory/` with today's date. It was the only check doing that (measured the
same day: one modified file after a full run, nothing else). The fix: T-0046's
check now calls the same generator's `main()` with `OUT_DIR` pointed at a temp
directory and runs its assertions there. Same live data, same assertions.

## Why

A check is supposed to be a read-only assertion. One that writes tracked files
turns "run the rot detector" into "change the site": the diff ends up in the
next commit, made by whoever happened to run the suite, with no ticket behind
it, and a stale elapsed time can be committed over a fresh one or the other way
round. It also confuses anyone using `git status` to see what their own change
touched. That is exactly the "no diff, no way to know which copy was newer"
drift this repo moved off the GitHub web editor to escape.

T-0046's old note said it left `backstory/` on disk on purpose, so that a
check would never destructively reset generated output. That concern still
holds, and a temp directory satisfies it: the check neither resets nor rewrites
anything real. Writing the live pages is `pulse-publish.yml`'s job.

Ruled out: running the generator and then `git checkout backstory/` afterwards.
That would throw away an editor's uncommitted work in that folder, which is
the destructive reset T-0046's note warned about. Also ruled out: deleting
the generator step and asserting only on the committed pages. That would stop
testing that the generator still works against today's data, which weakens the
check.

## Check

```sh
set -e
# Outcome: running T-0046's check (the one that ran the page generator)
# leaves the working tree exactly as it found it.
before=$(git status --porcelain --untracked-files=all)
body=$(awk '/^## Check/{c=1;next} c && /^```sh/{f=1;next} f && /^```/{exit} f' \
  docs/tickets/T-0046-backstory-permalinks-and-crosslinks.md)
bash -e -c "$body" >/dev/null 2>&1 || { echo "OPEN: T-0046's own check fails"; exit 1; }
after=$(git status --porcelain --untracked-files=all)
if [ "$before" != "$after" ]; then
  echo "OPEN: T-0046's check changed the working tree:"
  diff <(echo "$before") <(echo "$after") || true
  exit 1
fi

# Guard: no live ticket check runs the page generator as a script, which
# would write straight into backstory/.
for f in docs/tickets/T-*.md; do
  case "$(awk '/^status:/{print $2; exit}' "$f")" in DISCARDED|PROPOSED) continue;; esac
  if awk '/^## Check/{c=1;next} c' "$f" | grep -qE 'python3? +editorial/build_backstory_pages\.py'; then
    echo "OPEN: $f runs build_backstory_pages.py in place"; exit 1
  fi
done
```
