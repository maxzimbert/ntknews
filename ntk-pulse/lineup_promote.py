#!/usr/bin/env python3
"""NTK Pulse — Stream to Lineup, automatic promotion.

Runs on the cheap 20-minute schedule, right after triage. Watches every
fresh clustering pass for anything that's cleared real corroboration —
2 or more independent publishers — and, if it isn't already represented
in the current lineup, adds it. No approval step. This is what makes
"new and juicy" actually flow, rather than waiting up to 4 hours for the
next full assembly run.

Deliberately additive, never destructive:
  - Existing lineup.json entries (whether from assembly.py's own selection
    or a previous promotion run) are never touched or removed.
  - A cluster already represented — even under a DIFFERENT key, since keys
    drift as the window rolls — is recognized and skipped rather than
    duplicated. Recognition is URL-overlap first (see the note below),
    falling back to the original entity+cosine title match for stories
    that don't have recorded URLs yet, or for genuinely URL-disjoint
    coverage of the same event.
  - assembly.py's next full run (every 4 hours) does its own complete,
    more careful selection and naturally supersedes whatever this script
    added in between. That's intentional, not a bug: this script's job is
    faster visibility, not final editorial judgment.

Dedup (2026-08-14): title-fuzzy-matching missed real duplicates because the
*articles* underneath a story are stable across runs but the *representative
headline* cluster.py picks can drift as the window rolls — title similarity
is exactly what breaks when phrasing drifts. A sturdier signal sits one
level down: do a candidate's member URLs overlap an already-promoted
story's URLs? The same AP/Reuters piece keeps the same canonical URL run
after run no matter how the representative headline gets reworded around
it. URLs are canonicalized before comparison. Title-fuzzy-match is kept as
a fallback for what URL-overlap can't see: two genuinely different
articles, from different publishers, independently covering the same event
with no shared source piece.

Roundup filter (2026-08-14): "Weekly culture roundup," "Movie review
roundup," and similar clusters aren't single stories — they're a
publisher's own aggregation of several unrelated items. The 2+ publisher
bar doesn't distinguish that from a real story, so it gets its own check,
applied before dedup: a roundup-titled cluster is never eligible for
promotion.

Reads  data/clusters.json (this run's fresh clustering)
Reads  data/lineup.json   (if present — never required to exist)
Writes data/lineup.json   (existing entries preserved, new ones appended)

Stdlib only, same posture as the rest of the pipeline.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from cluster import entities, build_vectors, cosine

ROOT = Path(__file__).parent
DATA = ROOT / "data"

PROMOTE_MIN_PUBLISHERS = 2  # "2-3+ publishers" as specified — floor at 2
MATCH_THRESHOLD = 0.20      # entity+cosine bar for the title-match fallback
URL_OVERLAP_MIN = 1         # shared canonical URLs needed to call it a dupe

# Query params that vary per-share/per-click but don't change the article.
# Extend as new tracking schemes turn up in real feeds.
TRACKING_PARAM_PREFIXES = ("utm_",)
TRACKING_PARAMS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "ref_url",
    "cmpid", "icid", "smid", "s", "src",
}

# Title patterns for roundup/aggregation-style clusters — a publisher's own
# digest of several unrelated items, not a single story. Grow this list
# only after seeing a real false-promote, same discipline as the rest of
# this file's tuning.
ROUNDUP_TITLE_PATTERNS = [
    r"\bround[\s-]?up\b",
    r"\bweek(?:ly)? in review\b",
    r"\brecap\b",
    r"\bwrap[\s-]?up\b",
    r"\bbest of (?:the )?(?:week|month|year)\b",
    r"\beverything you missed\b",
    r"\bin case you missed\b",
    r"\bquick hits\b",
    r"\btop \d+\b.*\b(?:stories|headlines|reads)\b",
]
_ROUNDUP_RE = re.compile("|".join(ROUNDUP_TITLE_PATTERNS), re.IGNORECASE)


def log(msg):
    print(f"[promote] {msg}", flush=True)


def is_roundup(title):
    """Is this cluster's representative title an aggregation/roundup rather
    than a single story? Checked once per candidate, before dedup — a
    roundup is never eligible for promotion regardless of publisher count."""
    return bool(_ROUNDUP_RE.search(title or ""))


def canonicalize_url(url):
    """Strip tracking params, scheme, www/amp prefix, and trailing slash so
    the same article reached two different ways still compares equal.
    Best-effort — malformed URLs fall back to a stripped/lowered string."""
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
        netloc = parts.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if netloc.startswith("amp."):
            netloc = netloc[4:]
        path = parts.path.rstrip("/")
        if path.endswith("/amp"):
            path = path[: -len("/amp")]
        kept = [
            (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS
            and not k.lower().startswith(TRACKING_PARAM_PREFIXES)
        ]
        query = urlencode(sorted(kept))
        return urlunsplit(("", netloc, path, query, ""))
    except Exception:
        return url.strip().lower().rstrip("/")


def cluster_urls(cluster):
    """Canonical URL set for every member article in a cluster. Cluster
    items come straight from window.json via cluster.py, so this expects
    the same 'url' field ingest.py has always written."""
    return {
        canonicalize_url(it.get("url", ""))
        for it in cluster.get("items", [])
        if it.get("url")
    }


def title_match(candidate_title, candidate_entities, existing_stories, idf_pool):
    """Fallback for when URL-overlap finds nothing: the original entity+
    cosine title similarity. Covers two genuinely different articles,
    from different publishers, independently covering the same event with
    no shared source piece — URL-overlap can't see that case by design."""
    if not existing_stories:
        return False
    vecs = build_vectors(idf_pool)
    cand_vec = vecs.get("__candidate__")
    if not cand_vec:
        return False
    for i, story in enumerate(existing_stories):
        story_id = f"__existing_{i}__"
        if story_id not in vecs:
            continue
        sim = cosine(cand_vec, vecs[story_id])
        story_ents = entities(story.get("title", ""))
        shared = candidate_entities & story_ents
        if shared and sim >= MATCH_THRESHOLD:
            return True
    return False


