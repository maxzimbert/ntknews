#!/usr/bin/env python3
"""measure-output.py - what the last Generate Jefferson actually produced.

    python3 scripts/measure-output.py

Reads ntk-pulse/data/lineup-publish.json and reports the two things the
2026-09-17 em-dash decision and the 2026-09-18 Strunk work said to measure
rather than assume: how many em dashes survived, and whether the prose still
varies its sentence length.

The published sections are HTML, not markdown. An earlier pass at this
measured markdown and counted <a href="..."> blobs as words, which inflated
one sentence to 137 words and made the rhythm numbers meaningless. Strip the
tags first.

Baseline, measured 2026-09-18 on the pre-rule digest: 34 em dashes, 31
sections, 6% with a run of 3+ short sentences, median stdev 13.1, median
sentence 22.9 words.
"""
import html
import json
import re
import statistics
import sys

SECTIONS = ['truth', 'prob', 'poss', 'lies']


def clean(t):
    t = re.sub(r'\([^()]*<a [^>]*>[^<]*</a>[^()]*\)', '', t)   # parenthetical citations
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()


def short_run(lens):
    run = best = 0
    for n in lens:
        run = run + 1 if n < 9 else 0
        best = max(best, run)
    return best


def main():
    d = json.load(open('ntk-pulse/data/lineup-publish.json'))
    stories = d.get('stories', [])

    dashes = sum((s.get(f) or '').count('—')
                 for s in stories for f in ['headline', 'lede'] + SECTIONS)
    dashes += ((d.get('today') or {}).get('text') or '').count('—')

    rows = []
    for s in stories:
        for f in SECTIONS:
            lens = [len(x.split()) for x in
                    re.split(r'(?<=[.!?])\s+', clean(s.get(f) or '')) if x.strip()]
            if len(lens) < 6:
                continue
            rows.append((short_run(lens), statistics.pstdev(lens),
                         sum(lens) / len(lens), f, (s.get('headline') or '')[:40]))

    if not rows:
        sys.exit('no sections long enough to measure')

    runs = [r[0] for r in rows]
    flat = [r for r in rows if r[0] >= 3]

    print('\n%d stories, %d sections measured\n' % (len(stories), len(rows)))
    print('  em dashes in published output       %d   (threshold 3, see T-0004)' % dashes)
    print('  sections with 3+ short sentences    %d of %d  (%d%%, baseline 6%%)'
          % (len(flat), len(rows), 100 * len(flat) // len(rows)))
    print('  median sentence-length stdev        %.1f   (baseline 13.1, lower is flatter)'
          % statistics.median([r[1] for r in rows]))
    print('  median sentence length              %.1f words  (baseline 22.9)'
          % statistics.median([r[2] for r in rows]))

    if flat:
        print('\n  flattest sections:')
        for r in sorted(flat, reverse=True)[:6]:
            print('    run %d  stdev %4.1f  %-6s %s' % (r[0], r[1], r[3], r[4]))
    print()


if __name__ == '__main__':
    main()
