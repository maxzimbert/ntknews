#!/usr/bin/env node
// Runs Pulse's real punchUpHeadline (ntk-pulse/pulse.html) against stand-in model replies and checks
// the need-to-know headline (T-0125): it is asked for, it comes back last and labelled with what it
// rests on, and an old-shape reply still works.   node scripts/test_punch_up.js
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'ntk-pulse/pulse.html'), 'utf8');
const cut = (start, endMark) => {
  const i = html.indexOf(start); if (i < 0) throw new Error('not found: ' + start);
  return html.slice(i, html.indexOf(endMark, i) + endMark.length);
};
const src = [
  cut('const VOICE_REF', '`;'), cut('const NTK_HEADLINE_RULES', '`;\n'),
  cut('function parseJSON', '\n}\n'), cut('async function punchUpHeadline', '\n}\n'),
  cut('function applyPunchedHeadline', '\n}\n'),
].join('\n');
let reply = '', asked = '';
const P = new Function('ai', 'setStatus', 'saveLineup', 'render', 'activeArts',
  src + '; return {punchUpHeadline, applyPunchedHeadline};')(
  async p => { asked = p; return reply; }, (s, m, e) => { s.status = m; s.err = !!e; },
  () => {}, () => {}, s => s.arts);
let fails = 0;
const ok = (cond, msg) => { console.log((cond ? 'ok   ' : 'FAIL ') + msg); if (!cond) fails++; };
const story = () => ({ title: 'Old', arts: [{ source: 'NPR', title: 'Something happened', body: '' }] });

(async () => {
  let s = story();
  reply = JSON.stringify({ sharper: ['Sharp one', 'Sharp two'],
    need_to_know: 'Nvidia Makes the Chips AI Runs On. Its CEO Quit.', basis: 'background: Nvidia makes AI chips' });
  await P.punchUpHeadline(s);
  ok(/NEED-TO-KNOW HEADLINE/.test(asked) && /plainly true/.test(asked), 'the prompt asks for a need-to-know headline and its rules');
  ok(s.headlineCandidates.length === 3, 'three candidates');
  ok(s.headlineNtk && s.headlineNtk.i === 2 && /Chips AI Runs On/.test(s.headlineCandidates[2]), 'the need-to-know headline is last and marked');
  ok(/background/.test(s.headlineNtk.basis), 'it carries what it rests on');
  P.applyPunchedHeadline(s, s.headlineCandidates[2]);
  ok(s.title.startsWith('Nvidia') && s.headlineNtk === null && s.headlineCandidates === null, 'picking it sets the headline and clears the choices');

  s = story(); reply = '```json\n' + JSON.stringify({ sharper: ['a', 'b'], need_to_know: 'N. T.', basis: 'in the sources' }) + '\n```';
  await P.punchUpHeadline(s);
  ok(s.headlineNtk && s.headlineCandidates[2] === 'N. T.', 'a fenced reply still parses');

  s = story(); reply = JSON.stringify({ sharper: ['a', 'b', 'c'], need_to_know: '', basis: 'nothing certain and strong' });
  await P.punchUpHeadline(s);
  ok(s.headlineCandidates.length === 3 && s.headlineNtk && s.headlineNtk.i === -1, 'no standing truth: three plain headlines and the reason, nothing forced');

  s = story(); reply = JSON.stringify(['x', 'y', 'z']);
  await P.punchUpHeadline(s);
  ok(s.headlineCandidates.length === 3 && s.headlineNtk === null, 'an old-shape array gives three plain headlines, none marked');

  s = story(); reply = 'not json';
  await P.punchUpHeadline(s);
  ok(s.err && !s.busy, 'a bad reply shows an error and frees the story');

  const ui = html.slice(html.indexOf('s.headlineCandidates.map('), html.indexOf('punch-dismiss', html.indexOf('s.headlineCandidates.map(')));
  ok(/need to know/.test(ui) && /rests on/.test(ui) && /no need-to-know headline/.test(ui), 'the Lineup labels the headline and shows what it rests on');
  console.log(fails ? `${fails} failed` : 'all passed');
  process.exit(fails ? 1 : 0);
})();
