#!/usr/bin/env python3
"""Spine lab: a prototype of Backstory built on two clocks. Not part of the publish path.

Slow clock, once per category: a SPINE, the chronology of the category's argument as event-dated
milestones from its root to the most recent turn, each defended by one primary source that was
fetched and checked, plus one TREND LINE from a published series. Built once, reviewed once by the
editor, reused by every story filed under it.

Fast clock, once per story: place the story in a category, choose its "It starts in" from the spine
(the turn that set today's story in motion), select the Beginnings that lead to it and the steps
since, and have a second call that did not choose them judge the chain.

Why: the publish-time compose (T-0079) asked a model to research a category from nothing for every
misfit story, then cut what failed the checks. Yield swung from five Beginnings to none on the same
stories, and the editor had nothing stable to review. Choosing from a vetted spine is a smaller,
checkable task, and the editor's review is paid once per category, not once per story.

    python3 editorial/spine_lab.py            # writes ntk-pulse/data/spine-lab.json
Runs in .github/workflows/spine-lab.yml on the spine-lab branch (the key is a repo secret).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as C                                    # noqa: E402
from build_pairings import parse_json_loose, strip_html   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ntk-pulse" / "data" / "spine-lab.json"
MODEL = os.environ.get("SPINE_MODEL", "claude-sonnet-5-5")
API = "https://api.anthropic.com/v1/messages"
USAGE = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "web_searches": 0}
LOG = []

STYLE = ("STYLE: written for an Advanced Placement history reader: precise, concrete, plain. Name the actor "
         "and the act. No em dashes or en dashes. Never use: this document, this reflects, underscores, "
         "highlights, serves as, a reminder that, pivotal, landmark, groundbreaking, seminal, watershed. "
         "Take no side.")


def log(m):
    print(m, flush=True)
    LOG.append(m)


# --- the model -------------------------------------------------------------------------------------

def _post(body, timeout):
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")[:300]
            if e.code in (429, 500, 529) and attempt < 2:
                time.sleep(20 * (attempt + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}") from None
    u = d.get("usage") or {}
    USAGE["calls"] += 1
    USAGE["input_tokens"] += u.get("input_tokens", 0)
    USAGE["output_tokens"] += u.get("output_tokens", 0)
    USAGE["web_searches"] += (u.get("server_tool_use") or {}).get("web_search_requests", 0)
    return d


def ask(prompt, max_tokens=4000):
    d = _post({"model": MODEL, "max_tokens": max_tokens, "thinking": {"type": "between_tools"},
               "messages": [{"role": "user", "content": prompt}]}, 240)
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    return parse_json_loose(text, MODEL)


def search(prompt, max_tokens=12000, uses=10):
    """(parsed JSON, urls the search returned or cited)."""
    d = _post({"model": MODEL, "max_tokens": max_tokens, "thinking": {"type": "between_tools"},
               "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": uses}],
               "messages": [{"role": "user", "content": prompt}]}, 600)
    urls, text = set(), ""
    for b in d.get("content", []):
        if b.get("type") == "web_search_tool_result" and isinstance(b.get("content"), list):
            urls |= {x["url"] for x in b["content"] if x.get("url")}
        if b.get("type") == "text":
            text += b.get("text", "")
            urls |= {c["url"] for c in b.get("citations") or [] if c.get("url")}
    return parse_json_loose(text, MODEL), urls


# --- checking a source -----------------------------------------------------------------------------

def check_source(src, urls, pool):
    """Every source carries its check, so the editor sees why it is trusted. Nothing is dropped here:
    a source that fails is shown as failed and not used in a thread unless the editor approves it."""
    if src.get("matrix_id"):
        o = pool.get(src["matrix_id"])
        if not o:
            return dict(src, check="failed", check_note="not a matrix id")
        ok = o.get("link_status") in ("live", "live-pdf", None)
        return dict(src, title=o["title"], author=o.get("author", ""), doc_date=o.get("sort") or o.get("year"),
                    url=o.get("url", ""), check="matrix" if ok else "failed",
                    check_note="in the Object Matrix, link checked by check_links.py" if ok else f"matrix link is {o.get('link_status')}")
    url = str(src.get("url") or "").strip()
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url).lower()
    if not url.startswith("https://"):
        return dict(src, check="failed", check_note="link is not https")
    if any(d in host for d in C.DENY_HOSTS):
        return dict(src, check="failed", check_note=f"{host} is not a primary source")
    if url not in urls:
        return dict(src, check="failed", check_note="the link is not one the search returned")
    status, page = C._fetch(url)
    if status in (401, 403, 429) or status == 0:
        return dict(src, check="unchecked", check_note=f"the site refused the checker ({status or 'no answer'}); open it to confirm")
    if not 200 <= status < 400:
        return dict(src, check="failed", check_note=f"the link answers {status}")
    if not page:
        return dict(src, check="loads", check_note="the link loads (a PDF or script page: the quote could not be tested)")
    if C._quote_on_page(src.get("quote") or "", page):
        return dict(src, check="verified", check_note="the link loads and the quoted sentence is on the page")
    return dict(src, check="failed", check_note="the link loads but the quoted sentence is not on the page")


USABLE = ("verified", "matrix", "loads", "unchecked")       # unchecked is shown amber: the editor confirms it once


# --- inputs ----------------------------------------------------------------------------------------

def load_inputs():
    bs = json.loads((ROOT / "digest/data/backstory.json").read_text())
    lp = json.loads((ROOT / "ntk-pulse/data/lineup-publish.json").read_text())
    pool_doc = json.loads((ROOT / "ntk-pulse/data/backstory-pool.json").read_text())
    spec = json.loads((ROOT / "editorial/lenses.json").read_text())
    pairs = {p["story_id"]: p for p in bs.get("todays_pairings", [])}
    stories = []
    for s in lp["stories"]:
        p = pairs.get(s["key"], {})
        text = " ".join(strip_html(s.get(k) or "") for k in ("truth", "prob", "poss", "lies"))
        o = p.get("origin") or {}
        stories.append({"id": s["key"], "headline": strip_html(s.get("headline") or ""), "lede": strip_html(s.get("lede") or ""),
                        "truths": " ".join(strip_html(s.get("truth") or "").split()), "text": " ".join(text.split()),
                        "line": p.get("line", ""), "permalink": p.get("story_permalink", ""),
                        "prod_row": p.get("row"), "prod_origin": {"year": o.get("year"), "line": o.get("line"), "status": o.get("status"),
                                                                  "title": o.get("title"), "url": o.get("url")}})
    for s in stories:
        bare = re.sub(r"\(\s*[A-Z][^()]{0,80}\)", " ", s["text"])        # "( ABC Australia )" is a citation, not a subject
        s["lenses"] = [l for l in spec if not l.startswith("_") and C.lens_supported(l, spec, bare)]
    rows = [{"id": r["id"], "title": r["title"], "stratum": r.get("stratum"), "contest": r.get("milestone") or r.get("contest") or "",
             "start_date": r.get("start_date"), "start_line": r.get("start_line"), "stakes": r.get("stakes", ""),
             "indicator": r.get("indicator"), "beginnings": r.get("beginnings") or [], "objects": r.get("objects") or [],
             "subgenres": r.get("subgenres") or []} for r in bs["rows"]]
    pool = {o["id"]: o for o in pool_doc["objects"]}
    return stories, rows, pool, spec, pool_doc


# --- 1. placement ----------------------------------------------------------------------------------

def place(stories, rows):
    cats = "\n".join(f"- {r['id']} | {r['title']} | {'a live conflict' if r['stratum'] == 'fire' else 'a long argument' if r['stratum'] == 'held' else 'an editor category'} | {r['contest']}" for r in rows)
    st = "\n\n".join(f"[{i + 1}] id {s['id']}\nHEADLINE: {s['headline']}\nTRUTHS: {s['truths'][:1400]}\nSUBJECT LENSES THE TEXT SUPPORTS: {', '.join(s['lenses']) or '(none)'}"
                     for i, s in enumerate(stories))
    p = f"""You place today's news stories in NTK's Backstory. A category is a history a reader can follow: a live conflict (its own recent history), a long American argument (decades), or a category named for a subject. A story belongs to the category whose history best explains how this story came to be: the subject and the actors at its center, not a theme it shares in passing.

