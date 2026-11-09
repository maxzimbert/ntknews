#!/usr/bin/env python3
"""desk.py - the editor's morning page. Gathers what needs attention into one HTML file.

    python3 scripts/desk.py OUT.html        # writes the page, prints a one-line summary

It only reads: the ticket checks (scripts/rot.sh), the publish check (scripts/prepublish.py), the
voice review (scripts/voice_review.py, staging drafts when they are newer than the last publish),
GitHub Actions run history for the bots, open pull requests, and the Backstory link-health file.
It changes nothing, and it calls no paid API. The weekday routine runs it and republishes the page;
see docs/desk.md.
"""
import contextlib
import html
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
NOW = datetime.now(timezone.utc)

# Bots and how stale each may get before the desk says so. GitHub delays scheduled runs on this repo
# by hours (pulse-scan is set to every 20 minutes and ran 5 hours apart on 2026-11-09), so the bar is
# "has it run at all lately", not "is it on time".
BOTS = [('pulse-scan.yml', 'Stream scan', 8), ('pulse.yml', 'Pulse refresh', 8),
        ('newscast.yml', 'Newscast', 30), ('rot.yml', 'Ticket checks', 30)]
OLD_PR_DAYS = 14
LINKS_STALE_DAYS = 7


def sh(cmd, **kw):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, shell=isinstance(cmd, str), **kw)
    return r.stdout, r.returncode


def age(ts):
    if not ts:
        return None
    t = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (NOW - t).total_seconds() / 3600


def ago(hours):
    if hours is None:
        return 'never'
    if hours < 1:
        return '%d min ago' % (hours * 60)
    if hours < 48:
        return '%d h ago' % hours
    return '%d days ago' % (hours / 24)


# --- gather ----------------------------------------------------------------------------------------

def tickets():
    out, _ = sh(['bash', 'scripts/rot.sh'])
    rows, cur = [], None
    for line in out.splitlines():
        m = re.match(r'^(STALE|READY|OPEN|MANUAL|ANCHOR|ERR)\s+(T-\d+)\s+(.*)$', line)
        if m:
            cur = {'kind': m.group(1), 'id': m.group(2), 'text': m.group(3).replace(' — check passes, promote to VERIFIED', ''), 'why': []}
            rows.append(cur)
        elif cur and line.startswith('            ') and cur['kind'] == 'STALE':
            cur['why'].append(line.strip())
        elif not line.startswith(' '):
            cur = None
    summary = next((l for l in out.splitlines() if l.startswith('ok ')), '')
    return rows, summary


def prepublish():
    out, code = sh(['python3', 'scripts/prepublish.py'])
    blockers, warns, sect = [], [], None
    for line in out.splitlines():
        s = line.strip()
        if s.lower().startswith('blocker'):
            sect = blockers
        elif s.lower().startswith('warning'):
            sect = warns
        elif s.startswith('- ') and sect is not None:
            sect.append(s[2:])
        elif not s:
            sect = None
    return blockers, warns


def last_publish():
    out, _ = sh(['git', 'log', '-1', '--format=%cI', '--grep=^publish:', 'origin/main'])
    return out.strip() or None


def voice(pub_ts):
    import voice_review as vr
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            vr.staging(False)
        except SystemExit:
            pass
    gen = vr.staging_meta.get('generated')
    if gen and (not pub_ts or age(gen) < age(pub_ts)):
        return {'mode': 'staging', 'generated': gen, 'rules': vr.staging_meta.get('rules'),
                'stories': vr.staging_results}
    # The live edition is newer than staging's draft: review that instead.
    vr.findings.clear(); vr.long_heads.clear()
    saved = sys.argv
    sys.argv = ['voice_review.py']
    with contextlib.redirect_stdout(io.StringIO()):
        vr.main()
    sys.argv = saved
    return {'mode': 'live', 'generated': pub_ts,
            'findings': [dict(zip(('surface', 'where', 'rule', 'quote', 'source'), f)) for f in vr.findings]}


