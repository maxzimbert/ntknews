# Current state

**Re-verified 2026-10-01**, after a long session of Backstory redesign work.
Open defects live in `docs/tickets/`, where a check runs against them daily.
What remains here is narrative state. This is the fastest-rotting document in
`docs/`. If the date above is old, re-verify before relying on it — run
`bash scripts/rot.sh` first thing, don't trust this file's claims about
ticket status without it.

Anything here that matters enough to guard should be a ticket, not a
paragraph.

**Other sessions are active in this repo concurrently.** Confirmed multiple
times during the 2026-09-22 to 2026-10-01 session this file was last rewritten
from: tickets, PRs, and even a local checkout branch switch happened from
outside this session while it was running. `git pull --rebase` before
touching anything, and don't assume a ticket's status is what the last
session's summary said — check `rot.sh`.

---

## Session memo, 2026-09-22 to 2026-10-01 — for whoever picks this up next

### What got built, in rough order

**Headline quality (T-0038, T-0042, both merged).** `triage.py`'s headline
rubric and Pulse's punch-up button were both reasoning from other outlets'
headlines alone — `summary` and enriched article `body` existed on the data
but were never read. Both now use them; T-0042 additionally added a free
page-scrape fallback (`triage.py`'s `fetch_body()`) so triage gets real
article text even when only one outlet has covered a story, at zero API
cost beyond what was already being spent.

**Two small Pulse features (T-0040, T-0041, both merged).** A "scoop
import" path — paste a URL, certify it into the lineup — for single-outlet
stories that will never clear the normal corroboration bar. And one new
clause in `VOICE_REF` (`pulse.html`) aimed at making Jefferson output read
less mechanical; this one is an editorial judgment call, not a mechanical
fix, and wasn't independently re-confirmed by a second reader after merge —
worth an editorial gut-check on real output if it hasn't had one yet.

**The Backstory redesign — the bulk of the session.** The editor had a
design handoff (`design_handoff_backstory/` — **local-only, never
committed, confirmed empty via `git ls-files` as of this writing; ask the
editor to re-share it if it's gone**) describing four new screens (thread
list, placard/object carousel, row permalink, object page). What actually
shipped against that design:

- **T-0046 (merged):** real static pages at `/backstory/<row-id>/`, one
  per row, real OG tags, no `netlify.toml` change needed (Netlify serves
  any folder with an `index.html` by convention). Cross-links both
  directions: a Digest story that paired to a row today links to it, and
  the row's page links back to the specific paired story (not just
  `/digest` generally). Found and fixed a real sequencing bug in
  `pulse-publish.yml` along the way — `build_pairings.py` now runs before
  `build_digest.py`, not after, so the cross-link can actually see
  same-day data.
- **T-0053 (merged):** those pages now carry the real NTK logo (reused
  the existing data-URI asset already proven on two other dark headers in
  this codebase), not placeholder text.
