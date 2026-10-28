---
id: T-0107
title: Shared story links unfurl with NTK's designed preview card, not the bare photo
status: BUILT
tags: [digest, feature]
anchor: ntk-pulse/build_digest.py:797
---

## What

When a story link is pasted into iMessage, WhatsApp, Facebook, X, LinkedIn, Slack or email, the app fetches the story page and shows its `og:image`. Until now that was the raw featured photo (or nothing, for stories without one). `build_digest.py` now renders a 1200×630 designed card per story with the `share-cards/` package (`render_cards.py --only og`) into `digest/<date>/<slug>/share/og.jpg` and points `og:image` and `twitter:image` at it. If the card does not render (renderer not installed, a headline that overflows the card at minimum size, over the 300 KB budget), the page falls back to the photo, as before. `pulse-publish.yml` installs jinja2 and Playwright Chromium in a `continue-on-error` step before "Build digest". Built 2026-10-28. Run against the live lineup (5 stories) in a scratch copy: 5 of 5 cards, 57–143 KB each, about 0.5 s per story; with the renderer missing, all 5 fell back to the photo. Not yet run in GitHub Actions, and not yet seen in a real app's unfurl (unverified).

## Why

A shared link is the most common way a reader brings someone to NTK, and the preview is all the recipient sees before deciding to tap. The bare photo carried no NTK identity and no headline. The `share-cards/` package (delivered 2026-10-27, spec in `share-cards/SPEC.md`) also designs Instagram Story, carousel and Pinterest images and an on-site share panel. Those were held back on purpose: a full image set is about 3.7 MB per story, and the publish bot commits everything to `main`, so shipping them would add roughly 30 MB a day to git history. Where those images live is an open decision. The cards print the bare `ntknews.org` instead of the spec's short addresses (`ntknews.org/ballroom`): those need per-publish redirect rules that do not exist yet, and a printed address that 404s is worse than none. The renderer runs as a subprocess so `build_digest.py` stays stdlib-only and a renderer failure cannot fail a publish (the same posture as the Backstory steps around it). Platforms cache previews hard, and a re-publish on the same day overwrites `og.jpg` at the same URL, so a corrected headline may keep showing the old card until the Facebook Sharing Debugger or LinkedIn Post Inspector refreshes it.

## Check

```sh
# The newest dated edition: at least 80% of its story pages point og:image at
# their own share/og.jpg, and every card they point at exists and is <= 300 KB
# (WhatsApp drops larger previews). 80% tolerates a single headline that
# overflows the card and falls back to the photo; a renderer that broke in CI
# falls back on every story and fails this.
python3 - <<'PY'
import re, sys, pathlib
eds = sorted(p for p in pathlib.Path('digest').iterdir() if re.fullmatch(r'\d{4}-\d{2}-\d{2}', p.name))
ed = eds[-1]
pages = sorted(ed.glob('*/index.html'))
carded = 0
for p in pages:
    m = re.search(r'<meta property="og:image" content="([^"]+)"', p.read_text())
    if m and m.group(1).endswith(f'/digest/{ed.name}/{p.parent.name}/share/og.jpg'):
        og = p.parent / 'share' / 'og.jpg'
        if not og.exists() or og.stat().st_size > 300 * 1024:
            print(f'{og}: missing or over 300 KB'); sys.exit(1)
        carded += 1
print(f'{ed.name}: {carded}/{len(pages)} story pages carry the designed card')
sys.exit(0 if pages and carded >= 0.8 * len(pages) else 1)
PY
```
