---
id: T-0080
title: The landing page leads with what NTK does, and says "News that ends" only once the reader knows what it is
status: BUILT
tags: [editorial, feature]
anchor: index.html
---

## What

`ntknews.org` rebuilt from `ntk-marketing-page-recommendations.md`, with the
editor's calls from 2026-10-08:

- Hero H1 is the concrete proposition, comma version, no em dash: "NTK is the
  news you need, so you can stop reading the news." "News that ends." moves
  below the fold as the brand line, after the reader has seen the product.
- Order: proposition, a real story from this morning (on cream), the method
  (four questions), Jefferson, the promise ("News that ends."), Backstory,
  the editor, `/me`, payoff. A "problem" band ("The news is infinite. Your
  attention isn't.") was in the first draft and cut on the editor's review:
  the problem is universal, the hero already carries it, and a band that
  restates the hero is not doing a job.
- Jefferson sits straight after the method because it answers the question
  the method raises (why these four?). It was section 9 in the first draft.
- The four sections are shown as questions (What's true? ... What's false?)
  and keep the certainty ramp from `docs/design-system.md` §6.
- Lies is sold as a benefit to the reader ("You'll know the truth before
  someone tries the lie on you"), not defined defensively.
- Editor section: "Someone reads the news." and "Just news judgment." Names Yahoo News Digest
  as the human-in-the-loop precedent, at the editor's request.
- `/me` ("Know what you know") is written as an expectation the product has
  to meet. Measured 2026-10-08: `/me` ships the per-subject ladder ("Following
  It" and up, `digest/index.html` ~2694) and not much of the rest; Backstory
  and the Column E theme work are what close the gap.
- Jefferson: the 1807 letter to John Norvell, and why he was sour on the press
  (James Callender, whom he had paid to attack Adams, later turned on him). The
  quote is from the same letter as the four chapters. Wording checked from
  memory against the letter's well-known text, **unverified against Founders
  Online in this session.**

Unchanged on purpose: the `heroStory` block and every DOM id
`build_digest.py` writes to, the embedded base64 images, the type scale, the
dark/cream grounds. Every CTA points at `/digest` (the editor's call; it was
`/digest/latest`, a 301 to `/today`). Only the hero button carries no arrow.

The Backstory section reuses the Beginnings timeline CSS from the Backstory
permalink pages (`.tr` rows) with real rows from the published America Abroad
page, replacing a hand-rolled list.

Two JS display fixes rode along: the dateline's em dash (written by
`build_digest.py`'s `date_label`) renders as a middle dot, and the story card's
category no longer carries a stale "Historical frame," prefix. The em dash is
still in the data. Fixing it at the source in `build_digest.py` is a separate,
smaller change.

## Why

The old hero, "Know what matters. Enjoy it.", had the product's ingredients
and opened on the philosophy before saying what the product does. A
news-avoidant stranger (the Jamie persona) decides in seconds, and "News that
ends" is a line you only appreciate once you know what is ending. Leading with
the brand line made people work before they got the point.

This supersedes T-0018, which deliberately ruled out restructuring ("a design
conversation, not a copy pass"). This is that conversation. T-0018's three
measurable rules (no em dash in visible copy, the story count matching the
locked range, "Truths" not "Truth") are carried into the check below, so the
signal is not lost when that ticket closes.

The real risk in a marketing rewrite at NTK is overclaiming. For a product
whose sections are called Truths and Lies, a landing page that promises
features that don't exist is the first lie a reader catches. That's why `/me`
is framed as a direction and why the editor copy says what the human-in-the-loop
model actually is.

The hero still depends on `build_digest.py`'s regex finding exactly one
`const heroStory = {...};`. If a future edit breaks that match, the publish
logs a WARNING and the landing page silently freezes on an old story. The
check asserts the match and the ids.

Design-system audit 2026-10-08 (computed styles, every text element): all
sizes on the ten-step scale, only the loaded weights, radii 3px and 999px
only, Overpass on chrome only. It found and fixed four things: the method
cards' written copy was Overpass (now Newsreader); the Backstory year and
labels silently rendered in the wrong face because a CSS comment containing
`*/` ended early and the browser dropped the next rule without any error; the
mobile-menu button fell back to Arial; one footer span asked for a weight the
page does not load. **Open, not changed:** the landing page's display type
uses negative letter-spacing (-.015em to -.035em) where design-system §3 says
`0` outside named exceptions, and `digest/index.html` follows the rule. That
is a look the editor has approved, so it is a decision, not a cleanup.

The first draft broke T-0029 twice: arrows on five CTAs (only the primary
keeps one) and a bare "1807" label (an ornament T-0029 removed). `rot.sh`
caught both before commit. Recommendation docs don't know about the design
system, so run T-0029 whenever copy from one lands on a consumer surface.

Not checkable, stated here instead: whether the page persuades. Whether the
Jefferson section delights or digresses is a call for the editor on the deploy
preview.

## Check

```sh
python3 - <<'PY'
import html, re, sys
s = open('index.html', encoding='utf-8').read()
t = re.sub(r'(?is)<(script|style|svg)[^>]*>[\s\S]*?</\1>', '', s)
t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
t = re.sub(r'\s+', ' ', t)

# The proposition leads; the brand line follows.
h1 = re.search(r'(?is)<h1[^>]*>(.*?)</h1>', s)
if not h1: sys.exit('no h1 on the landing page')
h1t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', h1.group(1))))
if 'the news you need, so you can stop reading the news' not in h1t:
    sys.exit('hero h1 no longer leads with the proposition: %r' % h1t)
if 'ends' in h1t.lower():
    sys.exit('"News that ends" has moved back into the hero')
if 'News that ends' not in t:
    sys.exit('"News that ends" is gone from the page')

for q in ["What's true?", "What's probable?", "What's possible?", "What's false?"]:
    if q not in t: sys.exit('method question missing: ' + q)

for href in ['/digest', '/backstory', '/me']:
    if 'href="%s"' % href not in s: sys.exit('no link to ' + href)
for anchor in ['id="backstory"', 'id="me"', 'id="jefferson"', 'id="method"']:
    if anchor not in s: sys.exit('section missing: ' + anchor)
if 'href="/today"' in s: sys.exit('a CTA still points at /today; the editor chose /digest')
if 'The news is infinite' in t: sys.exit('the cut problem band is back')
# Order: story, method, origin, then the brand line.
pos = [s.index(m) for m in ['id="story"', 'id="method"', 'id="jefferson"', 'class="promise"']]
if pos != sorted(pos): sys.exit('section order changed: story, method, jefferson, promise')

# A stray comment terminator makes the browser drop the next CSS rule silently.
css = re.search(r'<style>([\s\S]*?)</style>', s).group(1)
if '*/' in re.sub(r'/\*[\s\S]*?\*/', '', css): sys.exit('stray */ in landing CSS: the next rule is being dropped')
if not re.search(r"\.fw-card-body\{font-family:'Newsreader'", css): sys.exit('method card copy is not Newsreader')
if not re.search(r"\.bs-tl \.ty\b[^}]*\{[^}]*font-family:'Overpass'", css) and not re.search(r"\.bs-tl \.ty,[^{]*\{font-family:'Overpass'", css) and ".bs-tl .lab, .bs-tl .ty" not in css:
    sys.exit('Backstory timeline years lost their Overpass rule')

# build_digest.py rewrites this block on every publish; one match or it freezes.
n = len(re.findall(r'const heroStory = \{.*?\n\};', s, re.DOTALL))
if n != 1: sys.exit('heroStory block matches %d times; build_digest.py needs exactly 1' % n)
for i in ['heroDateline','heroStoryCount','heroCardHeadline','storyImageHeadline',
          'storyTruth','storyProb','storyPoss','storyLies','storyCategory',
          'storyReadMore','heroImage','storyImage']:
    if s.count('id="%s"' % i) != 1: sys.exit('wired id %s not present exactly once' % i)

# Carried from T-0018.
n = t.count('—')
if n: sys.exit('%d em dash(es) in visible landing copy' % n)
dec = open('docs/decisions.md', encoding='utf-8').read()
m = re.search(r'\*\*The digest must end\.\*\*\s*(\d+)[–-](\d+) cards', dec)
if not m: sys.exit('the locked story-count range is no longer stated in docs/decisions.md')
lo_d, hi_d = int(m.group(1)), int(m.group(2))
claims = re.findall(r'(\d+)\s*(?:[–-]\s*(\d+))?\s*stories', t)
if not claims: sys.exit('the landing page no longer says how many stories a digest carries')
for c in claims:
    lo = int(c[0]); hi = int(c[1]) if c[1] else lo
    if (lo, hi) != (lo_d, hi_d):
        sys.exit('landing claims %s stories; docs/decisions.md locks %d-%d' % (
            '%d-%d' % (lo, hi) if hi != lo else str(lo), lo_d, hi_d))
if re.search(r'>\s*Truth\s*<', s):
    sys.exit('the first section is labeled "Truth" on the landing page and "Truths" in the product')
PY
```
