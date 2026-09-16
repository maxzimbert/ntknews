# 03 — Pipeline on Cloudflare

## Schedules

| Cron | Kind | Steps |
|---|---|---|
| `*/20 * * * *` | `scan` | ingest → cluster → triage (new/grown only) → promote |
| `0 */4 * * *` | `full` | scan steps → ledger → assembly |
| `15 6 * * *` | `daily` | fun fact for today, feed health summary, retention |

`scheduled()` in the Worker does one thing: ask the `Coordinator` Durable
Object for the lock, and if granted, start a `PipelineWorkflow` instance with
`{kind, trigger:'cron'}`. If a run is in progress the scan is recorded as a
`runs` row with `status='skipped'` and the reason, so the Runs page shows it.
Manual triggers from the CMS and the API go through the same path.

## PipelineWorkflow

```
step "start"     create runs row (running), publish progress to Coordinator
step "ingest"    enqueue one INGEST_QUEUE message per enabled feed; wait (step.sleep + poll)
                 until all feeds for this run reported (feeds.last_fetch_at >= run start) or 6 min elapsed
step "cluster"   load window (items.published_at >= now - scan.window_hours), run cluster(), upsert clusters,
                 respecting status (dismissed/merged) and editor-created clusters
step "triage"    for each cluster whose (key,size,rubric) has no triage row: enqueue AI_QUEUE {type:'triage'};
                 wait until done or 8 min
step "ledger"    (full only) for each YES/MAYBE cluster: enqueue AI_QUEUE {type:'ledger_diff', item ids not yet classified}
step "assembly"  (full only) run assembly() → insert lineups(kind='auto'); merge into working lineup per promote rules
step "promote"   run promote(): clusters with publisher_count >= promote.min_publishers not represented in the working lineup are appended
step "finish"    runs row succeeded/failed with summary; metrics to Analytics Engine; release lock
```

Each step is idempotent: re-running a step after a retry finds work already
done by keys. Step timeouts are explicit; a step that exceeds its budget
marks the run `failed` with the step name and releases the lock (the DO also
expires locks after 20 minutes as a safety net).

## Queues

**INGEST_QUEUE** message: `{run_id, feed_id}`. Consumer batch of 10: for each
feed do a conditional GET (`If-None-Match`/`If-Modified-Since` from the
`feeds` row), parse RSS 2.0 / Atom / Google News sitemap (port of
`ingest.py` parsers), normalize, upsert `items` by id, update feed status
and `consecutive_failures`. Per-feed failures are recorded, never retried in
the same run; a feed with 5 consecutive failures shows red on the Feeds page.

**AI_QUEUE** message: `{run_id?, type, ...}` with types `triage`,
`ledger_diff`, `story_step`, `today`, `fun_fact`, `image_gen`. Consumer with
`max_concurrency = 2`. Every call goes through `ai/gateway.ts`, which
resolves the model from `settings`, the prompt body from the active
`prompts` row, calls AI Gateway, and writes an `ai_calls` row with tokens,
cost and the gateway log id, whether the call succeeded or failed.

## Coordinator (Durable Object)

One instance (`idFromName('global')`). Methods:

- `acquire(kind, run_id)` returns `{ok}` or `{ok:false, holder}`; TTL 20 min.
- `release(run_id)`.
- `progress(run_id, step, payload)` stores the latest state and fans out to
  connected SSE clients (the Runs page).
- `GET /events` SSE endpoint proxied by `/api/admin/runs/:id/events`.

The DO uses SQLite-backed storage so its state survives eviction.

## Algorithm ports

Each Python module becomes a pure TypeScript module with the same inputs and
outputs, tested against fixtures captured from the live data on 2026-09-11:

