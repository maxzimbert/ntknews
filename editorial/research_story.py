"""
Research once (T-0111): fill a thin story's library gap with one web-search call, and keep what it finds for
every later story, so no subject is searched twice.

The ledger (editorial/research-ledger.json) holds:
  subjects  {key: {"subject", "searched_at", "for", "finds": [id], "notes"}}   what was searched, and when
  finds     [object]   every find that passed the checks; compose_story.load_library treats them as library
                       documents, so they serve every story, not just the one that paid for them
  series    [indicator]   checked chart series (T-0112)
Research runs only when the editor asks ("research it" on a thin page in Pulse), at most BUDGET calls per
draft run, and never for a subject searched in the last RECENT_DAYS: that answer is "already researched",
and its finds are already in the library. The search and its checks are compose_category.find_milestones,
unchanged: the link is one the search returned, a primary source, every number traceable to the quote.
A find the editor rejected (bs_rejected) is never added, and stays out on every later run.
"""
import re
from datetime import datetime, timezone, timedelta

import compose_category as CC
from build_pairings import call_claude

MODEL = "claude-sonnet-5-5"
BUDGET = 3              # research calls per draft run
RECENT_DAYS = 30
STOP = {"and", "the", "of", "in", "on", "a", "an", "to", "for", "its", "their", "us", "u.s"}


def subject_key(subject):
    words = sorted({w for w in re.findall(r"[a-z0-9]+", str(subject or "").lower()) if w not in STOP})
    return " ".join(words)


def same_subject(key, ledger, at=0.5):
    """A subject searched under other words. A page's scope is reworded each time it is recomposed
    ("Federal agents' anonymity and exposure", then "Federal immigration agents' public exposure"), and a
    second search ran on the second name (2026-10-29). Half the words shared counts as the same subject."""
    a = set(key.split())
    best, score = None, 0.0
    for k, e in ledger["subjects"].items():
        b = set(k.split())
        j = len(a & b) / len(a | b) if a | b else 0
        if j >= at and j > score and recent(e):
            best, score = e, j
    return best


def recent(entry, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        t = datetime.fromisoformat(entry["searched_at"])
    except (KeyError, ValueError):
        return False
    return now - t < timedelta(days=RECENT_DAYS)


def research(api_key, story, scope, thin, have, ledger, rejected, searcher=None, direction=None, story_id=None):
    """Returns (finds_added, note). `have` is the story's Beginnings, so the search does not repeat them.
    `direction` is the editor's own pointer for this search; it makes a subject of its own, so a directed search
    is not refused because the page's subject was researched, but the same direction is not run twice."""
    key = subject_key(scope + " " + direction) if direction else subject_key(scope)
    if not key:
        return [], "no subject to research"
    e = ledger["subjects"].get(key) or (None if direction else same_subject(key, ledger))
    if e and recent(e):
        return [], f"already researched on {e['searched_at'][:10]} (for \"{e.get('for', '')[:50]}\"); its {len(e.get('finds') or [])} find(s) are in the library"
    vetoed = []
    found, notes = CC.find_milestones(api_key, MODEL, {"headline": story["headline"], "text": story.get("truths", "")},
                                      scope, thin or "", have, 6 if direction else 4, searcher, call_claude,
                                      direction=direction, vetoed=vetoed)
    rej = set(rejected)
    have_urls = {f["url"] for f in ledger["finds"]}
    added = []
    for f in found:
        if f["id"] in rej or f["url"] in have_urls:
            continue
        f = dict(f, source_kind=CC.C.source_kind(f["url"]), researched_for=scope,
                 researched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        ledger["finds"].append(f)
        have_urls.add(f["url"])
        added.append(f)
    known = {f["url"] for f in ledger["finds"]} | {v["url"] for v in ledger["vetoed"]}
    for v in vetoed:                     # shown to the editor with the reason, who can approve it (T-0111)
        if v["id"] not in rej and v["url"] not in known:
            ledger["vetoed"].append(dict(v, researched_for=scope, story_id=story_id, direction=direction,
                                         researched_at=datetime.now(timezone.utc).isoformat(timespec="seconds")))
            known.add(v["url"])
    ledger["subjects"][key] = {"subject": scope, "direction": direction, "searched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "for": story["headline"], "finds": [f["id"] for f in added], "notes": notes[:10]}
    what = f"\"{direction}\"" if direction else f"\"{scope}\""
    return added, f"researched {what}: {len(added)} new document(s) kept, {len(vetoed)} vetoed by the checks (shown below to approve or leave)"


def approve(ledger, ids, story_id):
    """The editor overrules the checks: a vetoed find becomes a library document, marked as the editor's call."""
    moved = []
    for v in list(ledger["vetoed"]):
        if v["id"] in ids:
            ledger["vetoed"].remove(v)
            f = dict(v, approved_by="editor", approved_for=story_id, source_kind=CC.C.source_kind(v["url"]),
                     approved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            ledger["finds"].append(f)
            moved.append(f)
    return moved
