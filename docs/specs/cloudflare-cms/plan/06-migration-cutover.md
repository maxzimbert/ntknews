# 06 — Migration and cutover

## Order of operations

1. **Zone.** Add `ntknews.org` to the Cloudflare account and move the
   nameservers at the registrar. Until the switch, Cloudflare DNS is set to
   proxy-off records pointing at Netlify exactly as today, so the move itself
   changes nothing for readers. This is the one step that cannot be rehearsed
   on staging and is a prerequisite for Access and custom domains.
   *Uncertain at the time of writing: whether the zone is already on
   Cloudflare. The inspection host could only resolve the A record
   (a Netlify address), not the nameservers.*
2. **Zero Trust.** Create the Access applications `ntknews-admin`
   (`ntknews.org/admin/*`, `ntknews.org/api/admin/*`) and the staging
   equivalent; identity provider Google plus one-time PIN; policy: allow
   listed emails; one service token for agents. Record the AUD tags in
   `wrangler.toml` vars.
3. **Resources.** `wrangler d1 create`, `r2 bucket create`,
   `kv namespace create`, `queues create` for staging and production; set
   secrets; `wrangler d1 migrations apply`.
4. **Staging deploy + import rehearsal.** Deploy to `staging.ntknews.org`,
   run `scripts/import-legacy.ts` against staging, verify every check in the
   section below.
5. **Production import.** Same script against production. Run it twice: once
   now, once again on cutover day for the delta (it is idempotent by key).
6. **Parallel run (one week).** Pipeline cron enabled on Cloudflare while the
   GitHub Actions workflows keep running. Compare `runs` summaries with the
   Actions logs daily. Editors use the new CMS; the old Pulse stays reachable
   read-only.
7. **Cutover.** Flip the `ntknews.org` A/CNAME record to the Worker custom
   domain (proxied). Netlify remains deployed and unchanged for one more
   week as the rollback path.
8. **Decommission.** Disable the GitHub Actions workflows (delete the YAML),
   disable GitHub Pages (Settings → Pages → Source: None), stop Netlify builds
   and then delete the Netlify site, remove legacy directories from the repo in
   one commit tagged `legacy-final`.

## Import script (`scripts/import-legacy.ts`)

Runs locally with `wrangler d1 execute --remote` batches and R2 puts via the
S3-compatible API or `wrangler r2 object put`. Input is a checkout of the
repo at tag `legacy-final` (or `main` before cleanup). Idempotent: every
insert is `INSERT OR REPLACE` keyed by the legacy id.

| Step | Source | Target | Verification |
|---|---|---|---|
| feeds | `ntk-pulse/feeds.json` | `feeds` | 97 rows; `enabled` matches `_disabled` |
| items | `ntk-pulse/data/window.json` | `items` | count equals `items` length in file |
| clusters | `ntk-pulse/data/clusters.json` | `clusters`, `cluster_items`, `item_entities`, `triage` | 263 clusters; every `triage` object became a row |
| triage cache | `ntk-pulse/data/triage-cache.json` | `triage` | rows keyed by `<key>:<size>:v5` all present |
| ledgers | `ledgers.json`, `ledger-classes.json` | `ledgers`, `ledger_items` | 629 ledgers |
| lineup | `lineup.json` | `lineups(auto)`, `lineup_entries`, `lineups(working)` | 43 entries; one current working lineup |
| published stories | `lineup-publish.json` | `stories`, `today_overviews` | 7 stories with all four sections |
| editions | `digest/v2/<date>/index.html` (`const stories` block), `_headlines.json`, story pages | `editions`, `edition_stories`, `stories` | 6 editions; slugs match directory names |
| images | base64 in edition HTML, `digest/v2/images/*.jpg` | `media` (`source='legacy'`), R2, legacy path map | every `og:image` URL in old story pages maps to a media id |
| backstory | `digest/v2/data/backstory.json` | `backstory_rows`, one `backstory_publishes`, R2 | 21 rows; public `/api/public/backstory` equals the file |
| prompts | strings in `triage.py`, `ledger.py`, `assembly.py`, `pulse.html` | `prompts` v1 active | one active version per prompt id |
| redirects | `netlify.toml` | `redirects` | 4 rows |

The `const stories = [...]` block in each frozen edition is JavaScript, not
JSON. The importer evaluates it in an isolated `vm` context with no globals
and validates the result with a zod schema before insert.

## Verification before cutover (on staging, then production)

- Every URL in the public route table returns the expected status and, for
  HTML, contains the expected headline for the date.
- `curl -I` on ten random old `/digest/v2/...` links shows 301 to a 200.
- Lighthouse on `/today`: transfer under 400 KB, no console errors.
- The stream shows the same top ten clusters as `clusters.json` sorted by
  `pulse_score` at import time.
- A full editorial cycle on staging: promote a cluster, run the five steps,
  pick an image, publish, view on staging, roll back, view again.
- A scheduled scan and a full run complete on staging with `succeeded`.
- Access: an email not on the policy gets the Access denial page; a service
  token can call `POST /api/admin/runs`.

## Rollback plan

- Before decommission: change the DNS record back to Netlify. Netlify's last
  deploy is untouched. Time to effect: DNS TTL (set to 300 s before cutover).
- After decommission: redeploy the `legacy-final` tag to a new Netlify site
  and point DNS at it. Data created in the CMS after cutover is not
  reflected in the legacy site; that is accepted and is why decommission
  waits a week.

## Repository after cleanup

Kept: `src/`, `public/`, `migrations/`, `scripts/`, `test/`, `docs/`,
`wrangler.toml`, `package.json`, `README.md`, `legacy/` (one-off HTML tools,
not served). Removed: `ntk-pulse/`, `ntk-desk/`, `digest/`, `editorial/`,
`netlify/`, `netlify.toml`, `.github/workflows/pulse*.yml`, `desk.yml`,
`index.html` (now a template), `rss-scanner/`. The removal commit lands after
the import is verified on production and is tagged `legacy-final` so the
importer can always be re-run from a checkout.

## GitHub Actions after cutover

One workflow only: `deploy.yml` on push to `main` runs `pnpm test` and
`wrangler deploy` (production) with `CLOUDFLARE_API_TOKEN` as a repo secret;
pull requests deploy to staging. No bot commits ever again.
