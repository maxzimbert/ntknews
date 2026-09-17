# Backlog

Captured 2026-09-16. Ordered by what makes the product better for the friend
cohort soonest, which is the Goal A filter (`docs/decisions.md`).

This is a working list, not a commitment. Things move.

---

## Next up — small, verified, reader-facing

**1. ~~Em-dashes are leaking~~ — rule written 2026-09-17, unmeasured.**
There was never an em-dash rule in the prompts, and the prompts themselves held
82 em dashes including throughout the worked VOICE examples. Rule added, those
examples rewritten to match. **Measure the next digest** — if it does not drop
sharply, escalate to a deterministic pass. See `docs/decisions.md`.

**2. Local news is surfacing classifieds.**
`clasificados.laopinion.com` job listings render as Los Angeles "local news."

The fix is already described in `pulse-digest-technical-state.md` as shipped.
**It was never written.** `dataType` appears in zero files in the repo, and the
local-news merge dedups by URL only — so the same listing under five URLs
passes five times. Exact-title dedup is the more reliable signal and is also
absent.

Also worth revisiting what "local" should mean: the expectation is local TV,
radio, affiliates, blogs and digital outlets, and EventRegistry's crawler does
not reliably distinguish those from directory content on the same domain.

**3. Story permalinks in the address bar.**
Every story already has a real static page with OG tags
(`digest/YYYY-MM-DD/<slug>/`). `openStory()` pushes a history entry but does
not change the URL, so sharing only works through the share button.

Hook point is `openStory()` / `closeStory()` in `digest/index.html`, alongside
the existing `navOverlay` handling. The back gesture already works and must
keep working.

Related, and the editor wants to see it before deciding: the back affordance
becoming `Digest: <category>` or a story number rather than a bare arrow.

**4. Backstory button on a digest story opens that story's pairing.**
Now possible for the first time — `todays_pairings` carries `story_id`, so the
mapping is direct. Makes Backstory discoverable from inside a story instead of
only from the tab.

Note the naming collision flagged in `docs/backstory.md`: an older per-story
"Backstory ↓" coming-soon modal already exists and is unrelated. Reconcile.

**5. Orientation cards — remove or rebuild.**
Currently the first thing a new reader sees, and they describe an April
product. Either cut them entirely or rewrite around what exists now. Cheap
either way; the decision is the work.

---

## Bigger pieces

**Expertise / beats.** A working no-account localStorage implementation is live
(`BEATS_KEY`, progression toasts). What's missing is legibility — a reader
can't tell what it is or how it works. It surfaces throughout the experience,
so this is not a Profile-tab task.

**Analytics.** GA4 is attached but the event model predates most of what now
exists. Two separate problems: deciding *what is worth tracking* against the
Goal A questions (completion rate, caught-up confidence — the north stars in
`README-digest-assembly-and-acquisition`), and then instrumenting it. Do the
first before the second.

**Journalism Atlas sourcing.** Adding independent journalists from
journalismatlas.com to Pulse's feed list. **This reverses a July decision** —
Atlas was tabled as a poor fit for Pulse v1 on the grounds that Atlas is
creator-journalist analysis while Pulse's job is right-now reporting. Worth
re-examining that reasoning explicitly rather than quietly overriding it: it
may have been right, or the product may have changed.

**Full-body article sourcing beyond EventRegistry.** Unexplored: GDELT
(Jigsaw), Microsoft AI Marketplace for Publishers, Yahoo Scout. World News API
was evaluated and dismissed, but on queries that may not have been
representative — worth one more pass before ruling it out. EventRegistry's real
value is paywall/bot-blocked body fetching; any replacement has to clear that
bar, not just return headlines.

---

## Tweaks and open questions

- **Backstory should be more visual.** Currently type-only.
- **Backstory cards should link to what they cite.** Objects carry title,
  author, year and source but no URL — the matrix has no link column, so this
  needs a data decision before a UI one.
- **How objects are chosen is opaque.** `pick()` in `build_backstory.py` takes
  the two oldest pre-1981 and two most recent post-1981, automatically. Nobody
  selected them. Hand-curation is the documented upgrade path
  (`backstory-matrix-triage.md`), and it is not blocking.
- **Backstory categories feel untethered from the digest.** Preference is for
  something briefer and more clearly tied to the day's stories — a one or
  two-word unit.
- **Digest prompt tuning.** Ongoing. The em-dash item above is one instance of
  a broader "make the four sections as good as they can be" thread.
- **Still Counting rows are machine-unreachable.** Seven of 21 rows have no
  sub-genres, so the classifier can never assign them. Editor-assignable in
  Slice 5. Never actually decided — see `docs/backstory.md`.

---

## Backstory slices still open

See `docs/backstory.md` for the full plan. Slices 1–4 shipped 2026-09-16.

- **Slice 5** — Pulse tagging control, so a bad row assignment can be
  overridden before publish. Also the replacement for the disabled Backstory
  tab.
- **Slice 6** — Register 4 narratives. All 21 rows currently have none, which
  is why every detail view falls back.

**Before either: run `build_pairings.py` against the real models once.** The
plumbing is verified; the output quality has never been seen.
