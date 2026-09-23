---
id: T-0038
title: Both headline generators discard the body content they already have
status: BUILT
tags: [pulse, defect]
anchor: ntk-pulse/triage.py:116
---

## What

Measured 2026-09-23. `triage.py`'s `call_claude()` builds the HEADLINE
prompt's `headlines` block from `it['publisher']` and `it['title']` only
(`ntk-pulse/triage.py:116-118`) — it never reads `it['summary']`, even
though `ingest.py` writes up to 500 chars of RSS description onto every
item (`ntk-pulse/ingest.py:100-101`) and that field is sitting unused in
the same dict.

Separately, `punchUpHeadline()` in `pulse.html` builds its context from
`activeArts(story)` mapped to `a.title` only (`ntk-pulse/pulse.html:1493-1494`),
discarding `a.body` even though by the time an editor punches up a
headline the story has usually already been enriched with real fetched
article text sitting on that same field.

Net effect: both headline generators compress *other outlets' headlines*
into a headline, never the underlying facts. Punch-up isn't meaningfully
sharper than first-pass because it's reasoning over the same
headline-only input, just asked a second time with a different framing.

**Fixed and structurally confirmed** — `ntk-pulse/triage.py:115-124`
now folds `it['summary']` into the per-item line when present;
`punchUpHeadline()` in `ntk-pulse/pulse.html` now folds a 600-char slice
of `a.body` into the per-article context when present. Both files
compile/parse clean (check below). **Not yet confirmed against a real
model call** — no `ANTHROPIC_API_KEY` in this environment, and whether
the generated headlines actually read as sharper is an editorial
judgment only a real Pulse run can make. Promote to VERIFIED once the
editor runs a real triage pass and a real punch-up and agrees the output
improved; until then this is BUILT, not VERIFIED.

## Why

Raised directly by the editor: first-pass headlines are flat enough that
punch-up is being treated as a required second step rather than a rare
correction. The craft rubric in both places already asks for "stakes over
mechanism" and "stronger verb, when sources support it" — but a model
given only a handful of other publishers' headlines has nothing but their
own word choices to draw a sharper verb or a real stake from. That's a
data problem wearing a prompt-tuning problem's clothes.

The fix costs nothing new: `summary` is already collected by `ingest.py`
on every ingest run, and `a.body` is already fetched during enrichment
before an editor ever clicks "punch up." Both are being thrown away at
the exact prompt that most needs them.

Considered and rejected: rewriting the headline rubric's wording instead.
Ruled out because the rubric already states the right instructions (see
`docs/voice.md` §3) — the failure mode here is starvation of input, not
unclear instructions to the model.

## Check

```sh
set -e

# triage.py's rubric call must read summary, not just title, when building
# the per-item line the model sees.
awk '/^def call_claude/{f=1;print;next} f&&/^def /{exit} f' ntk-pulse/triage.py | grep -q "summary"

python3 -m py_compile ntk-pulse/triage.py

# punch-up must read the enriched body, not just the title, when present.
grep -n "async function punchUpHeadline" ntk-pulse/pulse.html >/dev/null
awk '/async function punchUpHeadline/{f=1} f{print} f&&/^\}/{exit}' ntk-pulse/pulse.html | grep -q "\.body"

# pulse.html's inline script must still parse after the edit.
awk '/<script>/{f=1;next}/<\/script>/{f=0}f' ntk-pulse/pulse.html > /tmp/pulse-script-check.js
node --check /tmp/pulse-script-check.js
rm -f /tmp/pulse-script-check.js
```
