# HANDOFF — NTK Desk deployment orders

**Who this is for:** a model operator (e.g., Claude Code) executing on behalf of
Max, the editor. You are deploying a system that was designed and fixture-tested
elsewhere. Your job is execution and verification, not redesign.

## Rules of engagement

1. Follow the steps **in order**. Each step ends with a VERIFY block — do not
   proceed until it passes.
2. If a VERIFY fails, use the FAILURE BRANCH for that step. If no branch
   covers what you see, **stop and report the exact error output to Max**.
   Do not improvise fixes outside the branches.
3. **Protected files — never modify without Max's explicit instruction:**
   - `DIFF_PROMPT` string in `ledger.py` (this is an editorial instrument)
   - `RUBRIC` string in `triage.py` (same)
   - The four threshold constants in `cluster.py` (see Step 7 escalation rules)
4. Never run `ledger.py` or `triage.py` without `--mock` unless
   `ANTHROPIC_API_KEY` is confirmed set AND Max has approved live spend.
5. Report costs when asked: triage ≤25 Haiku calls/run, ledger ≤15 Sonnet
   calls/run, cron ~72 runs/day, expected $2–6/day total.

## Context (two sentences)

The NTK Desk polls Max's publisher list, clusters items into stories, has
Claude triage them against NTK's need-to-know rubric, and diffs each new
article against a persistent per-story ledger of known facts so increments
never reach the editor. Output is `desk.html` — five piles: Developments,
Heating, Fresh, Angles, Killed.

---

## STEP 0 — Preconditions

Confirm: (a) you have write access to the `maxzimbert.github.io` repo (or the
repo serving ntknews on GitHub Pages); (b) GitHub Actions is enabled on it;
(c) the `ntk-desk-slice2.zip` contents are available to you.

**VERIFY:** you can list the repo root and see the existing `ntknews/` content.

## STEP 1 — Place the files

1. Create `ntk-desk/` at the **repo root** and add: `feeds.json`, `ingest.py`,
   `cluster.py`, `triage.py`, `ledger.py`, `desk.html`, `README.md`,
   `HANDOFF.md`, `fixtures/` (both files), and `data/` (the demo JSON files
   ship inside; keep them — they make desk.html render before the first run).
2. Place the workflow at **`.github/workflows/desk.yml` at the repo root** —
   NOT inside ntk-desk/. GitHub only reads workflows from the root path.

**VERIFY:** `ls ntk-desk/` shows 5 .py/.json/.html files + README + HANDOFF +
2 dirs; `ls .github/workflows/` shows `desk.yml`.
**FAILURE BRANCH:** if `.github/workflows/` doesn't exist, create it.

## STEP 2 — Add the API secret

Repo → Settings → Secrets and variables → Actions → New repository secret.
Name: `ANTHROPIC_API_KEY` — exact capitalization, exact underscore. Value:
provided by Max out of band. Never write the key into any file or commit.

**VERIFY:** the secret appears in the Actions secrets list by name.

## STEP 3 — Port the feed list

1. Source of truth: Max's 91-publisher list; the `ntknews/rss-scanner/` feed
   list (62 feeds) is the head start — extract its feed URLs.
2. For each publisher, add an entry to `feeds.json`:
   `{"id": "<slug>", "name": "<display name>", "url": "<feed url>",
   "type": "rss", "tier": <1|2|3>, "market": "<national|intl|la|nyc|dc|chs>"}`
3. Tier and market: copy from Max's list if annotated; otherwise tier 2 and
   your best market guess, and flag guesses in your report.
4. If a publisher's RSS is dead or missing, check `https://<domain>/robots.txt`
   for a news sitemap (commonly `/news-sitemap.xml`) and use
   `"type": "sitemap"` with that URL.

**VERIFY:** `python -c "import json; f=json.load(open('ntk-desk/feeds.json'))['feeds']; print(len(f)); assert len({x['id'] for x in f})==len(f), 'duplicate ids'"` — count matches the ported list, no duplicate ids.

## STEP 4 — Validate the feeds

Run from `ntk-desk/`: `python ingest.py --validate`

**VERIFY:** every feed prints `OK` with a nonzero item count.
**FAILURE BRANCHES:**
- `DEAD` with HTTPError 403/404 → the URL is wrong or bot-blocked. Try the
  sitemap route (Step 3.4). If both fail, comment the feed out (move it to a
  `"_disabled"` list in feeds.json) and note it in your report.
