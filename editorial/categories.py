"""
Backstory category records: validation (T-0079).

A category is composed in Pulse (a model drafts, the editor revises and edits) and carried
in lineup-publish.json as `backstory_categories`. This module is what CI runs on each record
before it can reach a reader. It is authoritative: it drops what fails and never invents a
replacement. Whatever Pulse's own checks said, nothing here trusts them.

Record shape (all text fields carry who wrote them in `by`: "model" or "editor"):

  id            "p-" + slug of the title
  title         the category's name
  status        "draft" (saved, never published) or "approved"
  contest       one "Whether X, or Y" sentence
  stakes        two short sentences
  lenses        subject histories this category draws Beginnings from (editorial/lenses.json)
  subgenres     American arguments (sub-genres of the fixed rows) it also draws Beginnings from
  custom_objects [{id, title, author, year, source, url}] objects the editor added by link
  indicator     a sourced, verified then/now figure, or null
  objects       [{object_id, ...}] the primary sources, each from the pool
  beginnings    [{object_id, year, line}] dated lineage, each also in objects
  by            {"contest": "model", "stakes": "editor", "lenses": "model", ...}
  approved_objects  [object_id] candidates the editor approved in place
  revisions     [{at, request, summary}] what was asked and what changed

Rules the model's text must meet (text the editor wrote is only length-checked: the editor's
voice is not ours to police):
  contest   starts "Whether", 12-30 words
  stakes    exactly two sentences, 25-55 words
  all       no dashes, none of the banned phrases
A lens the model chose must be supported by the text of a story filed under the category.
A lens the editor chose is honoured. An object must be in the pool with a link that is not
dead, and a candidate must be approved. A Beginning's object must belong to one of the
category's lenses (unless the editor put it there) and be dated before the origin.
"""
import re

DENY_HOSTS = ("wikipedia.org", "amazon.", "abebooks.", "ebay.", "goodreads.", "scribd.", "studocu.", "coursehero.", "quizlet.", "unz.com")
BANNED = ["this document", "this reflects", "underscores", "highlights", "serves as",
          "a reminder that", "pivotal", "landmark", "groundbreaking", "seminal"]
SENT = re.compile(r"[.!?](?:[\"')\]]*)(?:\s|$)")


def words(t):
    return len((t or "").split())


def lens_supported(lens, spec, text):
    cfg = spec.get(lens) or {}
    for w in cfg.get("story_terms", []):
        if re.search(r"\b" + re.escape(w) + r"\b", text, re.I):
            return True
    for w in cfg.get("story_terms_cs", []):
        if re.search(r"\b" + re.escape(w) + r"\b", text):
            return True
    return False


def text_problems(label, text, lo, hi, sentences=None, starts=None):
    p = []
    n = words(text)
    if not text or not text.strip():
        return [f"{label} is empty"]
    if not lo <= n <= hi:
        p.append(f"{label} is {n} words, wants {lo} to {hi}")
    if re.search(r"[—–]| -- ", text):
        p.append(f"{label} has a dash")
    if any(b in text.lower() for b in BANNED):
        p.append(f"{label} has a banned phrase")
    norm = text.strip()
    if norm and norm[-1] not in '.!?"\')]':
        norm += "."            # a last sentence with no full stop is still a sentence
    if sentences is not None and len(SENT.findall(norm)) != sentences:
        p.append(f"{label} is not {sentences} sentence{'s' if sentences != 1 else ''}")
    if starts and not text.startswith(starts):
        p.append(f'{label} does not start with "{starts}"')
    return p


