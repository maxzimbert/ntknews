#!/usr/bin/env python3
"""
Generate todays_pairings — one Backstory entry per digest story.

Two passes, matching editorial/prompts/:
  5A  classifier-backstory.md  (Haiku)  story -> sub-genre -> row
  5B  pairing-lines.md         (Sonnet) row + story -> one sentence

The prompts are read OUT OF the .md files rather than duplicated here. Those
files are editorial instruments and the only copy; editing them changes the
behaviour of this script directly, which is the point.

Reads   ntk-pulse/data/lineup-publish.json   the certified, published lineup
        digest/data/backstory.json           the 21-row library (vocabulary)
Writes  digest/data/backstory.json           todays_pairings only; rows untouched

Usage from the repo root:
  python3 editorial/build_pairings.py            # real run, needs ANTHROPIC_API_KEY
  python3 editorial/build_pairings.py --mock     # no API calls, deterministic
  python3 editorial/build_pairings.py --dry-run  # print assembled prompts, write nothing

Stdlib only.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINEUP = ROOT / "ntk-pulse" / "data" / "lineup-publish.json"
BACKSTORY = ROOT / "digest" / "data" / "backstory.json"
PROMPTS = ROOT / "editorial" / "prompts"

API_URL = "https://api.anthropic.com/v1/messages"
CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"
PAIRING_MODEL = "claude-sonnet-5"

# Below this the assignment is surfaced for editor review rather than dropped
# (classifier-backstory.md, roll-up rule 5). Nothing is filtered on the front
# end — a low score means "a human should look", not "hide it".
REVIEW_THRESHOLD = 0.55


def log(msg):
    print(msg, file=sys.stderr)


def read_system_prompt(filename):
    """Pull the fenced block under '## System prompt' out of a prompt .md."""
    text = (PROMPTS / filename).read_text()
    m = re.search(r"##\s*System prompt\s*\n+```(?:\w+)?\n(.*?)\n```", text, re.S)
    if not m:
        sys.exit(f"{filename}: no fenced block under '## System prompt'")
    return m.group(1).strip()


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def call_claude(api_key, model, system, user, max_tokens):
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        # These are rubric-bound classification and short-form writing, not
        # multi-step reasoning. Disabled for the same reason pulse.html's ai()
        # disables it: under Sonnet 5 thinking tokens bill out of this same
        # max_tokens ceiling, and reliability matters more here than a
        # speculative quality gain.
        "thinking": {"type": "disabled"},
    }
    req = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    # Filter by block type rather than taking content[0] — a positional read
    # returns undefined the moment a non-text block leads the response.
    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")
    text = text.replace("```json", "").replace("```", "").strip()
    if not text:
        raise RuntimeError(f"{model} returned no text block")
    return json.loads(text)


def build_vocabulary(rows):
    """sub-genre -> row id, plus the vocabulary block shown to the classifier.

    Only rows carrying sub-genres are classifier-reachable. The seven Still
    Counting rows deliberately have none (see build_backstory.py), so they are
    assignable by an editor but never by the model. If a conflict row should be
    machine-reachable, give it sub-genres there.
    """
    lookup, blocks = {}, []
    for r in rows:
        if not r.get("subgenres"):
            continue
        for sg in r["subgenres"]:
            lookup[sg.lower()] = r["id"]
        blocks.append(
            f"{r['title']} — {r.get('milestone') or ''}\n"
            + "\n".join(f"  - {sg}" for sg in r["subgenres"]))
    return lookup, "\n\n".join(blocks)


def classify(api_key, stories, vocab_block, mock):
    user = ("ROW VOCABULARY\n" + vocab_block + "\n\nTODAY'S LINEUP\n"
            + "\n".join(f"{s['story_id']}: {s['headline']}\n  {s['summary']}"
                        for s in stories))
    if mock:
        # Round-robin over the vocabulary: exercises the roll-up, the review
        # threshold and the collision path without spending anything.
        subs = sorted({sg for sg in MOCK_VOCAB})
        return user, [{"story_id": s["story_id"],
                       "subgenre": subs[i % len(subs)],
                       "confidence": 0.9 if i % 3 else 0.4}
                      for i, s in enumerate(stories)]
    system = read_system_prompt("classifier-backstory.md")
    return user, call_claude(api_key, CLASSIFIER_MODEL, system, user, 2000)


def write_lines(api_key, entries, rows_by_id, mock):
    lines = []
    for e in entries:
        row = rows_by_id[e["row"]]
        elapsed = elapsed_words(row["start_date"])
        lines.append(
            f"{e['story_id']}\n  ROW: {row['title']} ({row['id']})\n"
            f"  CONTEST: {row.get('milestone') or ''}\n"
            f"  RUNNING: {row.get('start_line') or row['start_date']} — {elapsed}\n"
            f"  STORY: {e['headline']}\n  SUMMARY: {e['summary']}")
    user = ("TODAY: " + datetime.now(timezone.utc).date().isoformat()
            + "\n\nENTRIES\n" + "\n\n".join(lines))
    if mock:
        return user, [{"story_id": e["story_id"],
                       "row": e["row"],
                       "line": f"[mock line for {e['row']}]"} for e in entries]
    system = read_system_prompt("pairing-lines.md")
    return user, call_claude(api_key, PAIRING_MODEL, system, user, 3000)


def elapsed_words(start_date):
    days = (datetime.now(timezone.utc).date()
            - datetime.fromisoformat(start_date).date()).days
    if days < 60:
        return f"{days} days"
    years = days // 365
    return f"{years} years" if years else f"{days // 30} months"


MOCK_VOCAB = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="no API calls")
    ap.add_argument("--dry-run", action="store_true",
                    help="print assembled prompts, write nothing")
    args = ap.parse_args()

    bs = json.loads(BACKSTORY.read_text())
    rows = bs["rows"]
    rows_by_id = {r["id"]: r for r in rows}
    lookup, vocab_block = build_vocabulary(rows)
    MOCK_VOCAB.extend(lookup.keys())
    log(f"vocabulary: {len(lookup)} sub-genres across "
        f"{sum(1 for r in rows if r.get('subgenres'))} rows "
        f"({sum(1 for r in rows if not r.get('subgenres'))} editor-only)")

    pub = json.loads(LINEUP.read_text())
    stories = [{"story_id": s["key"], "headline": s["headline"],
                "summary": strip_html(s.get("lede")) or strip_html(s.get("truth"))[:220]}
               for s in pub.get("stories", [])]
    if not stories:
        sys.exit("no stories in lineup-publish.json")
    log(f"lineup: {len(stories)} stories")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not (args.mock or args.dry_run):
        sys.exit("ANTHROPIC_API_KEY not set (use --mock to test the plumbing)")

    cls_user, raw = classify(api_key, stories, vocab_block, args.mock or args.dry_run)
    if args.dry_run:
        print("=" * 72)
        print(f"5A CLASSIFIER  —  {CLASSIFIER_MODEL}")
        print("=" * 72)
        print("\n--- SYSTEM ---\n" + read_system_prompt("classifier-backstory.md"))
        print("\n--- USER ---\n" + cls_user)

    # ── Roll-up, in code, not by the model (classifier-backstory.md §Roll-up):
    # one entry per story, always; no dedup, no cap, no floor. Story count in
    # equals entry count out.
    by_id = {c.get("story_id"): c for c in raw if isinstance(c, dict)}
    entries, unmapped = [], []
    for s in stories:
        c = by_id.get(s["story_id"]) or {}
        sub = (c.get("subgenre") or "").lower()
        row_id = lookup.get(sub)
        if not row_id:
            unmapped.append((s["story_id"], c.get("subgenre")))
            continue
        entries.append({**s, "row": row_id, "subgenre": c.get("subgenre"),
                        "confidence": c.get("confidence")})
    for sid, sub in unmapped:
        log(f"  UNMAPPED {sid}: sub-genre {sub!r} not in vocabulary — story dropped")
    if not entries:
        sys.exit("no story mapped to a row; nothing written")

    pair_user, pairs = write_lines(api_key, entries, rows_by_id,
                                   args.mock or args.dry_run)
    if args.dry_run:
        print("\n\n" + "=" * 72)
        print(f"5B PAIRING LINES  —  {PAIRING_MODEL}")
        print("=" * 72)
        print("\n--- SYSTEM ---\n" + read_system_prompt("pairing-lines.md"))
        print("\n--- USER ---\n" + pair_user)
        print("\n" + "=" * 72)
        print("NOTE: row assignments above are round-robin placeholders. A dry "
              "run makes\nno API call, so 5B is fed a stand-in classification "
              "rather than a real one.\nThe wording and structure are exact; "
              "which row each story landed on is not.")
        log("dry run — nothing written")
        return

    lines_by_id = {p.get("story_id"): p.get("line", "") for p in pairs
                   if isinstance(p, dict)}
    out = []
    for e in entries:
        out.append({
            "story_id": e["story_id"], "headline": e["headline"],
            "row": e["row"], "line": lines_by_id.get(e["story_id"], ""),
            "subgenre": e["subgenre"], "confidence": e["confidence"],
            # Surfaced in Pulse for review; never used to hide a card.
            "needs_review": (e["confidence"] or 0) < REVIEW_THRESHOLD,
        })

    counts = {}
    for e in out:
        counts[e["row"]] = counts.get(e["row"], 0) + 1
    collisions = {k: v for k, v in counts.items() if v > 1}

    bs["todays_pairings"] = out
    bs["pairings_generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    BACKSTORY.write_text(json.dumps(bs, indent=2, ensure_ascii=False) + "\n")

    log(f"wrote {len(out)} pairings to {BACKSTORY.relative_to(ROOT)}")
    log(f"  {sum(1 for e in out if e['needs_review'])} below {REVIEW_THRESHOLD} — flagged for review")
    log(f"  {sum(1 for e in out if not e['line'])} with no line")
    if collisions:
        log(f"  collisions (two stories, one row): {collisions}")


if __name__ == "__main__":
    main()
