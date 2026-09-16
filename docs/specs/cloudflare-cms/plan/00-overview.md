# 00 — Architecture overview

## One sentence

One Hono Worker serves the public site, the admin CMS and the JSON API; D1 is
the database, R2 holds binaries and immutable snapshots, KV caches, Queues
fan out feed fetches and AI jobs, Workflows run every multi-step process
durably, a Durable Object guarantees one pipeline run at a time, Cron
Triggers replace GitHub Actions, Cloudflare Access replaces the pasted token,
and AI Gateway sits in front of Anthropic.

## Service map

| Concern today | Today | Target |
|---|---|---|
| Scheduling | GitHub Actions cron (2 workflows) | Cron Triggers on the Worker → `PipelineWorkflow` |
| Feed fetching | Sequential Python in one job | `INGEST_QUEUE`, one message per feed, batch consumer |
| Clustering, triage, ledger, assembly | Python, stdlib | TypeScript port, same algorithms, run as Workflow steps; AI calls via `AI_QUEUE` |
| Editorial state | JSON files committed to git | D1 (`ntknews-db`) |
| Editor UI | `pulse.html`, keys in `localStorage` | Hono JSX pages under `/admin`, Access-protected |
| Secrets | Browser settings panel | Worker secrets (`wrangler secret put`) |
| Third-party AI | Direct from browser and from Actions | Worker → AI Gateway → Anthropic / Recraft; every call logged |
| Publish | Actions job rewrites HTML, commits | `PublishWorkflow`: snapshot → R2 → `settings.live_edition` → cache purge |
| Public HTML | Static files in repo, Netlify | Rendered by the Worker from D1/R2, edge-cached, purged on publish |
| Images | base64 inside HTML, JPGs in repo | R2 objects, `/media/<id>` with immutable cache |
| Weather / local news | Netlify Function | Hono route `/api/news`, KV cache |
| Auth | none (URL obscurity + GitHub token) | Cloudflare Access (Google or OTP), roles in D1, service tokens for agents |
| Audit | git log | `audit_log`, `ai_calls`, `runs`, `run_steps` |
| Deploy | push to main → Netlify + Pages | `wrangler deploy` (CI on `main`), staging environment |
| Domain | Netlify DNS/LB | Cloudflare zone, Worker custom domain |

## Request flow

```
                         ┌──────────────────────────── Cloudflare edge ────────────────────────────┐
 reader ── ntknews.org ──▶ Worker (Hono) ── public routes ──▶ Cache API / KV ──▶ D1, R2 ──▶ HTML   │
                         │                 /media/*  ───────▶ R2 (immutable)                        │
                         │                 /api/news ───────▶ KV cache ──▶ EventRegistry/Exa/weather│
 editor ── Access JWT ──▶ Worker (Hono) ── /admin/*  ──────▶ D1 ──▶ JSX pages + fragments          │
                         │                 /api/admin/* ───▶ D1, R2, Workflows, Queues, DO         │
 cron ───────────────────▶ scheduled() ───▶ COORDINATOR (lock) ──▶ PipelineWorkflow                 │
                         │                    ├─ INGEST_QUEUE ──▶ consumer: fetch feed → items      │
                         │                    ├─ cluster (in-step)                                  │
                         │                    ├─ AI_QUEUE ──▶ consumer: triage / ledger via Gateway │
                         │                    └─ assembly / promote → lineups                       │
                         └───────────────────────────────────────────────────────────────────────────┘
```

## Key decisions

**D1. One Worker, not two.** Public and admin share code (rendering a story is
the same function in preview and in production). Access policy on
`/admin/*` and `/api/admin/*` provides the security boundary; the Worker also
verifies the JWT so a misconfigured Access policy fails closed.

**D2. Server-rendered Hono JSX plus islands.** No React, no bundler-heavy SPA.
Pages render on the Worker; interactive parts (drag-to-reorder, Markdown
editor with preview, image picker, progress panes) are small vanilla modules
in `public/js/` that talk to `/api/admin/*` and swap HTML fragments returned
by the same Hono routes. This keeps the CMS at one deploy artifact and makes
every page usable without JavaScript for reading.

**D3. D1 is the source of truth; R2 holds immutable snapshots.** A publish
writes `editions/<date>.json` to R2 and one `editions` row. The public app
renders from the snapshot, never from mutable tables, so a publish is atomic
and a rollback is a pointer change (`settings.live_edition`).

**D4. Workflows for anything with more than one step.** Pipeline runs, the
five story steps and publish are Cloudflare Workflows: each step is retried
independently, state survives Worker restarts, and the Runs page shows
progress from the workflow instance status. The Durable Object only holds the
"one run at a time" lock and streams progress to the browser.

