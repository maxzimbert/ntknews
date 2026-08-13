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
    drift as the window rolls — is recognized via the same entity+cosine
    matcher cluster.py already uses, and skipped rather than duplicated.
  - assembly.py's next full run (every 4 hours) does its own complete,
    more careful selection and naturally supersedes whatever this script
    added in between. That's intentional, not a bug: this script's job is
    faster visibility, not final editorial judgment.

Reads  data/clusters.json (this run's fresh clustering)
Reads  data/lineup.json   (if present — never required to exist)
Writes data/lineup.json   (existing entries preserved, new ones appended)

Stdlib only, same posture as the rest of the pipeline.
"""
import json
from pathlib import Path

from cluster import entities, build_vectors, cosine

ROOT = Path(__file__).parent
DATA = ROOT / "data"

PROMOTE_MIN_PUBLISHERS = 2  # "2-3+ publishers" as specified — floor at 2
MATCH_THRESHOLD = 0.20      # entity+cosine bar for "already represented"


def log(msg):
    print(f"[promote] {msg}", flush=True)


def already_represented(candidate_title, candidate_entities, existing_stories, idf_pool):
    """Is this cluster already sitting in the lineup under some other key?
    Keys drift as the window rolls (the representative article shifts every
    run) — a title-level fuzzy match is what actually answers "is this the
    same story," not an exact key comparison."""
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
    for c in candidates:
        cand_ents = entities(c["title"])
        pool = idf_pool + [{"id": "__candidate__", "title": c["title"], "summary": ""}]
        if already_represented(c["title"], cand_ents, existing, pool):
            continue

        tri = c.get("triage") or {}
        existing.append({
            "slot": "promoted", "slot_label": "New",
            "key": c["key"],
            "title": tri.get("headline") or c["title"],
            "beat": tri.get("beat") or c.get("beat_hint", "other"),
            "publisher_count": c["publisher_count"],
            "publishers": c.get("publishers", []),
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
    log(f"{promoted} new stories promoted, {len(existing)} total in lineup")


if __name__ == "__main__":
    main()
