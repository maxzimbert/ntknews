-- NTK News CMS — D1 schema, migration 0001
-- Apply with: wrangler d1 migrations apply ntknews-db
-- Conventions: TEXT ids are content hashes or ULIDs; timestamps are ISO-8601 UTC strings;
-- JSON columns hold arrays/objects serialized by the application and are never queried by SQL.

PRAGMA foreign_keys = ON;

-- ── People and access ───────────────────────────────────────────────────────

CREATE TABLE users (
  id            INTEGER PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,            -- from the Access JWT
  name          TEXT,
  role          TEXT NOT NULL DEFAULT 'editor' CHECK (role IN ('admin','editor','viewer')),
  is_service    INTEGER NOT NULL DEFAULT 0,      -- 1 for Access service tokens (agents)
  created_at    TEXT NOT NULL,
  last_seen_at  TEXT
);

CREATE TABLE audit_log (
  id            INTEGER PRIMARY KEY,
  at            TEXT NOT NULL,
  actor_email   TEXT NOT NULL,
  action        TEXT NOT NULL,                   -- e.g. cluster.merge, lineup.reorder, edition.publish
  entity_type   TEXT NOT NULL,
  entity_id     TEXT,
  before_json   TEXT,
  after_json    TEXT,
  request_id    TEXT
);
CREATE INDEX audit_log_at ON audit_log(at DESC);
CREATE INDEX audit_log_entity ON audit_log(entity_type, entity_id);

-- ── Feeds and ingest (Layer 1) ──────────────────────────────────────────────

CREATE TABLE feeds (
  id                    TEXT PRIMARY KEY,        -- slug, e.g. 'reuters' (imported from feeds.json)
  name                  TEXT NOT NULL,
  url                   TEXT NOT NULL UNIQUE,
  type                  TEXT NOT NULL CHECK (type IN ('rss','atom','sitemap')),
  tier                  INTEGER NOT NULL DEFAULT 2,
  market                TEXT NOT NULL DEFAULT 'us',
  language              TEXT NOT NULL DEFAULT 'en',
  enabled               INTEGER NOT NULL DEFAULT 1,
  etag                  TEXT,                    -- conditional GET state
  last_modified         TEXT,
  last_fetch_at         TEXT,
  last_status           INTEGER,
  last_error            TEXT,
  last_item_count       INTEGER,
  consecutive_failures  INTEGER NOT NULL DEFAULT 0,
  created_at            TEXT NOT NULL,
  updated_at            TEXT NOT NULL
);

CREATE TABLE items (
  id              TEXT PRIMARY KEY,              -- 16-hex hash of canonical URL (same scheme as ingest.py)
  feed_id         TEXT NOT NULL REFERENCES feeds(id),
  url             TEXT NOT NULL,
  title           TEXT NOT NULL,
  summary         TEXT,
  publisher       TEXT NOT NULL,                 -- feed id
  publisher_name  TEXT NOT NULL,
  tier            INTEGER NOT NULL,
  market          TEXT NOT NULL,
  language        TEXT NOT NULL,
  published_at    TEXT NOT NULL,
  first_seen_at   TEXT NOT NULL,
  content_text    TEXT,                          -- fetched on demand for enrichment, never at ingest
  content_fetched_at TEXT
);
CREATE INDEX items_published ON items(published_at DESC);
CREATE INDEX items_feed ON items(feed_id, published_at DESC);
CREATE UNIQUE INDEX items_url ON items(url);

CREATE TABLE item_entities (
  item_id   TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  entity    TEXT NOT NULL,                       -- normalized entity string
  weight    REAL NOT NULL DEFAULT 1.0,           -- IDF weight at time of clustering
  PRIMARY KEY (item_id, entity)
);
CREATE INDEX item_entities_entity ON item_entities(entity);

-- ── Clusters and triage (Layers 2–3) ────────────────────────────────────────

CREATE TABLE clusters (
  key              TEXT PRIMARY KEY,             -- stable cluster key (same scheme as cluster.py)
  title            TEXT NOT NULL,
  beat_hint        TEXT,
  breaking         INTEGER NOT NULL DEFAULT 0,
  is_bridge        INTEGER NOT NULL DEFAULT 0,
  size             INTEGER NOT NULL DEFAULT 0,
  publisher_count  INTEGER NOT NULL DEFAULT 0,
  publishers_json  TEXT NOT NULL DEFAULT '[]',
  entities_json    TEXT NOT NULL DEFAULT '[]',
  latest_at        TEXT,
  latest_age_hours REAL,
  velocity         REAL,
  raw_velocity     REAL,
  pulse_score      REAL,
  status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','dismissed','merged','archived')),
  merged_into      TEXT REFERENCES clusters(key),
  flagged          INTEGER NOT NULL DEFAULT 0,
  origin           TEXT NOT NULL DEFAULT 'pipeline' CHECK (origin IN ('pipeline','editor','suggestion','search')),
  last_run_id      TEXT,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);
