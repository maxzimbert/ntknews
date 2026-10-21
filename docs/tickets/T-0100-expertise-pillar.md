---
id: T-0100
title: Expertise cannot be inspected, Backstory and links feed nothing, shares count on the tap, and nothing is reader-wide
status: VERIFIED
tags: [digest, feature]
anchor: digest/index.html:2290
---

## What

Measured 2026-10-21 on main (172c602b), `digest/index.html`:

- `showBsrPage` called `track('backstory_page')` and no `beatsRecord*`. Opening a Backstory
  row, object or Beginning changed nothing on the ladder. The Witness toast still said "you
  went into the history".
- No handler anywhere recorded an outbound link: 0 matches for `outbound` in the file.
- `shareStory` called `beatsRecordShare` before `navigator.share()`, so a cancelled sheet was
  a share, and the clipboard fallback counted the same as a sent message.
- `updateProgress` at `n === total` fired `track('digest_complete')` and nothing durable.
  No storage key held a finished edition (T-0021). `ntk_visits_v1` held `last` and `total`,
  no `first`.
- The only way to see a rung above Briefed was to read as a reader for weeks. No fixture, no
  copy gallery. The editor had not seen most of the product's own Expertise copy in place.
- `scripts/beats-sim.js` threw `ReferenceError: BEAT_REQS is not defined` and had since
  2026-09-18, when T-0025 made `beatIdx` table-driven.

Built on branch `T-0100-expertise-pillar`: inspect mode (`?inspect=<reader>`, four fixture
readers, a sheet of every line, writes to `__inspect`-suffixed keys only, `track()` silent);
`beatsRecordHistory` from `showBsrPage` with the toast deferred to `hideBsrPage`; Witness
requires `history: 2`; `beatsRecordLink` and `recordBump` from a delegated click handler;
shares credited in `navigator.share().then`, copies kept apart; `ntk_record_v1` with one
entry per finished edition; `/me` rebuilt with the record, a rail and behaviour marks per
beat; the simulator extracts `BEAT_REQS` and `beatMeets`. Narrative in `docs/expertise.md`.

## Why

**This is the pillar the editor says differentiates the product**, and before this it could
not be shown to anyone, including the editor. The briefing's own highest-signal behaviours,
the Backstory byway and sharing, were either unrecorded or recorded wrongly, so the system
was quietly saying things that were not true: "you went into the history" to a reader who
had not, "you are carrying it" to a reader who cancelled the share sheet. A recognition
system that congratulates behaviour the reader did not perform is the specific failure T-0015
was opened for, and two of its inputs still had it.

**Inspect mode writes to separate keys rather than flagging real data.** The alternative, a
flag that marks the editor's real record as "fixture", would have made the editor's own
record unusable as a test of the product on a phone they actually read on. The cost is one
function (`nsKey`) wrapped around every storage call for the six Expertise keys, and the check
below holds that at six.

**Witness requires history; the lower rungs do not.** The briefing puts "History layer
engaged more than once" at On the Beat. Requiring it there would cap any reader who never
opens the Backstory tab at Following It, and today that tab is one tap further than a story.
Witness is the rung whose copy names the history, so it is the rung that has to earn it.
Revisit when Backstory is reachable from inside a story. Simulated with
`scripts/beats-sim.js`: a story every three days with a Backstory trip every two weeks
reaches Witness on day 52.

**Shares cannot be told apart by app.** The Web Share API resolves on success and says
nothing about the destination. iMessage, Instagram and email are one count, and the record
says so rather than inventing a split. A native app would know.

**The record is counts, never dates.** `docs/decisions.md` locks no unread counts, sessions
per day as an anti-metric, and the assumption that the reader did not read yesterday.
Editions are stored by date because that is the natural key, and `/me` renders them only as
"14 digests finished". T-0026's check asserts no streak language in the product's copy, and
this change is held to it.

**Still a draft:** every new line of copy (the record lines, the behaviour marks, the
Backstory next-rung clause) was written alongside the mechanism. T-0027 holds the editorial
pass, which now has a sheet to read from. Status legibility on `/me` is option A of three;
the editor has not chosen (`docs/expertise.md` §5).

Ruled out here: building the Triforce in prod. The vision is mocked on the canvas; the
reader-wide record it would be built from now exists, which is the honest first step.

## Check

