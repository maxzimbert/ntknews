# Tasks

Ordered groups. Each group is a reviewable pull request or a short series of
them. A task is done when its verification line passes. Groups 3 to 9 can
proceed in parallel after Group 2, except where noted.

## Group 0: Prerequisites (human, not code)
- [ ] `ntknews.org` zone on Cloudflare; nameservers switched; records mirror Netlify — verify: `dig NS ntknews.org` shows Cloudflare nameservers and the site still serves from Netlify
- [ ] Zero Trust Access apps (prod, staging), Google + OTP, policy, one service token — verify: `/admin` on staging shows the Access login
- [ ] Decide repository visibility (recommend private) — verify: decision noted in `README.md`

## Group 1: Scaffold (see `plan/00-overview.md`)
- [ ] `package.json` (pnpm), TypeScript, Hono, zod, ulid, marked, Vitest with workers pool, ESLint, Prettier — verify: `pnpm test` runs an empty suite green
- [ ] `wrangler.toml` from `wrangler.example.toml`; staging and production resources created; ids filled — verify: `wrangler deploy --env staging --dry-run` succeeds
- [ ] `src/index.tsx` with Hono app, `scheduled()`, `queue()`, DO and Workflow exports stubbed — verify: `GET /healthz` returns `{ok:true, env}` on staging
- [ ] `deploy.yml`: PR → staging, `main` → production — verify: a PR deploys to staging automatically
- [ ] Shared layout, rail, top bar, error toast, CSS — verify: `/admin` renders the shell behind Access

## Group 2: Data layer (see `plan/01-data.md`, `schema/0001_init.sql`)
- [ ] `migrations/0001_init.sql` applied on staging and locally — verify: `wrangler d1 migrations list` shows applied; seeds present
- [ ] Typed query helpers per table in `src/db/` — verify: unit tests for each helper against in-memory D1
- [ ] `lib/markdown.ts` renderer with the citation link rule from `pulse.html` (`([Source](URL))`) — verify: fixture tests
- [ ] `auth/access.ts`: JWT verification, JWKS cache, role lookup, service tokens; fail-closed middleware — verify: integration tests (valid, expired, wrong aud, missing)
- [ ] `audit` helper wrapping every mutation — verify: test asserts one audit row per mutation route
- [ ] `scripts/seed-prompts.ts` extracting prompts from `triage.py`, `ledger.py`, `assembly.py`, `pulse.html` into `prompts` v1 — verify: 13 prompt ids active

## Group 3: Pipeline port (see `plan/03-pipeline.md`)
- [ ] Capture fixtures from `ntk-pulse/data/` and ten recorded feeds into `test/fixtures/` — verify: files present with a README noting capture time
- [ ] `pipeline/ingest.ts` + `INGEST_QUEUE` consumer with conditional GET — verify: parity test on recorded feeds; a 304 path test
- [ ] `pipeline/cluster.ts` — verify: parity test reproduces `clusters.json`
- [ ] `pipeline/triage.ts` + `AI_QUEUE` consumer + `ai/gateway.ts` with `ai_calls` accounting — verify: parity test with mocked model; `ai_calls` row per call
- [ ] `pipeline/ledger.ts` — verify: parity test with mocked model
- [ ] `pipeline/assembly.ts` and `pipeline/promote.ts` — verify: parity tests reproduce `lineup.json` and promotions
- [ ] `do/coordinator.ts` lock + progress + SSE — verify: second `scheduled()` during a run is `skipped`
- [ ] `workflows/pipeline.ts` with scan/full/daily kinds and step budgets — verify: a staging scan and full run succeed; `runs`/`run_steps` populated
- [ ] Retention job — verify: old unreferenced items deleted in test
- [ ] Daily AI budget stop — verify: test with budget 0 skips triage and sets the banner flag

## Group 4: Stream, Lineup, Search (see `plan/02-cms-ui.md` §2, 3, 6; `plan/05-api.md`)
- [ ] Clusters API and Stream page with filters, detail pane, all actions, bulk merge/dismiss — verify: e2e: dismiss survives next scan
- [ ] Suggestions pane and public `POST /api/public/suggest` with Turnstile and rate limit — verify: e2e from the public app
- [ ] Lineup API and page with drag reorder, hero, add/remove, slot plan rail — verify: reorder persists; promote never removes editor entries (test)
- [ ] Search API (window, EventRegistry, Exa) with KV cache and Add as story — verify: e2e adds a story from a result

