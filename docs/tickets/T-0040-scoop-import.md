---
id: T-0040
title: A single-outlet scoop has no way into the lineup
status: BUILT
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html:2365
---

## What

Requested directly by the editor: when one outlet breaks something big —
an NPR investigation, a single-source financial scoop — there needs to
be a way to generate Jefferson on that one article even though it will
never clear corroboration.

Measured 2026-09-23, before this change: `certify(cluster)`
(`ntk-pulse/pulse.html:1113`) does not check publisher count, triage
verdict, or provenance — any cluster shape reaches the lineup and
Jefferson generation once certified. So the actual gap was never
Jefferson itself; it was getting a single-source story *into* a
certifiable cluster in the first place. The only two paths into MANUAL
were `mergeSelected()` (needs 2+ clusters already selected from the
stream) and `extractSelected()` (needs 1+ items already sitting inside
an *existing* stream cluster). Neither covers a scoop that was never
ingested by the 97 RSS feeds at all — the normal case for "editor read
this on the outlet's own site this morning."

Added `newManualFromUrl()` and a persistent "add a one-source scoop as a
candidate" input at the top of the Stream panel. It fetches the page via
the existing `fetchUrlBody()` (same call `addUrlToManual` already makes)
and creates a one-item MANUAL cluster, tagged `Editor import`, that
certifies into the lineup exactly like any organic candidate.

## Why

Deliberately did not build a separate "generate Jefferson on a single
article" code path. Jefferson generation already doesn't care how many
sources a lineup story has — `makePrompt()` just takes whatever
`articlesText` the story has. Building a parallel single-article
generation path would have duplicated real machinery (the same craft
rubric, the same visual-marker system, the same section prompts) to
solve a problem that was actually one level upstream, in candidate
intake, not in generation.

Did not fetch and store full body text on the manual-cluster item at
creation time. `addUrlToManual()` — the existing, already-shipped
pattern this mirrors — only stores `title` from `fetchUrlBody()`, not
`body`; real body enrichment happens later, at the lineup-story level,
via the existing "add a source URL" control inside an opened story
(`addUrl()`, `pulse.html:1669`). Matching that existing division of
labor rather than inventing a second one. This also means a scoop's
Jefferson quality benefits directly from T-0038 (punch-up and downstream
generation now read `a.body` once it's fetched at the lineup-story
step).

Did not add a publisher-count or triage floor to this path on purpose —
the whole point is that a real scoop, by definition, often has exactly
one source. Gating it would recreate the problem it exists to route
around.

## Check

```sh
set -e

# The function exists and doesn't gate on publisher count or triage —
# certify() already doesn't, and this shouldn't invent a second standard.
grep -q "async function newManualFromUrl" ntk-pulse/pulse.html
awk '/async function newManualFromUrl/{f=1} f{print} f&&/^\}/{exit}' ntk-pulse/pulse.html \
  | grep -qv "publisher_count" # should find nothing — no such gate

# The UI control is wired into the Stream panel, not buried in a
# per-cluster action that only appears once something else already exists.
grep -q "scoop-add-in" ntk-pulse/pulse.html
grep -q "scoop-add-go" ntk-pulse/pulse.html

# Reuses fetchUrlBody rather than a second fetch implementation.
awk '/async function newManualFromUrl/{f=1} f{print} f&&/^\}/{exit}' ntk-pulse/pulse.html \
  | grep -q "fetchUrlBody"

# pulse.html's inline script still parses.
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' ntk-pulse/pulse.html > /tmp/pulse-t0040-check.js
node --check /tmp/pulse-t0040-check.js
rm -f /tmp/pulse-t0040-check.js
```

**Not yet confirmed live** — no way to fetch a real URL or exercise the
browser UI from this environment. Editor should paste a real single-
source scoop URL into the new field in a real Pulse session, confirm it
becomes a certifiable candidate, certify it, and confirm Jefferson
generates on it normally before this is promoted to VERIFIED.
