# NTK share cards — implementation spec

Prepared Oct. 27, 2026 for implementation in the NTK repo with Claude Code.
Everything in this package was built against the **live** ntknews.org: its
stylesheet, its `stories[]` shape, and `digest/data/backstory.json`.

> **Before editing any NTK file:** read the current version from the repo.
> Never rebuild `build_digest.py`, the digest `index.html`, `netlify.toml`, or
> the GitHub Actions workflows from memory or from this document. This package
> adds new files and describes small, targeted insertions into existing ones.

---

## 1. What a reader can do, platform by platform

There are two kinds of share. **Link shares** go through each platform's own
composer and unfurl the story's link preview (`og.jpg`). **Image shares** hand
our rendered images to the phone's share sheet.

| Platform | How a reader shares from ntknews.org | What the audience sees | Our asset |
|---|---|---|---|
| Facebook | Web intent (`sharer.php?u=`) | Link card | `og.jpg` |
| X | Web intent (`x.com/intent/tweet`, text + url) | Post + large link card | `og.jpg` |
| Threads | Web intent (`threads.com/intent/post`, text + url) | Post + link card | `og.jpg` |
| Bluesky | Web intent (`bsky.app/intent/compose`, text only; first URL becomes the card) | Post + link card | `og.jpg` |
| LinkedIn | Web intent (`share-offsite/?url=`) | Link card | `og.jpg` |
| Reddit | Web intent (`submit?url=&title=`) | Link post with preview | `og.jpg` |
| Pinterest | Web intent (`pin/create/button/?url=&media=&description=`) | Pin with **our image and a live link** | `pin.png` |
| WhatsApp | `wa.me/?text=` | Message + link card | `og.jpg` |
| iMessage, Slack, Discord, Signal, email | Native share sheet / copy link / `mailto:` | Link card | `og.jpg` |
| Instagram Stories (also Facebook Stories, Snapchat) | Share sheet with one image file; link copied to clipboard | Our Story card; link only if the reader adds a sticker | `story.png` (+ `story-quote.png` when available) |
| Instagram feed, Threads, Facebook, LinkedIn image posts | Share sheet with all slide files ("Slides") | Carousel | `slide-NN-*.png` |

Things no platform allows, so don't build toward them:

- **No one can attach a link to a reader's Instagram Story.** Meta's Sharing to
  Stories kit takes images and colors only, and only from native apps. The
  card carries the story's short address instead (§6.3).
- **No platform lets a website post for a reader.** Every path above ends in
  the platform's composer or the share sheet, where the reader confirms.
- **Facebook and LinkedIn ignore pre-filled text.** They take a URL and read
  the page's Open Graph tags.

## 2. Formats

| File | Size | Rendered when | Used for |
|---|---|---|---|
| `og.jpg` | 1200×630 | every story | Link previews everywhere (§1) |
| `og-backstory.jpg` | 1200×630 | story has an approved Backstory pairing | Link preview for the Backstory row page |
| `og-edition.jpg` | 1200×630 | once per edition | `/today` and the site-wide default `og:image` |
| `story.png` | 1080×1920 | every story | Instagram / Facebook Stories, Snapchat, TikTok photo |
| `story-quote.png` | 1080×1920 | story has a verified quote | Story variant |
| `pin.png` | 1000×1500 | every story | Pinterest |
| `slide-NN-<key>.png` | 1080×1350 (4:5) | per §5 | Carousels; `manifest.json` lists them and the 4-image subset |

Link cards are JPEG to stay under ~300 KB (WhatsApp drops previews it judges
too large; the renderer fails the build over budget). Everything a reader
posts as an image is PNG so type survives the platforms' re-compression.

4:5 is the one feed shape every platform here accepts without cropping the
type. X and Bluesky allow four images per post; `manifest.json` names the
subset (cover, truths, backstory, end) for any future NTK-account posting.

## 3. Design rules

All values come from the live site and live in `tokens/tokens.css` (and
`tokens/tokens.json` for Python or Pulse).

- **Palette:** the site's own variables: `--ink #261F23`, `--cream #EAD9C5`,
  `--cream-raised #FBF4EA`, `--amber #F2AE2E`, `--coral #DC6550`,
  `--coral-deep #A33421`, `--blue #0798F2`, `--blue-deep #045E96`,
  `--teal #01B2A7`. Grounds rotate between ink, cream, cream-raised, amber
  (end card) and blue-deep (quote Story) the way the site's sections do.
- **Type:** Newsreader for headlines (600, −0.035em), body (400), the amber
  italic accent, and small-caps section labels. Overpass for eyebrows (600,
  uppercase, +0.1em), buttons and URLs. Fonts are self-hosted in
  `assets/fonts/` (OFL), so CI renders match the site with no network.
