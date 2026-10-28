# NTK share cards

Share images and a share panel for ntknews.org, styled from the live site.

> **Wired in the repo:** `og.jpg`, each story's link preview (T-0107), and
> `og-edition.jpg`, the app's link preview (T-0108), both rendered by
> `ntk-pulse/build_digest.py`. The Story, carousel and pin images, the
> share panel in `web/`, and the short addresses in `netlify/` are not wired yet.

- **3 link-preview cards** (1200×630), used automatically by Facebook, X,
  Threads, Bluesky, LinkedIn, Reddit, WhatsApp, iMessage, Slack and Discord
  whenever someone pastes a story link.
- **2 Story cards** (1080×1920) for Instagram and Facebook Stories.
- **A 3–6 slide carousel** (1080×1350) assembled per story from its Truths,
  a verified quote, a named false claim, and its Backstory pairing.
- **A Pinterest pin** (1000×1500).
- **`share.js`**: an on-site share panel with web intents for every platform
  above, plus image sharing to the phone's share sheet.

## Start here (Claude Code)

1. Read `SPEC.md` end to end. Section 6 is the integration plan.
2. Read the current NTK files you'll touch (`build_digest.py`, the digest
   `index.html`, `netlify.toml`, `pulse-publish.yml`) before changing them.
3. Copy this folder into the repo as `share-cards/` and run the sample:

```bash
pip install -r share-cards/render/requirements.txt
python -m playwright install chromium
python share-cards/render/render_cards.py \
  --data share-cards/sample/sample-card.json --out /tmp/ntk-cards
```

Compare `/tmp/ntk-cards` with `sample/renders/`. Then try the data builder on
the live shapes in `sample/live-shape/`:

```bash
python share-cards/render/build_card_data.py \
  --stories share-cards/sample/live-shape/stories.json \
  --backstory share-cards/sample/live-shape/backstory.json \
  --out /tmp/ntk-build --include-provisional
```

## What's in the box

```
SPEC.md                      platform matrix, formats, design rules, data contract,
                             assembly gates, build integration, QA, open decisions
tokens/tokens.css            palette, type, shape, duotone; @font-face for self-hosted fonts
tokens/tokens.json           same values for Python / Pulse
assets/fonts/                Newsreader 400/600 (+italic), Overpass 500/600/700, OFL licenses
assets/logo/                 the NTK mark from the digest's SVG: white, ink, cream, source
templates/                   Jinja2 templates: _base, _macros, 3 og-*, 2 story-*, 6 slide-*, pin
render/render_cards.py       card.json → PNG/JPEG + manifest.json (fails on overflow or over-budget)
render/build_card_data.py    stories[] + backstory.json → card.json (editorial gates in code)
web/share.js, share.css      on-site share panel (pure ASCII, no dependencies)
web/og-meta.html.j2          per-story Open Graph / Twitter tags
netlify/                     short-address redirects and cache headers
sample/                      sample card data, live-shape inputs, stand-in photo, renders
```

The sample photo is a generated stand-in (no NTK photo could be pulled into
the build environment); real `featuredImage`s render through the same duotone.
