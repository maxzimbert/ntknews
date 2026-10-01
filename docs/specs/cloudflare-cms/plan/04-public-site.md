# 04 — Public site

## Routes

| Route | Renders | Cache | Mock |
|---|---|---|---|
| `GET /` | Landing page (port of root `index.html`; hero story from the live edition) | `s-maxage=300`, tag `app` | `mocks/public-landing.svg` |
| `GET /today`, `/digest`, `/digest/`, `/backstory`, `/me` | The app (`app.tsx`) with the live edition payload injected; the app opens the tab from the path | `s-maxage=300`, tag `app` | `mocks/public-app.svg` |
| `GET /digest/:date/` | Frozen edition: the app rendered with that edition's payload, `<link rel=canonical>` to itself, no "today" chrome | `s-maxage=86400`, tag `edition:<date>` | `mocks/public-edition.svg` |
| `GET /digest/:date/:slug/` | Story permalink page (port of `build_story_page`) with OG/Twitter tags, hero image from R2, back link | `s-maxage=86400`, tag `edition:<date>` | `mocks/public-story.svg` |
| `GET /digest/archive/` | Archive index from `editions` | `s-maxage=300`, tag `archive` | `mocks/public-archive.svg` |
| `GET /digest/images/:slug.jpg` | Legacy image path → 302 to `/media/<id>` (mapping stored at import) | 1 day | |
| `GET /media/:id` | R2 object, `Content-Type` from `media.mime`, `immutable, max-age=31536000` | edge + browser | |
| `GET /media/:id/w/:width` | Resized variant via Cloudflare Image Resizing (`cf: {image: {width}}`); falls back to original if resizing is not enabled on the zone | immutable | |
| `GET /api/public/edition/live` | The live edition JSON (what the app loads if it needs to refresh) | `s-maxage=60` | |
| `GET /api/public/backstory` | Latest backstory publish JSON | `s-maxage=60` | |
| `GET /api/news?mode=…` | Weather / local news proxy (port of `netlify/functions/news.js`) | KV 15 min | |
| `POST /api/public/suggest` | Reader suggestion; Turnstile verified; rate-limited by IP hash in KV | no | |
| `GET /digest/latest`, `/digest/v2`, `/digest/v2/*`, `/digest/index.html` | 301 from `redirects` table | | |
| `GET /sitemap.xml`, `/robots.txt`, `/favicon.png`, `/apple-touch-icon.png`, `/og-image.png` | generated / static assets | | |

Trailing-slash handling: `/digest/2026-08-28` redirects to `/digest/2026-08-28/`
(301), matching today's behaviour so old links keep working.

## The app port (`public/app.tsx`)

`digest/index.html` (4,094 lines) becomes a Hono JSX template with three
substitutions and one deletion:

1. `const stories = [...]` and `const funFact = ...` → `<script id="ntk-edition" type="application/json">` with the edition snapshot, read by a 10-line loader. No other JS changes.
2. `featuredImage: "data:image/jpeg;base64,…"` → `featuredImage: "/media/<id>/w/1200"`; the app's `<img>` gets `loading="lazy"` and `decoding="async"`.
3. `fetch('/digest/data/backstory.json')` → `fetch('/api/public/backstory')`.
4. Route boot stays (it reads `location.pathname`); the `TAB_PATHS` map stays.

Weather and local news calls change host from `/.netlify/functions/news` to
`/api/news`. The Profile tab (`/me`) stays client-side with `localStorage`
beats. The share button uses `permalink` from the payload, which is now
guaranteed to exist because it is computed at publish.

Expected result: HTML under 200 KB; images lazy; first paint unchanged.

## Rendering and caching

Public responses are built by `lib/cache.ts`:

```
key   = request URL (normalized, no query except allowed ones)
hit   → caches.default.match(key)  → return
miss  → render from D1/R2 → Response with Cache-Control + Cache-Tag → caches.default.put (waitUntil) → return
```

Publish purges by tag (`edition:<date>`, `app`, `archive`) through the zone
purge API using `CF_API_TOKEN_CACHE_PURGE`, then warms `/today` and the new
edition URL. Tag purge requires the zone; on staging (no tag purge on the
Workers-only plan is assumed) the TTL is 30 seconds instead.

Preview: `GET /admin/preview/app` renders the app from the working lineup
(no cache, Access-protected). Same template, so what the editor sees is what
publishes.

## Redirects

`public/redirects.ts` loads the `redirects` table into memory per isolate
(refreshed every 60 s) and applies exact and `/*` prefix rules before
routing. Seeded rules:

| From | To | Status |
|---|---|---|
| `/digest/latest` | `/today` | 301 |
| `/digest/v2` | `/today` | 301 |
| `/digest/v2/*` | `/digest/:splat` | 301 |
| `/digest/index.html` | `/today` | 301 |

Old GitHub Pages URLs (`maxzimbert.github.io/ntknews/...`) cannot be
redirected by this Worker; the Pages site is simply switched off.

## News proxy (`/api/news`)

Port of the thirteen modes of `netlify/functions/news.js` (`weather`,
`resolve-location`, `local-news`, `scan-*`, `fetch-*`, `resolve-concept`,
`context-scan`). Public modes: `weather`, `resolve-location`, `local-news`.
All other modes require an Access session (they serve the CMS's source
search) and live under `/api/admin/search`. Responses are cached in KV by
mode plus rounded coordinates (2 decimals) or normalized query for 15
minutes. Keys (`NEWSAPI_KEY`, `EXA_API_KEY`) are Worker secrets.

## Suggestions

The app's "suggest a story" CTA posts `{text, url?, contact?, token}` to
`/api/public/suggest`. The Worker verifies the Turnstile token, hashes the
IP, rate-limits to 5 per hour per hash, inserts `suggestions`, and returns
`{ok:true}`. Suggestions appear in the stream's Suggestions pane.

## SEO and sharing

- Permalink pages carry `og:title`, `og:description` (lede), `og:image`
  (`/media/<id>/w/1200`), `og:url` (canonical), `twitter:card=summary_large_image`.
- `sitemap.xml` lists editions and permalinks from `editions`/`edition_stories`.
- `robots.txt` disallows `/admin/` and `/api/`.

## Analytics

The existing Google Analytics tag is kept as-is in the template. In addition
the Worker writes one Analytics Engine data point per public page view
(route, edition, country) so the dashboard can show traffic without a third
party.
