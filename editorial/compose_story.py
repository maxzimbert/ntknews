#!/usr/bin/env python3
"""
Compose each story's own Backstory page from the shared library (T-0110). No web search.

The category is the library and the grouping; the page belongs to the story. For each story in the draft:
"We are here" (the pairing line), "It starts in" (the retrieved origin unless the editor nudged it), three
to six Beginnings before it, each with a line written for this story, and the case (the Beginnings'
objects plus up to two later ones). When the library cannot give the story three Beginnings that truly
connect, the page says so and names what is missing, rather than stretching an unrelated document to fill.
That is T-0111's cue to research; this script never searches.

The library: every matrix object with a live link, every approved candidate, and every object a category
already holds (including what earlier searches found and the checks kept), so a find made for one
category serves every story.

The editor's edits arrive on each story as `bs_edits` (from Pulse) and win over the model:
  off      [object_id]   not for this story; never chosen again for it
  lines    {object_id: text}   the editor's own line for a Beginning
  here     text          the editor's own "We are here"
  nudge    {here|starts|beginnings: text}   a note in the editor's words for that section's next run
and `bs_rejected` (top level) lists objects rejected everywhere.

  python3 editorial/compose_story.py --draft ntk-pulse/data/backstory-draft.json --lineup L [--only k1,k2] [--mock]

Writes `composed` onto each story of the draft, in place. Stdlib only.
"""
import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as C  # noqa: E402
import visual_story as V  # noqa: E402
import research_story as R  # noqa: E402
from build_pairings import parse_json_loose, strip_html, API_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "ntk-pulse" / "data" / "backstory-pool.json"
BACKSTORY = ROOT / "digest" / "data" / "backstory.json"
PROVISIONAL = ROOT / "ntk-pulse" / "data" / "provisional-rows.json"
MODEL = "claude-sonnet-5-5"
LIVE = ("live", "live-pdf")
STOP = set("the a an and or of to in on for by with from at as is was were be been are that this it its into "
           "than then over after before about their his her they them he she we our you your not no but who "
           "what when where which while has have had will would can could may might more most new says said "
           "also one two three year years".split())


def log(msg):
    print(msg, file=sys.stderr)


def toks(t):
    return [w for w in re.findall(r"[a-z][a-z'-]{2,}", str(t or "").lower()) if w not in STOP]


# --- the library -------------------------------------------------------------------------------------

def add_find(lib, f, origin):
    """A searched-and-checked document (a category's, or the research ledger's) as a library document."""
    if f.get("id") in lib:
        lib[f["id"]]["categories"].add(origin)
        return
    if not f.get("url"):
        return
    lib[f["id"]] = {"id": f["id"], "title": f.get("title", ""), "author": f.get("author", ""),
                    "year": str(f.get("year", "")), "url": f["url"], "about": f.get("about", ""),
                    "why": f.get("line", ""), "row": origin, "subgenre": "", "lenses": [],
                    "kind": "found", "evidence": f.get("evidence_quote", ""),
                    "source_kind": f.get("source_kind") or C.source_kind(f["url"]), "categories": {origin}}


