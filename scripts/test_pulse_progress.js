#!/usr/bin/env node
// Pulse's progress bar (2026-11-18): runs the PROG block of ntk-pulse/pulse.html in node on a fake clock.
// The job the editor set for it: answer "how long until I can look at this?", cover the whole job, never lie.
//   node scripts/test_pulse_progress.js
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'ntk-pulse/pulse.html'), 'utf8');
const m = html.match(/\/\* PROG:BEGIN \*\/([\s\S]*?)\/\* PROG:END \*\//);
if (!m) { console.error('FAIL: PROG block not found'); process.exit(1); }
const kit = () => {
  const K = new Function('progTick', m[1] + '; return {PROG, progStart, progRun, progStep, progDone, progJob, progFrac, progLabel, progExpected, progInner, progGlobal, progAt, PROG_DEFAULT_MS};')(() => {});
  const store = {}; K.PROG.store = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
  let t = 1e12; K.PROG.now = () => t; K.at = (ms) => { t += ms; return t; }; K.t = () => t;
  return K;
};
let fails = 0;
const check = (name, ok, detail) => { console.log((ok ? 'ok   ' : 'FAIL ') + name + (ok ? '' : '  ' + String(JSON.stringify(detail)).slice(0, 400))); if (!ok) fails++; };

// one part of 60 seconds, followed second by second until well past its usual time
let K = kit(), id = K.progStart('story:a', 'Build', ['build']), j = K.progJob(id), seen = [], labels = [];
for (let s = 0; s <= 240; s++) { seen.push(K.progFrac(j, K.t())); labels.push(K.progLabel(j, K.t())); K.at(1000); }
check('progress: the bar never goes backwards', seen.every((f, i) => i === 0 || f >= seen[i - 1]), seen.filter((f, i) => i && f < seen[i - 1]).length);
check('progress: the bar is never full before the job is done', Math.max(...seen) < 1 && Math.max(...seen) <= 0.98, Math.max(...seen));
check('progress: past its usual time it keeps moving and says so, it does not sit still', seen[200] > seen[100] && labels[200] === 'Taking longer than usual, still working', [seen[100], seen[200], labels[200]]);
K.progDone(id);
check('progress: done says done, with how long it took, and the bar is full', K.progFrac(j, K.t()) === 1 && /^Done in 4:0[01]$/.test(K.progLabel(j, K.t())), K.progLabel(j, K.t()));
K.at(9000);
check('progress: a finished bar goes away after a few seconds', K.progAt('story:a', K.t()) === null && K.progInner('story:a') === '', null);

// the time left, in words
K = kit(); id = K.progStart('bs:all', 'Build every proposal', ['build', 'build', 'build', 'build']); j = K.progJob(id);
const l0 = K.progLabel(j, K.t());
K.at(45000); K.progStep(id); K.at(45000); K.progStep(id); K.at(45000); K.progStep(id);
K.at(5000); const l3 = K.progLabel(j, K.t()); K.at(30000); const l4 = K.progLabel(j, K.t());
check('progress: it says the time left in minutes, then less than a minute, then almost done', l0 === 'About 3 min left' && l3 === 'Less than a minute left' && l4 === 'Almost done', [l0, l3, l4]);
check('progress: a whole job moves on as each part finishes', Math.abs(K.progFrac(j, K.t()) - (3 * 45000 + 35000) / 180000) < 0.01, K.progFrac(j, K.t()));

// timings are learned from the editor's own runs
K = kit();
const before = K.progExpected('propose');
for (const ms of [100000, 110000, 90000]) { const x = K.progStart('bs:b', 'Propose', ['propose']); K.at(ms); K.progDone(x); }
check("progress: it learns how long a kind of job takes from the editor's runs", before === K.PROG_DEFAULT_MS.propose && K.progExpected('propose') === 100000, [before, K.progExpected('propose')]);
const g = K.progStart('lineup', 'Generate all', ['section', 'section'], { learn: false }); K.at(999000); K.progStep(g); K.progDone(g);
check('progress: a job whose parts overlap teaches it nothing', K.progExpected('section') === K.PROG_DEFAULT_MS.section, K.progExpected('section'));

// Generate Jefferson: four sections, then the proposal, as one job
K = kit(); id = K.progStart('story:c', 'Generate Jefferson', ['section', 'section', 'section', 'section', 'propose']); j = K.progJob(id);
for (let i = 0; i < 4; i++) { K.at(25000); K.progStep(id); }
check('progress: Generate Jefferson covers the sections and the proposal, not just the sections', j.i === 4 && K.progFrac(j, K.t()) < 0.6 && K.progFrac(j, K.t()) > 0.5, K.progFrac(j, K.t()));

// a job queued behind another
K = kit(); const a = K.progStart('bs:d', 'Build', ['build'], { queue: 'bsx' }), b = K.progStart('bs:e', 'Opus', ['turn'], { queue: 'bsx', waiting: true });
const jb = K.progJob(b);
check('progress: a job queued behind another says it is waiting, and shows no progress yet', K.progLabel(jb, K.t()) === 'Waiting for 1 job ahead' && K.progFrac(jb, K.t()) === 0, K.progLabel(jb, K.t()));
K.at(30000); K.progDone(a); K.progRun(b); K.at(10000);
check('progress: when its turn comes it starts timing from then', jb.state === 'running' && /min left/.test(K.progLabel(jb, K.t())) && K.progFrac(jb, K.t()) > 0, K.progLabel(jb, K.t()));

// a job that fails
K.progDone(b, false, 'the draft kept changing under the save');
check('progress: a job that fails says stopped, and why', K.progLabel(jb, K.t()) === 'Stopped: the draft kept changing under the save' && K.progAt('bs:e', K.t()) && /var\(--stale\)/.test(K.progInner('bs:e')), K.progLabel(jb, K.t()));

// the bar along the top
K = kit(); K.progStart('story:f', 'Punch up', ['punch']); K.progStart('bs:all', 'Build every proposal', ['build', 'build', 'build']);
const top = K.progGlobal(K.t());
check('progress: the top bar counts what is running and follows the job with the most time left', top.n === 2 && top.job.label === 'Build every proposal' && /^2 jobs running: Build every proposal\. About 2 min left$/.test(top.text), top && top.text);
check('progress: no job, no top bar', kit().progGlobal() === null, null);

console.log('\n' + fails + ' failed');
process.exit(fails ? 1 : 0);
