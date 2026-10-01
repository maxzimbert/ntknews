#!/usr/bin/env python3
"""
Regenerate digest/data/backstory.json — the file the live app actually fetches.

NOTE: this wrote to digest/v2/data/ until 2026-09-16, which is the inert
pre-routing tree that nothing serves. If a change here appears to have no
effect, check the path before anything else.

Source of truth:
  editorial/backstory-rows.json        — the 14 Lifetimes rows (hand-edited)
  editorial/NTK_Backstory_Object_Matrix.xlsx  — the object case
  FIRE (below)                         — the 7 Still Counting rows

Preserved from the existing backstory.json on every run:
  todays_pairings, and per-row: narrative, instances,
  updated, photo, indicator.as_of / .verified, and any hand-picked objects.

Run from the repo root:  python3 editorial/build_backstory.py
"""
import json, os, sys, collections
from datetime import datetime, timezone

try:
    import openpyxl
except ImportError:
    sys.exit("pip install openpyxl")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROWS_IN = os.path.join(ROOT, 'editorial', 'backstory-rows.json')
MATRIX  = os.path.join(ROOT, 'editorial', 'NTK_Backstory_Object_Matrix.xlsx')
OUT     = os.path.join(ROOT, 'digest', 'data', 'backstory.json')

# ── Still Counting ────────────────────────────────────────────────────
# Edit here. These seven have no start_line by design — the day count is
# the whole statement.
FIRE = [
 ('us-canada-trade','US–Canada trade war','2026-08-22',
  'Whether a trade fight between neighbours is leverage or self-harm.',
  'Both governments withdraw the tariffs imposed since August.'),
 ('us-israel-iran','US–Israel–Iran','2026-02-28',
  'Whether a campaign of strikes is a policy with an end, or a war nobody has named.',
  'A negotiated halt to strikes and retaliation lasting more than ninety days.'),
 ('venezuela','Venezuela, post-Maduro','2026-01-03',
  'Whether a state can be rebuilt by the people who fled it.',
  'A recognised government exercising control with international acceptance.'),
 ('israel-hezbollah','Israel–Hezbollah, Lebanon','2023-10-08',
  'Whether a border can be quiet without a settlement behind it.',
  'A durable withdrawal and ceasefire holding more than one year.'),
 ('gaza','Gaza','2023-10-07',
  'Whether there is a limit force cannot be argued past.',
  'A permanent ceasefire with an agreed administration for the territory.'),
 ('sudan','Sudan civil war','2023-04-15',
  'Whether a country can survive two armies that each believe they are the state.',
  'A signed settlement between the SAF and RSF holding six months.'),
 ('ukraine-russia','Ukraine–Russia','2022-02-24',
  'Whether borders can still be changed by force.',
  'A ceasefire or settlement recognised by both governments.'),
]

