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
    if sentences is not None and len(SENT.findall(text)) != sentences:
        p.append(f"{label} is not {sentences} sentence{'s' if sentences != 1 else ''}")
    if starts and not text.startswith(starts):
        p.append(f'{label} does not start with "{starts}"')
    return p


def validate(cat, pool, spec, story_texts, origin_year=None):
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

    # objects
    approved = set(c.get("approved_objects") or [])
    objs = []
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
            if ap:
                problems += [f"{e['title']!r}: {x}" for x in ap]; about = ""
        objs.append({"object_id": e["id"], "title": e["title"], "author": e["author"], "year": e["year"],
                     "source": e["source"], "source_url": e["url"], "about": about,
                     "pool": e["pool"], "lenses": e["lenses"], "by": o.get("by", "model")})
    ids = {o["object_id"] for o in objs}
    c["objects"] = sorted(objs, key=lambda o: (o["year"], o["title"]))

    # beginnings
    begs, seen = [], set()
    for b in c.get("beginnings") or []:
        oid = b.get("object_id")
        o = next((x for x in objs if x["object_id"] == oid), None)
        if not o or oid in seen:
            problems.append(f"Beginning {oid!r} is not among the category's objects"); continue
        if origin_year and str(o["year"]) >= str(origin_year):
            problems.append(f"Beginning {o['title']!r} is dated {o['year']}, not before the origin"); continue
        if by.get("lenses") != "editor" and b.get("by") != "editor" and keep and not set(o["lenses"]) & set(keep):
            problems.append(f"Beginning {o['title']!r} belongs to none of the category's lenses {keep}"); continue
        line = (b.get("line") or "").strip()
        if b.get("by") == "editor":
            lp = [] if line else ["line is empty"]
        else:
            lp = text_problems("line", line, 12, 25, sentences=1)
        if lp:
            problems += [f"Beginning {o['title']!r}: {x}" for x in lp]; continue
        seen.add(oid); begs.append({"object_id": oid, "year": o["year"], "line": line, "by": b.get("by", "model")})
    c["beginnings"] = sorted(begs, key=lambda b: b["year"])
    # rule from T-0069: a Beginning is also in The case (already: begins from objects)

    ind = c.get("indicator")
    if ind and not (ind.get("verified") is True and ind.get("source") and ind.get("as_of")):
        problems.append("indicator is not verified with a source and a date")
        c["indicator"] = None
    c["by"] = by
    return c, problems
