#!/usr/bin/env node
// Runs the Backstory build from ntk-pulse/pulse.html (the CATS block and the BSX block) in node, with stand-in
// model replies, against the seven stories of the 2026-11-10 edition (editorial/fixtures/backstory-2026-11-10.json,
// from commit 845a14fb). T-0117: scopes, ties, thin, widen before search, rewrite never drop, event and recent
// rules, filler notes, the self-review, held pages, and the editor's words.   node scripts/test_pulse_backstory.js
//
// The model is never called. What these tests prove is the machinery around it: what is placed, left out,
// flagged, held, and which calls run in which order. Whether real builds come out better is measured in staging
// Pulse with the editor's key (docs/tickets/T-0117).
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'ntk-pulse/pulse.html'), 'utf8');
const cats = html.match(/\/\* CATS:BEGIN \*\/([\s\S]*?)\/\* CATS:END \*\//), bsx = html.match(/\/\* BSX:BEGIN \*\/([\s\S]*?)\/\* BSX:END \*\//);
if (!cats || !bsx) { console.error('FAIL: the CATS or BSX block was not found in pulse.html'); process.exit(1); }
if (!/async function bsxModel\(/.test(bsx[1])) { console.error('FAIL: bsxModel is not in the BSX block'); process.exit(1); }
const NAMES = ['bsxTerms', 'bsxScopes', 'bsxWider', 'bsxScopeShortlist', 'bsxCompose', 'bsxComposePrompt', 'bsxShape', 'bsxCheck', 'bsxEnforce', 'bsxBuild',
  'bsxSelfReview', 'bsxHold', 'bsxRefreshHere', 'bsxDirected', 'bsxOpensWithSource', 'bsxNoteFiller', 'bsxTooRecent', 'bsxDocDate', 'bsxMilestoneProblems', 'bsxApplyText', 'catTiesOk'];
// The live bsxModel is renamed out of the way; every call reaches the stand-in passed as `bsxModel`.
// bsxApplyText is outside the block in pulse.html; it is pure, so it is lifted on its own.
const applyText = html.match(/function bsxApplyText\(c, text\)\{[\s\S]*?\n\}/);
const src = cats[1] + '\n' + bsx[1].replace('async function bsxModel(', 'async function bsxModelLive(') + '\n' + applyText[0] + '\n; return {' + NAMES.join(',') + '};';
const env = { POOL: { objects: [] }, BSR_PUBLISHED: { rows: [] }, PUBCATS: [], ARENA: { objects: [] }, SETTINGS: { antKey: 'stand-in' }, document: null };
let REPLY = () => ({}), CALLS = [];
const kindOf = p => /Name that history/.test(p) ? 'terms' : /You compose one news story/.test(p) ? 'compose' : /broke their rules/.test(p) ? 'repair'
  : /Rewrite each milestone line/.test(p) ? 'reline' : /reviewing one Backstory page/.test(p) ? 'review' : /has since been revised/.test(p) ? 'change' : 'other';
const stub = async (model, prompt) => {
  const kind = kindOf(prompt); CALLS.push({ kind, model, prompt });
  const r = REPLY(kind, prompt, CALLS.filter(c => c.kind === kind).length);
  if (r instanceof Error) throw r;
  return { text: typeof r === 'string' ? r : JSON.stringify(r), urls: [], usage: { input_tokens: 1000, output_tokens: 200 } };
};
const L = new Function('POOL', 'BSR_PUBLISHED', 'PUBCATS', 'ARENA', 'SETTINGS', 'document', 'bsxModel',
  src)(env.POOL, env.BSR_PUBLISHED, env.PUBCATS, env.ARENA, env.SETTINGS, env.document, stub);

const FX = JSON.parse(fs.readFileSync(path.join(root, 'editorial/fixtures/backstory-2026-11-10.json'), 'utf8'));
const DATE = FX.date;
const byKey = Object.fromEntries(FX.stories.map(s => [s.key, s]));
const story = key => { const s = byKey[key]; return { headline: s.headline, lede: s.lede, truths: s.truths, date: DATE }; };
// The library: every document the seven pages shipped, as Pulse's library holds it (a note written by the model is
// not the library's, so it is not carried).
const LIB = {};
FX.stories.forEach(s => (s.page.case || []).forEach(o => { LIB[o.object_id] = { id: o.object_id, title: o.title, author: o.author || '', year: String(o.year), url: o.source_url,
  about: o.about_by === 'library' ? o.about : '', why: '', kind: o.kind || 'found', source_kind: o.source_kind || '', row: '', subgenre: '', lenses: [], categories: new Set(['fixture']), date: '' }; }));
const addDoc = (id, year, title, extra) => { LIB[id] = Object.assign({ id, title, author: 'Test author', year: String(year), url: 'https://www.govinfo.gov/' + id, about: '', why: '', kind: 'matrix', source_kind: '', row: '', subgenre: '', lenses: [], categories: new Set(['fixture']), date: '' }, extra || {}); return id; };
const ALL = () => Object.keys(LIB);
const lib = () => LIB;

const TAX = '3be9762b411856bb', NVDA = '78aa026d0c91fe6f', TB = '6c24db2c1b682211', HEG = '3c8b0c2c39a21fdb', CARTER = '6c735a29b9a9ff65';
// Lines that keep every rule, for stand-in milestones (12 to 25 words, one sentence, no numbers).
const LINE = n => ['Congress debated how far the national government could reach into private fortunes through the income tax laws.',
  'State lawmakers in California first proposed a direct levy on the largest personal fortunes held by residents of the state.',
  'Voters in several states weighed new taxes on the very rich to pay for public services after federal cuts.',
  'Opponents built a broad coalition of business groups and wealthy donors to fight new levies on accumulated wealth.'][n];
const TIES = { tax: 'California billionaires wealth', health: 'healthcare federal cuts', ballot: 'California voters rejected', money: 'opposition group raised' };
const SCOPES = { scopes: [
  { level: 'narrow', name: "California's billionaire tax", terms: ['Proposition 40', 'billionaire tax', 'California ballot measure'] },
  { level: 'middle', name: 'State taxes on great wealth', terms: ['wealth tax', 'state income tax', 'ballot initiative'] },
  { level: 'wide', name: 'Taxing great fortunes', terms: ['populist party platform', 'graduated income tax', 'tax cuts and jobs act'] }] };
const ok3 = ids => ids.map((id, i) => ({ id, line: LINE(i), ties_to: [TIES.tax, TIES.health, TIES.ballot, TIES.money][i] }));
const page = (extra) => Object.assign({ row: 'Taxes', title: 'Taxing the very rich', contest: 'Whether a state can tax the fortunes of its richest residents when they can spend heavily to defeat it at the ballot.',
  stakes: 'California would have raised money for healthcare from a few hundred of its richest residents. The defeat tells other states what a tax on great wealth costs to pass at the ballot box.', here: 'California voters rejected a one-time tax on the wealth of its billionaires after its opponents outspent its backers.', thin: null, why: 'stand-in' }, extra);

let fails = 0;
const check = (name, ok, detail) => { console.log((ok ? 'ok   ' : 'FAIL ') + name + (ok ? '' : '  ' + JSON.stringify(detail).slice(0, 600))); if (!ok) fails++; };
const reset = (fn) => { CALLS = []; REPLY = fn; };

(async () => {
  // Stand-in documents that tie to the billionaire-tax story, dated well before it.
  const D1 = addDoc('1913-02-03-sixteenth-amendment', 1913, 'Sixteenth Amendment to the Constitution: graduated income tax');
  const D2 = addDoc('2020-08-01-california-ab-2088-wealth-tax', 2020, 'California Assembly Bill 2088: a wealth tax on residents', { kind: 'candidate' });
  const D3 = addDoc('2024-03-01-washington-state-wealth-tax-bill', 2024, 'Washington State wealth tax bill');
  const D4 = addDoc('2025-07-04-one-big-beautiful-bill-act', 2025, 'One Big Beautiful Bill Act: federal healthcare cuts');
  const POPULIST = '1892-07-04-populist-party-platform', CU = '2010-01-21-citizens-united-v-federal-election-commission', TCJA = '2017-12-22-tax-cuts-and-jobs-act';
  const edits = () => ({ pool: ALL() });

  // ── scope ─────────────────────────────────────────────────────────────────────────────────────────────────────
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', scope_why: 'State wealth taxes are the policy this ballot measure belongs to.', milestones: ok3([D1, D2, D3]), starts: D3 }) : k === 'review' ? { verdict: 'ready', concerns: [] } : {});
  let c = await L.bsxCompose(story(TAX), null, null, lib(), { pool: ALL() }, [], []);
  const cp = CALLS.find(x => x.kind === 'compose').prompt;
  check('scope: three scopes are named and the two not chosen are kept as picks',
    c.scope && c.scope.level === 'middle' && /State wealth taxes/.test(c.scope.why) && c.scope_picks.map(p => p.level).join() === 'narrow,wide'
    && c.scope_picks.every(p => p.name && p.terms.length) && SCOPES.scopes.every(s => cp.includes(s.name)) && /scope_why/.test(cp)
    && CALLS.filter(x => x.kind === 'terms').length === 1 && CALLS.filter(x => x.kind === 'terms')[0].model === 'claude-haiku-5-5',
    { scope: c.scope, picks: c.scope_picks, calls: CALLS.map(x => x.kind) });
  check('scope: each document in the composer\'s list says which scope found it', /populist-party-platform \| [^\n]*\| scope: wide/.test(cp), cp.split('\n').filter(l => /populist/.test(l)));
  check('scope: an answer in the old shape becomes one middle scope, so the build does not fail', L.bsxScopes({ terms: ['a', 'b'] }).length === 1 && L.bsxScopes({ terms: ['a', 'b'] })[0].level === 'middle', L.bsxScopes({ terms: ['a', 'b'] }));
  check('scope: the next wider scope is the next one the naming call gave', L.bsxWider('narrow', SCOPES.scopes) === 'middle' && L.bsxWider('wide', SCOPES.scopes) === null && L.bsxWider('narrow', SCOPES.scopes.filter(s => s.level !== 'middle')) === 'wide', null);

  // ── tie ───────────────────────────────────────────────────────────────────────────────────────────────────────
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'wide', milestones: ok3([D1, D2, D3]).concat([
    { id: POPULIST, line: 'The People\'s Party adopted a platform demanding a graduated income tax at its first national convention that summer.', ties_to: 'Populist movement farmers' },
    { id: CU, line: 'The Supreme Court ruled that the government may not limit independent political spending by corporations and unions.' }]), starts: D3 }) : {});
  c = await L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []);
  const lo = Object.fromEntries((c.left_out || []).map(x => [x.object_id, x]));
  check('tie: a milestone that names nothing in the story is not placed',
    c.beginnings.length === 3 && !c.beginnings.some(b => [POPULIST, CU].includes(b.object_id)) && lo[POPULIST] && /Populist movement farmers/.test(lo[POPULIST].reason)
    && lo[CU] && /names nothing/.test(lo[CU].reason) && c.beginnings.every(b => b.ties_to) && !c.case.some(o => o.object_id === POPULIST),
    { begs: c.beginnings.map(b => b.object_id), left: c.left_out });
  check('tie: the ties are tested against the real story text (catTiesOk)', L.catTiesOk(TIES.tax, [story(TAX).headline, story(TAX).lede, story(TAX).truths].join(' ')) && !L.catTiesOk('Populist movement farmers', story(TAX).truths), null);

  // ── thin ──────────────────────────────────────────────────────────────────────────────────────────────────────
  // The 2026-11-10 billionaire-tax page: the 1892 platform, Citizens United and the 2017 tax act, and thin: null.
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'wide', thin: null, milestones: [
    { id: POPULIST, line: 'The People\'s Party adopted a platform demanding a graduated income tax at its first national convention that summer.', ties_to: 'Populist Party platform' },
    { id: CU, line: 'The Supreme Court ruled that the government may not limit independent political spending by corporations and unions.', ties_to: 'corporate political spending' },
    { id: TCJA, line: 'Congress passed a broad tax law that cut the corporate rate and changed the brackets for individual taxpayers.', ties_to: 'federal tax brackets corporate' }], starts: TCJA }) : {});
  c = await L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []);
  check('thin: three milestones that do not connect is a thin page', c.beginnings.length === 0 && !!c.thin && c.left_out.length === 3, { thin: c.thin, begs: c.beginnings.length });
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', thin: 'the library has nothing on the 2026 campaign', milestones: ok3([D1, D2, D3]), starts: D3 }) : {});
  c = await L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []);
  check('thin: three connected milestones are not thin, and what the model said is missing is kept as the gap', c.thin === null && /2026 campaign/.test(c.gaps), { thin: c.thin, gaps: c.gaps });

  // Widen before search: narrow is thin (one connects), middle connects three; no search runs.
  let searched = 0; const research = async () => { searched++; CALLS.push({ kind: 'search' }); return { added: [], note: 'stand-in search' }; };
  const forced = p => (p.match(/build this page on the (\w+) scope/) || [])[1];
  reset((k, p) => k === 'terms' ? SCOPES : k === 'compose' ? (forced(p) === 'middle' ? page({ scope: 'middle', milestones: ok3([D1, D2, D3]), starts: D3 }) : page({ scope: 'narrow', thin: 'little on California', milestones: ok3([D2]), starts: D2 })) : {});
  c = await L.bsxBuild(story(TAX), lib, edits(), [], [], research);
  const order1 = CALLS.map(x => x.kind).join(','), searched1 = searched;
  // Still thin after widening: then, and only then, one search, and a rebuild with what it found.
  const FOUND = addDoc('custom-prop-40-ballot-measure-text-2026-abc123', 2026, 'Proposition 40: the billionaire tax initiative, full text', { date: '2026-03-01', kind: 'found' });
  searched = 0; const research2 = async () => { searched++; CALLS.push({ kind: 'search' }); return { added: [{ id: FOUND }], note: 'found 1' }; };
  reset((k, p, n) => k === 'terms' ? SCOPES : k === 'compose' ? (n <= 2 ? page({ scope: forced(p) || 'narrow', thin: 'thin', milestones: ok3([D2]), starts: D2 }) : page({ scope: 'narrow', milestones: ok3([D2, D3, FOUND]), starts: D3 })) : {});
  const c2 = await L.bsxBuild(story(TAX), lib, { pool: ALL().filter(i => i !== FOUND) }, [], [], research2);
  const order2 = CALLS.map(x => x.kind).filter(k => k !== 'repair' && k !== 'reline').join(',');
  // Already on the widest scope: nothing wider, so the search runs straight away.
  searched = 0;
  reset((k, p) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'wide', thin: 'thin', milestones: ok3([D2]), starts: D2 }) : {});
  const c3 = await L.bsxBuild(story(TAX), lib, edits(), [], [], research);
  check('thin: a thin build widens over the library before it searches',
    searched1 === 0 && searched === 1 && c3.steps.join() === 'compose,search' && c.steps.join() === 'compose,widen:middle' && c.scope.level === 'middle' && c.beginnings.length === 3
    && c.widened && c.widened.from === 'narrow' && c.widened.kept === 'wider' && /narrow scope connected only 1/.test(c.scope.why)
    && order1 === 'terms,compose,compose'
    && order2 === 'terms,compose,compose,search,compose' && c2.steps.join() === 'compose,widen:middle,search,rebuild' && c2.beginnings.length === 3 && /after widening/.test(c2.research),
    { steps: [c.steps, c2.steps, c3.steps], order1, order2, scope: c.scope, widened: c.widened });

  // ── length: rewritten once more, then kept and flagged ────────────────────────────────────────────────────────
  const LONG = 'In a long and very detailed sequence of events that unfolded over many months California lawmakers and activists repeatedly proposed a tax on the largest fortunes in the state.';
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', milestones: [{ id: D1, line: LINE(0), ties_to: TIES.tax }, { id: D2, line: LONG, ties_to: TIES.tax }, { id: D3, line: LINE(2), ties_to: TIES.ballot }], starts: D3 })
    : k === 'repair' ? {} : k === 'reline' ? { [D2]: LONG } : {});
  c = await L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []);
  const kept = c.beginnings.find(b => b.object_id === D2);
  const relines = CALLS.filter(x => x.kind === 'reline');
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', milestones: [{ id: D1, line: LINE(0), ties_to: TIES.tax }, { id: D2, line: LONG, ties_to: TIES.tax }, { id: D3, line: LINE(2), ties_to: TIES.ballot }], starts: D3 })
    : k === 'repair' ? {} : k === 'reline' ? { [D2]: LINE(1) } : {});
  const cf = await L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []);
  check('length: a milestone whose sentence breaks a rule is kept and flagged',
    c.beginnings.length === 3 && kept && /words/.test(kept.flag) && relines.length === 1 && relines[0].prompt.includes(D2) && !relines[0].prompt.includes(D1 + ' | broke')
    && (c.problems.milestones || []).length === 1 && !c.thin && !cf.beginnings.find(b => b.object_id === D2).flag && cf.beginnings.find(b => b.object_id === D2).line === LINE(1),
    { begs: c.beginnings, relines: relines.length, problems: c.problems });

  // ── event: no line opens with an outlet or a document ─────────────────────────────────────────────────────────
  const shipped = [].concat(...FX.stories.map(s => s.page.beginnings.map(b => Object.assign({ key: s.key, o: LIB[b.object_id] }, b))));
  const flaggedLines = shipped.filter(b => L.bsxOpensWithSource(b.line, b.o)).map(b => b.line.slice(0, 40));
  const want = ['Bloomberg reported that Nvidia', 'ABC News reported in 2020', "On November 13, 2024, Biden's archived", 'CBS News reported on Biden'];
  // the November 13 line opens with its date; "Biden's archived account reported" is the subject
  const NV = shipped.find(b => /^Bloomberg reported/.test(b.line));
  const OLDNEWS = addDoc('custom-old-bloomberg-report-2025-def456', 2025, 'Nvidia sales to China', { url: 'https://www.bloomberg.com/news/articles/2025-04-01/nvidia', source_kind: 'news', author: 'Bloomberg', kind: 'found' });
  const OPENER = 'Bloomberg reported that federal officials told Nvidia that California billionaires would face a new levy on their wealth that year.';
  const FIXED = 'Federal officials told Nvidia that California billionaires would face a new levy on their accumulated wealth that year.';
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', milestones: [{ id: D1, line: LINE(0), ties_to: TIES.tax }, { id: OLDNEWS, line: OPENER, ties_to: TIES.tax }, { id: D3, line: LINE(2), ties_to: TIES.ballot }], starts: D3 })
    : k === 'repair' ? { milestones: [{ id: OLDNEWS, line: FIXED }] } : {});
  const ce1 = await L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []);
  const repairAsked = CALLS.filter(x => x.kind === 'repair').some(x => /opens with an outlet/.test(x.prompt));
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', milestones: [{ id: D1, line: LINE(0), ties_to: TIES.tax }, { id: OLDNEWS, line: OPENER, ties_to: TIES.tax }, { id: D3, line: LINE(2), ties_to: TIES.ballot }], starts: D3 })
    : k === 'repair' ? {} : k === 'reline' ? {} : {});
  const ce2 = await L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []);
  check('event: a milestone that opens with an outlet is rewritten or flagged',
    want.every(w => flaggedLines.some(f => w.startsWith(f.slice(0, 25)) || f.startsWith(w.slice(0, 25)))) && flaggedLines.length === want.length
    && repairAsked && ce1.beginnings.find(b => b.object_id === OLDNEWS).line === FIXED && !ce1.beginnings.find(b => b.object_id === OLDNEWS).flag
    && /opens with an outlet/.test(ce2.beginnings.find(b => b.object_id === OLDNEWS).flag) && ce2.beginnings.length === 3,
    { flaggedLines, repairAsked, ce2: ce2.beginnings.map(b => [b.object_id, b.flag]) });
  check('event: an official who reports to Congress is an event, not a report ("Carter reported to Congress")', !L.bsxOpensWithSource(shipped.find(b => /^Carter reported to Congress/.test(b.line)).line, {}), null);

  // ── recent: within 45 days of the story is "We are here" ──────────────────────────────────────────────────────
  const NVID = NV.object_id, NV_TIE = 'board independent committee';
  const D_OLD = addDoc('2026-09-01-commerce-department-chip-rule', 2026, 'Commerce Department rule on chip exports to China');
  const D_NEW = addDoc('2026-10-20-commerce-department-entity-list', 2026, 'Commerce Department adds Megaspeed to the Entity List');
  const NVL = n => ['The Commerce Department told Nvidia that sales of its most advanced chips to buyers in China would need a license.',
    'The Commerce Department set new limits on exports of advanced chips to buyers in China and to companies tied to them.',
    'The Commerce Department added a Singapore company to a trade blacklist over its purchases of advanced American chips.',
    'Nvidia\'s board said it would look into a spying case after its chief executive admitted an affair with an alleged Chinese asset.'][n];
  const nvTies = ['export rules chips China', 'barred from China chips', 'chips Washington barred', NV_TIE];
  const filId = Object.keys(LIB).find(i => i.startsWith('custom-nvidia-corp-form-8-k'));
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', milestones: [filId, D_OLD, D_NEW, NVID].map((id, i) => ({ id, line: NVL(i), ties_to: nvTies[i] })), starts: D_OLD, later: [] }) : {});
  c = await L.bsxCompose(story(NVDA), null, null, lib(), edits(), [], []);
  const tiesOk = nvTies.every(t => L.catTiesOk(t, [story(NVDA).headline, story(NVDA).lede, story(NVDA).truths].join(' ')));
  check('recent: a milestone within 45 days of the story is not a milestone',
    tiesOk && L.bsxDocDate(LIB[NVID]) === '2026-11-08' && !c.beginnings.some(b => [NVID, D_NEW].includes(b.object_id)) && c.beginnings.some(b => b.object_id === D_OLD)
    && c.left_out.filter(x => /45 days/.test(x.reason)).length === 2 && c.case.some(o => o.object_id === NVID) && L.bsxTooRecent({ year: '2027' }, DATE) && !L.bsxTooRecent({ year: '2026' }, DATE),
    { tiesOk, begs: c.beginnings.map(b => b.object_id), left: c.left_out.map(x => x.reason), case: c.case.map(o => o.object_id) });

  // ── note: filler is left blank ────────────────────────────────────────────────────────────────────────────────
  const notes = [].concat(...FX.stories.map(s => s.page.case.filter(o => o.about).map(o => Object.assign({ key: s.key }, o))));
  const filler = notes.filter(o => L.bsxNoteFiller(o.about, o)).map(o => o.object_id);
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', milestones: ok3([D1, D2, CU]).map((m, i) => i === 2 ? { id: CU, line: 'The Supreme Court ruled that the government may not limit independent political spending by corporations and unions.', ties_to: 'opposition group raised' } : m), starts: D2,
    about: { [CU]: notes.find(o => o.object_id === CU).about, [D1]: 'The amendment let Congress tax incomes without dividing the tax among the states by population. It ended a ruling that had struck down an earlier income tax, and opened the way to a graduated federal tax.' } }) : {});
  c = await L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []);
  const cuDoc = c.case.find(o => o.object_id === CU), d1Doc = c.case.find(o => o.object_id === D1);
  check('note: a note with no fact beyond title and date is left blank',
    filler.length === 2 && filler.includes(CU) && filler.includes(TCJA) && cuDoc.about === '' && /beyond the title/.test(cuDoc.about_flag) && d1Doc.about && !d1Doc.about_flag,
    { filler, cu: cuDoc, d1: d1Doc && d1Doc.about_flag, checked: notes.length });

  // ── review ────────────────────────────────────────────────────────────────────────────────────────────────────
  const built = await (async () => { reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', milestones: ok3([D1, D2, D3]), starts: D3 }) : {}); return L.bsxCompose(story(TAX), null, null, lib(), edits(), [], []); })();
  const R = async reply => { reset(k => k === 'review' ? reply : {}); return L.bsxSelfReview(JSON.parse(JSON.stringify(built)), story(TAX)); };
  const r1 = await R({ verdict: 'ready', concerns: [] });
  const r2 = await R({ verdict: 'needs you', concerns: [{ component: 'scope', concern: 'Nothing on California.', fix: 'Rebuild on the narrow scope.', blocking: true },
    { component: 'starts', concern: 'Starts too early.', fix: 'Start at the 2020 bill.' }, { component: 'chart', concern: 'not a component here', fix: 'x' },
    { component: 'documents', concern: 'One note is thin.', fix: 'Write a note.' }, { component: 'here', concern: 'Fine.', fix: 'None.' }] });
  const r3 = await R('I could not read the page.');
  check('review: a page comes back ready or needs you',
    r1.verdict === 'ready' && !r1.concerns.length && r2.verdict === 'needs you' && r2.concerns.length === 3 && r2.concerns.every(x => x.component !== 'chart' && x.fix)
    && r2.concerns[0].blocking === true && r2.concerns[1].blocking === false && r3.verdict === 'not reviewed'
    && CALLS.every(x => x.model === 'claude-sonnet-5-5'),
    { r1, r2, r3 });

  // ── held ──────────────────────────────────────────────────────────────────────────────────────────────────────
  const clone = x => JSON.parse(JSON.stringify(x));
  const thinPage = clone(built); thinPage.beginnings = thinPage.beginnings.slice(0, 2);
  const h1 = L.bsxHold(clone(thinPage), {}), h2 = L.bsxHold(clone(thinPage), { ship_anyway: true });
  const blockP = clone(built); blockP.review = r2; const h3 = L.bsxHold(clone(blockP), {});
  const softP = clone(built); softP.review = { verdict: 'needs you', concerns: [r2.concerns[1]] }; const h4 = L.bsxHold(clone(softP), {});
  const h5 = L.bsxHold(Object.assign(clone(built), { starts: null }), {}), h6 = L.bsxHold(Object.assign(clone(built), { here: '' }), {});
  const fx = FX.stories.map(s => [s.key, !!L.bsxHold(clone(s.page), s.bs_edits).held]);
  const heldFx = fx.filter(x => x[1]).map(x => x[0]).sort();
  // publish: backstory_draft.py apply skips a held page (run for real, on a temporary draft)
  const os = require('os'), tmp = fs.mkdtempSync(path.join(os.tmpdir(), 't0117-'));
  const wj = (n, d) => fs.writeFileSync(path.join(tmp, n), JSON.stringify(d));
  const shipP = Object.assign(clone(built), { v: 2 }), heldP = Object.assign(clone(h1), { v: 2 }), anyP = Object.assign(clone(h2), { v: 2 });
  wj('draft.json', { stories: [['a', shipP], ['b', heldP], ['c', anyP]].map(([k, cc], i) => ({ story_id: k, bs_hash: String(i), composed: cc, bs_edits_applied: k === 'c' ? { ship_anyway: true } : {} })),
    ship: { todays_pairings: ['a', 'b', 'c'].map(k => ({ story_id: k, row: 'gaza' })) } });
  wj('lineup.json', { stories: ['a', 'b', 'c'].map((k, i) => ({ key: k, bs_hash: String(i) })) });
  wj('bs.json', { rows: [{ id: 'gaza' }], todays_pairings: [] });
  const py = require('child_process').spawnSync('python3', [path.join(root, 'editorial/backstory_draft.py'), 'apply', '--draft', path.join(tmp, 'draft.json'), '--lineup', path.join(tmp, 'lineup.json'),
    '--backstory', path.join(tmp, 'bs.json'), '--provisional', path.join(tmp, 'p.json')], { encoding: 'utf8' });
  const pyErr = py.status ? String(py.stderr) : '', pyStderr = String(py.stderr || '');
  let pyShipped = []; try { pyShipped = JSON.parse(fs.readFileSync(path.join(tmp, 'bs.json'), 'utf8')).todays_pairings.map(p => p.story_id); } catch (e) {}
  check('held: a weak page does not ship until the editor ships it anyway',
    h1.held === true && /fewer than three/.test(h1.weak.join()) && !h2.held && h2.shipped_anyway === true && h3.held === true && /blocking concern on scope/.test(h3.weak.join())
    && !h4.held && h5.held && /It starts in/.test(h5.weak.join()) && h6.held && /We are here/.test(h6.weak.join()) && !L.bsxHold(clone(built), {}).held
    && !pyErr && pyShipped.join() === 'a,c' && /b: held: weak, not released/.test(pyStderr),
    { h1: h1.weak, h2: [h2.held, h2.shipped_anyway], h3: h3.weak, h4: h4.held, pyErr, pyShipped, pyStderr });
  check('held: on the 2026-11-10 pages, the two shipped with two milestones would have been held, and no other', heldFx.join() === [NVDA, CARTER].sort().join(), fx);
  check('held: a failed self-review holds nothing by itself', !L.bsxHold(Object.assign(clone(built), { review: r3 }), {}).held, null);

  // ── editor: what the editor directed is never held or flagged ─────────────────────────────────────────────────
  const ed1 = clone(thinPage); ed1.beginnings.forEach(b => { b.by = 'editor'; });
  const e1 = L.bsxHold(ed1, { pins: [{ id: ed1.beginnings[0].object_id }] });
  const ed2 = clone(built); ed2.review = { verdict: 'needs you', concerns: [{ component: 'contest', concern: 'Off the story.', fix: 'Rewrite.', blocking: true }] };
  ed2.contest = 'The editor\'s own contest — with a dash and far too short.'; L.bsxApplyText(ed2, { contest: ed2.contest });
  const e2 = L.bsxHold(ed2, { text: { contest: ed2.contest } });
  const ed3 = clone(built); L.bsxApplyText(ed3, { ['m:' + D1]: OPENER }); L.bsxEnforce(ed3, story(TAX), LIB, []); L.bsxHold(ed3, { text: { ['m:' + D1]: OPENER } });
  const ed4 = L.bsxHold(Object.assign(clone(built), { contest: '' }), { removed: ['contest'] });
  // an editor's pick with no tie to the story is placed; the editor's direction (a revise of the milestones) skips the tie and recent tests
  reset((k) => k === 'terms' ? SCOPES : k === 'compose' ? page({ scope: 'middle', milestones: ok3([D1, D2, D3]).concat([{ id: POPULIST, line: 'The People\'s Party adopted a platform demanding a graduated income tax at its first national convention that summer.' }]), starts: D3 }) : {});
  const e5 = await L.bsxCompose(story(TAX), null, null, lib(), { pool: ALL(), keep: [POPULIST] }, [], []);
  const notes6 = [], e6 = L.bsxShape({ milestones: [{ id: NVID, line: NVL(3) }] }, ALL(), LIB, {}, notes6, story(NVDA), null, { directed: true });
  check('editor: what the editor directed is never held or flagged',
    !e1.held && !e1.weak.length && !e2.held && !e2.review.concerns.length && e2.review.verdict === 'ready' && !(e2.problems || {}).contest
    && !ed3.beginnings.find(b => b.object_id === D1).flag && !(ed3.problems || {}).milestones && !ed4.held
    && e5.beginnings.some(b => b.object_id === POPULIST) && e6.beginnings.length === 1 && !e6.left_out.length && L.bsxDirected({ modify: { documents: 'x' } }).has('starts'),
    { e1: e1.weak, e2: [e2.held, e2.review, e2.problems], ed3: ed3.beginnings.map(b => [b.by, b.flag]), ed4: ed4.weak, e5: e5.beginnings.map(b => b.object_id), e6: e6.left_out });


  // ── change: a story revised after its page was built (T-0122, step two) ───────────────────────────────────────
  // The real case: the Hegseth page said the House must act within two legislative days; the revised story says the
  // House voted 211 to 204 to refer the articles.
  const H = byKey[HEG], HP = H.page, rev = Object.assign({ date: DATE }, H.revised);
  const NEWHERE = 'House Republicans voted 211 to 204 to refer the impeachment articles against Pete Hegseth to committee, ending the push for now.';
  reset(k => k === 'change' ? { holds: true, here: NEWHERE, why: 'The vote ends this round; the history of impeaching officers still holds.' } : {});
  let ch = await L.bsxRefreshHere(clone(HP), rev, H.bs_edits);
  const chCall = CALLS.filter(x => x.kind === 'change');
  const same = k => JSON.stringify(ch.page[k]) === JSON.stringify(HP[k]);
  check('change: a revised story refreshes We are here and keeps the milestones',
    /211 to 204/.test(rev.truths + rev.headline) && /two legislative days/.test(HP.here) && ch.current === true && ch.page.here === NEWHERE && ch.page.change.here_updated
    && ch.page.change.was === HP.here && ['title', 'contest', 'stakes', 'beginnings', 'case', 'starts'].every(same) && CALLS.length === 1 && chCall[0].model === 'claude-haiku-5-5'
    && chCall[0].prompt.includes('211 to 204') && chCall[0].prompt.includes('two legislative days') && ch.page.change.usage.input_tokens > 0,
    { here: ch.page.here, current: ch.current, change: ch.page.change, calls: CALLS.map(x => x.kind) });
  // a new line that breaks a rule (a number the story does not hold) is not taken, and the page is not called current
  reset(k => k === 'change' ? { holds: true, here: 'House Republicans voted 300 to 100 to refer the impeachment articles against Pete Hegseth to a committee.' } : {});
  const chBad = await L.bsxRefreshHere(clone(HP), rev, H.bs_edits);
  check('change: a new We are here that breaks a rule is not taken, and the page still reads as behind', chBad.page.here === HP.here && !chBad.current && /number/.test(chBad.page.change.kept_because), chBad.page.change);
  // the editor typed We are here: never rewritten, flagged, the history still checked
  reset(k => k === 'change' ? { holds: true, here: NEWHERE, why: 'holds' } : {});
  const typed = 'The House voted on the articles; the editor wrote this line.';
  const pe = Object.assign(clone(HP), { here: typed });
  const chE = await L.bsxRefreshHere(pe, rev, Object.assign({}, H.bs_edits, { text: { here: typed } }));
  const chM = await L.bsxRefreshHere(clone(HP), rev, { modify: { here: 'say where the vote stands' } });
  check('change: a We are here the editor typed is never rewritten',
    chE.page.here === typed && chE.page.change.editor_here === true && !chE.page.change.here_updated && chE.current === true
    && chM.page.here === HP.here && chM.page.change.editor_here === true, { e: chE.page.change, m: chM.page.change });
  // the history moved: no compose, no rebuild, the page says so and stays as built; a failed call keeps the page
  reset(k => k === 'change' ? { holds: false, here: NEWHERE, why: 'The story is now about the 2028 race, not the impeachment.' } : k === 'compose' ? page({}) : {});
  const chX = await L.bsxRefreshHere(clone(HP), rev, H.bs_edits);
  const kindsX = CALLS.map(x => x.kind);
  reset(k => k === 'change' ? new Error('overloaded') : {});
  const chF = await L.bsxRefreshHere(clone(HP), rev, H.bs_edits);
  const runSrc = html.slice(html.indexOf('async function bsxRun('), html.indexOf('// Remove (no model)'));
  check('change: a changed story never forces a rebuild',
    chX.current === false && chX.page.change.moved === true && chX.page.here === HP.here && ['title', 'beginnings', 'case'].every(k => JSON.stringify(chX.page[k]) === JSON.stringify(HP[k]))
    && kindsX.join() === 'change' && chF.current === false && /overloaded/.test(chF.page.change.error) && chF.page.here === HP.here
    && !/Rebuild from scratch\.'\); return false/.test(html) && /const changed=bsxStoryChanged\(d0, s\);\s*if \(changed && !opts\.build\)/.test(runSrc)
    && /We are here\\u201d updated to follow the story/.test(html) && /bsc2-rebuild-changed/.test(html),
    { x: chX.page.change, kindsX, f: chF.page.change });
  console.log('\n' + fails + ' failed'); process.exit(fails ? 1 : 0);
})().catch(e => { console.error('FAIL: the tests crashed: ' + (e.stack || e)); process.exit(1); });
