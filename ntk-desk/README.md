# NTK Desk — Slices 1 + 2 (Layers 1–4, 6 + Desk view)

The surveillance-and-triage layer that replaces the EventRegistry center column:
own the firehose (91 publishers polled directly), cluster locally, score by
discussion velocity instead of coverage volume, triage with the NTK rubric,
diff every new article against the story's ledger of known facts, and present
five piles to the editor. Taste as a rubric, run by a model, against a
firehose. You certify; the machine reads everything.

> **Deploying?** `HANDOFF.md` contains step-by-step execution orders written
> for a model operator. Follow it exactly; this README is background.

## What's here

| File | Layer | What it does |
|---|---|---|
| `feeds.json` | — | Feed registry. **Starter set — port your 91 publishers in.** |
| `ingest.py` | 1 | Polls RSS/Atom/Google News sitemaps → rolling 48h `data/window.json` |
| `cluster.py` | 2 | TF-IDF + entity clustering → scored `data/clusters.json` (velocity, diversity, angle) |
| `ledger.py` | 3 | **The Story Ledger.** Sonnet diffs new items against known facts → DEVELOPMENT / INCREMENT / RECYCLED + unique contribution + first-reported-by credits. Persistent across the window (`data/ledgers.json`), 14-day expiry. `--mock` for offline dry runs. |
| `triage.py` | 4 | Claude Haiku verdicts (YES/MAYBE/NO + rationale + pillars + anchor + scoop-or-pablum on solo stories), cached |
| `desk.html` | 6 | The Desk view: **Developments** / Heating / Fresh / Angles / Killed |
| `.github/workflows/desk.yml` | — | Cron every ~20 min: ingest → cluster → triage → ledger → commit |

The ledger diff runs ONLY on triage survivors (YES/MAYBE) with un-diffed
items, capped at 15 Sonnet calls/run. It judges headline + RSS summary — not
full bodies — with "judge on evidence" as a hard rule; full-body diffing
arrives with the fetch layer (Slice 3). **The DIFF_PROMPT in ledger.py and the
RUBRIC in triage.py are editorial instruments — the editor's red pen applies
to them, nobody else's.**

## Install (10 minutes)

1. **Upload this folder** to the repo root as `ntk-desk/` (GitHub → Upload files —
   these are past the web-editor size comfort zone). The workflow file must land at
   `.github/workflows/desk.yml` **at repo root**, not inside ntk-desk — move it there.
2. **Add the secret:** repo → Settings → Secrets and variables → Actions →
   New repository secret → name `ANTHROPIC_API_KEY`. Exact caps, underscore —
   same discipline as the Netlify env vars.
3. **Port your feeds:** replace the starter set in `feeds.json` with your 91
   (the rss-scanner's 62 are the head start). For publishers with dead RSS, try
   `type: "sitemap"` pointed at their Google News sitemap (usually
   `/news-sitemap.xml` — check `robots.txt` for the path).
4. **Validate feeds** before trusting the cron:
   `python ingest.py --validate` locally, or add a one-off validate step to the
   workflow. Fix anything marked DEAD/EMPTY. The starter URLs are best-effort —
   verify every one.
5. **First run:** Actions → NTK Desk → Run workflow. Then open
   `https://maxzimbert.github.io/ntknews/ntk-desk/desk.html`.

The shipped `data/` contains demo fixture output so desk.html renders
immediately; the first real run replaces it (and auto-prunes the demo
triage cache).

## Operating notes

- **Cost:** triage capped at 25 Haiku calls/run; ledger capped at 15 Sonnet
  calls/run, only on triage survivors with un-diffed items, incremental by
  item (each article is diffed once, ever). Expected total: roughly $2–6/day
  at 91 feeds.
- **The Killed pile is the tuning loop.** If good stories land there, the
  rubric in `triage.py` needs your red pen — it's a prompt, not code. If your
  rss-scanner verdict prompt is better, swap it into `RUBRIC`; the plumbing
  doesn't care.
- **The Developments pile is the product promise.** If increments show up
  there, the DIFF_PROMPT in `ledger.py` needs tightening — that prompt is the
  no-increments rule, executable.
- **Velocity math:** `velocity` = distinct publishers in the last 6h;
  `diversity` = distinct publishers over the cluster's life;
  `score = velocity*3 + diversity`. Tune in `cluster.py`.
- **Clustering thresholds** (`SIM_THRESHOLD` 0.22, `ENTITY_ASSIST` 0.12,
  `MERGE_THRESHOLD` 0.30) are calibrated on fixtures. Real-world tuning: if
  distinct stories merge, raise; if one story splits, lower. Watch the first
  week.
- **Repo hygiene:** the cron commits `data/` every ~20 min. That's ~70
  commits/day of small JSON — fine for a working repo, but if history bloat
  bothers you later, move data commits to a `desk-data` branch or repo.
- **Offline dry run:** `python ingest.py --fixtures fixtures/sample-window.json
  && python cluster.py && python triage.py && python ledger.py --mock`
  (then wave 2: same with `fixtures/sample-window-wave2.json`)

## What this doesn't replace yet

- **EventRegistry** stays for full article **body fetching** into the synthesis
  pipeline (paywalls/bot-blocking are solved problems there) and out-of-network
  discovery. Decision rule: after a month, check what fraction of certified
  stories needed an ER body fetch. Small fraction → cancel.
- **Exa** stays for breaking news beyond the 91.
- Destination: the Desk view replaces the center firehose column on the
  ntk-production certification screen (Slice 3).
