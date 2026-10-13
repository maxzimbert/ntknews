# 01 — Data model

The DDL is `../schema/0001_init.sql`. This file explains why each group
exists, how rows move through it, and what the legacy files map to.

## Groups

```
feeds ──< items ──< item_entities
              └──< cluster_items >── clusters ──< triage
                                          └──── ledgers ──< ledger_items
clusters ──< lineup_entries >── lineups
stories ──< story_sources, story_revisions ; stories ── media
lineups ── editions ──< edition_stories (frozen copies)
backstory_rows ; backstory_publishes (frozen copies in R2)
today_overviews ; fun_facts ; suggestions
runs ──< run_steps ; ai_calls ; prompts ; settings ; redirects ; users ; audit_log
```

## Lifecycle

**Items** are immutable facts about what feeds published. `id` keeps the
16-hex canonical-URL hash from `ingest.py` so imported clusters and ledgers
keep their references. `content_text` is only filled when a story's Step 4
(enrich) fetches the article; ingest never fetches article bodies.

**Clusters** are recomputed every scan but keyed stably (same key scheme as
`cluster.py`) so editor decisions attach to them. `status` is the editor's
override: `dismissed` and `merged` clusters are excluded from the stream and
the pipeline re-attaches new items to the surviving cluster instead of
resurrecting a dismissed one. `origin` distinguishes machine clusters from
ones an editor created from a search result or a reader suggestion.

**Triage** rows are append-only, one per `(cluster, size, rubric version)`,
which is exactly the cache key `triage-cache.json` uses today
(`<key>:<size>:v5`). The newest row is what the stream shows.

**Ledgers** carry the "what is already known" record; `ledger_items` is the
per-article classification that `ledger-classes.json` holds today.

**Lineups** come in two kinds. `auto` rows are the pipeline's assembly output
(one per full run, kept for the Runs page). Exactly one `working` row is
current; automation adds to it (`source='promote'`) and editors edit it.
Publish freezes the working lineup into an edition and starts a fresh working
lineup seeded from the published one.

**Stories** are the editorial packages. A story is created from a cluster
(or from a search result or suggestion) and moves through `draft → checked →
context → enriched → generated → ready → published`. The four section columns
hold Markdown; HTML is rendered on output with the same renderer in preview
and production. `packages_json` keeps the raw Step 5 output so a regeneration
can be diffed against the editor's edits. Every generation or edit that
changes a section writes a `story_revisions` snapshot.

**Media** is content-addressed by `sha256` so the same Commons image picked
twice is stored once. The R2 key embeds the id, so URLs are immutable and
cacheable for a year.

**Editions** are the only thing the public app renders. `snapshot_r2_key`
points at the exact JSON payload (stories with rendered HTML sections, image
URLs, credits, overlay, Today text, fun fact). `edition_stories` mirrors the
per-story part of that snapshot for querying, and provides the permalink
`slug`. Rollback is `settings.live_edition = '<date>'` plus a cache purge.

**Backstory** has its own publish clock. `backstory_rows` is the editable
registry; `backstory_publishes` records each publish with the frozen JSON in
R2, which is what `/backstory` reads.

**Runs / run_steps / ai_calls** are the observability spine. A Workflow
instance id links a run to Cloudflare's own execution record. `ai_calls`
records model, prompt version, tokens and computed cost for every call,
including the ones the editor triggers from the story page.

**Prompts** are versioned rows; exactly one version per id is active
(partial unique index). Seeded from the Python and `pulse.html` by
`scripts/seed-prompts.ts`.

**Settings** is a small key/value table read once per request through a KV-
backed 30-second cache. `live_edition` is the most important key.

**Redirects** hold the legacy rules that used to be in `netlify.toml`;
`/digest/v2/*` is seeded.

## Legacy file mapping (import)

| Legacy | Target |
|---|---|
| `ntk-pulse/feeds.json` (97 feeds, `_disabled` list) | `feeds` (`enabled=0` for disabled) |
| `ntk-pulse/data/window.json` (`items` keyed by id) | `items` |
| `ntk-pulse/data/clusters.json` | `clusters`, `cluster_items`, `item_entities` (from `entities`), `triage` (from `triage`) |
| `ntk-pulse/data/triage-cache.json` (`<key>:<size>:v5`) | `triage` |
| `ntk-pulse/data/ledgers.json` (629) | `ledgers` |
| `ntk-pulse/data/ledger-classes.json` | `ledger_items` |
| `ntk-pulse/data/lineup.json` | one `lineups` row (`auto`), `lineup_entries`; a copy as the initial `working` lineup |
| `ntk-pulse/data/lineup-publish.json` | `stories` (7, status `published`), `today_overviews` |
| `digest/v2/2026-08-13 … 2026-08-28` (frozen editions) | `editions`, `edition_stories`, `stories` (status `published`) parsed from each edition's `const stories` block and `_headlines.json` |
| `digest/v2/images/*.jpg` + base64 in HTML | `media` (`source='legacy'`) + R2 |
| `digest/v2/data/backstory.json` (21 rows) | `backstory_rows` + one `backstory_publishes` |
| `editorial/backstory-rows.json`, `NTK_Backstory_Object_Matrix.xlsx` | reference only; `objects_json`/`instances_json` come from `backstory.json` |
| prompts inside `triage.py`, `ledger.py` (`DIFF_PROMPT`), `assembly.py` (slot plan), `pulse.html` (Jefferson v14, concept check, summon, punch up, revise, Today) | `prompts` |
| `netlify.toml` redirects | `redirects` |

## Sizing

At today's volume: items ~2,500 per 6-hour window with a 30-day retention
job (items not referenced by any ledger or story are deleted after 30 days);
clusters ~300 active; ledgers ~600; stories a few hundred a year; editions
one a day. D1 stays in the tens of MB. R2 grows by roughly one to two MB per
edition.

## Retention jobs (daily cron)

- Delete `items` older than 30 days that have no `cluster_items`,
  `ledger_items` or `story_sources` references.
- Archive `clusters` with `status='active'` and `latest_at` older than 7 days
  (`status='archived'`).
- Keep `runs`/`run_steps` 90 days, `ai_calls` forever (small), `audit_log`
  forever.
