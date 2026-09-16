# 07 — Testing

Tooling: Vitest with `@cloudflare/vitest-pool-workers` (runs tests inside
workerd with real D1, R2, KV, Queue and DO bindings, in memory), Playwright
for end-to-end against staging.

## 1. Parity tests for the algorithm ports (gate for deleting the Python)

Fixtures captured on 2026-09-11 from `ntk-pulse/data/`:
`window.json`, `clusters.json`, `lineup.json`, `triage-cache.json`,
`ledgers.json`, `ledger-classes.json`, `feeds.json`, plus recorded feed XML
for ten feeds (RSS, Atom, sitemap).

| Module | Assertion |
|---|---|
| ingest | Parsing the recorded XML yields the same item ids, titles, publishers and `published` values as the items in `window.json` for those feeds |
| cluster | `cluster(window)` yields the same set of cluster keys, memberships, `publisher_count`, `is_bridge`, `breaking` and `pulse_score` (within 1e-6) as `clusters.json` |
| triage | With the model call mocked to return the cached outputs, the same cache keys are requested and the same fields are stored |
| ledger | With the model mocked, the same `ledger_items` classes are produced for the same `seen_ids` |
| assembly | `assembly(clusters, ledgers, slot_plan)` reproduces `lineup.json` stories, slots and `lint_failures` |
| promote | Given `lineup.json` and `clusters.json`, the same additions are proposed |
| publish render | Rendering the imported 2026-08-28 edition produces the same story text, slugs and headline order as the frozen `digest/v2/2026-08-28/` pages (whitespace-normalized text comparison, not byte comparison) |

## 2. Unit tests

Markdown renderer output for the four sections (citation links, emphasis,
no raw HTML injection); slug uniqueness; redirect matching (exact, prefix,
splat); Access JWT verification (valid, expired, wrong audience, missing);
zod schemas for every admin write; cost computation per model.

## 3. Integration tests (inside workerd)

- Migrations apply on an empty D1; seeds present.
- Import script against fixture repo checkout populates the counts in
  `06-migration-cutover.md`.
- `scheduled()` acquires the lock, a second call is `skipped`.
- Queue consumers: a feed message with a 304 response updates
  `last_fetch_at` only; a failing feed increments `consecutive_failures`.
- PublishWorkflow: creates edition, flips `live_edition`, new working lineup
  seeded, public `/today` renders the new headline (cache bypassed in test).
- Rollback: `make-live` on an earlier date changes `/today` and `/api/public/edition/live`.
- Audit: every admin mutation route writes exactly one `audit_log` row.
- Authorization: `viewer` gets 403 on every mutation; `editor` gets 403 on
  `/users` and `/settings` writes reserved for `admin`.

## 4. End-to-end (Playwright on staging)

- Sign in through Access (test identity with OTP), land on the dashboard.
- Stream → promote → lineup reorder → story five steps (AI mocked on
  staging with a `settings.ai.mock=true` flag that returns canned output) →
  pick a Commons image → publish → public app shows the story → share link
  opens → roll back.
- Backstory edit → publish → `/backstory` shows the change.
- Suggestion form on the public app → appears in the stream.
- Every public route from `04-public-site.md`, including ten legacy
  `/digest/v2/` URLs, returns the expected status.

## 5. Load and cost sanity

- 1,000 requests to `/today` with cache warm: p95 under 100 ms at the edge,
  D1 reads near zero.
- A simulated scan with all 97 feeds recorded: completes under 3 minutes;
  AI queue never exceeds concurrency 2.

## 6. Accessibility and weight

- axe run on every admin page: no serious violations.
- `/today` transfer size asserted under 400 KB in CI (fails the build if
  exceeded).