def bots():
    rows = []
    for wf, name, max_h in BOTS:
        out, code = sh(['gh', 'run', 'list', '--workflow', wf, '-L', '1', '--json', 'conclusion,createdAt,status,url'])
        try:
            r = json.loads(out)[0]
        except (ValueError, IndexError):
            rows.append({'name': name, 'state': 'unknown', 'note': 'could not read run history (gh)', 'url': None})
            continue
        h = age(r['createdAt'])
        bad = r.get('conclusion') not in ('success', None, '') or h > max_h
        note = '%s, %s' % (ago(h), r.get('conclusion') or r.get('status'))
        rows.append({'name': name, 'state': 'bad' if bad else 'ok', 'note': note, 'url': r.get('url')})
    return rows


def prs():
    out, _ = sh(['gh', 'pr', 'list', '--state', 'open', '--json', 'number,title,updatedAt,url,isDraft'])
    try:
        items = json.loads(out)
    except ValueError:
        return None
    for p in items:
        p['days'] = (age(p['updatedAt']) or 0) / 24
    return sorted(items, key=lambda p: p['days'])


def links():
    f = ROOT / 'editorial' / 'object-links-health.json'
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return None
    counts, dead, newest = {}, [], None
    for url, v in d.items():
        counts[v.get('status', '?')] = counts.get(v.get('status', '?'), 0) + 1
        if v.get('status') == 'dead':
            dead.append(url)
        c = v.get('checked')
        if c and (newest is None or c > newest):
            newest = c
    return {'counts': counts, 'dead': dead, 'checked': newest, 'days': (age(newest) or 0) / 24}


# --- render ----------------------------------------------------------------------------------------

def e(s):
    return html.escape(str(s if s is not None else ''))


CSS = """
:root{--ink:#261F23;--ink-2:#30282D;--line:rgba(242,234,226,.12);--fg:#F2EAE2;--mute:rgba(242,234,226,.62);
--amber:#F2AE2E;--terra:#DC6550;--teal:#01B2A7;--blue:#0798F2;
--serif:'Newsreader',Georgia,serif;--sans:'Overpass',system-ui,sans-serif;color-scheme:dark}
/* One column, the most urgent band first; each band is a list the editor clears. */
body{background:var(--ink);color:var(--fg);font:16px/1.5 var(--sans)}
.wrap{max-width:760px;margin:0 auto;padding-block:34px 60px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.date{font:600 13px var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--amber)}
h1{font:500 46px/1.05 var(--serif);margin:6px 0 10px;text-wrap:balance}
.lede{font:400 20px/1.4 var(--serif);color:var(--mute);margin:0 0 34px}
section{border-top:1px solid var(--line);padding-block:20px}
h2{font:600 20px var(--serif);margin:0 0 4px;display:flex;gap:10px;align-items:baseline}
h2 .n{font:600 13px var(--sans);color:var(--mute)}
.sub{color:var(--mute);font-size:13px;margin:0 0 13px}
ul{list-style:none;margin:0;padding:0;display:grid;gap:10px}
li{display:grid;grid-template-columns:auto 1fr;gap:10px;align-items:start;min-width:0}
.pill{font:700 10px var(--sans);letter-spacing:.1em;text-transform:uppercase;padding:3px 8px;border-radius:999px;white-space:nowrap;margin-top:3px}
.bad{background:var(--terra);color:var(--ink)} .warn{background:var(--amber);color:var(--ink)}
.ok{background:var(--teal);color:var(--ink)} .info{background:var(--line);color:var(--fg)}
.t{min-width:0;overflow-wrap:anywhere} .t b{font-weight:600}
.q{display:block;font:italic 16px/1.4 var(--serif);color:var(--mute);margin-top:3px}
.why{display:block;font:13px/1.4 ui-monospace,Menlo,monospace;color:var(--mute);margin-top:3px}
a{color:var(--blue)} a:focus-visible{outline:2px solid var(--amber);outline-offset:2px}
.empty{color:var(--mute);font-style:italic;font-family:var(--serif)}
details summary{cursor:pointer;color:var(--mute);font-size:13px;margin-top:10px}
.end{text-align:center;font:400 20px var(--serif);color:var(--mute);margin-top:34px}
@media (max-width:480px){h1{font-size:34px}}
"""