def validate(cat, pool, spec, story_texts, origin_year=None, vocab=None):
    """Return (clean_category, problems). `pool` maps object id to a pool entry from
    ntk-pulse/data/backstory-pool.json; `story_texts` is the text of the stories filed
    under this category (may be empty)."""
    problems = []
    c = dict(cat)
    by = dict(c.get("by") or {})
    for f in ("id", "title"):
        if not (c.get(f) or "").strip():
            return None, [f"missing {f}"]
    c["title"] = c["title"].strip()[:60]

    # contest and stakes
    for f, lo, hi, kw in (("contest", 12, 30, {"sentences": 1, "starts": "Whether"}),
                          ("stakes", 25, 55, {"sentences": 2})):
        t = (c.get(f) or "").strip()
        if by.get(f) == "editor":
            p = [] if t and words(t) <= 120 else [f"{f} is empty or over 120 words"]
        else:
            p = text_problems(f, t, lo, hi, **kw)
        if p:
            problems += p
            c[f] = ""            # dropped, never replaced
        else:
            c[f] = t

    # lenses
    keep = []
    text = " ".join(story_texts)
    for lens in c.get("lenses") or []:
        if lens not in spec or lens.startswith("_"):
            problems.append(f"unknown lens {lens!r}")
        elif by.get("lenses") != "editor" and story_texts and not lens_supported(lens, spec, text):
            problems.append(f"lens {lens!r} has no support in the story filed under {c['title']!r}")
        else:
            keep.append(lens)
    c["lenses"] = keep
    sg_keep = []
    for sg in c.get("subgenres") or []:
        if vocab is not None and sg not in vocab:
            problems.append(f"unknown sub-genre {sg!r}")
        else:
            sg_keep.append(sg)
    c["subgenres"] = sg_keep

    # objects the editor added by link become pool entries of their own
    pool = dict(pool)
    for cu in c.get("custom_objects") or []:
        url = (cu.get("url") or "").strip()
        host = re.sub(r"^https?://([^/]+).*$", r"\1", url).lower()
        why = None
        if not url.startswith("https://"):
            why = "a link must start with https://"
        elif any(d in host for d in DENY_HOSTS):
            why = f"{host} is not a primary source"
        elif not re.fullmatch(r"\d{3,4}", str(cu.get("year") or "")):
            why = "year must be a number"
        elif not (cu.get("title") or "").strip():
            why = "missing title"
        if why:
            problems.append(f"added object {cu.get('title')!r}: {why}"); continue
        cid = cu.get("id") or "custom-" + re.sub(r"[^a-z0-9]+", "-", cu["title"].lower())[:60]
        pool[cid] = {"id": cid, "pool": "custom", "approved": True, "title": cu["title"].strip(), "author": cu.get("author") or "",
                     "year": str(cu["year"]), "source": cu.get("source") or host, "url": url, "lenses": [], "subgenre": "",
                     "link_status": "unchecked", "about": "", "line": ""}

    # objects
    approved = set(c.get("approved_objects") or [])
    objs, abouts_seen = [], set()
    for o in c.get("objects") or []:
        e = pool.get(o.get("object_id"))
        if not e:
            problems.append(f"object {o.get('object_id')!r} is not in the pool"); continue
        if e["link_status"] == "dead" or not e["url"]:
            problems.append(f"object {e['title']!r} has no live link"); continue
        if e["pool"] == "candidate" and not (e["approved"] or e["id"] in approved):
            problems.append(f"candidate {e['title']!r} is not approved"); continue
        about = (o.get("about") or e.get("about") or "").strip()
        if about and o.get("by") != "editor":
            ap = text_problems("about", about, 1, 70)
            if about.lower() in abouts_seen:
                ap = ap + ["about is the same text as another object's"]
            if ap:
                problems += [f"{e['title']!r}: {x}" for x in ap]; about = ""
        if about:
            abouts_seen.add(about.lower())
        objs.append({"object_id": e["id"], "title": e["title"], "author": e["author"], "year": e["year"],
                     "source": e["source"], "source_url": e["url"], "about": about,
                     "pool": e["pool"], "lenses": e["lenses"], "by": o.get("by", "model")})
    ids = {o["object_id"] for o in objs}
    c["objects"] = sorted(objs, key=lambda o: (o["year"], o["title"]))

    # beginnings
    begs, seen, lines_seen = [], set(), set()
    for b in c.get("beginnings") or []:
        oid = b.get("object_id")
        o = next((x for x in objs if x["object_id"] == oid), None)
        if not o or oid in seen:
            problems.append(f"Beginning {oid!r} is not among the category's objects"); continue
        if origin_year and str(o["year"]) >= str(origin_year):
            problems.append(f"Beginning {o['title']!r} is dated {o['year']}, not before the origin"); continue
        subjects = set(keep) | set(sg_keep)
        if by.get("lenses") != "editor" and b.get("by") != "editor" and subjects and o["pool"] != "custom" \
                and not (set(o["lenses"]) & set(keep) or pool[o["object_id"]].get("subgenre") in sg_keep):
            problems.append(f"Beginning {o['title']!r} belongs to none of the category's lenses or sub-genres"); continue
        line = (b.get("line") or "").strip()
        if line.lower() in lines_seen:
            problems.append(f"Beginning {o['title']!r}: same line as another Beginning"); continue
        if b.get("by") == "editor":
            lp = [] if line else ["line is empty"]
        else:
            lp = text_problems("line", line, 12, 25, sentences=1)
        if lp:
            problems += [f"Beginning {o['title']!r}: {x}" for x in lp]; continue
        seen.add(oid); lines_seen.add(line.lower()); begs.append({"object_id": oid, "year": o["year"], "line": line, "by": b.get("by", "model")})
    c["beginnings"] = sorted(begs, key=lambda b: b["year"])
    # rule from T-0069: a Beginning is also in The case (already: begins from objects)

    ind = c.get("indicator")
    if ind:
        need = ("label", "then_value", "now_value", "source", "source_url", "as_of")
        miss = [k for k in need if not str(ind.get(k) or "").strip()]
        host = re.sub(r"^https?://([^/]+).*$", r"\1", str(ind.get("source_url") or "")).lower()
        if miss:
            problems.append("indicator is missing " + ", ".join(miss)); c["indicator"] = None
        elif ind.get("verified") is not True:
            problems.append("indicator is not verified"); c["indicator"] = None
        elif any(d in host for d in DENY_HOSTS):
            problems.append(f"indicator source {host} is not a primary source"); c["indicator"] = None
        elif ind.get("verified_by") == "system":
            ev = " ".join(ind.get("evidence") or [])
            nums = [re.sub(r"[^0-9.]", "", str(ind[k])) for k in ("then_value", "now_value")]
            if not ev or any(n and n not in ev for n in nums):
                problems.append("indicator: the system's evidence does not contain both figures"); c["indicator"] = None
    c["by"] = by
    return c, problems


