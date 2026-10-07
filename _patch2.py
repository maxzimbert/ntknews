import re
p='ntk-pulse/pulse.html'; s=open(p).read()
def rep(old,new,cnt=1):
    global s
    assert old in s, "MISSING: "+old[:80]
    s=s.replace(old,new,cnt)
def cut(start_marker, end_marker, keep_end=True):
    global s
    a=s.index(start_marker); b=s.index(end_marker,a)
    s=s[:a]+(s[b:] if keep_end else s[b+len(end_marker):])
def fn_span(name):
    m=re.search(r"\n(async )?function "+name+r"\(", s); a=m.start()+1
    n=re.search(r"\n(?=(async )?function |const |let |/\* ─)", s[a+10:]); b=a+10+n.start()+1
    return a,b
def replace_fn(name,new):
    global s
    a,b=fn_span(name); s=s[:a]+new.strip('\n')+"\n"+s[b:]

# ---------- legacy removal ----------
cut("// Seeded once, only if localStorage is empty — the seven rows locked in", "function load(k, fallback)")
rep("let BACKSTORY = load(LS.backstory, null) || seedBackstory();\n","")
a=s.index("function saveBackstory(){"); b=s.index("}\n",a)+2; s=s[:a]+s[b:]
cut("/* ─── Backstory tab — standing, cross-day storylines.", "// What actually published, read from the repo rather than this browser.")
rep("// What actually published, read from the repo rather than this browser.\n// The editable row list below is legacy localStorage and does not drive\n// anything; see the note in publishBackstory().\n","// What actually published, read from the repo rather than this browser.\n")
rep("// (T-0010). Read from the published file, NOT from this tab's BACKSTORY\n// array — that one is a stale seven-row seed in localStorage and is the\n// reason publishing from the Backstory tab had to be disabled. One source.\n","// (T-0010). Read from the published file. One source.\n")
rep("  backstory: 'ntk_pulse_backstory_v1',\n","")

# ---------- state ----------
rep("CATS[id]=JSON.parse(JSON.stringify({id:p.id,title:p.title,status:'approved',contest:p.contest||'',stakes:p.stakes||'',lenses:p.lenses||[],",
    "CATS[id]=JSON.parse(JSON.stringify({id:p.id,title:p.title,status:'approved',contest:p.contest||'',stakes:p.stakes||'',lenses:p.lenses||[],subgenres:p.subgenres||[],custom_objects:p.custom_objects||[],")
rep("    CATS[id]={id:id,title:name.trim().slice(0,60),status:'draft',contest:'',stakes:'',lenses:[],indicator:null,objects:[],beginnings:[],",
    "    CATS[id]={id:id,title:name.trim().slice(0,60),status:'draft',contest:'',stakes:'',lenses:[],subgenres:[],custom_objects:[],indicator:null,objects:[],beginnings:[],")
rep("let CAT_BUSY = {}, CAT_MSG = {};","let CAT_BUSY = {}, CAT_MSG = {}, CAT_VOCAB = null;")
rep("    if (p){ POOL=p; POOL_BY=Object.fromEntries(p.objects.map(o=>[o.id,o])); }",
    "    if (p){ POOL=p; POOL_BY=Object.fromEntries(p.objects.map(o=>[o.id,o])); CAT_VOCAB=new Set(((p.vocab||{}).subgenres||[]).map(x=>x.name)); }")
# entries incl. objects added by link
rep("function catListAll(){","""function catEntry(c, oid){
  if (POOL_BY[oid]) return POOL_BY[oid];
  const cu=(c.custom_objects||[]).find(x=>(x.id||'')===oid);
  return cu ? {id:oid,pool:'custom',approved:true,title:cu.title,author:cu.author||'',year:String(cu.year),source:cu.source||'',url:cu.url,lenses:[],subgenre:'',link_status:'unchecked',about:'',line:''} : null;
}
function catListAll(){""")

