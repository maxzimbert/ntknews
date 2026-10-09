"""
Compose a Backstory category automatically (T-0079).

The pairing step (build_pairings.py) already does two things well without the editor: it files each
story under a row, and it writes the one-line "Today" sentence. This is the third thing in the same
spirit. When a story fits no row, the pipeline names a category for it and composes the page: contest,
stakes, the histories to draw on, Beginnings and objects picked by rule, the lines written, a trend line
found by search. Pulse is where the editor reviews and revises it afterwards; nothing waits on a click.

Nothing here is trusted by the site. The record goes through categories.validate, which drops what fails.

The prompts are the same as the ones in ntk-pulse/pulse.html (composeCat, writeObjectText,
proposeIndicator). They are written out twice, once per language, and should be kept in step.
"""
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

import categories as C

STYLE = ("STYLE (all text): plain words, Grade 8 to 10. No em dashes. Never use: this document, this reflects, "
         "underscores, highlights, serves as, a reminder that, pivotal, landmark, groundbreaking, seminal. "
         "Take no side. Use only facts in the material you are given; no numbers that do not appear in it.")
AUTO_OK_LINKS = ("live", "live-pdf")        # a candidate the editor has not reviewed may be used only if its link was read


def slug(name):
    return "p-" + re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:40]


# --- picking Beginnings: the same rule as Pulse's selectBeginnings / pickBeginnings -------------

def select_beginnings(objs, k):
    """The most recent object, plus the rest spread evenly across time, no repeated author where a
    neighbour will do."""
    a = sorted(objs, key=lambda o: o["sort"])
    if len(a) <= k:
        return a
    last, rest, need = a[-1], a[:-1], k - 1
    out, used = [], set()
    for i in range(need):
        idx = round(i * (len(rest) - 1) / max(need - 1, 1))
        j = idx
        while j < len(rest) and (j in used or any(o["author"] and o["author"] == rest[j]["author"] for o in out)):
            j += 1
        if j >= len(rest):
            j = idx
            while j >= 0 and j in used:
                j -= 1
        if j < 0:
            break
        used.add(j)
        out.append(rest[j])
    return sorted(out + [last], key=lambda o: o["sort"])


def pick_beginnings(objs, k):
    """Matrix objects first (already vetted), then candidates spread over the rest of the span."""
    m = [o for o in objs if o["pool"] == "matrix"]
    c = [o for o in objs if o["pool"] != "matrix"]
    first = select_beginnings(m, k)
    if len(first) >= k or not c:
        return first
    return sorted(first + select_beginnings(c, k - len(first)), key=lambda o: o["sort"])


def eligible(o):
    if not o.get("url") or o.get("link_status") == "dead":
        return False
    if o["pool"] == "candidate" and not o.get("approved") and o.get("link_status") not in AUTO_OK_LINKS:
        return False
    return True


def pool_for(pool_objs, lenses, subgenres):
    return [o for o in pool_objs if eligible(o) and (set(o["lenses"]) & set(lenses) or (o.get("subgenre") and o["subgenre"] in subgenres))]


