---
id: T-0006
title: Two Netlify sites build from this repo, so every deploy runs twice
status: VERIFIED
tags: [infra, chore]
anchor: netlify.toml
---

## What

Verified 2026-09-16 as a defect: `rainbow-sherbet-b2f0e9.netlify.app` and
`ntknewscms.netlify.app` both served production, both built a deploy preview
for PR #2, and both returned byte-identical content alongside `ntknews.org`.

**Resolved 2026-09-17.** Max disabled `ntknewscms` from the Netlify dashboard.
Confirmed the same day: PR #3 built exactly one deploy preview, `ntknewscms`
now returns 404, and `ntknews.org` still returns 200 on `/` and `/today` — so
the site that holds the custom domain is the one still running.

## Why

Ongoing build spend, doubled, for no benefit, on an account where a deploy
flood had already consumed roughly 250 credits. API and build spend is a live
constraint on this project and this was the easiest unit of it to recover.

The recorded caution was that content hashes cannot distinguish the two sites,
so confirming which one holds the `ntknews.org` domain had to happen *before*
touching either — deleting or disabling the wrong one takes the site down. That
caution was honored and the verification below is what closed it.

**This ticket started life with `check: manual`**, on the grounds that Netlify
site ownership is not observable from the repository. That was correct at the
time and it is worth recording why it changed: the *dashboard* still cannot be
read from here, but the *consequence* can. One site serving and the other not
is observable over HTTP, and that is the property that actually matters. When a
manual check can be replaced by an outcome check, replace it — but not by
inventing a proxy that would have passed while the defect was live. This one
would have failed on 2026-09-16.

The dashboard remains the authority on which sites exist. This check only
asserts that the outcome is still right.

## Check

```sh
live=$(curl -s -o /dev/null -w '%{http_code}' -m 20 https://ntknews.org/today)
dupe=$(curl -s -o /dev/null -w '%{http_code}' -m 20 https://ntknewscms.netlify.app/)
[ "$live" = "200" ] || { echo "ntknews.org/today returned $live"; exit 1; }
[ "$dupe" = "200" ] && { echo "ntknewscms.netlify.app is serving again ($dupe)"; exit 1; }
exit 0
```
