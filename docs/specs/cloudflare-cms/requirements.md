# Requirements

## Problem

NTK News today has no CMS. It has:

- **A pipeline in GitHub Actions.** Python scripts (`ntk-pulse/`) run on cron
  (every 20 minutes and every 4 hours), call the Anthropic API, and commit JSON
  into `ntk-pulse/data/`. Ten to thirteen bot commits land on `main` every day.
- **An editor UI that is one HTML file.** `ntk-pulse/pulse.html` reads that JSON
  over HTTP, calls Anthropic, Recraft, Wikipedia and EventRegistry from the
  browser with keys pasted into a settings panel, and "saves" by writing files
  into the repository through the GitHub Contents API with a personal token kept
  in `localStorage`.
- **A publish step that rewrites HTML.** A push of `lineup-publish.json` triggers
  a workflow that runs `build_digest.py`, which regenerates a `const stories`
  block inside `digest/index.html`, freezes a dated edition, writes permalink
  pages and images, and commits the result. The public app is an 860 KB HTML
  file with its images embedded as base64.
- **Two deploy targets.** Netlify serves the repository root. GitHub Pages also
  builds on every push. Every bot commit is a potential deploy.

Consequences seen in September 2026: a half-finished move of `digest/v2/` to
`digest/`, broken Backstory data and share links on the live site, Netlify
credits burned by bot-triggered builds, the editor's API keys and a repo-write
token living in a browser, no audit trail, no preview, no rollback except
`git revert`, and content changes that are indistinguishable from code changes.

## Goal

Replace the storage, editing, publishing and hosting layers with a single Hono
application on Cloudflare, keeping the editorial model intact.

## Functional requirements

### R1. Editorial workflow parity
The CMS must support everything Pulse does today, as first-class pages:
stream monitoring with cluster actions (merge, extract, dismiss, flag,
promote), lineup editing with slots, the five-step story workflow (Draft,
Check concept, Summon context, Enrich sources, Generate Jefferson), source
search (window, EventRegistry, Exa), photo find (Wikimedia Commons) and
photo generation (Recraft), the Today overview, the Backstory registry with
its own publish clock, and Publish to the live digest.

### R2. Server-side secrets
No API key or repository token is ever entered into or stored by a browser.
All third-party calls (Anthropic, Recraft, EventRegistry, Exa, Wikipedia,
weather) are made by the Worker using Worker secrets.

### R3. Authentication and authorization
`/admin/*` and `/api/admin/*` are behind Cloudflare Access. The application
verifies the Access JWT on every request. Roles: `admin`, `editor`, `viewer`.
Service tokens allow an agent or script to call the admin API.

### R4. Database as source of truth
All editorial state lives in D1. Binary assets live in R2. The repository
contains code only. No pipeline or editor action commits to git.

### R5. Publishing
Publishing creates an immutable edition (date-keyed) with a snapshot of every
story, the Today overview and the fun fact. The live app reflects the newest
published edition within 60 seconds. Any previous edition can be re-published
as live (rollback) without rebuilding anything. A preview of the working
lineup is viewable before publish at a URL only editors can open.

### R6. Pipeline on Cloudflare
Ingest, cluster, triage, ledger, assembly and lineup promotion run on
Cloudflare on the same cadence as today (scan every 20 minutes, full run
every 4 hours), with per-run logs, metrics and cost recorded, a manual
trigger, and a hard guarantee that two runs never overlap.

### R7. Public site parity
All public URLs keep working: `/`, `/today`, `/backstory`, `/me`, `/digest/`,
`/digest/YYYY-MM-DD/`, `/digest/YYYY-MM-DD/<slug>/`, `/digest/archive/`,
`/digest/images/<slug>.jpg`, `/digest/latest`, and the legacy `/digest/v2/*`
paths, which 301 to their non-v2 equivalents. Open Graph and Twitter cards on
permalink pages keep working. The weather and local-news feature keeps working.

### R8. Media
Images are stored once in R2 and referenced by URL. The public app stops
embedding base64 images. Uploads, Recraft generations and Commons picks go
through the same media library with credit and license fields.

### R9. Observability and audit
Every editor action that changes state is written to an audit log with the
actor's email. Every AI call is recorded with model, prompt version, tokens
and estimated cost. Pipeline runs expose a step-by-step log.

### R10. Reader suggestions
The "suggest a story" call to action on the public app posts to the CMS
(with Turnstile) and shows up in the stream as a reviewable suggestion.

## Non-functional requirements

- **N1. Cloudflare only.** Workers, D1, R2, KV, Queues, Workflows, Durable
  Objects, Cron Triggers, Access, AI Gateway, Turnstile, DNS. No other hosting
  provider after cutover.
- **N2. Cost ceiling.** Runs within the Workers Paid plan ($5/month base) plus
  D1/R2/KV/Queues usage that stays inside included quotas at today's traffic.
  AI spend is the same third-party spend as today, now measured. Estimate is
  in `plan/00-overview.md` and is marked as an estimate.
- **N3. Public page weight.** The app HTML drops below 200 KB; images load
  lazily from R2 with immutable cache headers.
- **N4. Edge caching.** Public HTML is cached at the edge and purged on publish.
  A publish is visible globally within 60 seconds.
- **N5. No SPA framework.** Server-rendered Hono JSX with small vanilla
  JavaScript islands. One dependency tree, one deploy artifact.
- **N6. Reversible cutover.** Netlify stays up, unchanged, until the Cloudflare
  deployment has served production traffic for a week. DNS is the only switch.

## Non-goals (this spec)

- Reader accounts. The Profile tab (`/me`) stays client-side (`localStorage`)
  exactly as it is.
- Email newsletters, push notifications, comments.
- Re-designing the public app's look. It is ported, not redesigned.
- Multi-tenant or multi-publication support.
- Replacing the clustering or triage algorithms. They are ported line for line
  from Python to TypeScript and covered by fixture tests that assert identical
  output on the same input.

## Constraints

- One editor today (Max). Design for two to five, not fifty.
- The Python pipeline has editorial instruments in its prompts (the ledger
  `DIFF_PROMPT`, the Jefferson v14 section prompts, the assembly slot plan).
  These are content, not code: they move into the `prompts` table, versioned,
  and are editable in the CMS without a deploy.
- `ntknews.org` must move to Cloudflare DNS before cutover (Workers custom
  domains and Access both require the zone).
- The existing 6 editions, 21 backstory rows, 97 feeds, 629 ledgers and all
  images must be imported, and the old dated URLs must keep resolving.

## Success criteria

1. Max can open `/admin`, sign in with Cloudflare Access, and complete the
   full cycle stream → lineup → story → publish without leaving the browser
   and without pasting a key anywhere.
2. `git log` on `main` shows only human code commits for seven consecutive days.
3. The live site serves from the Worker, every URL in R7 returns the expected
   status, and Lighthouse on `/today` reports a transfer size under 400 KB.
4. A publish and a rollback to the previous edition each complete in under
   60 seconds end to end.
5. Netlify and GitHub Pages are switched off with no reader-visible change.