def item(pill, cls, body):
    return '<li><span class="pill %s">%s</span><span class="t">%s</span></li>' % (cls, e(pill), body)


def section(title, n, sub, items, empty):
    inner = '<ul>%s</ul>' % ''.join(items) if items else '<p class="empty">%s</p>' % e(empty)
    return '<section><h2>%s<span class="n">%s</span></h2>%s%s</section>' % (
        e(title), e(n) if n is not None else '', '<p class="sub">%s</p>' % sub if sub else '', inner)


def render(t_rows, t_sum, blockers, warns, v, bot_rows, pr_rows, lk, pub_ts):
    stale = [r for r in t_rows if r['kind'] in ('STALE', 'ANCHOR', 'ERR')]
    ready = [r for r in t_rows if r['kind'] == 'READY']
    manual = [r for r in t_rows if r['kind'] == 'MANUAL']
    bad_bots = [b for b in bot_rows if b['state'] != 'ok']

    if v['mode'] == 'staging':
        vf = [(s['headline'], f) for s in v['stories'] for f in s['findings'] if not f[3]]
        directed = sum(1 for s in v['stories'] for f in s['findings'] if f[3])
    else:
        vf = v['findings']
        directed = 0

    urgent = len(stale) + len(blockers) + len(bad_bots) + (1 if v.get('rules') in ('changed', 'missing') else 0)
    head = ('Nothing is broken.' if not urgent else
            '%d thing%s broken.' % (urgent, '' if urgent == 1 else 's'))
    lede = '%d voice finding%s, %d ticket%s ready to promote. Last publish %s.' % (
        len(vf), '' if len(vf) == 1 else 's', len(ready), '' if len(ready) == 1 else 's', ago(age(pub_ts)))

    # Broken
    items = []
    for r in stale:
        why = ''.join('<span class="why">%s</span>' % e(w) for w in r['why'][:3])
        items.append(item('stale', 'bad', '<b>%s</b> %s%s' % (e(r['id']), e(r['text']), why)))
    for b in blockers:
        items.append(item('blocker', 'bad', e(b)))
    for b in bad_bots:
        link = ' <a href="%s">run</a>' % e(b['url']) if b['url'] else ''
        items.append(item('bot', 'bad', '<b>%s</b> %s%s' % (e(b['name']), e(b['note']), link)))
    if v.get('rules') == 'changed':
        items.append(item('rules', 'warn', 'Backstory rules (BSX_RULES) changed on staging; the voice counts may be stale until <code>scripts/voice_review.py</code> is updated.'))
    broken = section('Broken', len(items) or None, 'A ticket that stopped being true, a publish blocker, or a bot that failed.', items, 'Nothing.')

    # Voice
    items = []
    if v['mode'] == 'staging':
        sub = 'Composed Backstory drafts on staging, generated %s. Counted against BSX_RULES; parts you directed are skipped%s.' % (
            ago(age(v['generated'])), ' (%d)' % directed if directed else '')
        for head_, f in vf:
            q = '<span class="q">“%s”</span>' % e(f[2]) if f[2] else ''
            items.append(item(f[0], 'warn', '%s <span class="why">%s</span>%s' % (e(f[1]), e(head_[:70]), q)))
    else:
        sub = 'The live edition (published %s), against docs/voice.md.' % ago(age(v['generated']))
        for f in vf:
            q = '<span class="q">“%s”</span>' % e(f['quote']) if f['quote'] else ''
            items.append(item(f['surface'], 'warn', '%s <span class="why">%s</span>%s' % (e(f['rule']), e(f['where']), q)))
    sub += ' The script counts; for the reading pass, say “voice review” in a session.'
    voice_s = section('Voice', len(items) or None, sub, items, 'No rule breaks the script can count.')

    # Ready
    items = [item(r['id'], 'ok', e(r['text'])) for r in ready]
    ready_s = section('Ready to promote', len(items) or None,
                      'Checks pass. Read the ticket for anything its check does not cover, then say “promote T-00xx”.',
                      items, 'None.')

    # Warnings
    items = [item('warning', 'warn', e(w)) for w in warns]
    warn_s = section('Publish warnings', len(items) or None, 'From prepublish on the live edition. Your call, not the script’s.', items, 'None.')

    # PRs
    if pr_rows is None:
        pr_s = section('Open pull requests', None, '', [], 'Could not read pull requests (gh).')
    else:
        items = []
        for p in pr_rows:
            cls = 'bad' if p['days'] > OLD_PR_DAYS else 'info'
            items.append(item('%d d' % p['days'], cls, '<a href="%s">#%d</a> %s' % (e(p['url']), p['number'], e(p['title']))))
        old = sum(1 for p in pr_rows if p['days'] > OLD_PR_DAYS)
        pr_s = section('Open pull requests', len(items) or None,
                       ('%d untouched for over %d days: merge or close.' % (old, OLD_PR_DAYS)) if old else '', items, 'None open.')

    # Bots, all
    items = [item(b['state'] if b['state'] != 'unknown' else '?', 'ok' if b['state'] == 'ok' else 'bad',
                  '<b>%s</b> %s' % (e(b['name']), e(b['note']))) for b in bot_rows]
    bots_s = section('Pipeline', None, 'Last run of each bot. GitHub delays scheduled runs by hours here; the bar is %d hours.' % BOTS[0][2], items, '')

    # Links
    if lk is None:
        links_s = section('Backstory links', None, '', [], 'No link-health file.')
    else:
        counts = ', '.join('%d %s' % (n, k.replace('_', ' ')) for k, n in sorted(lk['counts'].items(), key=lambda x: -x[1]))
        items = [item('dead', 'bad', '<a href="%s">%s</a>' % (e(u), e(u))) for u in lk['dead'][:10]]
        stale_note = (' Last checked %s, older than %d days: run <code>python3 editorial/check_links.py</code>.' % (ago(lk['days'] * 24), LINKS_STALE_DAYS)
                      if lk['days'] > LINKS_STALE_DAYS else ' Last checked %s.' % ago(lk['days'] * 24))
        links_s = section('Backstory links', None, counts + '.' + stale_note, items, 'No dead links.')

    man = ''.join(item(r['id'], 'info', e(r['text'])) for r in manual)
    man_s = ('<section><h2>Manual checks<span class="n">%d</span></h2><details><summary>Show the checks a script cannot run</summary><ul>%s</ul></details></section>'
             % (len(manual), man)) if manual else ''

    date = NOW.astimezone().strftime('%A, %B %-d')
    return ('<title>NTK Desk</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Overpass:wght@400;600;700&display=swap" rel="stylesheet">'
            '<style>%s</style><div class="wrap"><div class="date">%s · the desk</div><h1>%s</h1><p class="lede">%s</p>%s%s%s%s%s%s%s%s'
            '<p class="sub" style="margin-top:20px">%s · generated %s by scripts/desk.py</p><div class="end">— 30 —</div></div>'
            % (CSS, e(date), e(head), e(lede), broken, voice_s, ready_s, warn_s, pr_s, bots_s, links_s, man_s,
               e(t_sum), e(NOW.astimezone().strftime('%-I:%M %p'))))


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: desk.py OUT.html')
    sh(['git', 'fetch', '-q', 'origin'])
    t_rows, t_sum = tickets()
    blockers, warns = prepublish()
    pub_ts = last_publish()
    v = voice(pub_ts)
    page = render(t_rows, t_sum, blockers, warns, v, bots(), prs(), links(), pub_ts)
    Path(sys.argv[1]).write_text(page, encoding='utf-8')
    stale = sum(1 for r in t_rows if r['kind'] == 'STALE')
    print('desk: %d stale, %d blocker(s), %d ready, voice %s -> %s' % (
        stale, len(blockers), sum(1 for r in t_rows if r['kind'] == 'READY'), v['mode'], sys.argv[1]))


if __name__ == '__main__':
    main()
