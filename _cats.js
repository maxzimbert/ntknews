/* ─── Backstory categories (T-0079) ───────────────────────────────────────
   A category is composed here: a model drafts its contest, stakes and lines, objects are
   picked by rule from the pool (ntk-pulse/data/backstory-pool.json, exported from the
   matrix and the candidates workbook), the editor reads it, sends revisions, edits by hand,
   and approves. Approved categories ride in the Lineup publish as `backstory_categories`;
   CI (editorial/categories.py) re-validates them and drops what fails, so nothing in this
   file is trusted by the site. State is shared by every tab: Lineup's row dropdown and the
   publish payload read the same CATS.

   The logic between CATS:BEGIN and CATS:END is pure and is tested in node against the same
   fixtures as the Python validator (scripts/test_pulse_categories.js). Keep the two in step. */
/* CATS:BEGIN */
const CAT_BANNED = ['this document','this reflects','underscores','highlights','serves as','a reminder that','pivotal','landmark','groundbreaking','seminal'];
function catWords(t){ const s=(t||'').trim(); return s ? s.split(/\s+/).length : 0; }
function catSentences(t){ return ((t||'').match(/[.!?]["')\]]*(?:\s|$)/g)||[]).length; }
function catEscRe(w){ return w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); }
function catTextProblems(label, text, lo, hi, opt){
  opt = opt||{}; const p=[]; const t=(text||'').trim();
  if (!t) return [label+' is empty'];
  const n=catWords(t);
  if (n<lo||n>hi) p.push(label+' is '+n+' words, wants '+lo+' to '+hi);
  if (/[—–]| -- /.test(t)) p.push(label+' has a dash');
  const low=t.toLowerCase(); if (CAT_BANNED.some(b=>low.includes(b))) p.push(label+' has a banned phrase');
  if (opt.sentences!=null && catSentences(t)!==opt.sentences) p.push(label+' is not '+opt.sentences+' sentence'+(opt.sentences!==1?'s':''));
  if (opt.starts && !t.startsWith(opt.starts)) p.push(label+' does not start with "'+opt.starts+'"');
  return p;
}
function lensSupported(lens, spec, text){
  const c=(spec||{})[lens]||{};
  return (c.story_terms||[]).some(w=>new RegExp('\\b'+catEscRe(w)+'\\b','i').test(text)) ||
         (c.story_terms_cs||[]).some(w=>new RegExp('\\b'+catEscRe(w)+'\\b').test(text));
}
// The Beginnings rule: the most recent object (the turn closest to today) plus the rest
// spread evenly across time, no repeated author where a neighbour will do.
function selectBeginnings(objs, k){
  const a = objs.slice().sort((x,y)=> x.sort<y.sort ? -1 : x.sort>y.sort ? 1 : 0);
  if (a.length<=k) return a;
  const last=a[a.length-1], rest=a.slice(0,-1), need=k-1, out=[], used=new Set();
  for (let i=0;i<need;i++){
    const idx=Math.round(i*(rest.length-1)/Math.max(need-1,1));
    let j=idx;
    while (j<rest.length && (used.has(j) || out.some(o=>o.author && o.author===rest[j].author))) j++;
    if (j>=rest.length){ j=idx; while (j>=0 && used.has(j)) j--; }
    if (j<0) break;
    used.add(j); out.push(rest[j]);
  }
  return out.concat([last]).sort((x,y)=> x.sort<y.sort ? -1 : x.sort>y.sort ? 1 : 0);
}
// Mirror of editorial/categories.py validate(). Returns {clean, problems}.
function validateCat(cat, poolBy, spec, storyTexts, originYear){
  const problems=[]; const c=Object.assign({}, cat); const by=Object.assign({}, c.by||{});
  if (!(c.id||'').trim() || !(c.title||'').trim()) return {clean:null, problems:['missing id or title']};
  c.title=c.title.trim().slice(0,60);
  [['contest',12,30,{sentences:1,starts:'Whether'}],['stakes',25,55,{sentences:2}]].forEach(([f,lo,hi,opt])=>{
    const t=(c[f]||'').trim(); let p;
    if (by[f]==='editor') p = (t && catWords(t)<=120) ? [] : [f+' is empty or over 120 words'];
    else p = catTextProblems(f,t,lo,hi,opt);
    if (p.length){ problems.push(...p); c[f]=''; } else c[f]=t;
  });
  const text=(storyTexts||[]).join(' '); const keep=[];
  (c.lenses||[]).forEach(l=>{
    if (!spec[l]) problems.push('unknown lens '+l);
    else if (by.lenses!=='editor' && (storyTexts||[]).length && !lensSupported(l,spec,text)) problems.push('lens '+l+' has no support in the story filed under '+c.title);
    else keep.push(l);
  });
  c.lenses=keep;
  const approved=new Set(c.approved_objects||[]); const objs=[];
  (c.objects||[]).forEach(o=>{
    const e=poolBy[o.object_id];
    if (!e){ problems.push('object '+o.object_id+' is not in the pool'); return; }
    if (e.link_status==='dead' || !e.url){ problems.push('object '+e.title+' has no live link'); return; }
    if (e.pool==='candidate' && !(e.approved || approved.has(e.id))){ problems.push('candidate '+e.title+' is not approved'); return; }
    let about=(o.about||e.about||'').trim();
    if (about && o.by!=='editor'){ const ap=catTextProblems('about',about,1,70); if (ap.length){ ap.forEach(x=>problems.push(e.title+': '+x)); about=''; } }
    objs.push({object_id:e.id,title:e.title,author:e.author,year:e.year,source:e.source,source_url:e.url,about:about,pool:e.pool,lenses:e.lenses,by:o.by||'model'});
  });
  objs.sort((a,b)=> a.year<b.year?-1:a.year>b.year?1:(a.title<b.title?-1:1));
  c.objects=objs;
  const begs=[], seen=new Set();
  (c.beginnings||[]).forEach(b=>{
    const o=objs.find(x=>x.object_id===b.object_id);
    if (!o || seen.has(b.object_id)){ problems.push('Beginning '+b.object_id+' is not among the category’s objects'); return; }
    if (originYear && String(o.year)>=String(originYear)){ problems.push('Beginning '+o.title+' is dated '+o.year+', not before the origin'); return; }
    if (by.lenses!=='editor' && b.by!=='editor' && keep.length && !o.lenses.some(l=>keep.includes(l))){ problems.push('Beginning '+o.title+' belongs to none of the category’s lenses'); return; }
    const line=(b.line||'').trim();
    const lp = b.by==='editor' ? (line?[]:['line is empty']) : catTextProblems('line',line,12,25,{sentences:1});
    if (lp.length){ lp.forEach(x=>problems.push('Beginning '+o.title+': '+x)); return; }
    seen.add(b.object_id); begs.push({object_id:b.object_id,year:o.year,line:line,by:b.by||'model'});
  });
  begs.sort((a,b)=> a.year<b.year?-1:a.year>b.year?1:0);
  c.beginnings=begs;
  const ind=c.indicator;
  if (ind && !(ind.verified===true && ind.source && ind.as_of)){ problems.push('indicator is not verified with a source and a date'); c.indicator=null; }
  c.by=by;
  return {clean:c, problems:problems};
}
/* CATS:END */

const CAT_MAXTOK = 2400;
let CATS = load(LS.cats, {});          // id -> record. Drafts and approved-not-yet-published. Shared by every tab.
let POOL = null, POOL_BY = {};         // ntk-pulse/data/backstory-pool.json
let PUBCATS = [];                      // categories already published (ntk-pulse/data/provisional-rows.json)
let CAT_SEL = null;                    // the category open in the Backstory tab
let CAT_BUSY = {}, CAT_MSG = {};
function saveCats(){ localStorage.setItem(LS.cats, JSON.stringify(CATS)); }
function catSlug(name){ return 'p-' + String(name).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,40); }
function catPlain(h){ return String(h||'').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim(); }
function catStoryText(s){ const p=s.packages||{}; return SECS.map(x=>catPlain(p[x])).join(' '); }
function catStories(id){ return LINEUP.filter(s=>s.backstoryRow===id); }
function catRecord(id){ return CATS[id] || PUBCATS.find(r=>r.id===id) || null; }
function catListAll(){
  const out=Object.values(CATS).map(r=>({rec:r, where:'local'}));
  PUBCATS.forEach(r=>{ if (!CATS[r.id]) out.push({rec:r, where:'published'}); });
  return out;
}
function catEnsureLocal(id){            // editing a published category copies it into CATS first
  if (CATS[id]) return CATS[id];
  const p=PUBCATS.find(r=>r.id===id); if (!p) return null;
  CATS[id]=JSON.parse(JSON.stringify({id:p.id,title:p.title,status:'approved',contest:p.contest||'',stakes:p.stakes||'',lenses:p.lenses||[],
    indicator:p.indicator||null,objects:(p.objects||[]).map(o=>({object_id:o.object_id,about:o.about,by:o.by||'model'})),
    beginnings:(p.beginnings||[]).map(b=>({object_id:b.object_id,line:b.line,by:b.by||'model'})),
    by:p.by||{},approved_objects:p.approved_objects||[],revisions:p.revisions||[],created:p.created}));
  saveCats(); return CATS[id];
}
function newCategory(name, storyKeys){
  const id=catSlug(name); if (!id || id==='p-') return null;
  if (!CATS[id] && !PUBCATS.find(r=>r.id===id)){
    CATS[id]={id:id,title:name.trim().slice(0,60),status:'draft',contest:'',stakes:'',lenses:[],indicator:null,objects:[],beginnings:[],
      by:{},approved_objects:[],revisions:[],created:new Date().toISOString().slice(0,10)};
    saveCats();
  }
  (storyKeys||[]).forEach(k=>{ const s=LINEUP.find(x=>x.key===k); if (s) s.backstoryRow=id; });
  saveLineup();
  return id;
}
async function loadCatData(){
  try {
    const [p,s]=await Promise.all([
      fetch('data/backstory-pool.json?t='+Date.now()).then(r=>r.ok?r.json():null).catch(()=>null),
      fetch('data/provisional-rows.json?t='+Date.now()).then(r=>r.ok?r.json():null).catch(()=>null)]);
    if (p){ POOL=p; POOL_BY=Object.fromEntries(p.objects.map(o=>[o.id,o])); }
    PUBCATS=((s&&s.rows)||[]).filter(r=>r.status==='provisional');
  } catch(e){}
  render();
}
function catJson(text){
  const t=String(text).replace(/```json|```/g,'').trim();
  const a=t.indexOf('{'), b=t.lastIndexOf('}');
  if (a<0||b<a) throw new Error('the model did not return JSON');
  return JSON.parse(t.slice(a,b+1));
}
function catPoolFor(lenses){
  return (POOL?POOL.objects:[]).filter(o=>o.url && o.link_status!=='dead' && o.lenses.some(l=>lenses.includes(l)));
}
// pick Beginnings by rule: one lens takes up to six, two or more take up to three each
function catPick(lenses){
  const k = lenses.length===1 ? 6 : 3, seen=new Set(), out=[];
  lenses.forEach(l=>{
    selectBeginnings(catPoolFor([l]), k).forEach(o=>{ if (!seen.has(o.id)){ seen.add(o.id); out.push(o); } });
  });
  return out.sort((a,b)=> a.sort<b.sort?-1:1);
}
const CAT_STYLE_RULES = `STYLE (all text): plain words, Grade 8 to 10. No em dashes. Never use: this document, this reflects, underscores, highlights, serves as, a reminder that, pivotal, landmark, groundbreaking, seminal. Take no side. Use only facts in the material you are given; no numbers that do not appear in it.`;
async function composeCat(id){
  const c=CATS[id]; if (!c) return;
  if (!POOL){ CAT_MSG[id]='The object pool has not loaded.'; render(); return; }
  CAT_BUSY[id]='Composing…'; CAT_MSG[id]=''; render();
  try {
    const stories=catStories(id), texts=stories.map(catStoryText), joined=texts.join(' ');
    const supported=Object.keys(POOL.lenses).filter(l=>lensSupported(l,POOL.lenses,joined));
    const p1 = `You write the opening of a new category page for NTK's Backstory, a news product that shows readers how today's story sits inside a long American argument.

CATEGORY NAME: ${c.title}
THE STORIES FILED UNDER IT:
${stories.map((s,i)=>'['+(i+1)+'] '+s.title+'\n'+texts[i].slice(0,3500)).join('\n\n') || '(none yet)'}

SUBJECT LENSES that this text supports (histories a page may draw its Beginnings from): ${supported.join(', ') || '(none)'}

Write JSON only: {"contest":"...","stakes":"...","lenses":["..."],"note":"one sentence for the editor"}
1. contest: ONE sentence, "Whether X, or Y", two positions a reasonable person holds. 12 to 30 words.
2. stakes: TWO short sentences, 25 to 55 words in all, framed as the open questions the argument turns on (whether, when, by whom, who benefits). Do not write about "risks" in the abstract or "who pays". Write about the category as a whole, not about one story.
3. lenses: choose from the supported lenses above only the ones the stories are mainly about. Do not add a lens because it is a related topic. An empty list is fine.
${CAT_STYLE_RULES}`;
    const r1=catJson(await ai(p1,900));
    if (c.by.contest!=='editor' && r1.contest){ c.contest=String(r1.contest).trim(); c.by.contest='model'; }
    if (c.by.stakes!=='editor' && r1.stakes){ c.stakes=String(r1.stakes).trim(); c.by.stakes='model'; }
    if (c.by.lenses!=='editor'){ c.lenses=(r1.lenses||[]).filter(l=>supported.includes(l)); c.by.lenses='model'; }
    // objects by rule, texts by the model
    const picked=catPick(c.lenses);
    const keepEd=(c.objects||[]).filter(o=>o.by==='editor'), edIds=new Set(keepEd.map(o=>o.object_id));
    c.objects=picked.map(o=>({object_id:o.id,about:o.about||'',by:'model'})).filter(o=>!edIds.has(o.object_id)).concat(keepEd);
    c.beginnings=picked.map(o=>({object_id:o.id,line:o.line||'',by:'model'}));
    await writeObjectText(c, picked.filter(o=>!(o.line&&o.about)));
    c.revisions=(c.revisions||[]).concat([{at:new Date().toISOString(),request:'(first draft)',summary:r1.note||''}]);
    CAT_MSG[id]=r1.note||'';
  } catch(e){ CAT_MSG[id]='Compose failed: '+e.message; }
  delete CAT_BUSY[id]; saveCats(); render();
}
// one line (a Beginning) and one About for each object that has none yet
async function writeObjectText(c, objs){
  if (!objs.length) return;
  const p=`You write short text about primary-source documents for NTK's Backstory, for readers who have opted out of the news.

CATEGORY: ${c.title}
For each document below write:
  "line": ONE sentence, 12 to 25 words, saying what was done, starting with the actor or the event (the year is shown beside it). Past tense. Name the act, not its importance.
  "about": TWO to FOUR sentences, at most 70 words: what it is, who made it and when, what it says or did.
Use ONLY the fields given plus plain facts you are certain of. Use no numbers, quotations or dates that are not in the fields. If you cannot write something without guessing, use null for that item.
${CAT_STYLE_RULES}

DOCUMENTS:
${objs.map(o=>'- id: '+o.id+' | year: '+o.year+' | title: '+o.title+' | author: '+o.author+' | source: '+o.source+(o.why?' | why it is here: '+o.why:'')).join('\n')}

JSON only: {"<id>":{"line":"...","about":"..."}, ...}`;
  const r=catJson(await ai(p,CAT_MAXTOK));
  objs.forEach(o=>{
    const t=r[o.id]; if (!t) return;
    const ob=c.objects.find(x=>x.object_id===o.id), bg=c.beginnings.find(x=>x.object_id===o.id);
    if (ob && !ob.about && t.about) ob.about=String(t.about).trim();
    if (bg && !bg.line && t.line) bg.line=String(t.line).trim();
  });
}
async function reviseCat(id, request){
  const c=CATS[id]; if (!c || !request.trim()) return;
  CAT_BUSY[id]='Revising…'; CAT_MSG[id]=''; render();
  try {
    const avail=catPoolFor(c.lenses).filter(o=>!c.objects.some(x=>x.object_id===o.id));
    const cur=c.beginnings.map(b=>{ const o=POOL_BY[b.object_id]||{}; return '- '+b.object_id+' | '+o.year+' | '+o.title+' | line: '+b.line; }).join('\n');
    const p=`You are revising a Backstory category page for NTK at the editor's request.

CATEGORY: ${c.title}
CONTEST: ${c.contest}
STAKES: ${c.stakes}
LENSES: ${c.lenses.join(', ')||'(none)'}
BEGINNINGS NOW:
${cur||'(none)'}
OTHER DOCUMENTS AVAILABLE TO ADD (id | year | title):
${avail.slice(0,60).map(o=>o.id+' | '+o.year+' | '+o.title).join('\n')||'(none)'}

THE EDITOR'S REQUEST: ${request}

Change only what the request asks for. Return JSON with only the keys that change:
{"contest":"...","stakes":"...","lines":{"<id>":"..."},"abouts":{"<id>":"..."},"add":["<id from the available list>"],"drop":["<id>"],"note":"one sentence saying what you changed"}
contest: "Whether X, or Y", 12 to 30 words. stakes: two short sentences, 25 to 55 words. A line is one sentence of 12 to 25 words. An about is two to four sentences, at most 70 words.
${CAT_STYLE_RULES}`;
    const r=catJson(await ai(p,CAT_MAXTOK));
    if (r.contest){ c.contest=String(r.contest).trim(); c.by.contest='model'; }
    if (r.stakes){ c.stakes=String(r.stakes).trim(); c.by.stakes='model'; }
    (r.drop||[]).forEach(oid=>{ c.objects=c.objects.filter(o=>o.object_id!==oid); c.beginnings=c.beginnings.filter(b=>b.object_id!==oid); });
    (r.add||[]).forEach(oid=>{
      const o=POOL_BY[oid]; if (!o || c.objects.some(x=>x.object_id===oid)) return;
      c.objects.push({object_id:oid,about:o.about||'',by:'model'}); c.beginnings.push({object_id:oid,line:o.line||'',by:'model'});
    });
    Object.entries(r.lines||{}).forEach(([oid,t])=>{ const b=c.beginnings.find(x=>x.object_id===oid); if (b){ b.line=String(t).trim(); b.by='model'; } });
    Object.entries(r.abouts||{}).forEach(([oid,t])=>{ const o=c.objects.find(x=>x.object_id===oid); if (o){ o.about=String(t).trim(); o.by='model'; } });
    const need=c.beginnings.filter(b=>!b.line).map(b=>POOL_BY[b.object_id]).filter(Boolean);
    if (need.length) await writeObjectText(c, need);
    c.revisions=(c.revisions||[]).concat([{at:new Date().toISOString(),request:request,summary:r.note||''}]);
    CAT_MSG[id]=r.note||'Revised.';
  } catch(e){ CAT_MSG[id]='Revision failed: '+e.message; }
  delete CAT_BUSY[id]; saveCats(); render();
}
function catCheck(c){
  if (!POOL) return {clean:c, problems:[]};
  const texts=catStories(c.id).map(catStoryText);
  return validateCat(c, POOL_BY, POOL.lenses, texts, null);
}
// what the Lineup publish carries: every approved category, as the editor left it
function catsForPublish(){
  return Object.values(CATS).filter(c=>c.status==='approved').map(c=>JSON.parse(JSON.stringify(c)));
}
function catPreviewHtml(c){
  const chk=catCheck(c).clean||c; const rows=(c.beginnings||[]).map(b=>{
    const o=POOL_BY[b.object_id]||{}; return `<div style="display:flex;gap:10px;margin:6px 0"><b style="min-width:42px">${esc(o.year||'')}</b><span>${esc(b.line)}</span></div>`;
  }).join('');
  return `<div style="border:1px solid var(--rule);padding:12px 14px;max-width:560px;background:#faf8f3">
    <div style="font:600 24px Georgia,serif;margin-bottom:6px">${esc(c.title)}</div>
    <div style="font:italic 15px Georgia,serif;margin-bottom:10px">${esc(c.contest)}</div>
    <div style="font:15px Georgia,serif;margin-bottom:12px">${esc(c.stakes)}</div>
    ${c.indicator?`<div style="font-size:12px;margin-bottom:10px"><b>${esc(c.indicator.label)}</b> ${esc(c.indicator.then_value)} (${esc(c.indicator.then_year)}) to ${esc(c.indicator.now_value)} · ${esc(c.indicator.source)}, ${esc(c.indicator.as_of)}</div>`:''}
    <div style="font:700 11px sans-serif;letter-spacing:.08em;margin:8px 0">BEGINNINGS</div>${rows||'<i style="font-size:12px;color:var(--dim)">none yet</i>'}
    <div style="display:flex;gap:10px;margin:6px 0;color:var(--stale)"><b style="min-width:42px">…</b><span style="font:700 10px sans-serif;letter-spacing:.1em">WE ARE HERE</span> <span style="font-size:12px">(the year and line are set when the digest publishes)</span></div>
  </div>`;
}
function catEditorHtml(c){
  const busy=CAT_BUSY[c.id], stories=catStories(c.id), texts=stories.map(catStoryText), joined=texts.join(' ');
  const chk=catCheck(c), probs=chk.problems;
  const lensAll=POOL?Object.keys(POOL.lenses):[];
  const supported=lensAll.filter(l=>lensSupported(l,POOL.lenses,joined));
  const shown=Array.from(new Set(supported.concat(c.lenses||[])));
  const lensHtml=shown.map(l=>`<label style="margin-right:10px;white-space:nowrap"><input type="checkbox" class="cat-lens" data-lens="${esc(l)}" ${c.lenses.includes(l)?'checked':''}> ${esc(l)}${supported.includes(l)?'':' <span style="color:var(--stale)" title="the filed story never mentions this subject">⚠</span>'}</label>`).join('')
    + `<details style="display:inline-block;margin-left:6px"><summary style="cursor:pointer;font-size:11px;color:var(--dim)">other lenses</summary>${lensAll.filter(l=>!shown.includes(l)).map(l=>`<label style="margin-right:10px;white-space:nowrap"><input type="checkbox" class="cat-lens" data-lens="${esc(l)}"> ${esc(l)}</label>`).join('')}</details>`;
  const objRows=(c.objects||[]).map(o=>{
    const e=POOL_BY[o.object_id]||{}; const bg=(c.beginnings||[]).find(b=>b.object_id===o.object_id);
    const cand=e.pool==='candidate', ok=!cand || e.approved || (c.approved_objects||[]).includes(o.object_id);
    return `<div class="story" style="padding:8px 10px;margin:6px 0" data-oid="${esc(o.object_id)}">
      <div style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">
        <label title="show as a Beginning"><input type="checkbox" class="cat-isbeg" ${bg?'checked':''}> Beginning</label>
        <b>${esc(e.year||'')}</b> <span>${esc(e.title||o.object_id)}</span>
        <a href="${esc(e.url||'#')}" target="_blank" rel="noopener" style="font-size:11px">open source ↗</a>
        <span class="chip">${esc(e.link_status||'')}</span>
        ${cand?`<label style="font-size:11px;${ok?'':'color:var(--warn)'}"><input type="checkbox" class="cat-approve" ${ok?'checked':''} ${e.approved?'disabled':''}> ${ok?'approved':'candidate, needs your approval'}</label>`:'<span class="chip">matrix</span>'}
        <button class="mini cat-rm" style="margin-left:auto">remove</button>
      </div>
      ${bg?`<textarea class="cat-line" rows="2" style="width:100%;margin-top:5px" placeholder="Beginning line, one sentence">${esc(bg.line)}</textarea>`:''}
      <textarea class="cat-about" rows="2" style="width:100%;margin-top:4px" placeholder="About this: two to four sentences">${esc(o.about||'')}</textarea>
    </div>`;
  }).join('');
  const addable=catPoolFor(c.lenses).filter(o=>!(c.objects||[]).some(x=>x.object_id===o.id));
  const ind=c.indicator||{};
  const f=(k,w)=>`<input class="cat-ind" data-k="${k}" value="${esc(ind[k]||'')}" placeholder="${k}" style="width:${w||120}px">`;
  return `<div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
      <input id="cat-title" value="${esc(c.title)}" style="font-size:16px;font-weight:600;width:260px">
      <span class="chip" style="${c.status==='approved'?'background:var(--certified);color:#fff':''}">${esc(c.status)}</span>
      ${busy?`<span style="color:var(--warn)">${esc(busy)}</span>`:''}
      <span style="flex:1"></span>
      <button class="mini go" id="cat-compose" ${busy?'disabled':''}>${c.contest||c.beginnings.length?'Recompose':'Compose'}</button>
      <button class="mini" id="cat-save">Save draft</button>
      <button class="mini ${c.status==='approved'?'':'primary'}" id="cat-approve">${c.status==='approved'?'Back to draft':'Approve for publish'}</button>
      <button class="mini" id="cat-del">${PUBCATS.some(r=>r.id===c.id)?'(published)':'Delete'}</button>
    </div>
    ${CAT_MSG[c.id]?`<div style="font-size:12px;margin-bottom:8px;color:${/failed/.test(CAT_MSG[c.id])?'var(--stale)':'var(--dim)'}">${esc(CAT_MSG[c.id])}</div>`:''}
    <div style="font-size:11px;color:var(--dim);margin-bottom:6px">Filed under it: ${stories.length?stories.map(s=>esc(s.title)).join(' · '):'no story yet. In Lineup, pick this category on a story.'}</div>
    <div style="margin:8px 0"><b style="font-size:11px">LENSES</b> <span style="font-size:11px;color:var(--dim)">histories to draw Beginnings from. A ⚠ means the story never mentions the subject, and publish will drop it unless you chose it.</span><div style="margin-top:4px">${lensHtml||'<i>none</i>'}</div></div>
    <b style="font-size:11px">CONTEST</b><textarea id="cat-contest" rows="2" style="width:100%">${esc(c.contest)}</textarea>
    <b style="font-size:11px">STAKES</b><textarea id="cat-stakes" rows="3" style="width:100%">${esc(c.stakes)}</textarea>
    <details style="margin:6px 0"><summary style="cursor:pointer;font-size:11px"><b>TREND LINE</b> ${c.indicator?'('+esc(c.indicator.label||'set')+')':'(none: needs a sourced, verified indicator)'}</summary>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${f('label',220)}${f('then_value',70)}${f('then_year',60)}${f('now_value',70)}${f('direction',80)}${f('source',160)}${f('source_url',200)}${f('as_of',100)}
      <label style="font-size:11px"><input type="checkbox" class="cat-ind-ok" ${ind.verified?'checked':''}> I checked it against the source</label></div></details>
    <div style="margin:10px 0 4px"><b style="font-size:11px">BEGINNINGS AND OBJECTS</b> <span style="font-size:11px;color:var(--dim)">${(c.beginnings||[]).length} Beginnings, ${(c.objects||[]).length} objects. The reader sees them in date order.</span></div>
    ${objRows||'<i style="font-size:12px;color:var(--dim)">none yet. Compose, or add from the pool below.</i>'}
    ${addable.length?`<div style="margin-top:6px"><select id="cat-add"><option value="">add from the pool for these lenses (${addable.length})…</option>${addable.map(o=>`<option value="${esc(o.id)}">${esc(o.year)} · ${esc(o.title.slice(0,70))} (${o.pool})</option>`).join('')}</select></div>`:''}
    ${probs.length?`<div style="margin-top:8px;font-size:11px;color:var(--stale)"><b>Will be dropped at publish:</b><br>${probs.map(esc).join('<br>')}</div>`:''}
    <div style="margin:12px 0 4px"><b style="font-size:11px">SEND A REVISION</b></div>
    <textarea id="cat-rev" rows="2" style="width:100%" placeholder="Tell me what to change: 'make the stakes plainer', 'drop the 1974 entry', 'add the Section 230 object'…"></textarea>
    <button class="mini go" id="cat-revise" ${busy?'disabled':''}>Send revision</button>
    ${(c.revisions||[]).length?`<div style="font-size:11px;color:var(--dim);margin-top:6px">${(c.revisions||[]).slice(-5).map(r=>esc((r.at||'').slice(5,16).replace('T',' '))+' — '+esc(r.request)+(r.summary?' → '+esc(r.summary):'')).join('<br>')}</div>`:''}
    <div style="margin:12px 0 4px"><b style="font-size:11px">PREVIEW</b></div>${catPreviewHtml(c)}
  </div>`;
}
function renderBackstory(root){
  const list=catListAll();
  if (CAT_SEL && !catRecord(CAT_SEL)) CAT_SEL=null;
  const sel=CAT_SEL?catRecord(CAT_SEL):null;
  root.innerHTML = `
    <div id="bs-published">Loading today's pairings&hellip;</div>
    <div style="display:grid;grid-template-columns:230px 1fr;gap:16px;align-items:start">
      <div>
        <div style="font-size:11px;color:var(--dim);margin-bottom:6px">CATEGORIES</div>
        ${list.map(({rec,where})=>`<div class="story cat-pick" data-id="${esc(rec.id)}" style="padding:7px 9px;cursor:pointer;${rec.id===CAT_SEL?'border-color:var(--ink)':''}">
          <b style="font-size:12px">${esc(rec.title)}</b><br><span style="font-size:10.5px;color:var(--dim)">${esc(where==='published'?'published':rec.status)} · ${catStories(rec.id).length} stor${catStories(rec.id).length===1?'y':'ies'} filed</span></div>`).join('')||'<i style="font-size:12px;color:var(--dim)">none yet</i>'}
        <button class="mini primary" id="cat-new" style="margin-top:6px">+ new category</button>
        <div style="font-size:11px;color:var(--dim);margin-top:10px;line-height:1.5">The 21 fixed rows are edited in <code>editorial/backstory-rows.json</code>. A category made here becomes a page of its own and is sent with the Lineup publish once approved.</div>
      </div>
      <div id="cat-editor">${sel? (CATS[sel.id]||catEnsureLocal(sel.id) ? catEditorHtml(CATS[sel.id]) : '') : '<i style="color:var(--dim)">Pick a category on the left, or make a new one. A category named from a story in Lineup opens here.</i>'}</div>
    </div>`;
  fetchPublishedBackstory().then(d=>{ const el=document.getElementById('bs-published'); if (el) el.innerHTML=pairingsHtml(d); });
  root.querySelectorAll('.cat-pick').forEach(el=>el.addEventListener('click',()=>{ CAT_SEL=el.dataset.id; if (!CATS[CAT_SEL]) catEnsureLocal(CAT_SEL); render(); }));
  document.getElementById('cat-new').addEventListener('click',()=>{
    const n=prompt('Name the new category: a short noun phrase readers could build expertise in (for example "AI").','');
    if (!n||!n.trim()) return; const id=newCategory(n,[]); if (id){ CAT_SEL=id; render(); }
  });
  const c = sel && CATS[sel.id]; if (!c) return;
  const ed=document.getElementById('cat-editor');
  const touch=()=>{ c.status = c.status==='approved' ? 'draft' : c.status; saveCats(); };   // an edit after approval needs re-approval
  document.getElementById('cat-title').addEventListener('change',e=>{ c.title=e.target.value.trim().slice(0,60)||c.title; touch(); render(); });
  document.getElementById('cat-contest').addEventListener('change',e=>{ c.contest=e.target.value.trim(); c.by.contest='editor'; touch(); render(); });
  document.getElementById('cat-stakes').addEventListener('change',e=>{ c.stakes=e.target.value.trim(); c.by.stakes='editor'; touch(); render(); });
  ed.querySelectorAll('.cat-lens').forEach(el=>el.addEventListener('change',()=>{
    const l=el.dataset.lens; c.lenses=el.checked?Array.from(new Set(c.lenses.concat([l]))):c.lenses.filter(x=>x!==l); c.by.lenses='editor'; touch(); render(); }));
  ed.querySelectorAll('.cat-ind').forEach(el=>el.addEventListener('change',()=>{ c.indicator=c.indicator||{}; c.indicator[el.dataset.k]=el.value.trim(); touch(); render(); }));
  const indOk=ed.querySelector('.cat-ind-ok'); if (indOk) indOk.addEventListener('change',()=>{ c.indicator=c.indicator||{}; c.indicator.verified=indOk.checked; touch(); render(); });
  ed.querySelectorAll('[data-oid]').forEach(row=>{
    const oid=row.dataset.oid;
    row.querySelector('.cat-isbeg').addEventListener('change',e=>{
      if (e.target.checked){ const o=POOL_BY[oid]||{}; if (!c.beginnings.some(b=>b.object_id===oid)) c.beginnings.push({object_id:oid,line:o.line||'',by:'editor'}); }
      else c.beginnings=c.beginnings.filter(b=>b.object_id!==oid);
      touch(); render(); });
    const ap=row.querySelector('.cat-approve'); if (ap) ap.addEventListener('change',e=>{
      c.approved_objects=e.target.checked?Array.from(new Set((c.approved_objects||[]).concat([oid]))):(c.approved_objects||[]).filter(x=>x!==oid); touch(); render(); });
    row.querySelector('.cat-rm').addEventListener('click',()=>{ c.objects=c.objects.filter(o=>o.object_id!==oid); c.beginnings=c.beginnings.filter(b=>b.object_id!==oid); touch(); render(); });
    const ln=row.querySelector('.cat-line'); if (ln) ln.addEventListener('change',e=>{ const b=c.beginnings.find(x=>x.object_id===oid); if (b){ b.line=e.target.value.trim(); b.by='editor'; } touch(); render(); });
    row.querySelector('.cat-about').addEventListener('change',e=>{ const o=c.objects.find(x=>x.object_id===oid); if (o){ o.about=e.target.value.trim(); o.by='editor'; } touch(); render(); });
  });
  const add=document.getElementById('cat-add'); if (add) add.addEventListener('change',e=>{
    const oid=e.target.value; if (!oid) return; const o=POOL_BY[oid];
    c.objects.push({object_id:oid,about:o.about||'',by:'editor'}); c.beginnings.push({object_id:oid,line:o.line||'',by:'editor'});
    if (o.pool==='candidate') c.approved_objects=Array.from(new Set((c.approved_objects||[]).concat([oid])));   // adding it by hand is approving it
    touch(); render(); });
  document.getElementById('cat-compose').addEventListener('click',()=>{ if (!c.contest || confirm('Recompose replaces the model-written parts. Text you wrote or edited is kept.')) composeCat(c.id); });
  document.getElementById('cat-save').addEventListener('click',()=>{ saveCats(); CAT_MSG[c.id]='Saved. It stays a draft until you approve it.'; render(); });
  document.getElementById('cat-approve').addEventListener('click',()=>{
    if (c.status==='approved'){ c.status='draft'; saveCats(); render(); return; }
    const probs=catCheck(c).problems;
    if (probs.length && !confirm('Publish will drop these parts:\n\n  • '+probs.slice(0,8).join('\n  • ')+'\n\nApprove anyway?')) return;
    c.status='approved'; c.updated=new Date().toISOString(); saveCats(); CAT_MSG[c.id]='Approved. It goes out with the next Lineup publish.'; render(); });
  document.getElementById('cat-del').addEventListener('click',()=>{
    if (PUBCATS.some(r=>r.id===c.id)){ alert('This category is published. It archives itself after 30 days with no story filed under it.'); return; }
    if (!confirm('Delete the draft "'+c.title+'"? Stories filed under it go back to the classifier.')) return;
    delete CATS[c.id]; LINEUP.forEach(s=>{ if (s.backstoryRow===c.id) s.backstoryRow=''; }); saveLineup(); saveCats(); CAT_SEL=null; render(); });
  document.getElementById('cat-revise').addEventListener('click',()=>{ const t=document.getElementById('cat-rev').value; if (t.trim()) reviseCat(c.id,t); });
}
loadCatData();
