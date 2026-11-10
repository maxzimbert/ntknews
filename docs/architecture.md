# Architecture — how NTK actually runs

Verified against the repo **2026-09-15**. Every path and schedule below was
read out of the actual file, not recalled.

---

## The shape of it

There is no server. Netlify serves static files from `main`, with one
serverless function for the two things that genuinely can't run in a browser.
Everything else is either a scheduled GitHub Action writing JSON into the repo,
or a browser tool calling the Anthropic API with the editor's own key.

```
  RSS feeds (97)
        │
        ▼
  ┌─────────────────────────────────────────────┐
  │  GitHub Actions — two schedules              │
  │                                              │
  │  pulse-scan.yml    every 20 min   no LLM     │
  │    ingest → cluster → triage → promote       │
  │                                              │
  │  pulse.yml         every 4 hours  + Sonnet   │
  │    ingest → cluster → triage →               │
  │      ledger → assembly                       │
  └─────────────────────────────────────────────┘
        │  writes ntk-pulse/data/*.json
        ▼
  ┌─────────────────────────────────────────────┐
  │  Pulse — ntk-pulse/pulse.html                │
  │  The CMS. Runs in the editor's browser.      │
  │  Reads clusters.json + lineup.json.          │
  │  Generates the four sections via direct      │
  │  Anthropic calls (key in localStorage).      │
  │  "Publish" commits lineup-publish.json       │
  │  through GitHub's Contents API.              │
  └─────────────────────────────────────────────┘
        │  that commit IS the trigger
        ▼
  ┌─────────────────────────────────────────────┐
  │  pulse-publish.yml → build_digest.py         │
  │  The only thing that writes live site files. │
  └─────────────────────────────────────────────┘
        │
        ▼
  digest/index.html  ·  index.html  ·  digest/YYYY-MM-DD/…
```

---

## The two scheduled pipelines

They share a concurrency group so they never run at the same instant, but they
share no logic.

### `pulse-scan.yml` — every 20 minutes, no LLM spend

`ingest.py` → `cluster.py` → `triage.py` → `lineup_promote.py`

Keeps the Stream fresh and grows the Lineup candidate pool. Triage uses Haiku
against a cache, so routine runs are cheap.

### `pulse.yml` — every 4 hours, Sonnet spend

Everything above, plus `ledger.py` → `assembly.py`. This is where real
editorial selection happens. The ledger step is skippable on manual dispatch
via the `run_ledger` input. The commit step is `if: always()` — deliberately,
so a failure partway through still persists whatever was produced.

### `desk.yml` — manual dispatch only

The retired Desk system. Schedule disabled to conserve API credits. Do not
re-enable.

---

## Backstory: build, review, publish (T-0114, 2026-11-02)

Each story gets its own Backstory page, built and reviewed in Pulse before publish, to the contract at the top of
`docs/backstory.md`. Ticket: T-0114 (it supersedes T-0109 and T-0113). Decisions: `docs/decisions.md`, 2026-11-02.

```
  Pulse: Generate Jefferson  ──►  the story's Backstory builds itself (or "Build Backstory for every story")
        │  bsxBuild → bsxCompose: Haiku names the history at three scopes (narrow, middle, wide); the library is
        │  shortlisted for each (matrix, approved candidates, this story's research, and at most 10 items from the
        │  editor's Are.na library, T-0115); Sonnet picks one scope and says why, and writes the ten components.
        │  Each milestone names the story's words it ties to (catTiesOk) or is left out, with the reason; none is
        │  dated within 45 days of the story. Each part is checked against the contract and repaired once; a
        │  milestone line still breaking a rule is rewritten once more, then kept and flagged; a filler document
        │  note is left blank. The row is proposed from the story and filed (the editor can type another: it moves
        │  only the shelf and the chart). A thin build (fewer than 3 connected milestones) rebuilds once on the next
        │  wider scope; still thin, one web search on its gaps and one rebuild (T-0117). Then one Sonnet call
        │  reviews the page: ready, or needs you with up to three concerns. A weak page is held (held: true) until
        │  the editor clicks Ship anyway (bs_edits.ship_anyway). A row with no trend line gets one search for one
        │  (once per row per day).
        ▼  saved to ntk-pulse/data/backstory-draft.json on the branch Pulse is served from, via the Contents API
  Pulse, the review (under each story's preview)
        │  Direct the research (one web search, then re-choose the history) · results listed, any added to the
        │  page as found · revise one part by prompt · edit words · remove · also add to the Object Matrix.
        │  The editor's direction wins: what the editor directed is never repaired. All edits ride on the Lineup
        │  story (bs_edits) and are laid over every rebuild. Research writes editorial/research-ledger.json.
        ▼  Publish (live Pulse only)
  pulse-publish.yml
     backstory_draft.py apply   each story ships the page built for it if its bs_hash still matches; a story
                                not built, or changed since, ships no Backstory. A held page ships none
                                ("held: weak, not released") unless the editor shipped it anyway. Nothing is
                                chosen at publish.
                                Row trend lines found in Pulse (ship.row_indicators) go onto the rows.
     build_digest.py → build_backstory_pages.py   one static page per story: /backstory/s-<story id>/
     graduate_finds.py → export_for_pulse.py      documents the editor added to the Object Matrix join it
                                                  (primary sources; news from the 91 NTK_SOURCES publishers,
                                                  marked in column P, Source Kind); the pool is rebuilt
```

