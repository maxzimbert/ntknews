#!/usr/bin/env python3
"""Export the editor's Are.na library (editorial/arena.db) for Backstory to draw on.

    python3 editorial/export_library.py                # writes ntk-pulse/data/arena-library.json
    python3 editorial/export_library.py --fetch-dates  # first fetches a date for items whose URL has none

Everything in Are.na is something the editor saved as worth reading, so it ranks after primary
sources and ahead of anything a web search finds. It is not merged into the Object Matrix, whose rule
is primary sources only (docs/decisions.md). An item is kept only if a reader can open it and it can
be placed in time:
  - dropped: no link, a host refused everywhere (Wikipedia, retail), a host that is gone or only
    redirects (BuzzFeed News, apple.news, Twitter), and anything with no publication date;
  - flagged: `paywall` for outlets that meter or wall their pages, so a free copy can be preferred.
The date is the publication date from the URL (/2020/06/17/) or, with --fetch-dates, from the page's
own metadata, cached in editorial/arena-dates.json. The Are.na save date is never used: it says when
the editor read it, not when it was written.
"""
import argparse, json, re, sqlite3, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "editorial" / "arena.db"
DATES = ROOT / "editorial" / "arena-dates.json"
OUT = ROOT / "ntk-pulse" / "data" / "arena-library.json"

sys.path.insert(0, str(ROOT / "editorial"))
from categories import DENY_HOSTS, source_kind  # noqa: E402  (one list of refused and news hosts)

GONE = ("buzzfeednews.com", "apps.apple.com", "itunes.apple.com", "podcasts.apple.com", "open.spotify.com", "apple.news", "twitter.com", "x.com", "t.co", "youtube.com", "youtu.be",
        "instagram.com", "facebook.com", "tiktok.com", "bit.ly", "lnkd.in", "flip.it", "google.com")
PAYWALL = ("nytimes.com", "wsj.com", "bloomberg.com", "newyorker.com", "theatlantic.com", "washingtonpost.com",
           "ft.com", "economist.com", "latimes.com", "nymag.com", "wired.com", "businessinsider.com",
           "theinformation.com", "newrepublic.com", "bostonglobe.com", "vanityfair.com", "foreignaffairs.com",
           "harpers.org", "thetimes.co.uk", "telegraph.co.uk", "barrons.com", "seattletimes.com", "sfchronicle.com")
DROP_PARAMS = re.compile(r"^(utm_|smid|smtyp|referringSource|ref|fbclid|gclid|mc_|cmpid|s$|sh$|partner|rss|feed)")
URL_DATE = [re.compile(p) for p in (r"/((?:19|20)\d\d)/(\d\d)/(\d\d)(?:/|$)", r"/((?:19|20)\d\d)-(\d\d)-(\d\d)",
                                    r"[/_-]((?:19|20)\d\d)(\d\d)(\d\d)(?:[/_.-]|$)", r"/((?:19|20)\d\d)/(\d\d)/")]
META_DATE = re.compile(r'(?:article:published_time|datePublished|pubdate|publish-date|"dateCreated"|DC\.date\.issued)'
                       r'["\']?\s*(?:content=|:)\s*["\']((?:19|20)\d\d-\d\d-\d\d)', re.I)


def host_of(url):
    return urlsplit(url).netloc.lower().removeprefix("www.")


def on(host, names):
    return any(host == n or host.endswith("." + n) or (n.endswith(".") and n in host) for n in names)


def clean_url(url):
    s = urlsplit(url.strip())
    q = [(k, v) for k, v in parse_qsl(s.query, keep_blank_values=True) if not DROP_PARAMS.match(k)]
    return urlunsplit(("https", s.netloc, s.path, urlencode(q), ""))


def clean_title(title, provider):
    t = re.sub(r"\s+", " ", title or "").strip()
    # "Headline - The New York Times", "Headline | WIRED": the outlet goes in `source`, not the title
    t = re.sub(r"\s+[-|–—]\s+[^-|–—]{2,40}$", "", t) if re.search(r"\s[-|–—]\s", t) else t
    return t


