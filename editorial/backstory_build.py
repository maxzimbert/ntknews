#!/usr/bin/env python3
"""Backstory, built from categories that are researched once (T-0083).

The vocabulary (docs/decisions.md, 2026-10-12):
  Category      the history a story pairs with. One list: the long American arguments, the live
                conflicts, and subject categories created when nothing fits ("Outbreak secrecy").
  Beginnings    a category's dated milestones, each dated by when the event happened.
  Objects       the primary sources that defend the Beginnings ("the case"); one per Beginning.
  Trend line    one series per category, every value checked on the publisher's page.
  Subjects      tags (Israel, tech, Russia...) from editorial/lenses.json that make placement and
                research precise; the editor sees them as chips, never manages them as a list.
  It starts in  for one story, the Beginning that set it in motion.
  We are here   today's story, in the pairing line.

Per publish:
  1. place each story in a category (the editor's choice in Pulse wins), creating one if none fits;
  2. research a category once, when it has too few Beginnings: Beginnings with Objects that are
     fetched and checked, and a trend line;
  3. write the pairing line (build_pairings.write_lines, unchanged);
  4. choose each story's "It starts in" from the category's Beginnings (never the last 45 days),
     the Beginnings before it and the steps since; a second call judges the choice;
  5. write digest/data/backstory.json (rows and todays_pairings) and the store
     ntk-pulse/data/categories.json.

Publishing rule (the editor, 2026-10-12): a Beginning publishes without review when its Object is
verified (the link loads, the quoted sentence is on the page, and it is not a news site's copy) or
comes from the matrix. Everything else waits for the editor. The editor's rejections stick.

    python3 editorial/backstory_build.py                 # the publish step
    python3 editorial/backstory_build.py --seed-from F   # import categories built by the spine lab
"""
import argparse
import http.client
import io
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
import categories as C                                                       # noqa: E402
from build_pairings import parse_json_loose, strip_html, write_lines         # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LINEUP = ROOT / "ntk-pulse" / "data" / "lineup-publish.json"
BACKSTORY = ROOT / "digest" / "data" / "backstory.json"
STORE = ROOT / "ntk-pulse" / "data" / "categories.json"
POOL = ROOT / "ntk-pulse" / "data" / "backstory-pool.json"
SUBJECTS = ROOT / "editorial" / "lenses.json"
API = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("BACKSTORY_MODEL", "claude-sonnet-5-5")
MIN_BEGINNINGS = 6           # fewer publishable Beginnings than this and the category is researched
MAX_RESEARCH = 4             # categories researched per publish: a bound on spend (about $1.50 each)
MAX_FOCUSED = 3              # stories given their own targeted research per publish (about $0.50 to $1 each)
START_GAP_DAYS = 45          # "It starts in" is never inside this window: it is not today's news
USAGE = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "web_searches": 0}
NEWS_HOSTS = ("abcnews", "pbs.org", "lawfaremedia", "rollcall", "foreignpolicy", "aljazeera", "newsonair", "ms.now",
              "courthousenews", "reuters", "apnews", "nytimes", "washingtonpost", "cnn.", "bbc.", "theguardian", "politico",
              "axios", "npr.org", "cbsnews", "nbcnews", "foxnews", "bloomberg", "wsj.", "cnbc", "time.com", "newsweek",
              "thehill", "vox.com", "theatlantic", "independent.co")

STYLE = ("STYLE: written for an Advanced Placement history reader: precise, concrete, plain. Name the actor and the "
         "act. No em dashes or en dashes. Never use: this document, this reflects, underscores, highlights, serves as, "
         "a reminder that, pivotal, landmark, groundbreaking, seminal, watershed. Take no side.")


def log(m):
    print(m, flush=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
                time.sleep(20 * (attempt + 1))
                continue
            raise RuntimeError(f"{body['model']} HTTP {e.code}: {msg}") from None
        except (urllib.error.URLError, http.client.IncompleteRead, ConnectionError, TimeoutError) as e:
            # a long search answer cut off mid-read (the 2026-10-13 staging run lost a whole category's
            # research to IncompleteRead) is retried, not given up on
            if attempt < 2:
                time.sleep(15 * (attempt + 1))
                continue
            raise RuntimeError(f"{body['model']}: the connection failed ({type(e).__name__})") from None
    u = d.get("usage") or {}
    USAGE["calls"] += 1
    USAGE["input_tokens"] += u.get("input_tokens", 0)
    USAGE["output_tokens"] += u.get("output_tokens", 0)
    USAGE["web_searches"] += (u.get("server_tool_use") or {}).get("web_search_requests", 0)
    return d


def ask(prompt, max_tokens=4000):
    d = _post({"model": MODEL, "max_tokens": max_tokens, "thinking": {"type": "between_tools"},
               "messages": [{"role": "user", "content": prompt}]}, 240)
    return parse_json_loose("".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), MODEL)


def search(prompt, max_tokens=14000, uses=6):
    """(parsed JSON, the set of urls the search returned or cited)."""
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


# --- checking an Object ----------------------------------------------------------------------------

