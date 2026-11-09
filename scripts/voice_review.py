#!/usr/bin/env python3
"""voice_review.py - pull one edition's reader-facing copy apart by surface and run the
house-rule checks a script can make without judgment. T-0104.

    python3 scripts/voice_review.py                      # the edition already live
    python3 scripts/voice_review.py ~/Downloads/ntk-stories-2026-11-09.json
    python3 scripts/voice_review.py --text               # also print every passage, numbered

Reads ntk-pulse/data/lineup-publish.json (or the file given, which is what Pulse's
"download story data" saves) for /today and /digest, and digest/data/backstory.json plus the
edition's backstory_categories for /backstory.

It reports and never rewrites. Every finding names the surface, the place, the quoted text and
the rule in docs/voice.md it breaks. The reading-level numbers are a Flesch-Kincaid estimate
with a crude syllable count: a signal for the reader of this report, not a verdict.

Exit status is always 0. This is a review for the editor, not a gate; prepublish.py is the gate.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINEUP = ROOT / 'ntk-pulse' / 'data' / 'lineup-publish.json'
BACKSTORY = ROOT / 'digest' / 'data' / 'backstory.json'

SECTIONS = [('truth', 'Truths'), ('prob', 'Probabilities'), ('poss', 'Possibilities'), ('lies', 'Lies')]

# Per-surface ceilings, docs/decisions.md 2026-10-09: /today middle school, /digest high school,
# /backstory AP. AP has no ceiling worth enforcing, so Backstory's number is reported only.
CEILING = {'today': 8.0, 'digest': 12.0, 'backstory': None}
LEVEL_NAME = {'today': 'middle school (grade 8 ceiling)', 'digest': 'high school (grade 12 ceiling)',
              'backstory': 'AP (no ceiling, reported only)'}

# docs/voice.md section 5, VOICE_REF: the banned signpost verbs.
SIGNPOST = ['underscores', 'underscored', 'underscore', 'highlights', 'highlighted', 'demonstrates',
            'demonstrated', 'reveals', 'revealed', 'showcases', 'showcased', 'reflects', 'reflected',
            'signals', 'signaled', 'signalled', 'represents', 'speaks to', 'spoke to', 'illustrates',
            'illustrated', 'emphasizes', 'emphasized', 'spotlights', 'spotlighted', 'exemplifies',
            'exemplified']
# docs/voice.md section 1 (Register 1 failure modes) and section 3 (cut the hedge-phrase).
SPLAINER = [r"\blet'?s break (it|this) down\b", r"\bhere'?s the thing\b", r"\bin a nutshell\b",
            r"\bsimply put\b", r"\bbreaking it down\b", r"\bhere'?s what you need to know\b"]
HEDGE = [r'\bamid (growing )?concerns? (about|over)\b', r'\bin a move that\b', r'\bfor (unspecified|various|undisclosed) reasons\b']

findings = []
long_heads = []   # one finding per edition, not one per story: see SKILL.md


def find(surface, where, rule, quote, source):
    findings.append((surface, where, rule, quote, source))


def clean(t):
    t = re.sub(r'\(\s*<a [^>]*>[^<]*</a>\s*\)', '', t or '')      # ([Source](url)) citations
    t = re.sub(r'\[STORY:[^\]]*\]', '', t)
    t = re.sub(r'\[(PULLQUOTE|STAT):[^\]]*\]', '', t)
    t = re.sub(r'\[(HEADLINE|LEDE|SUBHEAD)\]', '', t)
    t = re.sub(r'</p>|<br\s*/?>', '\n\n', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = t.replace('**', '')
    t = html.unescape(t)
    return re.sub(r'[ \t]+', ' ', t).strip()


def paragraphs(t):
    return [p.strip() for p in re.split(r'\n\s*\n', clean(t)) if p.strip()]


def snip(s, at=None, width=90):
    if at is None:
        return s if len(s) <= width else s[:width - 1] + '…'
    a = max(0, at - width // 2)
    out = s[a:a + width]
    return ('…' if a else '') + out + ('…' if a + width < len(s) else '')


def syllables(w):
    w = w.lower()
    w = re.sub(r'[^a-z]', '', w)
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r'(?:[^laeiouy]es|ed|[^laeiouy]e)$', '', w)
    w = re.sub(r'^y', '', w)
    return max(1, len(re.findall(r'[aeiouy]{1,2}', w)))


def fk_grade(text):
    sents = [s for s in re.split(r'(?<=[.!?])\s+', text) if re.search(r'[A-Za-z]', s)]
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", text)
    if len(words) < 30 or not sents:
        return None
    syl = sum(syllables(w) for w in words)
    return 0.39 * len(words) / len(sents) + 11.8 * syl / len(words) - 15.59


def check_passage(surface, where, text):
    """The rules every surface shares."""
    for m in re.finditer('—|–(?=\s)|\s--\s', text):
        find(surface, where, 'em dash (hard rule)', snip(text, m.start()), 'voice.md §5 GLOBAL, VOICE_REF')
    low = text.lower()
    for v in SIGNPOST:
        for m in re.finditer(r'\b' + re.escape(v) + r'\b', low):
            find(surface, where, 'banned signpost verb "%s": find the actor' % v, snip(text, m.start()),
                 'voice.md §5 VOICE_REF')
    for pat in SPLAINER:
        for m in re.finditer(pat, low):
            find(surface, where, 'Explainer-Splainer phrasing', snip(text, m.start()), 'voice.md §1 Register 1')
    for pat in HEDGE:
        for m in re.finditer(pat, low):
            find(surface, where, 'hedge-phrase: name the thing being hedged', snip(text, m.start()),
                 'voice.md §3 move 3')


def check_headline(where, h):
    h = clean(h)
    if len(h) > 90:
        long_heads.append((where, len(h)))
    m = re.search(r'\b(1[6-9]|20)\d\d\b', h)
    if m:
        find('digest', where, 'year in a headline: no years as anchors (check it is not doing the anchoring)',
             snip(h), 'voice.md §1 civilian anchor, §3')
    if '?' in h:
        find('digest', where, 'rhetorical question in a headline', snip(h), 'voice.md §3 guardrail')


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    show_text = '--text' in sys.argv
    path = Path(args[0]).expanduser() if args else LINEUP
    d = load(path)
    if d is None:
        sys.exit('no such file: %s' % path)
    stories = d.get('stories', d if isinstance(d, list) else [])
    today = d.get('today') if isinstance(d, dict) else None
    cats = d.get('backstory_categories', []) if isinstance(d, dict) else []
    bs = load(BACKSTORY) or {}

    corpus = {'today': [], 'digest': [], 'backstory': []}   # (where, paragraph)

    # /today
    if today and today.get('text'):
        raw = today['text']
        for i, p in enumerate(paragraphs(raw), 1):
            corpus['today'].append(('Today ¶%d' % i, p))
        order = re.findall(r'\[STORY:\s*([0-9a-f]+)', raw)
        digest_order = [s.get('key') for s in stories]
        seen = [k for k in digest_order if k in order]
        if order != seen:
            find('today', 'Today', 'overview mentions stories out of Digest order (story 1 is the lead)',
                 'Today: %s / Digest: %s' % (', '.join(o[:6] for o in order), ', '.join(k[:6] for k in seen)),
                 'voice.md §5 Today')
        unknown = [k for k in order if k not in digest_order]
        if unknown:
            find('today', 'Today', 'overview points at a story not in the Digest', ', '.join(unknown),
                 'voice.md §5 Today')
    else:
        find('today', 'Today', 'no Today overview in this file', '', '')

    # /digest
    if not stories:
        find('digest', 'Digest', 'this file has no stories: nothing on /digest to review', '', '')
    for n, s in enumerate(stories, 1):
        tag = 'story %d "%s"' % (n, snip(clean(s.get('headline', '')), width=48))
        check_headline(tag + ' headline', s.get('headline', ''))
        corpus['digest'].append((tag + ' headline', clean(s.get('headline', ''))))
        if s.get('lede'):
            corpus['digest'].append((tag + ' lede', clean(s['lede'])))
        for key, name in SECTIONS:
            for i, p in enumerate(paragraphs(s.get(key, '')), 1):
                corpus['digest'].append(('%s %s ¶%d' % (tag, name, i), p))

    if long_heads:
        find('digest', '%d of %d headlines' % (len(long_heads), len(stories)),
             'headline over 90 characters (the punch-up prompt and triage.py still say under 90)',
             ', '.join('%s: %d' % (w.split('"')[0].strip(), n) for w, n in long_heads), 'voice.md §3, §4')

    # /backstory: the edition's categories, then today's pairings and the rows they open.
    for c in cats:
        tag = 'category "%s"' % c.get('title', c.get('id'))
        for f in ('contest', 'stakes'):
            if c.get(f):
                corpus['backstory'].append(('%s %s' % (tag, f), clean(c[f])))
        for o in c.get('objects', []):
            if o.get('about'):
                corpus['backstory'].append(('%s object %s' % (tag, o.get('object_id', '?')), clean(o['about'])))
        for b in c.get('beginnings', []):
            if b.get('line'):
                corpus['backstory'].append(('%s Beginning %s' % (tag, b.get('object_id', '?')), clean(b['line'])))
    rows = {r.get('id'): r for r in bs.get('rows', [])}
    keys = {s.get('key') for s in stories}
    paired = []
    for p in bs.get('todays_pairings', []):
        if p.get('story_id') not in keys:
            continue
        paired.append(p.get('row'))
        if p.get('line'):
            corpus['backstory'].append(('pairing line for "%s"' % snip(p.get('headline', ''), width=40), clean(p['line'])))
    if stories and not any(p.get('story_id') in keys for p in bs.get('todays_pairings', [])):
        find('backstory', 'backstory.json', "today's pairings are for a different edition; the row text below is the library, not this edition",
             'backstory.json generated %s' % bs.get('generated'), '')
    for rid in dict.fromkeys(paired):
        r = rows.get(rid)
        if not r:
            continue
        tag = 'row "%s"' % r.get('title', rid)
        for f in ('milestone', 'stakes', 'start_line'):
            if r.get(f):
                corpus['backstory'].append(('%s %s' % (tag, f), clean(r[f])))
        for i, para in enumerate(r.get('narrative') or [], 1):
            text = para if isinstance(para, str) else para.get('text', '')
            corpus['backstory'].append(('%s narrative ¶%d' % (tag, i), clean(text)))
        for b in r.get('beginnings') or []:
            if b.get('line'):
                corpus['backstory'].append(('%s Beginning %s' % (tag, b.get('year', '?')), clean(b['line'])))

    for surface, items in corpus.items():
        for where, text in items:
            check_passage(surface, where, text)

    # Report.
    print('voice review of %s' % path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    print('rules: docs/voice.md · levels: docs/decisions.md 2026-10-09\n')
    print('READING LEVEL (Flesch-Kincaid estimate)')
    for surface, items in corpus.items():
        g = fk_grade(' '.join(t for _, t in items))
        cap = CEILING[surface]
        verdict = '' if g is None or cap is None else ('  OVER' if g > cap else '  ok')
        print('  /%-10s %-6s %s%s' % (surface, '–' if g is None else '%.1f' % g, LEVEL_NAME[surface], verdict))
        if cap is not None:
            worst = sorted(((fk_grade(t), w) for w, t in items if fk_grade(t) is not None), reverse=True)
            for gg, w in worst[:3]:
                if gg > cap + 2:
                    print('      hardest: %.1f  %s' % (gg, w))
    print()
    print('MECHANICAL FINDINGS (%d)' % len(findings))
    for surface in ('today', 'digest', 'backstory'):
        mine = [f for f in findings if f[0] == surface]
        if not mine:
            print('  /%s: none' % surface)
            continue
        print('  /%s:' % surface)
        for _, where, rule, quote, source in mine:
            print('    - %s\n      rule: %s%s' % (where, rule, '  [%s]' % source if source else ''))
            if quote:
                print('      "%s"' % quote)
    print()
    print('NOT CHECKED HERE, needs a reader: the civilian anchor, numbers without units, the cynic test,')
    print('the cross-section boundary, Lies naming who makes the claim, Probabilities stated with conviction,')
    print('Register 1 failure modes beyond stock phrases, and whether Today excludes Lies.')

    if show_text:
        print('\nTEXT')
        for surface, items in corpus.items():
            print('\n=== /%s ===' % surface)
            for where, text in items:
                print('\n[%s]\n%s' % (where, text))


if __name__ == '__main__':
    main()