```sh
python3 - <<'PY'
import os, re, subprocess, sys, tempfile
s = open('digest/index.html', encoding='utf-8').read()

def grab(pat, what):
    m = re.search(pat, s)
    if not m: sys.exit(what + ' not found')
    return m.group(0)

def run_js(src, what):
    fd, path = tempfile.mkstemp(suffix='.js')
    os.write(fd, src.encode()); os.close(fd)
    r = subprocess.run(['node', path], capture_output=True, text=True)
    os.unlink(path)
    if r.returncode: sys.exit(r.stderr.strip() or (what + ' failed'))
    return r.stdout

# Every Expertise storage key goes through the namespace, so inspect mode cannot touch a
# reader's real record. Six keys, every get/set/remove.
keys = ['BEATS_KEY', 'VISITS_KEY', 'RECORD_KEY', 'ORIENT_KEY', 'CHIP_SEEN_KEY', 'BEATS_TOAST_KEY']
for k in keys:
    bare = re.findall(r'localStorage\.(?:get|set|remove)Item\(\s*' + k + r'\b', s)
    if bare: sys.exit(k + ' reaches localStorage without nsKey: %d call(s)' % len(bare))
    if not re.search(r'localStorage\.(?:get|set|remove)Item\(\s*nsKey\(' + k + r'\)', s):
        sys.exit(k + ' is never stored through nsKey')
if not re.search(r'function track\([^)]*\)\s*\{\s*if \(INSPECT\) return', s):
    sys.exit('a fixture reader reaches analytics')

# A Backstory page reaches the ladder, and the ladder speaks on the way out, not over the page.
if 'beatsRecordHistory' not in grab(r'function showBsrPage\([\s\S]*?\n\}', 'showBsrPage'):
    sys.exit('opening a Backstory page does not reach the ladder')
if 'showBeatToast' not in grab(r'function hideBsrPage\([\s\S]*?\n\}', 'hideBsrPage'):
    sys.exit('a rung crossed in Backstory is never spoken')

# A share is a share when the sheet reports success, not on the tap.
share = grab(r'function shareStory\(\)[\s\S]*?\n\}', 'shareStory')
if share.find('beatsRecordShare') < share.find('navigator.share('):
    sys.exit('a share is credited before the share sheet opens')
if '.then(' not in share: sys.exit('a share is not credited on success')

# Outbound links are recorded from the three surfaces that have them.
for where in ('#storyView', '#bsrPage', '#todayView'):
    if not re.search(r"closest\('" + re.escape(where) + r"'\)[\s\S]{0,300}?(beatsRecordLink|recordBump)", s):
        sys.exit('a link followed out of ' + where + ' is not recorded')

# Witness needs the history; the full pattern without it stays below. Run the scorer.
parts = [grab(p, n) for p, n in (
    (r'var BEATS_SCALE = \[[\s\S]*?\];', 'BEATS_SCALE'), (r'var BEAT_REQS = \[[\s\S]*?\n\];', 'BEAT_REQS'),
    (r'function beatMeets\([\s\S]*?\n\}', 'beatMeets'), (r'function beatIdx\([\s\S]*?\n\}', 'beatIdx'))]
run_js('\n'.join(parts) + '''
var full = {stories:20, sessions:9, depth:9, liesRead:true, shares:2, liesStories:['a','b','c','d','e']};
if (beatIdx(full) >= 6) { console.error('Witness without a Backstory trip'); process.exit(1); }
if (beatIdx(Object.assign({history:2}, full)) !== 6) { console.error('Witness unreachable with the history'); process.exit(1); }
if (beatIdx({stories:7, sessions:3, depth:2, liesRead:true, liesStories:['a','b','c']}) !== 5) { console.error('Carrying It now needs the Backstory'); process.exit(1); }
''', 'ladder fixture')

# Finishing a digest leaves one dated trace, once; /me says it as a count and never as days.
parts = [grab(p, n) for p, n in (
    (r'var INSPECT = [\s\S]*?\n\}\)\(\);', 'INSPECT'), (r'function nsKey\([^\n]*\}', 'nsKey'),
    (r'const months = \[[^\]]*\];', 'months'), (r'function storySubject\([\s\S]*?\n\}', 'storySubject'),
    (r'function beatsLoad\([\s\S]*?\n\}', 'beatsLoad'), (r'function visitsLoad\([\s\S]*?\n\}', 'visitsLoad'),
    (r'var RECORD_KEY = [\s\S]*?function recordBump\([\s\S]*?\n\}', 'the record'),
    (r'function todayDateStamp\([\s\S]*?\n\}', 'todayDateStamp'),
    (r'function profileRecordLines\([\s\S]*?\n\}', 'profileRecordLines'))]
out = run_js('''
var store = {}, location = { search: '', pathname: '/digest/2026-10-21/' };
var localStorage = { getItem: function(k){ return k in store ? store[k] : null; }, setItem: function(k, v){ store[k] = String(v); }, removeItem: function(k){ delete store[k]; } };
var BEATS_KEY = 'b', VISITS_KEY = 'v', ORIENT_KEY = 'o', CHIP_SEEN_KEY = 'c', BEATS_TOAST_KEY = 't';
var stories = [{subject:'Gaza'}, {subject:'Gaza'}, {category:'Nation'}];
''' + '\n'.join(parts) + '''
recordEdition(3); recordEdition(3);
var r = JSON.parse(store['ntk_record_v1']);
var keys = Object.keys(r.editions);
if (keys.length !== 1 || keys[0] !== '2026-10-21') { console.error('editions: ' + JSON.stringify(keys)); process.exit(1); }
if (r.editions[keys[0]].subjects.join() !== 'Gaza,Nation') { console.error('subjects: ' + r.editions[keys[0]].subjects); process.exit(1); }
store['v'] = JSON.stringify({ first: Date.now() - 86400000 * 40, last: Date.now(), total: 9 });
console.log(profileRecordLines().join(' | '));
''', 'record fixture')
if 'digest finished' not in out: sys.exit('the record does not count finished digests: ' + out)
if not out.startswith('Reading since '): sys.exit('the record does not say when reading began: ' + out)
for bad in ('streak', 'row', 'missed', 'days'):
    if re.search(r'\b' + bad + r'\b', out.lower()): sys.exit('the record speaks in days: ' + out)

# The simulator runs, and it models the Backstory.
sim = subprocess.run(['node', 'scripts/beats-sim.js'], capture_output=True, text=True)
if sim.returncode or 'Witness' not in sim.stdout or 'backstory' not in sim.stdout.lower():
    sys.exit('beats-sim.js does not run to Witness with the Backstory: ' + (sim.stderr or sim.stdout)[-300:])

# Inspect mode exists only behind the query string, with every reader seedable.
if not re.search(r"location\.search\.match\(/\[\?&\]inspect", s): sys.exit('inspect mode is not keyed to ?inspect')
readers = re.findall(r"^\s*'(\w+)':\s*\{ label:", grab(r'var INSPECT_READERS = \{[\s\S]*?\n\};', 'INSPECT_READERS'), re.M)
if len(readers) < 4: sys.exit('fewer than four fixture readers: %s' % readers)
PY
```
