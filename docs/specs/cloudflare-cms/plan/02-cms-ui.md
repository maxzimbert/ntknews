# 02 — CMS pages

All admin pages share one shell: a left rail with the sections below, a top
bar with the environment badge (production or staging), the signed-in email,
the live edition date, the pipeline lock state, and the AI spend today.
Pages are server-rendered Hono JSX; islands are listed per page. Every page
has an empty state, a loading state for islands, and inline error toasts
from the API's `error.message`. Keyboard: `/` focuses search where present,
`j`/`k` move through lists, `Enter` opens.

Rail order: Dashboard, Stream, Lineup, Stories, Search, Media, Today,
Backstory, Publish, Editions, Feeds, Runs, Prompts, Settings, Audit.

Mocks are in `../mocks/`. They are wireframes: layout and content, not
visual design.

---

## 1. Dashboard — `/admin`
Mock: `mocks/admin-dashboard.svg`

**Purpose.** Answer "what state is the site in" in five seconds.

**Content.** Live edition card (date, story count, published by, time
since, buttons Open, Publish page). Working lineup card (entries, ready vs
not ready, new since publish). Pipeline card (last scan, last full run,
next scheduled, lock state, last failure with link). AI spend (today, 7 days,
30 days, top purposes). Feed health (enabled, failing, last fetched). New
suggestions count. Recent audit entries (10).

**Actions.** Run scan, Run full, Open publish. **Islands.** None; the page
refreshes every 60 s with `<meta http-equiv=refresh>` unless an island is
focused. **Empty state.** No edition yet: card explains Publish.

---

## 2. Stream — `/admin/stream`
Mock: `mocks/admin-stream.svg`

**Purpose.** The monitoring surface: what the firehose is saying now.

**Layout.** Filter bar (beat, verdict, breaking, in lineup, flagged, text
search, sort by pulse or latest). Left: cluster list, each card showing
title (triage headline if present), beat tag, line, verdict pill,
publisher count and names, velocity, age, bridge and breaking marks, an
"in lineup" check, and a checkbox for bulk actions. Right: detail pane for
the selected cluster with items (publisher, time, title, link), triage
history, ledger summary (facts count, last development), and actions.
Bottom tab: Suggestions (reader submissions with Add and Dismiss).

**Actions.** Add to lineup / remove; Dismiss; Restore; Flag; Rescan
(re-triage); Merge selected into one; Extract checked items into a new
cluster; Create story from cluster. **Bulk.** Dismiss selected; Merge selected.

**Islands.** List with keyboard navigation and multi-select; detail pane
fetches `/api/admin/clusters/:key` as a fragment. **Live.** A small "N new
since you opened" pill when a scan finishes (SSE from the Coordinator).

---

## 3. Lineup — `/admin/lineup`
Mock: `mocks/admin-lineup.svg`

**Purpose.** Decide what the edition is.

**Layout.** Header: assembled-at of the underlying auto lineup, target vs
actual size, daytype, unfilled slots, lint failures. Main: ordered entry
rows with drag handle, position, slot label, story headline (or cluster
title when no story yet), story status chip (draft… ready… published),
source badge (assembly, promote, editor, suggestion), publisher count, hero
star, buttons Open story / Generate / Remove. Right rail: the current
assembly's slot plan with which slots are filled; "excluded sample" list
from assembly with one-click Add.

**Actions.** Reorder (drag or move up/down), Set hero, Remove, Add from
stream (opens a picker), Generate all ungenerated, Clear editor entries,
Open Publish.

**Rules shown inline.** Max size from `settings.lineup.max`; a warning when
an entry has no story or a story is not `ready`.

**Islands.** Drag-to-reorder posting `PATCH /lineup/order`; picker modal.

---

## 4. Stories list — `/admin/stories`
Mock: shares `mocks/admin-lineup.svg` layout conventions (table); no separate mock.

Filterable table by status, with search, showing headline, category,
status, updated, in-lineup, published edition. Row click opens the editor.
Button: New story (blank draft).

---

## 5. Story editor — `/admin/stories/:id`
Mock: `mocks/admin-story.svg`

**Purpose.** The five-step workflow and the Jefferson package editor.

**Layout.** Top: headline (editable), category select, lede (editable),
status chip, version, cluster link, in-lineup toggle. Step strip: five
buttons with state (not run, running with progress, done with time, failed
with reason) and a Run/Re-run button each; Step 4 shows the sources count
and `max_arts`. Left column: sources list (publisher, title, date, kind
badge, enriched check, remove), Add source (URL) and Search (opens the
Search page in a modal). Main: four section editors (Truths,
Probabilities, Possibilities, Lies) each as a Markdown textarea with a
rendered preview beside it and per-section buttons Rewrite, Punch up,
Revise (with instruction box). Right column: hero image (current image,
credit, overlay colour and opacity sliders, buttons Find photo, Generate
photo, Upload, Library), concept check result, context summary, revisions
list with Restore.

**Actions.** Save (autosave every 5 s of idle plus explicit), run any step,
per-section AI actions, set hero, archive, mark ready.

**Islands.** Markdown editor with preview (server-side render via
`/api/admin/render` for exact parity, debounced), step progress via SSE,
image tools modal, autosave.

