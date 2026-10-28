#!/usr/bin/env python3
"""Turn digest stories + backstory.json into share-card data (SPEC.md section 4).

    python render/build_card_data.py --stories digest-stories.json \
        --backstory digest/data/backstory.json --out build/share

Writes build/share/<story key>/card.json for each story, build/share/edition.json,
and build/share/_redirects.share (short-address redirects to append to Netlify's).

Input shapes are the ones the live digest uses (checked 2026-10-27):
  story: key, category, subject, entity, headline, lede, truth/prob/poss/lies
         (HTML strings), featuredImage (data URI), overlayColor, overlayOpacity,
         permalink, backstoryRow, backstoryTitle
         + optional editor overrides under story["share"] (set in Pulse):
           shortSlug, truths[], quote{text, speaker, role, source, sourceExcerpt},
           falseClaim{claim, claimant, correction, source}
  backstory.json: rows[] (id, title, milestone, beginnings[{year, line}]),
                  todays_pairings[] (story_id, row, line, needs_review)

Editorial gates live here, in code, not in prompts:
  * A quote is used only if its text appears verbatim in quote.sourceExcerpt.
  * A false claim is used only when an editor set share.falseClaim in Pulse.
  * A Backstory pairing is used only when needs_review is false
    (or --include-provisional is passed, for previews only).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

SITE = "ntknews.org"
AP_MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
ABBREV = r"(?:Mr|Mrs|Ms|Dr|St|Sen|Rep|Gov|Gen|Lt|Col|Jan|Feb|Aug|Sept|Oct|Nov|Dec|U\.S|U\.N|U\.K|E\.U|Inc|Co|Corp|No|vs)\."


# ── text helpers ─────────────────────────────────────────────────────────────
class _Paras(HTMLParser):
    """Collect <p> paragraphs as text, noting ones that are entirely <strong> (section titles)."""
    def __init__(self):
        super().__init__()
        self.paras, self._buf, self._in_p, self._strong_only, self._depth_strong = [], [], False, True, 0

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self._in_p, self._buf, self._strong_only = True, [], True
        elif tag in ("strong", "b"):
            self._depth_strong += 1

    def handle_endtag(self, tag):
        if tag == "p" and self._in_p:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                self.paras.append({"text": text, "title": self._strong_only})
            self._in_p = False
        elif tag in ("strong", "b"):
            self._depth_strong = max(0, self._depth_strong - 1)

    def handle_data(self, data):
        if self._in_p:
            self._buf.append(data)
            if data.strip() and self._depth_strong == 0:
                self._strong_only = False


def paragraphs(html: str | None) -> list[dict]:
    p = _Paras()
    p.feed(html or "")
    return p.paras


def sentences(text: str) -> list[str]:
    protected = re.sub(ABBREV, lambda m: m.group(0).replace(".", "․"), text)
    parts = re.split(r"(?:(?<=[.!?])|(?<=[.!?][\")”’]))\s+(?=[A-Z“\"‘'])", protected)
    return [s.replace("․", ".").strip() for s in parts if s.strip()]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def slugify(s: str, max_len: int = 28) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:max_len].rstrip("-")


# ── selection rules ──────────────────────────────────────────────────────────
def pick_truths(truth_html: str, k: int = 3, max_len: int = 230) -> list[str]:
    """One item per Truths paragraph: its first cited sentence (ends in a
    parenthetical source), with the sentence before it prepended when that
    still fits. Title paragraphs are skipped. Falls back to the first sentence."""
    out = []
    for para in paragraphs(truth_html):
        if para["title"]:
            continue
        ss = sentences(para["text"])
        idx = next((i for i, s in enumerate(ss) if re.search(r"\([^()]{2,60}\)[.!?\"”]*$", s)), None)
        if idx is None:
            continue  # uncited paragraphs are analysis, not a Truths card line
        item = ss[idx]
        if idx > 0 and len(ss[idx - 1]) + 1 + len(item) <= max_len:
            item = ss[idx - 1] + " " + item
        if len(item) <= max_len + 40:
            out.append(item)
        if len(out) == k:
            break
    return out


def verified_quote(q: dict | None) -> dict | None:
    if not q or not q.get("text") or not q.get("speaker"):
        return None
    excerpt = q.get("sourceExcerpt") or ""
    if norm(q["text"]) not in norm(excerpt):
        print(f"  ! quote dropped: text not found verbatim in sourceExcerpt: {q['text'][:60]}…", file=sys.stderr)
        return None
    return {"text": q["text"], "speaker": q["speaker"], "role": q.get("role", ""), "source": q.get("source", "")}


def false_claim(fc: dict | None) -> dict | None:
    need = ("claim", "claimant", "correction", "source")
    if not fc or not all(fc.get(k) for k in need):
        return None
    return {k: fc[k] for k in need}


def backstory_block(story: dict, bs: dict, include_provisional: bool) -> dict | None:
    pair = next((p for p in bs.get("todays_pairings", []) if p.get("story_id") == story.get("key")), None)
    if not pair or (pair.get("needs_review") and not include_provisional):
        return None
    row = next((r for r in bs.get("rows", []) if r.get("id") == pair.get("row")), None)
    if not row:
        return None
    ms = sorted((b for b in row.get("beginnings") or [] if b.get("year") and b.get("line")),
                key=lambda b: str(b["year"]))
    return {
        "id": row["id"],
        "title": row.get("title", ""),
        # The row's static page, written by editorial/build_backstory_pages.py.
        "url": f"https://{SITE}/backstory/{row['id']}/",
        "short_url": f"{SITE}/backstory",
        "pairing_line": pair.get("line") or row.get("milestone", ""),
        "row_line": row.get("milestone", ""),
        "milestones": [{"year": str(b["year"]), "line": b["line"]} for b in ms[-3:]],
        "today_line": story.get("lede", ""),
    }


# ── assembly ─────────────────────────────────────────────────────────────────
def story_date(permalink: str) -> date | None:
    m = re.search(r"/(\d{4})-(\d{2})-(\d{2})/", permalink or "")
    return date(int(m[1]), int(m[2]), int(m[3])) if m else None


def labels(d: date | None) -> tuple[str, str]:
    if not d:
        return "", ""
    return f"{AP_MONTHS[d.month - 1]} {d.day}, {d.year}", d.strftime("%A, %B ") + str(d.day)


def opacity(v) -> int:
    """Pulse writes overlayOpacity as a string ("45"); the templates divide it."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 45


