#!/usr/bin/env python3
"""T-0083: the rules in editorial/backstory_build.py, with stand-ins for the model and the web."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backstory_build as B  # noqa: E402

fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  " + str(detail)))
    if not ok:
        fails.append(name)


def beg(i, d, check_="verified", status="auto"):
    return {"id": i, "event_date": d, "year": d[:4], "line": f"Line {i} about an event.", "how": "",
            "object": {"title": f"T{i}", "url": f"https://x.gov/{i}", "quote": "q", "check": check_}, "status": status}


# the publishing rule
check("verified publishes", B.publishable(beg("a", "2000")))
check("matrix publishes", B.publishable(beg("a", "2000", "matrix")))
check("a news-site copy waits", not B.publishable(beg("a", "2000", "news-copy")))
check("an untested PDF waits", not B.publishable(beg("a", "2000", "loads")))
check("an approval publishes a waiting one", B.publishable(beg("a", "2000", "loads", "approved")))
check("a rejection holds back a verified one", not B.publishable(beg("a", "2000", "verified", "rejected")))

# the Object check
B._fetch_text = lambda url: (200, "the quoted sentence is here on the page for anyone")
o = B.check_object({"url": "https://www.gao.gov/r", "quote": "the quoted sentence is here on the page"}, {"https://www.gao.gov/r"}, {})
check("a page holding the quote is verified", o["check"] == "verified", o)
o = B.check_object({"url": "https://www.pbs.org/t", "quote": "the quoted sentence is here on the page"}, {"https://www.pbs.org/t"}, {})
check("the same quote on a news site is a news copy, which waits", o["check"] == "news-copy", o)
o = B.check_object({"url": "https://www.gao.gov/r", "quote": "words that the page does not hold at all"}, {"https://www.gao.gov/r"}, {})
check("a quote not on the page fails", o["check"] == "failed", o)
o = B.check_object({"url": "https://www.gao.gov/r", "quote": "the quoted sentence is here"}, set(), {})
check("a link the search did not return fails", o["check"] == "failed", o)

# the start is never the last 45 days
cat = {"title": "C", "contest": "", "beginnings": [beg("a", "2001-01-01"), beg("b", "2015-01-01"), beg("c", "2026-10-01")]}
B.ask = lambda p, mt=4000: {"start": "c", "start_line": "When c.", "runner_ups": [{"id": "b", "why_weaker": "w"}],
                             "before": [{"id": "a", "why": "w"}], "since": []}
ch = B.choose({"headline": "h", "truths": "t", "line": "l"}, cat, "2026-10-12")
check("a start inside 45 days falls back to the runner-up and moves to since",
      ch["start"] == "b" and [x["id"] for x in ch["since"]] == ["c"] and [x["id"] for x in ch["before"]] == ["a"], ch)

# the editor's overrides
ch2 = B.apply_overrides(dict(ch), {"start": "a", "include": ["b", "c"]}, cat)
check("the editor's start and Beginnings win", ch2["start"] == "a" and [x["id"] for x in ch2["since"]] == ["b", "c"] and ch2["by_editor"], ch2)

# Beginnings asked for in Pulse
store = {"categories": [{"id": "p-x", "title": "X", "kind": "subject", "beginnings": []}]}
ov = {"newcats": [{"id": "p-ports", "title": "Port security"}],
      "additions": {"p-ports": [{"event_date": "2002-11-25", "line": "Congress passed the Maritime Transportation Security Act.",
                                 "object": {"url": "https://www.congress.gov/x", "quote": "q", "check": "verified"}}],
                    "p-x": [{"event_date": "2002", "line": "", "object": {"url": "https://x.gov"}}]}}
B.merge_from_pulse(store, ov, {"rows": []}, "2026-10-12")
ports = [c for c in store["categories"] if c["id"] == "p-ports"]
check("a category made in Pulse is created", bool(ports), store)
check("a Beginning asked for in Pulse arrives unchecked, so the publish checks it (its own 'verified' is ignored)",
      ports and ports[0]["beginnings"][0]["object"]["check"] == "unchecked", ports)
check("an asked-for Beginning without a line is refused", not [c for c in store["categories"] if c["id"] == "p-x"][0]["beginnings"])

# the reader's row
row = B.row_for(dict(cat, id="c", trend={"label": "L", "unit": "%", "points": [{"date": "2000", "value": "10"}, {"date": "2020", "value": "30"}], "check": "verified"}),
                [ch], ["Today's line."])
check("the row marks the start, ends at We are here, and carries the trend line",
      [b.get("mark") for b in row["beginnings"]] == [None, "start", None] and row["here"] == ["Today's line."]
      and row["indicator"]["then_value"] == "10%" and row["indicator"]["now_value"] == "30%" and row["stratum"] == "held", row)
check("each Beginning shown has its Object in the case", [o["object_id"] for o in row["objects"]] == [b["object_id"] for b in row["beginnings"]] and all(o["about"] and o["source_url"] for o in row["objects"]), row["objects"])

# a page shows at least three Beginnings: too few chosen today are topped up from the category, never with a dropped one
thin = dict(cat, id="t", beginnings=[beg("p", "1990-01-01"), beg("q", "1995-01-01"), beg("r", "2000-01-01"), beg("s", "2010-01-01")])
row2 = B.row_for(thin, [{"start": "s", "before": [], "since": [], "dropped": ["r"]}], ["l"])
check("a page with one chosen Beginning is topped up to three, skipping the dropped one", [b["object_id"] for b in row2["beginnings"]] == ["p", "q", "s"], row2["beginnings"])

# the upgrade: a waiting news-site copy is replaced by the issuer's own, which then publishes
up = {"title": "U", "beginnings": [dict(beg("n", "2026-02-28", "news-copy", "pending"), object={"title": "PBS", "host": "pbs.org", "url": "https://www.pbs.org/x", "quote": "q", "check": "news-copy"})]}
B.search = lambda p, mt=14000, uses=12: ({"n": {"title": "Remarks", "url": "https://www.whitehouse.gov/r", "quote": "the quoted sentence is here on the page"}}, {"https://www.whitehouse.gov/r"})
B._fetch_text = lambda url: (200, "the quoted sentence is here on the page for anyone")
B.upgrade(up, {}, "2026-10-12")
check("a news-site copy is upgraded to the issuer's own copy and publishes",
      up["beginnings"][0]["object"]["host"] == "whitehouse.gov" and B.publishable(up["beginnings"][0]) and up["beginnings"][0]["replaced_object"]["host"] == "pbs.org", up)
B.upgrade(up, {}, "2026-10-12")
check("an upgrade is tried once", up["beginnings"][0].get("upgrade_tried") == "2026-10-12")

print(f"\n{len(fails)} failed")
sys.exit(1 if fails else 0)