# --- live checks (CI only: they use the network) ---------------------------------------

import html as _html
import urllib.error
import urllib.request

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"


def _fetch(url, limit=700000):
    """(status, text). status 0 means the host could not be reached at all."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read(limit)
            if "pdf" in r.headers.get("content-type", "") or body[:4] == b"%PDF":
                return r.status, ""
            return r.status, _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", "", body.decode("utf-8", "ignore"), flags=re.S))))
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001
        return 0, ""


def live_checks(c):
    """Links the editor added are checked, and an indicator's figures are looked for on
    its source page. Only a definite failure drops something: a host that refuses scripts
    (403, 429, a challenge page) leaves the item in, as the link checker does."""
    problems = []
    keep = []
    for o in c.get("objects") or []:
        if o.get("pool") == "custom":
            st, _ = _fetch(o["source_url"])
            if st in (404, 410) or st == 0:
                problems.append(f"added object {o['title']!r}: the link does not load (status {st})")
                continue
        keep.append(o)
    dropped = {o["object_id"] for o in c.get("objects") or []} - {o["object_id"] for o in keep}
    c["objects"] = keep
    c["beginnings"] = [b for b in c.get("beginnings") or [] if b["object_id"] not in dropped]
    ind = c.get("indicator")
    if ind:
        st, text = _fetch(ind["source_url"])
        if st == 200 and text:
            nums = [re.sub(r"[^0-9.]", "", str(ind[k])) for k in ("then_value", "now_value")]
            gone = [n for n in nums if n and n not in re.sub(r"[^0-9.%\s]", "", text) and n not in text]
            if gone:
                problems.append(f"indicator: {', '.join(gone)} not found on {ind['source_url']}")
                c["indicator"] = None
        elif st in (404, 410):
            problems.append(f"indicator source returns {st}")
            c["indicator"] = None
    return c, problems
