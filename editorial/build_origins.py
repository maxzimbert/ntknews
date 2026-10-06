#!/usr/bin/env python3
"""
build_origins.py - find each story's "It starts in YYYY" (T-0074).

Reads the story's full Truths and the row and sub-genre it was paired to, and
finds the proximate origin by retrieval, not memory:

  1. QUERIES   model (Haiku)   Truths + row + sub-genre -> 2-3 Wikipedia queries
  2. RETRIEVE  code            Wikipedia search -> leads, Wikidata dates,
                               Portal:Current_events day page (date check)
  3. CHOOSE    model (Sonnet)  picks among the retrieved candidates only
  4. VALIDATE  code            year, quote and numbers must be in the lead; an
                               origin that fails falls back to the row's own
                               start_line and is marked so the editor sees it.
                               A story's past is read from its Truths; the row
                               is only a hint and its fit is rated separately.

Wikipedia is used to find and date the event. It is never a link shown to the
reader. Nothing here is verified; every origin carries "verified": false.

  ANTHROPIC_API_KEY=... python3 editorial/build_origins.py            # real run
  python3 editorial/build_origins.py --queries q.json --choices c.json # replay

Model steps can be supplied as files (--queries / --choices) so a run can be
replayed or hand-checked without spending anything. Without a key and without
the files, the script writes what each model step would be sent and exits.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pairings import call_claude, read_system_prompt, strip_html  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BACKSTORY = ROOT / "digest" / "data" / "backstory.json"
LINEUP = ROOT / "ntk-pulse" / "data" / "lineup-publish.json"
OUT = ROOT / "editorial" / "origins.json"

QUERY_MODEL = "claude-haiku-4-5-20251001"
CHOOSE_MODEL = "claude-sonnet-5"
UA = "ntknews-origins/1.0 (https://ntknews.org; editorial research)"
WIKI = "https://en.wikipedia.org/w/api.php"
MAX_CANDIDATES = 12


def log(msg):
    print(msg, file=sys.stderr)


def get_json(url, params):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


# --- retrieval ---------------------------------------------------------------

def wiki_search(q, n=5):
    d = get_json(WIKI, {"action": "query", "list": "search", "srsearch": q,
                        "srlimit": n, "format": "json"})
    return [h["title"] for h in d.get("query", {}).get("search", [])]


def wiki_leads(titles):
    """title -> {title, url, lead, qid}. One call; redirects are followed."""
    out = {}
    for i in range(0, len(titles), 8):
        d = get_json(WIKI, {"action": "query", "prop": "extracts|info|pageprops",
                            "exintro": 1, "explaintext": 1, "exlimit": "max",
                            "inprop": "url", "ppprop": "wikibase_item",
                            "titles": "|".join(titles[i:i + 8]), "redirects": 1,
                            "format": "json"})
        for p in d.get("query", {}).get("pages", {}).values():
            if "missing" in p or not p.get("extract"):
                continue
            out[p["title"]] = {"title": p["title"], "url": p.get("fullurl"),
                               "lead": re.sub(r"\s+", " ", p["extract"]).strip()[:1800],
                               "qid": (p.get("pageprops") or {}).get("wikibase_item")}
    # A short lead (a pending case, a stub) rarely states the origin. Read further
    # into the article so the origin can be quoted from text we retrieved.
    for t, c in out.items():
        if len(c["lead"]) < 500:
            d = get_json(WIKI, {"action": "query", "prop": "extracts", "explaintext": 1,
                                "exchars": 3500, "titles": t, "redirects": 1, "format": "json"})
            for p in d.get("query", {}).get("pages", {}).values():
                if p.get("extract"):
                    c["lead"] = re.sub(r"\s+", " ", p["extract"]).strip()
    return out


def wikidata_dates(qids):
    """qid -> ISO date of start time (P580), point in time (P585) or inception (P571)."""
    qids = [q for q in qids if q]
    if not qids:
        return {}
    d = get_json("https://www.wikidata.org/w/api.php",
                 {"action": "wbgetentities", "ids": "|".join(qids), "props": "claims",
                  "format": "json"})
    out = {}
    for qid, ent in (d.get("entities") or {}).items():
        for prop in ("P580", "P585", "P571"):
            for c in (ent.get("claims") or {}).get(prop, []):
                v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
                m = re.match(r"\+(\d{4})-(\d\d)-(\d\d)", v.get("time", ""))
                if m:
                    prec = v.get("precision", 0)
                    y, mo, da = m.groups()
                    out[qid] = {"year": int(y), "iso": f"{y}-{mo}-{da}" if prec >= 11 else None}
                    break
            if qid in out:
                break
    return out


def portal_check(iso, title):
    """Read the Portal:Current_events day page for iso and see whether an entry
    links to `title`. Returns {date, matched, entry} or None if the page is unreadable."""
    if not iso:
        return None
    dt = datetime.strptime(iso, "%Y-%m-%d")
    page = f"Portal:Current events/{dt.year} {dt.strftime('%B')} {dt.day}"
    try:
        d = get_json(WIKI, {"action": "parse", "page": page, "prop": "text",
                            "disabletoc": 1, "format": "json"})
    except Exception:
        return None
    html = (d.get("parse") or {}).get("text", {}).get("*")
    if not html:
        return None
    want = urllib.parse.unquote(title.replace(" ", "_")).lower()
    toks = [w.lower() for w in re.findall(r"[A-Za-z]{5,}", title)]
    need = max(1, (len(toks) + 1) // 2)
    keyword = None
    for li in re.findall(r"<li>(.*?)</li>", html, re.S):
        hrefs = [urllib.parse.unquote(h).lower() for h in re.findall(r'href="/wiki/([^"#]+)', li)]
        text = strip_html(li)
        if want in hrefs:
            return {"date": iso, "matched": "link", "entry": text[:400]}
        if keyword is None and toks and sum(t in text.lower() for t in toks) >= need:
            keyword = text[:400]
    if keyword:
        return {"date": iso, "matched": "keywords", "entry": keyword}
    return {"date": iso, "matched": None, "entry": None}


def retrieve(queries):
    titles = []
    for q in queries:
        for t in wiki_search(q):
            if t not in titles:
                titles.append(t)
    leads = wiki_leads(titles[:MAX_CANDIDATES + 4])
    dates = wikidata_dates([c["qid"] for c in leads.values()])
    cands = []
    for t in titles:
        c = leads.get(t)
        if not c:
            continue
        wd = dates.get(c["qid"]) or {}
        years = sorted({int(y) for y in re.findall(r"\b(1[89]\d\d|20[0-3]\d)\b", c["lead"])})
        cands.append({**c, "wikidata_year": wd.get("year"), "wikidata_date": wd.get("iso"),
                      "years_in_lead": years})
        if len(cands) == MAX_CANDIDATES:
            break
    return cands


# --- model steps ---------------------------------------------------------------

def lineage(row):
    return "; ".join(f"{o['year']} {o['title']}" for o in (row.get("objects") or [])[:7])


def story_block(s, row):
    return (f"STORY {s['story_id']}: {s['headline']}\n"
            f"TRUTHS:\n{s['truths']}\n\n"
            f"ROW HINT (may be wrong): {row['title']}, starts {str(row['start_date'])[:4]}. "
            f"CONTEST: {row.get('milestone')}\n"
            f"SUB-GENRE: {s.get('subgenre') or '(editor-tagged row, no sub-genre)'}\n"
            f"ROW LINEAGE (context only): {lineage(row)}")


def choose_block(s, row, cands):
    cs = "\n\n".join(
        f"[{i + 1}] TITLE: {c['title']}\n  WIKIDATA DATE: {c['wikidata_date'] or c['wikidata_year'] or 'none'}\n"
        f"  LEAD: {c['lead']}" for i, c in enumerate(cands))
    return story_block(s, row) + "\n\nCANDIDATES\n" + (cs or "(none retrieved)")


# --- validation ------------------------------------------------------------------

def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def validate(s, row, cands, ch):
    """Return (ok, problems, candidate). Hard problems send the story to fallback."""
    p = []
    if not ch or not ch.get("choice"):
        return False, [f"no origin chosen: {(ch or {}).get('why', 'no answer')}"], None
    cand = next((c for c in cands if c["title"] == ch["choice"]), None)
    if not cand:
        return False, ["chosen title was not among the retrieved candidates"], None
    if ch.get("fit") not in ("direct", "inferred"):
        p.append("model found no origin among the candidates")
    y, line = ch.get("year"), ch.get("line") or ""
    lead, truths = norm(cand["lead"]), norm(s.get("truths"))
    q = norm(ch.get("evidence_quote"))
    # Evidence is a verbatim quote from the retrieved article, or from the story's own
    # Truths when they state the origin themselves (the Truths are cited reporting).
    src = "lead" if q and q in lead else "truths" if q and q in truths else None
    text = cand["lead"] if src == "lead" else s.get("truths") or ""
    if not src:
        p.append("evidence quote is not verbatim in the lead or the Truths")
    elif str(y) not in q:
        p.append("evidence quote does not contain the year")
    if not isinstance(y, int):
        p.append(f"year {y} is not an integer")
    elif src == "lead" and not (y in cand["years_in_lead"] or y == cand["wikidata_year"]):
        p.append(f"year {y} is not stated in the chosen lead")
    sy = int(str(s.get("story_year") or datetime.now(timezone.utc).year))
    if isinstance(y, int) and y > sy:
        p.append("origin is later than the story")
    n = len(line.split())
    if not (12 <= n <= 30):
        p.append(f"line is {n} words, wants 12 to 30")
    if not line.startswith("When "):
        p.append('line does not start with "When"')
    if re.search(r"[\u2014\u2013]| -- ", line):
        p.append("line has a dash")
    pool = cand["lead"] + " " + (s.get("truths") or "")
    for num in re.findall(r"\d[\d,.]*", line):
        if num.strip(",.") not in pool:
            p.append(f"number {num} in the line is not in the lead or the Truths")
    ch["_evidence_source"] = src
    return not p, p, cand


def fallback(row, why):
    return {"status": "fallback", "year": int(str(row["start_date"])[:4]),
            "line": row.get("start_line"), "why_fallback": why, "verified": False}


# --- main ---------------------------------------------------------------------------

def load_stories(lineup_path, pairings_path):
    lp = json.loads(Path(lineup_path).read_text())
    bs = json.loads(Path(pairings_path).read_text())
    pairs = {p["story_id"]: p for p in bs.get("todays_pairings", [])}
    stories = []
    for st in lp.get("stories", []):
        p = pairs.get(st["key"])
        if not p:
            continue
        stories.append({"story_id": st["key"], "headline": st["headline"],
                        "row": p["row"], "subgenre": p.get("subgenre"),
                        "truths": strip_html(st.get("truth")),
                        "story_year": (bs.get("pairings_generated") or "")[:4] or None})
    return stories, {r["id"]: r for r in bs["rows"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lineup", default=str(LINEUP))
    ap.add_argument("--pairings", default=str(BACKSTORY))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--queries", help="JSON list from step 1, instead of calling the model")
    ap.add_argument("--choices", help="JSON list from step 3, instead of calling the model")
    ap.add_argument("--reuse", action="store_true",
                    help="reuse the retrieval saved beside --out (search results drift between runs)")
    ap.add_argument("--apply", action="store_true",
                    help="write each origin onto its pairing in digest/data/backstory.json")
    args = ap.parse_args()

    stories, rows = load_stories(args.lineup, args.pairings)
    if not stories:
        sys.exit("no stories with a pairing")
    key = os.environ.get("ANTHROPIC_API_KEY")
    log(f"{len(stories)} stories")

    # 1 QUERIES
    if args.queries:
        qs = json.loads(Path(args.queries).read_text())
    elif key:
        sysq = read_system_prompt("origin-queries.md")
        qs = [call_claude(key, QUERY_MODEL, sysq, story_block(s, rows[s["row"]]), 600)
              for s in stories]
    else:
        sys.exit("no ANTHROPIC_API_KEY and no --queries file; step 1 cannot run")
    qby = {q["story_id"]: q for q in qs}

    # 2 RETRIEVE
    cache = Path(args.out).with_name("origins-cache.json")
    if args.reuse and cache.exists():
        retrieved = json.loads(cache.read_text())
        log(f"reusing retrieval from {cache.name}")
    else:
        retrieved = {}
        for s in stories:
            q = qby.get(s["story_id"], {}).get("queries") or []
            retrieved[s["story_id"]] = retrieve(q) if q else []
            log(f"  {s['story_id']}: {len(q)} queries -> {len(retrieved[s['story_id']])} candidates")
        cache.write_text(json.dumps(retrieved, indent=1, ensure_ascii=False))

    # 3 CHOOSE
    if args.choices:
        cs = json.loads(Path(args.choices).read_text())
    elif key:
        sysc = read_system_prompt("origin-choice.md")
        cs = [call_claude(key, CHOOSE_MODEL, sysc,
                          choose_block(s, rows[s["row"]], retrieved[s["story_id"]]), 800)
              for s in stories]
    else:
        wd = Path(args.out).with_name("origins-retrieved.json")
        wd.write_text(json.dumps({s["story_id"]: {"prompt": choose_block(s, rows[s["row"]], retrieved[s["story_id"]])}
                                  for s in stories}, indent=1, ensure_ascii=False))
        sys.exit(f"no ANTHROPIC_API_KEY and no --choices file; step 3 input written to {wd}"
                 f" (rerun with --reuse so the same candidates are validated)")
    cby = {c["story_id"]: c for c in cs}

    # 4 VALIDATE
    out = []
    for s in stories:
        row, cands = rows[s["row"]], retrieved[s["story_id"]]
        ch = cby.get(s["story_id"])
        ok, problems, cand = validate(s, row, cands, ch)
        entry = {"story_id": s["story_id"], "headline": s["headline"], "row": s["row"],
                 "row_fit": (qby.get(s["story_id"]) or {}).get("row_fit"),
                 "subgenre": s["subgenre"], "origin_event": qby.get(s["story_id"], {}).get("origin_event"),
                 "queries": qby.get(s["story_id"], {}).get("queries"),
                 "candidates": [c["title"] for c in cands]}
        if ok:
            iso = cand["wikidata_date"]
            entry["origin"] = {"status": "retrieved", "year": ch["year"], "line": ch["line"],
                               "title": cand["title"], "url": cand["url"],
                               "evidence_quote": ch["evidence_quote"], "why": ch.get("why"),
                               "fit": ch["fit"], "row_fit": ch.get("row_fit"),
                               "evidence_source": ch.get("_evidence_source"),
                               "before_row_start": ch["year"] < int(str(row["start_date"])[:4]),
                               "portal": portal_check(iso, cand["title"]),
                               "verified": False}
        else:
            entry["origin"] = fallback(row, "; ".join(problems))
            entry["rejected"] = {"choice": (ch or {}).get("choice"), "year": (ch or {}).get("year"),
                                 "line": (ch or {}).get("line")}
        out.append(entry)
        o = entry["origin"]
        log(f"  {o['status'].upper():9} {s['story_id']} {o['year']}  {o.get('line') or ''}"
            + (f"   [{o.get('why_fallback')}]" if o["status"] == "fallback" else ""))

    Path(args.out).write_text(json.dumps(
        {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "origins": out}, indent=1, ensure_ascii=False) + "\n")
    log(f"wrote {args.out}")

    if args.apply:
        bs = json.loads(Path(args.pairings).read_text())
        by = {e["story_id"]: e["origin"] for e in out}
        n = 0
        for p in bs["todays_pairings"]:
            if p["story_id"] in by:
                p["origin"] = by[p["story_id"]]
                n += 1
        Path(args.pairings).write_text(json.dumps(bs, indent=2, ensure_ascii=False) + "\n")
        log(f"applied {n} origins to {args.pairings}")


if __name__ == "__main__":
    main()