- **Fingerprints.** Pulse hashes exactly what a page is built from: headline, description, Truths, the row, and the
  editor's edits (`bs_hash`; `bs_text_hash` without the edits). Python only compares them. An edit to another
  section, or a trend line found for the row, does not stop a built page from shipping.
- **News reports** may stand in only when no primary source exists, only from `NTK_SOURCES`
  (`netlify/functions/news.js`; Pulse's copy is `NTK_PUBLISHERS`, Python reads the original through
  `editorial/publishers.py`), labelled with the reason.
- **The editor's Are.na library** (T-0115) is refreshed by hand, never in CI:
  1. `python3 editorial/arena_pull.py` pulls the editor's channels into `editorial/arena.db` (gitignored). The token
     is in `~/.config/arena/token`.
  2. `python3 editorial/export_library.py --fetch-dates` writes `ntk-pulse/data/arena-library.json`. It keeps what
     can be opened and dated, and flags paywalls.
  3. Commit the JSON and `editorial/arena-dates.json`.

  Pulse loads the JSON beside the pool. Its items bypass the publisher rule and carry `source_kind: 'library'`, so
  readers see no label, and they never join the Object Matrix.
- **The reader app** (`digest/index.html`, `bsrStoryRow`) draws a pairing that carries `composed` as the story's own
  page: title, contest, stakes, chart, timeline, the case; the card's foot names the row. No day counters anywhere.
  `?draft` lays the branch's draft over the published file, showing what publish will ship.
- **Staging never publishes.** Staging Pulse cannot publish; its drafts, ledger and edits live on the `staging`
  branch, and a prod publish reads only `main`'s draft.
- **Retired, still on disk for older tickets' checks:** `build_pairings.py` (the classifier), `build_origins.py`,
  `compose_category.py`. Nothing runs them.
- **Costs.** A build is three or four model calls (naming, composing, repair when needed, the self-review; T-0117
  added the review and a second line rewrite only when a line still breaks a rule). A thin one adds one compose on
  the wider scope (no second naming call), and only if still thin a web search and a rebuild, once per subject in 30 days.
  The tests for the build run in node with stand-in replies: `node scripts/test_pulse_backstory.js`. Directed research is one web search plus one call (an identical
  direction within 30 days is skipped unless the editor forces it). A new row's trend line is one web search.

---

## The pipeline scripts

All in `ntk-pulse/`.

| Script | Does | Model |
|---|---|---|
| `ingest.py` | Polls 97 feeds into `data/window.json` (6-hour window). Lenient XML recovery for malformed feeds — retry only, never rewrites well-formed XML. | — |
| `cluster.py` | IDF-weighted entity clustering, cohesion split, bridge detection, velocity. | — |
| `triage.py` | Beat, verdict, one-line description, four scoring axes, generated headline, and the `progress_coded` flag. | `claude-haiku-5-5` |
| `ledger.py` | DEVELOPMENT / INCREMENT / RECYCLED classification and contradiction tracking. | `claude-sonnet-5-5` |
| `assembly.py` | Editorial selection — slot plans, set constraints, lint. | — |
| `lineup_promote.py` | Stream → Lineup. Additive only, never removes or reorders. | — |
| `build_digest.py` | Generates the live site. Fun fact via Wikipedia's On This Day. | `claude-haiku-5-5` |

