#!/usr/bin/env python3
"""Tabulate Backstory build rounds from the draft's history on a branch (T-0117's before-and-after).

Each "Build Backstory for every story" in Pulse saves the draft once, as one commit ("backstory: N page(s) from
Pulse") on the branch Pulse is served from: `main` for live Pulse, `staging` for staging Pulse. This reads every
such commit since a time and prints, per page it rebuilt: milestones, flagged lines, left out, the scope, whether it widened,
whether it searched, the self-review, held, and tokens. It reads git only; it calls no model.

  git fetch origin
  python3 scripts/backstory_rounds.py --branch origin/staging --since 2026-11-11T00:00
  python3 scripts/backstory_rounds.py --branch origin/main --since 2026-11-11T00:00

Stdlib only.
"""
import argparse
import json
import subprocess

DRAFT = "ntk-pulse/data/backstory-draft.json"


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def row(c):
    b = c.get("beginnings") or []
    rv = c.get("review") or {}
    u = c.get("usage") or {}
    return {
        "milestones": len(b),
        "editor": sum(1 for x in b if x.get("by") == "editor"),
        "flagged": sum(1 for x in b if x.get("flag")),
        "left_out": len(c.get("left_out") or []),
        "scope": (c.get("scope") or {}).get("level", "-"),
        "widened": "yes" if c.get("widened") else "-",
        "searched": "yes" if str(c.get("research") or "").startswith("searched automatically") else "-",
        "review": rv.get("verdict", "-"),
        "held": "HELD" if c.get("held") else ("anyway" if c.get("shipped_anyway") else "-"),
        "blank_notes": sum(1 for o in c.get("case") or [] if o.get("about_flag") and not o.get("about")),
        "tokens": f"{u.get('input_tokens', 0)}/{u.get('output_tokens', 0)}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="origin/staging")
    ap.add_argument("--since", required=True, help="ISO time, e.g. 2026-11-11T00:00")
    a = ap.parse_args()
    log = git("log", "--reverse", f"--since={a.since}", "--format=%H %cI %s", a.branch, "--", DRAFT).splitlines()
    rounds = [ln.split(" ", 2) for ln in log if "page(s) from Pulse" in ln]
    if not rounds:
        print(f"no build rounds on {a.branch} since {a.since}")
        return
    cols = ["milestones", "editor", "flagged", "left_out", "scope", "widened", "searched", "review", "held", "blank_notes", "tokens"]
    totals, seen = {}, {}
    for n, (sha, when, subj) in enumerate(rounds, 1):
        d = json.loads(git("show", f"{sha}:{DRAFT}"))
        print(f"\nround {n}  {when}  {sha[:8]}  {subj}")
        print("  story              " + "  ".join(f"{k:>10}" for k in cols))
        for s in d.get("stories", []):
            c = s.get("composed") or {}
            if c.get("v") != 2 or seen.get(s["story_id"]) == json.dumps(c, sort_keys=True):
                continue                                 # a page this commit did not rebuild is not counted again
            seen[s["story_id"]] = json.dumps(c, sort_keys=True)
            r = row(c)
            t = totals.setdefault(s["story_id"], [])
            t.append(r)
            print(f"  {s['story_id']:<18} " + "  ".join(f"{str(r[k]):>10}" for k in cols))
    print("\nper story over all rounds: milestones, searches, held")
    for k, rs in totals.items():
        print(f"  {k:<18} milestones {[r['milestones'] for r in rs]}  searched {sum(r['searched'] == 'yes' for r in rs)}/{len(rs)}"
              f"  held {sum(r['held'] == 'HELD' for r in rs)}/{len(rs)}")


if __name__ == "__main__":
    main()
