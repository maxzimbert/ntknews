---
id: T-0109
title: Pulse can run the publish-time Backstory steps as a draft, and publish ships the draft the editor saw
status: BUILT
tags: [pulse, feature]
anchor: .github/workflows/pulse-publish.yml
---

## What

Asked for by the editor 2026-10-28, after the morning's publish. Measured on `origin/main` that day:
`pulse-publish.yml` runs two Backstory steps after Pulse commits the Lineup. `build_pairings.py`
puts each story in a category, and when none fits, `auto_categories` writes a new one with its objects
(the 2026-10-28T18:58Z publish created `p-class-signaling` this way). `build_origins.py` writes each
story's "It starts in", origin and Beginnings. Both call the model (Haiku and Sonnet). The whole publish
run took about 3 minutes (18:55:33 to 18:58:31). Pulse cannot run either step. Its per-story preview
(T-0098) says so: the Today line and "It starts in" are written at publish, so the preview shows the
last published ones.

Wanted, three parts:

1. **Draft.** A button in Pulse sends the current Lineup to a workflow that runs the Backstory steps
   on the code of the branch that Pulse is served from, and writes their output to
   `ntk-pulse/data/backstory-draft.json` (keyed to the Lineup it was run on), not to `digest/`,
   `backstory/` or `provisional-rows.json`. Staging Pulse drafts on the staging branch; the live
   Pulse drafts on main. Once T-0110 and T-0111 land, the draft is where they run.
2. **Show it.** Pulse reads the draft and shows it in the per-story preview: the category chosen or
   created, its objects, "It starts in", the Beginnings. A story whose Lineup entry changed since the
   draft says the draft is stale for it.
3. **Ship it.** At publish, a story whose draft matches the Lineup gets the draft's results and is not
   run again; anything else runs as today. The editor's approval is of what ships, not of a sample of
   it.

**Staging is the test bed.** Amended 2026-10-28 with the editor. This, T-0110 and T-0111 are built
on their own branches, merged into `staging` (reset to main on 2026-10-28) and tried in staging Pulse
with real Lineups before anything reaches main. What is ruled out below is staging as the daily review
step, not staging as the place the build is tried.

Prior art, measured 2026-10-28: commit `de7e91c7` (T-0083, kept on branch `staging-2026-10-13`) added "Send
to a staging run". It applies to today's main without conflicts and Pulse's script still parses, but it
runs a whole publish onto the staging branch and shows the result on the staging site. Nothing returns
to production Pulse, and production publish recomputes. Its way of sending the Lineup somewhere other
than main is reusable. Merged with today's main, its push retry (T-0093) would rebase the staging
branch onto main and fail; any reuse has to retry against the branch it pushes to.

## Why

The editor likes what the publish-time selection does and sees it only after it is live. Approval is
the editor's last look (T-0091); a Backstory chosen after that look is not approved, it is reviewed in
production. Today's category and objects went out unread.

Ruled out:
- **Porting the selection to Pulse's JavaScript.** Two copies of the logic drift; this is the
  `digest/v2/` duplication again, and T-0091's rule was to share the code, not copy it.
- **Making the staging site the daily review surface** (`de7e91c7` as built). It runs on whatever code
  `staging` holds (two weeks behind main on 2026-10-28, 297 commits), the result lives on another
  site, and the real publish chooses again, so what was reviewed is not what ships.
- **A draft that publish ignores.** Two model runs per edition, and the second can choose
  differently. Freezing the draft is what makes the review true and stops the double spend.

Cost: the same model calls, moved earlier. A redraft after Lineup edits spends again, so the draft
should rerun only the stories that changed. The wait is minutes (an Actions run), acceptable for a
review step, not for clicking around. Touches `docs/decisions.md`: "Beginnings and objects are chosen
by rule, not by hand" stands (the rule still chooses; the editor sees it first), and an auto category
still needs two objects that survive the checks.

Not decided: whether the editor can reject a drafted pick in Pulse and have that stick at publish, or
only look. Start with look; the editor's tray (T-0085) is where rejection already lives.

Done means the editor drafted, read, published, and the live Backstory matched the draft. That last
step is manual and is what moves this to VERIFIED, alongside the check below.

## Check

```sh
python3 - <<'PY'
import glob, sys
bad = []
pulse = open('ntk-pulse/pulse.html', encoding='utf-8').read()
publish = open('.github/workflows/pulse-publish.yml', encoding='utf-8').read()
others = [p for p in glob.glob('.github/workflows/*.yml') if not p.endswith('pulse-publish.yml')]
drafters = [p for p in others if 'build_pairings.py' in open(p).read() and 'build_origins.py' in open(p).read()]
if not drafters:
    bad.append('no workflow besides publish runs the Backstory steps, so nothing can draft them')
for p in drafters:
    if 'backstory-draft.json' not in open(p).read():
        bad.append(f'{p} runs the Backstory steps but does not write the draft')
if 'backstory-draft.json' not in pulse:
    bad.append('Pulse never reads the draft')
# Publish must consult the draft before the two Backstory steps, and skip them only when it was used.
i = publish.find('backstory_draft.py apply')
if i < 0 or i > publish.find('build_pairings.py') or publish.count("steps.draft.outputs.used != 'true'") < 2:
    bad.append('publish does not ship the draft before choosing again')
# And the ship rule itself: a matching draft ships, one changed story means nothing ships.
import json, os, subprocess, tempfile
if os.path.exists('editorial/backstory_draft.py'):
    t = tempfile.mkdtemp()
    w = lambda n, d: json.dump(d, open(os.path.join(t, n), 'w'))
    row = {'id': 'p-x', 'stratum': 'provisional'}
    draft = {'generated': 'now', 'stories': [{'story_id': 'a', 'bs_hash': '1'}, {'story_id': 'b', 'bs_hash': '2'}],
             'ship': {'todays_pairings': [{'story_id': 'a', 'row': 'p-x'}], 'pairings_generated': 'now',
                      'provisional_rows': [row], 'provisional_store': {'rows': [row]}, 'origins': {'origins': []}}}
    w('draft.json', draft)
    for case, h, want in (('same', '2', 'used'), ('changed', 'edited', 'not used')):
        w('lineup.json', {'stories': [{'key': 'a', 'bs_hash': '1'}, {'key': 'b', 'bs_hash': h}]})
        w('bs.json', {'rows': [{'id': 'fixed'}], 'todays_pairings': []})
        out = subprocess.run(['python3', 'editorial/backstory_draft.py', 'apply'] + sum(
            [[f'--{k}', os.path.join(t, v)] for k, v in (('draft', 'draft.json'), ('lineup', 'lineup.json'),
             ('backstory', 'bs.json'), ('provisional', 'prov.json'), ('origins', 'origins.json'))], []),
            capture_output=True, text=True).stdout.strip()
        bs = json.load(open(os.path.join(t, 'bs.json')))
        if out != want:
            bad.append(f'a draft with {case} stories was {out!r}, expected {want!r}')
        if want == 'used' and ([r['id'] for r in bs['rows']] != ['fixed', 'p-x'] or not bs['todays_pairings']):
            bad.append('a shipped draft did not replace the pairings and categories, or lost a fixed row')
        if want == 'not used' and bs['todays_pairings']:
            bad.append('a draft that was not used still changed backstory.json')
else:
    bad.append('no editorial/backstory_draft.py, so publish cannot ship a draft')
if bad:
    print('\n'.join(bad)); sys.exit(1)
PY
```
