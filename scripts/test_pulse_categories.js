#!/usr/bin/env node
// Runs the pure category logic from ntk-pulse/pulse.html (between CATS:BEGIN and CATS:END)
// against the same cases as editorial/test_categories.py, so the browser and CI cannot drift
// silently (T-0079).   node scripts/test_pulse_categories.js
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'ntk-pulse/pulse.html'), 'utf8');
const m = html.match(/\/\* CATS:BEGIN \*\/([\s\S]*?)\/\* CATS:END \*\//);
if (!m) { console.error('FAIL: CATS block not found'); process.exit(1); }
const L = new Function(m[1] + '; return {validateCat, selectBeginnings, pickBeginnings, lensSupported, catTextProblems};')();
const poolDoc = JSON.parse(fs.readFileSync(path.join(root, 'ntk-pulse/data/backstory-pool.json'), 'utf8'));
const poolBy = Object.fromEntries(poolDoc.objects.map(o => [o.id, o]));
const spec = JSON.parse(fs.readFileSync(path.join(root, 'editorial/lenses.json'), 'utf8'));
const ALTMAN = "OpenAI's publicist tried to shut down a question about a dead teenager. Altman told a magazine that some bad things will happen as a result of AI. Lawmakers and the FTC opened probes of the chatbot maker.";
const pid = (part, pool) => { const o = poolDoc.objects.find(o => o.title.toLowerCase().includes(part.toLowerCase()) && (!pool || o.pool === pool)); if (!o) throw new Error(part); return o.id; };
const good = () => ({
  id: 'p-ai', title: 'AI', status: 'approved',
  contest: 'Whether the companies building AI should answer for the harm it causes, or whether its benefits justify letting society absorb some of that harm.',
  stakes: 'Whether, when and by whom this new technology should be regulated, and who should share in its benefits, is still being settled. Companies, courts and lawmakers are each claiming the decision.',
  lenses: ['tech'], by: { contest: 'model', stakes: 'model', lenses: 'model' },
  approved_objects: [pid('Privacy Act of 1974'), pid('Executive Order 14110')],
  objects: [pid('Privacy Act of 1974'), pid('Telecommunications Act of 1996'), pid('PATRIOT'), pid('Executive Order 14110')].map(object_id => ({ object_id })),
  beginnings: [
    { object_id: pid('Privacy Act of 1974'), line: 'Congress limited what federal agencies may do with personal records after Watergate-era surveillance scandals.' },
    { object_id: pid('Telecommunications Act of 1996'), line: "Congress rewrote the nation's communications law, covering telephone, cable and broadcast, and for the first time the internet." },
    { object_id: pid('PATRIOT'), line: "Congress passed the USA PATRIOT Act soon after the terrorist attacks of that year, widening the government's powers to investigate and watch people." },
    { object_id: pid('Executive Order 14110'), line: 'President Biden ordered the first broad federal rules on the safety and testing of artificial intelligence systems.' }]
});
const run = (c, texts = [ALTMAN], origin = 2025) => L.validateCat(c, poolBy, spec, texts, origin);
let fails = 0;
const check = (name, ok, detail) => { console.log((ok ? 'ok   ' : 'FAIL ') + name + (ok ? '' : '  ' + JSON.stringify(detail))); if (!ok) fails++; };
let r = run(good());
check('a well-formed tech category validates cleanly', !r.problems.length && r.clean.beginnings.length === 4 && r.clean.objects.length === 4, r.problems);
let x = good(); x.lenses = ['tech', 'china']; r = run(x);
check('a lens the story does not support is dropped (the AI page defect)', r.clean.lenses.join() === 'tech' && r.problems.some(p => p.includes('china')), r);
x = good(); x.lenses = ['tech', 'china']; x.by.lenses = 'editor'; r = run(x);
check('a lens the editor chose is honoured', r.clean.lenses.join() === 'tech,china', r.clean.lenses);
x = good(); x.approved_objects = []; r = run(x);
check('an unapproved candidate is dropped, with its Beginning', r.clean.beginnings.length === 2 && r.clean.objects.length === 2, r.problems);
x = good(); r = run(x, [ALTMAN], 2000);
check('a Beginning dated at or after the origin is dropped', r.clean.beginnings.every(b => +b.year < 2000) && r.clean.beginnings.length === 2, r.clean.beginnings);
x = good(); x.stakes = 'Billions hang on this — and a landmark ruling could end it all for good now.'; r = run(x);
check('model text with a dash and a banned word is dropped, not repaired', r.clean.stakes === '' && r.problems.some(p => p.includes('dash')), r.problems);
x.by.stakes = 'editor'; r = run(x);
check('the same text written by the editor is kept', r.clean.stakes !== '', r.problems);
x = good(); const sh = pid('Shanghai Communique', 'matrix'); x.beginnings[1].object_id = sh; x.objects.push({ object_id: sh }); r = run(x);
check("a Beginning from outside the category's lenses is dropped", !r.clean.beginnings.some(b => b.object_id === sh) && r.problems.some(p => p.includes('lenses')), r.problems);
x = good(); x.objects.push({ object_id: 'no-such-object' }); r = run(x);
check('an object not in the pool is dropped', r.problems.some(p => p.includes('not in the pool')) && r.clean.objects.length === 4, r.problems);
x = good(); x.indicator = { label: 'x', verified: false }; r = run(x);
check('an unverified indicator is dropped', r.clean.indicator === null, r.problems);
x = good(); x.indicator = { label: 'Oppose a data center nearby', then_value: '42%', now_value: '75%', source: 'Heatmap Pro', as_of: 'August 2026', verified: true }; r = run(x);
check('an indicator with no source link is dropped', r.clean.indicator === null, r.problems);
x.indicator.source_url = 'https://heatmap.news/daily/data-center-opposition-poll-collapse'; r = run(x);
check('a fully sourced, checked indicator is kept', r.clean.indicator !== null, r.problems);
x = good(); x.beginnings[1].line = x.beginnings[0].line; r = run(x);
check('two Beginnings with the same line: the second is dropped', r.clean.beginnings.length === 3 && r.problems.some(p => p.includes('same line')), r.problems);
x = good(); r = run(x, []);
check('with no story filed yet, a model-chosen lens is kept', r.clean.lenses.join() === 'tech', r.clean.lenses);
// selection rule
const techs = poolDoc.objects.filter(o => o.lenses.includes('tech') && o.url);
const pick = L.selectBeginnings(techs, 6);
check('selectBeginnings keeps the most recent object and spreads the rest', pick.length === 6 && pick[pick.length - 1].id === techs.slice().sort((a, b) => a.sort < b.sort ? -1 : 1).pop().id, pick.map(o => o.year));
const pk = L.pickBeginnings(techs, 6);
check('pickBeginnings takes every matrix object first, then fills with candidates', techs.filter(o => o.pool === 'matrix').every(o => pk.some(p => p.id === o.id)) && pk.length === 6, pk.map(o => o.pool + ' ' + o.year));
check('lensSupported reads whole words only', L.lensSupported('tech', spec, ALTMAN) && !L.lensSupported('china', spec, ALTMAN) && !L.lensSupported('tech', spec, 'The mail arrived said the senator'), null);
console.log('\n' + fails + ' failed'); process.exit(fails ? 1 : 0);
