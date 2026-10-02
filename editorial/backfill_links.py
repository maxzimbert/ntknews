#!/usr/bin/env python3
"""
Backfill the Object Matrix's "Source URL" column (col O) for objects that can
be linked from their citation. T-0065, tier A.

  python3 editorial/backfill_links.py             # dry run: report only
  python3 editorial/backfill_links.py --apply     # write col O (blanks only)

Never overwrites a URL that is already there. Every link it proposes is
verified before it counts:

  Supreme Court cases   Oyez (matched on volume+page from Oyez's own term
                        lists, else on case name and year), then the Library
                        of Congress U.S. Reports scan, checked live.
  Statutes              govinfo. Public laws from the 104th Congress on, and
                        Statutes at Large pages, fetched as PDF and checked for
                        a distinctive word from the act's title.

Stdlib only; pypdf is used for the statute check if it is installed.
Report: editorial/object-links-report.json
"""
import io, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "editorial" / "NTK_Backstory_Object_Matrix.xlsx"
REPORT = ROOT / "editorial" / "object-links-report.json"
UA = {"User-Agent": "ntknews-link-backfill/1.0 (editorial; contact via repo)"}
STOP = {"act", "of", "the", "and", "for", "to", "in", "a", "an", "amendments", "signing", "remarks",
        "statement", "united", "states", "authorization", "use", "reform", "protection", "law",
        "resolution", "agreement", "v", "vs", "versus", "scotus", "dissenting", "opinion"}

# Pre-104th-Congress public laws: Statutes at Large page. These are HINTS from
# memory, not facts. A hint is only used if the fetched page names the act.
STAT_HINTS = {"90-351": (82, 197), "90-618": (82, 1213), "91-604": (84, 1676), "96-8": (93, 14),
              "102-166": (105, 1071), "103-3": (107, 6), "103-141": (107, 1488), "103-322": (108, 1796)}


