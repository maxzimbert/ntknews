---
id: T-0006
title: Two Netlify sites build from this repo, so every deploy runs twice
status: DECIDED
tags: [infra, chore]
anchor: netlify.toml
---

## What

Verified 2026-09-16: `rainbow-sherbet-b2f0e9.netlify.app` and
`ntknewscms.netlify.app` both serve production, and both built a deploy preview
for PR #2. Those two and `ntknews.org` return byte-identical content.

## Why

Ongoing build spend, doubled, for no benefit, on an account where a deploy
flood already consumed roughly 250 credits. API and build spend is a live
constraint on this project and this is the easiest unit of it to recover.

**Before deleting either, confirm in the Netlify dashboard which site holds the
`ntknews.org` custom domain.** Content hashes cannot distinguish them — that is
the whole trap — and deleting the wrong one takes the site down.

This check is honestly manual. Netlify site ownership is not observable from
the repository, and a check that pretended otherwise would be exactly the kind
of decorative assertion this system exists to stop.

## Check

manual: the Netlify dashboard lists one site building from maxzimbert/ntknews, and it holds the ntknews.org domain
