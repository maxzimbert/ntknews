---
id: T-0091
title: Pulse's Backstory preview looks like the reader's /backstory page
status: VERIFIED
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Raised by the editor 2026-10-15 with two screenshots. The reader's card on ntknews.org/backstory
(`renderBackstoryTab` in `digest/index.html`) reads top to bottom: TODAY, the pairing line in quotes, IT
STARTS IN <year> in red capitals, the origin in italic serif, a small mark, and the category name in bold
sans at the foot. The same story in Pulse's TODAY'S PAIRINGS list (`pairingsHtml` in
`ntk-pulse/pulse.html`) reads: the category name in bold with the classifier's confidence ("1.00"), "It
starts in 2022" in plain sans, the origin in plain sans, then the pairing line, then the headline, in a grey
bordered box. Same data, different order, labels and type. The category PREVIEW (`catPreviewHtml`) is a third
layout again (Georgia, BEGINNINGS, WE ARE HERE), and the reader's category page (`showBsrPage`) a fourth.

Wanted: Pulse renders today's pairings and each category's preview with the reader's own markup and CSS,
fed Pulse's data. Editor-only facts (confidence, the headline, needs-review flags, draft status) sit outside
the card, in a strip above or beside it, so the card itself is exactly what a reader will see. The way to
get there is to share the render code (one function both pages load), not to copy the look into Pulse,
which would drift again.

Seen in the same screenshots, unverified: Pulse's Ukraine-Russia line ("A private company decided overnight
how much of the war Kyiv could see...") is not the line live on /backstory that day ("A private company's
pricing tier decided what Kyiv could see and strike overnight..."). Pulse caches the published
`backstory.json` for the session (`BSR_PUBLISHED`), so a Pulse tab opened before a later publish shows the
older pairings. The parity work should refetch after a publish or say how old the copy is.

## Why

Approving is the editor's last look. If the preview differs from the page, approval checks the wrong thing,
and every difference becomes a surprise found in production. `docs/design-system.md` governs the reader
page's look; Pulse should borrow it, not restate it.

Built 2026-10-15. The reader's card is one pure function, `bsrCardHtml`, and its CSS one block, both between
BSR-CARD markers in `digest/index.html`. Pulse fetches `../digest/index.html`, takes the code and CSS from
between the markers (plus the page's `:root` colours and its Google Fonts link) and draws with them, so a
change to the reader's card shows in Pulse with no second edit. TODAY'S PAIRINGS shows each story as the
reader's card with the editor's facts (row, confidence, review and fit flags, headline) in a strip above it;
each category shows THE CARD, AS READERS SEE IT for every story filed under it. Pulse re-reads the published
`backstory.json` after a minute instead of keeping the first copy for the session. If the card cannot be
read, Pulse says so and falls back to plain text.

Checked in a local preview: the reader's Backstory tab produces byte-identical HTML before and after the
refactor (7 cards, 5,186 characters, against main's page on the same data); Pulse draws 7 reader cards in
Newsreader on the cream ground with the terra label.

Not done: the category PAGE (`showBsrPage`, designs 4C and 4D) is still a Pulse summary, labelled as such.
That is the second half of this ticket.

## Check

```sh
python3 - <<'PY' > /tmp/t0091.js || exit 1
import re
s = open('digest/index.html', encoding='utf-8').read()
js = re.search(r'/\* BSR-CARD:BEGIN[^*]*\*/([\s\S]*?)/\* BSR-CARD:END \*/', s)
css = re.search(r'/\* BSR-CARD-CSS:BEGIN[^*]*\*/([\s\S]*?)/\* BSR-CARD-CSS:END \*/', s)
p = open('ntk-pulse/pulse.html', encoding='utf-8').read()
if not js or not css or '.bt-row' not in css.group(1) or 'BSR-CARD:BEGIN' not in p or 'bsrCardHtml(' not in p: raise SystemExit(1)
print("var document={createElement:function(){var o={set textContent(v){o.innerHTML=String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}};return o;}};")
print(js.group(1))
print("""var h=bsrCardHtml({id:'p-x',title:'Robots and Law',start_date:'2026-10-15',stratum:'provisional',pairline:'A robot did a thing.',origin:{status:'retrieved',year:1999,line:'It began'}},'#',0);
if (h.indexOf('bt-row')<0 || h.indexOf('A robot did a thing.')<0 || h.indexOf('It starts in 1999')<0) { console.log(h); process.exit(1); }""")
PY
node /tmp/t0091.js
# manual: the category page (showBsrPage) in Pulse matches /backstory/<id>/
```