def _fetch_text(url):
    """(status, text). A PDF is read with pypdf when it is installed, so a court filing's quote can be
    tested instead of only its link (the spine lab could not test 9 of 50 Objects for this reason)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": C._UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read(8_000_000)
            ctype = r.headers.get("content-type", "")
            status = r.status
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001
        return 0, ""
    if "pdf" in ctype or body[:4] == b"%PDF":
        try:
            from pypdf import PdfReader
            pages = PdfReader(io.BytesIO(body)).pages[:60]
            return status, " ".join((p.extract_text() or "") for p in pages)
        except Exception:  # noqa: BLE001
            return status, ""
    import html as _html
    t = body.decode("utf-8", "ignore")
    t = re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S)
    return status, _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))


def host_of(url):
    h = re.sub(r"^https?://([^/]+).*$", r"\1", str(url or "")).lower()
    return h[4:] if h.startswith("www.") else h


def check_object(obj, urls, pool):
    """Every Object carries its check, so the editor sees why it is trusted. Nothing is dropped here."""
    if obj.get("matrix_id"):
        o = pool.get(obj["matrix_id"])
        if not o:
            return dict(obj, check="failed", check_note="not a matrix id")
        ok = o.get("link_status") in ("live", "live-pdf", None)
        return dict(obj, title=o["title"], author=o.get("author", ""), doc_date=o.get("sort") or o.get("year"),
                    url=o.get("url", ""), host=host_of(o.get("url")), check="matrix" if ok else "failed",
                    check_note="in the Object Matrix; its link is checked by check_links.py" if ok else f"the matrix link is {o.get('link_status')}")
    url = str(obj.get("url") or "").strip()
    host = host_of(url)
    obj = dict(obj, host=host)
    if not url.startswith("https://"):
        return dict(obj, check="failed", check_note="the link is not https")
    if any(d in host for d in C.DENY_HOSTS):
        return dict(obj, check="failed", check_note=f"{host} is not a primary source")
    if url not in urls:
        return dict(obj, check="failed", check_note="the link is not one the search returned")
    status, page = _fetch_text(url)
    if status in (401, 403, 429) or status == 0:
        return dict(obj, check="unchecked", check_note=f"the site refused the checker ({status or 'no answer'}); open it to confirm")
    if not 200 <= status < 400:
        return dict(obj, check="failed", check_note=f"the link answers {status}")
    if not page:
        return dict(obj, check="loads", check_note="the link loads, but its text could not be read, so the quote is untested")
    if not C._quote_on_page(obj.get("quote") or "", page):
        return dict(obj, check="failed", check_note="the link loads but the quoted sentence is not on the page")
    if any(n in host for n in NEWS_HOSTS):
        return dict(obj, check="news-copy", check_note=f"the quote is on the page, but {host} is a news site; the issuer's own copy is preferred")
    return dict(obj, check="verified", check_note="the link loads and the quoted sentence is on the page")


def recheck(store, pool):
    """Once per Beginning: re-test an Object whose quote could not be tested (a PDF, before the checker
    read PDFs) or whose site refused the checker. The editor's decisions are left alone."""
    n = 0
    for c in store["categories"]:
        for b in c.get("beginnings") or []:
            o = b["object"]
            if o.get("check") in ("loads", "unchecked") and not b.get("rechecked") and b.get("status") not in ("approved", "rejected") and o.get("url"):
                b["object"] = check_object({k: v for k, v in o.items() if k not in ("check", "check_note")}, {o["url"]}, pool)
                b["rechecked"] = now_iso()[:10]
                b["status"] = "auto" if publishable(dict(b, status="auto")) else "pending"
                n += 1
    if n:
        log(f"rechecked {n} Objects")


def merge_from_pulse(store, ov, bs, today):
    """What the editor made in Pulse's Backstory tab: new categories, and Beginnings found by asking for
    them. A Beginning found in Pulse is checked here like any other (recheck), so the publishing rule
    holds whoever found it."""
    have = {c["id"]: c for c in store["categories"]}
    lib = {c["id"]: c for c in library_rows(bs)}
    for nc in ov.get("newcats") or []:
        cid = nc.get("id") or ""
        if cid.startswith("p-") and cid not in have and cid not in lib and nc.get("title"):
            have[cid] = {"id": cid, "title": str(nc["title"])[:60], "kind": "subject", "contest": nc.get("contest") or "",
                         "subjects": nc.get("subjects") or [], "beginnings": [], "trend": None, "created": today, "stories": [],
                         "source": "made in Pulse"}
            store["categories"].append(have[cid])
            log(f"new category from Pulse: {nc['title']!r}")
    for cid, items in (ov.get("additions") or {}).items():
        c = have.get(cid)
        if not c and cid in lib:
            c = {k: v for k, v in lib[cid].items() if k != "_row"}
            store["categories"].append(c); have[cid] = c
        if not c:
            continue
        ids = {b["id"] for b in c.get("beginnings") or []}
        for m in items or []:
            d, line, o = str(m.get("event_date") or ""), " ".join(str(m.get("line") or "").split()), m.get("object") or {}
            if not re.match(r"^\d{3,4}", d) or not line or not str(o.get("url") or "").startswith("https://"):
                continue
            b = {"id": bid(d, line), "event_date": d, "year": re.match(r"\d{3,4}", d).group(), "line": line, "how": m.get("how", ""),
                 "object": dict({k: v for k, v in o.items() if k not in ("check", "check_note")}, check="unchecked",
                                check_note="found in Pulse; checked at publish"),
                 "status": "pending", "added": today, "asked": m.get("asked", "")}
            if b["id"] not in ids:
                c.setdefault("beginnings", []).append(b); ids.add(b["id"])
                log(f"  from Pulse, {c['title']}: {b['year']} {line[:60]}")
        c["beginnings"] = sorted(c.get("beginnings") or [], key=lambda b: b["event_date"])


def publishable(b):
    """The editor's rule. An approval or a rejection by the editor always wins."""
    if b.get("status") in ("approved", "rejected"):
        return b["status"] == "approved"
    return b["object"].get("check") in ("verified", "matrix")


# --- the store -------------------------------------------------------------------------------------

def slug(s, n=48):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:n]


def bid(event_date, line):
    return f"b-{event_date[:10]}-{slug(line, 36)}"


def load_store():
    if STORE.exists():
        return json.loads(STORE.read_text())
    return {"version": 1, "categories": []}


def library_rows(bs):
    """The rows in backstory.json, as categories: long arguments and live conflicts."""
    out = []
    for r in bs["rows"]:
        if r.get("stratum") == "provisional":
            continue                      # the old provisional categories are superseded by the store
        out.append({"id": r["id"], "title": r["title"], "kind": "live" if r.get("stratum") == "fire" else "long",
                    "contest": r.get("milestone") or "", "subjects": [], "beginnings": [], "trend": None,
                    "_row": r})
    return out


def all_categories(store, bs):
    by = {c["id"]: c for c in library_rows(bs)}
    for c in store["categories"]:
        base = by.get(c["id"], {})
        by[c["id"]] = dict(base, **c)
    return by


