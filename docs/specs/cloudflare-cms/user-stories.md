# User stories

Roles: **Editor** (Max), **Admin** (Max, or whoever runs the deployment),
**Pipeline** (the scheduled system), **Reader** (public visitor),
**Agent** (a script or coding agent driving the admin API with a service token).

Each story lists acceptance criteria that a test can assert.

## Editor

**E1. Sign in without secrets.** As an editor I open `/admin` and am signed in
by Cloudflare Access with my Google account or a one-time PIN. I never paste an
API key or a GitHub token anywhere.
- `/admin` without an Access JWT returns the Access login page.
- The settings page has no fields for third-party keys.

**E2. Watch the stream.** As an editor I see the current clusters ranked by
pulse score, with beat, line, verdict, publisher count, velocity, and the
newest items, and I can filter by beat, verdict, breaking, and "not yet in
lineup".
- Stream loads in under 1 second from D1 (indexed on `status`, `pulse_score`).
- Each cluster card shows the same fields Pulse shows today.

**E3. Shape clusters.** As an editor I can merge clusters, extract selected
items into a new cluster, dismiss a cluster, flag it, and add it to the lineup.
- Each action is one POST, applied atomically in D1, written to `audit_log`.
- Dismissed clusters do not reappear on the next pipeline run (the run
  respects `status`).

**E4. Search for sources.** As an editor I can search the ingest window,
EventRegistry, and Exa from the CMS and add a result as a new story or as a
source on an existing story.
- Searches go through the Worker; the browser never holds a key.
- Results are cached in KV for 10 minutes per query.

**E5. Edit the lineup.** As an editor I see the working lineup with slots and
slot labels, reorder by drag, pick the hero, remove entries, and see which
entries are new since the last publish.
- The lineup is a single `lineups` row with `kind='working'` and ordered
  `lineup_entries`; reorder is one PATCH with the new order.
- Automatic promotion never removes or reorders an editor's entries.

**E6. Write a story in five steps.** As an editor I open a story and run
Draft, Check concept, Summon context, Enrich sources, and Generate Jefferson,
each as a durable step with visible progress, then edit the four sections
(Truths, Probabilities, Possibilities, Lies) in a Markdown editor with a live
preview that matches the public rendering.
- Each step is a Cloudflare Workflow; refreshing the page shows its progress.
- Every generation is recorded in `ai_calls` and creates a `story_revisions` row.
- "Rewrite", "punch up", "revise" per section reuse the same mechanism.

**E7. Pick or make a photo.** As an editor I can search Wikimedia Commons or
generate an image with Recraft, choose a style, set overlay colour and
opacity, add a credit, and see the result as the story hero.
- The chosen image is stored once in R2 with `media.source` and `credit`.
- Generation happens server-side; the browser polls for the result.

**E8. Write the Today overview and fun fact.** As an editor I can generate,
edit and approve the Today overview and see the fun fact the pipeline picked
(grounded in Wikipedia's On This Day), and replace it.

**E9. Maintain the Backstory registry.** As an editor I can list, edit, add
and reorder backstory rows with their objects, instances, milestones and
clocks, and publish the registry independently of the daily edition.
- Backstory publish is its own action with its own history table.
- The public Backstory tab reads the latest published snapshot.

**E10. Preview, publish, roll back.** As an editor I open Publish, see a diff
between the working lineup and the live edition (added, removed, changed
stories), open a preview URL that renders the public app from the working
state, and publish. From Editions I can make any earlier edition live again.
- Publish creates an `editions` row with date, snapshot in R2, and purges
  the cache. Live changes within 60 seconds.
- Rollback is "set `settings.live_edition` to another date and purge"; no
  rebuild.

**E11. See what the machine is doing.** As an editor I can open Runs, see
every pipeline run with steps, durations, counts and errors, and trigger a
scan or a full run manually.

**E12. Manage feeds.** As an editor I can enable or disable feeds, change
tier, market and language, add a feed by URL with validation, and see each
feed's last status and consecutive failures.

**E13. Edit prompts and settings.** As an editor I can view and edit the
triage rubric, the ledger diff prompt, the Jefferson section prompts, the
assembly slot plan, models per purpose, body length and article limits, with
every change versioned and revertible.

## Pipeline

**P1. Scan every 20 minutes.** Ingest all enabled feeds via a queue (one
message per feed), cluster the 6-hour window, triage new or grown clusters,
and promote corroborated clusters to the working lineup.
- Two scans never overlap: a Durable Object lock rejects the second.
- A feed that fails 5 times in a row is marked and shown on the Feeds page.

**P2. Full run every 4 hours.** Scan plus ledger diffing and digest assembly
producing a fresh automatic lineup that never displaces editor entries.

**P3. Record everything.** Every run writes `runs` and `run_steps`; every AI
call writes `ai_calls` with token counts and estimated cost.

**P4. Respect editor decisions.** Dismissed clusters stay dismissed; editor
lineup entries are never removed by automation; a story's editor-edited
sections are never overwritten by a regeneration without creating a revision.

## Reader

**R1. Open the app.** `/today`, `/backstory`, `/me`, `/digest/` render the
swipe app with the live edition. First load transfers under 400 KB.

**R2. Follow a shared link.** Any old `/digest/v2/...` link redirects (301)
to the same path without `v2` and renders. Any `/digest/YYYY-MM-DD/<slug>/`
page has correct Open Graph tags and image.

**R3. See local weather and news.** With location permission, the Today tab
shows weather and local headlines. Responses are cached per rounded location
for 15 minutes.

**R4. Suggest a story.** The suggestion form submits with Turnstile and
confirms; the editor sees it in the stream under Suggestions.

## Admin / operator

**A1. Deploy from git.** `wrangler deploy` from `main` deploys the Worker;
D1 migrations run with `wrangler d1 migrations apply`. A staging environment
exists with its own D1, R2 and KV.

**A2. Observe.** Workers Logs show request and pipeline logs; an Analytics
Engine dataset receives run metrics and AI cost; an alert fires when a
scheduled run fails twice in a row.

**A3. Import and cut over.** A one-time import script loads the six existing
editions, images, the backstory rows, feeds and ledgers into D1 and R2.
DNS is switched to Cloudflare; Netlify, GitHub Pages and the GitHub Actions
workflows are switched off; the old data directories are removed from the
repo.

## Agent

**G1. Drive the admin API.** With a Cloudflare Access service token an agent
can list clusters, create a story, run a step, and publish, receiving JSON.
Every such action is attributed to the service token's name in `audit_log`.