def load_library(pool_path, bs_path, prov_path, ledger=None):
    lib = {}
    for o in json.loads(Path(pool_path).read_text())["objects"]:
        ok = o.get("url") and o.get("link_status") in LIVE and (o.get("pool") == "matrix" or o.get("approved"))
        if ok:
            lib[o["id"]] = {"id": o["id"], "title": o.get("title", ""), "author": o.get("author", ""),
                            "year": str(o.get("year", "")), "url": o["url"], "about": o.get("about", ""),
                            "why": o.get("why", ""), "row": o.get("row", ""), "subgenre": o.get("subgenre", ""),
                            "lenses": o.get("lenses") or [], "kind": "matrix" if o.get("pool") == "matrix" else "candidate",
                            "categories": set()}
    bs = json.loads(Path(bs_path).read_text())
    for r in bs.get("rows", []):
        for o in r.get("objects") or []:
            oid = o.get("object_id")
            if not oid:
                continue
            e = lib.get(oid)
            if e is None and o.get("source_url"):
                e = lib[oid] = {"id": oid, "title": o.get("title", ""), "author": o.get("author", ""),
                                "year": str(o.get("year", "")), "url": o["source_url"], "about": "", "why": "",
                                "row": r.get("title", ""), "subgenre": "", "lenses": [], "kind": "category",
                                "source_kind": o.get("source_kind"), "categories": set()}
            if e is not None:
                e["about"] = e["about"] or o.get("about", "")
                e["categories"].add(r.get("title", ""))
    if Path(prov_path).exists():
        for r in json.loads(Path(prov_path).read_text()).get("rows", []):
            for cu in r.get("custom_objects") or []:
                if cu.get("id") in lib or not cu.get("url"):
                    if cu.get("id") in lib:
                        lib[cu["id"]]["categories"].add(r.get("title", ""))
                    continue
                add_find(lib, cu, r.get("title", ""))
    for f in (ledger or {}).get("finds", []):   # T-0111: what research found for any story serves every story
        if f.get("id") not in set((ledger or {}).get("rejected", [])):
            add_find(lib, f, "research: " + str(f.get("researched_for", ""))[:60])
    return lib


def shortlist(lib, story, row_title, terms, k=45):
    """The objects worth showing the model for this story. Mostly by `terms`, the history the story belongs
    to as named by a small model (laws, cases, events, institutions): a story's own words alone pulled the
    1918 Fourteen Points speech for an Ohio poll that moved six points. Then rare words shared with the
    headline, and everything already in the story's category."""
    fields = {i: {"title": o["title"].lower(), "about": (o["about"] + " " + o["why"]).lower(),
                  "meta": " ".join([o["author"], o["row"], o["subgenre"], " ".join(o["lenses"]),
                                    " ".join(o["categories"])]).lower()} for i, o in lib.items()}
    docs = {i: toks(" ".join(f.values())) for i, f in fields.items()}
    df = Counter(w for ws in docs.values() for w in set(ws))
    n = len(docs) or 1
    idf = {w: math.log(n / (1 + c)) for w, c in df.items()}
    head = Counter(toks(story["headline"] + " " + story.get("lede", "")))
    terms = [t.lower().strip() for t in terms if t and t.strip()]
    scored = []
    for i, f in fields.items():
        s = 0.0
        for t in terms:
            if t in f["title"]:
                s += 12
            elif t in f["about"]:
                s += 7
            elif t in f["meta"]:
                s += 4
            else:
                tw = toks(t)
                hit = [w for w in tw if w in docs[i]]
                if tw and len(hit) == len(tw):
                    s += sum(idf.get(w, 0) for w in hit)
        s += 0.5 * sum(idf.get(w, 0) * min(head[w], 2) for w in set(docs[i]) if w in toks(f["title"]))
        if row_title and row_title in lib[i]["categories"]:
            s += 6
        if s > 0:
            scored.append((s, i))
    scored.sort(reverse=True)
    return [i for _, i in scored[:k]]


TERMS_MODEL = "claude-haiku-5-5"


