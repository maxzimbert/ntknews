# Spec: NTK News CMS on Cloudflare (Hono)

- **Status:** draft for review, 2026-09-11
- **Public rendering of this spec (with mocks):** https://files.fwnrd.net/harness-artifacts/public/docs/ntknews-cms-spec-2026-09-11/index.html
- **Repository:** github.com/maxzimbert/ntknews, branch `feat/cloudflare-cms-spec`

## What this is

A full specification for replacing the current "git repository as database" setup
(GitHub Actions cron + a 200 KB single-file CMS that writes to the repo through the
GitHub API + Netlify serving the repo root) with a real CMS: one Hono application
running entirely on Cloudflare (Workers, D1, R2, KV, Queues, Workflows, Cron
Triggers, Access, AI Gateway), with the public site served by the same Worker.

Editorial behaviour is preserved deliberately. The pipeline layers (ingest,
cluster, triage, ledger, assembly, lineup promotion), the five-step story
workflow ending in the Jefferson package (Truths, Probabilities, Possibilities,
Lies), the Backstory registry, and the public swipe app keep their semantics.
What changes is where state lives, how it is edited, and how it is deployed.

## Files

| File | Contents |
|---|---|
| `requirements.md` | Problem statement, goals, non-goals, constraints, success criteria |
| `user-stories.md` | Stories for the editor, the pipeline, readers, and the operator |
| `plan/INDEX.md` | Plan navigation |
| `plan/00-overview.md` | Architecture, Cloudflare service map, key decisions, repo layout |
| `plan/01-data.md` | Data model narrative; the DDL is in `schema/0001_init.sql` |
| `plan/02-cms-ui.md` | Every CMS page with its mock, components, and interactions |
| `plan/03-pipeline.md` | Cron, Queues, Workflows, AI Gateway, prompts, cost controls |
| `plan/04-public-site.md` | Public routes, rendering, caching, redirects, the news proxy |
| `plan/05-api.md` | HTTP API surface (admin and public) |
| `plan/06-migration-cutover.md` | Data import from the repo, DNS, decommissioning Netlify, Pages, Actions |
| `plan/07-testing.md` | Test strategy |
| `plan/08-launch.md` | Rollout checklist |
| `schema/0001_init.sql` | Complete D1 schema |
| `wrangler.example.toml` | Bindings, crons, queues, environments |
| `mocks/*.svg` | Wireframe mock per page (desktop for CMS, phone for the public app) |
| `tasks.md` | Implementation checklist, grouped and ordered |

## Reading order

Requirements, then `plan/00-overview.md`, then `plan/02-cms-ui.md` with the mocks
open, then the schema. Everything else is reference for implementers.

## Prerequisite that is not code

`ntknews.org` must be a zone on Cloudflare DNS before cutover. At the time of
writing the domain resolves to a Netlify load balancer and the nameservers could
not be verified from the inspection host; see `plan/06-migration-cutover.md`.
