---
id: T-0070
title: Pulse now logs which outlets fed each story, and Truths reads wire copy first
status: BUILT
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html:509
---

## What

Opened 2026-10-05 after the editor was asked which publishers the digest draws
on and could not say. Three changes, built, not yet seen in a real publish:

1. **Source log.** `buildStoryPayload()` adds `sources` to each story: domain,
   outlet, wire flag, origin (er / rss / editor), where the body came from and
   its length. `build_digest.py` appends one line per story to
   `ntk-pulse/data/source-log.jsonl` and the reader-facing build ignores the
   field (it writes only named fields). `pulse-publish.yml` commits the file.
2. **Truths prefers wire copy.** `artsBlock()` puts AP, Reuters and AFP articles
   first, tagged `[WIRE]`, with a one-paragraph source note. The other three
   sections get the same text as before.
3. **Wire top-up.** If enrichment finds no wire article and the story has a
   `narrowKeyword`, Pulse makes one extra EventRegistry call (`pool=wire`,
   at most 3 articles).

Measured on 2026-10-05: Pulse requests article bodies on every path that feeds
generation (`scan-by-concept`, `keyword-scan`, `scan-more-event`,
`fetch-by-uri`); only the title scans use 250 characters, deliberately. So
"include the body everywhere" was already true where it matters.

**Exa is not wired into Pulse.** `news.js` has a `scan-exa` mode and `pulse.html`
never calls it (grep finds no caller anywhere in the repo). A live call on
2026-10-05 failed with `Invalid value "undefined" for header "x-api-key"`, so
`EXA_API_KEY` is also not set in Netlify. Nothing was changed for this.

## Why

The only record of which articles a story used was the editor's screen during
generation, so the question "which publishers" had no answer a month later. The
log answers it from real use after a few weeks; until it has data, any ranking
is a guess. A first-sample count from lineup data (54 mentions) is too small
to quote.

Cost: the wire top-up adds at most one EventRegistry call per enriched story
and only when the main search found no wire copy. The non-wire trim (1500
characters, applied to Truths only, only when a wire body of 400+ characters
exists) cuts input tokens on the section that carries the most sources. It
trims non-wire bodies, so a Truths fact that appears only deep in a non-wire
article will be missed; the other three sections still see full bodies.

Ruled out: running the wire search on the concept alone. It returns that
person's whole week of wire stories and some are a different story, so the
keyword is required. Also ruled out: a prompt rewrite. The Truths prompt text is
untouched (docs/voice.md); the wire preference rides in the articles block.

Surprise worth keeping: a server-side mode that nothing calls looks like a
feature in a code read. Confirm a caller exists, and that the key is set,
before assuming a source is feeding the product.

## Check

```sh
set -e
S=$(mktemp -d)
# 1. source log is written and not leaked into reader HTML
mkdir -p $S/ntk-pulse/data $S/digest/data
cp digest/index.html $S/digest/; cp index.html $S/; cp digest/data/backstory.json $S/digest/data/
python3 - "$S" <<'PY'
import json, sys
st = [{"key":"k1","category":"Politics","headline":"Fixture Headline","lede":"l","truth":"<p>t</p>",
       "prob":"<p>p</p>","poss":"<p>q</p>","lies":"<p>x</p>",
       "sources":[{"domain":"fixture-wire-outlet.test","outlet":"Reuters","wire":True,
                   "origin":"er","body_from":"er","body_chars":1800}]}]
json.dump({"stories":st,"today":None}, open(sys.argv[1]+"/ntk-pulse/data/lineup-publish.json","w"))
PY
(cd $S && GITHUB_WORKSPACE=$S python3 "$OLDPWD/ntk-pulse/build_digest.py" ntk-pulse/data/lineup-publish.json >/dev/null 2>&1)
grep -q "fixture-wire-outlet.test" $S/ntk-pulse/data/source-log.jsonl
! grep -rq "fixture-wire-outlet.test" $S/digest $S/index.html
# 2. Truths puts wire first and trims the rest; Lies is untouched
python3 - <<'PY' > $S/t.js
h = open("ntk-pulse/pulse.html").read()
a = h.index("const WIRE_RE"); b = h.index("function toggleSup")
print("const SETTINGS={bodyLen:4000};\n" + h[a:b] + r"""
const L='x'.repeat(3000);
const arts=[{title:'N',source:'NYT',url:'https://www.nytimes.com/a',date:'d',body:L},
            {title:'W',source:'Reuters',url:'https://www.reuters.com/b',date:'d',body:L}];
const t=artsBlock(arts,'truths'), p=artsBlock(arts,'lies');
if(!(t.indexOf('[WIRE] W')<t.indexOf('TITLE: N'))) throw 'wire not first';
if(p.includes('[WIRE]')) throw 'lies was changed';
if(!(t.length<p.length)) throw 'non-wire not trimmed';
""")
PY
node $S/t.js
# 3. proxy supports the wire pool; JS still parses
grep -q "pool === 'wire'" netlify/functions/news.js
node --check netlify/functions/news.js
rm -rf $S
```
