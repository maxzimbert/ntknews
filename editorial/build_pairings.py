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

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
LINEUP = ROOT / "ntk-pulse" / "data" / "lineup-publish.json"
BACKSTORY = ROOT / "digest" / "data" / "backstory.json"
PROVISIONAL = ROOT / "ntk-pulse" / "data" / "provisional-rows.json"
EXPIRE_DAYS = 30
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
    # T-0076: the classifier reads the full Truths (300 to 460 words), not just the
    # headline and a 14 to 35 word summary. A story's argument is rarely in its lede.
    user = ("ROW VOCABULARY\n" + vocab_block + "\n\nTODAY'S LINEUP\n"
            + "\n".join(f"{s['story_id']}: {s['headline']}\n  {s.get('truths') or s['summary']}"
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


def slug(name):
    return "p-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]


def apply_categories(path, pub, stories, bs, today):
    """Merge the categories Pulse sent into the store, validate them, expire, and inject (T-0079).

    Pulse composes a category (a model drafts, the editor revises and edits) and carries the
    whole record in lineup-publish.json as `backstory_categories`. Here each approved record
    is validated by editorial/categories.py, which drops what fails and invents nothing, then
    stored in ntk-pulse/data/provisional-rows.json and injected into the published rows.
      draft      saved in Pulse, never published: ignored here
      expire     no story filed under it for EXPIRE_DAYS days: archived, no longer shown
      promote    never automatic. `promotion` records what is still missing
    Categories never enter backstory-rows.json and have no sub-genres, so the classifier
    cannot reach them; only an editor tag (a story's backstory_row) can.
    """
    import categories
    store = json.loads(path.read_text()) if path.exists() else {"rows": []}
    by_id = {r["id"]: r for r in store["rows"]}
    pool_doc = json.loads((ROOT / "ntk-pulse" / "data" / "backstory-pool.json").read_text())
    pool = {o["id"]: o for o in pool_doc["objects"]}
    spec = json.loads((ROOT / "editorial" / "lenses.json").read_text())
    for cat in pub.get("backstory_categories") or []:
        cid = cat.get("id") or ""
        if cat.get("status") != "approved":
            log(f"  category {cid!r} is a draft; not published")
            continue
        filed = [s for s in stories if s.get("editor_row") == cid]
        clean, probs = categories.validate(cat, pool, spec, [s["text"] for s in filed])
        if not clean:
            log(f"  category {cid!r} rejected: {'; '.join(probs)}")
            continue
        if probs:
            log(f"  category {cid!r}: dropped {len(probs)} part(s): " + "; ".join(probs[:4]))
        r = by_id.get(cid)
        if not r:
            r = {"id": cid, "created": today, "stories": []}
            store["rows"].append(r); by_id[cid] = r
            log(f"  category created: {clean['title']!r}")
        keep = {k: r[k] for k in ("created", "stories", "last_story", "start_date", "start_line") if k in r}
        r.clear(); r.update(clean); r.update(keep)
        r["status"] = "provisional"; r["draft_problems"] = probs
        for s in filed:
            if not any(x["story_id"] == s["story_id"] for x in r["stories"]):
                r["stories"].append({"story_id": s["story_id"], "date": today, "headline": s["headline"]})
        if filed:
            r["last_story"] = today
    cutoff = (datetime.fromisoformat(today) - __import__("datetime").timedelta(days=EXPIRE_DAYS)).date().isoformat()
    for r in store["rows"]:
        if r["status"] == "provisional" and r.get("last_story", r["created"]) < cutoff:
            r["status"] = "archived"
            log(f"  category archived (no story since {r.get('last_story')}): {r['title']!r}")
        days = {x["date"] for x in r["stories"]}
        missing = []
        if len(r["stories"]) < 3 or len(days) < 2:
            missing.append(f"needs 3 stories on 2 days (has {len(r['stories'])} on {len(days)})")
        missing.append("needs 3 linked matrix objects and a sourced indicator")
        r["promotion"] = {"ready": False, "missing": missing}
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n")
    # inject into the published rows: rebuilt each run from the store
    bs["rows"] = [r for r in bs["rows"] if r.get("stratum") != "provisional"]
    for r in store["rows"]:
        if r["status"] != "provisional":
            continue
        bs["rows"].append({
            "id": r["id"], "stratum": "provisional", "title": r["title"],
            "start_date": r.get("start_date") or r["created"], "start_line": r.get("start_line"),
            "milestone": r.get("contest") or "", "stakes": r.get("stakes"),
            "indicator": r.get("indicator"), "objects": r.get("objects") or [],
            "beginnings": r.get("beginnings") or [], "lenses": r.get("lenses") or [],
            "subgenres": [], "roots": [], "updated": False, "narrative": None, "instances": [], "photo": None})
    return store


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
    ap.add_argument("--lineup", default=str(LINEUP), help="test hook")
    ap.add_argument("--backstory", default=str(BACKSTORY), help="test hook")
    ap.add_argument("--provisional", default=str(PROVISIONAL), help="test hook")
    ap.add_argument("--dry-run", action="store_true",
                    help="print assembled prompts, write nothing")
    args = ap.parse_args()

    bs = json.loads(Path(args.backstory).read_text())
    rows = bs["rows"]
    rows_by_id = {r["id"]: r for r in rows}
    lookup, vocab_block = build_vocabulary(rows)
    MOCK_VOCAB.extend(lookup.keys())
    log(f"vocabulary: {len(lookup)} sub-genres across "
        f"{sum(1 for r in rows if r.get('subgenres'))} rows "
        f"({sum(1 for r in rows if not r.get('subgenres'))} editor-only)")

    pub = json.loads(Path(args.lineup).read_text())
    stories = [{"story_id": s["key"], "headline": s["headline"],
                "summary": strip_html(s.get("lede")) or strip_html(s.get("truth"))[:220],
                "truths": strip_html(s.get("truth")),
                "text": " ".join(strip_html(s.get(k)) for k in ("truth", "prob", "poss", "lies")),
                "editor_row": s.get("backstory_row") or None,
                }
               for s in pub.get("stories", [])]
    if not stories:
        sys.exit("no stories in lineup-publish.json")
    log(f"lineup: {len(stories)} stories")

    # -- Categories (T-0079): the editor composes them in Pulse; a story filed under one
    # carries its id as backstory_row. Applied before the editor-row check below, so the
    # row exists when the story is looked up.
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    apply_categories(Path(args.provisional), pub, stories, bs,
                     datetime.now(timezone.utc).date().isoformat())
    rows = bs["rows"]
    rows_by_id = {r["id"]: r for r in rows}

    # -- Editor assignments (T-0010) win over the classifier.
    # Pulse writes backstory_row per story at certification time. An assignment
    # the editor made is reviewed editorial and is not re-litigated by a model.
    # It also reaches the seven rows that carry no sub-genres and so are
    # unreachable by classification at all (T-0012).
    #
    # An unknown row id falls back to the classifier rather than being trusted:
    # a stale id left behind by a renamed row would otherwise produce a pairing
    # against a row the renderer cannot resolve, which is silently dropped at
    # the far end and looks like a missing card.
    for s in stories:
        if s["editor_row"] and s["editor_row"] not in rows_by_id:
            log(f"  editor row {s['editor_row']!r} on {s['story_id']} is not in "
                f"the library - falling back to the classifier")
            s["editor_row"] = None
    to_classify = [s for s in stories if not s["editor_row"]]
    if len(to_classify) < len(stories):
        log(f"editor-assigned: {len(stories) - len(to_classify)} of {len(stories)}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not (args.mock or args.dry_run):
        sys.exit("ANTHROPIC_API_KEY not set (use --mock to test the plumbing)")

    if to_classify:
        cls_user, raw = classify(api_key, to_classify, vocab_block,
                                 args.mock or args.dry_run)
    else:
        cls_user = "(every story carries an editor assignment - 5A skipped)"
        raw = []
        log("5A skipped - nothing left to classify")
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
        if s["editor_row"]:
            entries.append({**s, "row": s["editor_row"], "subgenre": None,
                            "confidence": 1.0})
            continue
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
            # Which of the two paths put this row here. The editor needs to
            # know whether they are looking at their own call or the model's.
            "source": "editor" if e.get("editor_row") else "classifier",
            # Surfaced in Pulse for review; never used to hide a card.
            "needs_review": (e["confidence"] or 0) < REVIEW_THRESHOLD,
            **({"provisional": True} if str(e["row"]).startswith("p-") else {}),
        })

    counts = {}
    for e in out:
        counts[e["row"]] = counts.get(e["row"], 0) + 1
    collisions = {k: v for k, v in counts.items() if v > 1}

    bs["todays_pairings"] = out
    bs["pairings_generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    Path(args.backstory).write_text(json.dumps(bs, indent=2, ensure_ascii=False) + "\n")

    log(f"wrote {len(out)} pairings to {args.backstory}")
    log(f"  {sum(1 for e in out if e['needs_review'])} below {REVIEW_THRESHOLD} — flagged for review")
    log(f"  {sum(1 for e in out if not e['line'])} with no line")
    if collisions:
        log(f"  collisions (two stories, one row): {collisions}")


if __name__ == "__main__":
    main()