def get(url, binary=False, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        return (data if binary else data.decode("utf-8", "replace")), r.headers.get("Content-Type", ""), r.geturl()


def words(title):
    return [w for w in re.findall(r"[a-z]{4,}", title.lower()) if w not in STOP]


def pdf_text(url):
    try:
        import pypdf
    except ImportError:
        return None
    data, ctype, final = get(url, binary=True, timeout=60)
    if "pdf" not in ctype.lower():
        return ""
    rd = pypdf.PdfReader(io.BytesIO(data))
    return " ".join((rd.pages[i].extract_text() or "") for i in range(min(3, len(rd.pages)))).lower()


_oyez = {}
def oyez_term(term):
    if term not in _oyez:
        try:
            _oyez[term] = json.loads(get(f"https://api.oyez.org/cases?per_page=0&filter=term:{term}")[0])
        except Exception:
            _oyez[term] = []
        time.sleep(0.3)
    return _oyez[term]


def era_terms(year):
    y = int(year)
    if y < 1851: return ["1789-1850"]
    if y < 1901: return ["1850-1900"]
    if y < 1941: return ["1900-1940"]
    if y < 1956: return ["1940-1955"]
    return [str(y - 2), str(y - 1), str(y)]


NOISE = {"inc", "co", "corp", "et", "al", "the", "of", "and", "ltd", "scotus", "dissenting", "opinion", "concurring"}
# Hofstadter-era titles whose Oyez names differ. HINTS only: a hint must still
# find a case in Oyez's list for that era, decided within a year of the matrix year.
ALIAS = {"dred scott v standford": "scott v sandford", "slaughterhouse cases": "slaughterhouse cases",
         "us v ec knight": "united states v ec knight", "abrams v us": "abrams v united states",
         "us butler": "united states v butler", "charles river bridge v warren bridge": "charles river bridge v warren bridge"}


def norm(name):
    n = name.lower().replace("-", "").replace("\u2013", " ")
    n = re.sub(r"\b(versus|vs\.?|v\.)(?=\s)", "v", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return " ".join(w for w in n.split() if w not in NOISE)


def toks(name):
    return set(norm(name).split())


def name_match(title, cands, year):
    key = norm(title.split(" in ")[-1]) if "dissent" in title.lower() and " in " in title.lower() else norm(title)
    key = ALIAS.get(key, key)
    T = set(key.split())
    best = None
    for c in cands:
        cy = (c.get("citation") or {}).get("year")
        if cy and abs(int(cy) - int(year)) > 1:
            continue
        O = toks(c["name"])
        if not T or not O:
            continue
        inter = len(T & O)
        if inter / len(T) >= 0.75 and inter / len(O) >= 0.5:
            score = inter / len(T | O)
            if not best or score > best[0]:
                best = (score, c)
    return best[1] if best else None


# Citations for Hofstadter-era objects whose matrix source gives no U.S. cite, or
# whose name would match the wrong case (Brown I vs Brown II). Hints only: they
# are resolved through Oyez's own citation field, so a wrong hint finds nothing.
CITE_OVERRIDE = {"Brown v Board of Education of Topeka": "347 U.S. 483", "U.S. v E.C. Knight": "156 U.S. 1",
                 "Abrams v U.S.": "250 U.S. 616", "U.S. Butler": "297 U.S. 1"}


def override_cite(title):
    n = norm(title)
    return next((c for k, c in CITE_OVERRIDE.items() if n.startswith(norm(k))), None)


def link_case(year, title, source):
    source = override_cite(title) or source
    m = re.search(r"(\d+) U\.S\. (\d+)", source or "")
    cands = [c for t in era_terms(year) for c in oyez_term(t)]
    hit = None
    if m:
        hit = next((c for c in cands if c.get("citation") and str(c["citation"].get("volume")) == m.group(1)
                    and str(c["citation"].get("page")) == m.group(2)), None)
        how = "oyez:citation"
    if not hit:
        hit = name_match(title, cands, year)
        how = "oyez:name"
    if hit:
        path = hit["href"].split("/cases/")[1]
        return f"https://www.oyez.org/cases/{path}", how, f'Oyez: {hit["name"]} ({hit.get("citation", {}).get("volume")} U.S. {hit.get("citation", {}).get("page")})'
    if m:  # Library of Congress U.S. Reports scan
        v, pg = f"{int(m.group(1)):03d}", f"{int(m.group(2)):03d}"
        url = f"https://tile.loc.gov/storage-services/service/ll/usrep/usrep{v}/usrep{v}{pg}/usrep{v}{pg}.pdf"
        try:
            _, ctype, _ = get(url, binary=True, timeout=60)
            if "pdf" in ctype.lower():
                return url, "loc:usrep", "Oyez has no match; Library of Congress U.S. Reports PDF"
            return None, "none", "LoC did not return a PDF"
        except Exception as e:
            return None, "none", f"no Oyez match, LoC check failed: {e}"
    return None, "none", "no citation and no Oyez name match"


def link_statute(title, source):
    s = source or ""
    pl = re.search(r"Pub\. L\. (\d+)-(\d+)", s)
    st = re.search(r"(\d+) Stat\. (\d+)", s)
    kw = words(title)
    tries = []
    if pl and int(pl.group(1)) >= 104:
        tries.append((f"https://www.govinfo.gov/link/plaw/{pl.group(1)}/public/{pl.group(2)}?link-type=pdf", "govinfo:plaw"))
    if st:
        tries.append((f"https://www.govinfo.gov/link/statute/{st.group(1)}/{st.group(2)}", "govinfo:statute"))
    elif pl and f"{pl.group(1)}-{pl.group(2)}" in STAT_HINTS:
        v, p = STAT_HINTS[f"{pl.group(1)}-{pl.group(2)}"]
        tries.append((f"https://www.govinfo.gov/link/statute/{v}/{p}", "govinfo:statute (page from hint)"))
    for url, how in tries:
        try:
            text = pdf_text(url)
        except Exception as e:
            continue
        if text is None:
            return url, how, "fetched but not content-checked (pypdf not installed)", False
        flat = re.sub(r"[\u2010-\u2015\u2212]", "-", re.sub(r"\s+", " ", text or ""))
        if pl and re.search(rf"public law {pl.group(1)}-{pl.group(2)}\b", flat):
            return url, how, f"PDF header names Public Law {pl.group(1)}-{pl.group(2)}", True
        if text and any(w in text for w in kw[:4]):
            return url, how, "PDF text contains: " + ", ".join(w for w in kw[:4] if w in text), True
    return None, "none", "no govinfo page that names the act", False


def main(apply):
    wb = openpyxl.load_workbook(MATRIX)
    ws = wb["Objects"]
    hdr = [c.value for c in ws[1]]
    assert hdr[14] == "Source URL", hdr
    out = []
    for i in range(2, ws.max_row + 1):
        g = lambda c: ws.cell(i, c).value
        title, author, src, year = str(g(6) or ""), str(g(7) or ""), str(g(10) or ""), str(g(2) or "")
        if g(15):
            continue
        is_case = re.search(r"\d+ U\.S\. \d+", src) or override_cite(title) or (("SCOTUS" in author or "SCOTUS" in title)
                                                  and re.search(r"\b(v\.?|vs\.?|versus|cases)\b", title.lower()))
        is_stat = (not is_case) and re.search(r"Stat\.|Pub\. L\.", src)
        if not (is_case or is_stat):
            continue
        if is_case:
            url, how, note = link_case(year, title, src); ok = bool(url)
        else:
            url, how, note, ok = link_statute(title, src)
        out.append({"row": i, "year": year, "title": title, "source": src, "url": url, "method": how, "verified": ok, "note": note})
        if apply and url and ok:
            ws.cell(i, 15).value = url
        time.sleep(0.2)
    REPORT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if apply:
        wb.save(MATRIX)
    good = [o for o in out if o["url"] and o["verified"]]
    print(f"{len(out)} candidates, {len(good)} linked and verified, {len(out) - len(good)} not")
    for o in out:
        flag = "OK " if (o["url"] and o["verified"]) else "-- "
        print(flag, o["year"], o["title"][:44].ljust(44), o["method"].ljust(24), (o["url"] or "")[:70])


if __name__ == "__main__":
    main("--apply" in sys.argv)
