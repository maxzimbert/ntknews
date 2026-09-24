---
id: T-0044
title: A Jefferson section generation call can fail with "content blocks: empty" and no other diagnosis
status: PROPOSED
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html:582
---

## What

Reported by the editor 2026-09-24: a story that had just been re-enriched
with 5+ real sources still failed to generate, with the section showing
`[Generation failed: No text content in response (content blocks: empty)]`.
The same story had generated successfully on an earlier attempt.

`ai()` (`ntk-pulse/pulse.html:550`) throws this exact message when the
Anthropic response has `d.content` as an empty array and no `d.error` —
see the `types.join(', ') || 'empty'` fallback at line 581. The comment
directly above it (line 560) documents one known cause of a similar
message — thinking silently consuming the whole token budget — but that
comment specifically describes `content blocks: thinking`, a non-empty
array containing a thinking block. An *empty* array is a different shape:
the API returned 200 with no error and genuinely nothing back.

**Checked and ruled out:** status.claude.com showed no incident covering
today at the time this was written — the most recent listed incident
(elevated errors on specific models, 2026-09-22) had already resolved.
So this isn't a known, ongoing outage.

**Not yet diagnosed**, because nothing in this repo captures the raw
Anthropic response on failure — `ai()` throws a message string, not the
response body, and the call happens client-side in the editor's browser,
which no log here can see. Genuinely candidate causes, none confirmed:
a moderation-style refusal on hard-news content (war, sabotage,
disinformation) that returns empty rather than an `error` object; a
transient issue specific to the hours right after adding fresh API
credits; or something else this ticket doesn't have enough information
to name.

## Why

Two things are true at once: the failure is real and reproducible enough
to have hit twice in one session, and there is currently no way to learn
more about it from this repo — every existing safeguard in `ai()` (the
thinking-disabled fix, the block-type filter) was built by reading a
raw response that led to a specific fix; this one doesn't have that yet.
Guessing at a fix without the response body risks exactly the failure
mode `docs/decisions.md` and this project's history both warn about:
a patch that looks sufficient and isn't.

**Not a total loss in the meantime.** `reviseSection()`
(`ntk-pulse/pulse.html:1975`) already exists as a per-section retry —
called with no note, it regenerates just the failed section without
touching the other three or losing the story's sources. The editor does
not need to lose real work to one failed section.

**What would unblock this:** the raw response body from the browser's
network tab the next time it happens — right-click the failed
`/v1/messages` request in DevTools → Copy Response. With that in hand,
`ai()` can either surface the real cause (if the API sent one under a key
this code doesn't check) or this ticket can record confirmation that it's
a genuine, unexplained empty response worth an Anthropic support ticket.

## Check

```sh
manual: the editor captures a raw API response the next time this recurs,
or confirms it hasn't recurred after N more Pulse sessions; promote to
DECIDED once a cause is confirmed, or DISCARDED if it turns out to be
non-reproducible.
```