# --- inputs ----------------------------------------------------------------------------------------

def story_subjects(text, spec):
    bare = re.sub(r"\(\s*[A-Z][^()]{0,80}\)", " ", text)          # "( ABC Australia )" is a citation, not a subject
    return [k for k in spec if not k.startswith("_") and C.lens_supported(k, spec, bare)]


def load_stories(lp, spec):
    out = []
    for s in lp["stories"]:
        text = " ".join(strip_html(s.get(k) or "") for k in ("truth", "prob", "poss", "lies"))
        truths = " ".join(strip_html(s.get("truth") or "").split())
        out.append({"story_id": s["key"], "headline": strip_html(s.get("headline") or ""),
                    "summary": strip_html(s.get("lede") or "") or truths[:300], "truths": truths,
                    "text": " ".join(text.split()), "editor_category": s.get("backstory_row") or None,
                    "subjects": story_subjects(text, spec)})
    return out


# --- 1. placement ----------------------------------------------------------------------------------

def place(stories, cats):
    kinds = {"live": "a live conflict", "long": "a long American argument", "subject": "a subject"}
    lst = "\n".join(f"- {c['id']} | {c['title']} | {kinds.get(c.get('kind'), 'a subject')} | {c.get('contest', '')}"
                    + (f" | subjects: {', '.join(c['subjects'])}" if c.get("subjects") else "")
                    for c in cats.values())
    st = "\n\n".join(f"[{i + 1}] id {s['story_id']}\nHEADLINE: {s['headline']}\nTRUTHS: {s['truths'][:1400]}\n"
                     f"SUBJECTS IN ITS TEXT: {', '.join(s['subjects']) or '(none)'}" for i, s in enumerate(stories))
    p = f"""You place today's news stories in NTK's Backstory. A category is a history a reader can follow: a live conflict (its own recent history), a long American argument (decades), or a subject (a technology, a country's or an industry's history, a recurring kind of event). A story belongs to the category whose history best explains how this story came to be: the subject and the actors at its center, not a theme it shares in passing.

CATEGORIES:
{lst}

STORIES:
{st}

For each story choose one category id, or "new". A new category is named for its subject, 1 to 5 words ("AI", "Outbreak secrecy", "Israel's arms and tech boom"), with a contest line ("Whether X, or Y", 12 to 30 words, two positions a reasonable person holds) and the subjects it draws on, chosen from the story's SUBJECTS when they apply. Prefer a live conflict when the story is a consequence of it. Prefer an existing subject category over a near duplicate. Two stories about the same subject share a new category: give them the same title.
{STYLE}
JSON only: [{{"story_id":"...","category":"<id or new>","new_title":null,"new_contest":null,"subjects":[],"why":"one sentence"}}]"""
    out = ask(p, 3000)
    return {x["story_id"]: x for x in (out if isinstance(out, list) else out.get("stories", [])) if isinstance(x, dict)}


# --- 2. research, once per category ----------------------------------------------------------------

def matrix_seeds(cat, pool):
    r = cat.get("_row") or {}
    ids = {o.get("object_id") for o in r.get("objects") or []} | {b.get("object_id") for b in r.get("beginnings") or []}
    subj = set(cat.get("subjects") or [])
    out = [o for o in pool.values() if o.get("pool") == "matrix" and o.get("link_status") in ("live", "live-pdf", None)
           and (o["id"] in ids or set(o.get("lenses") or []) & subj or (r and o.get("row") == r.get("title")))]
    return sorted(out, key=lambda o: o.get("sort") or o.get("year") or "")[-45:]


def research(cat, filed, pool, today, focus=False):
    """Beginnings and Objects for one category, every Object checked. Merged into what the category
    already holds; nothing the editor has decided is touched."""
    seeds = matrix_seeds(cat, pool)
    have = [b for b in cat.get("beginnings") or [] if b.get("status") != "rejected"]
    seed_txt = "\n".join(f"- {o['id']} | {o.get('year')} | {o['title'][:110]}" for o in seeds) or "(none)"
    have_txt = "\n".join(f"- {b['event_date']} | {b['line']}" for b in have) or "(none)"
    st = "\n\n".join(f"[{i + 1}] {s['headline']}\n{s['truths'][:1800]}" for i, s in enumerate(filed))
    need = 6 if focus else max(6, 12 - len(have))
    p = f"""You are the researcher for NTK's Backstory, written for college-educated adults at the standard of an Advanced Placement history class. You are building the Beginnings of one category: the dated milestones a reader needs in order to understand today's stories filed under it, each defended by one primary source (its Object). The category is researched once and reused by every later story in it, so it must be accurate and defensible.

CATEGORY: {cat['title']}
ITS ARGUMENT: {cat.get('contest') or ''}
SUBJECTS IT DRAWS ON: {', '.join(cat.get('subjects') or []) or '(none)'}
TODAY: {today}
STORIES FILED UNDER IT TODAY:
{st}

{FOCUS if focus else ""}BEGINNINGS IT ALREADY HAS (do not repeat):
{have_txt}

MATRIX DOCUMENTS (primary sources already verified in NTK's library; adopt one by its id when it is the primary source for a milestone you choose):
{seed_txt}

Add up to {need} Beginnings, oldest to newest. First think: what are the events, in order, without which these stories could not have happened? Who acted, what did they decide, what changed? When the category draws on more than one subject, weave them into one chronology. Then:
- Two or three may reach back to the root of the argument. Most should come from the period that set today's stories in motion, and the last should be the most recent turn before today.
- A Beginning is an event: a law, ruling, order, treaty, attack, outbreak, filing, election, report or decision. Date it by when the event happened, not by when something was written about it.
- Each is defended by ONE primary source: the document itself (the law, the ruling, the order, the filing, the official statement or transcript, the dataset, the agency report), or an official video of the event, from the issuer's own site or an archive's, court's, legislature's or government's copy. Not Wikipedia, not a news article or explainer, and not a news site's reprint when the issuer's own copy exists. Use web search to find it and give the exact URL you found. Quote one sentence from that page, word for word.
- Every Beginning must matter to at least one of today's stories through its subject, its actors or its action, or be an earlier case of the same kind of event that shows the pattern. A document that only shares a theme is an analogy and does not belong.
- If you cannot source a Beginning, leave it out. Fewer well-sourced Beginnings are better than padding.
{STYLE}

JSON only:
{{"beginnings":[{{"event_date":"YYYY-MM-DD, or YYYY when the day is not known","line":"one sentence of 12 to 30 words saying what happened, actor first","how":"one sentence: what in today's stories this explains","object":{{"matrix_id":null,"title":"the document's exact title","author":"who issued it","doc_date":"YYYY-MM-DD or YYYY","media_type":"document | video | dataset","url":"https://...","quote":"one sentence copied word for word from that page"}}}}]}}"""
    r, urls = search(p, 14000, 6)        # 6 searches, not 12: research was the bulk of the 2026-10-09 and 10-12 spend
    items = r.get("beginnings") if isinstance(r, dict) else r
    added, seen = [], {b["id"] for b in cat.get("beginnings") or []}
    for m in items or []:
        d = str(m.get("event_date") or "")
        line = " ".join(str(m.get("line") or "").split())
        if not re.match(r"^\d{3,4}", d) or not line:
            continue
        b = {"id": bid(d, line), "event_date": d, "year": re.match(r"\d{3,4}", d).group(), "line": line,
             "how": m.get("how") or "", "object": check_object(m.get("object") or {}, urls, pool),
             "status": "auto", "added": today}
        if b["id"] in seen:
            continue
        seen.add(b["id"])
        b["status"] = "auto" if publishable(dict(b, status="auto")) else "pending"
        added.append(b)
    cat["beginnings"] = sorted((cat.get("beginnings") or []) + added, key=lambda b: b["event_date"])
    cat["researched"] = now_iso()
    log(f"  researched {cat['title']}: +{len(added)} Beginnings ("
        + ", ".join(f"{b['year']} {b['object']['check']}" for b in added) + ")")
    return added


