import sys,re,json,html,urllib.request,urllib.error,ssl,concurrent.futures as cf
sys.path.insert(0,'.')
from cand import C
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
ctx=ssl.create_default_context()
def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html,application/pdf;q=0.9,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req,timeout=25,context=ctx) as r:
            b=r.read(600000); ct=r.headers.get('content-type','')
            return r.status,r.geturl(),ct,b
    except urllib.error.HTTPError as e: return e.code,u,'',b''
    except Exception as e: return 0,u,type(e).__name__,b''
def check(c):
    lens,yr,sd,title,au,src,row,sg,urls,kws,why=c
    out=[]
    for u in urls:
        if u.startswith('SEARCH:'): out.append(('search',u,0,'')); continue
        st,final,ct,b=get(u)
        txt=b.decode('utf-8','ignore') if 'pdf' not in ct else ''
        t=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',re.sub(r'<(script|style).*?</\1>','',txt,flags=re.S))))
        hit=[k for k in kws if k.lower() in t.lower()]
        out.append(('ok' if st==200 and (len(hit)==len(kws) or 'pdf' in ct) else 'weak' if st==200 else 'fail',u,st,f"{ct[:20]} hits {len(hit)}/{len(kws)} final={final[:80]}"))
    return c,out
with cf.ThreadPoolExecutor(6) as ex: res=list(ex.map(check,C))
for c,out in res:
    print(f"{c[0]:7} {c[1]} {c[3][:55]}")
    for kind,u,st,info in out: print(f"    {kind:6} {st} {u[:90]} {info}")
