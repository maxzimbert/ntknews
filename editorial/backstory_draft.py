#!/usr/bin/env python3
"""
The Backstory draft at publish (T-0109, T-0114): Pulse builds each story's page into backstory-draft.json; publish ships it.

  apply  at publish (T-0114, the contract): each story ships the page the editor built and reviewed in
         Pulse, if its bs_hash still matches; a story not built, or changed since, ships no Backstory.
         Nothing is chosen at publish.

bs_hash is written by Pulse (one implementation, in JavaScript) over the fields that decide a story's
Backstory: its text, the row the editor filed it under, and that category's record as Pulse sends it.
This script only compares the strings.

  python3 editorial/backstory_draft.py apply [--github-output "$GITHUB_OUTPUT"]

Stdlib only.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFT = ROOT / "ntk-pulse" / "data" / "backstory-draft.json"
LINEUP = ROOT / "ntk-pulse" / "data" / "lineup-publish.json"
BACKSTORY = ROOT / "digest" / "data" / "backstory.json"
PROVISIONAL = ROOT / "ntk-pulse" / "data" / "provisional-rows.json"
ORIGINS = ROOT / "editorial" / "origins.json"
# What a composed page carries for the review in Pulse and readers never see (T-0114, T-0117).
REVIEW_ONLY = ("notes", "usage", "shortlist", "model", "terms", "research_items", "problems", "scopes", "scope_picks",
               "left_out", "review", "weak", "held", "shipped_anyway", "steps", "widened", "gaps")


def log(msg):
    print(msg, file=sys.stderr)


def load(p):
    return json.loads(Path(p).read_text())


def dump(p, d, indent=2):
    Path(p).write_text(json.dumps(d, indent=indent, ensure_ascii=False) + "\n")


def apply(args):
    """T-0114, the contract: each story ships the Backstory built for it in Pulse, or none. A story ships when the
    draft holds a page built to the contract (composed v2) and its bs_hash still matches the Lineup's; any other
    story, unbuilt or changed since it was built, goes out with no Backstory. Nothing is chosen at publish.
    The draft's trend lines for rows (ship.row_indicators) go onto the rows."""
    lineup, bs = load(args.lineup), load(args.backstory)
    draft = load(args.draft) if Path(args.draft).exists() else {"stories": [], "ship": {}}
    ship = draft.get("ship") or {}
    by = {d["story_id"]: d for d in draft.get("stories", [])}
    pairs = {p["story_id"]: p for p in ship.get("todays_pairings", [])}
    out, left = [], []
    for st in lineup.get("stories", []):
        k, d = st["key"], by.get(st["key"])
        c = (d or {}).get("composed") or {}
        if not d or c.get("v") != 2:
            left.append(f"{k}: not built")
            continue
        if not st.get("bs_hash") or d.get("bs_hash") != st["bs_hash"]:
            left.append(f"{k}: changed since it was built")
            continue
        # T-0117: a weak page is held in Pulse until the editor clicks Ship anyway (the editor, 2026-11-10).
        # Pulse clears `held` when he does; the choice also rides in the edits, so either says ship.
        if c.get("held") and not (d.get("bs_edits_applied") or {}).get("ship_anyway"):
            left.append(f"{k}: held: weak, not released ({'; '.join(c.get('weak') or []) or 'weak'})")
            continue
        p = dict(pairs.get(k) or d.get("pairing") or {})
        if not p.get("row"):
            left.append(f"{k}: no row")
            continue
        p["composed"] = {kk: v for kk, v in c.items() if kk not in REVIEW_ONLY}
        p["line"] = c.get("here") or p.get("line") or ""
        out.append(p)
    if ship.get("provisional_rows") is not None and out:
        bs["rows"] = [r for r in bs["rows"] if r.get("stratum") != "provisional"] + ship["provisional_rows"]
    for r in bs["rows"]:
        ind = (ship.get("row_indicators") or {}).get(r["id"])
        if ind:
            r["indicator"], r["indicator_by"] = ind, "pulse"     # kept by build_backstory.py's carry()
    bs["todays_pairings"] = out
    bs["pairings_generated"] = ship.get("pairings_generated") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    dump(args.backstory, bs)
    if out and ship.get("provisional_store"):
        dump(args.provisional, ship["provisional_store"])
    log(f"Backstory: {len(out)} of {len(lineup.get('stories', []))} stories ship a page"
        + ("; without one:\n  " + "\n  ".join(left) if left else ""))
    if args.github_output:
        with open(args.github_output, "a") as f:
            f.write(f"shipped={len(out)}\n")
    print(f"shipped {len(out)}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--draft", default=str(DRAFT))
    a.add_argument("--lineup", default=str(LINEUP))
    a.add_argument("--backstory", default=str(BACKSTORY))
    a.add_argument("--provisional", default=str(PROVISIONAL))
    a.add_argument("--origins", default=str(ORIGINS))
    a.add_argument("--github-output")
    args = ap.parse_args()
    apply(args)


if __name__ == "__main__":
    main()