**Note:** all Haiku callers use `claude-haiku-5-5`. Haiku 5.5 thinks by default, so
`triage.py`, `newscast.py` and `build_digest.py` send `thinking: disabled`.

---

## What `build_digest.py` writes

This is the only script that touches reader-facing files. It does **surgical
regex replacement into existing HTML**, not template rendering. Understanding
that is the difference between a safe change and a corrupted homepage.

Reads `ntk-pulse/data/lineup-publish.json`. Then:

1. **`digest/index.html`** — replaces three `const` markers in place:
   - `const stories = [...]`
   - `const funFact = "..."`
   - `const todayOverview = "..."`

   Everything else in the file — all 4,000 lines of app shell, CSS, and JS — is
   left untouched.

2. **`index.html`** (repo root) — replaces `const heroStory = {...}` so the
   landing page mirrors the lead story.

3. **`digest/YYYY-MM-DD/index.html`** — a frozen, complete copy of that day's
   edition. Full UI, not a stub.

4. **`digest/YYYY-MM-DD/<slug>/index.html`** — one static page per story, with
   real OG/Twitter tags baked into the HTML. These must be static files:
   crawlers don't execute JavaScript, so an SPA route cannot produce a working
   link preview.

5. **`digest/images/<slug>.jpg`** — decodes the base64 image off the story
   object and writes real bytes. `og:image` cannot be a data URI.

6. **`digest/archive/index.html`** — reverse-chronological edition index.

7. **`ntk-pulse/data/last-published.json`** — a receipt.

### Two failure modes this code has actually hit

Both are silent. Both cost real debugging time. Do not reintroduce them.

**Backslashes in regex replacement strings.** Python's `re.sub` re-parses
backslash sequences in a *string* replacement. A literal `\n` meant to stay
escaped inside a JS string gets collapsed into a real newline, which is invalid
there. **Always pass a function:** `lambda m: replacement`. Verify by running
the output through `node --check`, not by checking that Python didn't raise.

**Matching JS string literals.** `r'const foo = "[^"]*";'` breaks the moment the
content contains an escaped quote — the match stops early and the substitution
silently no-ops. Correct pattern: `r'const foo = "(?:[^"\\]|\\.)*";'`. This bites
exactly on the content NTK ships most days, since the editorial voice is built
around quoting.

---

## Routing

Five rules in `netlify.toml`. The 200s are rewrites — the address bar keeps the
clean path and the app reads the URL on load to open the matching tab.

| URL | → | Status |
|---|---|---|
| `/today` | `/digest/index.html` | 200 |
| `/backstory` | `/digest/index.html` | 200 |
| `/me` | `/digest/index.html` | 200 |
| `/digest/latest` | `/today` | 301 |
| `/digest/v2` | `/today` | 301 |

`/digest` needs no rule — `digest/index.html` serves there by folder
convention. `/digest/YYYY-MM-DD/` likewise.

**The canonical file is `digest/index.html`, a sibling of `digest/v2/`, not
inside it.** Uploading a new app build to `digest/v2/index.html` by mistake has
already broken `/today` once — it silently fell back to the root landing page.
If `/today`, `/backstory`, or `/me` ever stop showing tabs, check this first.

---

## Netlify build-skip rule

```toml
ignore = "git diff --quiet HEAD^ HEAD -- . ':(exclude)ntk-desk/data/' … ':(exclude)ntk-pulse/data/**'"
```

A commit touching **only** those data folders does not deploy. This is what
keeps the every-20-minutes bot from burning Netlify build credits. Normal
publishes also touch `digest/`, so they deploy normally.

**Consequence to remember:** any new automated commit path that writes *only*
into a data folder will silently never deploy.

---

## The one piece of server-side code

`netlify/functions/news.js` proxies two things, mode-dispatched by query param:

- **EventRegistry** — keeps the API key server-side.
- **NWS weather** — their CORS is unreliable, and the required `User-Agent`
  header turns a simple request into a preflighted one that also fails.

---

## What runs in the reader's own browser

Everything on the Today tab's **Layer 2** — local news and weather — is
generated per-visitor, client-side, from browser geolocation. It is never
centrally authored or published. Blending it into the editorial prose is
deliberately *not* built; see `docs/decisions.md`.
