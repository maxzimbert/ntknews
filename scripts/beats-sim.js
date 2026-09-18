#!/usr/bin/env node
//
// beats-sim.js — show what the Expertise ladder does, and when.
//
//     node scripts/beats-sim.js              # one topical beat, a story every 3 days
//     node scripts/beats-sim.js --every 1    # a section label at the live digest's mix
//     node scripts/beats-sim.js --days 90 --no-share
//
// It does NOT reimplement the ladder. It extracts BEATS_SCALE, beatIdx,
// beatsToastCopy, beatsShouldToast and beatsMarkToast out of digest/index.html
// and runs those. That is deliberate: a second copy of the scoring rules is
// exactly the version drift this project already paid for once, and a
// simulator that agrees with a stale copy of the code is worse than no
// simulator. If the ladder changes, this output changes with it.

const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, '..', 'digest', 'index.html');
const src = fs.readFileSync(SRC, 'utf8');

function grab(re, what) {
  const m = src.match(re);
  if (!m) { console.error('could not find ' + what + ' in digest/index.html'); process.exit(1); }
  return m[0];
}

const parts = [
  grab(/var BEATS_SCALE = \[[\s\S]*?\];/,        'BEATS_SCALE'),
  grab(/var BEATS_TOAST_KEY = '[^']+';/,          'BEATS_TOAST_KEY'),
  grab(/function beatIdx\([\s\S]*?\n\}/,          'beatIdx'),
  grab(/function beatsToastCopy\([\s\S]*?\n\}/,   'beatsToastCopy'),
  grab(/function beatsToastState\([\s\S]*?\n\}/,  'beatsToastState'),
  grab(/function beatsShouldToast\([\s\S]*?\n\}/, 'beatsShouldToast'),
  grab(/function beatsMarkToast\([\s\S]*?\n\}/,   'beatsMarkToast'),
];

// A clock and a localStorage the extracted code can run against.
let NOW = 0;
const store = {};
const sandbox = {
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
  Date: { now: () => NOW },
  JSON, console,
};
const fn = new Function('localStorage', 'Date', 'JSON', 'console',
  parts.join('\n') + '\nreturn { BEATS_SCALE, beatIdx, beatsToastCopy, beatsShouldToast, beatsMarkToast };');
const B = fn(sandbox.localStorage, sandbox.Date, JSON, console);

// ── args
const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf(k); return i < 0 ? d : Number(argv[i + 1]); };
const EVERY  = arg('--every', 3);      // days between stories on this beat
const DAYS   = arg('--days', 60);
const SHARES = !argv.includes('--no-share');
const CAT    = (argv.indexOf('--cat') < 0) ? 'Housing' : argv[argv.indexOf('--cat') + 1];

const pad = (s, n) => String(s).padEnd(n);

// ── the ladder itself
console.log('\nTHE LADDER — ' + SRC.replace(process.cwd() + '/', '') + '\n');
const REQ = [
  'first story read in this category',
  'opened one section below the summary',
  'revealed the Lies layer',
  '3 stories, across 2 separate sittings',
  '5 stories, 2 sittings, 2 sections opened',
  '7 stories, 3 sittings, Lies read, 1 share',
  '10 stories, 4 sittings, 5 sections, Lies read, 2 shares',
];
const WHERE = [
  'chip + Profile only, never interrupts',
  'toast on story close, chip, Profile',
  'toast on story close, chip, Profile',
  'toast on story close, chip, Profile',
  'toast on story close, chip, Profile',
  'toast on story close, always speaks',
  'toast on story close, always speaks',
];
console.log(pad('#', 3) + pad('STATUS', 15) + pad('WHAT IT TAKES', 56) + 'WHERE IT SHOWS');
console.log('-'.repeat(126));
B.BEATS_SCALE.forEach((b, i) => console.log(pad(i, 3) + pad(b.label, 15) + pad(REQ[i], 56) + WHERE[i]));

console.log('\nFrequency rule: Skimmed never interrupts. Carrying It and Witness always speak.');
console.log('Everything between gets one toast per sitting, unless the jump is 2+ rungs.\n');

// ── the timeline
console.log('A READER ON "' + CAT + '" — one story every ' + EVERY + ' day' + (EVERY === 1 ? '' : 's') +
            ', ' + DAYS + ' days' + (SHARES ? '' : ', never shares') + '\n');

const d = { stories: 0, depth: 0, shares: 0, liesRead: false, sessions: 0, last: -1e12 };
let spoke = 0;
for (let day = 1; day <= DAYS; day += EVERY) {
  NOW = day * 24 * 3600000;
  const before = d.stories ? B.beatIdx(d) : -1;
  if ((NOW - d.last) / 3600000 > 4) d.sessions++;
  d.last = NOW;
  d.stories++;
  if (day % 2 === 1) d.depth += 1;                 // opens a section about half the time
  if (day >= 4) d.liesRead = true;                 // finds the Lies layer early on
  if (SHARES && (day % 21 === 1) && day > 1) d.shares++;   // shares every few weeks
  const after = B.beatIdx(d);
  if (after > before && B.beatsShouldToast(after)) {
    spoke++;
    console.log('  day ' + pad(day, 4) + pad(B.BEATS_SCALE[after].label, 15) +
                B.beatsToastCopy(CAT, after, d.stories).replace(/<[^>]+>/g, ''));
    B.beatsMarkToast(after);
  }
}
console.log('\n  ' + spoke + ' orientation moments in ' + DAYS + ' days. Ends at: ' +
            B.BEATS_SCALE[B.beatIdx(d)].label + ' (' + d.stories + ' stories, ' + d.sessions +
            ' sittings, ' + d.depth + ' sections, ' + d.shares + ' shares).\n');