# ── Indicators ────────────────────────────────────────────────────────
# T-0047, 2026-09-28/29: checked all 14 against their named source
# (WebSearch/WebFetch, not recall — see the ticket for exact citations
# per row). 13 of 14 confirmed or corrected below; 'power' is left as it
# was and UNVERIFIED — real effort was spent trying to pin a single
# current combined figure for "the other party threatens the nation"
# and it did not resolve to one citable number, so it is not marked
# verified. Two of the 13 (america-abroad's 1970 figure, equality's
# 1983 figure) have a solidly confirmed NOW value but a "then" baseline
# that traces to a commonly-cited figure rather than one pinned primary
# source — noted per-row below, and digest/data/backstory.json's
# verified:true on those two reflects "now value checked," not "every
# number on the row independently re-derived."
IND = {
 # 1988: 351 ppm (NOAA GML Mauna Loa record) — matches as claimed.
 # Now: 427.55 ppm, August 2026, NOAA GML trends page, updated 2026-09-05.
 'climate':       ('Atmospheric carbon dioxide', '351 ppm', '1988', '428 ppm', 'worse', 'NOAA Global Monitoring Laboratory'),
 # 1976: 72% — Gallup's own account: 68% (1972), 69% (1974), 72% (1976,
 # the historical high, post-Watergate/Vietnam reporting). Now: 28%,
 # September 2025 Gallup poll (news.gallup.com/poll/695762) — the 31%
 # this replaces was accurate as of May 2024 and has since fallen further.
 'media':         ('Trust the press a great deal or fair amount', '72%', '1976', '28%', 'worse', 'Gallup'),
 # 1970: 4.7% — matches Census exactly. Now: 14.8%, 2024 (Census's own
 # July 2026 250-year retrospective; 2024 is the record high, 50.2M people).
 'immigration':   ('Foreign-born share of the population', '4.7%', '1970', '14.8%', 'contested', 'U.S. Census Bureau'),
 # 1980: Pew's own account puts the 1980s at "5 to 7%" — 7% sits at the
 # top of that range, kept as-is. Now: 28%, confirmed against Pew's
 # 2023-24 Religious Landscape Study (largest, most recent).
 'faith':         ('Adults with no religious affiliation', '7%', '1980', '28%', 'contested', 'Pew Research Center'),
 # 2019: "about 0" holds — the median line was crossed only twice (1999,
 # 2011) before a March 2019 incident, against decades of tacit
 # adherence; the real pattern-break starts 2020. Now: 3,070 crossings
 # in 2024 (Taiwan MND, via Focus Taiwan/Jamestown reporting) — tightened
 # from "over 3,000" to the actual annual figure.
 'taiwan':        ('PLA aircraft crossing the median line', 'about 0', '2019', '3,070 a year', 'worse', 'Taiwan Ministry of National Defense'),
 # 1958: 73% — matches Pew's own account exactly (first year the
 # question was asked). Now: 17%, per Pew's "Public Trust in Government:
 # 1958-2025" (Dec 2025) — a September 2025 survey. The 22% this
 # replaces was real but stale (May 2024); trust fell further since.
 'government':    ("Trust Washington to do what's right", '73%', '1958', '17%', 'worse', 'Pew Research Center'),
 # 1991: 758.2 (FBI's own cited peak) — matches as claimed. Now: 359.1
 # per 100,000 in 2024 (FBI UCR data, via Axios/OpenCrime reporting;
 # 2024 is a two-decade low) — corrected from 370.
 'order':         ('Violent crime per 100,000 people', '758', '1991', '359', 'better', 'FBI Uniform Crime Reports'),
 # 1970: "about 1 million" is the commonly-cited Vietnam-era figure —
 # corroborated (336k in South Vietnam alone at year-end 1970, plus
 # substantial Cold War Europe deployment) but not pinned to one single
 # DMDC total for that exact year; treat with more caution than the
 # other rows. Now: about 166,000 active-duty overseas as of June 2024
 # (DMDC, via USAFacts/Voronoi reporting) — tightened from 170,000.
 'america-abroad':('U.S. troops stationed abroad', 'about 1 million', '1970', 'about 166,000', 'contested', 'Defense Manpower Data Center'),
 # UNVERIFIED — left exactly as it was. Real research attempted (Pew's
 # partisan-hostility tracking is real and the general magnitude/
 # direction checks out against related Pew metrics from 2022), but no
 # single current figure for this exact "threat to the nation" framing,
 # combined across parties, could be pinned to one citable source. Needs
 # a second pass with more time, not a forced number.
 'power':         ('Say the other party threatens the nation', 'about 20%', '1994', 'about 70%', 'worse', 'Pew Research Center'),
 # 1973: 24% is the commonly-cited figure for that era (BLS's own
 # "comparable" series only starts 1983 at 20.1%; the 1973 figure traces
 # to compiled historical CPS data, not a direct BLS 1973 release) —
 # kept, same caveat as america-abroad's 1970 figure. Now: 10.0% in 2025
 # (BLS, published 2026, "Union membership rate 10.0 percent in 2025")
 # — matches as claimed exactly.
 'work':          ('Share of workers in a union', '24%', '1973', '10%', 'worse', 'Bureau of Labor Statistics'),
 # 1970: Census's own CPS-cited figure is 20.8 (sources range 20.6-21);
 # tightened from 21. Now: 28.4 in 2025 (Census) — tightened from 28.
 'family':        ('Median age at first marriage, women', '20.8', '1970', '28.4', 'contested', 'U.S. Census Bureau'),
 # Now: "$15 for every $100" in 2022 is Institute for Policy Studies'
 # own phrase, applied to SCF data — matches as claimed exactly. 1983:
 # "about $16" is a commonly-cited approximation; different studies
 # compute the 1983 ratio differently depending on definition (a
 # cohort-based Fed study finds ~3x, not ~6x) — same caution as the
 # other two "then" values above, this one kept as-is rather than
 # picking one study's number over another's.
 'equality':      ('Black family wealth per $100 of white family wealth', 'about $16', '1983', 'about $15', 'flat', 'Federal Reserve Survey of Consumer Finances'),
 # 2005: "0" holds — North Korea's first confirmed nuclear test was
 # October 2006. Now: about 60, FAS's early-2026 estimate (up from the
 # 50 this replaces — a real increase, not just a tightened citation).
 'korea':         ('Estimated North Korean nuclear warheads', '0', '2005', 'about 60', 'worse', 'Federation of American Scientists'),
 # 1986: about 70,000 (FAS cites ~70,300) — matches as claimed. Now:
 # about 12,300, FAS's early-2026 "Status of World Nuclear Forces" —
 # tightened from 12,000.
 'bomb':          ('Nuclear warheads worldwide', 'about 70,000', '1986', 'about 12,300', 'better', 'Federation of American Scientists'),
}

