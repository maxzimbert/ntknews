p='ntk-pulse/pulse.html'; s=open(p).read()
def rep(old,new,cnt=1):
    global s
    assert old in s, "MISSING: "+old[:90]
    s=s.replace(old,new,cnt)
rep("// pattern seedBackstory() uses. Derived","// pattern the Backstory seed once used. Derived") if "// pattern seedBackstory() uses. Derived" in s else None
s=s.replace("same pattern seedBackstory() uses","same pattern the Backstory seed once used")

# --- sub-genres block after the lenses block
rep("""    <b style="font-size:11px">CONTEST</b><textarea id="cat-contest" """,
"""    <div style="margin:8px 0"><b style="font-size:11px">SUB-GENRES</b> <span style="font-size:11px;color:var(--dim)">American arguments this category belongs to; their sources feed the Beginnings.</span>
      <div style="margin-top:4px">${(c.subgenres||[]).map(g=>`<label style="margin-right:10px;white-space:nowrap"><input type="checkbox" class="cat-sg" data-sg="${esc(g)}" checked> ${esc(g)}</label>`).join('')}
      <select id="cat-sg-add"><option value="">add a sub-genre\\u2026</option>${((POOL&&POOL.vocab&&POOL.vocab.subgenres)||[]).filter(x=>!(c.subgenres||[]).includes(x.name)).map(x=>`<option value="${esc(x.name)}">${esc(x.row_title)}: ${esc(x.name)}</option>`).join('')}</select></div></div>
    <b style="font-size:11px">CONTEST</b><textarea id="cat-contest" """)

# --- trend line: display what is tracked, source, verification; fields only under "edit by hand"
a=s.index("    <details style=\"margin:6px 0\"><summary style=\"cursor:pointer;font-size:11px\"><b>TREND LINE</b>")
b=s.index("</details>",a)+len("</details>")
new_trend = """    <div style="margin:8px 0"><b style="font-size:11px">TREND LINE</b>
      ${c.indicator?`<div style="font-size:12px;margin:4px 0"><b>${esc(c.indicator.label||'')}</b>: ${esc(c.indicator.then_value||'')} (${esc(c.indicator.then_year||'')}) to ${esc(c.indicator.now_value||'')} \\u00b7 ${esc(c.indicator.direction||'')}<br>
        Source: ${c.indicator.source_url?`<a href="${esc(c.indicator.source_url)}" target="_blank" rel="noopener">${esc(c.indicator.source||'source')} \\u2197</a>`:esc(c.indicator.source||'')}, ${esc(c.indicator.as_of||'')}<br>
        <span style="color:${c.indicator.verified?'var(--certified)':'var(--stale)'}">${c.indicator.verified?'Checked'+(c.indicator.verified_by==='system'?' by the system':' by you')+': '+esc(c.indicator.how_checked||''):'Proposed, not verified: '+esc(c.indicator.unverified_reason||'it needs a source link and a check')+'. It will not publish.'}</span>
        ${(c.indicator.evidence||[]).length?`<br><span style="color:var(--dim)">Cited passage: \\u201c${esc((c.indicator.evidence||[])[0].slice(0,220))}\\u201d</span>`:''}</div>`
        :`<div style="font-size:12px;color:var(--dim);margin:4px 0">None yet. Compose finds one by web search, or tell me what to track in the revision box ("use a measure of local opposition").</div>`}
      <details><summary style="cursor:pointer;font-size:11px;color:var(--dim)">edit by hand</summary>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${f('label',260)}${f('then_value',70)}${f('then_year',60)}${f('now_value',70)}${f('direction',90)}${f('source',170)}${f('source_url',260)}${f('as_of',100)}
        <input class="cat-ind" data-k="how_checked" value="${esc(ind.how_checked||'')}" placeholder="how you checked it" style="width:100%">
        <label style="font-size:11px"><input type="checkbox" class="cat-ind-ok" ${ind.verified?'checked':''}> I checked it against the source</label></div></details></div>"""
s=s[:a]+new_trend+s[b:]

# --- add an object: whole pool search + by link
a=s.index("    ${addable.length?`<div style=\"margin-top:6px\"><select id=\"cat-add\">")
b=s.index("</div>`:''}",a)+len("</div>`:''}")
new_add = """    <details style="margin-top:8px"><summary style="cursor:pointer;font-size:12px"><b>+ Add an object</b></summary>
      <div style="margin:6px 0"><div style="font-size:11px;color:var(--dim)">From the pool (matrix and candidates, ${POOL?POOL.objects.length:0} objects). Search by title, author, year or lens.</div>
        <input id="cat-find" placeholder="search the pool\\u2026" style="width:280px"><div id="cat-find-out" style="margin-top:4px"></div></div>
      <div style="margin:10px 0 4px;font-size:11px;color:var(--dim)">Or add a primary source by its link. A model writes its line and About text; adding it counts as your approval.</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap"><input id="cu-title" placeholder="title" style="width:220px"><input id="cu-author" placeholder="author" style="width:150px"><input id="cu-year" placeholder="year" style="width:60px"><input id="cu-source" placeholder="source (archive or publisher)" style="width:190px"><input id="cu-url" placeholder="https:// link to the document" style="width:300px"><button class="mini go" id="cu-add">Add</button></div>
      <div style="font-size:11px;color:var(--dim);margin-top:3px">Not accepted as sources: Wikipedia, retail pages, flashcard and homework sites. The link is checked when you publish.</div>
    </details>"""
