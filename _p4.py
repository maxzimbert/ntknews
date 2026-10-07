p='ntk-pulse/pulse.html'; s=open(p).read()
def rep(old,new,cnt=1):
    global s
    assert old in s, "MISSING: "+old[:90]
    s=s.replace(old,new,cnt)

# --- pure: verify a document the model found by search; custom objects honour an exact date
rep("/* CATS:END */","""// A document the model found by web search: the link must be one the search returned, https, not on
// the refused list, and it needs a title and a year. CI checks that the link loads at publish.
function verifyFoundObject(o, search){
  const url=String(o.source_url||'').trim(), host=url.replace(/^https?:\\/\\/([^\\/]+).*$/,'$1').toLowerCase();
  if (!url.startsWith('https://')) return {ok:false, reason:'the link must start with https://'};
  if (!(search.urls||[]).includes(url)) return {ok:false, reason:'the link is not one the search returned'};
  if (CAT_DENY.some(d=>host.includes(d))) return {ok:false, reason:host+' is not a primary source'};
  if (!/^\\d{3,4}$/.test(String(o.year||''))) return {ok:false, reason:'it has no year'};
  if (!String(o.title||'').trim()) return {ok:false, reason:'it has no title'};
  return {ok:true};
}
/* CATS:END */""")
rep("sort:String(cu.year)+'-01-01',source:cu.source||host,url:url,lenses:[]","sort:/^\\d{4}-\\d\\d-\\d\\d$/.test(cu.date||'')?cu.date:String(cu.year)+'-01-01',source:cu.source||host,url:url,lenses:[]")
rep("year:String(cu.year),sort:String(cu.year)+'-01-01',source:cu.source||'',url:cu.url,lenses:[],subgenre:'',link_status:'unchecked',about:'',line:''} : null;",
    "year:String(cu.year),sort:/^\\d{4}-\\d\\d-\\d\\d$/.test(cu.date||'')?cu.date:String(cu.year)+'-01-01',source:cu.source||'',url:cu.url,lenses:[],subgenre:'',link_status:'unchecked',about:'',line:''} : null;")
rep("'<span class=\"chip\">matrix</span>'}","'<span class=\"chip\">'+esc(e.pool==='custom'?'added':'matrix')+'</span>'}")

# --- find a document by search
rep("async function reviseCat(id, request){","""async function proposeObject(c, desc){
  const p=`You find ONE primary-source document for a Backstory category page at NTK.

CATEGORY: ${c.title}
THE EDITOR WANTS: ${desc}

Use web search to find the document itself, or the copy held by an archive, court, legislature, government agency or the original publisher. Not Wikipedia, not a news article or summary about it, not a retail or study-guide page. Then answer with JSON only:
{"title":"the document's exact title","author":"who issued or wrote it","year":"YYYY","date":"YYYY-MM-DD if you know the exact date, else null","source":"the publishing body or archive","source_url":"the exact page or PDF where the document can be read","note":"one sentence"}
If you cannot find one, answer {"none":"why"}.`;
  const r=await aiSearch(p,1500), j=catJson(r.text);
  if (j.none) return 'Could not find "'+desc+'": '+j.none+'.';
  const v=verifyFoundObject(j,{urls:r.urls});
  if (!v.ok) return 'Found "'+(j.title||desc)+'" but could not use it: '+v.reason+'.';
  const cid='custom-'+String(j.title).toLowerCase().replace(/[^a-z0-9]+/g,'-').slice(0,60);
  if ((c.objects||[]).some(o=>o.object_id===cid)) return '"'+j.title+'" is already here.';
  const cu={id:cid,title:String(j.title).trim(),author:j.author||'',year:String(j.year),date:/^\\d{4}-\\d\\d-\\d\\d$/.test(j.date||'')?j.date:'',source:j.source||'',url:j.source_url,found_by:'search'};
  c.custom_objects=(c.custom_objects||[]).filter(x=>x.id!==cid).concat([cu]);
  c.objects.push({object_id:cid,about:'',by:'model'}); c.beginnings.push({object_id:cid,line:'',by:'model'});
  return 'Added '+cu.title+' ('+cu.year+') from '+String(cu.url).replace(/^https?:\\/\\/([^\\/]+).*$/,'$1')+'.';
}
async function reviseCat(id, request){""")
rep('"add":["<id from the available list>"],"drop":["<id>"],"note":"one sentence saying what you changed"}','"add":["<id from the available list>"],"drop":["<id>"],"find":["a short description of a document to look up"],"note":"one sentence saying what you changed"}')
rep("contest: \"Whether X, or Y\", 12 to 30 words. stakes: two short sentences, 25 to 55 words. A line is one sentence of 12 to 25 words. An about is two to four sentences, at most 70 words.\n${CAT_STYLE_RULES}`;\n    const r=catJson(await ai(p,CAT_MAXTOK));",
    "contest: \"Whether X, or Y\", 12 to 30 words. stakes: two short sentences, 25 to 55 words. A line is one sentence of 12 to 25 words. An about is two to four sentences, at most 70 words.\nIf the editor asks for a document that is not in the available list, NEVER refuse and never say it does not exist: put a short description of it in \"find\" (for example \"the Mueller report on Russian interference in the 2016 election\") and a web search will look for the original. Up to three.\n${CAT_STYLE_RULES}`;\n    const r=catJson(await ai(p,CAT_MAXTOK));")
