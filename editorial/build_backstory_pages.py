#!/usr/bin/env python3
"""
T-0046 — Generate a static, shareable permalink page per Backstory row.

Mirrors ntk-pulse/build_digest.py's per-story permalink pages
(digest/YYYY-MM-DD/<slug>/index.html): real OG/Twitter tags, one static
file per row, no client-side fetch needed for a reader who lands here
from a shared link or a search result.

Reads  digest/data/backstory.json   the 21-row library + todays_pairings
       (todays_pairings entries carry story_permalink once
       ntk-pulse/build_digest.py has run and enriched them — run this
       script AFTER that one, per pulse-publish.yml)
Writes backstory/<row-id>/index.html   one static page per row

Deliberately does NOT render:
  - the long-form narrative essay (narrative[] is empty for every row
    today; out of scope here regardless — see docs/tickets/T-0046)
  - a quote per object (objects only carry {title, author, year, source}
    today; renders the plain citation. Picks up a real `quote` field
    automatically once T-0045 lands — no change needed here for that.)
  - accumulated past episodes (instances[] is empty for every row in
    prod; "In the digest" below shows only today's real pairings)

Why /backstory/<row-id>/ needs no netlify.toml rule: Netlify serves any
folder with an index.html by convention (same reason /digest/YYYY-MM-DD/
needs none), and netlify.toml's existing `/backstory` redirect is an
exact match, not a wildcard — it never intercepts /backstory/<row-id>.
The file just needs to land at backstory/<row-id>/index.html, a sibling
of digest/, not nested under it.

Stdlib only.
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKSTORY_JSON = ROOT / "digest" / "data" / "backstory.json"
OUT_DIR = ROOT / "backstory"
BASE_URL = "https://ntknews.org"

INK = "#261F23"
CREAM = "#EAD9C5"
BLUE_DEEP = "#045E96"
TERRA = "#DC6550"
AMBER_DEEP = "#7A5308"


def log(msg):
    print(f"[backstory-pages] {msg}", flush=True)


def html_esc(s):
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def elapsed(start_iso, today):
    """(years, months) between an ISO date and today — matches the
    arithmetic already live on ntknews.org/backstory (verified against
    it directly: media's 1987-08-04 start_date produces the same
    "39 yrs, 1 mo" the live modal shows)."""
    y_s, m_s, d_s = (int(x) for x in start_iso.split("-"))
    y = today.year - y_s
    m = today.month - m_s
    if today.day < d_s:
        m -= 1
    if m < 0:
        y -= 1
        m += 12
    return y, m


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_esc} — Backstory — NTK News</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="NTK News">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{milestone_esc}">
<meta property="og:url" content="{canonical_url}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{title_esc}">
<meta name="twitter:description" content="{milestone_esc}">
<link href="https://fonts.googleapis.com/css2?family=Overpass:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500;1,6..72,600&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Newsreader',Georgia,serif; background:{cream}; color:{ink};
    max-width:640px; margin:0 auto; }}
  a {{ color:{blue_deep}; }}
  header {{ background:{ink}; padding:13px 20px; }}
  header a {{ font-family:'Overpass',sans-serif; font-size:14px; font-weight:700;
    letter-spacing:.05em; color:{cream}; text-decoration:none; }}
  .hd {{ padding:28px 20px 22px; border-bottom:1px solid {ink}; }}
  .hd h1 {{ font-family:'Newsreader',serif; font-weight:600; font-size:clamp(26px,7vw,34px);
    line-height:1.08; letter-spacing:-.01em; margin:0 0 14px; }}
  .hd .milestone {{ font-family:'Newsreader',serif; font-style:italic; font-size:20px;
    line-height:1.35; color:rgba(38,31,35,.85); }}
  section {{ padding:22px 20px; border-bottom:1px solid rgba(38,31,35,.22); }}
  .kicker {{ font-family:'Overpass',sans-serif; font-size:10px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase; color:{terra}; margin-bottom:10px; }}
  .elapsed {{ text-align:center; padding:16px 0 6px; }}
  .elapsed .num {{ font-family:'Overpass',sans-serif; font-size:42px; font-weight:700; }}
  .elapsed .unit {{ font-size:18px; font-weight:600; }}
  .elapsed .since {{ font-family:'Overpass',sans-serif; font-size:10px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase; color:rgba(38,31,35,.6); margin-top:8px; }}
  .unverified {{ display:inline-block; border:1px solid {terra}; color:{terra};
    font-family:'Overpass',sans-serif; font-size:10px; font-weight:700; letter-spacing:.08em;
    text-transform:uppercase; padding:3px 6px; border-radius:3px; margin-top:12px; }}
  .obj {{ border-top:1px solid rgba(38,31,35,.2); padding:13px 0; }}
  .obj:first-child {{ border-top:none; }}
  .obj .t {{ font-family:'Newsreader',serif; font-style:italic; font-size:15px; margin-bottom:4px; }}
  .obj .by {{ font-family:'Overpass',sans-serif; font-size:13px; color:rgba(38,31,35,.65); }}
  .ep {{ display:block; border-top:1px solid rgba(38,31,35,.18); padding:13px 0; text-decoration:none; color:{ink}; }}
  .ep:first-child {{ border-top:none; }}
  .ep .d {{ font-family:'Overpass',sans-serif; font-size:13px; color:rgba(38,31,35,.6); }}
  .ep .h {{ font-family:'Newsreader',serif; font-size:16px; margin-top:5px; }}
  .back {{ display:block; text-align:center; padding:26px 20px 40px; font-family:'Overpass',sans-serif;
    font-size:13px; font-weight:600; text-decoration:none; }}
  .end {{ font-family:'Newsreader',serif; font-style:italic; font-size:16px; text-align:center;
    color:rgba(38,31,35,.45); padding:26px 0 0; }}
</style>
</head>
<body>
<header><a href="/backstory">NTK</a></header>
<div class="hd">
  <h1>{title_esc}</h1>
  <div class="milestone">{milestone_esc}</div>
</div>
{body}
<a class="back" href="/backstory">← All of Backstory</a>
</body>
</html>
"""