CREATE INDEX clusters_stream ON clusters(status, pulse_score DESC);
CREATE INDEX clusters_latest ON clusters(latest_at DESC);

CREATE TABLE cluster_items (
  cluster_key  TEXT NOT NULL REFERENCES clusters(key) ON DELETE CASCADE,
  item_id      TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  added_at     TEXT NOT NULL,
  added_by     TEXT NOT NULL DEFAULT 'pipeline', -- 'pipeline' or an editor email (extract/merge)
  PRIMARY KEY (cluster_key, item_id)
);
CREATE INDEX cluster_items_item ON cluster_items(item_id);

CREATE TABLE triage (
  id                      INTEGER PRIMARY KEY,
  cluster_key             TEXT NOT NULL REFERENCES clusters(key) ON DELETE CASCADE,
  rubric_version          TEXT NOT NULL,         -- 'v5' today; cache key = cluster_key + size_at + rubric_version
  size_at                 INTEGER NOT NULL,
  headline                TEXT,
  beat                    TEXT,
  line                    TEXT,
  verdict                 TEXT CHECK (verdict IN ('YES','MAYBE','NO')),
  politician_led          INTEGER,
  progress_coded          INTEGER,
  actionability           INTEGER,
  conversational_currency INTEGER,
  emotional_load          INTEGER,
  explainability          INTEGER,
  ai_call_id              INTEGER,
  created_at              TEXT NOT NULL,
  UNIQUE (cluster_key, size_at, rubric_version)
);
CREATE INDEX triage_cluster ON triage(cluster_key, created_at DESC);

-- ── Story ledger (Layer 3b) ─────────────────────────────────────────────────

CREATE TABLE ledgers (
  id                  TEXT PRIMARY KEY,          -- same id scheme as ledgers.json keys
  cluster_key         TEXT REFERENCES clusters(key),
  title               TEXT NOT NULL,
  facts_json          TEXT NOT NULL DEFAULT '[]',
  entities_json       TEXT NOT NULL DEFAULT '[]',
  contradictions_json TEXT NOT NULL DEFAULT '[]',
  credits_json        TEXT NOT NULL DEFAULT '[]',
  created_at          TEXT NOT NULL,
  last_active_at      TEXT NOT NULL
);
CREATE INDEX ledgers_active ON ledgers(last_active_at DESC);

CREATE TABLE ledger_items (
  id            INTEGER PRIMARY KEY,
  ledger_id     TEXT NOT NULL REFERENCES ledgers(id) ON DELETE CASCADE,
  item_id       TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  class         TEXT NOT NULL CHECK (class IN ('DEVELOPMENT','INCREMENT','DUPLICATE','CONTRADICTION','UNRELATED')),
  what_new      TEXT,
  contradicts_json TEXT,
  is_unique     INTEGER NOT NULL DEFAULT 0,
  credits_json  TEXT,
  ai_call_id    INTEGER,
  created_at    TEXT NOT NULL,
  UNIQUE (ledger_id, item_id)
);

-- ── Lineups (Layers 5–6) ────────────────────────────────────────────────────

CREATE TABLE lineups (
  id              TEXT PRIMARY KEY,              -- ULID
  kind            TEXT NOT NULL CHECK (kind IN ('auto','working')),
  is_current      INTEGER NOT NULL DEFAULT 0,    -- exactly one current 'working' lineup
  assembled_at    TEXT NOT NULL,
  daytype         TEXT,
  target_size     INTEGER,
  actual_size     INTEGER,
  slot_plan_json  TEXT,
  lint_failures_json TEXT,
  displacement_json  TEXT,
  excluded_sample_json TEXT,
  run_id          TEXT,
  created_by      TEXT NOT NULL DEFAULT 'pipeline'
);
CREATE UNIQUE INDEX lineups_current ON lineups(kind) WHERE is_current = 1;