# ---------- pool + pick ----------
replace_fn('catPoolFor',"""
function catPoolFor(lenses, subgenres){
  const sg=subgenres||[];
  return (POOL?POOL.objects:[]).filter(o=>o.url && o.link_status!=='dead' && (o.lenses.some(l=>lenses.includes(l)) || (o.subgenre && sg.includes(o.subgenre))));
}
""")
replace_fn('catPick',"""
// One subject takes up to six Beginnings, two or more take up to three each. A subject is a lens
// (a country or a technology) or a sub-genre (an American argument).
function catPick(lenses, subgenres){
  const subjects=(lenses||[]).map(l=>({l:l})).concat((subgenres||[]).map(g=>({g:g})));
  const k = subjects.length===1 ? 6 : 3, seen=new Set(), out=[];
  subjects.forEach(sj=>{
    pickBeginnings(sj.l ? catPoolFor([sj.l],[]) : catPoolFor([],[sj.g]), k).forEach(o=>{ if (!seen.has(o.id)){ seen.add(o.id); out.push(o); } });
  });
  return out.sort((a,b)=> a.sort<b.sort ? -1 : 1);
}
""")

# ---------- aiSearch + trend line ----------
rep("const CAT_STYLE_RULES =","""async function aiSearch(prompt, maxTok){
  if (!SETTINGS.antKey) throw new Error('No Anthropic key — set it in ⚙');
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method:'POST',
    headers:{'Content-Type':'application/json','x-api-key':SETTINGS.antKey,'anthropic-version':'2023-06-01','anthropic-dangerous-direct-browser-access':'true'},
    body:JSON.stringify({model:'claude-sonnet-5',max_tokens:maxTok||2500,thinking:{type:'disabled'},
      tools:[{type:'web_search_20250305',name:'web_search',max_uses:5}],messages:[{role:'user',content:prompt}]})});
  const d = await r.json();
  if (d.error) throw new Error(d.error.message);
  const urls=[], citations=[]; let text='';
  (d.content||[]).forEach(b=>{
    if (b.type==='web_search_tool_result' && Array.isArray(b.content)) b.content.forEach(x=>{ if (x.url) urls.push(x.url); });
    if (b.type==='text'){ text+=b.text||''; (b.citations||[]).forEach(c=>{ if (c.url){ citations.push({url:c.url,cited_text:c.cited_text||''}); if (!urls.includes(c.url)) urls.push(c.url); } }); }
  });
  if (!text.trim()) throw new Error('the search returned no answer');
  return {text:text, urls:urls, citations:citations};
}
// The model finds a trend line by web search; the system checks it (verifyIndicator). A figure
// that cannot be checked is kept as a proposal and never published.
async function proposeIndicator(c, guidance){
  const stories=catStories(c.id);
  const p=`You choose the trend line for a Backstory category page at NTK: ONE measure, shown as a then-and-now pair, of whether things are getting better, getting worse, or are contested on the argument this category is about.

CATEGORY: ${c.title}
CONTEST: ${c.contest||'(not written yet)'}
STORIES FILED UNDER IT: ${stories.map(s=>s.title).join(' | ')||'(none yet)'}
${guidance?"THE EDITOR'S REQUEST FOR THIS TREND LINE: "+guidance+"\\n":''}
Use web search to find a real published figure at its original source (the pollster, agency, court, statistics office or organisation that ran the survey), not an article repeating it. Prefer a measure asked the same way at two dates, or a rate published as a series. Then answer with JSON only:
{"label":"what is measured, as a reader would say it","then_value":"42%","then_year":"2025","now_value":"75%","direction":"worse|better|contested|flat","source":"the organisation","source_url":"the exact page where you found both figures","as_of":"month and year of the latest figure","note":"one sentence on what the two figures are"}
Rules: both figures must be stated on the page at source_url, in the form you give. Do not estimate or calculate. "direction" describes the figure, not your opinion of it: use contested when a rise or fall is not clearly good or bad. If you cannot find such a pair, answer {"none":"why"}.`;
  const r=await aiSearch(p,2500);
  const j=catJson(r.text);
  if (j.none){ c.indicator=null; return 'No trend line found: '+j.none; }
  const ind={label:j.label,then_value:j.then_value,then_year:j.then_year,now_value:j.now_value,direction:j.direction,source:j.source,source_url:j.source_url,as_of:j.as_of,note:j.note||''};
  const v=verifyIndicator(ind,{urls:r.urls,citations:r.citations});
  if (v.ok){
    ind.verified=true; ind.verified_by='system'; ind.evidence=v.evidence;
    ind.how_checked='Both figures appear in the passage cited from '+String(ind.source_url).replace(/^https?:\\/\\/([^\\/]+).*$/,'$1')+'.';
    c.by.indicator='model'; c.indicator=ind; return 'Trend line found and checked.';
  }
  ind.verified=false; ind.unverified_reason=v.reason; c.by.indicator='model'; c.indicator=ind;
  return 'Trend line proposed but not verified: '+v.reason+'. It will not publish. Tell me what to change.';
}
const CAT_STYLE_RULES =""")