- **T-0047 (merged, partial):** 13 of 14 `held`-row indicator numbers
  checked against their actual named source (Gallup, Pew, NOAA, FBI,
  Census, BLS, DMDC, FAS, Taiwan's MND) via real search, not model recall
  — five were genuinely wrong or stale, not just imprecise, and got
  corrected. **`power` (the "other party threatens the nation" figure) is
  still `verified: false` on purpose** — real effort didn't turn up one
  citable current figure for that exact framing. Don't force a number
  there without doing the actual lookup.
- **T-0049 (merged):** the *live in-app* Backstory tab — which T-0046 never
  touched — now knows fire rows from held rows. Before, every row led with
  the same bare, duplicated day count regardless of whether it had an
  earned `start_line`; that was the original confusion that kicked off this
  whole thread. CI caught a real mistake on first push here (two new CSS
  rules at an off-scale `14px`, violating T-0029's locked type scale) —
  fixed before merge, worth remembering that `digest/index.html` changes
  need `bash scripts/rot.sh` run locally against the *actual* branch, not
  just eyeballed.
- **T-0045, T-0048 — specs only, not built.** T-0045 is the mechanism for
  real, sourced one-sentence pull-quotes per object (the placard screen
  needs this; hand-researching 8 of them for a mockup this session showed
  it needs real search/fetch access, not a bare model call, since working
  from memory got at least one wrong). T-0048 is the content-model gap for
  the object page (4D) — two paragraphs of real context, a "where it
  stands now," an outbound source URL, none of which exist in the schema
  yet. Both are real scoping work already done; neither has an
  implementation.
- **Not touched at all, still fully in scope for later:** the long-form
  narrative essay (Register 3/4 in the old framing). Every row's
  `narrative` is still empty. This was explicitly out of scope for every
  ticket this session touched, by direct instruction — it's the one piece
  of the original design ambition nobody has started.

**A staging environment now exists for Pulse — not built by this session,
found already merged partway through it (T-0051, T-0052).** Pulse keeps
everything in `localStorage`, which is origin-scoped, and the editor's real
working Pulse is at `maxzimbert.github.io`, a different origin than any
Netlify preview URL — so Netlify previews were always useless for testing
Pulse changes (empty storage). `scripts/stage.sh` now publishes a `staging`
branch (main plus whichever PRs are being tried) to a separate repo,
`maxzimbert/ntknews-staging`, served at the same GitHub Pages origin as the
real Pulse, so it shares real `localStorage`. **It does not auto-update on
merge — it's a manually-run script.** T-0051 locks down Pulse's Publish
button so it only works from the two real hosts, specifically so a staging
copy can never accidentally publish to production.

**Docs added or updated this session:** `docs/voice.md` (editorial rules —
the register ladder, headline rubric, Jefferson prompts, all consolidated
from scattered prompt strings) and `docs/design-system.md` (visual rules —
the type scale, color tokens, the certainty ladder) both now exist and are
referenced from `CLAUDE.md`'s own doc table. `docs/backlog.md` has a new
entry on the Pulse staging gap, written before T-0052 was discovered
already solving it — that entry is now historical, not a live backlog item.

### Loose ends worth a look, not urgent

- **T-0040 and T-0051 both report `READY`** (`bash scripts/rot.sh`) —
  their checks pass but nobody has promoted them to `VERIFIED` yet. Cheap
  to close out.
- **T-0011** (Backstory cards are indistinguishable when two stories share
  a row) is still `OPEN` and adjacent to all the stratum/list-view work
  this session did — worth a look now that `renderBackstoryTab()` has
  already been touched once.
- **T-0012** (seven `fire` rows carry no sub-genres, unreachable by the
  classifier) is still `OPEN` — unrelated to this session's work but
  sitting in the same file.

### Recommended next steps, roughly in order

1. **T-0050** (tagging control → Backstory `instances[]`, i.e. "Earlier
   episodes") — spec'd (`DECIDED`) by another session, not built. This is
   the mechanism that makes `bsrEpisodesHtml()`'s permalink-aware rendering
   (already live, already correct, just fed nothing) actually show
   something. High leverage, already scoped.
2. **T-0045** (placard quotes) — the mechanism question (Object Matrix
   spreadsheet column vs. a `build_backstory.py` generation step) still
   needs a decision before building. Whatever does the sourcing needs real
   search/fetch, proven necessary this session.
3. **T-0048** (object page / 4D content) — bigger writing lift than T-0045,
   real editorial content across 56 objects. Probably wants the editor
   more directly in the loop than a Claude-alone pass.
4. **T-0047's `power` indicator** — small, bounded, already has a clear bar
   to clear (one citable current figure for the framing), just needs
   someone to actually find it or decide the framing itself should change.
5. **The narrative essay** — the biggest remaining piece of the original
   design ambition, and the one with no ticket yet. Worth a real
   conversation with the editor about scope before starting (what Register
   3/4 actually becomes, given the rest of the redesign is now mostly
   live) rather than assuming the old plan still holds.

---

## Resolved — READMEs that are now stale

`ReadMes (post 9:10)/ntk-url-routing_readme.md` lists two "manual edits still
outstanding." **Both are done:**

- `pulse.html:1167` — `GH_BACKSTORY_PATH = 'digest/data/backstory.json'` ✅
- `pulse-publish.yml` — commits `git add digest/ index.html …` ✅

---

## Contradictions between READMEs, resolved

Recorded so they don't get re-litigated:

| Question | Answer |
|---|---|
| Is the story-list `i === 0` image gating a bug? | **No — it's the intended design.** `README-ntk-pulse-automation.md` lists it as an open bug; `ntk-pulse-sonnet5-migration-and-permalinks.md` §6 records Max explicitly clarifying that only story #1 gets the hero treatment in the list view, and that any story with an image shows it in the reading view. The latter is correct. Code at `digest/index.html:2277,2282` matches it. |
| Which app file is canonical? | `digest/index.html`. Not `digest/v2/index.html`. |
| Is v14 deployed? | Yes, in `pulse.html`. |
| Which Backstory design is the plan? | Part 2 (per-story pairings). See `docs/backstory.md`. |
