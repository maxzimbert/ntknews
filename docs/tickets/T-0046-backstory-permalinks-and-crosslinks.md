---
id: T-0046
title: Backstory rows have no permalink, and Digest never links to Backstory
status: VERIFIED
tags: [backstory, feature]
anchor: netlify.toml:20
---

## What

Confirmed 2026-09-28, both directions:

**No Backstory permalink exists.** `netlify.toml`'s `/backstory` rule is
an exact match (`from = "/backstory"`, no wildcard) rewriting to the SPA
shell — there's no rule and no generated file for `/backstory/<row-id>`,
so that path 404s today. `editorial/build_backstory.py` only writes
`digest/data/backstory.json` (the JSON the SPA fetches client-side); it
generates no HTML. Nothing like `build_digest.py`'s per-story static
page (`digest/YYYY-MM-DD/<slug>/index.html`, real OG/Twitter tags) exists
for a Backstory row.

**Digest never links to Backstory, in either direction it currently
could.** `build_digest.py` never reads `digest/data/backstory.json`. A
Digest story has no way to point a reader at its paired row, even though
the pairing data (`todays_pairings`) already exists and is keyed exactly
right — `build_pairings.py:179` sets `story_id = s["key"]`, the same
`key` field `build_digest.py`'s `stories` list already carries
(`build_stories_block()`, `ntk-pulse/build_digest.py:148`). The join is
free; nothing does it.

**A real sequencing bug, found while tracing this:**
`.github/workflows/pulse-publish.yml` runs `build_digest.py` *before*
`editorial/build_pairings.py`. Even after this ticket wires the
cross-link, `build_digest.py` would still be reading yesterday's
pairings — the two steps are in the wrong order for the join to ever
see today's data. Fixed by reordering (pairings now runs first) and
adding a new step for `build_backstory_pages.py` after `build_digest.py`
specifically, since it needs the permalinks that step just enriched
`backstory.json` with.

**Verified beyond the mechanical check, 2026-09-28:** ran the real chain
by hand — `build_pairings.py --mock` (fresh `todays_pairings`, no API
cost) → `GITHUB_WORKSPACE=<repo root> build_digest.py` → confirmed the
log line "6 of 6 stories cross-link to Backstory today," confirmed
`digest/data/backstory.json`'s pairings actually gained real
`story_permalink` URLs, confirmed a real generated story page
(`trump-banned-cnn-from-the-white-house.../index.html`) renders the
Backstory link box pointing at `/backstory/equality/` → re-ran
`build_backstory_pages.py` and confirmed its "In the digest" links
upgraded from the `/today` fallback to the real story permalink. Both
directions work, not just each half in isolation. Test-run content
(the mock pairings, the regenerated `digest/index.html`, the dated
edition folder) was reverted before committing — the `backstory/`
folder committed with this ticket is a fresh run against real,
already-published data, not leftover test output.

## Why

The editor's framing, direct: readers should be able to go from a
Digest story to its Backstory row and back "seamlessly and logically."
That's two things, not one — a real page to land on, and a real link to
get there.

**Scope, deliberately bounded.** This ticket is the plumbing (pages
exist, links exist, both directions), not new editorial content. A
Backstory permalink page shows exactly what `digest/data/backstory.json`
already has — milestone, `start_line` or elapsed time depending on
`stratum`, indicator, objects — the same reconciliation already done in
`design_handoff_backstory/Backstory v5 (real data).dc.html`. The
long-form narrative essay and T-0045's real quotes are explicitly not
blocked on this and not built here.

**"In the digest" on a permalink page uses only what's real today**:
`todays_pairings` for that row. `instances[]` (accumulated history) is
empty for every row in prod and stays empty — building the accumulation
mechanism is separate work, not silently faked here with placeholder
episodes.