def terms_for(api_key, story, row_title):
    """8 to 14 names for the history behind the story, to search the library with. Haiku, no tools."""
    p = f"""A news story needs its history: the long argument it belongs to. Name that history as 8 to 14 short search terms for a library of primary documents (laws, court cases, treaties, speeches, reports): the specific acts, cases, institutions, events and general subjects a historian would look up. Use the common names ("Citizens United", "campaign finance", "Federal Election Campaign Act", "Knesset", "coalition government"). Not the story's own people or numbers.

STORY: {story['headline']}
SUMMARY: {story.get('lede') or ''}
FILED UNDER: {row_title or '(none)'}
DETAIL: {story.get('truths', '')[:1500]}

JSON only: {{"terms":["..."]}}"""
    body = {"model": TERMS_MODEL, "max_tokens": 400, "messages": [{"role": "user", "content": p}],
            "thinking": {"type": "disabled"}}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    u = data.get("usage") or {}
    return (parse_json_loose(text, TERMS_MODEL).get("terms") or [])[:14], \
        {"input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}


# --- the model ---------------------------------------------------------------------------------------

def call(api_key, prompt, max_tokens=3000):
    body = {"model": MODEL, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}],
            "thinking": {"type": "between_tools"}}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{MODEL} HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from None
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    u = data.get("usage") or {}
    return parse_json_loose(text, MODEL), {"input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0)}


def prompt_for(story, origin, row_title, cands, lib, edits, origin_ok=True):
    nudge = edits.get("nudge") or {}
    keep = [i for i in (edits.get("keep") or []) if i in lib]
    lines = [f"- {i} | {lib[i]['year']} | {lib[i]['title'][:110]} | {lib[i]['author'][:50]}"
             + (f" | {(lib[i]['about'] or lib[i]['why'])[:220]}" if (lib[i]['about'] or lib[i]['why']) else "")
             for i in cands]
    starts = f"{origin.get('year')}: {origin.get('line')}" if origin_ok else \
        "(none found: you choose it, see step 5)"
    return f"""You compose one news story's Backstory page for NTK News. The reader is a college-educated adult at an Advanced Placement history level: precise and plain. The page shows how we got to today's story, as dated milestones, each defended by a primary document the reader can open.

STORY: {story['headline']}
SUMMARY: {story.get('lede') or ''}
WHAT IS TRUE (from the story):
{story.get('truths', '')[:3500]}

FILED UNDER: {row_title or '(no category)'}
"IT STARTS IN", FOUND BY RETRIEVAL: {starts}

DOCUMENTS IN THE LIBRARY (id | year | title | author | what it is):
{chr(10).join(lines) or '(none)'}

Do this:
1. Decide the SCOPE: the history this story actually belongs to, in two to six plain words. Not the category name unless it fits; not a verdict ("corruption"), a subject ("Private money and the presidency").
2. Choose 3 to 6 BEGINNINGS from the library: documents a reader needs, in order, to see how this story came to be. Dated before "It starts in" (the same year is allowed). Spread across time. Only documents that truly connect to THIS story's scope. A milestone is public history: a law, ruling, treaty, official act, public statement or public event. Never a private person's court file, family or personal records, even when the story mentions them. If fewer than 3 truly connect, choose only those, and set "thin" to the subject the library is missing and what kind of milestones would be needed. Never stretch an unrelated document to fill.
3. For each Beginning write one sentence (12 to 26 words) saying what happened, in the past tense, using only facts in its line above. No dashes. No numbers that are not in its line. Do not say "this document".
4. Choose up to 2 LATER documents (after "It starts in", before today) that belong in the case, if any truly connect.
5. "starts_object": {'normally null, keeping the retrieved "It starts in". Only if the editor note below asks for it, the id of the Beginning that should be the start instead.' if origin_ok else 'no "It starts in" was found, so give the id of the Beginning where this story starts: the most recent turn that set up today, not today itself.'}
{('EDITOR PICKS, which must be used (as Beginnings when dated before "It starts in", otherwise as LATER documents): ' + ', '.join(keep)) if keep else ''}
{('EDITOR NOTE ON BEGINNINGS: ' + nudge['beginnings']) if nudge.get('beginnings') else ''}
{('THE EDITOR POINTED THIS HISTORY AT: ' + edits['research_direction'] + '. Comparable cases in the library that fit this direction belong among the Beginnings, even though they happened elsewhere.') if edits.get('research_direction') else ''}
{('EDITOR NOTE ON IT STARTS IN: ' + nudge['starts']) if nudge.get('starts') else ''}

JSON only: {{"scope":"...","beginnings":[{{"id":"...","line":"..."}}],"later":["id"],"starts_object":null,"thin":null or "what is missing","why":"one sentence on the choices"}}"""


def here_prompt(story, line, note):
    return f"""Rewrite this one-line Backstory pairing for NTK News. The reader is a college-educated adult. One or two plain sentences, 12 to 30 words, no dashes, no numbers not in the story, take no side.

STORY: {story['headline']}
WHAT IS TRUE: {story.get('truths', '')[:1500]}
CURRENT LINE: {line}
EDITOR'S NOTE: {note}

JSON only: {{"line":"..."}}"""


# --- composing one story -----------------------------------------------------------------------------

def compose(api_key, story, pairing, row, lib, edits, rejected, mock=False, known=(), ledger=None, search_visual=False):
    origin = (pairing or {}).get("origin") or {}
    # A fallback origin is the category's own start line, or a bare year with no line (the Ohio ad drew "2026"
    # and nothing; the South Carolina race drew a 1977 line about gun owners): the composer chooses instead.
    origin_ok = origin.get("status") == "retrieved" and bool(origin.get("line")) and str(origin.get("year", "")).isdigit()
    oy = int(origin["year"]) if origin_ok else 9999
    off = set(edits.get("off") or []) | set(rejected)
    keep = [i for i in (edits.get("keep") or []) if i in lib and i not in off]
    notes, usage = [], {"input_tokens": 0, "output_tokens": 0}
    if mock:
        terms = toks(story["headline"])
    else:
        terms, u = terms_for(api_key, story, (row or {}).get("title"))
        usage = {k: usage[k] + u[k] for k in usage}
    cands = keep + [i for i in shortlist(lib, story, (row or {}).get("title"), terms) if i not in off and i not in keep]
    if mock:
        early = sorted([i for i in cands if lib[i]["year"][:4].isdigit() and int(lib[i]["year"][:4]) <= oy],
                       key=lambda i: lib[i]["year"])[-4:]
        r = {"scope": (row or {}).get("title") or "mock scope", "later": [], "starts_object": None, "thin": None,
             "beginnings": [{"id": i, "line": f"{lib[i]['title']} was written."} for i in early], "why": "mock"}
    else:
        r, u = call(api_key, prompt_for(story, origin, (row or {}).get("title"), cands, lib, edits, origin_ok))
        usage = {k: usage[k] + u[k] for k in usage}
    begs = []
    for b in r.get("beginnings") or []:
        i = b.get("id")
        if i not in cands:
            notes.append(f"{i!r} is not in the shortlist; dropped")
            continue
        o = lib[i]
        y = int(o["year"][:4]) if o["year"][:4].isdigit() else None
        if y is None or y > oy:
            notes.append(f"{o['title'][:40]!r} ({o['year']}) is after It starts in ({oy}); dropped")
            continue
        line = (edits.get("lines") or {}).get(i) or b.get("line", "")
        by = "editor" if (edits.get("lines") or {}).get(i) else "model"
        probs = [] if by == "editor" else C.text_problems("line", line, 8, 30)
        if by == "model" and not C.numbers_ok(line, o["title"], o["year"], o["about"], o["why"], o.get("evidence", "")):
            probs.append("a number in the line is not in the document's record")
        if probs:
            notes.append(f"{o['title'][:40]!r}: {'; '.join(probs)}; dropped")
            continue
        begs.append({"object_id": i, "year": o["year"][:4], "line": line, "by": by})
    begs.sort(key=lambda b: b["year"])
    chosen = {b["object_id"] for b in begs}
    later = [i for i in (r.get("later") or [])[:2] if i in cands and i not in chosen]
    later += [i for i in keep if i not in chosen and i not in later]   # the editor's picks always reach the case
    case = [{"object_id": i, "year": lib[i]["year"][:4], "title": lib[i]["title"], "author": lib[i]["author"],
             "source_url": lib[i]["url"], "about": lib[i]["about"], "kind": lib[i]["kind"],
             **({"source_kind": "news"} if lib[i].get("source_kind") == "news" else {})}
            for i in [b["object_id"] for b in begs] + later]
    starts = {"year": origin.get("year"), "line": origin.get("line"), "from": "retrieval"} if origin_ok else None
    so = r.get("starts_object")
    if so and so in chosen:
        b = next(b for b in begs if b["object_id"] == so)
        starts = {"year": b["year"], "line": b["line"], "object_id": so, "from": "editor nudge" if origin_ok else "composer"}
    if starts and starts.get("from") == "composer" and str(starts["year"]) >= str(datetime.now(timezone.utc).year):
        starts = None                            # "It starts in" is never the last 45 days; a year is all we have
    if not starts and not origin_ok and begs:    # never an empty "It starts in": the latest Beginning before this year
        prior = [b for b in begs if b["year"] < str(datetime.now(timezone.utc).year)]
        if prior:
            b = prior[-1]
            starts = {"year": b["year"], "line": b["line"], "object_id": b["object_id"], "from": "composer"}
    here = edits.get("here") or (pairing or {}).get("line") or ""
    here_by = "editor" if edits.get("here") else "pairing"
    note = (edits.get("nudge") or {}).get("here")
    if note and not edits.get("here") and not mock:
        h, u = call(api_key, here_prompt(story, here, note), 400)
        usage = {k: usage[k] + u[k] for k in usage}
        if h.get("line") and not C.text_problems("line", h["line"], 8, 32):
            here, here_by = h["line"], "model, nudged"
        else:
            notes.append("the nudged We are here line failed the checks; kept the old one")
    thin = r.get("thin") or (None if len(begs) >= 3 else f"only {len(begs)} Beginning(s) connect")
    scope = r.get("scope") or ""
    # T-0112: the chart. The editor's own series or "no chart" wins; a search only when the editor asked for one.
    vnote = (edits.get("nudge") or {}).get("visual")
    visual = V.from_editor(edits["visual"]) if edits.get("visual") else None
    if edits.get("visual") and visual is None:
        notes.append("your chart is missing a field (measure, both figures, years, source and link); not drawn")
    if visual is None and not mock and search_visual:
        prev = edits.get("_prev_visual") or {}
        visual, entry, vn = V.search(api_key, story, scope, prev.get("label"), vnote)
        notes.append("chart search: " + vn)
        if entry is not None and ledger is not None:
            ledger["series"].append(entry)
    if visual is None and not mock:
        visual, u = V.propose(lambda p: call(api_key, p, 600), story, scope, list(known), vnote)
        usage = {k: usage[k] + u[k] for k in usage}
    if visual is None:
        visual = {"status": "none", "why": "mock run", "values": []}
    return {"scope": scope, "visual": visual, "here": here, "here_by": here_by, "starts": starts,
            "beginnings": begs, "case": case, "thin": thin, "why": r.get("why", ""),
            "terms": terms, "shortlist": len(cands), "notes": notes, "usage": usage, "model": None if mock else MODEL}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--lineup", required=True)
    ap.add_argument("--only", default="", help="comma-separated story keys; others keep their page")
    ap.add_argument("--pool", default=str(POOL))
    ap.add_argument("--backstory", default=str(BACKSTORY), help="rows to draw category objects from")
    ap.add_argument("--provisional", default=str(PROVISIONAL))
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--ledger", default=str(V.LEDGER), help="research ledger: checked series and searched subjects (T-0111, T-0112)")
    args = ap.parse_args()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.mock:
        sys.exit("ANTHROPIC_API_KEY not set (use --mock to test the plumbing)")
    draft = json.loads(Path(args.draft).read_text())
    lineup = json.loads(Path(args.lineup).read_text())
    by_key = {s["key"]: s for s in lineup.get("stories", [])}
    rejected = lineup.get("bs_rejected") or []
    ledger = V.load_ledger(args.ledger)
    n_series, n_finds, n_rej = len(ledger["series"]), len(ledger["finds"]), len(ledger["rejected"])
    ledger["rejected"] = sorted(set(ledger["rejected"]) | set(rejected))   # a rejection outlives the browser that made it
    rejected = ledger["rejected"]
    lib = load_library(args.pool, args.backstory, args.provisional, ledger)
    research_keys, budget = set(lineup.get("research") or []), R.BUDGET
    directions = lineup.get("research_direction") or {}
    approved_any = False
    rows = json.loads(Path(args.backstory).read_text()).get("rows", []) + [d["row"] for d in draft["stories"] if d.get("row")]
    known = V.known_series(rows, ledger)
    search_visual = set(lineup.get("visual_search") or [])
    for d in draft["stories"]:                   # a category the draft itself made, for a rerun that has no copy of it
        r = d.get("row") or {}
        for o in r.get("objects") or []:
            oid = o.get("object_id")
            if oid and oid not in lib and o.get("source_url"):
                lib[oid] = {"id": oid, "title": o.get("title", ""), "author": o.get("author", ""),
                            "year": str(o.get("year", "")), "url": o["source_url"], "about": o.get("about", ""),
                            "why": "", "row": r.get("title", ""), "subgenre": "", "lenses": [], "kind": "category",
                            "source_kind": o.get("source_kind"), "categories": {r.get("title", "")}}
            elif oid in lib:
                lib[oid]["categories"].add(r.get("title", ""))
    log(f"library: {len(lib)} objects")
    only = set(filter(None, args.only.split(",")))
    total = {"input_tokens": 0, "output_tokens": 0}
    for d in draft["stories"]:
        if only and d["story_id"] not in only:
            continue
        s = by_key.get(d["story_id"])
        if not s or not d.get("pairing"):
            continue
        story = {"headline": s.get("headline", ""), "lede": strip_html(s.get("lede")), "truths": strip_html(s.get("truth"))}
        try:
            edits = dict(s.get("bs_edits") or {}, _prev_visual=(d.get("composed") or {}).get("visual"))
            # T-0111: a vetoed find the editor approved becomes a library document and goes on this page
            ok = list(edits.get("approved") or [])
            for f in R.approve(ledger, set(ok), d["story_id"]):
                add_find(lib, f, "approved by the editor")
                approved_any = True
            edits["keep"] = list(dict.fromkeys(list(edits.get("keep") or []) + [i for i in ok if i in lib]))
            rnote = None
            prev = d.get("composed") or {}
            if d["story_id"] in research_keys and not args.mock:
                if budget <= 0:
                    rnote = f"not researched: this run's limit of {R.BUDGET} research calls is spent"
                else:
                    added, rnote = R.research(api_key, story, prev.get("scope") or (d.get("row") or {}).get("title", ""),
                                              prev.get("thin"), [{"year": b["year"], "title": b.get("line", "")} for b in prev.get("beginnings") or []],
                                              ledger, rejected, direction=(directions.get(d["story_id"]) or "").strip() or None,
                                              story_id=d["story_id"])
                    if not rnote.startswith("already"):
                        budget -= 1
                    for f in added:
                        add_find(lib, f, "research: " + f.get("researched_for", "")[:60])
                log(f"  {d['story_id']}: {rnote}")
            c = compose(api_key, story, d["pairing"], d.get("row"), lib, edits, rejected, args.mock,
                        known, ledger, d["story_id"] in search_visual)
        except Exception as e:  # noqa: BLE001 - one story's failure must not cost the others their page
            log(f"  {d['story_id']}: compose failed ({e})")
            d["composed"] = {"error": str(e)[:300]}
            continue
        # what the checks turned down for this story, for the editor to approve or leave
        c["vetoed"] = [{k: v.get(k) for k in ("id", "year", "title", "author", "source", "url", "line", "relation",
                                              "vetoed_because", "direction")}
                       for v in ledger["vetoed"] if v.get("story_id") == d["story_id"] and v["id"] not in set(rejected)]
        if rnote:
            c["research"] = rnote
        elif prev.get("research"):
            c["research"] = prev["research"]
        d["composed"] = c
        if only:
            d["bs_hash"] = s.get("bs_hash")
            d["bs_text_hash"] = s.get("bs_text_hash")
        total = {k: total[k] + c["usage"][k] for k in total}
        log(f"  {d['story_id']}: {c['scope']!r} {len(c['beginnings'])} Beginnings, {len(c['case'])} in the case"
            + (f", thin: {c['thin']}" if c["thin"] else "") + (f"; {len(c['notes'])} dropped" if c["notes"] else ""))
    draft["compose_usage"] = total
    if (len(ledger["series"]), len(ledger["finds"]), len(ledger["rejected"])) != (n_series, n_finds, n_rej) or research_keys or approved_any:
        V.save_ledger(ledger, args.ledger)
        log(f"ledger: {len(ledger['series']) - n_series} new series, {len(ledger['finds']) - n_finds} new finds, "
            f"{len(ledger['rejected'])} rejected in all")
    draft["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")   # Pulse waits for this to move
    Path(args.draft).write_text(json.dumps(draft, indent=1, ensure_ascii=False) + "\n")
    log(f"composed; tokens in {total['input_tokens']}, out {total['output_tokens']}")


if __name__ == "__main__":
    main()
