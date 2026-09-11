# 05 — HTTP API

Conventions: JSON in and out; `Content-Type: application/json`; errors are
`{error: {code, message, details?}}` with 400/401/403/404/409/422/429/500.
Every admin mutation writes `audit_log`. Admin routes require an Access JWT
(`Cf-Access-Jwt-Assertion` header or the `CF_Authorization` cookie); service
tokens are accepted the same way. Requests carrying
`Accept: text/html` on admin routes get the JSX page or fragment instead of
JSON, which is how the UI islands work.

## Admin API (`/api/admin`)

### Session
| Method | Path | Purpose |
|---|---|---|
| GET | `/me` | `{email, name, role, is_service}` |

### Stream and clusters
| Method | Path | Body / query | Notes |
|---|---|---|---|
| GET | `/clusters` | `?status=active&beat=&verdict=&breaking=&in_lineup=&q=&sort=pulse|latest&limit=&cursor=` | stream listing with newest triage joined |
| GET | `/clusters/:key` | | cluster, items, triage history, ledger, lineup membership |
| POST | `/clusters/merge` | `{keys:[...], into}` | sets `status='merged'`, `merged_into`; moves items |
| POST | `/clusters/:key/extract` | `{item_ids:[...], title?}` | creates cluster `origin='editor'` |
| POST | `/clusters/:key/dismiss` | `{reason?}` | |
| POST | `/clusters/:key/restore` | | |
| POST | `/clusters/:key/flag` | `{flagged: bool}` | |
| POST | `/clusters/:key/rescan` | | enqueue triage for current size, bypass cache |
| POST | `/clusters/:key/lineup` | | append to working lineup (`source='editor'`) |
| DELETE | `/clusters/:key/lineup` | | remove from working lineup |

### Search (sources)
| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/search` | `{provider:'window'|'eventregistry'|'exa', q, from?, to?, limit?}` | KV-cached 10 min |
| POST | `/search/add-story` | `{results:[{url,title,publisher,published_at}], headline?}` | creates cluster `origin='search'` + story draft |
| POST | `/stories/:id/sources` | `{url, title?, publisher?}` | manual source |

### Lineup
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/lineup` | | working lineup with entries, story status, "new since publish" |
| PATCH | `/lineup/order` | `{entry_ids:[...]}` | full order |
| POST | `/lineup/entries` | `{cluster_key?, story_id?}` | |
| DELETE | `/lineup/entries/:id` | | |
| PATCH | `/lineup/entries/:id` | `{slot?, slot_label?, is_hero?}` | |
| POST | `/lineup/clear` | | removes all editor entries; keeps nothing |
| GET | `/lineups` | `?kind=auto` | assembly history |

### Stories
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/stories` | `?status=&q=&limit=&cursor=` | |
| POST | `/stories` | `{cluster_key?, headline?}` | create draft |
| GET | `/stories/:id` | | full story, sources, revisions summary, media |
| PATCH | `/stories/:id` | any editable column subset | creates revision when a section changes |
| POST | `/stories/:id/steps/:step` | `{}` | `step ∈ draft|check|context|enrich|generate`; starts StoryWorkflow; 202 with `{run_id}` |
| GET | `/stories/:id/steps/:step` | | status of the latest run for that step |
| POST | `/stories/:id/sections/:section/rewrite` | `{mode:'rewrite'|'punch-up'|'revise', instruction?}` | single AI call, revision |
| GET | `/stories/:id/revisions` | | |
| POST | `/stories/:id/revisions/:version/restore` | | |
| POST | `/stories/:id/archive` | | |
| POST | `/stories/generate-all` | `{story_ids?}` | all ungenerated in lineup; queued |

### Media
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/media` | `?source=&q=&limit=&cursor=` | |
| POST | `/media/upload` | multipart `file`, `credit?`, `license?`, `alt?` | sha256 dedupe |
| POST | `/media/commons/search` | `{q, limit?}` | Wikimedia Commons API via Worker |
| POST | `/media/commons/pick` | `{file_title}` | downloads, stores, records license/credit |
| POST | `/media/generate` | `{prompt, model, style?, size?}` | Recraft; 202 with `{run_id}`; poll `/runs/:id` |
| PATCH | `/media/:id` | `{credit?, license?, alt?}` | |
| POST | `/stories/:id/media` | `{media_id, overlay_color?, overlay_opacity?, credit?}` | set hero |