# ---------- compose ----------
replace_fn('composeCat',"""
async function composeCat(id){
  const c=catEnsureLocal(id); if (!c) return;
  if (c.status==='approved') c.status='draft';       // new text needs a fresh approval
  if (!POOL){ CAT_MSG[id]='The object pool has not loaded.'; render(); return; }
  CAT_BUSY[id]='Composing…'; CAT_MSG[id]=''; render();
  const msgs=[];
  try {
    const stories=catStories(id), texts=stories.map(catStoryText), joined=texts.join(' ');
    const withText=stories.filter((s,i)=>texts[i].length>200).length;
    const allLenses=Object.keys(POOL.lenses);
    // with a story, only lenses its text supports; with none yet, the category's name must do the work
    const supported = withText ? allLenses.filter(l=>lensSupported(l,POOL.lenses,joined)) : allLenses;
    const vocab=((POOL.vocab||{}).subgenres||[]);
    const p1 = `You write the opening of a new category page for NTK's Backstory, a news product that shows readers how today's story sits inside a long American argument.

CATEGORY NAME: ${c.title}
THE STORIES FILED UNDER IT:
${stories.map((s,i)=>'['+(i+1)+'] '+s.title+'\\n'+texts[i].slice(0,3500)).join('\\n\\n') || '(none yet: decide from the category name alone)'}

SUBJECT LENSES (histories of a country, alliance or technology): ${supported.join(', ') || '(none)'}
SUB-GENRES (long American arguments, with their row): ${vocab.map(x=>x.name+' ['+x.row_title+']').join('; ')}

Write JSON only: {"contest":"...","stakes":"...","lenses":["..."],"subgenres":["..."],"note":"one sentence for the editor"}
1. contest: ONE sentence ending in a full stop, "Whether X, or Y", two positions a reasonable person holds. 12 to 30 words.
2. stakes: TWO short sentences, 25 to 55 words in all, framed as the open questions the argument turns on (whether, when, by whom, who benefits). Do not write about "risks" in the abstract or "who pays". Write about the category as a whole, not about one story.
3. lenses: choose from the lenses above only those the category is mainly about. A lens is for a country, alliance or technology. Do not add a lens because it is a related topic.
4. subgenres: choose up to two from the sub-genres above that name the American argument this category belongs to, exactly as written, if it belongs to one. Choose at least one lens or one sub-genre: a category needs a history to draw on.
${CAT_STYLE_RULES}`;
    const r1=catJson(await ai(p1,1100));
    if (c.by.contest!=='editor' && r1.contest){ c.contest=String(r1.contest).trim(); c.by.contest='model'; }
    if (c.by.stakes!=='editor' && r1.stakes){ c.stakes=String(r1.stakes).trim(); c.by.stakes='model'; }
    if (c.by.lenses!=='editor'){
      c.lenses=(r1.lenses||[]).filter(l=>supported.includes(l));
      c.subgenres=(r1.subgenres||[]).filter(g=>CAT_VOCAB && CAT_VOCAB.has(g)).slice(0,2);
      c.by.lenses='model';
    }
    const picked=catPick(c.lenses, c.subgenres);
    const keepEd=(c.objects||[]).filter(o=>o.by==='editor'), edIds=new Set(keepEd.map(o=>o.object_id));
    c.objects=picked.map(o=>({object_id:o.id,about:o.about||'',by:'model'})).filter(o=>!edIds.has(o.object_id)).concat(keepEd);
    c.beginnings=picked.map(o=>({object_id:o.id,line:o.line||'',by:'model'})).concat((c.beginnings||[]).filter(b=>edIds.has(b.object_id)));
    if (!picked.length) msgs.push(!stories.length ? 'No story is filed under this category yet and the model chose no lens or sub-genre with sources. Pick lenses or sub-genres below, or add objects by hand.' : withText ? 'No Beginnings: no lens or sub-genre with sources matched this story. Pick some below, or add objects by hand.' : 'The filed story has no generated text yet, so no lens could be matched. Generate the story, or pick lenses and sub-genres below.');
    await writeObjectText(c, picked.filter(o=>!(o.line&&o.about)));
    c.revisions=(c.revisions||[]).concat([{at:new Date().toISOString(),request:'(first draft)',summary:r1.note||''}]);
    if (r1.note) msgs.push(r1.note);
    if (c.by.indicator!=='editor'){
      CAT_BUSY[id]='Finding a trend line…'; render();
      try { msgs.push(await proposeIndicator(c,'')); } catch(e){ msgs.push('Trend line: '+e.message+' (web search may not be enabled for this key). Tell me what to track in the revision box.'); }
    }
  } catch(e){ msgs.push('Compose failed: '+e.message); }
  CAT_MSG[id]=msgs.join(' ');
  delete CAT_BUSY[id]; saveCats(); render();
}
""")

