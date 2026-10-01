# 08 — Launch checklist

## Before staging

- [ ] `ntknews.org` zone active on Cloudflare (nameservers switched, records replicating Netlify)
- [ ] Zero Trust: Access apps for admin (prod, staging), Google IdP, OTP fallback, policy emails, one service token
- [ ] D1, R2, KV, Queues, Workflows, DO created for staging and production; ids in `wrangler.toml`
- [ ] Secrets set in both environments (Anthropic, Recraft, EventRegistry, Exa, Turnstile, purge token)
- [ ] AI Gateway `ntknews` and `ntknews-staging` created; logging on; cost tracking on
- [ ] Turnstile site key/secret for the suggestion form
- [ ] Analytics Engine dataset `ntknews_metrics`
- [ ] `deploy.yml` with `CLOUDFLARE_API_TOKEN` repo secret; PR deploys to staging

## Staging sign-off

- [ ] Migrations applied; import rehearsal counts match `06-migration-cutover.md`
- [ ] Parity test suite green
- [ ] Full editorial cycle done by Max on staging, including publish and rollback
- [ ] Two scheduled scans and one full run succeeded on staging
- [ ] Public URL table verified; ten legacy links 301 → 200
- [ ] Lighthouse `/today` under 400 KB, no console errors
- [ ] Access denial verified for a non-listed email

## Production

- [ ] Production import run; counts verified
- [ ] Parallel run week: Cloudflare cron on, Actions still on, daily comparison noted in `runs.summary_json`
- [ ] Editors switched to `/admin`; old Pulse marked read-only (banner)
- [ ] DNS TTL lowered to 300 s two days before cutover
- [ ] Cutover: record flipped to the Worker custom domain; smoke test from two networks
- [ ] Purge verified: publish shows within 60 s from a cold region

## Decommission (one week after cutover, no incidents)

- [ ] GitHub Actions pipeline workflows deleted
- [ ] GitHub Pages disabled
- [ ] Netlify builds stopped, then site deleted
- [ ] Legacy directories removed; commit tagged `legacy-final`
- [ ] Repository visibility decided (private recommended)
- [ ] Old Pulse `localStorage` tokens: Max revokes the GitHub personal token that Pulse used

## Ownership

Max owns editorial sign-off and the domain registrar. The implementer owns
everything under Cloudflare and the repository until handover, then Max (or
whoever he names) is added as account admin.
