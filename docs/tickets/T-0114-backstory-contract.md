---
id: T-0114
title: Each story's Backstory is built in Pulse to the contract, reviewed by the editor, and shipped as built
status: BUILT
tags: [backstory, feature]
anchor: ntk-pulse/pulse.html
---

## What

The Backstory rebuilt against the contract agreed 2026-11-02 (`docs/backstory.md`, top section). Built on branch
`T-0114-backstory-contract`, on staging, not on main. Measured on the branch 2026-11-02:

- **Building.** After Generate Jefferson, Pulse builds the story's page from its headline, description and Truths
  (two or three model calls). The composer fills the ten components: row, title, contest, stakes, chart, It starts in,
  milestones, We are here, documents, About text. The row is proposed from the story and never shapes the page.
- **Reviewing.** The editor's screen has three levels of control.
  - *Direct the research* searches, then re-chooses the history. Every research result for the story is listed, vetoed
    ones included, each with *add to page*.
  - *Revise* changes one part by prompt.
  - *Edit words* lets the editor type the text, with no model call.
  - When the editor directs a part, the editor's words win and nothing repairs them.
- **The chart.** It is sought automatically, once per row per day.
- **When the library is thin** (added 2026-11-04, the editor's call). A build that comes back thin, with fewer than 4
  milestones, after the matrix and the editor's Are.na library (T-0115), runs one web search on the gaps it named
  and rebuilds once with what it kept. A subject searched in the last 30 days is not searched again; its finds are
  offered and the page is not rebuilt. The review says it searched and why.
- **The editor's Are.na library** (T-0115, folded in 2026-11-04): Backstory's second tier, after primary documents.
  T-0115's check covers it.
- **The review, 2026-11-04.** "Make it a milestone" on every document that is not one; the card readers see sits
  at the top.
- **No blank revisions** (2026-11-04). A revise that returns an empty part keeps what was there and tells the editor.
  A directed part that comes back blank on a full build is repaired, not shipped empty. Found on staging: a contest
  revised to "Emphasize what the results say about America now" was saved as "".
- **News reports.** Allowed only from the 91 `NTK_SOURCES` outlets, labelled, and only when no primary source will do.
- **Publish.** Each story ships the page built for it if its fingerprint still matches; any other story ships with no
  Backstory. Nothing is chosen at publish: `backstory-draft.yml` and the classifier and origin steps are gone.
- **Readers.** Readers no longer see day counters, the pull quote, the long context or "where it stands now".

Checked with stand-in model replies in a local Pulse and with fixture runs of the Python. **Unverified against a live
publish**: no prod publish has run this code.

## Why

The editor tested the per-story Backstory on staging and judged it had "drifted into a bad place". Their vision is
"the history that demonstrates how the news in the digest came to be the news in the digest", scoped from the story and
with the editor in the loop. The old build had several faults against that:
- The row (category) shaped the page. A Binance hack filed under Gaza became "Gaza's path to blockade".
- Contest and stakes were empty.
- Day counters had stopped earning their place.
- The editor's prompts were quietly "repaired" back to word counts.

So the contract fixes the components and who decides each one. The rest is execution.

Decisions this carries (`docs/decisions.md`, 2026-11-02):
- the contract itself, with counters retired;
- the editor's words win when they direct;
- the loop as built;
- the chart sourcing itself;
- news from approved publishers.

What did not work along the way, worth knowing:
- **Research finds lost to the shortlist.** They had to win a 45-document shortlist against about 440 matrix items, so
  the model mostly never saw them. They are now always offered first.
- **No results list.** The first review screen did not show research results at all; the editor reported it as "you're
  keeping them out".
- **A fingerprint that covered too much.** It included the Lies section and the category record, so a typo fix in Lies,
  or a trend line found for the row, would have silently dropped a built page at publish. It now covers only what the
  page is built from.

Tickets superseded, each marked DISCARDED with the reason and its check left as written:
- T-0109: the all-or-nothing draft.
- T-0113: rows building the page, and counters on conflict pages.
- T-0049, T-0092: counter display.
- T-0046, T-0090: a counter, the publish-time classifier, and the "none filed" chip.
- T-0089 (2026-11-04): reusing an existing category at publish, a step that no longer runs.

What still held in those (row permalinks, the digest reading Backstory, Lineup order, the typed row) is in the check
below.

Cost: a build is two or three Sonnet/Haiku calls; a thin one adds one web search and one rebuild, at most once per
subject in 30 days. A directed research is one web search plus one call, skipped when
the same direction was searched in 30 days unless the editor forces it. A new row's trend line is one web search.

## Check

```sh
python3 - <<'PY' || exit 1
import json, os, re, subprocess, sys, tempfile
bad = []
s = open('ntk-pulse/pulse.html', encoding='utf-8').read()
app = open('digest/index.html', encoding='utf-8').read()
pages = open('editorial/build_backstory_pages.py', encoding='utf-8').read()
pub = open('.github/workflows/pulse-publish.yml', encoding='utf-8').read()
def fn(src, name):
    m = re.search(r'(?m)^(async )?function ' + re.escape(name) + r'\(', src)
    if not m: return ''
    i = m.start(); le = src.index('\n', i); first = src[i:le]
    return first if first.count('{') == first.count('}') and first.rstrip().endswith('}') else src[i:src.index('\n}\n', i) + 2]

# Building: the ten components, from the story; the row never shapes the page
rules = s[s.index('const BSX_RULES'):s.index('};', s.index('const BSX_RULES'))]
for k in ('row', 'title', 'contest', 'stakes', 'starts', 'milestones', 'here', 'about'):
    if not re.search(r'\b' + k + r'\s*:', rules): bad.append('the composer has no rule for ' + k)
if 'rowTitle' in fn(s, 'bsxShortlist').split('ranked=ids.map')[1].split('.filter(')[0].replace('rowTitle, terms', ''):
    bad.append("the shortlist lifts the row's own documents")
if re.search(r'function bsxTerms\([^)]*row', s): bad.append('the history search terms are shaped by the row')
if 'bsxRun([story.key], {build:true})' not in fn(s, 'generateStory'): bad.append('Generate Jefferson does not build the Backstory')
# The editor's direction wins
rv = fn(s, 'bsxRevise')
if 'the note wins' not in rv or 'delete P[comp]' not in rv: bad.append("a revise does not put the editor's note above the rules")
if 'bsxApplyText(' not in fn(s, 'bsxRun') or 'bsxApplyPins(' not in fn(s, 'bsxRun'): bad.append("the editor's typed words or added results do not survive a build")
# The review screen
h = fn(s, 'bsc2Html') + fn(s, 'bsc2Card') + fn(s, 'bsc2ResearchList')
for want, why in (('DIRECT THE RESEARCH', 'no Direct the research'), ('bsc2-words', 'no edit words'), ('bsc2-res-add', 'research results cannot be added to the page')):
    if want not in h: bad.append('review screen: ' + why)
# Thin builds search once; a blank revision is never accepted (2026-11-04)
run = fn(s, 'bsxRun')
if 'c.thin' not in run or 'bsxResearch(story, key, c.title' not in run: bad.append('a thin build does not search on its own')
if 'revise_blank' not in rv or 'bsxBlank(' not in fn(s, 'bsxCompose'): bad.append('a blank revision can be accepted')
# Research results always reach the composer
if 'edits.pool' not in fn(s, 'bsxCompose'): bad.append("the story's own research is not offered to the composer")
# Fingerprint: only what the page is built from
bh = fn(s, 'bsHash')
if re.search(r's\.(prob|poss|lies)\b|cats\.find', bh): bad.append('the fingerprint covers more than headline, description, Truths, row and edits')
# News: only the approved publishers; one list
js = open('netlify/functions/news.js').read()
src_list = re.findall(r"'([^']+)'", re.search(r"NTK_SOURCES\s*=\s*\[([\s\S]*?)\]", js).group(1))
pulse_list = re.findall(r"'([^']+)'", re.search(r"const NTK_PUBLISHERS=\[([^\]]*)\]", s).group(1))
if pulse_list != src_list: bad.append("Pulse's publisher list differs from NTK_SOURCES in news.js")
sys.path.insert(0, 'editorial'); import publishers
if publishers.is_approved('https://www.politico.com/x') or not publishers.is_approved('https://apnews.com/x'): bad.append('the approved-publisher test is wrong')
# Readers: no counters, no retired fields
for src, name in ((app, 'digest/index.html'), (pages, 'build_backstory_pages.py')):
    for w in ('bsrDaysSince', 'bsrFormatDuration', 'render_fire', 'Running for', 'where_now', 'o.quote', 'o.context', '"quote"', '"context"'):
        if w in src: bad.append(f'{name} still has {w}')
# Publish: nothing chosen at publish; each story ships as built
if 'build_pairings' in pub or 'build_origins' in pub: bad.append('publish still chooses Backstory (classifier or origins)')
if os.path.exists('.github/workflows/backstory-draft.yml'): bad.append('the GitHub first draft still exists')
t = tempfile.mkdtemp(); w = lambda n, d: json.dump(d, open(os.path.join(t, n), 'w'))
c2 = lambda x: {'v': 2, 'title': x, 'here': 'Here ' + x, 'beginnings': [], 'case': [], 'notes': ['n']}
w('draft.json', {'stories': [{'story_id': 'a', 'bs_hash': '1', 'composed': c2('A')}, {'story_id': 'b', 'bs_hash': '2', 'composed': c2('B')},
                             {'story_id': 'd', 'bs_hash': '4', 'composed': {'scope': 'old'}}],
                 'ship': {'todays_pairings': [{'story_id': k, 'row': 'gaza'} for k in 'abd'], 'provisional_rows': [],
                          'row_indicators': {'gaza': {'label': 'L'}}}})
w('lineup.json', {'stories': [{'key': 'a', 'bs_hash': '1'}, {'key': 'b', 'bs_hash': 'edited'}, {'key': 'c', 'bs_hash': '3'}, {'key': 'd', 'bs_hash': '4'}]})
def apply(d):
    w('bs.json', {'rows': [{'id': 'gaza', 'stratum': 'fire'}], 'todays_pairings': [{'story_id': 'yesterday'}]})
    subprocess.run(['python3', 'editorial/backstory_draft.py', 'apply'] + sum([[f'--{k}', os.path.join(t, v)] for k, v in
        (('draft', d), ('lineup', 'lineup.json'), ('backstory', 'bs.json'), ('provisional', 'p.json'), ('origins', 'o.json'))], []), capture_output=True)
    return json.load(open(os.path.join(t, 'bs.json')))
bs = apply('draft.json')
if [p['story_id'] for p in bs['todays_pairings']] != ['a']: bad.append('publish did not ship exactly the built, unchanged story: ' + str([p['story_id'] for p in bs['todays_pairings']]))
elif 'notes' in bs['todays_pairings'][0]['composed'] or bs['todays_pairings'][0]['line'] != 'Here A': bad.append('a shipped page carries build bookkeeping, or its line is not We are here')
if (bs['rows'][0].get('indicator') or {}).get('label') != 'L': bad.append("a row's trend line found in Pulse did not reach the row")
if apply('missing.json')['todays_pairings']: bad.append("with no draft, yesterday's pairings stayed")
# Carried from T-0046: every row gets a permalink page; the digest reads Backstory
out = tempfile.mkdtemp()
r = subprocess.run(['python3', '-c', f"import sys; sys.path.insert(0,'editorial'); import build_backstory_pages as b; from pathlib import Path; b.OUT_DIR=Path({out!r}); b.main()"], capture_output=True, text=True)
rows = json.load(open('digest/data/backstory.json'))['rows']
miss = [x['id'] for x in rows if not os.path.exists(os.path.join(out, x['id'], 'index.html'))]
if r.returncode or miss: bad.append(f'the page builder failed or left rows without a page: {miss[:3]} {r.stderr[-200:]}')
if 'backstory.json' not in open('ntk-pulse/build_digest.py').read(): bad.append('the digest does not read backstory.json')
# Carried from T-0090: the Backstory tab is the Lineup, in order, and flags what is not built
lu = fn(s, 'bsrLineupHtml')
if 'LINEUP.map(' not in lu or 'bsrDraftChip(' not in lu or "not built" not in fn(s, 'bsrDraftChip'): bad.append('the Backstory tab is not the Lineup in order, or hides unbuilt stories')
# Carried from T-0113: a typed row resolves to an existing row, or starts one
open(os.path.join(t, 'r.js'), 'w').write("const names=[{id:'ukraine-russia',title:'Ukraine–Russia'},{id:'gaza',title:'Gaza'}];const bsrRowNames=()=>names,newCategory=n=>'NEW:'+n;\n"
    + fn(s, 'bsrRowResolve') + "\nconsole.log([bsrRowResolve('ukraine russia'),bsrRowResolve('GAZA'),bsrRowResolve('Crypto')].join(','))")
if subprocess.run(['node', os.path.join(t, 'r.js')], capture_output=True, text=True).stdout.strip() != 'ukraine-russia,gaza,NEW:Crypto': bad.append('a typed row does not resolve')
# Nothing in Pulse calls a Backstory function that is gone
called = set(re.findall(r'\b((?:bs|cat)\w*)\(', s)); defined = set(re.findall(r'(?:function\s+|(?:const|let|var)\s+)((?:bs|cat)\w*)\s*[(=]', s))
gone = sorted(called - defined - {'bsrCardHtml', 'catch'})   # bsrCardHtml is read from the reader app at run time; catch is a keyword
if gone: bad.append('Pulse calls functions that do not exist: ' + ' '.join(gone))
if bad: print('\n'.join(bad)); sys.exit(1)
PY
```
