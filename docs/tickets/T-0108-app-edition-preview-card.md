---
id: T-0108
title: Links to /today, /digest and frozen editions unfurl with the edition preview card
status: BUILT
tags: [digest, feature]
anchor: ntk-pulse/build_digest.py:846
---

## What

`digest/index.html` is served at /today, /digest, /backstory and /me, and each frozen edition at /digest/<date>/ is a copy of it. Until 2026-10-28 its `<head>` had no Open Graph tags at all, so a copied address-bar link from the app unfurled with no image. It now carries a tag block between `<!-- OG:EDITION -->` markers, which `build_digest.py` rewrites on each publish to point at that day's edition card (`digest/<date>/share/og-edition.jpg`: date, story count, lead headline, lead photo), rendered with the same `share-cards/` renderer as T-0107. If the card does not render, the tags point at the landing page's default `/og-image.png`. Built 2026-10-28 and run against the live lineup in a scratch copy: card rendered (110 KB), live and frozen copies both point at it; with the renderer missing, both fall back to `/og-image.png`. Not yet run in GitHub Actions or seen in a real app's preview (unverified).

## Why

T-0107 gave story permalinks a designed card. The in-app Share button shares those permalinks, but a reader who copies the address bar shares the app's own URL, and that had nothing. One tag block covers every path the app serves because they are all one file. The frozen-edition copy inherits the tags, and because the image URL is dated, an old edition keeps its own day's card rather than whatever is current. /backstory and /me show the edition card too: imperfect for /backstory, but Backstory rows have their own static pages for sharing, and a reasonable card beats none. `og:url` is left out on purpose so each path stays its own canonical. Editions frozen before this change have no tags and stay that way. The landing page (`index.html`) keeps its own static `og-image.png`; the spec suggested pointing it at the edition card, but that changes the front door's preview daily and was not asked for.

## Check

```sh
# The live app's preview points at the newest edition's own card, and that
# card exists and is <= 300 KB. The site-default fallback is a degraded state
# and does not pass.
python3 - <<'PY'
import re, sys, pathlib
html = pathlib.Path('digest/index.html').read_text()
m = re.search(r'<meta property="og:image" content="https://ntknews.org/digest/(\d{4}-\d{2}-\d{2})/share/og-edition.jpg">', html)
if not m:
    print('digest/index.html: og:image is not an edition card'); sys.exit(1)
newest = sorted(p.name for p in pathlib.Path('digest').iterdir() if re.fullmatch(r'\d{4}-\d{2}-\d{2}', p.name))[-1]
card = pathlib.Path('digest', m.group(1), 'share', 'og-edition.jpg')
if m.group(1) != newest or not card.exists() or card.stat().st_size > 300 * 1024:
    print(f'{card}: not the newest edition ({newest}), missing, or over 300 KB'); sys.exit(1)
print(f'/today previews with {card} ({card.stat().st_size // 1024} KB)')
PY
```