def pick_for_subjects(pools, total=6, minimum=4):
    """Four to six objects across all the category's subjects, matrix objects first.

    Each subject contributes a little more than its share; the union is then cut to `total` by the
    same rule as one pool (matrix first, the latest kept, the rest spread across time). If that
    leaves fewer than `minimum` and the pools hold more, the earliest gaps are filled."""
    per = -(-total // max(len(pools), 1)) + 1
    seen = {}
    for pool in pools:
        for o in pick_beginnings(pool, per):
            seen[o["id"]] = o
    out = pick_beginnings(list(seen.values()), total)
    if len(out) < minimum:
        have = {o["id"] for o in out}
        rest = {o["id"]: o for pool in pools for o in pool if o["id"] not in have}
        out = sorted(out + select_beginnings(list(rest.values()), minimum - len(out)), key=lambda o: o["sort"])
    return out


def pick(pool_objs, lenses, subgenres):
    pools = [pool_for(pool_objs, [x], []) for x in lenses] + [pool_for(pool_objs, [], [x]) for x in subgenres]
    return pick_for_subjects(pools)


def choose_objects(api_key, model, story, title, contest, objs, lenses, subgenres, caller, notes):
    """The pool is fixed by rule (every eligible object of the category's lenses and sub-genres, matrix
    first); the model chooses the five to seven that connect to THIS story. A rule cannot judge that:
    the first real run drew Rugged Individualism (1928) and the Nixon pardon into a lab-accident
    category because they share a broad sub-genre. Whatever the model returns is checked against the
    pool; if the call fails, the rule picks."""
    pool = {}
    for x in lenses:
        for o in pool_for(objs, [x], []):
            pool[o["id"]] = o
    for x in subgenres:
        for o in pool_for(objs, [], [x]):
            pool[o["id"]] = o
    if not pool:
        return []
    ordered = sorted(pool.values(), key=lambda o: (o["pool"] != "matrix", o["sort"]))[:90]
    ordered.sort(key=lambda o: o["sort"])
    p = f"""You choose the primary sources for a Backstory category page at NTK. The page shows how today's story sits inside a long argument: a dated list of documents, oldest to newest, each one a step in how we got here.

CATEGORY: {title}
CONTEST: {contest or ''}
TODAY'S STORY: {story['headline']}. {story['text'][:700]}

DOCUMENTS (id | year | title | author | pool | sub-genre):
""" + "\n".join(f"{o['id']} | {o['year']} | {o['title'][:90]} | {o['author'][:40]} | {o['pool']} | {o.get('subgenre') or ''}" for o in ordered) + """

Choose 5 to 7 documents that connect most directly to this story and category. A reader should see why each one is part of the road to today. Rules:
1. Prefer pool=matrix whenever a matrix document connects equally well.
2. Spread them across time, and include the most recent document that truly bears on the story.
3. Do NOT choose a document only because it is about a related branch of government, a general theme, or the same decade. If fewer than 5 connect, choose fewer, but never choose one that does not connect.
4. Use only ids from the list.
JSON only: {"choose":["<id>", ...],"why":"one sentence"}"""
    for attempt in (1, 2):
        try:
            r = caller(api_key, model, "", p, 900)
            if isinstance(r, list):                    # the model answered a bare list of ids
                r = {"choose": r}
            ids = [i for i in ((r.get("choose") if isinstance(r, dict) else None) or []) if i in pool]
            if ids:
                notes.append("objects chosen for relevance: " + ((r.get("why") if isinstance(r, dict) else "") or ""))
                return sorted((pool[i] for i in dict.fromkeys(ids)), key=lambda o: o["sort"])
            notes.append("the model chose no objects from the pool")
        except Exception as e:  # noqa: BLE001
            notes.append(f"object choice failed ({type(e).__name__}: {str(e)[:80]})")
    # The rule is the fallback only for the subjects that are specific (a country or a technology). A broad
    # sub-genre by date is how off-topic documents got in, so with only sub-genres the story gets none.
    notes.append("the rule picked from the lenses alone")
    return pick(objs, lenses, [])


# --- web search, for the trend line ------------------------------------------------------------

def call_search(api_key, model, prompt, max_tokens=3000):
    # Sonnet 5.5 answers HTTP 400 to thinking: disabled (the first real run, 2026-10-09, with the search
    # tool on); between_tools is its thinking-off mode, as in build_pairings.call_claude.
    body = {"model": model, "max_tokens": max_tokens,
            "thinking": {"type": "between_tools" if "sonnet" in model else "disabled"},
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-api-key": api_key,
                                          "anthropic-version": "2023-06-01"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:            # say why: the first real run only said "HTTP 400"
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:400]}") from None
    urls, cites, text = [], [], ""
    for b in d.get("content", []):
        if b.get("type") == "web_search_tool_result" and isinstance(b.get("content"), list):
            urls += [x["url"] for x in b["content"] if x.get("url")]
        if b.get("type") == "text":
            text += b.get("text", "")
            for c in b.get("citations") or []:
                if c.get("url"):
                    cites.append({"url": c["url"], "cited_text": c.get("cited_text", "")})
                    if c["url"] not in urls:
                        urls.append(c["url"])
    if not text.strip():
        raise RuntimeError("the search returned no answer")
    return text, urls, cites


def verify_indicator(ind, urls, cites):
    """The link must be one the search returned, and both figures must be in a cited passage or in the
    model's quoted sentence (which CI then looks for on the page itself)."""
    if not ind.get("source_url"):
        return False, "no source link", None
    if ind["source_url"] not in urls:
        return False, "the link is not one the search returned", None
    nums = [re.sub(r"[^0-9.]", "", str(ind.get(k) or "")) for k in ("then_value", "now_value")]
    has = lambda t: all(n and n in t for n in nums)
    cited = " ".join(c["cited_text"] for c in cites if c["url"] == ind["source_url"])
    if cited and has(cited):
        return True, "cited", [c["cited_text"] for c in cites if c["url"] == ind["source_url"] and c["cited_text"]]
    q = (ind.get("evidence_quote") or "").strip()
    if q and has(q):
        return True, "quoted", [q]
    return False, "both figures do not appear together in a cited or quoted passage", None


