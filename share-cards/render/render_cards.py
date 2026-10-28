#!/usr/bin/env python3
"""Render NTK share cards from a card-data JSON file to PNGs.

    python render/render_cards.py --data sample/sample-card.json --out sample/renders

The card-data contract is documented in SPEC.md (section 4) and produced by
build_card_data.py. This script only lays out and renders; editorial selection
(which truths, whether a quote or a false claim qualifies) happens upstream.

Requires: jinja2, playwright (Chromium). Fonts and logo are self-hosted in
assets/, so rendering needs no network unless photo URLs are remote.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from playwright.sync_api import sync_playwright

PKG = Path(__file__).resolve().parent.parent
TEMPLATES = PKG / "templates"

# name: (template, width, height, what it's for)
FORMATS = {
    "og":            ("og-story.html.j2",     1200,  630, "Link preview for the story permalink: Facebook, X, Threads, Bluesky, LinkedIn, Reddit, iMessage, WhatsApp, Slack, Discord"),
    "og-backstory":  ("og-backstory.html.j2", 1200,  630, "Link preview for a Backstory row page"),
    "og-edition":    ("og-edition.html.j2",   1200,  630, "Link preview for /today and the site default"),
    "story":         ("story-headline.html.j2", 1080, 1920, "Instagram / Facebook Stories, Snapchat, TikTok photo (reader share)"),
    "story-quote":   ("story-quote.html.j2",  1080, 1920, "Story variant when the story carries a verified quote"),
    "pin":           ("pin.html.j2",          1000, 1500, "Pinterest pin (passed as media= in the Pinterest intent)"),
}

# Carousel slides, in order. Each is included only when its data is present.
SLIDES = [
    ("cover",     "slide-cover.html.j2",     lambda s: True),
    ("truths",    "slide-truths.html.j2",    lambda s: bool(s.get("truths"))),
    ("quote",     "slide-quote.html.j2",     lambda s: bool(s.get("quote"))),
    ("false",     "slide-false.html.j2",     lambda s: bool(s.get("false_claim"))),
    ("backstory", "slide-backstory.html.j2", lambda s: bool(s.get("backstory"))),
    ("end",       "slide-end.html.j2",       lambda s: True),
]
SLIDE_W, SLIDE_H = 1080, 1350
# Link-preview cards ship as JPEG: WhatsApp drops previews whose image is much
# over ~300 KB, and a photo-bearing 1200x630 PNG runs ~450 KB. Everything a
# reader posts as an image stays PNG so the type stays crisp after re-compression.
JPEG_FORMATS = {"og", "og-backstory", "og-edition"}
OG_BUDGET_KB = 300
# X and Bluesky allow 4 images per post: this is the subset to hand them.
FOUR_UP = ["cover", "truths", "backstory", "end"]


def resolve_src(src: str, base: Path) -> str:
    if not src or src.startswith(("http://", "https://", "data:", "file://")):
        return src
    return (base / src).resolve().as_uri()


def plan(data: dict) -> list[dict]:
    """Decide which files to render for this card data."""
    story, edition = data.get("story"), data.get("edition")
    jobs: list[dict] = []
    if story:
        jobs.append({"name": "og", "fmt": "og"})
        jobs.append({"name": "story", "fmt": "story"})
        if story.get("quote"):
            jobs.append({"name": "story-quote", "fmt": "story-quote"})
        jobs.append({"name": "pin", "fmt": "pin"})
        if story.get("backstory"):
            jobs.append({"name": "og-backstory", "fmt": "og-backstory"})
        slides = [(k, t) for k, t, keep in SLIDES if keep(story)]
        for i, (key, tpl) in enumerate(slides, 1):
            jobs.append({"name": f"slide-{i:02d}-{key}", "template": tpl, "W": SLIDE_W, "H": SLIDE_H,
                         "slide": {"key": key, "index": i, "total": len(slides)},
                         "use": "Carousel slide (Instagram feed, Threads, Facebook, LinkedIn, Reddit gallery, WhatsApp)"})
    if edition:
        jobs.append({"name": "og-edition", "fmt": "og-edition"})
    for j in jobs:
        if "fmt" in j:
            tpl, w, h, use = FORMATS[j["fmt"]]
            j.update(template=tpl, W=w, H=h, use=use)
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--only", help="comma-separated output names to render (e.g. og,story)")
    ap.add_argument("--keep-html", action="store_true", help="keep the intermediate HTML next to each PNG")
    args = ap.parse_args()

    data = json.loads(args.data.read_text())
    base = args.data.resolve().parent
    for blk in (data.get("story"), data.get("edition")):
        if blk and blk.get("photo"):
            blk["photo"]["src"] = resolve_src(blk["photo"]["src"], base)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), undefined=StrictUndefined,
                      autoescape=True, trim_blocks=True, lstrip_blocks=True)
    jobs = plan(data)
    if args.only:
        wanted = set(args.only.split(","))
        jobs = [j for j in jobs if j["name"] in wanted]
    args.out.mkdir(parents=True, exist_ok=True)

    manifest, failures = [], []
    with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
        browser = pw.chromium.launch()
        for j in jobs:
            html = env.get_template(j["template"]).render(
                root=PKG.as_uri(), W=j["W"], H=j["H"], title=j["name"],
                story=data.get("story") or {}, edition=data.get("edition") or {},
                slide=j.get("slide") or {}, four_up=FOUR_UP)
            page_path = (Path(tmp) / f"{j['name']}.html") if not args.keep_html else (args.out / f"{j['name']}.html")
            page_path.write_text(html)
            page = browser.new_page(viewport={"width": j["W"], "height": j["H"]}, device_scale_factor=1)
            page.goto(page_path.resolve().as_uri())
            page.wait_for_function("window.__fitDone === true", timeout=15000)
            over = page.eval_on_selector_all("[data-overflow]", "els => els.map(e => (e.className || e.tagName) + '')")
            clip = {"x": 0, "y": 0, "width": j["W"], "height": j["H"]}
            if j.get("fmt") in JPEG_FORMATS:
                img = args.out / f"{j['name']}.jpg"
                for q in (86, 80, 74, 68):
                    page.screenshot(path=str(img), clip=clip, type="jpeg", quality=q)
                    if img.stat().st_size <= OG_BUDGET_KB * 1024:
                        break
                else:
                    failures.append(f"{img.name}: {img.stat().st_size // 1024} KB, over the {OG_BUDGET_KB} KB link-preview budget")
            else:
                img = args.out / f"{j['name']}.png"
                page.screenshot(path=str(img), clip=clip)
            page.close()
            if over:
                failures.append(f"{j['name']}: text still overflows at minimum size in {over}")
            manifest.append({"file": img.name, "width": j["W"], "height": j["H"], "bytes": img.stat().st_size,
                             "use": j["use"], **({"slide": j["slide"]} if j.get("slide") else {})})
            print(f"rendered {img.name} ({j['W']}x{j['H']}, {img.stat().st_size // 1024} KB)")
        browser.close()

    (args.out / "manifest.json").write_text(json.dumps(
        {"four_up": [m["file"] for m in manifest if m.get("slide", {}).get("key") in FOUR_UP], "files": manifest},
        indent=2))
    if failures:
        print("\nOVERFLOW — fix the copy or the selection rules before publishing:", *failures, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