def upgrade(cat, pool, today, limit=10):
    """A Beginning waits when its Object is a news site's copy, untested, or failed. One search asks for
    the issuer's own copy of each (the White House transcript, not PBS's reprint). A copy that checks
    out replaces the old Object and the Beginning publishes under the rule. Tried once per Beginning."""
    todo = [b for b in cat.get("beginnings") or [] if b.get("status") == "pending" and not b.get("upgrade_tried")
            and b["object"].get("check") in ("news-copy", "failed", "unchecked", "loads")][-limit:]
    if not todo:
        return 0
    lst = "\n".join(f"- {b['id']} | {b['event_date']} | {b['line']} | current source: {b['object'].get('title', '')} ({b['object'].get('host', '')})" for b in todo)
    p = f"""For each event below, find the primary source on the issuer's own site or an official archive: the government, court, legislature, agency, international body or organisation that issued it (whitehouse.gov, congress.gov, a court's site, un.org, who.int, an agency's site, the company's own newsroom, govinfo.gov, the American Presidency Project). Not a news site's reprint, not Wikipedia. Use web search, give the exact URL you found, and quote one sentence from that page word for word. If you cannot find an official copy, leave the event out.

EVENTS:
{lst}

JSON only: {{"<id>":{{"title":"the document's exact title","author":"who issued it","doc_date":"YYYY-MM-DD or YYYY","url":"https://...","quote":"one sentence copied word for word from that page"}}}}"""
    try:
        r, urls = search(p, 9000, 6)
    except Exception as e:  # noqa: BLE001
        log(f"  upgrade search failed for {cat['title']}: {e}")
        return 0
    n = 0
    for b in todo:
        b["upgrade_tried"] = today
        o = r.get(b["id"]) if isinstance(r, dict) else None
        if not isinstance(o, dict) or not o.get("url"):
            continue
        new = check_object(o, urls, pool)
        if new.get("check") in ("verified", "matrix"):
            b["replaced_object"] = b["object"]
            b["object"] = new
            b["status"] = "auto"
            n += 1
    log(f"  upgraded {n} of {len(todo)} waiting Beginnings in {cat['title']} to the issuer's own copy")
    return n


def write_stakes(cat, filed):
    """Two sentences framing the open questions the category turns on (T-0059: every page has them).
    Written once per category; a draft that breaks the text rules is retried once, then left empty."""
    st = "; ".join(s["headline"] for s in filed)
    for _ in range(2):
        p = f"""Write the stakes paragraph for a Backstory category page at NTK: TWO sentences, 25 to 55 words in all, framing the open questions this category turns on (whether, when, by whom, who benefits). Do not write about "risks" in the abstract. No numbers.
CATEGORY: {cat['title']}
ITS ARGUMENT: {cat.get('contest') or ''}
TODAY'S STORIES: {st}
{STYLE}
JSON only: {{"stakes":"..."}}"""
        try:
            t = " ".join(str(ask(p, 800).get("stakes") or "").split())
        except Exception:  # noqa: BLE001
            return ""
        if t and not C.text_problems("stakes", t, 25, 55, sentences=2):
            return t
    return ""


FOCUS = """FOCUS: the story above sits in a corner of this category that its Beginnings do not cover yet: they are about the category in general, and the judge found none that explain this story. Add the Beginnings of this story's own thread inside the category's history: its actors, its action, the policy, market or institution it turns on. For example, a deal over Russian diesel needs the history of sanctions on Russian oil and fuel, not the history of the war. Every other rule below holds.

"""


