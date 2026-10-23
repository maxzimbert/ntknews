---
id: T-0101
title: Engagement events are recorded but never spoken, the toast overwrites itself, Backstory cannot be shared, and the copy judges the reader
status: VERIFIED
tags: [digest, feature]
anchor: digest/index.html:2840
---

## What

Measured 2026-10-23 on main (6cfec1b1), `digest/index.html`, after T-0100:

- Finishing a digest, a first trip into Backstory, a first document, a return to Backstory
  and a first share were all recorded and shown on `/me`, and none produced a moment. The
  only things that spoke were a rung crossing, the returning-reader line and the
  three-stories card. The editor's read: "Is this it?"
- `showBeatToast` cleared and replaced whatever was showing, so two moments on one story
  close meant the first was never read.
- Backstory row pages had a permalink and no share control: 0 matches for a share button in
  `bpRowHtml`.
- The Moment of Then closed on "Congratulations — you completed today's NTK News", a cheer
  with an em dash, and said nothing about the record.
- Several lines judged the reader rather than naming what they did: "That is attention, not
  habit", "you cannot unsee it", "You did not take the surface at face value". The generated
  next-rung sentence read as a spec and carried a comma before "or" inside one clause.

Built: `MARKS` (ten firsts, `markFire` fires each once ever and returns its line); a queue in
`showBeatToast`; Backstory firsts held until Back, then spoken; a Share control on the row
page with the same success-only credit as a story share; the Moment of Then carries "Your
14th digest, start to finish"; every line rewritten to one rule; `/me` lists the firsts under
the record with the day each happened; fixture readers carry marks; the Every line sheet
lists them.

## Why

**The editor set the direction on 2026-10-23 and the words of it are the spec.** Wanted:
"reward/milestone language for engagement and investment time in news reading and
exploring." Not wanted: "cheerleading, therapy-speak, jargon, or gamification." The rule
that falls out, and that every line here was rewritten to: a concrete thing the reader did,
past tense, then the word for it, and nothing about the reader's character. The lines that
already worked ("You sent a Housing story to someone. You are carrying it now.") had that
shape; the ones that drifted were interpreting the reader.

