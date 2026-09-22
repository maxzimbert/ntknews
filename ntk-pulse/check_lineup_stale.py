#!/usr/bin/env python3
"""Cost gate for the Story Ledger stage (T-0030).

Prints `stale=true` or `stale=false` to stdout — nothing else — so the
workflow can capture it straight into $GITHUB_OUTPUT. Diagnostic reasoning
goes to stderr, visible in the Action log but not in the output file.

"Stale" means the ledger pass is worth its Sonnet spend: the lineup is
missing entirely, empty, or older than STALE_HOURS. Otherwise there's
already a fresh, populated lineup and a scheduled run has nothing to add.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

STALE_HOURS = 12
DATA = Path(__file__).parent / "data"


def main():
    path = DATA / "lineup.json"
    if not path.exists():
        print("stale=true")
        print("reason: no lineup.json yet", file=sys.stderr)
        return

    lineup = json.loads(path.read_text())

    if not lineup.get("stories"):
        print("stale=true")
        print("reason: lineup is empty", file=sys.stderr)
        return

    assembled_at = lineup.get("assembled_at")
    if not assembled_at:
        print("stale=true")
        print("reason: lineup has stories but no assembled_at timestamp", file=sys.stderr)
        return

    age = datetime.now(timezone.utc) - datetime.fromisoformat(assembled_at)
    if age >= timedelta(hours=STALE_HOURS):
        print("stale=true")
        print(f"reason: lineup is {age} old (>= {STALE_HOURS}h)", file=sys.stderr)
        return

    print("stale=false")
    print(f"reason: lineup has {len(lineup['stories'])} stories, "
          f"assembled {age} ago (< {STALE_HOURS}h) — skipping ledger", file=sys.stderr)


if __name__ == "__main__":
    main()