def research_trend(cat, filed):
    st = "; ".join(s["headline"] for s in filed)
    p = f"""Find ONE trend line for a Backstory category page at NTK: a measure a reader can check, from the agency, statistical office or pollster that publishes it, showing how something at the heart of this category has moved over time.

CATEGORY: {cat['title']}
ITS ARGUMENT: {cat.get('contest') or ''}
TODAY'S STORIES: {st}

Prefer a series the publisher updates (EIA, BLS, FRED, CDC, Census, Pew, Gallup, a court or agency dataset) over a one-off study. Give 3 to 8 points from ONE page that states them all, oldest to newest, the last as recent as the page allows. Every value must appear on that page exactly as you give it. Use web search.
JSON only: {{"label":"what is measured, as a reader would say it","unit":"%, $ per gallon, cases, ...","points":[{{"date":"YYYY or YYYY-MM","value":"as printed on the page"}}],"source":"the publisher","source_url":"https://...","why":"one sentence: why this measure belongs to this category"}}
If no such page exists, answer {{"none":"why"}}."""
    try:
        r, urls = search(p, 6000, 6)
    except Exception as e:  # noqa: BLE001
        return {"none": f"the search failed: {e}"}
    if not isinstance(r, dict) or r.get("none") or not r.get("points"):
        return {"none": (r.get("none") if isinstance(r, dict) else None) or "no answer"}
    url = str(r.get("source_url") or "")
    if url not in urls:
        return dict(r, check="failed", check_note="the link is not one the search returned")
    status, page = _fetch_text(url)
    if not page:
        return dict(r, check="unchecked" if status in (0, 401, 403, 429) else "loads" if 200 <= status < 400 else "failed",
                    check_note=f"the page could not be read as text ({status}); open it to confirm the values")
    digits = re.sub(r"[^0-9. ]", " ", page)
    missing = [p_["value"] for p_ in r["points"] if re.sub(r"[^0-9.]", "", str(p_["value"])) not in digits]
    if missing:
        return dict(r, check="failed", check_note=f"values not found on the page: {', '.join(map(str, missing[:4]))}")
    return dict(r, check="verified", check_note="the page loads and every value appears on it")


# --- 4. each story's Backstory ---------------------------------------------------------------------

def choose(story, cat, today):
    usable = [b for b in cat["beginnings"] if publishable(b)]
    if not usable:
        return {"start": None, "start_line": "", "runner_ups": [], "before": [], "since": [], "note": "no publishable Beginnings"}
    cutoff = (datetime.fromisoformat(today) - timedelta(days=START_GAP_DAYS)).strftime("%Y-%m-%d")
    lst = "\n".join(f"- {b['id']} | {b['event_date']} | {b['line']}" for b in usable)
    p = f"""You choose one story's Backstory at NTK from its category's Beginnings: a chronology of vetted milestones, each with a primary source. You choose; you do not invent.

STORY: {story['headline']}
{story['truths'][:2500]}
TODAY'S LINE (what the story is, already written): {story.get('line', '')}

CATEGORY: {cat['title']}: {cat.get('contest') or ''}
BEGINNINGS:
{lst}

TODAY: {today}

1. START ("It starts in YYYY"): choose the ONE Beginning that set today's story in motion: the specific, consequential turn without which this story would not exist. It is never today's news itself or the trigger of the last few weeks: it is the earlier decision or event that made today possible, usually months or years back. Only Beginnings dated before {cutoff} may be the start. Prefer it close enough to explain today over a distant root. Name two runner-ups (also before {cutoff}) and say in a few words why each is weaker.
2. BEFORE: 3 to 5 Beginnings dated before the start, oldest to newest, that a reader needs in order to see how we got to the start: earlier steps in this story, or earlier cases of the same kind of event that show the pattern. Each must connect to this story's subject, actors or action.
3. SINCE: 0 to 2 Beginnings after the start and before today: the most recent turns that bring us to today.
4. START LINE: one sentence beginning "When" that says what happened at the start, 12 to 28 words.
{STYLE}
JSON only: {{"start":"<id>","start_line":"When ...","runner_ups":[{{"id":"<id>","why_weaker":"..."}}],"before":[{{"id":"<id>","why":"one sentence naming what in this story it connects to"}}],"since":[{{"id":"<id>","why":"..."}}]}}"""
    r = ask(p, 3000)
    by = {b["id"]: b for b in usable}
    early = {i for i, b in by.items() if b["event_date"] < cutoff}
    clean = lambda xs: [x for x in xs or [] if isinstance(x, dict) and x.get("id") in by]
    out = {"start": r.get("start") if r.get("start") in by else None, "start_line": r.get("start_line", ""),
           "runner_ups": clean(r.get("runner_ups")), "before": clean(r.get("before") or r.get("beginnings")),
           "since": clean(r.get("since"))}
    if out["start"] not in early:          # the rule, in code: a late pick falls back to the first runner-up that qualifies
        late = out["start"]
        alt = next((x["id"] for x in out["runner_ups"] if x["id"] in early), None)
        out["note"] = f"the model chose {late}, inside the last {START_GAP_DAYS} days; " + (f"the runner-up {alt} is used" if alt else "no runner-up qualifies")
        if late:
            out["since"] = [{"id": late, "why": "the model's choice of start, moved here: it is too recent to be the start"}] + out["since"]
        out["start"] = alt
        out["start_line"] = ("When " + by[alt]["line"][0].lower() + by[alt]["line"][1:]) if alt else ""
        out["runner_ups"] = [x for x in out["runner_ups"] if x["id"] != alt]
    sd = by[out["start"]]["event_date"] if out["start"] else None
    out["before"] = [x for x in out["before"] if not sd or by[x["id"]]["event_date"] < sd]
    out["since"] = [x for x in out["since"] if sd and by[x["id"]]["event_date"] > sd]
    return out


def judge(story, cat, ch):
    by = {b["id"]: b for b in cat["beginnings"]}
    chain = ([("start", ch["start"])] if ch.get("start") else []) + [("before", x["id"]) for x in ch["before"]] + [("since", x["id"]) for x in ch["since"]]
    if not chain:
        return {}
    items = "\n".join(f"- {i} ({role}) | {by[i]['event_date']} | {by[i]['line']}" for role, i in chain if i in by)
    p = f"""You are a skeptical editor at NTK checking one story's Backstory before it is published. You did not choose these items.

STORY: {story['headline']}
{story['truths'][:2500]}

THE CHOICE ("start" is shown to the reader as "It starts in YYYY"):
{items}

These come from a category the editor reviews; your job is to catch what does not belong in THIS story. Keep an item if a reader would understand this story better for it: a step in the story's own history, an earlier case of the same kind of event that shows the pattern, or the origin of a background the story names. Drop it only if it would mislead or distract: an analogy from another field, or something that shares only a broad theme (a decade, a branch of government, "regulation"). For the start, say whether it is the right "It starts in": the earlier, specific turn that set this story in motion (never today's news itself).
JSON only: {{"items":{{"<id>":{{"keep":true,"why":"one sentence"}}}},"start_ok":true,"start_note":"one sentence"}}"""
    try:
        return ask(p, 2000)
    except Exception as e:  # noqa: BLE001
        return {"items": {}, "start_ok": None, "start_note": f"the judge call failed: {e}"}


