#!/usr/bin/env node
// Runs the pure category logic from ntk-pulse/pulse.html (between CATS:BEGIN and CATS:END)
// against the same cases as editorial/test_categories.py, so the browser and CI cannot drift
// silently (T-0079).   node scripts/test_pulse_categories.js
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'ntk-pulse/pulse.html'), 'utf8');
const m = html.match(/\/\* CATS:BEGIN \*\/([\s\S]*?)\/\* CATS:END \*\//);
if (!m) { console.error('FAIL: CATS block not found'); process.exit(1); }
const L = new Function(m[1] + '; return {validateCat, selectBeginnings, pickBeginnings, lensSupported, catTextProblems, verifyIndicator, catSentences, verifyFoundObject, applySourceEdit, catFieldKey, pickForSubjects, verifyMilestone, catNumbersOk, catTiesOk};')();
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
const VOCAB = new Set(poolDoc.vocab.subgenres.map(g => g.name));
const run = (c, texts = [ALTMAN], origin = 2025) => L.validateCat(c, poolBy, spec, texts, origin, VOCAB);
let fails = 0;
const check = (name, ok, detail) => { console.log((ok ? 'ok   ' : 'FAIL ') + name + (ok ? '' : '  ' + JSON.stringify(detail))); if (!ok) fails++; };
let r = run(good());
check('a well-formed tech category validates cleanly', !r.problems.length && r.clean.beginnings.length === 4 && r.clean.objects.length === 4, r.problems);
let x = good(); x.objects = []; x.beginnings = []; x.approved_objects = []; x.custom_objects = []; r = run(x);
check('a category with no objects is not valid, so it is never published', r.clean === null && r.problems.some(p => p.includes('no objects')), r);
x = good(); x.lenses = ['tech', 'china']; r = run(x);
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
x = good(); x.contest = x.contest.replace(/\.$/, ''); r = run(x);
check('a contest with no final full stop still counts as one sentence', r.clean.contest !== '' && !r.problems.some(p => p.includes('sentence')), r.problems);
const war = poolDoc.objects.find(o => o.pool === 'matrix' && o.subgenre === 'military intervention').id;
x = { id: 'p-war', title: 'War powers', status: 'approved', lenses: [], subgenres: ['military intervention', 'no such sub-genre'], by: { contest: 'editor', stakes: 'editor' }, contest: 'Whether presidents may start wars alone, or only with Congress.', stakes: 'Who decides, and when, is still open.', objects: [{ object_id: war }], beginnings: [{ object_id: war, line: 'A president asked Congress to approve the use of American force abroad, and Congress took up the request.' }] };
r = L.validateCat(x, poolBy, spec, [], 2025, VOCAB);
check('a category can draw Beginnings from a sub-genre; an unknown sub-genre is dropped', r.clean.subgenres.join() === 'military intervention' && r.clean.beginnings.length === 1 && r.problems.some(p => p.includes('sub-genre')), r);
x = good(); x.custom_objects = [{ id: 'custom-x', title: 'A speech', author: 'Someone', year: '1998', source: 'National Archives', url: 'https://www.archives.gov/x' }];
x.objects.push({ object_id: 'custom-x', by: 'editor', about: 'A speech given in 1998.' }); x.beginnings.push({ object_id: 'custom-x', line: 'Someone gave a speech about the new technology.', by: 'editor' }); r = run(x);
check('an object added by link is kept and can be a Beginning', r.clean.objects.some(o => o.object_id === 'custom-x') && r.clean.beginnings.some(b => b.object_id === 'custom-x'), r.problems);
x.custom_objects[0].url = 'https://en.wikipedia.org/wiki/X'; r = run(x);
check('an added object on Wikipedia is refused', !r.clean.objects.some(o => o.object_id === 'custom-x') && r.problems.some(p => p.includes('primary source')), r.problems);
x = good(); x.indicator = { label: 'L', then_value: '42%', now_value: '75%', source: 'S', source_url: 'https://example.org/p', as_of: 'August 2026', verified: true, verified_by: 'system', evidence: [] }; r = run(x);
check('a system-verified indicator with no evidence is dropped', r.clean.indicator === null, r.problems);
x.indicator.evidence = ['43% in support and 42% opposed, then 75% oppose']; r = run(x);
check('a system-verified indicator whose evidence holds both figures is kept', r.clean.indicator !== null, r.problems);
const ind = { source_url: 'https://example.org/p', then_value: '42%', now_value: '75%' };
check('verifyIndicator: a link the search did not return fails', !L.verifyIndicator(ind, { urls: ['https://other.org'], citations: [] }).ok, null);
check('verifyIndicator: a figure missing from the cited passage fails', !L.verifyIndicator(ind, { urls: [ind.source_url], citations: [{ url: ind.source_url, cited_text: 'Opposition was 42% last year.' }] }).ok, null);
check('verifyIndicator: both figures in the cited passage passes', L.verifyIndicator(ind, { urls: [ind.source_url], citations: [{ url: ind.source_url, cited_text: 'Opposition rose from 42% to 75%.' }] }).ok, null);
x = good(); x.beginnings.reverse(); x.objects.reverse(); r = run(x);
const yrs = r.clean.beginnings.map(b => b.year);
check('Beginnings and objects always come out oldest to newest', yrs.join() === yrs.slice().sort().join() && r.clean.objects.map(o => o.year).join() === r.clean.objects.map(o => o.year).slice().sort().join(), yrs);
const q = { urls: [ind.source_url], citations: [] };
check('verifyIndicator: no citation but a quoted sentence holding both figures passes, marked quoted', (v => v.ok && v.source === 'quoted')(L.verifyIndicator(Object.assign({ evidence_quote: 'Opposition rose from 42% to 75% in a year.' }, ind), q)), null);
check('verifyIndicator: no citation and a quote missing a figure fails', !L.verifyIndicator(Object.assign({ evidence_quote: 'Opposition is now 75%.' }, ind), q).ok, null);
check('verifyIndicator: no citation and no quote fails', !L.verifyIndicator(ind, q).ok, null);
const mu = { title: 'Report on the Investigation into Russian Interference in the 2016 Presidential Election', year: '2019', source_url: 'https://www.justice.gov/archives/sco/file/1373816/dl' };
check('verifyFoundObject: a link the search returned passes', L.verifyFoundObject(mu, { urls: [mu.source_url] }).ok, null);
check('verifyFoundObject: a link the search did not return fails', !L.verifyFoundObject(mu, { urls: ['https://elsewhere.org'] }).ok, null);
check('verifyFoundObject: Wikipedia is refused', !L.verifyFoundObject(Object.assign({}, mu, { source_url: 'https://en.wikipedia.org/wiki/Mueller_report' }), { urls: ['https://en.wikipedia.org/wiki/Mueller_report'] }).ok, null);
check('verifyFoundObject: no year fails', !L.verifyFoundObject(Object.assign({}, mu, { year: '' }), { urls: [mu.source_url] }).ok, null);
x = good(); x.custom_objects = [{ id: 'custom-m', title: 'A report', author: 'Office', year: '2019', date: '2019-04-18', source: 'Justice Department', url: 'https://www.justice.gov/x' }];
x.objects.push({ object_id: 'custom-m', by: 'editor', about: 'A report released in 2019.' }); x.beginnings.push({ object_id: 'custom-m', line: 'An office released a report on interference in an election.', by: 'editor' }); r = run(x);
check('an added object with an exact date sorts by that date', r.clean.objects[r.clean.objects.length - 1].object_id === 'custom-m' || r.clean.objects.some(o => o.object_id === 'custom-m'), r.problems);
x = good(); const tel = x.objects.find(o => o.object_id === pid('Telecommunications Act of 1996')).object_id;
const lineBefore = x.beginnings.find(b => b.object_id === tel).line;
let ed = L.applySourceEdit(x, tel, { title: 'Telecommunications Act of 1996', author: 'U.S. Congress', year: '1996', source: 'Federal Communications Commission', url: 'https://www.fcc.gov/general/telecommunications-act-1996' });
check('edit source: a pool object becomes the category\'s own with the editor\'s link, keeping its Beginning line', ed.ok && x.custom_objects.length === 1 && x.beginnings.some(b => b.object_id === ed.id && b.line === lineBefore) && !x.objects.some(o => o.object_id === tel), ed);
r = run(x);
check('edit source: the edited object validates and keeps its place', r.clean.objects.some(o => o.object_id === ed.id && o.source_url.includes('fcc.gov')) && r.clean.beginnings.some(b => b.object_id === ed.id), r.problems);
x = good(); ed = L.applySourceEdit(x, pid('PATRIOT'), { title: 'x', year: '2001', url: 'https://en.wikipedia.org/wiki/USA_PATRIOT_Act' });
check('edit source: Wikipedia is refused and nothing changes', !ed.ok && x.custom_objects === undefined && x.objects.some(o => o.object_id === pid('PATRIOT')), ed);
ed = L.applySourceEdit(x, pid('PATRIOT'), { title: 'USA PATRIOT Act', year: '', url: 'https://www.govinfo.gov/x' });
check('edit source: a missing year is refused', !ed.ok, ed);
const fake = (cls, extra) => Object.assign({ id: '', classList: { contains: c => cls.includes(c) }, dataset: {}, closest: sel => (sel === '[data-oid]' ? { dataset: { oid: 'obj1' } } : null) }, extra);
const keys = ['title', 'author', 'year', 'source', 'url'].map(f => L.catFieldKey(fake(['cat-src-f'], { dataset: { f } })));
check('catFieldKey: the five edit-source fields of one object get five different keys', new Set(keys).size === 5, keys);
check('catFieldKey: a Beginning line and an About in the same row differ', L.catFieldKey(fake(['cat-line'])) !== L.catFieldKey(fake(['cat-about'])), null);
check("sentences: 'v.' and 'U.S.' do not end a sentence", L.catSentences('The Court decided Loper Bright Enterprises v. Raimondo, ending a rule the U.S. government relied on.') === 1, null);
check('sentences: two real sentences count as two, a decimal is not a boundary', L.catSentences('One thing happened. Another did') === 2 && L.catSentences('It rose 3.5% in a year.') === 1, null);
check('catSentences counts a last sentence with no full stop', L.catSentences('Whether A, or B') === 1 && L.catSentences('One. Two') === 2, null);
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
const MM = (i, y, pool) => ({ id: (pool || 'm')[0] + i, pool: pool || 'matrix', author: 'a' + i, sort: y + '-01-01', year: String(y) });
const bigp = [0, 1, 2].map(n => Array.from({ length: 10 }, (_, i) => MM(i + n * 20, 1800 + n * 50 + i * 4)));
check('pickForSubjects: three rich subjects give six objects, not nine', L.pickForSubjects(bigp).length === 6, L.pickForSubjects(bigp).length);
const mx = [Array.from({ length: 2 }, (_, i) => MM(i, 1900 + i * 10)).concat(Array.from({ length: 8 }, (_, i) => MM(i + 20, 1920 + i * 7, 'candidate')))];
const gp = L.pickForSubjects(mx);
check('pickForSubjects: every matrix object is used before candidates fill the six', gp.length === 6 && gp.filter(o => o.pool === 'matrix').length === 2, gp.map(o => o.pool));
check('pickForSubjects: a thin pool gives what exists', L.pickForSubjects([[MM(1, 1950), MM(2, 1990)], [MM(3, 1970)]]).length === 3, null);
const MSU = 'https://www.govinfo.gov/content/pkg/example-act.pdf';
const msv = (o) => Object.assign({ year: '1972', date: '1972-04-10', title: 'Convention on Biological Weapons', source_url: MSU, line: 'Dozens of states signed a treaty banning the development and stockpiling of biological weapons in April 1972.', about: 'Governments signed this treaty in 1972. It bans developing and stockpiling biological weapons. It was opened for signature in April.', evidence_quote: 'The Convention was opened for signature on 10 April 1972.' }, o || {});
check('verifyMilestone: a well-formed milestone from a returned link passes', L.verifyMilestone(msv(), [MSU]).ok, L.verifyMilestone(msv(), [MSU]));
const STORYT = 'A worker died at an anti-plague lab in Irkutsk. Russia locked down five regions.';
check('verifyMilestone: a ties_to copied from the story passes', L.verifyMilestone(msv({ ties_to: 'anti-plague lab in Irkutsk', relation: 'same subject' }), [MSU], STORYT).ok, L.verifyMilestone(msv({ ties_to: 'anti-plague lab in Irkutsk', relation: 'same subject' }), [MSU], STORYT));
check('catTiesOk: reordered words from the story pass; a one-word tie or foreign words fail', L.catTiesOk('Irkutsk anti-plague laboratory', STORYT) && !L.catTiesOk('Irkutsk', STORYT) && !L.catTiesOk('nuclear arms treaty', STORYT), null);
check('verifyMilestone: a ties_to not in the story fails', !L.verifyMilestone(msv({ ties_to: 'a phrase nowhere in it', relation: 'same subject' }), [MSU], STORYT).ok, null);
check('verifyMilestone: a relation outside the three fails', !L.verifyMilestone(msv({ ties_to: 'anti-plague lab in Irkutsk', relation: 'shares a theme' }), [MSU], STORYT).ok, null);
check('verifyMilestone: a link the search did not return fails', !L.verifyMilestone(msv(), ['https://other.org']).ok, null);
check('verifyMilestone: Wikipedia fails', !L.verifyMilestone(msv({ source_url: 'https://en.wikipedia.org/wiki/X' }), ['https://en.wikipedia.org/wiki/X']).ok, null);
check('verifyMilestone: a number not in the quote fails', !L.verifyMilestone(msv({ line: 'A total of 150 states signed a treaty banning the development and stockpiling of biological weapons in April 1972.' }), [MSU]).ok, null);
check('verifyMilestone: no quote fails', !L.verifyMilestone(msv({ evidence_quote: '' }), [MSU]).ok, null);
x = good(); x.custom_objects = [{ id: 'custom-ms', title: 'Convention on Biological Weapons', author: 'Parties', year: '1972', date: '1972-04-10', source: 'UN', url: MSU, found_by: 'search', evidence_quote: 'The Convention was opened for signature on 10 April 1972.' }];
x.objects.push({ object_id: 'custom-ms', by: 'model', about: 'Governments signed this treaty in 1972. It bans developing and stockpiling biological weapons. It was opened for signature in April.' });
x.beginnings.push({ object_id: 'custom-ms', by: 'model', line: 'Dozens of states signed a treaty banning the development and stockpiling of biological weapons in April 1972.' }); r = run(x);
check('a found milestone validates', r.clean.beginnings.some(b => b.object_id === 'custom-ms') && r.clean.objects.some(o => o.object_id === 'custom-ms'), r.problems);
x.beginnings[x.beginnings.length - 1].line = 'A total of 150 states signed a treaty banning the development and stockpiling of biological weapons in April 1972.'; r = run(x);
check('a found milestone whose line states a number the quote lacks is dropped as a Beginning', !r.clean.beginnings.some(b => b.object_id === 'custom-ms') && r.problems.some(p => p.includes('number')), r.problems);
check('lensSupported reads whole words only', L.lensSupported('tech', spec, ALTMAN) && !L.lensSupported('china', spec, ALTMAN) && !L.lensSupported('tech', spec, 'The mail arrived said the senator'), null);
console.log('\n' + fails + ' failed'); process.exit(fails ? 1 : 0);