**D5. Queues bound external concurrency.** Feed fetches fan out to the
ingest queue (97 feeds, batches of 10). AI jobs go to the AI queue with
`max_concurrency = 2`, which is how Anthropic rate limits are respected
without hand-written throttling.

**D6. Port the algorithms, don't reinvent them.** `ingest.py`, `cluster.py`,
`triage.py`, `ledger.py`, `assembly.py`, `lineup_promote.py` are ported to
TypeScript function-for-function. Fixture tests feed the same
`window.json`/`clusters.json` inputs to both and assert identical output
before the Python is deleted. Prompts move into the `prompts` table.

**D7. Prompts and slot plans are content.** The ledger `DIFF_PROMPT`, the
Jefferson v14 prompts, the triage rubric and the assembly slot plan are rows
in `prompts` with versions and an active flag, editable in the CMS, with
every AI call recording which version it used.

**D8. The public app is ported, not rewritten.** `digest/index.html` becomes
a Hono JSX template. The `const stories` block is replaced by a JSON payload
injected server-side from the edition snapshot; images become R2 URLs;
everything else (swipe UI, tabs, beats in `localStorage`, speech, share) is
kept. Only the route-boot and data-loading code changes.

**D9. Edge cache with explicit purge.** Public HTML responses carry
`Cache-Control: public, s-maxage=300` and an `edition:<date>` cache tag.
Publish purges by tag through the zone API. Media carries
`immutable, max-age=31536000` because the URL contains the content id.

**D10. Staging is real.** `staging.ntknews.org` runs the same Worker with its
own D1, R2, KV and Access application. Migrations and imports are rehearsed
there first.

## Repository layout (target)

```
ntknews/
  wrangler.toml
  package.json               pnpm; hono, zod, ulid, marked (server-side markdown), vitest, @cloudflare/vitest-pool-workers
  migrations/                D1 migrations (0001_init.sql, ...)
  src/
    index.tsx                Hono app: routes, scheduled(), queue(), exports for DO and Workflows
    env.ts                   Bindings type
    auth/                    access.ts (JWT verify, JWKS cache), roles.ts
    db/                      typed query helpers per table (no ORM), ulid.ts
    pipeline/                ingest.ts cluster.ts triage.ts ledger.ts assembly.ts promote.ts (ports)
    ai/                      gateway.ts (Anthropic via AI Gateway), recraft.ts, prompts.ts, cost.ts
    workflows/               pipeline.ts story.ts publish.ts
    do/                      coordinator.ts
    queues/                  ingest-consumer.ts ai-consumer.ts
    admin/                   pages/ (JSX) fragments/ actions/ (POST handlers)
    public/                  routes.tsx app.tsx edition.tsx story.tsx archive.tsx landing.tsx news-proxy.ts redirects.ts
    lib/                     markdown.ts slug.ts cache.ts turnstile.ts
  public/                    static assets (css, js islands, icons) served by the assets binding
  scripts/
    import-legacy.ts         one-time import from the old repo layout (see 06)
    seed-prompts.ts          loads the prompts extracted from the Python and pulse.html
  test/
    fixtures/                window.json, clusters.json, lineup.json, expected outputs
    unit/ integration/ e2e/
  docs/specs/cloudflare-cms/ this spec
```

Legacy directories (`ntk-pulse/`, `ntk-desk/`, `digest/`, `editorial/`,
`netlify/`, `.github/workflows/`, `netlify.toml`) are deleted at cutover in
one commit tagged `legacy-final`, after the import is verified. `rss-scanner/`,
`editor.html`, `article-generator.html`, `ntknews-index.html`,
`ntknews-momtest.html`, `ntk-production.html` are one-off tools; they are
moved to `legacy/` in the same commit and are not served.

## Cost estimate (estimate, not a quote)

Assumes today's traffic (low thousands of page views a day) and today's AI
usage. Cloudflare list prices as of mid-2026 should be checked before launch.

| Item | Basis | Monthly |
|---|---|---|
| Workers Paid plan | base | $5 |
| Worker requests | well under 10M included | $0 |
| D1 | reads/writes and storage under included | $0 to $1 |
| R2 | under 1 GB media, low egress via Worker | $0 to $1 |
| KV, Queues, Workflows, DO | under included | $0 to $2 |
| AI Gateway, Access (≤50 users), Turnstile | free tiers | $0 |
| Anthropic | same as today, now visible in `ai_calls` | unchanged |
| Recraft, EventRegistry, Exa | same as today | unchanged |

What goes away: Netlify (credits), GitHub Actions minutes (free on public
repos anyway), and the 18 MB repo deploys.

## Not decided here

- Whether to keep the repository public. Nothing in the target design
  requires it, and a private repo removes the "everything in the repo is on
  the internet" property of today's setup.
- Whether `ntk-desk/` is worth porting at all. The spec treats it as retired;
  its ideas already live in `ntk-pulse/`.