def url_date(url):
    for p in URL_DATE:
        m = p.search(urlsplit(url).path)
        if m:
            y, mo = int(m.group(1)), int(m.group(2))
            d = int(m.group(3)) if m.lastindex >= 3 else 1
            if 1900 <= y <= datetime.now().year and 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}" if m.lastindex >= 3 else f"{y:04d}-{mo:02d}-01"
    return None


def fetch_date(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (NTK library date check)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            m = META_DATE.search(r.read(400000).decode("utf-8", "replace"))
            return m.group(1) if m else ""
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-dates", action="store_true")
    a = ap.parse_args()
    if not DB.exists():
        sys.exit(f"{DB} missing: run python3 editorial/arena_pull.py first")
    db = sqlite3.connect(DB)
    dates = json.loads(DATES.read_text()) if DATES.exists() else {}

    rows = db.execute("""
        SELECT b.id, b.title, b.source_url, b.provider, substr(b.created_at, 1, 10),
               (SELECT group_concat(c.title, '|') FROM connections k JOIN channels c ON c.id = k.channel_id
                WHERE k.block_id = b.id)
        FROM blocks b WHERE b.source_url LIKE 'http%' ORDER BY b.id""").fetchall()

    seen, out, dropped = set(), [], {"refused": 0, "gone": 0, "duplicate": 0, "undated": 0, "untitled": 0}
    todo = []
    for bid, title, url, provider, saved, chans in rows:
        u = clean_url(url)
        h = host_of(u)
        if on(h, DENY_HOSTS) or any(d in h for d in DENY_HOSTS if d.endswith(".")):
            dropped["refused"] += 1; continue
        if on(h, GONE):
            dropped["gone"] += 1; continue
        if u in seen:
            dropped["duplicate"] += 1; continue
        seen.add(u)
        t = clean_title(title, provider)
        if not t:
            dropped["untitled"] += 1; continue
        d = url_date(u) or dates.get(u)
        from_url = d is not None and d == url_date(u)
        if d is None and a.fetch_dates:
            todo.append(u)
        out.append({"id": f"arena-{bid}", "title": t, "source": h, "url": u, "date": d,
                    "channels": [c.strip() for c in (chans or "").split("|") if c.strip()],
                    "paywall": on(h, PAYWALL), "source_kind": source_kind(u), "_saved": saved, "_from_url": from_url})

    if todo:
        print(f"fetching dates for {len(todo)} pages", flush=True)
        for n, u in enumerate(todo, 1):
            dates[u] = fetch_date(u)
            if n % 50 == 0:
                DATES.write_text(json.dumps(dates, indent=0, sort_keys=True)); print(f"  {n}", flush=True)
            time.sleep(0.3)
        DATES.write_text(json.dumps(dates, indent=0, sort_keys=True))
        for o in out:
            o["date"] = o["date"] or dates.get(o["url"]) or None

    kept = []
    dropped["date after save"] = 0
    for o in out:
        saved, from_url = o.pop("_saved"), o.pop("_from_url")
        if not o["date"]:
            dropped["undated"] += 1; continue
        # nothing is published after the editor saved it. A magazine's issue date in its URL can run a few
        # weeks ahead of the day it went online, so that is allowed; a page's own metadata date is not.
        if o["date"] > saved and not (from_url and (datetime.fromisoformat(o["date"]) - datetime.fromisoformat(saved)).days <= 45):
            dropped["date after save"] += 1; continue
        o["year"] = o["date"][:4]
        kept.append(o)
    kept.sort(key=lambda o: o["date"])

    doc = {"_comment": "The editor's Are.na library, exported by editorial/export_library.py. Ranks after primary "
                       "sources and before web search. Not part of the Object Matrix.",
           "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "count": len(kept), "dropped": dropped, "objects": kept}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    pw = sum(o["paywall"] for o in kept)
    print(f"kept {len(kept)} ({pw} paywalled), dropped {dropped}; wrote {OUT.relative_to(ROOT)} "
          f"({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