CATEGORIES:
{cats}

STORIES:
{st}

For each story choose one category id, or "new" with a short title (1 to 4 words, named for the subject, like "AI" or "Fuel prices") and a contest line ("Whether X, or Y", 12 to 30 words, two positions a reasonable person holds). Prefer a live conflict when the story is a consequence of it. Two stories about the same subject share a new category: give them the same title.
{STYLE}
JSON only: [{{"story_id":"...","category":"<id or new>","new_title":null,"new_contest":null,"why":"one sentence"}}]"""
    out = ask(p, 3000)
    return {x["story_id"]: x for x in (out if isinstance(out, list) else out.get("stories", []))}


# --- 2. the spine ----------------------------------------------------------------------------------

def matrix_seeds(cat, lenses, pool, spec):
    """Matrix documents a spine may adopt: the row's own objects, and those under the stories' lenses."""
    ids = {o.get("object_id") for o in cat.get("objects") or []} | {b.get("object_id") for b in cat.get("beginnings") or []}
    out = [o for o in pool.values() if o["id"] in ids or set(o.get("lenses") or []) & set(lenses)
           or (cat.get("title") and o.get("row") == cat["title"])]
    out = [o for o in out if o.get("pool") == "matrix" and o.get("link_status") in ("live", "live-pdf", None)]
    out = sorted(out, key=lambda o: o.get("sort") or o.get("year") or "")[-45:]       # the most recent 45
    return out


def build_spine(cat, filed, lenses, pool, spec, today):
    seeds = matrix_seeds(cat, lenses, pool, spec)
    seed_txt = "\n".join(f"- {o['id']} | {o.get('year')} | {o['title'][:110]}" for o in seeds) or "(none)"
    st = "\n\n".join(f"[{i + 1}] {s['headline']}\n{s['truths'][:1800]}" for i, s in enumerate(filed))
    p = f"""You are the researcher for NTK's Backstory, written for college-educated adults at the standard of an Advanced Placement history class. You are building the SPINE of one category: the chronology a reader needs in order to understand today's stories filed under it. The spine is built once, reviewed by the editor, and reused by every later story in the category, so it must be accurate and defensible.

