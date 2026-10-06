import sys,re,html,urllib.request,urllib.error,ssl,concurrent.futures as cf,json
sys.path.insert(0,'.')
from cand2 import C2
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
ctx=ssl.create_default_context()
def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html,application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req,timeout=25,context=ctx) as r:
            b=r.read(700000); return r.status,r.geturl(),r.headers.get('content-type',''),b
    except urllib.error.HTTPError as e: return e.code,u,'',b''
    except Exception as e: return 0,u,type(e).__name__,b''
def chk(c):
    lens,sd,title,au,src,row,sg,urls,kws,why,note=c; res=[]
    for u in urls:
        st,f,ct,b=get(u); pdf='pdf' in ct or b[:4]==b'%PDF'
        tx='' if pdf else html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',re.sub(r'<(script|style).*?</\1>','',b.decode('utf-8','ignore'),flags=re.S))))
        hits=[k for k in kws if k.lower() in tx.lower()]
        js = 'docs.un.org' in u or 'undocs' in u
        if st==200 and pdf: kind='live-pdf'
        elif st==200 and js: kind='needs-check'
        elif st==200 and len(hits)==len(kws): kind='live'
        elif st==200: kind='weak'
        else: kind='fail'
        res.append((kind,u,st,len(tx)))
    return c,res
with cf.ThreadPoolExecutor(8) as ex: out=list(ex.map(chk,C2))
json.dump([[list(c[:3]),r] for c,r in out],open('res2.json','w'))
good=bad=0
for c,r in out:
    best=next((x for x in r if x[0] in('live','live-pdf','needs-check')),None)
    flag='OK ' if best else '-- '
    print(flag,c[0][:8].ljust(9),c[1][:4],c[2][:48].ljust(48),(best[0]+' '+best[1][:60]) if best else ' | '.join(f"{x[0]}{x[2]}" for x in r))