def pick_for(s, c, today):
    """Choose one story's start and Beginnings from its category, then judge them."""
    try:
        ch = choose(s, c, today)
    except Exception as e:  # noqa: BLE001
        log(f"  choosing failed for {s['story_id']}: {e}")
        ch = {"start": None, "start_line": "", "runner_ups": [], "before": [], "since": [], "note": str(e)}
    ch["judge"] = judge(s, c, ch) if ch.get("start") else {}
    drop = {k for k, v in (ch["judge"].get("items") or {}).items() if isinstance(v, dict) and v.get("keep") is False and k != ch.get("start")}
    ch["dropped"] = sorted(drop)
    ch["before"] = [x for x in ch["before"] if x["id"] not in drop]
    ch["since"] = [x for x in ch["since"] if x["id"] not in drop]
    if ch.get("start") and (ch["judge"] or {}).get("start_ok") is False:
        # the judge says the start is wrong: no start from the category; build_origins retrieves one
        ch["doubted_start"] = ch["start"]
        ch["note"] = (ch.get("note", "") + " the judge doubted the start, so it is retrieved instead: " + str(ch["judge"].get("start_note", ""))).strip()
        by_ = {b["id"]: b for b in c["beginnings"]}
        ch["since"] = sorted(ch["since"] + [{"id": ch["start"], "why": "the start the judge doubted"}], key=lambda x: by_[x["id"]]["event_date"])
        ch["start"] = None
    return ch


def apply_overrides(ch, ov, cat):
    """The editor's choices for one story, from Pulse: a start, and which Beginnings show."""
    by = {b["id"]: b for b in cat["beginnings"] if publishable(b)}
    if ov.get("start") in by:
        ch["start"] = ov["start"]
        ch["start_line"] = "When " + by[ov["start"]]["line"][0].lower() + by[ov["start"]]["line"][1:]
        ch["by_editor"] = True
    if isinstance(ov.get("include"), list):
        sd = by[ch["start"]]["event_date"] if ch.get("start") in by else None
        inc = [i for i in ov["include"] if i in by and i != ch.get("start")]
        ch["before"] = [{"id": i, "why": "chosen by the editor"} for i in inc if not sd or by[i]["event_date"] < sd]
        ch["since"] = [{"id": i, "why": "chosen by the editor"} for i in inc if sd and by[i]["event_date"] > sd]
        ch["by_editor"] = True
    return ch


# --- 5. the reader's data --------------------------------------------------------------------------

def trend_to_indicator(tr):
    if not tr or not tr.get("points"):
        return None
    a, b = tr["points"][0], tr["points"][-1]
    fa = float(re.sub(r"[^0-9.\-]", "", str(a["value"])) or 0)
    fb = float(re.sub(r"[^0-9.\-]", "", str(b["value"])) or 0)
    unit = tr.get("unit") or ""
    fmt = lambda v: f"{v}%" if unit.strip() == "%" and "%" not in str(v) else str(v)
    return {"label": tr["label"], "then_value": fmt(a["value"]), "then_year": str(a["date"]), "now_value": fmt(b["value"]),
            "direction": "up" if fb > fa else "down" if fb < fa else "flat", "source": tr.get("source", ""),
            "source_url": tr.get("source_url", ""), "as_of": str(b["date"]), "points": tr["points"], "unit": unit,
            "verified": tr.get("check") == "verified", "check": tr.get("check"), "check_note": tr.get("check_note", "")}


def row_for(cat, picks, lines):
    """One category, as the reader sees it today: the Beginnings chosen for today's stories in it, the
    start(s) marked, the Objects behind them, the trend line, and today's lines as "We are here"."""
    by = {b["id"]: b for b in cat["beginnings"]}
    ids, starts = set(), set()
    for ch in picks:
        if ch.get("start"):
            ids.add(ch["start"]); starts.add(ch["start"])
        ids |= {x["id"] for x in ch["before"] + ch["since"]}
    if not ids:                                    # no story today: the most recent six it can publish
        ids = {b["id"] for b in [b for b in cat["beginnings"] if publishable(b)][-6:]}
    # a page shows 3 to 8 Beginnings (T-0069). Fewer chosen today: the nearest publishable ones before the
    # start are added, never one the judge dropped. More (several stories): the starts and the latest stay.
    dropped = set().union(*[set(ch.get("dropped") or []) for ch in picks]) if picks else set()
    first = min((by[i]["event_date"] for i in starts if i in by), default="9999")
    spare = [b for b in cat["beginnings"] if publishable(b) and b["id"] not in ids and b["id"] not in dropped and b["event_date"] < first]
    while len(ids) < 3 and spare:
        ids.add(spare.pop()["id"])
    chosen = sorted((by[i] for i in ids if i in by), key=lambda b: b["event_date"])
    if len(chosen) > 8:
        keep = {b["id"] for b in chosen if b["id"] in starts} | {b["id"] for b in chosen[-(8 - len(starts)):]}
        chosen = [b for b in chosen if b["id"] in keep][-8:]
    begs = [{"year": b["year"], "line": b["line"], "object_id": b["id"], **({"mark": "start"} if b["id"] in starts else {})} for b in chosen]
    objs = [{"object_id": b["id"], "title": b["object"].get("title", ""), "author": b["object"].get("author", ""),
             "year": str(b["object"].get("doc_date") or b["year"])[:4], "source": b["object"].get("host") or "",
             "source_url": b["object"].get("url", ""), "evidence_quote": b["object"].get("quote", ""),
             "about": b.get("how") or b["line"], "check": b["object"].get("check")} for b in chosen]
    r = cat.get("_row") or {}
    return {"id": cat["id"], "stratum": "held", "kind": cat.get("kind", "subject"), "title": cat["title"],
            "milestone": cat.get("contest", ""), "stakes": cat.get("stakes") or r.get("stakes", ""), "subgenres": r.get("subgenres", []),
            "subjects": cat.get("subjects", []), "start_date": None, "start_line": None, "close_condition": r.get("close_condition"),
            "roots": r.get("roots", []), "indicator": trend_to_indicator(cat.get("trend")) or r.get("indicator"),
            "beginnings": begs, "objects": objs, "here": [l for l in lines if l], "narrative": [], "instances": [], "photo": None,
            "updated": True}


