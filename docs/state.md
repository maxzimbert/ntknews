# Current state

**Partially re-verified 2026-09-17.** Open defects now live in `docs/tickets/`,
where a check runs against them daily. What remains here is narrative state.
This is the fastest-rotting document in `docs/`. If the date above is old,
re-verify before relying on it.

Anything here that matters enough to guard should be a ticket, not a
paragraph.

---

## What is live right now

- **The digest contains six stories**, published 2026-09-16T18:12Z. The publish
  path works end to end: dated edition, six permalinks with OG tags, six
  decoded images, archive index, and the root landing-page hero all regenerated
  correctly from one button press. The prior edition (2026-09-14) was a single
  story.
- **Backstory has not been published since 2026-09-14** and is untouched by
  digest publishes — the two are decoupled by design, on separate buttons and
  separate commits. All six rows still carry empty narratives and
  `last_rewritten_at: null`; no Register 3 rewrite pass has ever been run. This
  is why the tab reads as out of date: not a wiring fault, an unpopulated
  feature. See defect #3 and `docs/backstory.md`.
- **v14 editorial prompts are deployed** in `ntk-pulse/pulse.html`. The July
  handoff's open item "v14 has not been deployed yet" is **resolved**.
- **URL routing works.** `/today`, `/backstory`, `/me` all rewrite to
  `digest/index.html`.
- **The Desk is retired**, manual-dispatch only, as decided.
- **Backstory renders 21 library rows**, all with empty narratives, plus six
  `todays_pairings` entries. Corrected 2026-09-17; this line said six rows.

---

## Resolved — READMEs that are now stale

`ReadMes (post 9:10)/ntk-url-routing_readme.md` lists two "manual edits still
outstanding." **Both are done:**

- `pulse.html:1167` — `GH_BACKSTORY_PATH = 'digest/data/backstory.json'` ✅
- `pulse-publish.yml` — commits `git add digest/ index.html …` ✅

---

## Open defects

**Moved to `docs/tickets/`.** They are no longer listed here, because listing
them here is what let four of the six go stale inside two days while this
document still asserted them.

```bash
bash scripts/rot.sh
```

| Ticket | |
|---|---|
| `T-0001` | The Today overview ships with onramp keys that do not resolve |
| `T-0002` | Pulse reads two-day-stale data when served from Netlify |
| `T-0003` | Every Backstory narrative is empty |
| `T-0004` | Em dashes reach published output |
| `T-0005` | The Haiku model string differs between pipeline stages |
| `T-0006` | Two Netlify sites build from this repo |
| `T-0007` | The Backstory generator writes the file the app reads — **verified, guarded** |

Closed on 2026-09-17 by measurement, having been listed here as open: the
Today overview CSS class (`digest/index.html:2017` carries it), the Backstory
generator's output path (`editorial/build_backstory.py:31` writes
`digest/data/`), the pairings renderer (`todays_pairings` and `.bsr-pairline`
are both live), and the drifted second copy of the editorial prompts
(`ntk-production.html` no longer exists).

Still open but too small to ticket, tracked in `docs/backlog.md`:
`handleSubscribeClick()` on permalink pages, five TLS-blocked Substack feeds,
and two feeds failing XML parse.

---

## Contradictions between READMEs, resolved

Recorded so they don't get re-litigated:

| Question | Answer |
|---|---|
| Is the story-list `i === 0` image gating a bug? | **No — it's the intended design.** `README-ntk-pulse-automation.md` lists it as an open bug; `ntk-pulse-sonnet5-migration-and-permalinks.md` §6 records Max explicitly clarifying that only story #1 gets the hero treatment in the list view, and that any story with an image shows it in the reading view. The latter is correct. Code at `digest/index.html:2277,2282` matches it. |
| Which app file is canonical? | `digest/index.html`. Not `digest/v2/index.html`. |
| Is v14 deployed? | Yes, in `pulse.html`. |
| Which Backstory design is the plan? | Part 2 (per-story pairings). See `docs/backstory.md`. |
