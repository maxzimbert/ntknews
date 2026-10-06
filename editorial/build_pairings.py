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
from merge_object_notes import BANNED  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LINEUP = ROOT / "ntk-pulse" / "data" / "lineup-publish.json"
BACKSTORY = ROOT / "digest" / "data" / "backstory.json"
PROVISIONAL = ROOT / "ntk-pulse" / "data" / "provisional-rows.json"
PROVISIONAL_MODEL = "claude-sonnet-5"
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


def draft_row(api_key, name, truths_list, contest_file):
    """One model call: a contest line and stakes for a new category, then checked.
    Returns ({"contest", "stakes"} or {}, problems). A failed draft leaves the page
    with the editor's name only: no stakes is better than an unchecked paragraph."""
    sys_ = read_system_prompt("provisional-row.md")
    user = f"CATEGORY: {name}\n\nTRUTHS OF THE STORIES FILED UNDER IT\n" + "\n\n".join(truths_list)
    if contest_file:
        d = json.loads(Path(contest_file).read_text()).get(name) or {}
    elif api_key:
        d = call_claude(api_key, PROVISIONAL_MODEL, sys_, user, 600)
    else:
        return {}, ["no API key; page carries the name only"]
    problems = []
    contest, stakes = (d.get("contest") or "").strip(), (d.get("stakes") or "").strip()
    pool = " ".join(truths_list) + " " + name
    for label, text, lo, hi in (("contest", contest, 12, 30), ("stakes", stakes, 25, 55)):
        if not text:
            problems.append(f"{label} is empty"); continue
        n = len(text.split())
        if not lo <= n <= hi:
            problems.append(f"{label} is {n} words, wants {lo} to {hi}")
        if re.search(r"[\u2014\u2013]| -- ", text):
            problems.append(f"{label} has a dash")
        if any(b in text.lower() for b in BANNED):
            problems.append(f"{label} has a banned phrase")
        for num in re.findall(r"\d[\d,.]*", text):
            if num.strip(",.") not in pool:
                problems.append(f"{label}: number {num} is not in the Truths")
    if contest and not contest.startswith("Whether"):
        problems.append('contest does not start with "Whether"')
    if len(re.findall(r"[.!?](?:\s|$)", stakes)) != 2 and stakes:
        problems.append("stakes is not two sentences")
    if problems:
        return {}, problems
    return {"contest": contest, "stakes": stakes}, []


def sync_provisional(path, stories, bs, api_key, contest_file, today):
    """Create, reuse, expire and inject provisional rows (T-0076).

    A story the editor files under a new category name gets a provisional row
    instead of the closest misfit. Rules, all in code, none by the model:
      reuse    a name that slugs to an existing provisional row joins it
      create   otherwise a new row; the model drafts the contest line and stakes,
               and the draft is validated or dropped
      expire   no story in EXPIRE_DAYS days: archived, no longer shown
      promote  never automatic. `promotion` records what is still missing
    Provisional rows never enter backstory-rows.json and have no sub-genres, so
    the classifier cannot reach them; only an editor tag can.
    """
    store = json.loads(path.read_text()) if path.exists() else {"rows": []}
    by_id = {r["id"]: r for r in store["rows"]}
    for s in stories:
        name = s.get("category")
        if not name:
            continue
        rid = slug(name)
        r = by_id.get(rid)
        if not r:
            draft, probs = draft_row(api_key, name, [s["truths"]], contest_file)
            r = {"id": rid, "title": name, "status": "provisional", "created": today,
                 "contest": draft.get("contest"), "stakes": draft.get("stakes"),
                 "draft_problems": probs, "stories": []}
            store["rows"].append(r); by_id[rid] = r
            log(f"  provisional row created: {name!r}" + (f" ({'; '.join(probs)})" if probs else ""))
        if not any(x["story_id"] == s["story_id"] for x in r["stories"]):
            r["stories"].append({"story_id": s["story_id"], "date": today, "headline": s["headline"]})
        r["last_story"] = today
        s["editor_row"] = rid
    cutoff = (datetime.fromisoformat(today) - __import__("datetime").timedelta(days=EXPIRE_DAYS)).date().isoformat()
    for r in store["rows"]:
        if r["status"] == "provisional" and r.get("last_story", r["created"]) < cutoff:
            r["status"] = "archived"
            log(f"  provisional row archived (no story since {r.get('last_story')}): {r['title']!r}")
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
            "indicator": None, "objects": [], "beginnings": [], "subgenres": [], "roots": [],
            "updated": False, "narrative": None, "instances": [], "photo": None})
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
    ap.add_argument("--contest-file", help="test hook: JSON {name: {contest, stakes}} instead of the model")
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
                "editor_row": s.get("backstory_row") or None,
                # T-0076: a category the editor named because no row fits (Pulse
                # "no row fits"). It becomes a provisional row.
                "category": (s.get("backstory_category") or "").strip() or None}
               for s in pub.get("stories", [])]
    if not stories:
        sys.exit("no stories in lineup-publish.json")
    log(f"lineup: {len(stories)} stories")

    # -- Provisional rows (T-0076): a story filed under a new category gets its own
    # row now, not the nearest misfit.
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    sync_provisional(Path(args.provisional), stories, bs, api_key, args.contest_file,
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