s=s[:a]+new_add+s[b:]
rep("  const addable=catPoolFor(c.lenses).filter(o=>!(c.objects||[]).some(x=>x.object_id===o.id));\n","")

# --- handlers: replace the old #cat-add handler with search + by-link + sub-genre handlers
a=s.index("  const add=document.getElementById('cat-add'); if (add)"); b=s.index("  document.getElementById('cat-compose')",a)
new_h = """  ed.querySelectorAll('.cat-sg').forEach(el=>el.addEventListener('change',()=>{ c.subgenres=el.checked?Array.from(new Set((c.subgenres||[]).concat([el.dataset.sg]))):(c.subgenres||[]).filter(x=>x!==el.dataset.sg); c.by.lenses='editor'; touch(); render(); }));
  const sgAdd=document.getElementById('cat-sg-add'); if (sgAdd) sgAdd.addEventListener('change',e=>{ if (!e.target.value) return; c.subgenres=Array.from(new Set((c.subgenres||[]).concat([e.target.value]))); c.by.lenses='editor'; touch(); render(); });
  const addFromPool=oid=>{
    const o=catEntry(c,oid); if (!o || c.objects.some(x=>x.object_id===oid)) return;
    c.objects.push({object_id:oid,about:o.about||'',by:'editor'}); c.beginnings.push({object_id:oid,line:o.line||'',by:'editor'});
    if (o.pool==='candidate') c.approved_objects=Array.from(new Set((c.approved_objects||[]).concat([oid])));   // adding it by hand is approving it
    touch(); render();
    if (!(o.line&&o.about)) writeObjectText(c,[o]).then(()=>{ saveCats(); render(); }).catch(err=>{ CAT_MSG[c.id]='Could not write its text: '+err.message; render(); });
  };
  const find=document.getElementById('cat-find'); if (find) find.addEventListener('input',()=>{
    const q=find.value.trim().toLowerCase(), out=document.getElementById('cat-find-out'); if (!q){ out.innerHTML=''; return; }
    const have=new Set((c.objects||[]).map(o=>o.object_id));
    const hits=(POOL?POOL.objects:[]).filter(o=>!have.has(o.id) && o.url && (o.title+' '+o.author+' '+o.year+' '+o.lenses.join(' ')+' '+(o.subgenre||'')).toLowerCase().includes(q)).slice(0,12);
    out.innerHTML=hits.map(o=>`<div style="font-size:12px;margin:2px 0"><button class="mini cat-addhit" data-id="${esc(o.id)}">add</button> <b>${esc(o.year)}</b> ${esc(o.title.slice(0,80))} <span class="chip">${esc(o.pool)}</span> <span style="color:var(--dim)">${esc(o.lenses.join(', '))}</span></div>`).join('')||'<i style="font-size:11px;color:var(--dim)">nothing matches</i>';
    out.querySelectorAll('.cat-addhit').forEach(b=>b.addEventListener('click',()=>addFromPool(b.dataset.id)));
  });
  const cuAdd=document.getElementById('cu-add'); if (cuAdd) cuAdd.addEventListener('click',()=>{
    const g=id=>document.getElementById(id).value.trim();
    const cu={title:g('cu-title'),author:g('cu-author'),year:g('cu-year'),source:g('cu-source'),url:g('cu-url')};
    if (!cu.title || !cu.url || !/^\\d{3,4}$/.test(cu.year)){ CAT_MSG[c.id]='An added object needs a title, a year and a link.'; render(); return; }
    if (!cu.url.startsWith('https://')){ CAT_MSG[c.id]='The link must start with https://'; render(); return; }
    if (/wikipedia\\.org|amazon\\.|abebooks\\.|ebay\\.|goodreads\\.|scribd\\.|studocu\\.|coursehero\\.|quizlet\\.|unz\\.com/i.test(cu.url)){ CAT_MSG[c.id]='That host is not accepted as a primary source.'; render(); return; }
    cu.id='custom-'+cu.title.toLowerCase().replace(/[^a-z0-9]+/g,'-').slice(0,60);
    c.custom_objects=(c.custom_objects||[]).filter(x=>x.id!==cu.id).concat([cu]);
    addFromPool(cu.id);
  });
"""
s=s[:a]+new_h+s[b:]
open(p,'w').write(s)
print('ok')