PRESERVE_ROW = ('narrative', 'instances', 'updated', 'photo')


def load_objects():
    sh = openpyxl.load_workbook(MATRIX)['Objects']
    by_row = collections.defaultdict(list)
    for i in range(2, sh.max_row + 1):
        g = lambda c: sh.cell(row=i, column=c).value
        if not g(11):
            continue
        by_row[g(11)].append({'title': g(6), 'author': g(7) or '',
                              'year': str(g(4))[:4] if g(4) else '',
                              'source': g(10), '_sort': str(g(4) or '9999')})
    return by_row


def pick(pool):
    """Two deepest pre-1981, two most recent. Falls back if the row is thin."""
    all_o = sorted(pool, key=lambda o: o['_sort'])
    if not all_o:
        return []
    old = [o for o in all_o if o['_sort'][:4] < '1981']
    new = [o for o in all_o if o['_sort'][:4] >= '1981']
    chosen = old[:2] + new[-2:]
    if len(chosen) < 4:
        chosen += [o for o in all_o if o not in chosen][:4 - len(chosen)]
    return [{k: o[k] for k in ('title', 'author', 'year', 'source')}
            for o in sorted(chosen, key=lambda o: o['_sort'])]


def main():
    spec = json.load(open(ROWS_IN))
    objs = load_objects()

    prev, prev_rows = {}, {}
    if os.path.exists(OUT):
        prev = json.load(open(OUT))
        prev_rows = {r['id']: r for r in prev.get('rows', [])}

    out = {
        '_comment': ('LIBRARY of 21 rows plus todays_pairings, the set actually rendered '
                     '(one entry per digest story). GENERATED by '
                     'editorial/build_backstory.py — edit editorial/backstory-rows.json '
                     'and rebuild. Narratives, instances, pairings and verified flags '
                     'ARE preserved across rebuilds.'),
        'version': '2.0',
        'generated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'published': prev.get('published'),
        'rows': [],
        'todays_pairings': prev.get('todays_pairings', []),
    }

    def carry(row, old):
        for k in PRESERVE_ROW:
            if old and k in old:
                row[k] = old[k]
        # hand-picked objects win over the automatic pick
        if old and old.get('objects_locked'):
            row['objects'] = old['objects']
            row['objects_locked'] = True
        if row.get('indicator') and old and old.get('indicator'):
            for k in ('as_of', 'verified'):
                if k in old['indicator']:
                    row['indicator'][k] = old['indicator'][k]
        return row

    for rid, title, start, contest, close in FIRE:
        out['rows'].append(carry({
            'id': rid, 'stratum': 'fire', 'title': title,
            'start_date': start, 'start_line': None,
            'milestone': contest, 'close_condition': close,
            'roots': [], 'subgenres': [], 'updated': False,
            'narrative': [], 'indicator': None,
            'objects': [], 'instances': [], 'photo': None,
        }, prev_rows.get(rid)))

    for r in spec['rows']:
        ind = IND.get(r['id'])
        out['rows'].append(carry({
            'id': r['id'], 'stratum': 'held', 'title': r['title'],
            'start_date': r['start_date'], 'start_line': r['start_line'],
            'milestone': r['contest'], 'close_condition': None,
            'roots': r['roots'], 'subgenres': r['subgenres'],
            'updated': False, 'narrative': [],
            'indicator': ({'label': ind[0], 'then_value': ind[1], 'then_year': ind[2],
                           'now_value': ind[3], 'direction': ind[4], 'source': ind[5],
                           'as_of': None, 'verified': False} if ind else None),
            'objects': pick(objs.get(r['title'], [])),
            'instances': [], 'photo': None,
        }, prev_rows.get(r['id'])))

    out['rows'].sort(key=lambda r: r['start_date'], reverse=True)

    ids = [r['id'] for r in out['rows']]
    dupes = [i for i, c in collections.Counter(ids).items() if c > 1]
    if dupes:
        sys.exit('duplicate row ids: %s' % dupes)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write('\n')

    held = [r for r in out['rows'] if r['stratum'] == 'held']
    written = sum(1 for r in out['rows'] if r['narrative'])
    unver = sum(1 for r in held if r['indicator'] and not r['indicator']['verified'])
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    print('  %d rows (%d fire, %d held)' % (len(out['rows']), len(FIRE), len(held)))
    print('  %d narratives written, %d empty' % (written, len(out['rows']) - written))
    print('  %d indicators UNVERIFIED' % unver)
    print('  %d pairings carried over' % len(out['todays_pairings']))


if __name__ == '__main__':
    main()