**Where the new pages live, and why it needs a workflow change beyond
just adding a script.** `netlify.toml`'s `/digest/YYYY-MM-DD/` pattern
needs no explicit rule because Netlify serves any folder with an
`index.html` by convention — the same trick works for
`/backstory/<row-id>/` *only* if the physical file sits at
`backstory/<row-id>/index.html` off the repo root, a sibling of
`digest/`, not nested under it. `pulse-publish.yml`'s commit step
currently does `git add digest/ index.html ntk-pulse/data/last-published.json`
— a new top-level `backstory/` folder needs adding to that list or it
generates correctly and then is silently never committed.

**Stdlib only, no cross-import.** `editorial/build_pairings.py` and
`editorial/build_backstory.py` don't import from `ntk-pulse/` or each
other — matching that, the new page-generation script duplicates the
handful of color/font constants it needs rather than reaching into
`build_digest.py`.

## Check

```sh
set -e

# 1. The generator script exists, is stdlib-only, and compiles.
test -f editorial/build_backstory_pages.py
python3 -m py_compile editorial/build_backstory_pages.py
grep -qE '^import (json|os|re|sys)' editorial/build_backstory_pages.py

# 2. Run the real generator's main() against the live data and confirm it
# writes a real page per row, at the right path, with real OG tags — not a
# stub. It writes into a temp dir, not backstory/: a check must not rewrite
# tracked files (the elapsed time changes by the month — T-0081).
OUT=$(mktemp -d "${TMPDIR:-/tmp}/t0046.XXXXXX")
trap 'rm -rf "$OUT"' EXIT
OUT="$OUT" python3 - <<'PYEOF'
import importlib.util, os
from pathlib import Path
spec = importlib.util.spec_from_file_location("bbp", "editorial/build_backstory_pages.py")
bbp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bbp)
bbp.OUT_DIR = Path(os.environ["OUT"])
bbp.main()
PYEOF

OUT="$OUT" python3 - <<'PYEOF'
import json, os, re, sys
from pathlib import Path

out = Path(os.environ["OUT"])
data = json.loads(Path("digest/data/backstory.json").read_text())
rows = data["rows"]
missing = [r["id"] for r in rows if not (out / r["id"] / "index.html").exists()]
if missing:
    sys.exit(f"OPEN: {len(missing)} rows have no permalink page, e.g. {missing[0]}")

media = (out / "media" / "index.html").read_text()
assert 'og:title' in media and 'The Media' in media, "permalink page missing real OG tags"
assert 'canonical' in media.lower() or 'og:url' in media, "permalink page missing a canonical/og:url"

ukr = [r for r in rows if r["stratum"] == "fire"][0]
ukr_html = (out / ukr["id"] / "index.html").read_text()
assert "yrs" in ukr_html or "yr" in ukr_html, "fire-row permalink should show elapsed time, not a bare day count"
print(f"{len(rows)} permalink pages written, held and fire both render")
PYEOF

# 3. build_digest.py must read backstory.json and cross-link — check the
# source for the read, not just hope the wiring exists.
grep -q "backstory.json\|backstory\[" ntk-pulse/build_digest.py

# 4. Workflow ordering: build_pairings must run before build_digest in
# pulse-publish.yml, and the commit step must stage backstory/.
python3 - <<'PYEOF'
import re, sys
wf = open(".github/workflows/pulse-publish.yml").read()
# Only the real `run:` command lines count — a step's own prose comment is
# free to mention the other script by name without affecting order.
di = wf.find("run: python build_digest.py")
pa = wf.find("run: python editorial/build_pairings.py")
if not (0 < pa < di):
    sys.exit("OPEN: 'run: python editorial/build_pairings.py' must appear before "
             "'run: python build_digest.py' in pulse-publish.yml")
commit_step = wf[wf.find("name: Commit"):]
if "backstory/" not in commit_step.split("git push")[0]:
    sys.exit("OPEN: commit step does not stage the new backstory/ folder")
print("workflow order and commit staging both correct")
PYEOF
```

Note: this check runs the real generator against the real, current
`digest/data/backstory.json`, but writes into a temp directory it removes on
exit. It used to write `backstory/` in place, which made `rot.sh` rewrite
tracked pages whenever a row's elapsed time ticked over (T-0081). Writing the
live pages is the pipeline's job (`pulse-publish.yml`), not the check's.