## Group 5: Stories and media (see `plan/02-cms-ui.md` §4, 5, 7)
- [ ] Stories API, list page, editor page with autosave and section editors with preview — verify: edit creates a revision; restore works
- [ ] `workflows/story.ts` five steps; SSE progress on the page — verify: e2e with mocked AI runs all five; refresh shows progress
- [ ] Per-section Rewrite / Punch up / Revise — verify: each creates a revision and an `ai_calls` row
- [ ] Media API: upload with sha256 dedupe, Commons search and pick, Recraft generate, library page, `/media/:id` and resized variant — verify: same Commons image picked twice yields one row; `/media/:id` has immutable cache headers
- [ ] Story hero picker with overlay controls — verify: published story JSON carries image URL, credit, overlay

## Group 6: Today, Backstory (see `plan/02-cms-ui.md` §8, 9)
- [ ] Today overview API and page; fun fact generation from Wikipedia On This Day — verify: approve sets current; only one current
- [ ] Backstory registry API, list with reorder, editor with preview, publish with history — verify: `/api/public/backstory` equals the latest publish snapshot

## Group 7: Publish and editions (see `plan/03-pipeline.md` PublishWorkflow, `plan/02-cms-ui.md` §10, 11)
- [ ] Publish diff endpoint and page; preview route `/admin/preview/app` — verify: preview shows working lineup headline not yet live
- [ ] `workflows/publish.ts`: freeze, render, write, flip, purge, warm — verify: `/today` shows the new headline within 60 s on staging
- [ ] Editions API and pages; Make live (rollback) and Unpublish — verify: rollback changes `/today` without a rebuild
- [ ] Cache tag purge via zone API with token; staging fallback to short TTL — verify: purge call logged in run steps

## Group 8: Public site (see `plan/04-public-site.md`)
- [ ] `public/app.tsx` port of `digest/index.html` with JSON payload injection, R2 image URLs, lazy images — verify: transfer under 200 KB HTML; tabs and route boot unchanged (e2e)
- [ ] Landing page port with hero from live edition — verify: hero headline matches live edition
- [ ] Edition, story permalink (OG tags), archive pages — verify: e2e route table
- [ ] Redirect middleware from `redirects` table; trailing slash rule — verify: ten legacy `/digest/v2/` URLs 301 → 200
- [ ] `/api/news` proxy port with KV cache; admin-only modes moved under `/api/admin/search` — verify: weather request cached 15 min (second call `cache: hit` header)
- [ ] `sitemap.xml`, `robots.txt`, static icons via assets binding — verify: fetch each
- [ ] Analytics Engine page-view data point — verify: query shows counts on staging

## Group 9: Feeds, Runs, Prompts, Settings, Audit (see `plan/02-cms-ui.md` §12–16)
- [ ] Feeds API and page with validate and health — verify: a bad URL fails validation; failing feed shows red after 5 failures (test)
- [ ] Runs API, list, detail with live SSE, manual trigger, cancel — verify: manual scan appears and streams progress
- [ ] Prompts API and editor with versions, diff, activate — verify: activating a version changes `ai_calls.prompt_version` on the next call
- [ ] Settings page with zod validation; Users and roles (admin only) — verify: editor gets 403 on users
- [ ] Audit page with filters and CSV export — verify: rows match `audit_log`
- [ ] Dashboard — verify: cards reflect staging state

## Group 10: Import and cutover (see `plan/06-migration-cutover.md`)
- [ ] `scripts/import-legacy.ts` covering every row of the mapping table; idempotent — verify: counts table on staging
- [ ] Legacy image path map (`/digest/images/<slug>.jpg` → media id) — verify: old `og:image` URLs 302 → 200
- [ ] Staging sign-off checklist in `plan/08-launch.md` completed — verify: checklist ticked with dates
- [ ] Production import; parallel-run week — verify: daily comparison notes in `runs.summary_json`
- [ ] DNS cutover; smoke tests — verify: `curl -I https://ntknews.org/today` shows `server: cloudflare` and the Worker's header
- [ ] Decommission: Actions workflows removed, Pages off, Netlify off, legacy directories removed, tag `legacy-final` — verify: `git ls-files | grep -c ntk-pulse` is 0; Netlify site deleted

## Group 11: Quality gates (see `plan/07-testing.md`)
- [ ] Parity suite in CI, blocking — verify: CI fails on a deliberate cluster.ts change
- [ ] e2e suite against staging on every PR — verify: CI status
- [ ] `/today` weight budget check in CI — verify: fails when over 400 KB
- [ ] axe checks on admin pages — verify: no serious violations