def propose_indicator(api_key, model, rec, headline, searcher=None):
    searcher = searcher or call_search
    p = f"""You choose the trend line for a Backstory category page at NTK: ONE measure, shown as a then-and-now pair, of whether things are getting better, getting worse, or are contested on the argument this category is about.

CATEGORY: {rec['title']}
CONTEST: {rec.get('contest') or '(not written yet)'}
STORY FILED UNDER IT: {headline}

Use web search to find a real published figure at its original source (the pollster, agency, court, statistics office or organisation that ran the survey), not an article repeating it. Prefer a measure asked the same way at two dates, or a rate published as a series. Then answer with JSON only:
{{"label":"what is measured, as a reader would say it","then_value":"42%","then_year":"2025","now_value":"75%","direction":"worse|better|contested|flat","source":"the organisation","source_url":"the exact page where you found both figures","as_of":"month and year of the latest figure","evidence_quote":"one sentence copied word for word from that page that states both figures","note":"one sentence on what the two figures are"}}
Rules: both figures must be stated on the page at source_url, in the form you give, and evidence_quote must be copied exactly from it. Do not estimate or calculate. "direction" describes the figure, not your opinion of it: use contested when a rise or fall is not clearly good or bad. If you cannot find such a pair, answer {{"none":"why"}}."""
    text, urls, cites = searcher(api_key, model, p)
    from build_pairings import parse_json_loose
    j = parse_json_loose(text, "trend line")
    if j.get("none"):
        return None, "no trend line found: " + str(j["none"])
    ind = {k: j.get(k) for k in ("label", "then_value", "then_year", "now_value", "direction", "source", "source_url", "as_of", "evidence_quote", "note")}
    ok, how, ev = verify_indicator(ind, urls, cites)
    if not ok:
        return None, "a trend line was proposed but could not be verified (" + how + ")"
    host = re.sub(r"^https?://([^/]+).*$", r"\1", ind["source_url"])
    ind.update(verified=True, verified_by="system", evidence=ev, evidence_source=how,
               how_checked=("Both figures appear in the passage cited from " + host + ".") if how == "cited" else
               "The search returned this page and the quoted sentence holds both figures. Publish confirms them against the page itself.")
    return ind, "trend line found and checked"


# --- compose ------------------------------------------------------------------------------------