- **Shape:** 3px corners and full pills. Nothing in between.
- **Motifs reused from the site, not invented:**
  - the hero: ink ground, "Get clear on *what's news.*" with the amber italic
    accent, and a cream story card overlapping a duotone photo;
  - the four questions encoded by **rule weight** (Truths 6px ink,
    Probabilities 5px ink 60%, Possibilities 4px ink 34%, Lies 6px coral-deep,
    italic);
  - the Backstory timeline: years, ink dots on a hairline, ending in the coral
    ring marked **Today / You came in here**;
  - amber buttons with ink text; an ink button on the amber end card.
- **Photos:** duotone, tinted by the story's Pulse `overlayColor` at
  `overlayOpacity`, the same per-story editorial call the digest already
  uses. If the digest has its own duotone function, use that one so cards and
  site match exactly.
- **Logo:** `assets/logo/ntk-logo-{white,ink,cream}.svg`, taken from the
  digest's embedded SVG (the bars-above-and-below mark). Never retype it in
  CSS.
- **Text never clips.** Every variable-length block has a box and a
  `data-fit="max,min"` range; the fit script steps the size down to fit. If
  copy still overflows at the minimum, the renderer exits non-zero and names
  the card. Fix the selection, not the template.
- **Safe zones:** link cards keep everything essential inside x 64–700 (some
  apps crop the sides). Story cards keep the bottom ~320px clear for an
  optional link sticker and the app's reply bar.

## 4. Card data contract

`render/build_card_data.py` produces one `card.json` per story from the live
data. `sample/sample-card.json` is a full example.

| Field | Type | From (live data) |
|---|---|---|
| `story.id` | string | `story.key` |
| `story.category`, `story.subject` | string | same fields |
| `story.date_label` | "Oct. 15, 2026" (AP months) | date in `permalink` |
| `story.edition_label` | "Thursday, October 15" | date in `permalink` |
| `story.headline`, `story.lede` | string | same fields |
| `story.permalink` | absolute URL, trailing slash | `story.permalink` |
| `story.short_url` | "ntknews.org/<slug>" | `share.shortSlug` (Pulse) or slug of `story.entity` |
| `story.photo` | `{src, overlay_color, overlay_opacity, alt}` | `featuredImage` (data URI is fine here), `overlayColor`, `overlayOpacity` |
| `story.truths` | 1–3 strings, each with its citation | `share.truths` (Pulse) or auto-picked from `story.truth` (§5) |
| `story.quote` | `{text, speaker, role, source}` or null | `share.quote` (Pulse), verbatim-checked |
| `story.false_claim` | `{claim, claimant, correction, source}` or null | `share.falseClaim` (Pulse only) |
| `story.backstory` | `{id, title, url, short_url, pairing_line, row_line, milestones[≤3], today_line}` or null | `backstory.json`: `todays_pairings[]` matched on `story_id`, then `rows[]` |
| `edition` | `{edition_label, url, story_count, lead_headline, photo}` | `stories[0]` + count |

New, optional fields Pulse should write under `story.share`:
`shortSlug`, `truths[]`, `quote{text, speaker, role, source, sourceExcerpt}`,
`falseClaim{claim, claimant, correction, source}`.

## 5. Assembly rules

The carousel varies by story. Order is fixed; slides without data are skipped
and the `NN / total` counters are computed.

1. **Cover**: always.
2. **What's true?**: always (if no Truths line qualifies, fail the card and
   flag it in Pulse; don't render an empty slide).
3. **Quote**: only with a quote that passed the verbatim check.
4. **What's false?**: only when an editor set `share.falseClaim`.
5. **Backstory + We are here**: only with an approved pairing.
6. **End card**: always.

So a story runs 3 to 6 slides. The sample story, as published, would run 3
(its pairing is still `needs_review`, and it has no quote or named false claim).

**Gates, enforced in code** (a prompt instruction alone is not enough for a
deterministic requirement):

- **Truths auto-pick:** one line per Truths paragraph, using the paragraph's
  first sentence that ends in a parenthetical citation, with the sentence
  before it prepended when the pair fits (≤230 characters). Bold title
  paragraphs and uncited paragraphs are skipped: an uncited paragraph is
  analysis, not a fact card. An editor can override with `share.truths`.
- **Quote:** the text must appear verbatim (quotes and whitespace normalized)
  in `share.quote.sourceExcerpt`, which the editor pastes from the source
  article. Fails closed: no match, no quote slide, no quote Story.
- **False claim:** never generated. Only an editor-entered
  `share.falseClaim` with all four fields renders. The slide always shows the
  claim labeled **FALSE** with the correction underneath, so a cropped
  screenshot can't spread the claim on its own. (This is the social
  counterpart to keeping Lies out of audio: friction stays, here as the
  label and the pairing.)
