---
id: T-0015
title: The Expertise ladder has seven rungs and speaks on three of them
status: VERIFIED
tags: [digest, defect]
anchor: digest/index.html:2572
---

## What

`BEATS_SCALE` defines seven rungs — Skimmed, Briefed, Read It, Following It,
On the Beat, Carrying It, Witness. `beatsToastCopy` returns copy for rungs 4,
5 and 6 and `null` for the rest, and the caller gates on `newIdx >= 4`
anyway. A reader's first week of reading produces no recognition at all
beyond one static card that says "Three stories in."

Measured 2026-09-18 against `digest/index.html`:

- `beatsRecordLies` and `beatsRecordDepth` both write to storage. In
  `beatIdx` they are only consulted below rung 3, so once a reader has read
  three stories in a category neither input can change their status again.
  Reading the Lies layer — the behavior the Expertise briefing calls most
  significant — cannot affect any rung a reader will realistically reach.
- `shareStory` (`digest/index.html:3626`) calls `track()` and nothing else.
  Sharing does not feed the ladder, though the briefing makes "shared more
  than once" the threshold for Carrying It.
- `beatIdx({stories:20, sessions:9})` returns 6. A reader who opens twenty
  stories and never goes below the summary is a Witness.
- `orientShown` is a plain `let` (`digest/index.html:2323`). The card reads
  "Three stories in. You're paying attention." on day 60 as well as day one.
- `openBeatsSheet`, `closeBeatsSheet` and `renderBeatsSheet`
  (`digest/index.html:2679`) address `beatsOverlay`, `beatsSheet`,
  `beatsDomainList` and `beatsScalePills`. None of those four IDs exist in
  the document. `window.openBeatsSheet` throws if anything calls it. Nothing
  does; `renderProfileTab` is the live copy.

## Why

The editor's read from production was that Expertise is siloed on the Profile
tab. It is not — there are three digest-side surfaces already shipped (the
beat chip in the hero row, the orientation card between stories three and
four, the orientation toast on story close). The reason it reads as absent is
that the ladder almost never speaks, and when it does it congratulates
behavior the reader did not perform.

That second half matters more than the first. The briefing doc's own argument
for the vocabulary is that the markers "are hard to fake — you cannot skim
your way to Witness." Today you can, in about two days, because the only
input that moves the ladder above rung 3 is how many stories were opened.
Shipping more recognition on top of that scoring would make the product
louder and less true at the same time, which is the specific failure the
four named voice failure modes in `docs/decisions.md` exist to prevent.

Ruled out: adding rungs, renaming rungs, or surfacing status on every story
card. The briefing's open question 09 is explicit that per-story status
"turns reading into performance," and the seven-rung vocabulary is settled
editorial work, not a draft.

Not in scope, and deliberately: what a beat is keyed to. That is T-0016. This
ticket fixes what the ladder says and what it counts; T-0016 fixes what it
counts it against. Doing both in one change makes the digest diff unreviewable
against a publish-schema change.

## Check

```sh
python3 - <<'PY'
import re, subprocess, sys, tempfile, os
s = open('digest/index.html', encoding='utf-8').read()

# Dead code: JS that addresses elements the document does not contain.
for dead in ('beatsOverlay', 'beatsSheet', 'beatsDomainList', 'beatsScalePills'):
    if dead in s and ('id="%s"' % dead) not in s:
        sys.exit('%s is addressed in JS but no element carries that id' % dead)

# Every rung on the scale has something to say.
m = re.search(r'function beatsToastCopy\([\s\S]*?\n\}', s)
if not m: sys.exit('beatsToastCopy not found')
covered = {int(n) for n in re.findall(r'idx\s*===\s*(\d+)', m.group(0))}
missing = sorted(set(range(7)) - covered)
if missing: sys.exit('rungs with no recognition copy: %s' % missing)

# ...and the caller is not gating those rungs back out again.
if re.search(r'newIdx\s*>=\s*4', s):
    sys.exit('the toast is still gated at rung 4')

# Sharing feeds the ladder.
m = re.search(r'function shareStory\(\)[\s\S]*?\n\}', s)
if not m or 'beatsRecordShare' not in m.group(0):
    sys.exit('shareStory does not record a share against the ladder')

# The three-stories card does not repeat forever.
if not re.search(r'orientShown[\s\S]{0,600}?localStorage', s):
    sys.exit('orientShown is not persisted')

# You cannot skim your way to Witness. Run the real scorer, do not read it.
# beatIdx became table-driven on 2026-09-18 (T-0025), so its inputs come
# along too. The assertions below are unchanged; only the extraction is.
parts = []
for pat, name in ((r'var BEATS_SCALE = \[[\s\S]*?\];',   'BEATS_SCALE'),
                  (r'var BEAT_REQS = \[[\s\S]*?\n\];',   'BEAT_REQS'),
                  (r'function beatMeets\([\s\S]*?\n\}',  'beatMeets'),
                  (r'function beatIdx\([\s\S]*?\n\}',    'beatIdx')):
    m = re.search(pat, s)
    if not m: sys.exit('%s not found' % name)
    parts.append(m.group(0))
prog = '\n'.join(parts) + '''
var L = function(n){ var a=[]; for(var i=0;i<n;i++) a.push('s'+i); return a; };
var cases = [
  [{stories:20, sessions:9},                                          'lt', 6,
   'twenty stories, no depth, no lies, no shares reaches Witness'],
  [{stories:20, sessions:9, depth:9, liesRead:true},                  'lt', 5,
   'Carrying It is reachable on volume alone, with no share and no repeated lies'],
  [{stories:20, sessions:9, depth:9, liesRead:true, shares:2},        'eq', 6,
   'the full behavioral pattern does not reach Witness'],
  [{stories:20, sessions:9, depth:9, liesRead:true, liesStories:L(3)},'eq', 5,
   'the Lies-layer route to Carrying It is closed to a reader who never shares'],
  [{stories:20, sessions:9, depth:9, liesRead:true, liesStories:L(5)},'eq', 6,
   'the Lies-layer route to Witness is closed to a reader who never shares']
];
for (var i=0;i<cases.length;i++){
  var c = cases[i], got = beatIdx(c[0]);
  var ok = c[1]==='lt' ? got < c[2] : got === c[2];
  if (!ok){ console.error(c[3] + ' (beatIdx returned ' + got + ')'); process.exit(1); }
}
'''
fd, path = tempfile.mkstemp(suffix='.js')
os.write(fd, prog.encode()); os.close(fd)
r = subprocess.run(['node', path], capture_output=True, text=True)
os.unlink(path)
if r.returncode: sys.exit(r.stderr.strip() or 'beatIdx fixture run failed')
PY
```
