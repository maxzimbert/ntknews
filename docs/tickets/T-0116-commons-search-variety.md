---
id: T-0116
title: Pulse's photo search shows varied photos of a subject, not one event's batch filling the grid
status: VERIFIED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html:809
---

## What

The editor searched "Russell Brand" in Pulse on 2026-11-09 and every candidate looked like it came from
one conference. Measured the same day against the Commons API with the old query: of the 24 landscape
results it kept from a 40-file keyword search, 18 were one photographer's upload of "AmericaFest 2025"
(Turning Point USA, December 2025). Pulse showed the first 12. Commons holds 176 files in
`Category:Russell_Brand`, from 2008 to 2025, and the old search never reached most of them.

Built in `ntk-pulse/pulse.html`, all free and keyless:

1. **One tile per upload batch.** `commonsBatchKey` strips the sequence number and Flickr import id from
   the file name and adds the day taken; `commonsGroup` folds a batch into one tile with "+N more", which
   opens the set and has a way back.
2. **The subject, not just the words.** `commonsEntity` matches the query to a Wikidata item by exact
   label or alias (so a headline-like query finds nothing and falls back cleanly). Its Commons category
   (P373) and the files tagged as depicting it (`haswbstatement:P180=`) are searched alongside the
   keyword search and ranked first. The API returns file details for 50 files per response, so
   `commonsPages` follows `iicontinue`.
3. **Tall photos kept.** The landscape-only filter (`ratio > 1.2`) is gone. `lockCommonsImage` crops a
   tall or square photo to 16:9, centred 25% from the top, matching the digest's `object-position`.
   Tiles show the date taken and caption. The lock reads the 1,280px rendition, not a 6,000px original.

Verified 2026-11-09 in a local Pulse against live Commons: "Russell Brand" gave 24 different tiles from
2008 to 2025, eight of them sets; a tall photo locked at 800×450 with its credit; a landscape one locked
at 800×508, uncropped; "Marco Rubio" resolved to its category. **Unverified on GitHub Pages Pulse**
until this merges.

## Why

The photo is the first thing a reader sees in the digest, and the Commons search is the only route to a
photo of a real person: AI images of identifiable public figures are ruled out (`docs/decisions.md`,
"Images and illustration"). A search that returns one event leaves the editor choosing between that event
and no photo. For a contested figure that is not neutral: a story about Russell Brand illustrated only from
a Turning Point USA stage frames him by one political setting.

Considered and set aside on 2026-11-09: other free sources (Openverse, Flickr open licenses, US government
photo sets) as further buttons, and a memory of photos already used per subject. The editor dropped the
memory as likely to make the photos repetitive. The other sources remain options. Paid editorial libraries
were left for a lead story with no usable free photo. Getty's free embed cannot work here: it shows only
inside Getty's frame, and the build needs a real file for `og:image`.

Each search now makes up to about ten Commons requests instead of one. Commons rate-limits a client that
makes many requests in quick succession (a test run from Node got 429s after a few dozen searches). One
editor searching by hand will not hit that. If one fails, the others still return; if all fail, the panel
shows the error.

## Check

```sh
# Run the real grouping and filtering code on fixture Commons pages: a 24-photo
# batch from one event plus four different photos (one tall, one SVG logo).
# Pass: 5 tiles, the batch is one tile of 24, the tall photo is kept, the SVG is
# dropped. Then the subject lookups, pagination and the 16:9 crop are present.
node - <<'JS'
const s = require('fs').readFileSync('ntk-pulse/pulse.html', 'utf8');
const grab = n => { const i = s.indexOf('function ' + n + '('); return i < 0 ? '' : s.slice(i, s.indexOf('\n}\n', i) + 2); };
const bad = [];
let lib;
try { lib = new Function(grab('commonsText') + grab('commonsItem') + grab('commonsBatchKey') + grab('commonsGroup') +
  'return {commonsItem, commonsGroup};')(); } catch (e) { bad.push('Commons helpers do not load: ' + e.message); }
const page = (title, w, h, date, mime) => ({ title, imageinfo: [{ width: w, height: h, mime: mime || 'image/jpeg',
  url: 'https://upload.wikimedia.org/x.jpg', thumburl: 'https://thumb.wikimedia.org/x/1280px-x.jpg',
  extmetadata: { DateTimeOriginal: { value: date }, LicenseShortName: { value: 'CC BY-SA 4.0' } } }] });
if (lib) {
  const pages = [];
  for (let i = 1; i <= 24; i++) pages.push(page(`File:AmericaFest 2025 - Russell Brand ${String(i).padStart(2, '0')}.jpg`, 6000, 3376, '2025-12-18 18:19:18'));
  pages.push(page('File:Russell Brand Roxy-2008 1.jpg', 3008, 2000, '2008-06-02'));
  pages.push(page('File:Russell Brand at the Cambridge Union Society.JPG', 4000, 3000, '2014-01-13'));
  pages.push(page('File:Russell Brand 2008.jpg', 1000, 1200, '2008-01-25'));
  pages.push(page('File:Russell Brand (5622561306).jpg', 720, 480, '2011-04-16'));
  pages.push(page('File:Russell Brand signature.svg', 900, 560, '', 'image/svg+xml'));
  const groups = lib.commonsGroup(pages.map(p => lib.commonsItem(p, 0)).filter(Boolean));
  const sizes = groups.map(g => g.items.length).sort((a, b) => b - a).join(',');
  if (sizes !== '24,1,1,1,1') bad.push('one event\'s batch is not folded into one tile; tile sizes: ' + sizes);
  if (!groups.some(g => g.items[0].ratio < 1)) bad.push('a tall photo was dropped from the results');
  if (groups.some(g => /\.svg$/.test(g.items[0].title))) bad.push('an SVG reached the results');
}
if (!/haswbstatement:P180=/.test(s)) bad.push('no search for files tagged as depicting the subject');
if (!/claims\.P373/.test(s)) bad.push('no lookup of the subject\'s Commons category');
if (!/iicontinue/.test(s)) bad.push('Commons results stop at the first 50 files');
if (!/sw \* 9 \/ 16/.test(grab('lockCommonsImage'))) bad.push('tall photos are not cropped to 16:9 at lock');
if (/ratio > 1\.2/.test(grab('commonsSearch') + grab('commonsItem'))) bad.push('the landscape-only filter is back');
bad.forEach(b => console.log(b));
process.exit(bad.length ? 1 : 0);
JS
```
