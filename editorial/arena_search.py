#!/usr/bin/env python3
"""Search the editor's Are.na index (editorial/arena.db) for Backstory leads.

    python3 editorial/arena_search.py "tariff smoot hawley"
    python3 editorial/arena_search.py --channel "presidents" -n 50
    python3 editorial/arena_search.py --channels          # list channels

Words are ORed and ranked by bm25, so a loose query still finds something.
Each hit is a lead, not an object: the Are.na block is usually a news story or
essay pointing at the primary document. The `kind` column guesses whether the
link itself is primary (archives, .gov, court and treaty sites) or coverage.
Nothing found here goes in the matrix until it has been through
NTK_Backstory_Candidates.xlsx and the editor's approval (CLAUDE.md rule 8).
"""
import argparse, json, re, sqlite3, sys
from pathlib import Path
from urllib.parse import urlparse

DB = Path(__file__).with_name("arena.db")

PRIMARY = re.compile(
    r"(\.gov$|\.mil$|archives\.|founders\.archives|avalon\.law\.yale|loc\.gov|congress\.gov|"
    r"supremecourt|oyez\.org|presidency\.ucsb|millercenter|un\.org|treaties|hathitrust|"
    r"gutenberg|jstor|\.edu$|europa\.eu|nato\.int|state\.gov|history\.state)"
)
COVERAGE = re.compile(r"(wikipedia|amazon\.|goodreads|youtube|twitter|x\.com|instagram|medium\.com)")


def kind(url):
    if not url:
        return "note"
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if COVERAGE.search(host):
        return "avoid"
    return "primary?" if PRIMARY.search(host) else "coverage"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="*")
    ap.add_argument("--channel", help="limit to channels whose title contains this")
    ap.add_argument("--channels", action="store_true", help="list channels and exit")
    ap.add_argument("-n", type=int, default=25)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not DB.exists():
        sys.exit(f"{DB} missing: run python3 editorial/arena_pull.py first")
    db = sqlite3.connect(DB)

    if a.channels:
        for slug, title, vis, n in db.execute(
            "SELECT c.slug, c.title, c.visibility, count(k.block_id) FROM channels c LEFT JOIN connections k "
            "ON k.channel_id = c.id GROUP BY c.id ORDER BY 4 DESC"):
            print(f"{n:5}  {title}  ({slug}, {vis})")
        return

    where, params = [], []
    if a.query:
        terms = [re.sub(r"[^\w]", "", t) for t in " ".join(a.query).split()]
        match = " OR ".join(f'"{t}"' for t in terms if t)
        where.append("b.id IN (SELECT rowid FROM blocks_fts WHERE blocks_fts MATCH ?)")
        params.append(match)
        order = "(SELECT bm25(blocks_fts) FROM blocks_fts WHERE blocks_fts MATCH ? AND rowid = b.id)"
        params_order = [match]
    else:
        order, params_order = "b.created_at DESC", []
    if a.channel:
        where.append("b.id IN (SELECT k.block_id FROM connections k JOIN channels c ON c.id = k.channel_id "
                     "WHERE c.title LIKE ?)")
        params.append(f"%{a.channel}%")
    sql = (
        "SELECT b.id, b.type, b.title, b.source_url, b.created_at, b.arena_url, "
        "(SELECT group_concat(c.title, ' | ') FROM connections k JOIN channels c ON c.id = k.channel_id "
        " WHERE k.block_id = b.id) FROM blocks b"
        + (" WHERE " + " AND ".join(where) if where else "")
        + f" ORDER BY {order} LIMIT ?"
    )
    rows = db.execute(sql, params + params_order + [a.n]).fetchall()

    out = [dict(id=r[0], type=r[1], title=(r[2] or "").strip(), url=r[3], saved=(r[4] or "")[:10],
                arena=r[5], channels=r[6], kind=kind(r[3])) for r in rows]
    if a.json:
        print(json.dumps(out, indent=1))
        return
    for o in out:
        print(f"[{o['kind']:8}] {o['title'][:90]}")
        print(f"            {o['url'] or o['arena']}   ({o['channels'] or 'no channel'}, saved {o['saved']})")
    print(f"\n{len(out)} hits")


if __name__ == "__main__":
    main()
