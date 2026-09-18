---
id: T-0017
title: Five Strunk and White rules are missing from the prompts, and the worked example contradicts one of them
status: VERIFIED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html:741
---

## What

The editor asked for eleven Strunk and White rules across Pulse's prompts.
Measured against `GLOBAL` (`ntk-pulse/pulse.html:719`) and `VOICE_REF`
(`:741`) on 2026-09-18, six are already covered, in some cases more sharply
than Strunk states them: active voice by VOICE rule 7's banned signpost verbs,
concrete language by GLOBAL's STAKES & PLOT, omitting needless words by
GLOBAL's LENGTH, emphatic words last by VOICE rule 6, the paragraph as a unit
by `autoParagraph()`, and a suitable design by the four-section framework.

Five are absent: put statements in positive form, avoid a succession of loose
sentences, express coordinate ideas in similar form, keep related words
together, and in summaries keep to one tense.

The second of those is the one that matters, and the worked example the model
is told to study breaks it. Measured on the BODY example inside `VOICE_REF`,
sentence lengths in words run 16, 7, 26, 17, 4, 23, 24, 17, 7, 5, 3 — and the
example closes on three consecutive sentences under nine words.

`punchUpHeadline` (`:1400`) and `draftMeta` (`:1422`) compose their prompts
from scratch and include neither `GLOBAL` nor `VOICE_REF`.

## Why

`docs/decisions.md` records, as a correction dated 2026-09-17, that the
em-dash rule failed for a specific reason: the rule did not exist, and when
it was written the worked examples still contained 82 em dashes of their own.
The model was not ignoring an instruction, it was copying the demonstration.
Adding "avoid a succession of loose sentences" to a prompt whose exemplar
ends on three short declaratives in a row would reproduce that failure
exactly, one week later, with a different rule.

There is a second-order effect worth recording because it is not obvious. The
em-dash ban is three days old and its instruction is explicit: "If none of
the three works, the sentence is carrying two ideas and wants to be two
sentences." That systematically converts subordination into parataxis, which
is precisely the succession of loose sentences Strunk warns about, and it is
the most likely mechanical cause of the flatness the editor is trying to fix.

The ban is kept. `docs/decisions.md` says to measure the next digest before
touching the em-dash work, and restoring the dash to fix rhythm would trade a
formatting problem for a different formatting problem. The fix is a rhythm
rule plus an exemplar that varies sentence length, so instruction and
demonstration agree.

Not done here: rewriting the 52 em dashes in `SEC_PROMPTS`' instructional
text. That is held under the same decision, pending a measurement of output.

## Check

```sh
python3 - <<'PY'
import re, statistics, sys
s = open('ntk-pulse/pulse.html', encoding='utf-8').read()

g = re.search(r'const GLOBAL = `([\s\S]*?)`;', s)
v = re.search(r'const VOICE_REF = `([\s\S]*?)`;', s)
if not (g and v): sys.exit('GLOBAL or VOICE_REF not found')
shared = (g.group(1) + v.group(1)).lower()

for needle, name in [
    ('positive form',                'put statements in positive form'),
    ('succession of loose sentences','avoid a succession of loose sentences'),
    ('coordinate ideas',             'express coordinate ideas in similar form'),
    ('related words together',       'keep related words together'),
    ('one tense',                    'in summaries, keep to one tense'),
]:
    if needle not in shared: sys.exit('rule absent from the shared prompt: ' + name)

# The demonstration has to obey the rule it demonstrates.
b = re.search(r'BODY \(worked example[\s\S]*?:\s*"([\s\S]*?)"\s*\nDETAIL:', v.group(1))
if not b: sys.exit('the BODY worked example could not be located in VOICE_REF')
lens = [len(x.split()) for x in re.split(r'(?<=[.!?])\s+', b.group(1)) if x.strip()]
if len(lens) < 6: sys.exit('the worked example is too short to measure rhythm')
run = best = 0
for L in lens:
    run = run + 1 if L < 9 else 0
    best = max(best, run)
if best >= 3:
    sys.exit('the worked example runs %d sentences under nine words back to back' % best)
if statistics.pstdev(lens) < 4:
    sys.exit('the worked example has no sentence-length variation (pstdev %.1f)' % statistics.pstdev(lens))

# The standalone prompts inherit the voice instead of reinventing it.
for fn in ('punchUpHeadline', 'draftMeta'):
    m = re.search(r'async function %s\([\s\S]*?\n\}\n' % fn, s)
    if not m: sys.exit('%s not found' % fn)
    if 'VOICE_REF' not in m.group(0):
        sys.exit('%s does not carry VOICE_REF' % fn)
PY
```