def already_represented(cluster, existing_stories, idf_pool):
    """Is this cluster already sitting in the lineup under some other key?
    URL-overlap is checked first — the sturdier signal, since it doesn't
    drift the way title similarity does when the representative headline
    changes run to run. Falls back to title_match for stories that don't
    have any 'urls' recorded yet (pre-migration lineup entries) or for
    URL-disjoint coverage of the same event."""
    cand_urls = cluster_urls(cluster)
    if cand_urls:
        for story in existing_stories:
            story_urls = set(story.get("urls") or [])
            if story_urls and len(cand_urls & story_urls) >= URL_OVERLAP_MIN:
                return True

    candidate_entities = entities(cluster["title"])
    return title_match(cluster["title"], candidate_entities, existing_stories, idf_pool)


def main():
    clusters_path = DATA / "clusters.json"
    lineup_path = DATA / "lineup.json"

    if not clusters_path.exists():
        log("no clusters.json yet — nothing to promote from")
        return

    clusters = json.loads(clusters_path.read_text()).get("clusters", [])

    if lineup_path.exists():
        lineup = json.loads(lineup_path.read_text())
    else:
        # First run, or assembly.py has genuinely never fired yet. Build a
        # minimal, honest shell rather than pretending an edition exists.
        lineup = {
            "assembled_at": None, "slot_plan": "A", "daytype": "weekday",
            "target_size": [8, 10], "actual_size": 0, "lint_failures": [],
            "slots_unfilled": [], "stories": [], "excluded_sample": [],
        }
    existing = lineup.setdefault("stories", [])
    existing_keys = {s["key"] for s in existing}

    # Build the IDF pool once: every existing story's title plus every
    # promotion candidate's title, so similarity is computed over a
    # consistent, shared vocabulary rather than pairwise in isolation.
    idf_pool = [{"id": f"__existing_{i}__", "title": s.get("title", ""), "summary": ""}
                for i, s in enumerate(existing)]

    candidates = [c for c in clusters
                  if c.get("publisher_count", 0) >= PROMOTE_MIN_PUBLISHERS
                  and c["key"] not in existing_keys]

    promoted = 0
    skipped_roundup = 0
    for c in candidates:
        if is_roundup(c["title"]):
            skipped_roundup += 1
            log(f"  skipped (roundup): {c['title'][:60]}")
            continue

        pool = idf_pool + [{"id": "__candidate__", "title": c["title"], "summary": ""}]
        if already_represented(c, existing, pool):
            continue

        tri = c.get("triage") or {}
        existing.append({
            "slot": "promoted", "slot_label": "New",
            "key": c["key"],
            "title": tri.get("headline") or c["title"],
            "beat": tri.get("beat") or c.get("beat_hint", "other"),
            "publisher_count": c["publisher_count"],
            "publishers": c.get("publishers", []),
            "urls": sorted(cluster_urls(c)),
            "scores": {k: tri.get(k, 3) for k in
                       ("emotional_load", "explainability", "actionability",
                        "conversational_currency")},
            "politician_led": tri.get("politician_led", False),
            "ledger_class": None,   # ledger hasn't necessarily reached this yet
            "new_facts": [],
            "line": tri.get("line", ""),
            "assembly_score": c.get("pulse_score", 0),
        })
        existing_keys.add(c["key"])
        promoted += 1
        log(f"  promoted: {c['title'][:60]} ({c['publisher_count']} pubs)")

    lineup["actual_size"] = len(existing)
    lineup_path.write_text(json.dumps(lineup, indent=1))
    log(f"{promoted} new stories promoted, {skipped_roundup} roundups skipped, "
        f"{len(existing)} total in lineup")


if __name__ == "__main__":
    main()
