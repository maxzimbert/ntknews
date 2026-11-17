#!/usr/bin/env node
// T-0123: each story's Backstory starts as a proposal the editor settles in conversation with Opus, then is built
// once. Runs the real Backstory block of ntk-pulse/pulse.html (between BSX:BEGIN and BSX:END) in node, with the
// category helpers from its CATS block, against a stand-in GitHub (the branch's draft and research ledger, kept in
// memory) and stand-in model replies. No network, no API spend.   node scripts/test_pulse_conversation.js
//
// What this cannot cover: the real models' judgment, the real web search, and the browser screen beyond the HTML
// that bspHtml returns. Those need the editor's key in staging Pulse.
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'ntk-pulse/pulse.html'), 'utf8');
const block = (name) => { const m = html.match(new RegExp('/\\* ' + name + ':BEGIN \\*/([\\s\\S]*?)/\\* ' + name + ':END \\*/')); if (!m) { console.error('FAIL: ' + name + ' block not found'); process.exit(1); } return m[1]; };
// a top-level function's source, by name (as T-0114's check reads them)
const fnSrc = (name) => { const m = html.match(new RegExp('(?:^|\\n)((?:async )?function ' + name + '\\([\\s\\S]*?\\n\\})\\n')); if (!m) throw new Error('no function ' + name); return m[1]; };
const CATS = new Function(block('CATS') + '; return {catTextProblems, catWords, catSentences, catNumbersOk, catTiesOk, catSourceKind, bsxPublisher, NTK_PUBLISHERS, verifyFoundObject, verifyMilestone, CAT_RELATIONS, CAT_DENY};')();
const BSX = block('BSX');
const EXPORTS = 'bsxRun, bsxGet, bsxPut, bspShape, bspDiff, bspBuild, bspUnbuilt, bspHtml, bspPropose, bsxRefreshHere, bsxEnforce, bspDollars, BSX_OPUS, BSX_SONNET, BSX_HAIKU';

let fails = 0;
const check = (name, ok, detail) => { console.log((ok ? 'ok   ' : 'FAIL ') + name + (ok ? '' : '  ' + String(JSON.stringify(detail)).slice(0, 600))); if (!ok) fails++; };

// ─── The library and the stories ────────────────────────────────────────────────────────────────────────────────
const doc = (id, year, title, author, about) => ({ id, pool: 'matrix', title, author, year: String(year), url: 'https://www.govinfo.gov/' + id, link_status: 'live', row: '', subgenre: '', lenses: [], about });
const POOL = { objects: [
  doc('m-bribery', 1962, 'Bribery, Graft, and Conflicts of Interest Act', 'U.S. Congress', 'A federal law that made it a crime for officials to take bribes or act on matters in which they had a financial interest.'),
  doc('m-ethics', 1978, 'Ethics in Government Act of 1978', 'U.S. Congress', 'A federal law passed after Watergate that required senior officials and members of Congress to disclose their finances each year.'),
  doc('m-reform', 1989, 'Ethics Reform Act of 1989', 'U.S. Congress', 'A federal law that limited outside income and gifts for members of Congress and senior officials.'),
  doc('m-stock', 2012, 'Stop Trading on Congressional Knowledge Act of 2012', 'U.S. Congress', 'A federal law that barred members of Congress from using nonpublic information for private profit and required them to report stock trades.'),
  doc('m-fourteen', 1918, 'Fourteen Points', 'Woodrow Wilson', 'An address to Congress setting out war aims and a league of nations.'),
  doc('m-fedact', 1913, 'Federal Reserve Act', 'U.S. Congress', 'A federal law that created the Federal Reserve System as the central bank of the United States.'),
  doc('m-accord', 1951, 'Treasury and Federal Reserve Accord', 'Treasury Department and Federal Reserve', 'An agreement that freed the Federal Reserve to set interest rates apart from Treasury borrowing needs.'),
  doc('m-humphrey', 1978, 'Full Employment and Balanced Growth Act', 'U.S. Congress', 'A federal law that gave the Federal Reserve goals for both employment and stable prices.'),
] };
const POOL_BEFORE = JSON.stringify(POOL);
// the editor's Are.na library: twelve items the story's terms match, and one only the editor's words reach
const ARENA_FILE = { objects: Array.from({ length: 12 }, (_, k) => ({ id: 'arena-stock-' + k, title: 'The STOCK Act at ten, part ' + (k + 1), source: 'apnews.com', url: 'https://apnews.com/stock-' + k, year: '2022', channels: ['Congress'] }))
  .concat([{ id: 'arena-spouses', title: 'Spouses and their trading accounts in the House', source: 'politico.com', url: 'https://www.politico.com/spouses', year: '2021', channels: ['Congress'] }]) };
