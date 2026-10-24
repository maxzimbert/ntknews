# Plan index

| File | What it covers |
|---|---|
| `00-overview.md` | Architecture, Cloudflare service map, key decisions, repo layout, cost estimate |
| `01-data.md` | Data model narrative and lifecycle; DDL in `../schema/0001_init.sql` |
| `02-cms-ui.md` | Every admin page: route, mock, components, actions, empty and error states |
| `03-pipeline.md` | Cron, Queues, Workflows, the Coordinator lock, AI Gateway, prompts, cost controls |
| `04-public-site.md` | Public routes, rendering strategy, caching and purge, redirects, the news proxy, the app port |
| `05-api.md` | Admin and public HTTP API |
| `06-migration-cutover.md` | Import script, DNS move, decommissioning, repo cleanup, rollback |
| `07-testing.md` | Fixture parity tests, unit, integration (Miniflare), end-to-end, load |
| `08-launch.md` | Rollout checklist |

Mocks: `../mocks/` (one SVG per page, referenced from `02-cms-ui.md` and `04-public-site.md`).