CATEGORY: {cat['title']}
ITS ARGUMENT: {cat.get('contest') or ''}
TODAY: {today}
STORIES FILED UNDER IT TODAY:
{st}

MATRIX DOCUMENTS (primary sources already verified in NTK's library; adopt one by its id when it is the primary source for a milestone you choose):
{seed_txt}

Build 10 to 14 milestones, oldest to newest. First think: what are the events, in order, without which these stories could not have happened? Who acted, what did they decide, what changed? Then:
- Two or three milestones may reach back to the root of the argument. Most should come from the period that set today's stories in motion, and the last should be the most recent turn before today.
- A milestone is an event: a law, ruling, order, treaty, attack, outbreak, filing, election, report or decision. Date it by when the event happened, not by when something was written about it.
- Each milestone is defended by ONE primary source: the document itself (the law, the ruling, the order, the filing, the official statement, the dataset, the agency report), or an archive's, court's, legislature's or government's copy. Not Wikipedia, not a news article or explainer about it, not a retail page. Use web search to find it and give the exact URL you found. Quote one sentence from that page, word for word.
- Every milestone must matter to at least one of today's stories through its subject, its actors or its action. A document that only shares a theme is an analogy and does not belong.
- If you cannot source a milestone, leave it out. Fewer well-sourced milestones are better than padding.
{STYLE}

JSON only:
{{"milestones":[{{"event_date":"YYYY-MM-DD, or YYYY when the day is not known","line":"one sentence of 12 to 30 words saying what happened, actor first","matters_to":[1],"how":"one sentence: what in today's stories this explains","source":{{"matrix_id":null,"title":"the document's exact title","author":"who issued it","doc_date":"YYYY-MM-DD or YYYY","url":"https://...","quote":"one sentence copied word for word from that page"}}}}]}}"""
    try:
        r, urls = search(p, 14000, 12)
    except Exception as e:  # noqa: BLE001
        log(f"  spine search failed for {cat['title']}: {e}")
        return []
    ms = r.get("milestones") if isinstance(r, dict) else r
    out = []
    for m in ms or []:
        src = check_source(m.get("source") or {}, urls, pool)
        d = str(m.get("event_date") or "")
        if not re.match(r"^\d{3,4}", d):
            continue
        out.append({"id": f"m{len(out) + 1}", "event_date": d, "year": int(re.match(r"\d{3,4}", d).group()),
                    "line": " ".join(str(m.get("line") or "").split()), "matters_to": m.get("matters_to") or [],
                    "how": m.get("how") or "", "source": src})
    out.sort(key=lambda m: m["event_date"])
    for i, m in enumerate(out):
        m["id"] = f"m{i + 1}"
    good = sum(m["source"]["check"] in USABLE for m in out)
    log(f"  spine {cat['title']}: {len(out)} milestones, {good} with a usable source; "
        + "; ".join(f"{m['year']} {m['source']['check']}" for m in out))
    return out


def build_indicator(cat, filed):
    st = "; ".join(s["headline"] for s in filed)
    p = f"""Find ONE trend line for a Backstory category page at NTK: a measure a reader can check, from the agency, statistical office or pollster that publishes it, showing how something at the heart of this category has moved over time.

CATEGORY: {cat['title']}
ITS ARGUMENT: {cat.get('contest') or ''}
TODAY'S STORIES: {st}

Prefer a series the publisher updates (EIA, BLS, FRED, CDC, Census, Pew, Gallup, a court or agency dataset) over a one-off study. Give 3 to 8 points from ONE page that states them all, oldest to newest, the last as recent as the page allows. Every value must appear on that page exactly as you give it. Use web search.
JSON only: {{"label":"what is measured, as a reader would say it","unit":"%, $ per gallon, cases, ...","points":[{{"date":"YYYY or YYYY-MM","value":"as printed on the page"}}],"source":"the publisher","source_url":"https://...","quote":"one sentence copied word for word from that page that states at least one of the values","why":"one sentence: why this measure belongs to this category"}}
If no such page exists, answer {{"none":"why"}}."""
    try:
        r, urls = search(p, 6000, 6)
    except Exception as e:  # noqa: BLE001
        return {"none": f"search failed: {e}"}
    if not isinstance(r, dict) or r.get("none") or not r.get("points"):
        return {"none": (r or {}).get("none", "no answer") if isinstance(r, dict) else "no answer"}
    url = str(r.get("source_url") or "")
    if url not in urls:
        return dict(r, check="failed", check_note="the link is not one the search returned")
    status, page = C._fetch(url)
    if not page:
        return dict(r, check="unchecked" if status in (0, 401, 403, 429) else "loads" if 200 <= status < 400 else "failed",
                    check_note=f"the page could not be read as text ({status}); open it to confirm the values")
    norm = lambda t: re.sub(r"\s+", " ", str(t)).strip()
    missing = [p_["value"] for p_ in r["points"] if norm(re.sub(r"[^0-9.]", "", str(p_["value"]))) not in re.sub(r"[^0-9. ]", " ", page)]
    if missing:
        return dict(r, check="failed", check_note=f"values not found on the page: {', '.join(map(str, missing[:4]))}")
    return dict(r, check="verified", check_note="the page loads and every value appears on it")


# --- 3. the thread ---------------------------------------------------------------------------------

def thread(story, cat, spine, today):
    usable = [m for m in spine if m["source"]["check"] in USABLE]
    cutoff = (datetime.fromisoformat(today) - timedelta(days=45)).strftime("%Y-%m-%d")
    lst = "\n".join(f"- {m['id']} | {m['event_date']} | {m['line']}" for m in usable)
    o = story["prod_origin"]
    p = f"""You build one story's Backstory thread at NTK from a category's spine: a chronology of vetted milestones, each with a primary source. You choose; you do not invent.

STORY: {story['headline']}
{story['truths'][:2500]}
TODAY'S LINE (what the story is, already written): {story['line']}
A RETRIEVED ORIGIN, FOR REFERENCE: {o.get('year')}: {o.get('line')}

CATEGORY: {cat['title']}: {cat.get('contest') or ''}
SPINE:
{lst}

TODAY: {today}

1. START ("It starts in YYYY"): choose the ONE milestone that set today's story in motion: the specific, consequential turn without which this story would not exist. It is never today's news itself or the trigger of the last few weeks: it is the earlier decision or event that made today possible, usually months or years back. Only milestones dated before {cutoff} may be the start. Prefer it close enough to explain today over a distant root. Name two runner-ups (also before {cutoff}) and say in a few words why each is weaker.
2. BEGINNINGS: 3 to 5 milestones dated before the start, oldest to newest, that a reader needs in order to see how we got to the start: earlier steps in this story, or earlier cases of the same kind of event that show the pattern. Each must connect to this story's subject, actors or action.
3. SINCE: 0 to 2 milestones after the start and before today: the most recent turns that bring us to today.
4. START LINE: one sentence beginning "When" that says what happened at the start, 12 to 28 words.
{STYLE}
JSON only: {{"start":"m#","start_line":"When ...","runner_ups":[{{"id":"m#","why_weaker":"..."}}],"beginnings":[{{"id":"m#","why":"one sentence naming what in this story it connects to"}}],"since":[{{"id":"m#","why":"..."}}]}}"""
    r = ask(p, 3000)
    ids = {m["id"] for m in usable}
    early = {m["id"] for m in usable if m["event_date"] < cutoff}
    clean = lambda xs: [x for x in xs or [] if isinstance(x, dict) and x.get("id") in ids]
    out = {"start": r.get("start") if r.get("start") in ids else None, "start_line": r.get("start_line", ""),
           "runner_ups": clean(r.get("runner_ups")), "beginnings": clean(r.get("beginnings")), "since": clean(r.get("since"))}
    # the rule, in code: the start is never the last 45 days. A late pick falls back to the first runner-up that qualifies.
    if out["start"] not in early:
        late = out["start"]
        alt = next((x["id"] for x in out["runner_ups"] if x["id"] in early), None)
        out["start_note"] = f"the model chose {late}, inside the last 45 days; " + (f"the runner-up {alt} is used" if alt else "no runner-up qualifies")
        if late:
            out["since"] = [{"id": late, "why": "the model's choice of start, moved to since: it is inside the last 45 days"}] + out["since"]
        by = {m["id"]: m for m in usable}
        out["start"] = alt
        out["start_line"] = ("When " + by[alt]["line"][0].lower() + by[alt]["line"][1:]) if alt else ""
        out["runner_ups"] = [x for x in out["runner_ups"] if x["id"] != alt]
    return out


def judge(story, cat, spine, th):
    by = {m["id"]: m for m in spine}
    chain = [("start", th["start"])] + [("beginning", b["id"]) for b in th["beginnings"]] + [("since", s["id"]) for s in th["since"]]
    items = "\n".join(f"- {mid} ({role}) | {by[mid]['event_date']} | {by[mid]['line']}" for role, mid in chain if mid in by)
    p = f"""You are a skeptical editor at NTK checking one story's Backstory before it is published. You did not choose these items.

STORY: {story['headline']}
{story['truths'][:2500]}

THE THREAD (oldest first; "start" is shown to the reader as "It starts in YYYY"):
{items}

These items come from a category spine the editor reviews; your job is to catch what does not belong in THIS story. Keep an item if a reader would understand this story better for it: a step in the story's own history, an earlier case of the same kind of event that shows the pattern, or the origin of a background the story names. Drop it only if it would mislead or distract: an analogy from another field, or something that shares only a broad theme (a decade, a branch of government, "regulation"). For the start, say whether it is the right "It starts in": the earlier, specific turn that set this story in motion (never today's news itself).
JSON only: {{"items":{{"m#":{{"keep":true,"why":"one sentence"}}}},"start_ok":true,"start_note":"one sentence"}}"""
    try:
        return ask(p, 2000)
    except Exception as e:  # noqa: BLE001
        return {"items": {}, "start_ok": None, "start_note": f"the judge call failed: {e}"}


# --- main ------------------------------------------------------------------------------------------

def rethread(today):
    """Redo only the per-story step against the spines already built (no web search)."""
    doc = json.loads(OUT.read_text())
    cats = {c["id"]: c for c in doc["categories"]}
    before = dict(doc.get("usage") or {})
    for s in doc["stories"]:
        c = cats[s["placement"]["category"]]
        th = thread(s, c, c["spine"], today)
        th["judge"] = judge(s, c, c["spine"], th) if th.get("start") else {}
        s["thread"] = th
        log(f"thread {s['headline'][:50]!r}: start {th.get('start')} | beginnings {[b['id'] for b in th['beginnings']]} | since {[x['id'] for x in th['since']]}"
            + (f" | {th['start_note']}" if th.get("start_note") else ""))
    doc["usage"] = {k: before.get(k, 0) + USAGE[k] for k in USAGE}
    doc["threads_generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc["log"] = (doc.get("log") or []) + ["--- threads redone ---"] + LOG
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    log(f"rethreaded; this pass {USAGE}")


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if "--threads-only" in sys.argv:
        return rethread(today)
    stories, rows, pool, spec, pool_doc = load_inputs()
    log(f"{len(stories)} stories, {len(rows)} categories, model {MODEL}")
    placed = place(stories, rows)
    by_row = {r["id"]: r for r in rows}
    cats = {}
    for s in stories:
        pl = placed.get(s["id"]) or {}
        cid = pl.get("category")
        if cid == "new" or cid not in by_row:
            title = (pl.get("new_title") or "Uncategorised").strip()
            cid = "p-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            base = by_row.get(cid) or {"id": cid, "title": title, "stratum": "new", "contest": pl.get("new_contest") or "",
                                       "beginnings": [], "objects": []}
        else:
            base = by_row[cid]
        c = cats.setdefault(cid, dict(base, stories=[], lenses=set()))
        c["stories"].append(s["id"])
        c["lenses"] |= set(s["lenses"])
        s["placement"] = {"category": cid, "why": pl.get("why", "")}
        log(f"placed {s['headline'][:60]!r} -> {cid} ({pl.get('why', '')[:90]})")
    sb = {s["id"]: s for s in stories}
    for cid, c in cats.items():
        filed = [sb[i] for i in c["stories"]]
        c["lenses"] = sorted(c["lenses"])
        c["spine"] = build_spine(c, filed, c["lenses"], pool, spec, today)
        c["trend"] = build_indicator(c, filed)
        log(f"  trend {c['title']}: {c['trend'].get('label') or c['trend'].get('none')} [{c['trend'].get('check', '-')}]")
    for s in stories:
        c = cats[s["placement"]["category"]]
        try:
            th = thread(s, c, c["spine"], today)
        except Exception as e:  # noqa: BLE001
            log(f"  thread failed for {s['id']}: {e}")
            th = {"start": None, "start_line": "", "runner_ups": [], "beginnings": [], "since": [], "error": str(e)}
        th["judge"] = judge(s, c, c["spine"], th) if th.get("start") else {}
        s["thread"] = th
        log(f"thread {s['headline'][:50]!r}: start {th.get('start')} | beginnings {[b['id'] for b in th['beginnings']]} | since {[x['id'] for x in th['since']]}")
    doc = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": MODEL, "usage": USAGE, "log": LOG,
           "stories": stories,
           "categories": [{k: v for k, v in c.items() if k not in ("objects",)} for c in cats.values()]}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    log(f"wrote {OUT}; usage {USAGE}")


if __name__ == "__main__":
    main()