const S1 = { key: 's1', title: 'Senate votes to ban stock trading by members of Congress', headline: 'Senate votes to ban stock trading by members of Congress',
  lede: 'Members of Congress and their spouses could no longer trade individual stocks.',
  truth: 'The Senate voted on Tuesday to ban members of Congress and their spouses from trading individual stocks. Supporters said the STOCK Act of 2012 had failed to stop insider trading by lawmakers. The ban now goes to the House.' };
const S2 = { key: 's2', title: 'The Federal Reserve holds interest rates steady', headline: 'The Federal Reserve holds interest rates steady',
  lede: 'The central bank kept its benchmark rate unchanged.', truth: 'The Federal Reserve kept its benchmark interest rate unchanged on Wednesday. Officials said inflation was cooling but jobs remained strong. The central bank has a dual mandate for employment and stable prices.' };

// ─── Stand-in model replies, by what each prompt asks ───────────────────────────────────────────────────────────
const LONG = 'Congress passed a sweeping law after the Watergate scandal that required senior officials and every member of Congress to disclose their personal finances in detailed public reports filed every single year with ethics offices.';
const FOUND_URL = 'https://www.govinfo.gov/content/pkg/CRPT-117hrpt/stock-trading-report.pdf';
const WIKI_URL = 'https://en.wikipedia.org/wiki/STOCK_Act';
const EDITOR_SAYS = 'Reach back to the 1962 bribery law,  and the contest should be: Who polices lawmakers\u2019 trades?';
const EDITOR_SAYS_2 = 'Find the House report on stock trading by members of Congress, and look in my Are.na for spouses trading accounts.';
const replies = {
  terms: () => ({ terms: ['STOCK Act', 'congressional ethics', 'Ethics in Government Act', 'conflicts of interest', 'Federal Reserve'] }),
  proposeS1: () => ({ reply: '', category: 'Congressional ethics', contest: 'Whether members of Congress can be trusted to police their own conflicts of interest, or whether outside rules must bind them.',
    starts: '2012', beginnings: [
      { year: '1978', id: 'm-ethics', ties_to: 'members of Congress', asked: false },
      { year: '1989', id: 'm-reform', ties_to: 'members of Congress', asked: false },
      { year: '2012', id: 'm-stock', ties_to: 'STOCK Act of 2012', asked: false },
      { year: '1918', id: 'm-fourteen', ties_to: 'League of Nations covenant', asked: false }],
    later: [], lacks: 'No House or Senate ethics committee rulings on stock trades.' }),
  proposeS2: () => ({ reply: '', category: 'The Federal Reserve', contest: 'Whether the central bank should answer first for stable prices, or share that duty equally with keeping people at work.',
    starts: '1978', beginnings: [
      { year: '1913', id: 'm-fedact', ties_to: 'Federal Reserve', asked: false },
      { year: '1951', id: 'm-accord', ties_to: 'Federal Reserve interest rate', asked: false },
      { year: '1978', id: 'm-humphrey', ties_to: 'dual mandate for employment', asked: false }], later: [], lacks: '' }),
  turn1: () => ({ reply: 'Added the 1962 law, which first made an official\u2019s financial interest a crime, and used your contest.', category: 'Congressional ethics',
    contest: 'Who polices lawmakers\u2019 trades?', starts: '2012', beginnings: [
      { year: '1962', id: 'm-bribery', ties_to: 'conflicts of interest', asked: true },
      { year: '1978', id: 'm-ethics', ties_to: 'members of Congress', asked: false },
      { year: '1989', id: 'm-reform', ties_to: 'members of Congress', asked: false },
      { year: '2012', id: 'm-stock', ties_to: 'STOCK Act of 2012', asked: false }],
    later: [], lacks: 'No House or Senate ethics committee rulings on stock trades.' }),
  turn2: () => ({ reply: 'Found the House report and added it; the Wikipedia page and a link I could not confirm are left out.', category: 'Congressional ethics',
    contest: 'Who polices lawmakers\u2019 trades?', starts: '2012', beginnings: [
      { year: '1962', id: 'm-bribery', ties_to: 'conflicts of interest', asked: true },
      { year: '1978', id: 'm-ethics', ties_to: 'members of Congress', asked: false },
      { year: '1989', id: 'm-reform', ties_to: 'members of Congress', asked: false },
      { year: '2012', id: 'm-stock', ties_to: 'STOCK Act of 2012', asked: false }],
    later: [
      { found: { title: 'Stock Trading by Members of Congress: Report of the Committee on House Administration', author: 'Committee on House Administration', year: '2022', source: 'U.S. Government Publishing Office', source_url: FOUND_URL, source_kind: 'document', evidence_quote: 'The Committee examined trading by members of Congress.' } },
      { found: { title: 'STOCK Act', author: 'Wikipedia', year: '2012', source_url: WIKI_URL, source_kind: 'document' } },
      { found: { title: 'A report I remember', author: 'Congress', year: '2021', source_url: 'https://www.congress.gov/not-returned-by-the-search', source_kind: 'document' } }],
    lacks: '' }),
  buildS1: (p) => { const ids = [...p.matchAll(/- (\d{4}) \| (\S+) \|/g)].map(m => m[2]); const lines = {};
    ids.forEach(id => { lines[id] = id === 'm-ethics' ? LONG : ({ 'm-bribery': 'Congress made it a crime for federal officials to act on matters in which they held a financial interest.', 'm-reform': 'Congress limited the outside income and gifts that its members and senior officials could accept.', 'm-stock': 'Congress barred its members from trading on nonpublic information and required them to report their stock trades.' })[id] || 'Congress acted on the conflicts of interest of its own members in a new federal law.'; });
    return { title: 'Congress and its own trades', contest: 'Whether the build may rewrite the agreed contest, which it must not do under any circumstances at all.',
      stakes: 'Lawmakers write the rules that govern their own investments, and voters see little of how those rules are kept. Whether the ban becomes law decides who watches the watchers in Congress.',
      lines, starts_line: 'Congress passed the law that first required its members to report their stock trades.', here: 'The Senate has voted to ban stock trading by members of Congress and their spouses, and the House takes it up next.',
      about: { [Object.keys(lines).find(i => i.startsWith('web-')) || 'none']: 'A House committee report published in 2022. It examined stock trading by members of Congress.' } }; },
  repair: () => ({ contest: 'Whether a repair may change what the editor agreed, which it never may in any case at all.', milestones: [{ id: 'm-ethics', line: LONG }] }),
  reline: () => ({ 'm-ethics': LONG }),
  refresh: () => ({ holds: true, here: 'The House now takes up the Senate ban on stock trading by members of Congress and their spouses.', why: 'The same argument; the bill moved to the House.' }),
};
function route(body) {
  const p = body.messages[0].content, m = body.model;
  if (/Name that history as 8 to 14 short search terms/.test(p)) return replies.terms();
  if (/THE EDITOR NOW SAYS: Reach back to the 1962/.test(p)) return replies.turn1();
  if (/THE EDITOR NOW SAYS: Find the House report/.test(p)) return replies.turn2();
  if (/Propose this story's Backstory/.test(p)) return /stock trading/.test(p) ? replies.proposeS1() : replies.proposeS2();
  if (/from a proposal the editor has agreed/.test(p)) return replies.buildS1(p);
  if (/These parts of a Backstory page broke their rules/.test(p)) return replies.repair();
  if (/Rewrite each milestone line below/.test(p)) return replies.reline();
  if (/The story has since been revised/.test(p)) return replies.refresh();
  throw new Error('no stand-in reply for a ' + m + ' prompt beginning: ' + p.slice(0, 120));
}

// ─── A stand-in world: the branch on GitHub, the Anthropic API, Pulse's globals ─────────────────────────────────
function world(gh) {
  const calls = [], ghWrites = [];
  const b64 = (o) => Buffer.from(JSON.stringify(o), 'utf8').toString('base64');
  const resp = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body, text: async () => (typeof body === 'string' ? body : JSON.stringify(body)) });
  async function fetch(url, init) {
    init = init || {};
    if (url.startsWith('https://api.anthropic.com/')) {
      const body = JSON.parse(init.body); calls.push(body);
      if (body.thinking && body.thinking.type === 'disabled' && body.model === 'claude-opus-5-5') return resp(200, { error: { message: 'thinking disabled is not supported on this model' } });
      const j = route(body), search = (body.tools || []).some(t => t.name === 'web_search');
      // the second turn's search runs long: the API pauses it once (pause_turn) after the first search, and Pulse must carry on
      if (search && /Find the House report/.test(body.messages[0].content) && body.messages.length === 1)
        return resp(200, { content: [{ type: 'web_search_tool_result', content: [{ url: FOUND_URL }] }], stop_reason: 'pause_turn', usage: { input_tokens: 9000, output_tokens: 100, server_tool_use: { web_search_requests: 1 } } });
      const paused = body.messages.length > 1;      // the continuation: only what this round searched
      const content = (search ? [{ type: 'web_search_tool_result', content: paused ? [{ url: WIKI_URL }] : [{ url: FOUND_URL }, { url: WIKI_URL }] }] : []).concat([{ type: 'text', text: JSON.stringify(j) }]);
      return resp(200, { content, stop_reason: 'end_turn', usage: { input_tokens: 9000, output_tokens: 700, server_tool_use: search ? { web_search_requests: 1 } : undefined } });
    }
    const gm = url.match(/^https:\/\/api\.github\.com\/repos\/[^/]+\/[^/]+\/contents\/([^?]+)/);
    if (gm) {
      const p = decodeURIComponent(gm[1]);
      if ((init.method || 'GET') === 'PUT') { const b = JSON.parse(init.body); gh[p] = { data: JSON.parse(Buffer.from(b.content, 'base64').toString('utf8')), sha: String(Date.now() + Math.random()) }; ghWrites.push(p); return resp(200, {}); }
      if (!gh[p]) return resp(404, {});
      if (/raw/.test(((init.headers || {}).Accept) || '')) return resp(200, typeof gh[p].data === 'string' ? gh[p].data : JSON.stringify(gh[p].data));
      return resp(200, { content: b64(gh[p].data), sha: gh[p].sha });
    }
    if (url.startsWith('../editorial/prompts/')) return resp(200, fs.readFileSync(path.join(root, url.slice(3).split('?')[0]), 'utf8'));
    if (url.startsWith('data/provisional-rows.json')) return resp(200, { rows: [] });
    if (url.startsWith('data/arena-library.json')) return resp(200, ARENA_FILE);
    throw new Error('unexpected fetch ' + url);
  }
  const LINEUP = [Object.assign({ packages: { truths: S1.truth }, backstoryRow: '', bsEdits: {} }, S1), Object.assign({ packages: { truths: S2.truth }, backstoryRow: '', bsEdits: {} }, S2)];
  const rows = [{ id: 'p-congressional-ethics', title: 'Congressional ethics' }];
  const env = {
    ...CATS, fetch, console, setTimeout, clearTimeout, LINEUP, POOL, BSR_PUBLISHED: { rows: [] }, ARENA: null, PUBCATS: [], CAT_STYLE_RULES: '',
    SETTINGS: { antKey: 'stand-in', ghToken: 'stand-in' }, location: {}, pulseBranch: () => 'staging', GH_REPO: 'maxzimbert/ntknews', GH_DRAFT_OUT: 'ntk-pulse/data/backstory-draft.json',
    TAB: 'backstory', BSR_DRAFT: null, BSR_DRAFT_STATE: '', BSR_PREV_OPEN: {}, BSX_LED: null,
    window: { addEventListener() {} }, document: { createElement: () => { let h = ''; return { set innerHTML(v) { h = String(v || ''); }, get textContent() { return h.replace(/<[^>]+>/g, ' '); } }; } },
    render() {}, saveLineup() {}, bsrRefreshHashes: async () => {}, bsxFindChart: async () => '', bsxRowIndicator: () => null, catRecord: () => null,
    bsRejected: () => [], bsrRowNames: () => rows, bsrRowTitle: (id) => (rows.find(r => r.id === id) || { title: id }).title,
    bsrRowResolve: (name) => { const id = 'p-' + String(name).toLowerCase().replace(/[^a-z0-9]+/g, '-'); if (!rows.some(r => r.id === id)) rows.push({ id, title: name }); return id; },
    bsEdits: (s) => { s.bsEdits = s.bsEdits || {}; return s.bsEdits; }, bsxResearchItems: () => [], bsrRunning: () => false,
    esc: (t) => String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'), rel: () => 'a moment',
    buildStoryPayload: () => LINEUP.map(L => ({ key: L.key, headline: L.headline, lede: L.lede, truth: L.truth, backstory_row: L.backstoryRow, ...(Object.keys(L.bsEdits || {}).length ? { bs_edits: L.bsEdits } : {}) })),
    bsWithHashes: async (ss) => { ss.forEach(s => { s.bs_story_hash = JSON.stringify([s.headline, s.lede, s.truth]); s.bs_text_hash = JSON.stringify([s.headline, s.lede, s.truth, s.backstory_row]); s.bs_hash = JSON.stringify([s.bs_text_hash, s.bs_edits || null]); }); return ss; },
  };
  env.bsxStoryChanged = new Function(fnSrc('bsxStoryChanged') + '; return bsxStoryChanged;')();
  const L = new Function('env', 'with (env) {' + BSX + '\n; return {' + EXPORTS + '}; }')(env);
  return { L, env, calls, ghWrites, draft: () => (gh['ntk-pulse/data/backstory-draft.json'] || {}).data, entry: (k) => (((gh['ntk-pulse/data/backstory-draft.json'] || {}).data || {}).stories || []).find(d => d.story_id === k) || {} };
}
const ledger0 = { subjects: {}, finds: [], series: [], rejected: [], vetoed: [], candidates: [] };
const GH = { 'editorial/research-ledger.json': { data: JSON.parse(JSON.stringify(ledger0)), sha: '1' } };

