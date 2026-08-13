#!/usr/bin/env python3
"""NTK Digest — full automated build.

Runs unattended, triggered by a push from Pulse's Publish button. Takes
whatever's currently in the lineup and turns it into the live site: no
paste, no download, no terminal.

What it does, in order:
  1. Reads the published story data (committed by Pulse's Publish button).
  2. Picks today's "fun fact" — grounded in Wikipedia's real On This Day
     feed, never invented (see pick_fun_fact()).
  3. Regenerates digest/v2/index.html's `const stories` and `const funFact`
     blocks in place — the live homepage, not a copy. Everything else in
     that file (the swipe-app shell, styling, JS) is left untouched; this
     only touches the two blocks that used to be hand-pasted.
  4. Decodes each story's base64 image into a real file.
  5. Writes a standalone permalink page per story, real OG/Twitter tags.
  6. Freezes today's edition at a permanent dated path.
  7. Rebuilds the archive index from what's actually on disk.
  8. Writes a last-published timestamp Pulse can read and show you.

Writes DIRECTLY to digest/v2/ — no test-folder detour. That was the right
call while this was unverified; it's a deliberate, later decision to skip
it now that the mechanics are proven and there's no live audience yet.

Stdlib only.
"""
import base64
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TEAL = "#01B2A7"
INK = "#261F23"
CREAM = "#EAD9C5"
GOLD = "#F2AE2E"
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"


def log(msg):
    print(f"[build] {msg}", flush=True)


# ─── fun fact: grounded in a real source, never invented ───
def fetch_on_this_day():
    """Wikipedia's own editorial pick of the day's most notable historical
    events — same en.wikipedia.org/api/rest_v1 domain Summon Context
    already calls, no new infrastructure, no API key."""
    now = datetime.now(timezone.utc)
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/selected/{now.month:02d}/{now.day:02d}"
    req = urllib.request.Request(url, headers={"User-Agent": "NTK-News-Build/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    events = data.get("selected", [])
    return [{"year": e.get("year"), "text": e.get("text", "")} for e in events if e.get("text")]


def call_claude(api_key, prompt, max_tokens=300):
    body = {"model": MODEL, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read())
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def pick_fun_fact(api_key):
    """One real event, selected and written up — never generated from
    nothing. If Wikipedia or the API call fails, falls back to the
    existing funFact already in the file rather than writing something
    unsourced."""
    try:
        events = fetch_on_this_day()
        if not events:
            return None
        listing = "\n".join(f"- {e['year']}: {e['text']}" for e in events[:20])
        prompt = (
            "Pick ONE event from this real, verified list of things that happened on this "
            "date in history. Choose whichever is most surprising, delightful, or humanizing "
            "— not necessarily the most famous. Write it up in 35-50 words, plain and warm, "
            "in the spirit of a closing 'moment of zen' — something a reader closes the day "
            "on, not more news to process.\n\n"
            "Judge only what's on this list. Do not add detail beyond what's stated. If "
            "nothing here is genuinely delightful, pick the most human one anyway.\n\n"
            f"{listing}\n\n"
            "Return ONLY the 35-50 word write-up, no preamble, no quotation marks around it."
        )
        text = call_claude(api_key, prompt, max_tokens=200).strip()
        return text if text else None
    except Exception as e:
        log(f"  fun fact generation failed, keeping existing: {e}")
        return None


# ─── homepage regeneration: touch only the two blocks that were hand-pasted ───
def jsEsc(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def build_stories_block(stories):
    lines = ["const stories = ["]
    for s in stories:
        img_fields = ""
        if s.get("featuredImage"):
            img_fields = (f',\n    featuredImage: "{jsEsc(s["featuredImage"])}"'
                          f',\n    overlayColor: "{jsEsc(s.get("overlayColor", "#0798F2"))}"'
                          f',\n    overlayOpacity: {s.get("overlayOpacity", 45)}')
        lines.append(f'  {{\n'
                      f'    category: "{jsEsc(s.get("category",""))}",\n'
                      f'    headline: "{jsEsc(s.get("headline",""))}",\n'
                      f'    lede: "{jsEsc(s.get("lede",""))}",\n'
                      f'    truth: "{jsEsc(s.get("truth",""))}",\n'
                      f'    prob: "{jsEsc(s.get("prob",""))}",\n'
                      f'    poss: "{jsEsc(s.get("poss",""))}",\n'
                      f'    lies: "{jsEsc(s.get("lies",""))}"{img_fields}\n'
                      f'  }},')
    lines.append("]; // ← END OF DAILY CONTENT. Do not edit below this line.")
    return "\n".join(lines)


def regenerate_homepage(html, stories, fun_fact):
    """Regex-replace the two hand-pasted blocks in place. Everything else
    in the file — the swipe-app shell, all its JS and CSS — is left
    completely untouched. This is deliberately NOT a from-scratch
    regeneration of the page; duplicating that logic here would be a
    second place for it to drift out of sync with the real, working app."""
    stories_re = re.compile(
        r"const stories = \[.*?\];\s*// ← END OF DAILY CONTENT\. Do not edit below this line\.",
        re.DOTALL)
    new_html, n = stories_re.subn(build_stories_block(stories), html)
    if n != 1:
        raise RuntimeError(f"expected exactly 1 stories block match, found {n} — "
                            "homepage template may have changed; refusing to guess")

    if fun_fact:
        fact_re = re.compile(r'const funFact = "[^"]*";')
        new_html, n2 = fact_re.subn(f'const funFact = "{jsEsc(fun_fact)}";', new_html)
        if n2 != 1:
            log(f"  WARNING: expected 1 funFact match, found {n2} — leaving funFact untouched")
            new_html = html if n != 1 else new_html  # safety, though n==1 already checked above

    return new_html


# ─── per-story permalinks (unchanged logic from the earlier build) ───
def slugify(text, max_len=60):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    text = re.sub(r"[\s-]+", "-", text)
    return text[:max_len].strip("-") or "story"


def unique_slugs(stories):
    seen, out = {}, []
    for s in stories:
        base = slugify(s.get("headline", "story"))
        slug, n = base, 2
        while slug in seen:
            slug = f"{base}-{n}"; n += 1
        seen[slug] = True
        out.append(slug)
    return out


def decode_image(data_uri, out_path):
    if not data_uri or not data_uri.startswith("data:image"):
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(data_uri.split(",", 1)[1]))
    return True


def html_esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def strip_html_for_description(html, max_len=200):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:max_len] + "…") if len(text) > max_len else text


