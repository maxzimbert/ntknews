---
id: T-0053
title: Backstory permalink pages show a bare "NTK" text link, not the logo, and link to a root path
status: DECIDED
tags: [backstory, defect]
anchor: digest/index.html:2100
---

## What

Low priority. Reported by the editor 2026-10-01 after testing the staged
Backstory pages (T-0046, PR #38). Confirmed in the staged HTML the same day
(`backstory/equality/index.html`):

- The header is `<header><a href="/backstory">NTK</a></header>`: plain text,
  no logo. The editor wants the NTK logo. The logo already exists as an inline
  SVG in the app header (`digest/index.html:2100`, class `ntk-logo`); there is
  no standalone logo file tracked in the repo (checked 2026-10-01), so the
  generator has to extract or inline it.
- The page has exactly two links, the header and "← All of Backstory" at the
  bottom, and both go to `/backstory`. On ntknews.org that path is a Netlify
  rewrite to the SPA's Backstory tab (`netlify.toml`). On the staging copy it
  resolves to `maxzimbert.github.io/backstory`, which does not exist.

**Staging artifact versus product defect, kept separate.** The root-absolute
`/backstory` links are correct on ntknews.org and wrong only on the staging
copy, because GitHub Pages serves it from a subpath with no Netlify rewrites.
I have not seen the pages on ntknews.org: #38 is not merged, so they do not
exist there yet (unverified). The missing logo is a real product gap
either way.

**A question this ticket does not decide:** where a logo in the header should
go. Today the header and the footer link both go to the Backstory tab. A logo
conventionally goes home (`/today` or `/`). Editor's call.

## Why

The Backstory pages are what a shared link or a search result lands on, so
for many readers the header is their first sight of NTK. A bare text link
looks like a different product from the app's own header. Low priority
because the pages work and read correctly; this is brand polish, not
function.

Ruled out for the staging links: rewriting the generator's `/backstory` links
to relative paths. That would still 404 on staging, since the SPA routes
(`/today`, `/backstory`, `/me`) exist only as Netlify rewrites, and it would
make the production URLs less obviously canonical. If staging links matter
later, give the staging build a base path or a 404 fallback; do not change
production markup for it.

## Check

```sh
set -e
[ -f backstory/equality/index.html ] || {
  echo "backstory/ pages are not on main yet (T-0046, PR #38)"; exit 1; }
# The header link wraps an image or svg, not bare text.
grep -Eq '<header>[[:space:]]*<a [^>]*>[[:space:]]*<(img|svg)' backstory/equality/index.html
```