(async () => {
  let w = world(GH);
  // ── proposal ──────────────────────────────────────────────────────────────────────────────────────────────────
  const gen = fnSrc('generateStory');
  await w.L.bsxRun(['s1', 's2'], { propose: true });
  const e1 = w.entry('s1'), e2 = w.entry('s2');
  check('proposal: Generate Jefferson leaves every story with a proposal and no page',
    gen.includes('bsxRun([story.key], {propose:true})') && !gen.includes('{build:true}') && !!e1.proposal && !!e2.proposal && !e1.composed && !e2.composed
    && !w.calls.some(c => c.model === w.L.BSX_SONNET), { gen: gen.includes('{propose:true}'), e1: Object.keys(e1), e2: Object.keys(e2), models: w.calls.map(c => c.model), state: w.env.BSR_DRAFT_STATE });
  const p1 = e1.proposal || {};
  check('proposal: holds a category, a contest, It starts in, beginnings and objects',
    p1.category === 'Congressional ethics' && /^Whether /.test(p1.contest) && p1.starts === '2012' && p1.beginnings.length === 3
    && p1.beginnings.every(b => /^\d{4}$/.test(b.year) && p1.docs[b.object_id] && p1.docs[b.object_id].url) && p1.objects.join() === p1.beginnings.map(b => b.object_id).join()
    && typeof p1.lacks === 'string' && p1.left_out.some(x => /Fourteen Points/.test(x.title) && /does not say/.test(x.reason)), p1);
  const opusCalls = w.calls.filter(c => /Propose this story's Backstory/.test(c.messages[0].content));
  check('proposal: written by the conversation model, Opus',
    opusCalls.length === 2 && opusCalls.every(c => c.model === 'claude-opus-5-5' && !c.thinking && c.output_config && c.messages[0].content.includes('You are the historian behind NTK News')) && p1.model === 'claude-opus-5-5'
    && (e1.bsp_cost || {})['claude-opus-5-5'] && (e1.bsp_cost || {})['claude-haiku-5-5'], { models: opusCalls.map(c => c.model), cost: e1.bsp_cost });

  // ── publish ─────────────────────────────────────────────────────────────────────────────────────────────────
  const pub = fnSrc('publishToDigest'), at = pub.indexOf('bspUnbuilt('), firstConfirm = pub.indexOf('confirm(');
  const stop = pub.slice(at, pub.indexOf('\n', pub.indexOf('if (ub.length)', at)));
  const stories = [{ key: 's1', headline: S1.headline }, { key: 's2', headline: S2.headline }];
  const ub0 = w.L.bspUnbuilt(stories, w.draft());
  check('publish: an unbuilt proposal stops the publish, with no way through',
    ub0.length === 2 && ub0.every(x => /proposal is not built/.test(x)) && w.L.bspUnbuilt(stories, null).length === 2
    && at > 0 && at < firstConfirm && pub.indexOf('todayPreflight(') < at && /if \(ub\.length\)\{ alert\([^\n]*\); return; \}/.test(stop) && !/confirm\(/.test(stop), { ub0, at, firstConfirm, stop });

  // ── chat ────────────────────────────────────────────────────────────────────────────────────────────────────
  await w.L.bsxRun(['s1'], { turn: { s1: { message: EDITOR_SAYS } } });
  let e = w.entry('s1'), last = (e.chat || []).slice(-1)[0] || {};
  check('chat: a turn changes the proposal and says what it changed',
    e.proposal.beginnings.some(b => b.object_id === 'm-bribery' && b.year === '1962' && b.asked) && e.proposal.contest === 'Who polices lawmakers\u2019 trades?'
    && last.role === 'historian' && /1962/.test(last.text) && last.changed.includes('added beginning 1962: Bribery, Graft, and Conflicts of Interest Act') && last.changed.includes('contest rewritten')
    && !e.composed, { chat: e.chat, prop: e.proposal && e.proposal.beginnings });
  const ledgerBefore = JSON.stringify(GH['editorial/research-ledger.json'].data);
  const callsBefore = w.calls.length;
  await w.L.bsxRun(['s1'], { turn: { s1: { message: EDITOR_SAYS_2 } } });
  e = w.entry('s1'); last = e.chat.slice(-1)[0];
  const found = Object.values(e.proposal.docs).find(d => d.url === FOUND_URL);
  const turnCalls = w.calls.slice(callsBefore).filter(c => c.model === 'claude-opus-5-5'), turnCall = turnCalls[0];
  check('chat: the web search has no cap, and a turn the API pauses carries on without losing what it found',
    (turnCall.tools || []).every(t => t.max_uses === undefined) && turnCalls.length === 2 && turnCalls[1].messages.length === 2 && turnCalls[1].messages[1].role === 'assistant'
    && w.entry('s1').chat.slice(-1)[0].searched === 2, { tools: turnCall.tools, rounds: turnCalls.map(c => c.messages.length) });
  check('chat: a document found on the web joins the proposal and not the Object Matrix',
    !!found && found.kind === 'web' && e.proposal.later.includes(found.id) && !Object.values(e.proposal.docs).some(d => d.url === WIKI_URL)
    && last.dropped.length === 2 && last.dropped.some(x => /wikipedia/.test(x.reason)) && last.dropped.some(x => /not one the search returned/.test(x.reason))
    && (turnCall.tools || []).some(t => t.type === 'web_search_20260209')
    && JSON.stringify(GH['editorial/research-ledger.json'].data) === ledgerBefore && JSON.stringify(POOL) === POOL_BEFORE && !JSON.stringify(e.proposal).includes('approved_by'),
    { found, last, ledgerChanged: JSON.stringify(GH['editorial/research-ledger.json'].data) !== ledgerBefore });
  // a reload: a fresh Pulse reads the branch's draft again
  w = world(GH);
  const reread = (await w.L.bsxGet('ntk-pulse/data/backstory-draft.json')).data, re1 = reread.stories.find(d => d.story_id === 's1');
  const page = w.L.bspHtml({ key: 's1' }, re1);
  const pp = opusCalls[0].messages[0].content, tp = turnCall.messages[0].content, nA = (t) => (t.match(/- arena-/g) || []).length;
  check("chat: the editor's Are.na library is loaded before any proposal, and a turn searches it with the editor's words",
    nA(pp) > 0 && nA(pp) <= 10 && tp.includes('- arena-spouses |') && nA(tp) > 10, { proposal: nA(pp), turn: nA(tp), spouses: tp.includes('arena-spouses') });
  check('chat: the conversation survives a reload',
    re1.chat.length === 4 && re1.chat[0].text === EDITOR_SAYS && re1.chat[2].text === EDITOR_SAYS_2 && page.includes('Who polices lawmakers\u2019 trades?')
    && page.includes(w.env.esc(EDITOR_SAYS)) && page.includes('Stock Trading by Members of Congress') && page.includes('bsp-send') && page.includes('bsp-build'), { chat: re1.chat });

  // ── build ───────────────────────────────────────────────────────────────────────────────────────────────────
  const prop = re1.proposal, TYPED = 'Who trades on the Hill';
  w.env.LINEUP[0].bsEdits = { text: { title: TYPED } };
  await w.L.bsxRun(['s1'], { build: true });
  e = w.entry('s1'); const c = e.composed || {};
  check('build: Build writes the page from the settled proposal and keeps what was agreed',
    c.v === 2 && c.built_from === 'proposal' && c.row === prop.category && c.contest === prop.contest && c.starts && c.starts.year === prop.starts
    && c.beginnings.map(b => b.object_id).join() === prop.beginnings.map(b => b.object_id).join() && c.case.map(o => o.object_id).sort().join() === prop.objects.slice().sort().join()
    && c.starts.object_id === 'm-stock' && !!e.proposal.built_at && w.L.bspUnbuilt(stories, w.draft()).length === 1 && w.L.bspUnbuilt(stories, w.draft())[0].includes('Federal Reserve'),
    { row: c.row, contest: c.contest, starts: c.starts, begs: (c.beginnings || []).map(b => b.object_id), kase: (c.case || []).map(o => o.object_id), prop });
  const longOne = (c.beginnings || []).find(b => b.object_id === 'm-ethics');
  check('build: a beginning is never dropped for its sentence length',
    !!longOne && longOne.line === LONG && /words/.test(longOne.flag || '') && w.calls.some(x => /Rewrite each milestone line below/.test(x.messages[0].content)), longOne);
  const story1 = { headline: S1.headline, lede: S1.lede, truths: S1.truth };
  const ties = { v: 1, category: 'Congressional ethics', contest: 'Whether X, or Y.', starts: '2012', lacks: '', later: [], docs: {},
    beginnings: [{ year: '1918', object_id: 'm-fourteen', ties_to: 'League of Nations covenant' }, { year: '1962', object_id: 'm-bribery', ties_to: 'treaty ports abroad', asked: true },
      { year: '1978', object_id: 'm-ethics', ties_to: 'members of Congress' }, { year: '2012', object_id: 'm-stock', ties_to: 'STOCK Act of 2012' }] };
  ties.objects = ties.beginnings.map(b => b.object_id);
  const lib = Object.fromEntries(POOL.objects.map(o => [o.id, Object.assign({ categories: new Set(), why: '', kind: 'matrix' }, o)]));
  const tb = await w.L.bspBuild(story1, ties, lib, {});
  check('build: a beginning that names nothing in the story is not placed',
    !tb.beginnings.some(b => b.object_id === 'm-fourteen') && !tb.case.some(o => o.object_id === 'm-fourteen') && tb.left_out.some(x => x.object_id === 'm-fourteen')
    && tb.beginnings.some(b => b.object_id === 'm-bribery') && tb.beginnings.some(b => b.object_id === 'm-stock'), { begs: tb.beginnings.map(b => b.object_id), left: tb.left_out });

  // ── change ──────────────────────────────────────────────────────────────────────────────────────────────────
  const before = JSON.parse(JSON.stringify(e.composed));
  w.env.LINEUP[0].truth = S1.truth.replace('The ban now goes to the House.', 'The ban now goes to the House, where leaders have not scheduled a vote.');
  await w.L.bsxRun(['s1'], { refresh: true });
  e = w.entry('s1'); const ch = e.composed;
  check('change: a revised story refreshes We are here and keeps the beginnings',
    ch.here !== before.here && /House now takes up/.test(ch.here) && ch.change && ch.change.here_updated && ch.beginnings.map(b => b.object_id + b.line).join() === before.beginnings.map(b => b.object_id + b.line).join()
    && ch.contest === before.contest && e.bs_story_hash === JSON.stringify([S1.headline, S1.lede, w.env.LINEUP[0].truth]) && w.calls.some(x => x.model === w.L.BSX_HAIKU && /has since been revised/.test(x.messages[0].content)),
    { here: ch.here, change: ch.change });

  // ── editor ──────────────────────────────────────────────────────────────────────────────────────────────────
  check('editor: what the editor typed is never rewritten',
    before.title === TYPED && ch.title === TYPED && e.chat[0].text === EDITOR_SAYS && e.chat[0].role === 'editor' && prop.contest === 'Who polices lawmakers\u2019 trades?' && ch.contest === prop.contest,
    { title: [before.title, ch.title], said: e.chat[0] });

  // ── T-0117's machinery stays gone; the cost is measured ─────────────────────────────────────────────────────
  check("t-0117: no holds, verdicts, Ship anyway or three scopes in Pulse", !/Ship anyway|held: weak|shipped_anyway|scope_picks|bsxSelfReview|bsxHold\(/.test(html), null);
  const dollars = w.L.bspDollars(e.bsp_cost);
  check('cost: every call on a story is recorded by model, and priced', dollars > 0 && Object.keys(e.bsp_cost).sort().join() === ['claude-haiku-5-5', 'claude-opus-5-5', 'claude-sonnet-5-5'].join(), e.bsp_cost);

  console.log('\n' + fails + ' failed');
  process.exit(fails ? 1 : 0);
})().catch(err => { console.error('FAIL: the run broke: ' + (err && err.stack || err)); process.exit(1); });