STORY_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{headline} — NTK News</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="NTK News">
<meta property="og:title" content="{headline_esc}">
<meta property="og:description" content="{description_esc}">
<meta property="og:url" content="{canonical_url}">
{og_image_tags}
<meta name="twitter:card" content="{twitter_card_type}">
<meta name="twitter:title" content="{headline_esc}">
<meta name="twitter:description" content="{description_esc}">
{twitter_image_tag}
<style>
  :root {{ --ink:{ink}; --cream:{cream}; --teal:{teal}; --gold:{gold}; }}
  body {{ background:var(--cream); color:var(--ink); font-family:'Source Serif 4',Georgia,serif;
    max-width:640px; margin:0 auto; padding:24px 20px 60px; line-height:1.6; }}
  h1,h2,.cat,.back {{ font-family:'Space Grotesk',sans-serif; }}
  .cat {{ color:var(--teal); font-size:12px; text-transform:uppercase; letter-spacing:1px; font-weight:600; }}
  h1 {{ font-size:28px; line-height:1.25; margin:8px 0 6px; }}
  .lede {{ font-size:17px; color:#4a3f43; margin-bottom:20px; }}
  .hero {{ width:100%; border-radius:4px; margin-bottom:20px; object-fit:cover; max-height:340px; }}
  h2.sec {{ font-size:13px; text-transform:uppercase; letter-spacing:1.5px; color:var(--ink);
    border-bottom:2px solid var(--ink); padding-bottom:4px; margin:28px 0 10px; }}
  .body p {{ margin:0 0 12px; }}
  .back {{ display:inline-block; margin-top:36px; font-size:13px; color:var(--teal); text-decoration:none; }}
  a {{ color:var(--teal); }}
</style>
</head>
<body>
  <div class="cat">{category}</div>
  <h1>{headline_esc}</h1>
  <div class="lede">{lede_esc}</div>
  {hero_img}
  <h2 class="sec">Truths</h2><div class="body">{truth}</div>
  <h2 class="sec">Probabilities</h2><div class="body">{prob}</div>
  <h2 class="sec">Possibilities</h2><div class="body">{poss}</div>
  <h2 class="sec">Lies</h2><div class="body">{lies}</div>
  <a class="back" href="../">← Back to today's digest</a>
</body>
</html>
"""


def build_story_page(story, image_rel_url, image_abs_url, canonical_url):
    headline = story.get("headline", "")
    description = story.get("lede") or strip_html_for_description(story.get("truth", ""))
    has_image = bool(image_abs_url)
    og_image_tags = (
        f'<meta property="og:image" content="{image_abs_url}">\n'
        f'<meta property="og:image:width" content="1200">\n'
        f'<meta property="og:image:height" content="630">' if has_image else "")
    twitter_image_tag = (f'<meta name="twitter:image" content="{image_abs_url}">' if has_image else "")
    return STORY_PAGE_TEMPLATE.format(
        headline=headline.replace("<", "").replace(">", ""),
        headline_esc=html_esc(headline), description_esc=html_esc(description),
        canonical_url=canonical_url, og_image_tags=og_image_tags,
        twitter_card_type="summary_large_image" if has_image else "summary",
        twitter_image_tag=twitter_image_tag, ink=INK, cream=CREAM, teal=TEAL, gold=GOLD,
        category=html_esc(story.get("category", "")), lede_esc=html_esc(description),
        hero_img=(f'<img class="hero" src="{image_rel_url}" alt="">' if has_image else ""),
        truth=story.get("truth", ""), prob=story.get("prob", ""),
        poss=story.get("poss", ""), lies=story.get("lies", ""))


ARCHIVE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archive — NTK News</title>
<style>
  body {{ background:{cream}; color:{ink}; font-family:'Source Serif 4',Georgia,serif;
    max-width:640px; margin:0 auto; padding:24px 20px 60px; }}
  h1 {{ font-family:'Space Grotesk',sans-serif; }}
  .ed {{ margin-bottom:28px; }}
  .ed-date {{ font-family:'Space Grotesk',sans-serif; font-size:13px; color:{teal};
    text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }}
  .ed a.day {{ font-weight:600; }}
  ul {{ margin:6px 0 0; padding-left:18px; }}
  li {{ margin-bottom:3px; font-size:15px; }}
</style>
</head>
<body>
<h1>Archive</h1>
{editions}
</body>
</html>
"""


def rebuild_archive(digest_dir, base_url):
    date_dirs = sorted([d for d in digest_dir.iterdir()
                        if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", d.name)], reverse=True)
    blocks = []
    for d in date_dirs:
        meta_path = d / "_headlines.json"
        if not meta_path.exists():
            continue
        headlines = json.loads(meta_path.read_text())
        items = "\n".join(
            f'    <li><a href="{base_url}/digest/v2/{d.name}/{h["slug"]}/">{html_esc(h["headline"])}</a></li>'
            for h in headlines)
        blocks.append(f'<div class="ed"><div class="ed-date">{d.name}</div>'
                       f'<a class="day" href="{base_url}/digest/v2/{d.name}/">Full edition</a>'
                       f'<ul>\n{items}\n  </ul></div>')
    archive_dir = digest_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.html").write_text(
        ARCHIVE_TEMPLATE.format(cream=CREAM, ink=INK, teal=TEAL, editions="\n".join(blocks)))
    log(f"archive rebuilt: {len(date_dirs)} editions listed")


def main():
    repo_root = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    story_json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DEFAULT
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base_url = "https://maxzimbert.github.io/ntknews"
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    digest_dir = repo_root / "digest" / "v2"
    live_index_path = digest_dir / "index.html"

    stories = json.loads(story_json_path.read_text())
    log(f"{len(stories)} stories loaded from {story_json_path}")

    # 1. Fun fact — real source, graceful fallback to whatever's already there.
    fun_fact = pick_fun_fact(api_key) if api_key else None
    if fun_fact:
        log(f"fun fact: {fun_fact[:70]}...")
    else:
        log("no fresh fun fact generated — leaving today's existing one in place")

    # 2. Regenerate the LIVE homepage in place. This is the piece that
    # makes the whole chain zero-click: no more paste, ever.
    current_html = live_index_path.read_text()
    new_html = regenerate_homepage(current_html, stories, fun_fact)
    live_index_path.write_text(new_html)
    log(f"live homepage regenerated: {live_index_path}")

    # 3. Freeze today's now-correct homepage at a permanent dated path.
    dated_dir = digest_dir / date_str
    dated_dir.mkdir(parents=True, exist_ok=True)
    (dated_dir / "index.html").write_text(new_html)

    # 4. Per-story permalinks + images.
    slugs = unique_slugs(stories)
    headlines_meta = []
    for story, slug in zip(stories, slugs):
        story_dir = dated_dir / slug
        story_dir.mkdir(parents=True, exist_ok=True)
        canonical_url = f"{base_url}/digest/v2/{date_str}/{slug}/"

        image_rel_url = image_abs_url = None
        if story.get("featuredImage"):
            img_name = f"{slug}.jpg"
            if decode_image(story["featuredImage"], digest_dir / "images" / img_name):
                image_rel_url = f"../../images/{img_name}"
                image_abs_url = f"{base_url}/digest/v2/images/{img_name}"

        page = build_story_page(story, image_rel_url, image_abs_url, canonical_url)
        (story_dir / "index.html").write_text(page)
        headlines_meta.append({"slug": slug, "headline": story.get("headline", "")})
        log(f"  story page: {slug}/  (image: {'yes' if image_abs_url else 'no'})")

    (dated_dir / "_headlines.json").write_text(json.dumps(headlines_meta, indent=1))

    # 5. Archive, rebuilt from what's actually on disk.
    rebuild_archive(digest_dir, base_url)

    # 6. Last-published marker — what Pulse's button reads to show you
    # "last published: N ago" without you having to go check GitHub.
    (repo_root / "ntk-pulse" / "data" / "last-published.json").write_text(
        json.dumps({"at": datetime.now(timezone.utc).isoformat(), "stories": len(stories)}, indent=1))

    log("")
    log(f"Done. Live at {base_url}/digest/v2/")


DATA_DEFAULT = Path("ntk-pulse/data/lineup-publish.json")

if __name__ == "__main__":
    main()