**Firsts are the one kind of milestone that cannot become a streak.** `docs/decisions.md`
locks no unread counts, sessions per day as an anti-metric, and the assumption that the
reader lapses. A first fires once ever, by definition, so it cannot become a greeting
(T-0026's worry) and it counts a thing done, never a day. The digest marks are at 1, 5, 10,
25 and 50 finished, which is a count of things done; the same marks at "7 days running" would
be the mechanism this audience left. T-0026's check still asserts no streak language anywhere
in the product's copy, and this change is held to it.

**The digest moment stays the Moment of Then.** Finishing is the closure promise, and the
reveal is already its signal. A second toast for the same event would be two moments for one
act. The record line goes inside the reveal instead, and the digest marks fire there silently.

**A first share yields to Carrying It.** When both land on one close, the rung toast says the
same thing better, so the mark is recorded and not spoken.

**Not a mark, deliberately: turning on location.** The editor asked for it. A permission
grant is not reading, and rewarding one reads as a dark pattern whether or not it is one.
The decision is recorded here so it is not re-decided casually.

**The web cannot see which app a share went to**, so a Backstory share is one count, like a
story share, until the app is native.

Cost: one storage key (`ntk_marks_v1`, namespaced like the rest so inspect mode cannot touch
a reader's own), one function per mark site, no pipeline change.

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

# The marks key goes through the namespace like the other six.
if re.search(r'localStorage\.(?:get|set|remove)Item\(\s*MARKS_KEY\b', s): sys.exit('MARKS_KEY bypasses nsKey')
if not re.search(r'localStorage\.setItem\(\s*nsKey\(MARKS_KEY\)', s): sys.exit('marks are never stored')

# Every mark has a label and a line, and each fires exactly once. Run it.
parts = [grab(p, n) for p, n in (
    (r'function nsKey\([^\n]*\}', 'nsKey'), (r'var MARKS_KEY = [\s\S]*?function ordinalWord\([\s\S]*?\n\}', 'marks'))]
out = run_js('''
var INSPECT = '', store = {};
var localStorage = { getItem: function(k){ return k in store ? store[k] : null; }, setItem: function(k, v){ store[k] = String(v); } };
function escBsr(x){ return String(x); }
''' + '\n'.join(parts) + '''
var ids = Object.keys(MARKS);
if (ids.length < 10) { console.error('only ' + ids.length + ' marks'); process.exit(1); }
ids.forEach(function(id){ if (!MARKS[id].label || !MARKS[id].line) { console.error(id + ' incomplete'); process.exit(1); } });
var a = markFire('backstory_first', { cat: 'Housing' }), b = markFire('backstory_first', { cat: 'Housing' });
if (!a || a.indexOf('Housing') < 0) { console.error('first fire gave: ' + a); process.exit(1); }
if (b !== null) { console.error('second fire spoke: ' + b); process.exit(1); }
if (ordinalWord(1) !== 'first' || ordinalWord(14) !== '14th' || ordinalWord(22) !== '22nd') { console.error('ordinals'); process.exit(1); }
console.log(ids.map(function(id){ return MARKS[id].line; }).join('\\n'));
''', 'marks fixture')

# Every mark site exists: Backstory firsts wait for Back, the digest marks live in the
# Moment of Then, a story share can be a first, and a Backstory share is possible at all.
if 'markFire' not in grab(r'function showBsrPage\([\s\S]*?\n\}', 'showBsrPage'): sys.exit('Backstory firsts are not recorded')
if 'bsrPendingMarks' not in grab(r'function hideBsrPage\([\s\S]*?\n\}', 'hideBsrPage'): sys.exit('Backstory firsts are never spoken')
mot = grab(r'function startMotAnimation\([\s\S]*?\n\}', 'startMotAnimation')
if 'motRecordLine' not in mot or 'markFire' not in mot: sys.exit('the Moment of Then carries no record line')
if 'id="motRecordLine"' not in s: sys.exit('no element for the record line in the reveal')
if 'markFire' not in grab(r'function shareStory\(\)[\s\S]*?\n\}', 'shareStory'): sys.exit('a first share is not a mark')
if 'data-bp="share"' not in grab(r'function bpRowHtml\([\s\S]*?\n\}', 'bpRowHtml'): sys.exit('a Backstory page cannot be shared')
sb = grab(r'function shareBackstory\([\s\S]*?\n\}', 'shareBackstory')
if sb.find('beatsRecordShare') < sb.find('navigator.share('): sys.exit('a Backstory share is credited before the sheet opens')

# The toast queues; it does not overwrite.
if 'beatToastQueue' not in grab(r'function showBeatToast\([\s\S]*?\n\}', 'showBeatToast'): sys.exit('the toast overwrites itself')

# The lines that judged the reader stay gone, in the toasts, the explainers and the marks.
copy = '\n'.join([grab(r'function beatsToastCopy\([\s\S]*?\n\}', 'toast'), grab(r'function beatsExplain\([\s\S]*?\n\}', 'explain'), out])
for bad in ('not habit', 'unsee', 'face value', 'Congratulations', 'habit of mind', 'well enough'):
    if bad in copy: sys.exit('the copy judges the reader again: %r' % bad)
if '—' in copy: sys.exit('em dash in the copy')

# The generated next-rung sentence is nouns, with no comma inside a clause.
parts = [grab(p, n) for p, n in (
    (r'var BEATS_SCALE = \[[\s\S]*?\];', 'BEATS_SCALE'), (r'var BEAT_REQS = \[[\s\S]*?\n\];', 'BEAT_REQS'),
    (r'function beatMeets\([\s\S]*?\n\}', 'beatMeets'), (r'function beatIdx\([\s\S]*?\n\}', 'beatIdx'),
    (r'function beatsJoin\([\s\S]*?\n\}', 'beatsJoin'), (r'function beatsNextRung\([\s\S]*?\n\}', 'beatsNextRung'))]
out = run_js('function beatsLoad(){ return {}; }\n' + '\n'.join(parts) + '''
for (var i = 0; i < 6; i++) {
  var req = BEAT_REQS[i], d = { stories: req.stories || 1, sessions: req.sessions || 1, depth: req.depth || 0, liesRead: !!req.lies, history: req.history || 0, liesStories: [], shares: req.carry ? req.carry.shares : 0 };
  var nx = beatsNextRung('Housing', d);
  if (!nx) { console.error('no next rung from ' + i); process.exit(1); }
  console.log(nx.sentence);
}
''', 'next-rung fixture')
for line in out.strip().split('\n'):
    if re.search(r', (or|and) \w+ing\b', line): sys.exit('comma inside a clause: ' + line)
    if re.search(r'\b(goes to readers|opening|reading the|going back)\b', line): sys.exit('the next-rung sentence instructs: ' + line)
PY
```
