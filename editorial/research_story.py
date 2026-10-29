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


def research(api_key, story, scope, thin, have, ledger, rejected, searcher=None):
    """Returns (finds_added, note). `have` is the story's Beginnings, so the search does not repeat them."""
    key = subject_key(scope)
    if not key:
        return [], "no subject to research"
    e = ledger["subjects"].get(key) or same_subject(key, ledger)
    if e and recent(e):
        return [], f"already researched on {e['searched_at'][:10]} (for \"{e.get('for', '')[:50]}\"); its {len(e.get('finds') or [])} find(s) are in the library"
    found, notes = CC.find_milestones(api_key, MODEL, {"headline": story["headline"], "text": story.get("truths", "")},
                                      scope, thin or "", have, 4, searcher, call_claude)
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
    ledger["subjects"][key] = {"subject": scope, "searched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "for": story["headline"], "finds": [f["id"] for f in added], "notes": notes[:10]}
    return added, f"researched \"{scope}\": {len(added)} new document(s) kept, {len(notes)} rejected by the checks"