- **Backstory:** only when the pairing's `needs_review` is false. Use
  `--include-provisional` for previews only, never in the publish job.
  Milestones are the row's last three `beginnings`, oldest first.

## 6. Build integration

### 6.1 Where it runs
After `build_digest.py` writes the static story pages, in the publish
workflow (`pulse-publish.yml`):

```bash
pip install -r share-cards/render/requirements.txt
python -m playwright install --with-deps chromium

python share-cards/render/build_card_data.py \
  --stories <the digest's stories JSON> \
  --backstory digest/data/backstory.json \
  --out build/share

for card in build/share/*/card.json; do
  key=$(basename "$(dirname "$card")")
  dest="<that story's permalink directory>/share"   # e.g. digest/2026-10-15/<slug>/share
  python share-cards/render/render_cards.py --data "$card" --out "$dest" || exit 1
done
python share-cards/render/render_cards.py --data build/share/edition.json --out digest/today-share
```

Cost: about 5 seconds for a full set of 12 images on one story (measured
here), so a five-story edition adds well under a minute.

### 6.2 Tags
Render `web/og-meta.html.j2` into each story page's `<head>`, replacing any
story-level OG tags the build writes now. Point `/today`'s `og:image` and the
site default (`/og-image.png`) at `og-edition.jpg`. Image URLs must be
absolute hosted files; `og:image` can't be a data URI.

### 6.3 Short addresses
`build_card_data.py` writes `_redirects.share`. Merge it into Netlify's
redirects above any catch-alls, with a reserved-words check. Details and
cache headers are in `netlify/redirects-and-headers.md`. Use 302s: slugs get
reused.

### 6.4 On the site
- Load `web/share.css` and `web/share.js` on the digest.
- Point the existing Share button at `NTKShare.open(stories[currentStoryIndex])`.
  Keep the existing `shareStory()` (native share sheet) reachable, as a "More"
  row or as the default on platforms where the panel adds nothing.
- Keep the existing analytics: `share.js` calls `window.track` with
  `story_share_platform`; also call `beatsRecordShare(subject, 'share')` on
  any completed share so the Beats system counts it.
- `shareBackstory()` should get the same panel, pointed at the Backstory
  row's URL and `og-backstory.jpg`.

### 6.5 Pulse
Add a Share panel to the story editor: the rendered cards as thumbnails, the
four `share.*` fields, the pairing's review status, and a warning when the
renderer reported an overflow.

## 7. QA before turning it on

- [ ] `python render/render_cards.py --data sample/sample-card.json --out /tmp/r` exits 0 and the PNGs match `sample/renders/`.
- [ ] A real edition renders with no overflow failures.
- [ ] Facebook Sharing Debugger, LinkedIn Post Inspector, and a pasted link
      in X, Threads, Bluesky, iMessage, WhatsApp and Slack all show `og.jpg`.
- [ ] On an iPhone (Safari) and an Android phone (Chrome): Instagram Story
      share, then "Slides" into Instagram feed, Threads, WhatsApp and LinkedIn.
      **Record which apps turn several files into one carousel post**; this
      varies by app and OS version and isn't documented. If an app takes only
      the first image, change the "Slides" status line for that platform to
      point readers to "Save all, then post from the app."
- [ ] Desktop: image rows download files; link rows open intents in a popup.
- [ ] Every short address resolves; none shadows a real route.
- [ ] Panel: keyboard reachable, Escape closes and returns focus, 44px
      targets, status line announced.

## 8. Open decisions (for Max)

1. **Handle.** Add `twitter:site` and an @handle on the cards once accounts exist.
2. **Backstory link target.** The "We are here" button points at
   `today#backstory/<row id>`. Confirm the route `shareBackstory()` uses.
3. **Short-slug style.** Default is the slugified `entity`
   (`/white-house-ballroom`). Pulse can override with something shorter
   (`/ballroom`).
4. **Wording.** Card copy reuses site lines ("Get clear on what's news.",
   "The lead story right now", "See how NTK reads it", "Free. No sign-up. No
   endless feed."). New strings: "Read it on NTK", "Swipe for what's true",
   "In their words", "We are here", "The claim", "What the record shows".

## Sources

- Meta, Sharing to Stories: https://developers.facebook.com/documentation/instagram-platform/sharing-to-stories
- Meta, Threads web intents: https://developers.facebook.com/documentation/threads/threads-web-intents
- X, Web intent: https://docs.x.com/x-for-websites/post-button/guides/web-intent
- Bluesky, Action intent links: https://www.docs.bsky.app/docs/advanced-guides/intent-links
