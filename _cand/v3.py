import re,html,urllib.request,urllib.error,ssl,concurrent.futures as cf
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
ctx=ssl.create_default_context()
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA}),timeout=25,context=ctx) as r: return r.status,r.headers.get('content-type',''),r.read(600000)
    except urllib.error.HTTPError as e: return e.code,'',b''
    except Exception as e: return 0,type(e).__name__,b''
U=["https://peacemaker.un.org/node/1581","https://peacemaker.un.org/sites/default/files/document/files/2024/05/sy120630final20communique20of20the20action20group20for20syria.pdf",
"http://www.mandela.gov.za/mandela_speeches/before/640420_trial.htm","https://static.un.org/en/events/mandeladay/court_statement_1964.shtml",
"https://www.japaneselawtranslation.go.jp/en/laws/view/174","https://www.ndl.go.jp/constitution/e/etc/c01.html",
"https://ustr.gov/about-us/policy-offices/press-office/ustr-archives/north-american-free-trade-agreement-nafta","http://www.sice.oas.org/trade/nafta/naftatce.asp",
"https://www.cvce.eu/en/obj/treaty_between_the_french_republic_and_the_federal_republic_of_germany_on_french_german_cooperation_22_january_1963-en-68956f73-75cb-4749-a6e2-344c8aad84ba.html",
"https://germanhistorydocs.ghi-dc.org/sub_document.cfm?document_id=78","https://ghdi.ghi-dc.org/sub_document.cfm?document_id=76","https://germanhistorydocs.ghi-dc.org/sub_document.cfm?document_id=172",
"https://www.presidency.ucsb.edu/documents/the-state-the-union-address-delivered-before-joint-session-the-congress-1",
"https://www.bundesregierung.de/breg-en/news/policy-statement-by-olaf-scholz-chancellor-of-the-federal-republic-of-germany-and-member-of-the-german-bundestag-27-february-2022-in-berlin-2008378",
"https://avalon.law.yale.edu/20th_century/usmu001.asp","https://mea.gov.in/in-focus-article.htm?19005/Simla+Agreement+July+2+1972",
"https://www.un.org/unispal/document/auto-insert-178331/","https://www.mfa.gov.tr/lausanne-peace-treaty-part-i_-political-clauses.en.mfa",
"https://www.nato.int/cps/en/natohq/topics_52044.htm","https://www.mofa.go.jp/region/n-america/us/q&a/ref/1.html","https://www.mofa.go.jp/policy/q_a/faq4/index.html"]
def c(u):
    st,ct,b=get(u); t=b.decode('utf-8','ignore'); ti=re.search(r'<title[^>]*>(.*?)</title>',t,re.S)
    tx=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',re.sub(r'<(script|style).*?</\1>','',t,flags=re.S))))
    return u,st,ct[:15],(html.unescape(ti.group(1)).strip()[:70] if ti else ''),len(tx)
with cf.ThreadPoolExecutor(8) as ex:
    for r in ex.map(c,U): print(r[1],r[2],r[4],'|',r[3],'|',r[0][:80])