rep("    const need=c.beginnings.filter(b=>!b.line).map(b=>catEntry(c,b.object_id)).filter(Boolean);\n    if (need.length) await writeObjectText(c, need);\n    c.revisions=(c.revisions||[]).concat([{at:new Date().toISOString(),request:request,summary:r.note||''}]);\n    CAT_MSG[id]=r.note||'Revised.';",
"""    const found=[];
    for (const d of (r.find||[]).slice(0,3)){
      try { found.push(await proposeObject(c, d)); } catch(e){ found.push('Could not search for "'+d+'": '+e.message+' (web search may not be enabled for this key).'); }
    }
    const need=c.beginnings.filter(b=>!b.line).map(b=>catEntry(c,b.object_id)).filter(Boolean);
    if (need.length) await writeObjectText(c, need);
    const summary=[r.note||''].concat(found).filter(Boolean).join(' ');
    c.revisions=(c.revisions||[]).concat([{at:new Date().toISOString(),request:request,summary:summary}]);
    CAT_MSG[id]=summary||'Revised.';""")

# --- keep what you are typing when something else triggers a re-render
rep("function renderBackstory(root){\n  const list=catListAll();","""// Something else in Pulse (a story generating in Lineup, say) calls render() while you are typing here.
// Capture what you have typed and where your cursor is, and put it back after the tab redraws.
function catFieldKey(el){
  const row=el.closest && el.closest('[data-oid]');
  if (el.id) return el.id;
  if (row) return (el.classList.contains('cat-line')?'line:':'about:')+row.dataset.oid;
  if (el.classList.contains('cat-ind')) return 'ind:'+el.dataset.k;
  return null;
}
const CAT_FIELDS='textarea, input[type=text], input:not([type])';
function catCaptureInputs(){
  const ed=document.getElementById('cat-editor'); if (!ed) return null;
  const dirty={}; let focus=null; const ae=document.activeElement;
  ed.querySelectorAll(CAT_FIELDS).forEach(el=>{
    const k=catFieldKey(el); if (!k) return;
    if (el.value!==el.defaultValue) dirty[k]=el.value;
    if (el===ae) focus={k:k,s:el.selectionStart,e:el.selectionEnd};
  });
  return {dirty:dirty, focus:focus, y:window.scrollY, sel:CAT_SEL};
}
function catRestoreInputs(st){
  const ed=document.getElementById('cat-editor'); if (!st || !ed || st.sel!==CAT_SEL) return;
  ed.querySelectorAll(CAT_FIELDS).forEach(el=>{
    const k=catFieldKey(el); if (!k) return;
    if (st.dirty[k]!==undefined) el.value=st.dirty[k];
    if (st.focus && st.focus.k===k){ el.focus(); try { el.setSelectionRange(st.focus.s, st.focus.e); } catch(e){} }
  });
  window.scrollTo(0, st.y);
}
function renderBackstory(root){
  const _kept=catCaptureInputs();
  const list=catListAll();""")
rep("  fetchPublishedBackstory().then(d=>{ const el=document.getElementById('bs-published'); if (el) el.innerHTML=pairingsHtml(d); });","  catRestoreInputs(_kept);\n  fetchPublishedBackstory().then(d=>{ const el=document.getElementById('bs-published'); if (el) el.innerHTML=pairingsHtml(d); });")
rep("return {validateCat","return {validateCat") if False else None
open(p,'w').write(s)
