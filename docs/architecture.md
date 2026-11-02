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

## Backstory: draft, compose, publish (2026-10-30)

Each story gets its own Backstory page, drafted and edited before publish. Tickets: T-0109 (draft), T-0110
(per-story page), T-0111 (research and the matrix). Decisions: `docs/decisions.md`, 2026-10-28 and 2026-10-30.

```
  Pulse, Backstory tab: "Draft Backstory"
        │  commits ntk-pulse/data/lineup-draft.json to the branch Pulse is served from
        ▼     (live Pulse → main; staging Pulse → staging)
  backstory-draft.yml   the first draft only, on copies of the live files:
        │   build_pairings.py (classifier, new categories) → build_origins.py ("It starts in")
        │   → backstory_draft.py make → commits ntk-pulse/data/backstory-draft.json
        ▼
  Pulse composes each story's page in the browser (bsxCompose: Haiku names the history, the library is
  searched, Sonnet picks Beginnings and the case and writes each line; every line is checked), and saves it
  into backstory-draft.json through the Contents API. Every edit after that (rerun, apply, approve,
  not for this story, reject, research, outline) runs in Pulse the same way: no workflow run.
  Research writes editorial/research-ledger.json (searched subjects, finds, waiting items, rejections).
        │
        ▼  Publish (live Pulse only)
  pulse-publish.yml
     backstory_draft.py apply   ships the draft if every story's bs_hash still matches it; otherwise the
                                pairing and origin steps run as before and nothing composed ships
     build_digest.py → build_backstory_pages.py   one static page per composed story: /backstory/s-<story id>/
     graduate_finds.py → export_for_pulse.py      documents the editor approved join the Object Matrix
                                                  (primary sources only); the pool is rebuilt
```

- **The normal path since T-0113:** the editor types each story's row on the Backstory tab and Pulse builds
  the page there (`bsxEnsureEntries`, then `bsxCompose`), writing "We are here" itself and choosing "It starts
  in" from the page's own Beginnings. If no draft exists Pulse starts one from the published rows and the
  category store. The GitHub first draft above remains as "Draft with the classifier".
- **Fingerprints.** Pulse hashes each story's Backstory-relevant fields (`bs_hash`, with edits; `bs_text_hash`,
  without). Python only compares them. A story whose text changed needs a new first draft; one whose edits
  changed is recomposed in Pulse.
- **The reader app** (`digest/index.html`, `bsrStoryRow`) draws a pairing that carries `composed` as the story's
  own page, with the row page, object pages and the category's trend line. `?draft` lays the branch's current
  draft over the published file under a "not published" bar: `ntknews.org/backstory?draft=1`, or on staging
  `…/ntknews-staging/digest/index.html?draft=1#backstory`.
- **Staging never publishes.** Staging Pulse cannot publish; its drafts, ledger and edits live on the `staging`
  branch, and a prod publish reads only `main`'s draft.
- **Costs.** A first draft costs what the Backstory half of a publish costs; a publish that follows with
  nothing changed does not spend it again. Composing is two small calls per story. Research and outline lines
  are one web-search call each, and a subject or line is not searched twice in 30 days.

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
