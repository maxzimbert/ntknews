#!/usr/bin/env python3
"""prepublish.py - everything worth checking about an edition before it ships.

    python3 scripts/prepublish.py                      # the last published edition
    python3 scripts/prepublish.py ~/Downloads/ntk-stories-2026-09-18.json

With no argument it reads ntk-pulse/data/lineup-publish.json, which is the
edition already live. To check one BEFORE it goes out, click "download story
data" in Pulse and pass that file: it is byte-identical to what publish sends.

Exit 1 if any BLOCKER fired. Warnings never fail the run; they are for the
editor to look at, not for a script to veto.

Scope, deliberately: this counts and it resolves. It cannot tell you whether a
lede lands, and a version that pretended to would be worse than none, because
it would be trusted. See docs/tickets/T-0008.
"""
import html
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / 'ntk-pulse' / 'data' / 'lineup-publish.json'
SECTIONS = ['truth', 'prob', 'poss', 'lies']
INSUFFICIENT = 'INSUFFICIENT SOURCE MATERIAL'

blockers, warnings = [], []
def block(m): blockers.append(m)
def warn(m):  warnings.append(m)


def locked_range():
    m = re.search(r'\*\*The digest must end\.\*\*\s*(\d+)[–-](\d+) cards',
                  (ROOT / 'docs' / 'decisions.md').read_text(encoding='utf-8'))
    if not m:
        warn('docs/decisions.md no longer states the story-count range; skipping that check')
        return None
    return int(m.group(1)), int(m.group(2))


def clean(t):
    t = re.sub(r'\([^()]*<a [^>]*>[^<]*</a>[^()]*\)', '', t or '')
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()


def label(s):
    return (s.get('headline') or '').strip()[:52] or ('story ' + str(s.get('key', '?')))


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.exists():
        sys.exit('no such file: %s' % path)
    d = json.loads(path.read_text(encoding='utf-8'))
    stories = d.get('stories', d if isinstance(d, list) else [])
    today = d.get('today') if isinstance(d, dict) else None
    print('\nprepublish - %s\n%d stor%s\n' % (path, len(stories), 'y' if len(stories) == 1 else 'ies'))

    # ── Blockers: nothing downstream can build from these (T-0022) ──────────
    for s in stories:
        if not (s.get('headline') or '').strip():
            block('%s (%s) has no headline; build_digest.py will skip it'
                  % (s.get('key', '?'), s.get('category', 'no category')))
        if not (s.get('lede') or '').strip():
            block('%s has no lede; the card and the og:description will be empty' % label(s))

    # ── Story count against the locked range (T-0023) ───────────────────────
    rng = locked_range()
    live = [s for s in stories if (s.get('headline') or '').strip()]
    if rng and not (rng[0] <= len(live) <= rng[1]):
        warn('%d stories would publish; docs/decisions.md says %d-%d' % (len(live), rng[0], rng[1]))

    # ── Per story: refusals, images, attribution ────────────────────────────
    for s in stories:
        secs = [(s.get(f) or '') for f in SECTIONS]
        if secs and all(INSUFFICIENT in x for x in secs):
            block('%s: every section is [%s]' % (label(s), INSUFFICIENT))
        elif any(INSUFFICIENT in x for x in secs):
            warn('%s: %d of 4 sections are [%s]'
                 % (label(s), sum(1 for x in secs if INSUFFICIENT in x), INSUFFICIENT))
        if not s.get('featuredImage'):
            warn('%s: no image' % label(s))
        # Truths only. Measured across the 2026-09-17 and 2026-09-18 editions:
        # Truths carried a citation in 12 of 12 sections, while Probabilities,
        # Possibilities and Lies went uncited in 8, 9 and 5 of 12. Those three
        # argue from the sourced facts rather than re-citing them, so flagging
        # them would fire on the normal case, and a warning that fires on the
        # normal case is one nobody reads.
        if (s.get('truth') or '') and '<a ' not in (s.get('truth') or ''):
            warn('%s: the Truths section cites no source' % label(s))

    # ── Em dashes (T-0004) and rhythm (T-0019) ──────────────────────────────
    dash = sum((s.get(f) or '').count('—') for s in stories
               for f in ['headline', 'lede'] + SECTIONS)
    dash += ((today or {}).get('text') or '').count('—')
    if dash > 3:
        block('%d em dashes in the edition (T-0004 threshold is 3)' % dash)
    elif dash:
        warn('%d em dash(es) in the edition' % dash)

    rows = []
    for s in stories:
        for f in SECTIONS:
            lens = [len(x.split()) for x in re.split(r'(?<=[.!?])\s+', clean(s.get(f))) if x.strip()]
            if len(lens) < 6:
                continue
            run = best = 0
            for n in lens:
                run = run + 1 if n < 9 else 0
                best = max(best, run)
            rows.append((best, statistics.pstdev(lens)))
    if len(rows) >= 10:
        flat = 100 * sum(1 for r in rows if r[0] >= 3) / len(rows)
        sd = statistics.median([r[1] for r in rows])
        print('  rhythm: %d%% of sections flat (baseline 6%%), median stdev %.1f (baseline 13.1)'
              % (flat, sd))
        if flat > 20:
            warn('%d%% of sections run 3+ short sentences in a row' % flat)
        if sd < 8:
            warn('median sentence-length stdev %.1f; the prose has gone flat' % sd)

    # ── Today overview: present, and its onramps resolve (T-0001) ───────────
    if not (today or {}).get('text'):
        warn('no Today overview in this payload')
    else:
        keys = {s.get('key') for s in stories}
        dead = [r.split('|')[0].strip()
                for r in re.findall(r'\[STORY:\s*([^\]]+)\]', today['text'])
                if r.split('|')[0].strip() not in keys]
        if dead:
            block('Today overview has %d onramp(s) pointing at no story: %s' % (len(dead), dead))
        if not today.get('generatedAt'):
            warn('the Today overview has no generatedAt, so its freshness cannot be judged')

    # ── Report ──────────────────────────────────────────────────────────────
    for name, items in (('BLOCKER', blockers), ('warning', warnings)):
        if items:
            print('\n%s%s' % (name, '' if len(items) == 1 else 's'))
            for i in items:
                print('  - %s' % i)
    if not blockers and not warnings:
        print('  nothing to flag.')
    print('\n%d blocker(s), %d warning(s). Taste is not checked here; read it yourself.\n'
          % (len(blockers), len(warnings)))
    return 1 if blockers else 0


if __name__ == '__main__':
    sys.exit(main())
