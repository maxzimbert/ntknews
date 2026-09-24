---
id: T-0044
title: A Jefferson section generation call can fail with "content blocks: empty" and no other diagnosis
status: VERIFIED
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html:582
---

## What

Reported by the editor 2026-09-24: a story that had just been re-enriched
with 5+ real sources still failed to generate, with the section showing
`[Generation failed: No text content in response (content blocks: empty)]`.
The same story had generated successfully on an earlier attempt.

**Diagnosed same day, by the editor, from a captured raw response:** this
is `stop_reason: "refusal"`, `stop_details.category: "bio"` — Anthropic's
safety classifier refusing the request. A refusal comes back as HTTP 200
with `content: []` and no `error` field, so `ai()`'s only existing check
(`if (d.error)`, line 572) never caught it, and every refusal fell
through to the generic empty-content message with nothing to say what
actually happened.

**Fixed:** `ai()` now checks `d.stop_reason === 'refusal'` immediately
after the `d.error` check and throws `Refused by the model (category:
${d.stop_details.category})` — falling back to the plain message if a
future refusal ever arrives without a category. Checked directly against
a mock of the editor's exact captured response (`stop_reason: 'refusal',
stop_details: {category: 'bio'}, content: []`) and it throws the new
message; checked separately against a refusal with no `stop_details` at
all, and against a normal successful response, so the added check can't
mask or break either of those.

**Not addressed here, and worth a separate conversation:** *why* the
classifier fires on stories written in a "worst version of events" Lies
section about hard news. That's an editorial/prompting question, not a
bug — this ticket only makes the failure legible instead of opaque.

## Why

The prior version of this ticket documented the symptom without a cause,
specifically because nothing in the repo captured the raw response and
the call happens client-side in the editor's browser. The editor supplied
that response directly, which is what made a real fix possible instead of
another guess — see the ruled-out causes (moderation vs. a
credit-propagation glitch vs. something unnamed) the earlier draft of
this ticket had to leave open.

`reviseSection()` (`ntk-pulse/pulse.html:1975`) was already a working
per-section retry before this fix and still is — this ticket doesn't
change whether a refused section can be retried, only whether the editor
can tell what happened when it does.

## Check

```sh
set -e
grep -q "d.stop_reason === 'refusal'" ntk-pulse/pulse.html

awk '/<script>/{f=1;next}/<\/script>/{f=0}f' ntk-pulse/pulse.html > /tmp/t0044-pulse-script.js
node --check /tmp/t0044-pulse-script.js

# Fixture: extract ai() as shipped and run it against three mocked
# responses — the editor's exact captured refusal shape, a refusal with
# no category, and a normal success — asserting each behaves correctly.
# No live key, no network.
node - <<'NODEEOF'
const fs = require('fs');
const src = fs.readFileSync('ntk-pulse/pulse.html', 'utf8');
const start = src.indexOf('async function ai(prompt');
if (start < 0) throw new Error('ai() not found');
const end = src.indexOf('\n}\n', start) + 3;
const aiSrc = src.slice(start, end);

async function run(mockResponse, expect) {
  global.fetch = async () => ({ json: async () => mockResponse });
  global.SETTINGS = { antKey: 'fake' };
  const fn = new Function(aiSrc + '\nreturn ai;')();
  try {
    const text = await fn('prompt');
    if (expect.throws) throw new Error('expected a throw, got: ' + text);
    if (text !== expect.text) throw new Error('expected "' + expect.text + '", got "' + text + '"');
  } catch (e) {
    if (!expect.throws) throw e;
    if (!e.message.includes(expect.message)) {
      throw new Error('expected message to include "' + expect.message + '", got "' + e.message + '"');
    }
  }
}

(async () => {
  await run({ stop_reason: 'refusal', stop_details: { category: 'bio' }, content: [] },
    { throws: true, message: 'Refused by the model (category: bio)' });
  await run({ stop_reason: 'refusal', content: [] },
    { throws: true, message: 'Refused by the model' });
  await run({ stop_reason: 'end_turn', content: [{ type: 'text', text: 'a real headline' }] },
    { throws: false, text: 'a real headline' });
  console.log('T-0044 fixture check passed');
})();
NODEEOF
rm -f /tmp/t0044-pulse-script.js
```