# ---------- revise routing ----------
rep("""  CAT_BUSY[id]='Revising…'; CAT_MSG[id]=''; render();
  try {
    const avail=catPoolFor(c.lenses).filter(o=>!c.objects.some(x=>x.object_id===o.id));""","""  CAT_BUSY[id]='Revising…'; CAT_MSG[id]=''; render();
  if (/\\b(trend|chart|indicator|poll|statistic|measure|figure|data point)\\b/i.test(request)){
    try {
      CAT_MSG[id]=await proposeIndicator(c, request);
      c.revisions=(c.revisions||[]).concat([{at:new Date().toISOString(),request:request,summary:CAT_MSG[id]}]);
    } catch(e){ CAT_MSG[id]='Trend line search failed: '+e.message; }
    delete CAT_BUSY[id]; saveCats(); render(); return;
  }
  try {
    const avail=catPoolFor(c.lenses,c.subgenres).filter(o=>!c.objects.some(x=>x.object_id===o.id));""")
rep("    const cur=c.beginnings.map(b=>{ const o=POOL_BY[b.object_id]||{};","    const cur=c.beginnings.map(b=>{ const o=catEntry(c,b.object_id)||{};")
rep("LENSES: ${c.lenses.join(', ')||'(none)'}\nBEGINNINGS NOW:","LENSES: ${c.lenses.join(', ')||'(none)'}\nSUB-GENRES: ${(c.subgenres||[]).join(', ')||'(none)'}\nBEGINNINGS NOW:")
rep("    const need=c.beginnings.filter(b=>!b.line).map(b=>POOL_BY[b.object_id]).filter(Boolean);","    const need=c.beginnings.filter(b=>!b.line).map(b=>catEntry(c,b.object_id)).filter(Boolean);")
rep("      const o=POOL_BY[oid]; if (!o || c.objects.some(x=>x.object_id===oid)) return;","      const o=catEntry(c,oid); if (!o || c.objects.some(x=>x.object_id===oid)) return;")

# ---------- check with vocab ----------
rep("  return validateCat(c, POOL_BY, POOL.lenses, texts, null);","  return validateCat(c, POOL_BY, POOL.lenses, texts, null, CAT_VOCAB);")
# preview + rows use catEntry
rep("    const o=POOL_BY[b.object_id]||{}; return `<div style=\"display:flex;gap:10px;margin:6px 0\">","    const o=catEntry(c,b.object_id)||{}; return `<div style=\"display:flex;gap:10px;margin:6px 0\">")
rep("    const e=POOL_BY[o.object_id]||{}; const bg=(c.beginnings||[]).find(b=>b.object_id===o.object_id);","    const e=catEntry(c,o.object_id)||{}; const bg=(c.beginnings||[]).find(b=>b.object_id===o.object_id);")
rep("const un=(c.objects||[]).filter(o=>{ const e=POOL_BY[o.object_id]||{};","const un=(c.objects||[]).filter(o=>{ const e=catEntry(c,o.object_id)||{};")
rep("(POOL_BY[oid]||{}).pool==='candidate')))); touch(); render(); });","(catEntry(c,oid)||{}).pool==='candidate')))); touch(); render(); });")
rep("    const e=catEntry(c,o.object_id)||{}; const bg=","    const e=catEntry(c,o.object_id)||{}; const bg=")  # no-op sanity
rep("    const oid=e.target.value; if (!oid) return; const o=POOL_BY[oid];","    const oid=e.target.value; if (!oid) return; const o=catEntry(c,oid);")
rep("      if (e.target.checked){ const o=POOL_BY[oid]||{};","      if (e.target.checked){ const o=catEntry(c,oid)||{};")
open(p,'w').write(s)
print('patched')