CREATE TABLE lineup_entries (
  id              INTEGER PRIMARY KEY,
  lineup_id       TEXT NOT NULL REFERENCES lineups(id) ON DELETE CASCADE,
  position        INTEGER NOT NULL,
  cluster_key     TEXT REFERENCES clusters(key),
  story_id        TEXT,                          -- set once a story package exists (FK below via trigger-free convention)
  slot            TEXT,
  slot_label      TEXT,
  assembly_score  REAL,
  scores_json     TEXT,
  ledger_class    TEXT,
  new_facts_json  TEXT,
  is_hero         INTEGER NOT NULL DEFAULT 0,
  source          TEXT NOT NULL CHECK (source IN ('assembly','promote','editor','suggestion','search')),
  added_at        TEXT NOT NULL,
  added_by        TEXT NOT NULL,
  UNIQUE (lineup_id, position)
);
CREATE INDEX lineup_entries_lineup ON lineup_entries(lineup_id, position);

-- ── Stories (editorial packages) ────────────────────────────────────────────

CREATE TABLE stories (
  id                    TEXT PRIMARY KEY,        -- ULID; legacy imports keep the old 16-hex key
  cluster_key           TEXT REFERENCES clusters(key),
  status                TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft','checked','context','enriched','generated','ready','published','archived')),
  category              TEXT,                    -- World, U.S., Business, Science, ...
  headline              TEXT,
  lede                  TEXT,
  truths_md             TEXT,
  probabilities_md      TEXT,
  possibilities_md      TEXT,
  lies_md               TEXT,
  concept_json          TEXT,                    -- Step 2 output
  context_json          TEXT,                    -- Step 3 output ("summon context")
  context_at            TEXT,
  enriched_at           TEXT,                    -- Step 4
  packages_json         TEXT,                    -- Step 5 raw model output, kept for regeneration diffs
  featured_media_id     TEXT,
  featured_image_credit TEXT,
  overlay_color         TEXT,
  overlay_opacity       REAL,
  body_len              INTEGER,
  max_arts              INTEGER,
  version               INTEGER NOT NULL DEFAULT 1,
  created_by            TEXT NOT NULL,
  created_at            TEXT NOT NULL,
  updated_at            TEXT NOT NULL,
  published_edition     TEXT                     -- edition date when first published
);
CREATE INDEX stories_status ON stories(status, updated_at DESC);
CREATE INDEX stories_cluster ON stories(cluster_key);

CREATE TABLE story_sources (
  id            INTEGER PRIMARY KEY,
  story_id      TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  position      INTEGER NOT NULL,
  item_id       TEXT REFERENCES items(id),
  url           TEXT NOT NULL,
  title         TEXT,
  publisher     TEXT,
  published_at  TEXT,
  excerpt       TEXT,
  content_text  TEXT,                            -- filled by Step 4 (enrich)
  kind          TEXT NOT NULL CHECK (kind IN ('cluster','window','eventregistry','exa','manual')),
  enriched_at   TEXT,
  UNIQUE (story_id, url)
);

CREATE TABLE story_revisions (
  id            INTEGER PRIMARY KEY,
  story_id      TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
  version       INTEGER NOT NULL,
  reason        TEXT NOT NULL,                   -- 'generate','rewrite:truths','edit','punch-up','revise','import'
  snapshot_json TEXT NOT NULL,                   -- full stories row at that version
  created_by    TEXT NOT NULL,
  created_at    TEXT NOT NULL,
  UNIQUE (story_id, version)
);

-- ── Media (R2-backed) ───────────────────────────────────────────────────────

CREATE TABLE media (
  id          TEXT PRIMARY KEY,                  -- ULID; the R2 key is media/<id>.<ext>
  r2_key      TEXT NOT NULL UNIQUE,
  mime        TEXT NOT NULL,
  width       INTEGER,
  height      INTEGER,
  bytes       INTEGER NOT NULL,
  sha256      TEXT NOT NULL,
  source      TEXT NOT NULL CHECK (source IN ('upload','recraft','commons','legacy','url')),
  source_url  TEXT,
  credit      TEXT,
  license     TEXT,
  alt         TEXT,
  gen_prompt  TEXT,                              -- for recraft
  gen_model   TEXT,
  gen_style   TEXT,
  created_by  TEXT NOT NULL,
  created_at  TEXT NOT NULL
);
CREATE INDEX media_sha ON media(sha256);

-- ── Today overview and fun facts ────────────────────────────────────────────