- `DEAD` with URLError/timeout → retry once; if it persists, same as above.
- `EMPTY` → wrong `type` value. Flip rss↔sitemap and re-validate.
- `OK` but `(0 dated)` → items lack parseable dates; acceptable (ingest falls
  back to first_seen), but note it.

## STEP 5 — Offline dry run (no API spend)

From `ntk-desk/`, with the shipped demo `data/` **deleted first**
(`rm data/*.json`):

```
python ingest.py --fixtures fixtures/sample-window.json
python cluster.py
cp fixtures/sample-triage-cache.json data/triage-cache.json
python triage.py
python ledger.py --mock
python ingest.py --fixtures fixtures/sample-window-wave2.json
python cluster.py
cp fixtures/sample-triage-cache.json data/triage-cache.json
python triage.py
python ledger.py --mock
```

(The cache is copied twice because triage prunes stale fingerprints each run —
correct in production, but the dry run's second wave needs its entries back.)

(The copied cache supplies canned verdicts so triage runs without an API key —
it will print "applying cached verdicts only"; that is correct behavior.)

**VERIFY, in order:**
- first cluster run prints `12 items -> 5 clusters (3 multi-source)`
- first ledger run prints `4 live ledgers`
- second cluster run prints `15 items -> 6 clusters (4 multi-source)`
- final ledger run prints `4 live ledgers` and a nonzero development count
- the celebrity story has no ledger (NO verdict — Killed stories never get one)
- in `data/clusters.json`, the WTOP item titled "Reports: California now
  selling..." carries `"class": "RECYCLED"` and `"credits": ["Associated Press"]`

**FAILURE BRANCH:** any Python traceback → report it verbatim. Do not patch.

## STEP 6 — First live run

1. Commit and push everything.
2. GitHub → Actions → "NTK Desk" → Run workflow.
3. When it completes, confirm a bot commit ("desk: refresh ...") landed.

**VERIFY:**
- `ntk-desk/data/window.json` has hundreds of items (91 feeds × 48h)
- `ntk-desk/data/clusters.json` has clusters with `triage` verdicts populated
- `https://<pages-domain>/ntk-desk/desk.html` renders five piles with content
  (allow for GitHub Pages CDN propagation delay — verify on a real device,
  minutes later, per Max's standing note)
**FAILURE BRANCHES:**
- Workflow fails at Triage/Ledger with 401 → secret name/value wrong; redo Step 2.
- Workflow fails at Commit with permission error → repo Settings → Actions →
  General → Workflow permissions → "Read and write permissions".
- desk.html loads but shows the fetch error → data path mismatch; confirm
  desk.html and data/ are siblings inside ntk-desk/.

## STEP 7 — First-week monitoring (report, don't tune)

Once daily, compile for Max:
1. **Merge/split errors:** clusters containing two clearly different stories
   (over-merge), or one story split across clusters (under-split). Quote the
   titles. DO NOT change the constants in cluster.py yourself — Max approves
   threshold changes. (Known acceptable case: a story split across two
   clusters that share one ledger — the ledger is the story identity; note it,
   don't fix it.)
2. **Killed-pile audit:** any story in Killed that Max would have wanted.
   Quote title + the rationale the model gave.
3. **Developments-pile audit:** any item marked DEVELOPMENT whose what_new is
   not actually new. This is the no-increments promise — flag every case.
4. **Feed health:** any feed erroring in the Actions logs.
5. **Cost:** count Sonnet + Haiku calls from the run logs; estimate the daily rate.

Escalation rule: if any single run makes >25 Sonnet calls, or daily cost
estimate exceeds $10, stop the cron (disable the workflow) and report.

## STEP 8 — Done criteria

Deployment is complete when: all feeds validate or are consciously disabled;
the cron has run clean for 24 hours; desk.html renders all five piles with
live data; and the first daily monitoring report has been delivered to Max.

What comes after is NOT yours to start: ER/Exa demotion decisions (one-month
parallel-run data, Max decides), threshold tuning (Max approves), prompt
changes (Max's red pen), and Slice 3 integration into ntk-production
(designed elsewhere). 