### Today and fun fact
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/today` | | current overview + today's fun fact candidates |
| POST | `/today/generate` | `{}` | AI; new row, not current until approved |
| PATCH | `/today/:id` | `{text_md}` | |
| POST | `/today/:id/approve` | | sets current |
| POST | `/fun-facts/regenerate` | `{date?}` | |
| POST | `/fun-facts/:id/choose` | | |

### Backstory
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/backstory` | | rows ordered by position |
| POST | `/backstory` | row fields | |
| PATCH | `/backstory/:id` | row fields | |
| PATCH | `/backstory/order` | `{ids:[...]}` | |
| POST | `/backstory/:id/retire` | | |
| POST | `/backstory/publish` | | `backstory_publishes` + R2 + purge |
| GET | `/backstory/publishes` | | history |

### Publish and editions
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/publish/diff` | | working lineup vs live edition: added, removed, changed (by story version), unready stories |
| POST | `/publish` | `{date?}` | 409 if any lineup story is not `ready`/`published` unless `{force:true}`; 202 with `{run_id}` |
| GET | `/editions` | | |
| GET | `/editions/:date` | | stories, snapshot url |
| POST | `/editions/:date/make-live` | | rollback/roll-forward; purge |
| POST | `/editions/:date/unpublish` | | 404 on public routes afterwards |

### Feeds
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/feeds` | | with health |
| POST | `/feeds` | `{url, name?, type?, tier?, market?, language?}` | validates by fetching once |
| PATCH | `/feeds/:id` | editable columns | |
| POST | `/feeds/:id/validate` | | fetch now, report |
| DELETE | `/feeds/:id` | | only if no items reference it; else disable |

### Runs
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/runs` | `?kind=&status=&limit=&cursor=` | |
| GET | `/runs/:id` | | with steps, ai cost |
| GET | `/runs/:id/events` | | SSE progress via Coordinator |
| POST | `/runs` | `{kind:'scan'|'full'}` | 409 if locked |
| POST | `/runs/:id/cancel` | | best effort: Workflow terminate + lock release |

### Prompts and settings
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/prompts` | | ids with active version |
| GET | `/prompts/:id` | | all versions |
| POST | `/prompts/:id` | `{body, notes?, activate?:bool}` | new version |
| POST | `/prompts/:id/activate/:version` | | |
| GET | `/settings` | | |
| PATCH | `/settings` | `{key: value, ...}` | validated by a zod schema per key |

### Suggestions, audit, users
| Method | Path | Notes |
|---|---|---|
| GET | `/suggestions?status=` | |
| POST | `/suggestions/:id/add` | creates cluster `origin='suggestion'` and story draft |
| POST | `/suggestions/:id/dismiss` | |
| GET | `/audit?entity_type=&entity_id=&actor=&limit=&cursor=` | |
| GET | `/users`, `PATCH /users/:id {role}` | admin only |

## Public API (`/api/public`, no auth)

| Method | Path | Notes |
|---|---|---|
| GET | `/edition/live` | live edition JSON |
| GET | `/edition/:date` | |
| GET | `/backstory` | latest backstory publish JSON |
| GET | `/archive` | editions list |
| POST | `/suggest` | Turnstile-verified |
| GET | `/api/news?mode=weather|resolve-location|local-news&…` | cached proxy |

## Service tokens (agents)

Create a Cloudflare Access service token; add it to the Access policy for
`/api/admin/*`; the Worker maps its client id to a `users` row with
`is_service=1` and the configured role. Calls send
`CF-Access-Client-Id` and `CF-Access-Client-Secret` headers. Example, a
scan trigger:

```
curl -X POST https://ntknews.org/api/admin/runs \
  -H "CF-Access-Client-Id: $ID" -H "CF-Access-Client-Secret: $SECRET" \
  -H "Content-Type: application/json" -d '{"kind":"scan"}'
```