def compose(api_key, model, story, name, pool_doc, spec, caller, searcher=None, today=None):
    """Returns (record or None, notes). `caller(api_key, model, system, user, max_tokens)` is call_claude."""
    notes = []
    objs = pool_doc["objects"]
    BYID = {o["id"]: o for o in objs}
    vocab = [x for x in pool_doc.get("vocab", {}).get("subgenres", [])]
    vocab_names = {x["name"] for x in vocab}
    supported = [k for k in spec if not k.startswith("_") and C.lens_supported(k, spec, story["text"])]
    p1 = f"""You write the opening of a new category page for NTK's Backstory, a news product that shows readers how today's story sits inside a long American argument. No existing category fits this story, so this one is new.

CATEGORY NAME (a short noun phrase readers could build expertise in; you may improve it): {name or '(none: choose one)'}
THE STORY FILED UNDER IT:
{story['headline']}
{story['text'][:3500]}

SUBJECT LENSES this text supports (histories of a country, alliance or technology): {', '.join(supported) or '(none)'}
SUB-GENRES (long American arguments, with their row): {'; '.join(x['name'] + ' [' + x['row_title'] + ']' for x in vocab)}

Write JSON only: {{"title":"the category name, 1 to 4 words","contest":"...","stakes":"...","lenses":["..."],"subgenres":["..."],"note":"one sentence for the editor"}}
1. title: a short noun phrase for the whole subject (for example "AI"), not for this one story.
2. contest: ONE sentence ending in a full stop, "Whether X, or Y", two positions a reasonable person holds. 12 to 30 words.
3. stakes: TWO short sentences, 25 to 55 words in all, framed as the open questions the argument turns on (whether, when, by whom, who benefits). Do not write about "risks" in the abstract or "who pays". Write about the category as a whole, not about one story.
4. lenses: choose from the supported lenses only the one or two the category is NAMED for. A lens is for a country, alliance or technology. Do not add a lens because it appears in one incident or is a related topic.
5. subgenres: choose up to two from the sub-genres above that name the American argument this category belongs to, exactly as written, if it belongs to one. Choose at least one lens or one sub-genre: a category needs a history to draw on.
{STYLE}"""
    r1 = caller(api_key, model, "", p1, 1100)
    title = (r1.get("title") or name or "").strip()[:60]
    if not title:
        return None, ["the model gave no category name"]
    lenses = [x for x in (r1.get("lenses") or []) if x in supported]
    subgenres = [x for x in (r1.get("subgenres") or []) if x in vocab_names][:2]
    picked = choose_objects(api_key, model, story, title, r1.get("contest"), objs, lenses, subgenres, caller, notes)
    if not picked:
        return None, [f"no lens or sub-genre with sources matched ({lenses}, {subgenres}); the story keeps its row"]
    approved_auto = [o["id"] for o in picked if o["pool"] == "candidate" and not o.get("approved")]
    need = [o for o in picked if not (o.get("line") and o.get("about"))]
    texts = {}
    if need:
        p2 = f"""You write short text about primary-source documents for NTK's Backstory, for readers who have opted out of the news.

CATEGORY: {title}
For each document below write:
  "line": ONE sentence, 12 to 25 words, saying what was done, starting with the actor or the event (the year is shown beside it). Past tense. Name the act, not its importance.
  "about": TWO to FOUR sentences, at most 70 words: what it is, who made it and when, what it says or did.
Use ONLY the fields given plus plain facts you are certain of. Use no numbers, quotations or dates that are not in the fields. If you cannot write something without guessing, use null for that item.
{STYLE}

DOCUMENTS:
""" + "\n".join(f"- id: {o['id']} | year: {o['year']} | title: {o['title']} | author: {o['author']} | source: {o['source']}"
                + (f" | why it is here: {o['why']}" if o.get("why") else "") for o in need) + """

JSON only: {"<id>":{"line":"...","about":"..."}, ...}"""
        texts = caller(api_key, model, "", p2, 2400) or {}
    # Lines the model wrote that break the rules get one repair round, with the problem named.
    problems = {}
    for o in need:
        t = texts.get(o["id"]) or {}
        lp = C.text_problems("line", (t.get("line") or "").strip(), 12, 25, sentences=1)
        ap = C.text_problems("about", (t.get("about") or "").strip(), 1, 70) if t.get("about") else []
        if lp or ap:
            problems[o["id"]] = lp + ap
    if problems:
        p3 = ("Some text you wrote broke the rules. Rewrite ONLY these, fixing the problem named. A line is ONE sentence of 12 to 25 words. "
              "An about is two to four sentences, at most 70 words.\n" + STYLE + "\n\n"
              + "\n".join(f"- id: {i} | title: {BYID[i]['title']} | year: {BYID[i]['year']} | problem: {'; '.join(ps)} | your text: "
                          f"{json.dumps(texts.get(i))}" for i, ps in problems.items() if i in BYID)
              + '\n\nJSON only: {"<id>":{"line":"...","about":"..."}, ...}')
        try:
            fixed = caller(api_key, model, "", p3, 2000) or {}
            for i, v in fixed.items():
                if i in texts and isinstance(v, dict):
                    texts[i] = {**texts[i], **{k: x for k, x in v.items() if x}}
            notes.append(f"repaired {len(problems)} line(s)")
        except Exception as e:  # noqa: BLE001
            notes.append(f"repair skipped ({type(e).__name__})")
    rec = {
        "id": slug(title), "title": title, "status": "approved", "auto": True,
        "contest": (r1.get("contest") or "").strip(), "stakes": (r1.get("stakes") or "").strip(),
        "lenses": lenses, "subgenres": subgenres, "custom_objects": [], "indicator": None,
        "objects": [{"object_id": o["id"], "about": o.get("about") or (texts.get(o["id"]) or {}).get("about") or "", "by": "model"} for o in picked],
        "beginnings": [{"object_id": o["id"], "line": o.get("line") or (texts.get(o["id"]) or {}).get("line") or "", "by": "model"} for o in picked],
        "by": {"contest": "model", "stakes": "model", "lenses": "model"},
        "approved_objects": approved_auto, "auto_approved": approved_auto,
        "revisions": [{"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "request": "(made automatically)",
                       "summary": r1.get("note") or ""}],
        "created": today or datetime.now(timezone.utc).date().isoformat(),
    }
    if r1.get("note"):
        notes.append(r1["note"])
    try:
        ind, why = propose_indicator(api_key, model, rec, story["headline"], searcher)
        rec["indicator"] = ind
        notes.append("trend line: " + why)
    except Exception as e:  # noqa: BLE001
        notes.append(f"trend line skipped ({type(e).__name__}: {str(e)[:100]})")
    return rec, notes