def build_card(story: dict, bs: dict, include_provisional: bool) -> dict:
    share = story.get("share") or {}
    d = story_date(story.get("permalink", ""))
    date_label, edition_label = labels(d)
    slug = share.get("shortSlug") or slugify(story.get("entity") or story.get("subject") or story.get("key", ""))
    return {"story": {
        "id": story.get("key"),
        "category": story.get("category", ""),
        "subject": story.get("subject", ""),
        "date_label": date_label,
        "edition_label": edition_label,
        "headline": story.get("headline", ""),
        "lede": story.get("lede", ""),
        "permalink": story.get("permalink", ""),
        # Short addresses (SPEC.md 6.3) are not routed yet, so a card that
        # printed one would send readers to a 404. Bare domain until they are.
        "short_url": SITE,
        "photo": {"src": story.get("featuredImage", ""), "overlay_color": story.get("overlayColor") or "#0798F2",
                  "overlay_opacity": opacity(story.get("overlayOpacity")),
                  "alt": story.get("headline", "")},
        "truths": share.get("truths") or pick_truths(story.get("truth", "")),
        "quote": verified_quote(share.get("quote")),
        "false_claim": false_claim(share.get("falseClaim")),
        "backstory": backstory_block(story, bs, include_provisional),
    }, "_slug": slug}


def build_edition(stories: list[dict]) -> dict:
    lead = stories[0]
    d = story_date(lead.get("permalink", ""))
    return {"edition": {
        "edition_label": labels(d)[1], "url": f"https://{SITE}/today", "story_count": len(stories),
        "lead_headline": lead.get("headline", ""),
        "photo": {"src": lead.get("featuredImage", ""), "overlay_color": lead.get("overlayColor") or "#0798F2",
                  "overlay_opacity": opacity(lead.get("overlayOpacity"))},
    }}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stories", required=True, type=Path, help="JSON list of digest stories, or {\"stories\": [...]}")
    ap.add_argument("--backstory", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--include-provisional", action="store_true", help="use pairings still marked needs_review (previews only)")
    args = ap.parse_args()

    raw = json.loads(args.stories.read_text())
    stories = raw["stories"] if isinstance(raw, dict) else raw
    bs = json.loads(args.backstory.read_text())
    args.out.mkdir(parents=True, exist_ok=True)

    redirects, seen = [], set()
    for s in stories:
        card = build_card(s, bs, args.include_provisional)
        slug = card.pop("_slug")
        if slug in seen:  # same-day collision: suffix with the story's month-day
            d = story_date(s.get("permalink", ""))
            slug = f"{slug}-{d:%m%d}" if d else f"{slug}-{s.get('key', '')[:4]}"
        seen.add(slug)
        path = s.get("permalink", "").replace(f"https://{SITE}", "") or "/"
        redirects.append(f"/{slug}  {path}  302")
        out = args.out / (s.get("key") or slug)
        out.mkdir(parents=True, exist_ok=True)
        (out / "card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False))
        st = card["story"]
        print(f"{s.get('key')}: truths={len(st['truths'])} quote={'yes' if st['quote'] else 'no'} "
              f"false={'yes' if st['false_claim'] else 'no'} backstory={'yes' if st['backstory'] else 'no'} → {st['short_url']}")

    if stories:
        (args.out / "edition.json").write_text(json.dumps(build_edition(stories), indent=2, ensure_ascii=False))
    # 302, not 301: short slugs get reused by later stories, and browsers cache 301s.
    (args.out / "_redirects.share").write_text("\n".join(redirects) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