| Python | TypeScript | Notes |
|---|---|---|
| `ingest.py` | `pipeline/ingest.ts` | parsers, canonical URL hashing, tier/market from feed |
| `cluster.py` | `pipeline/cluster.ts` | IDF-weighted entity join, bridge detection, velocity, pulse score; stable keys |
| `triage.py` | `pipeline/triage.ts` + prompt `triage_rubric` | output fields identical (beat, line, headline, verdict, 6 scores) |
| `ledger.py` | `pipeline/ledger.ts` + prompt `ledger_diff` | classes DEVELOPMENT/INCREMENT/DUPLICATE/CONTRADICTION/UNRELATED |
| `assembly.py` | `pipeline/assembly.ts` + prompt/config `assembly_slot_plan` | slot filling, lint failures, displacement report |
| `lineup_promote.py` | `pipeline/promote.ts` | additive only, never removes editor entries |
| `build_digest.py` | `workflows/publish.ts` + `public/*.tsx` | edition freeze, permalinks, archive become renders, not files |

The Python is deleted only after the parity test suite passes on the
captured fixtures (see `07-testing.md`).

## StoryWorkflow (the five steps)

One instance per `(story_id, step)`; the story page starts it and polls
`/api/admin/stories/:id/steps/:step` (or subscribes via the Coordinator SSE).

| Step | Input | Output | Prompt |
|---|---|---|---|
| 1 Draft | cluster items / search result | `headline`, `lede`, `category` draft; `status=draft` | `draft` |
| 2 Check concept | draft | `concept_json` (is this a Jefferson-framework item, angle, risks); `status=checked` | `concept_check` |
| 3 Summon context | draft + ledger | `context_json` (what is already known, entities, timeline); `status=context` | `summon_context` |
| 4 Enrich sources | story_sources | fetch each source URL (Worker fetch, readability extraction), fill `content_text`; add EventRegistry/Exa results up to `limits.max_arts`; `status=enriched` | none |
| 5 Generate Jefferson | context + enriched sources | four section Markdowns via four calls (`jefferson_truths`, `jefferson_probabilities`, `jefferson_possibilities`, `jefferson_lies`); `packages_json`; `status=generated`; new `story_revisions` | Jefferson v14 |

Per-section actions Rewrite, Punch up, Revise are single AI calls with
their own prompts; each creates a revision. "Generate all ungenerated"
starts one StoryWorkflow per story in the lineup, queued through
`AI_QUEUE` so concurrency stays bounded.

## PublishWorkflow

```
step "freeze"    read working lineup + stories (status ready or published) + current today overview + today's fun fact
step "render"    render each section Markdown → HTML; compute slugs (unique within edition); build snapshot JSON
step "write"     R2 put editions/<date>.json; insert editions + edition_stories; mark stories published
step "flip"      settings.live_edition = <date>; start a new working lineup seeded from the published one
step "purge"     purge cache tags edition:*, app, archive via zone API; warm /today and /digest/<date>/
step "finish"    runs row; audit_log entry
```

Publishing twice on the same UTC date replaces that date's edition
(`editions.date` is the key; the previous snapshot is kept in R2 under a
versioned key for rollback). Backstory publish is the same shape with one
step fewer.

## AI Gateway

All Anthropic traffic uses the gateway URL from `vars.AI_GATEWAY_URL` with
the provider key as a Worker secret. Gateway features used: logging (with
`cf-aig-metadata` carrying `run_id`, `story_id`, `purpose`, `prompt_version`),
caching for identical triage requests (`cf-aig-cache-ttl: 3600`), rate limit
alerts, and cost tracking. The `ai_calls.gateway_log_id` column links each
row to the gateway log.

## Cost controls

- `settings.limits.max_arts`, `limits.body_len` cap enrichment and output.
- Triage is cached by `(cluster, size, rubric)`; only new or grown clusters
  cost anything, exactly like today's `triage-cache.json`.
- AI queue concurrency of 2 and per-run step budgets bound the worst case.
- The Runs page shows cost per run; the dashboard shows cost today, this
  week and this month from `ai_calls`.
- A daily spend threshold in `settings.limits.daily_ai_usd` stops
  non-editor-triggered AI work (triage/ledger) for the rest of the UTC day
  and shows a banner in the CMS.