def render_held(row):
    parts = []

    ind = row.get("indicator")
    if ind:
        verified_badge = "" if ind.get("verified") else '<div class="unverified">Unverified</div>'
        parts.append(f"""<section>
  <div class="kicker">{html_esc(ind['label'])} · {html_esc(ind['direction']).title()}</div>
  <div style="font-family:'Overpass',sans-serif;font-size:15px">
    {html_esc(ind['then_value'])} ({html_esc(ind['then_year'])}) &rarr; <b>{html_esc(ind['now_value'])}</b> (now)
  </div>
  <div style="font-family:'Overpass',sans-serif;font-size:11px;color:rgba(38,31,35,.6);margin-top:8px">{html_esc(ind['source'])}</div>
  {verified_badge}
</section>""")

    if row.get("start_line"):
        # First-letter capitalize only — str.capitalize() also lowercases
        # every other letter in the string, which mangles a proper noun
        # like "Washington" the moment it's not the first word.
        line = row["start_line"]
        line = line[:1].upper() + line[1:]
        parts.append(f"""<section>
  <div class="kicker">Begins</div>
  <div style="font-family:'Newsreader',serif;font-size:15px;line-height:1.5">{html_esc(line)}.</div>
</section>""")

    objs = row.get("objects") or []
    if objs:
        rows = []
        for o in objs:
            # Picks up a real `quote` field automatically once T-0045
            # ships a generation step — falls back to a plain citation
            # today since that field doesn't exist in the schema yet.
            # Author is blank on some real objects (e.g. Abrams v U.S. has
            # no author field) — fall back to the row title rather than
            # render a dangling " · 1919" with nothing before it.
            by = o.get("author") or row["title"]
            if o.get("quote"):
                rows.append(f'<div class="obj"><div class="t">{html_esc(o["quote"])}</div>'
                            f'<div class="by">{html_esc(by)} · {html_esc(o["year"])}</div></div>')
            else:
                rows.append(f'<div class="obj"><div class="t">{html_esc(o["title"])}</div>'
                            f'<div class="by">{html_esc(by)} · {html_esc(o["year"])}</div></div>')
        parts.append(f'<section><div class="kicker">The case</div>{"".join(rows)}</section>')

    return "\n".join(parts)


def render_fire(row, today):
    y, m = elapsed(row["start_date"], today)
    return f"""<section class="elapsed">
  <div><span class="num">{y}</span> <span class="unit">yrs</span> <span class="num">{m}</span> <span class="unit">mo</span></div>
  <div class="since">since {row['start_date']}</div>
</section>"""


def render_episodes(row_id, pairings):
    today_pairs = [p for p in pairings if p.get("row") == row_id]
    if not today_pairs:
        return ""
    items = []
    for p in today_pairs:
        link = p.get("story_permalink")
        href = link if link else "/today"
        items.append(f'<a class="ep" href="{html_esc(href)}"><div class="d">Today</div>'
                      f'<div class="h">&ldquo;{html_esc(p.get("line") or p.get("headline",""))}&rdquo;</div></a>')
    return f'<section><div class="kicker">In the digest</div>{"".join(items)}</section>'


def build_page(row, pairings, today):
    body_sections = (render_fire(row, today) if row["stratum"] == "fire" else render_held(row))
    episodes = render_episodes(row["id"], pairings)
    body = body_sections + episodes + '<div class="end">— 30 —</div>'
    return PAGE_TEMPLATE.format(
        title_esc=html_esc(row["title"]),
        milestone_esc=html_esc(row["milestone"]),
        canonical_url=f"{BASE_URL}/backstory/{row['id']}/",
        cream=CREAM, ink=INK, blue_deep=BLUE_DEEP, terra=TERRA, amber_deep=AMBER_DEEP,
        body=body,
    )


def main():
    if not BACKSTORY_JSON.exists():
        sys.exit(f"{BACKSTORY_JSON} not found — run editorial/build_backstory.py first")
    data = json.loads(BACKSTORY_JSON.read_text())
    rows = data.get("rows", [])
    pairings = data.get("todays_pairings", [])
    today = date.today()

    OUT_DIR.mkdir(exist_ok=True)
    written = 0
    for row in rows:
        page = build_page(row, pairings, today)
        row_dir = OUT_DIR / row["id"]
        row_dir.mkdir(parents=True, exist_ok=True)
        (row_dir / "index.html").write_text(page)
        written += 1

    log(f"{written} permalink pages written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