**Errors.** A step that fails shows the model error and a Retry; the
editor's text is never replaced by a failed generation.

---

## 6. Search — `/admin/search`
Mock: `mocks/admin-search.svg`

Provider tabs: Window (local items), EventRegistry, Exa. Query, date
range, limit. Results table with checkbox, publisher, title, date, link.
Actions: Add as story (checked), Add to story (choose from open stories),
Create cluster. Also opens as a modal from Stream and Story.

---

## 7. Media library — `/admin/media`
Mock: `mocks/admin-media.svg`

Grid of images with source badge (upload, Recraft, Commons, legacy), size,
credit, license; filter by source and text. Detail drawer: preview,
metadata edit (credit, license, alt), where used (stories, backstory).
Buttons: Upload, Commons search, Generate (prompt, model, style, size).
Generation shows progress and lands in the grid.

---

## 8. Today — `/admin/today`
Mock: `mocks/admin-today.svg`

Left: Today overview editor (Markdown with preview), Generate, Approve,
history of overviews. Right: fun fact for today (text, source link, chosen
mark), Regenerate, candidates list with Choose. Bottom: weather corner
settings (default city when geolocation is denied, units).

---

## 9. Backstory registry — `/admin/backstory` and `/admin/backstory/:id`
Mocks: `mocks/admin-backstory.svg`, `mocks/admin-backstory-edit.svg`

**List.** Ordered rows: title, stratum, indicator, start date and clock
("52 years"), status, verified, updated. Drag to reorder. Buttons: New
row, Publish Backstory (shows rows changed since last publish and the last
publish time), History.

**Editor.** Fields: title, stratum, indicator, start date, start line,
narrative (Markdown), milestone, close condition, roots (tags), subgenres
(tags), objects (repeatable: object rows as in the registry), instances
(repeatable: date, text, link), photo (media picker), verified, status.
Preview pane renders the row exactly as the public Backstory tab does.

---

## 10. Publish — `/admin/publish`
Mock: `mocks/admin-publish.svg`

**Purpose.** See exactly what will go live, preview it, publish it.

**Layout.** Diff panel with three groups: Added (stories not in the live
edition), Removed, Changed (story version differs), each with headline and
status; Not ready list (blocks publish unless Force). Today overview and fun
fact as they will freeze. Buttons: Open preview (new tab, `/admin/preview/app`),
Publish, Force publish (admin only). Below: publish history (date, by, at,
stories, duration, status) with Make live and Open.

**Progress.** After Publish, the page shows the PublishWorkflow steps
(freeze, render, write, flip, purge) live, then a link to `/today`.

---

## 11. Editions — `/admin/editions` and `/admin/editions/:date`
Mock: `mocks/admin-editions.svg`

List: date, status, published by/at, stories, live mark. Detail: stories
in order with headline, slug, permalink, version; buttons Make live,
Unpublish, Open public page, Download snapshot JSON.

---

## 12. Feeds — `/admin/feeds`
Mock: `mocks/admin-feeds.svg`

Table: name, id, type, tier, market, language, enabled, last fetch, last
status, items last run, consecutive failures (red at 5). Filters: failing,
disabled, market. Row edit inline. Buttons: Add feed (URL, validate
fetch), Validate all (enqueues a scan-less validation run).

---

## 13. Runs — `/admin/runs` and `/admin/runs/:id`
Mock: `mocks/admin-runs.svg`

List: started, kind, trigger, status, duration, items new, clusters,
triaged, promoted, AI cost, error. Buttons: Run scan, Run full (disabled
with reason when locked). Detail: steps with timings and metrics, live
progress via SSE while running, AI calls in this run (purpose, model,
tokens, cost, gateway link), log download, Cancel.

---

## 14. Prompts — `/admin/prompts` and `/admin/prompts/:id`
Mock: `mocks/admin-prompts.svg`

List of prompt ids with active version, last edited, usage count (30 d).
Editor: body textarea, notes, versions list with diff against active,
Activate, Save as new version. Warning banner on the ledger diff prompt and
the Jefferson prompts: "editorial instrument; changes affect every future
generation".

---

## 15. Settings — `/admin/settings`
Mock: `mocks/admin-settings.svg`

Grouped forms: Models (per purpose), Limits (body length, max articles,
lineup max, daily AI budget), Pipeline (window hours, promote threshold,
crons shown read-only), Site (origin, cache TTLs), Users (list with role
edit, admin only), Service tokens (names only, admin only). No secrets are
displayed or editable here; a note explains `wrangler secret put`.

---

## 16. Audit — `/admin/audit`
Mock: `mocks/admin-audit.svg`

Filterable log: time, actor, action, entity, with expandable before/after
JSON. Filters: actor, entity type, action, date range. Export CSV.

---

## Cross-cutting

- **Banner states.** AI daily budget reached; pipeline lock stuck (>20 min);
  a feed failing; staging environment.
- **Roles.** `viewer` sees everything, no buttons. `editor` everything except
  Users, service tokens, force publish. `admin` all.
- **No-JS.** Every list and detail page renders fully without JavaScript;
  islands only add drag, live progress and editors with preview.