CREATE TABLE today_overviews (
  id            INTEGER PRIMARY KEY,
  text_md       TEXT NOT NULL,
  is_current    INTEGER NOT NULL DEFAULT 0,
  generated_by  TEXT,                            -- model or editor email
  ai_call_id    INTEGER,
  created_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX today_current ON today_overviews(is_current) WHERE is_current = 1;

CREATE TABLE fun_facts (
  id            INTEGER PRIMARY KEY,
  for_date      TEXT NOT NULL,                   -- YYYY-MM-DD
  text          TEXT NOT NULL,
  source_title  TEXT,
  source_url    TEXT,
  chosen        INTEGER NOT NULL DEFAULT 0,
  ai_call_id    INTEGER,
  created_at    TEXT NOT NULL
);
CREATE INDEX fun_facts_date ON fun_facts(for_date, chosen);

-- ── Editions (published, immutable) ─────────────────────────────────────────

CREATE TABLE editions (
  date              TEXT PRIMARY KEY,            -- YYYY-MM-DD (UTC), matches public URL
  status            TEXT NOT NULL DEFAULT 'published' CHECK (status IN ('published','unpublished')),
  published_at      TEXT NOT NULL,
  published_by      TEXT NOT NULL,
  lineup_id         TEXT REFERENCES lineups(id),
  today_text_md     TEXT,                        -- frozen copy
  fun_fact_text     TEXT,
  fun_fact_source_url TEXT,
  story_count       INTEGER NOT NULL,
  snapshot_r2_key   TEXT NOT NULL,               -- editions/<date>.json: the exact payload the app renders
  notes             TEXT
);

CREATE TABLE edition_stories (
  edition_date   TEXT NOT NULL REFERENCES editions(date) ON DELETE CASCADE,
  position       INTEGER NOT NULL,
  story_id       TEXT NOT NULL REFERENCES stories(id),
  story_version  INTEGER NOT NULL,
  slug           TEXT NOT NULL,                  -- unique within the edition; public permalink segment
  headline       TEXT NOT NULL,
  snapshot_json  TEXT NOT NULL,                  -- the story as published (sections html, image url, credit, overlay)
  PRIMARY KEY (edition_date, position),
  UNIQUE (edition_date, slug)
);

-- ── Backstory registry (own publish clock) ──────────────────────────────────

CREATE TABLE backstory_rows (
  id               TEXT PRIMARY KEY,             -- imported ids kept
  position         INTEGER NOT NULL,             -- display order
  title            TEXT NOT NULL,
  stratum          TEXT,
  indicator        TEXT,
  start_date       TEXT,                         -- YYYY-MM-DD; clocks compute at render
  start_line       TEXT,
  narrative_md     TEXT,
  milestone        TEXT,
  close_condition  TEXT,
  roots_json       TEXT NOT NULL DEFAULT '[]',
  subgenres_json   TEXT NOT NULL DEFAULT '[]',
  objects_json     TEXT NOT NULL DEFAULT '[]',
  instances_json   TEXT NOT NULL DEFAULT '[]',
  photo_media_id   TEXT REFERENCES media(id),
  verified         INTEGER NOT NULL DEFAULT 0,
  status           TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','retired')),
  updated_by       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);

CREATE TABLE backstory_publishes (
  id              INTEGER PRIMARY KEY,
  published_at    TEXT NOT NULL,
  published_by    TEXT NOT NULL,
  row_count       INTEGER NOT NULL,
  snapshot_r2_key TEXT NOT NULL                  -- backstory/<id>.json; the public tab reads the latest
);

-- ── Reader suggestions ──────────────────────────────────────────────────────

CREATE TABLE suggestions (
  id           INTEGER PRIMARY KEY,
  text         TEXT NOT NULL,
  url          TEXT,
  contact      TEXT,                             -- optional, reader-provided
  ip_hash      TEXT,
  status       TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','reviewed','added','dismissed')),
  cluster_key  TEXT REFERENCES clusters(key),
  reviewed_by  TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX suggestions_status ON suggestions(status, created_at DESC);

-- ── Runs, steps, AI accounting ──────────────────────────────────────────────

CREATE TABLE runs (
  id                    TEXT PRIMARY KEY,        -- ULID
  kind                  TEXT NOT NULL CHECK (kind IN ('scan','full','publish','backstory_publish','story_step','import','manual')),
  trigger               TEXT NOT NULL CHECK (trigger IN ('cron','manual','api','workflow')),
  status                TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed','cancelled','skipped')),
  workflow_instance_id  TEXT,
  triggered_by          TEXT NOT NULL,           -- 'cron' or an email / service token name
  started_at            TEXT,
  finished_at           TEXT,
  summary_json          TEXT,                    -- counts: feeds ok/failed, items new, clusters, triaged, promoted, ...
  error                 TEXT
);
CREATE INDEX runs_recent ON runs(started_at DESC);

CREATE TABLE run_steps (
  id           INTEGER PRIMARY KEY,
  run_id       TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,                    -- ingest, cluster, triage, ledger, assembly, promote, render, purge
  status       TEXT NOT NULL,
  started_at   TEXT,
  finished_at  TEXT,
  metrics_json TEXT,
  log_r2_key   TEXT                              -- logs/<run_id>/<step>.txt when large
);
CREATE INDEX run_steps_run ON run_steps(run_id);

CREATE TABLE ai_calls (
  id              INTEGER PRIMARY KEY,
  run_id          TEXT REFERENCES runs(id),
  story_id        TEXT,
  purpose         TEXT NOT NULL,                 -- triage, ledger_diff, jefferson:truths, today, fun_fact, rewrite, ...
  provider        TEXT NOT NULL,                 -- anthropic, recraft
  model           TEXT NOT NULL,
  prompt_id       TEXT,
  prompt_version  INTEGER,
  tokens_in       INTEGER,
  tokens_out      INTEGER,
  cost_usd        REAL,
  latency_ms      INTEGER,
  gateway_log_id  TEXT,                          -- AI Gateway log id for drill-down
  status          TEXT NOT NULL,                 -- ok, error, cached
  error           TEXT,
  created_at      TEXT NOT NULL
);
CREATE INDEX ai_calls_at ON ai_calls(created_at DESC);
CREATE INDEX ai_calls_run ON ai_calls(run_id);

-- ── Prompts, settings, redirects ────────────────────────────────────────────

CREATE TABLE prompts (
  id          TEXT NOT NULL,                     -- triage_rubric, ledger_diff, jefferson_truths, jefferson_probabilities,
                                                 -- jefferson_possibilities, jefferson_lies, concept_check, summon_context,
                                                 -- today_overview, fun_fact, assembly_slot_plan, punch_up, revise
  version     INTEGER NOT NULL,
  body        TEXT NOT NULL,
  notes       TEXT,
  is_active   INTEGER NOT NULL DEFAULT 0,
  created_by  TEXT NOT NULL,
  created_at  TEXT NOT NULL,
  PRIMARY KEY (id, version)
);
CREATE UNIQUE INDEX prompts_active ON prompts(id) WHERE is_active = 1;

CREATE TABLE settings (
  key         TEXT PRIMARY KEY,                  -- live_edition, models.triage, models.ledger, models.jefferson,
                                                 -- limits.body_len, limits.max_arts, lineup.max, scan.window_hours, ...
  value_json  TEXT NOT NULL,
  updated_by  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

CREATE TABLE redirects (
  from_path   TEXT PRIMARY KEY,                  -- exact path or prefix ending in /*
  to_path     TEXT NOT NULL,                     -- may contain :splat
  status      INTEGER NOT NULL DEFAULT 301,
  note        TEXT,
  created_at  TEXT NOT NULL
);

-- Seed rows that the application relies on existing.
INSERT INTO settings (key, value_json, updated_by, updated_at) VALUES
  ('live_edition',        'null',                 'migration', '2026-09-11T00:00:00Z'),
  ('models.triage',       '"claude-haiku-4-5"',   'migration', '2026-09-11T00:00:00Z'),
  ('models.ledger',       '"claude-sonnet-5"',    'migration', '2026-09-11T00:00:00Z'),
  ('models.jefferson',    '"claude-sonnet-5"',    'migration', '2026-09-11T00:00:00Z'),
  ('models.today',        '"claude-sonnet-5"',    'migration', '2026-09-11T00:00:00Z'),
  ('models.fun_fact',     '"claude-haiku-4-5"',   'migration', '2026-09-11T00:00:00Z'),
  ('limits.body_len',     '4000',                 'migration', '2026-09-11T00:00:00Z'),
  ('limits.max_arts',     '15',                   'migration', '2026-09-11T00:00:00Z'),
  ('lineup.max',          '12',                   'migration', '2026-09-11T00:00:00Z'),
  ('scan.window_hours',   '6',                    'migration', '2026-09-11T00:00:00Z'),
  ('promote.min_publishers', '2',                 'migration', '2026-09-11T00:00:00Z');

INSERT INTO redirects (from_path, to_path, status, note, created_at) VALUES
  ('/digest/latest',   '/today',          301, 'legacy front door',           '2026-09-11T00:00:00Z'),
  ('/digest/v2',       '/today',          301, 'legacy front door',           '2026-09-11T00:00:00Z'),
  ('/digest/v2/*',     '/digest/:splat',  301, 'legacy v2 permalinks',        '2026-09-11T00:00:00Z'),
  ('/digest/index.html','/today',         301, 'file path to clean path',     '2026-09-11T00:00:00Z');