# --- main ------------------------------------------------------------------------------------------

def seed(path, store, bs, pool):
    """Import categories the spine lab built (ntk-pulse/data/spine-lab.json)."""
    lab = json.loads(Path(path).read_text())
    have = {c["id"]: c for c in store["categories"]}
    lib = {c["id"]: c for c in library_rows(bs)}
    for c in lab["categories"]:
        kind = "live" if c.get("stratum") == "fire" else "long" if c.get("stratum") == "held" else "subject"
        begs = []
        for m in c.get("spine") or []:
            src = dict(m.get("source") or {})
            src["host"] = host_of(src.get("url"))
            if src.get("check") == "verified" and any(n in src["host"] for n in NEWS_HOSTS):
                src.update(check="news-copy", check_note=f"the quote is on the page, but {src['host']} is a news site; the issuer's own copy is preferred")
            b = {"id": bid(m["event_date"], m["line"]), "event_date": m["event_date"], "year": str(m["year"]), "line": m["line"],
                 "how": m.get("how", ""), "object": src, "status": "auto", "added": lab["generated"][:10]}
            b["status"] = "auto" if publishable(b) else "pending"
            begs.append(b)
        rec = {"id": c["id"], "title": c["title"], "kind": kind, "contest": c.get("contest") or lib.get(c["id"], {}).get("contest", ""),
               "subjects": c.get("lenses") or [], "beginnings": begs, "trend": c.get("trend"), "researched": lab["generated"],
               "stories": [], "source": "spine lab, 2026-10-09"}
        have[c["id"]] = rec
        log(f"seeded {c['title']}: {len(begs)} Beginnings, {sum(publishable(b) for b in begs)} publishable without review")
    store["categories"] = list(have.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-from")
    ap.add_argument("--today")
    a = ap.parse_args()
    today = a.today or datetime.now(timezone.utc).date().isoformat()
    bs = json.loads(BACKSTORY.read_text())
    pool = {o["id"]: o for o in json.loads(POOL.read_text())["objects"]}
    spec = json.loads(SUBJECTS.read_text())
    store = load_store()
    if a.seed_from:
        seed(a.seed_from, store, bs, pool)
        STORE.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n")
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set; the previous Backstory stays in place")
    lp = json.loads(LINEUP.read_text())
    stories = load_stories(lp, spec)
    ov = lp.get("backstory_overrides") or {}
    merge_from_pulse(store, ov, bs, today)
    # the editor's decisions on Beginnings, from Pulse, are stored first: they stick
    for cid, decisions in (ov.get("beginnings") or {}).items():
        for c in store["categories"]:
            if c["id"] == cid:
                for b in c["beginnings"]:
                    if decisions.get(b["id"]) in ("approved", "rejected", "auto"):
                        b["status"] = decisions[b["id"]] if decisions[b["id"]] != "auto" else ("auto" if publishable(dict(b, status="auto")) else "pending")
                        b["decided"] = today
    recheck(store, pool)
    cats = all_categories(store, bs)
    log(f"{len(stories)} stories, {len(cats)} categories, model {MODEL}")

    # 1. placement: the editor's category wins
    placed = place([s for s in stories if s["editor_category"] not in cats], cats) if any(s["editor_category"] not in cats for s in stories) else {}
    for s in stories:
        if s["editor_category"] in cats:
            s["category"], s["placed_by"], s["placed_why"] = s["editor_category"], "editor", "chosen by the editor in Pulse"
            continue
        pl = placed.get(s["story_id"]) or {}
        cid = pl.get("category")
        if cid not in cats:
            title = (pl.get("new_title") or s["headline"][:40]).strip()
            cid = "p-" + slug(title, 40)
            if cid not in cats:
                cats[cid] = {"id": cid, "title": title, "kind": "subject", "contest": pl.get("new_contest") or "",
                             "subjects": [x for x in pl.get("subjects") or [] if x in spec], "beginnings": [], "trend": None,
                             "created": today, "stories": []}
                log(f"new category {title!r} ({cid})")
        s["category"], s["placed_by"], s["placed_why"] = cid, "model", pl.get("why", "")
        log(f"placed {s['headline'][:60]!r} -> {cid}")

    # 2. research, once, where a category used today has too few publishable Beginnings
    used = {}
    for s in stories:
        used.setdefault(s["category"], []).append(s)
    budget = MAX_RESEARCH
    for cid, filed in used.items():
        c = cats[cid]
        c.setdefault("beginnings", [])
        if sum(publishable(b) for b in c["beginnings"]) < MIN_BEGINNINGS and budget > 0:
            budget -= 1
            try:
                research(c, filed, pool, today)
            except Exception as e:  # noqa: BLE001
                log(f"  research failed for {c['title']}: {e}")
        upgrade(c, pool, today)
        if not c.get("stakes") and not (c.get("_row") or {}).get("stakes"):
            c["stakes"] = write_stakes(c, filed)
        has_row_indicator = bool((c.get("_row") or {}).get("indicator"))
        if not has_row_indicator and (not c.get("trend") or (c["trend"].get("none") and c.get("trend_tried") != today)):
            c["trend"] = research_trend(c, filed)
            c["trend_tried"] = today
            log(f"  trend {c['title']}: {c['trend'].get('label') or c['trend'].get('none')} [{c['trend'].get('check', '-')}]")

    # 3. the pairing line, written as before
    rows_by_id = {cid: dict((c.get("_row") or {}), id=cid, title=c["title"], milestone=c.get("contest", ""),
                            stratum=(c.get("_row") or {}).get("stratum", "provisional"),
                            start_date=(c.get("_row") or {}).get("start_date") or today) for cid, c in cats.items()}
    entries = [dict(s, row=s["category"]) for s in stories]
    try:
        _, pairs = write_lines(os.environ["ANTHROPIC_API_KEY"], entries, rows_by_id, False)
        lines = {p.get("story_id"): p.get("line", "") for p in pairs if isinstance(p, dict)}
    except Exception as e:  # noqa: BLE001
        log(f"pairing lines failed ({e}); stories keep their summaries")
        lines = {}

    # 4. each story's Backstory. A story left with fewer than three Beginnings (its category is about
    # something broader than its angle) gets one targeted research call for its own thread, then is chosen
    # again. Found on the 2026-10-13 staging run: a Russian diesel deal filed under Ukraine-Russia had only
    # war history to draw on, and the judge rightly dropped all of it.
    picks = {}
    focused = 0
    for s in stories:
        s["line"] = lines.get(s["story_id"], "")
        c = cats[s["category"]]
        ch = pick_for(s, c, today)
        if (not ch.get("start") or len(ch["before"]) + len(ch["since"]) < 2) and focused < MAX_FOCUSED:
            focused += 1
            try:
                added = research(c, [s], pool, today, focus=True)
                if any(publishable(b) for b in added):
                    ch = pick_for(s, c, today)
                    ch["focused"] = True
            except Exception as e:  # noqa: BLE001
                log(f"  focused research failed for {s['story_id']}: {e}")
        ch = apply_overrides(ch, (ov.get("stories") or {}).get(s["story_id"]) or {}, c)
        picks[s["story_id"]] = ch
        log(f"  {s['headline'][:50]!r}: starts {ch.get('start')} | before {[x['id'][2:12] for x in ch['before']]} | since {[x['id'][2:12] for x in ch['since']]}"
            + (" | focused research" if ch.get("focused") else "") + (f" | {ch['note']}" if ch.get("note") else ""))

    # 5. write. If no story could be given a Backstory (the API down, the credit spent), the previous
    # backstory.json stays: an empty Backstory is worse than yesterday's. What research found is kept.
    if stories and all(p.get("note", "").startswith("claude-") or "HTTP" in p.get("note", "") for p in picks.values()):
        store["categories"] = [{k: v for k, v in c.items() if k != "_row"} for c in cats.values() if c.get("beginnings") or c.get("stories")]
        store["generated"] = now_iso()
        STORE.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n")
        sys.exit(f"every story's Backstory failed ({next(iter(picks.values())).get('note', '')[:120]}); the previous backstory.json is kept")
    by_cat = {}
    for s in stories:
        by_cat.setdefault(s["category"], []).append(s)
    new_rows = {cid: row_for(cats[cid], [picks[s["story_id"]] for s in ss], [s["line"] for s in ss]) for cid, ss in by_cat.items()}
    # a category whose page cannot show three Beginnings is held back (T-0069; the editor: no Objects, no
    # category). A long argument or live conflict keeps its old page; a subject category has none yet, so
    # its stories publish with their "It starts in" and no link. The editor sees why in Pulse.
    held = {cid for cid, r in new_rows.items() if len(r["beginnings"]) < 3}
    for cid in held:
        new_rows.pop(cid)
        log(f"  held back {cats[cid]['title']}: fewer than three Beginnings can publish")
    bs["rows"] = [new_rows.pop(r["id"], r) for r in bs["rows"] if r.get("stratum") != "provisional"] + list(new_rows.values())
    out = []
    for s in stories:
        c, ch = cats[s["category"]], picks[s["story_id"]]
        by = {b["id"]: b for b in c["beginnings"]}
        st = by.get(ch.get("start"))
        origin = ({"status": "retrieved", "source": "category", "year": int(st["year"]), "line": ch["start_line"].rstrip(".") + ".",
                   "title": st["object"].get("title", ""), "url": st["object"].get("url", ""),
                   "evidence_quote": st["object"].get("quote", ""), "beginning_id": st["id"], "fit": "direct",
                   "verified": st.get("status") == "approved", "why": (ch.get("judge") or {}).get("start_note", "")}
                  if st else {"status": "none", "source": "category", "why": ch.get("note", "no publishable Beginning")})
        out.append({"story_id": s["story_id"], "headline": s["headline"], "row": s["category"], "line": s["line"],
                    "subgenre": None, "confidence": None, "source": "editor" if s["placed_by"] == "editor" else "category",
                    "placed_why": s["placed_why"], "needs_review": False, "origin": origin,
                    "start": ch.get("start"), "before": [x["id"] for x in ch["before"]], "since": [x["id"] for x in ch["since"]],
                    "runner_ups": ch.get("runner_ups", []), "why": {x["id"]: x.get("why", "") for x in ch["before"] + ch["since"]},
                    "judge": ch.get("judge", {}), "dropped": ch.get("dropped", []), "by_editor": ch.get("by_editor", False),
                    "note": ch.get("note", ""), "held_back": s["category"] in held})
    bs["todays_pairings"] = out
    bs["pairings_generated"] = now_iso()
    BACKSTORY.write_text(json.dumps(bs, indent=2, ensure_ascii=False) + "\n")
    for cid, ss in by_cat.items():
        c = cats[cid]
        c["stories"] = ((c.get("stories") or []) + [{"id": s["story_id"], "date": today, "headline": s["headline"]} for s in ss])[-30:]
    keep = [c for c in cats.values() if c.get("beginnings") or c.get("stories")]
    store["categories"] = [{k: v for k, v in c.items() if k != "_row"} for c in keep]
    store["generated"] = now_iso()
    store["usage_last_run"] = USAGE
    STORE.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n")
    log(f"wrote {len(out)} pairings and {len(store['categories'])} categories; usage {USAGE}")


if __name__ == "__main__":
    main()
