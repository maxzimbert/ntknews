---
id: T-0026
title: Nothing marks a reader coming back, which is the moment the product is built for
status: VERIFIED
tags: [digest, feature]
anchor: digest/index.html:3395
---

## What

The orientation card between stories three and four is the only reader-level
moment in the app, it fires once ever, and the editor reports it got the best
feedback of anything in Expertise.

Nothing else is reader-level. `ntk_beats_v1` records `lastActive` per subject;
no timestamp records the reader's own last visit, so the app cannot currently
tell a first session from a second, or a return after a week from a return
after a day.

Wanted: the same kind of moment at the points that matter — a second day, a
return after a gap, the first story back.

## Why

This is the product's own thesis. `docs/decisions.md` records the design
assumption in one line: **the reader did not read yesterday and will not read
tomorrow.** A reader who came back anyway did the thing the entire product is
trying to earn, and right now the app does not notice.

**The register is the whole risk, and it cuts against the obvious
implementation.** Four locked decisions apply at once: no unread counts ever,
sessions-per-day is an anti-metric, the digest must end, and the reader is
assumed to lapse. A returning-reader moment is one wrong sentence away from a
streak, and a streak is precisely the backlog-as-debt mechanism that the
audience is avoiding. So:

- Never count consecutive days. Never show a gap as a number.
- Never imply the reader owes anything for the days they missed.
- A longer absence gets a *warmer* welcome, not a cooler one. The instinct to
  escalate at the reader is the instinct to build a streak.
- Say nothing at all more often than not. A moment that fires every session is
  a greeting, and a greeting stops being noticed by the third one.

Worth stating because it will come up: the right copy for a two-week absence is
closer to "the news kept going; here is where it got to" than to anything
about the reader. The absence is not the subject.

The copy shipped here is a first draft written by whoever wrote the
mechanism. The editor has flagged it for a pass; T-0027 holds that, and
nothing in this ticket should be read as settling the words.

Related: T-0021 wants a durable reading record, and the visit log this needs
is the smallest honest piece of it. Build it so that ticket can read it, and
do not build the record here.

## Check

```sh
python3 - <<'PY'
import re, subprocess, sys, tempfile, os
s = open('digest/index.html', encoding='utf-8').read()

if 'ntk_visits' not in s:
    sys.exit('no reader-level visit log')
m = re.search(r'function visitMoment\([\s\S]*?\n\}', s)
if not m: sys.exit('visitMoment not found')

# No streak, in the code or in the copy. This is the failure the ticket exists
# to prevent, so it is asserted rather than trusted.
for bad in ('streak', 'consecutive', 'days in a row', "don't break", 'keep it up'):
    if bad in s.lower():
        sys.exit('streak language or logic present: %r' % bad)

# A returning reader is greeted; a same-session reload is not.
prog = m.group(0) + '''
var cases = [
  [null,                       true,  'a first-ever visit says nothing'],
  [Date.now() - 30 * 60000,    false, 'a same-session reload greets the reader again'],
  [Date.now() - 26 * 3600000,  true,  'a next-day return says nothing'],
  [Date.now() - 9 * 86400000,  true,  'a return after a week says nothing']
];
var fails = [];
cases.forEach(function(c){
  var got = visitMoment(c[0]);
  var spoke = !!(got && got.length);
  if (c[0] === null && spoke) fails.push(c[2]);
  else if (c[0] !== null && spoke !== c[1]) fails.push(c[2]);
});
if (fails.length){ console.error(fails.join('; ')); process.exit(1); }
'''
fd, path = tempfile.mkstemp(suffix='.js')
os.write(fd, prog.encode()); os.close(fd)
r = subprocess.run(['node', path], capture_output=True, text=True)
os.unlink(path)
if r.returncode: sys.exit(r.stderr.strip() or 'visitMoment fixture run failed')
PY
```
