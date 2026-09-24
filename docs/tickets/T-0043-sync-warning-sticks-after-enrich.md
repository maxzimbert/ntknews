---
id: T-0043
title: The "no source material" warning stays up after a story is successfully re-sourced
status: BUILT
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html:3034
---

## What

Reported by the editor 2026-09-24, seen live: a lineup story showed the red
"⚠ no source material" bar, they generated its Jefferson package
successfully anyway, then on a second story got the same bar, re-enriched
it with 5+ real sources, and the bar stayed up.

`story.syncFailed` is set once, at `materializeEditionStory()`
(`ntk-pulse/pulse.html:3466`), when the story's original cluster key
can't be found in the current 6-hour stream window and no reconnect match
is found either. It is cleared in exactly one place —
`acceptReconnect()` (`ntk-pulse/pulse.html:3480`), the "use this" button
on the *separate* reconnect-suggestion banner. Nothing clears it when the
editor instead brings in real sources through search, add-URL, or
`enrich()` — none of those three touch the flag. The bar's own text
("won't work until real sources are attached") becomes false the moment
sources are attached, but the bar doesn't know that.

Fixed by gating the render on live state instead of the stale flag alone:
the bar now shows only when `s.syncFailed` is set **and** the story
genuinely has no active sources (`activeArts(s).length === 0`) —
the same predicate `generateStory()` and `draftMeta()` already use to
decide whether generation can proceed. `syncFailed` itself is left
untouched, including its only other reader; this is a one-line read-side
fix, not a data-model change.

## Why

The warning was never actually blocking anything — Draft/Enrich/Generate
already check `activeArts(story).length` themselves and work fine once
sources exist, which is why the editor's first story generated Jefferson
successfully despite the bar. But a warning that says "this won't work"
next to a working button is exactly the kind of thing that erodes trust in
every other warning in the tool — the file's own header comment (line 61)
says the design intent is "loud by design" when something is genuinely
wrong; a loud warning that's wrong is the opposite of that.

Considered clearing the flag at the point of success inside `enrich()`
and `addUrl()` instead of gating the render. Rejected: three call sites
would all need the same one-line fix, `syncFailed` has exactly one other
reader total, and a story that loses its sources again later (all
articles suppressed or marked duplicate) should show the warning again —
gating on live state gets that behavior for free; clearing it once would
not.

## Check

```sh
grep -q 's.syncFailed && !activeArts(s).length' ntk-pulse/pulse.html
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' ntk-pulse/pulse.html > /tmp/pulse-t0043-check.js
node --check /tmp/pulse-t0043-check.js
rm -f /tmp/pulse-t0043-check.js
```
