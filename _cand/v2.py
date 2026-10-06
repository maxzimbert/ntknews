import sys,re,html,urllib.request,urllib.error,ssl,concurrent.futures as cf
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
ctx=ssl.create_default_context()
def get(u):
    req=urllib.request.Request(u,headers={"User-Agent":UA})
    try:
        with urllib.request.urlopen(req,timeout=30,context=ctx) as r:
            b=r.read(800000); return r.status,r.geturl(),r.headers.get('content-type',''),b
    except urllib.error.HTTPError as e: return e.code,u,'',b''
    except Exception as e: return 0,u,type(e).__name__,b''
T=[("https://www.treaty-accord.gc.ca/text-texte.aspx?id=101662",["Lakes","Lake Ontario"]),
("https://www.international.gc.ca/trade-commerce/assets/pdfs/agreements-accords/cusfta-e.pdf",[]),
("https://www.govinfo.gov/app/details/SERIALSET-13880_00_00-008-0216-0000",["Free-Trade"]),
("https://www.ruhr-uni-bochum.de/gna/Quellensammlung/09/09_jointstatementissuedatOgdensburg_1940.htm",["Ogdensburg","defence"]),
("https://www.federalregister.gov/documents/2025/02/07/2025-02406/imposing-duties-to-address-the-flow-of-illicit-drugs-across-our-northern-border",["Northern Border","Canada"]),
("https://www.govinfo.gov/app/details/DCPD-202500209",["Northern Border"]),
("https://www.nato.int/en/about-us/official-texts-and-resources/official-texts/2025/06/25/the-hague-summit-declaration",["Hague","3.5%"]),
("https://www.presidency.ucsb.edu/documents/national-security-presidential-memorandum-ceasing-united-states-participation-the-joint",["Joint Comprehensive Plan of Action"]),
("https://history.state.gov/historicaldocuments/frus1964-68v13/d137",["NATO","sovereignty"]),
("https://www.cvce.eu/content/publication/1997/10/13/d97bf195-34e1-4862-b5e7-87577a8c1632/publishable_en.pdf",[]),
("https://www.elysee.fr/emmanuel-macron/2023/04/17/adresse-aux-francais-2",["retraites","Français"]),
("https://archive.globalpolicy.org/political-issues-in-iraq/important-documents-on-iraq/34911.html",["Villepin","Iraq"]),
("https://www.un.org/unispal/document/auto-insert-185393/",["Partition","Jewish","Palestine"]),
("https://docs.un.org/en/S/PV.4701",["Iraq"]),
("https://main.un.org/securitycouncil/en/content/resolutions-adopted-security-council-1987",["598"]),
("https://digitallibrary.un.org/record/94433",["598"]),
("https://www.iusct.com/",["Algiers"]),
("https://2001-2009.state.gov/r/pa/ho/time/jd/91716.htm",["Rush","Bagot"]),
]
def chk(t):
    u,k=t; st,f,ct,b=get(u); txt=b.decode('utf-8','ignore') if 'pdf' not in ct else ''
    tx=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',re.sub(r'<(script|style).*?</\1>','',txt,flags=re.S))))
    return u,st,ct[:25],[x for x in k if x.lower() in tx.lower()],len(k),len(tx),tx[:120]
with cf.ThreadPoolExecutor(6) as ex:
    for r in ex.map(chk,T): print(r[1],r[2],f"{len(r[3])}/{r[4]}",r[5],r[0][:95],'|',r[6][:90])
