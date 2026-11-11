---
id: T-0122
title: A story that changes after its Backstory was built keeps that Backstory at publish
status: BUILT
tags: [backstory, defect]
anchor: editorial/backstory_draft.py:60
---

## What

Measured 2026-11-10. At the 20:33 UTC publish all seven stories shipped a Backstory. The editor then revised
one story's Truths from an imported report (story `3c8b0c2c…`, the Hegseth impeachment) and republished at
23:20 UTC. The publish log: "6 of 7 stories ship a page; without one: 3c8b0c2c…: changed since it was built".
The page dropped was the one the editor had built by hand, all three milestones `by: editor`.

Two causes:

- `editorial/backstory_draft.py apply` shipped a page only when the story's fingerprint (`bs_hash`) matched
  the one the page was built from. Any edit to the headline, description or Truths removed the page.
- Pulse said the opposite. The publish dialog (`draftPreflight`) and the story's review (`bsrStaleNote`) both
  read "publish will choose the Backstory again", wording from before T-0114, when publish did choose. A
  second, accurate warning (`rowPreflight`) sat beside it.

Built 2026-11-10 on branch `T-0122-backstory-never-stripped`:

1. `apply` ships a built page whether or not the fingerprint matches, and logs which shipped "as last built,
   the story changed since". Only a story never built to the contract ships none.
2. The false warning is gone. The accurate one now says the page ships as last built and that "We are here"
   may be behind the story. The note on the review says the same and offers a rebuild as a choice.

Run against the real Lineup and draft on `main`: 7 of 7 ship.

**Not built here**, handed to the T-0117 work because it changes the same functions: when a story changes,
Pulse judges whether its page still holds and refreshes "We are here" alone, at the cost of one small call
per changed story. Until then a page can ship with a "We are here" one step behind its story.

## Why

The editor, 2026-11-10: "all I did was import a story, revise the truths with the imported story. backstory
didn't need to substantively change. why couldn't it simply look at the digest story and make its own
decision? or why not let me do a rebuild if I thought it necessary? stripping out backstory from a digest
item is never ok."

The fingerprint rule existed so a page could never contradict a story that changed under it. It bought that
by treating every edit as invalidating, with removal as its only response, and it never asked. A stale "We
are here" is a smaller harm than a story with no Backstory, and the editor can see and fix it.

The rule is narrow, by the editor's choice the same day: a page that was built is never dropped. A first
build the system judges weak may still be held until the editor ships it (T-0117).

This also explains T-0013 going stale that evening: its check holds that every published story has a
pairing, which T-0114 had quietly stopped promising. With this change it is true again for every built story.

T-0114's check expected a changed story to ship nothing. That one clause was rewritten to the new rule, with
the date and this ticket named beside it.

## Check

```sh
python3 - <<'PY' || exit 1
import json, os, subprocess, sys, tempfile
t = tempfile.mkdtemp(); w = lambda n, d: json.dump(d, open(os.path.join(t, n), 'w'))
page = lambda x: {'v': 2, 'title': x, 'here': 'Here ' + x, 'beginnings': [], 'case': []}
w('draft.json', {'stories': [{'story_id': 'same', 'bs_hash': '1', 'composed': page('A')}, {'story_id': 'edited', 'bs_hash': '2', 'composed': page('B')}],
                 'ship': {'todays_pairings': [{'story_id': k, 'row': 'gaza'} for k in ('same', 'edited')]}})
w('lineup.json', {'stories': [{'key': 'same', 'bs_hash': '1'}, {'key': 'edited', 'bs_hash': 'the story changed'}, {'key': 'unbuilt', 'bs_hash': '3'}]})
w('bs.json', {'rows': [{'id': 'gaza'}], 'todays_pairings': []})
r = subprocess.run([sys.executable, 'editorial/backstory_draft.py', 'apply', '--draft', t + '/draft.json', '--lineup', t + '/lineup.json',
                    '--backstory', t + '/bs.json', '--provisional', t + '/p.json'], capture_output=True, text=True)
got = [p['story_id'] for p in json.load(open(t + '/bs.json'))['todays_pairings']]
if got != ['same', 'edited']:
    print('OPEN: a story edited after its Backstory was built does not keep it: shipped', got); sys.exit(1)
if 'edited' not in r.stderr or 'last built' not in r.stderr:
    print('OPEN: publish does not say which page shipped as last built'); sys.exit(1)
s = open('ntk-pulse/pulse.html', encoding='utf-8').read()
for wrong in ('Publish will choose the Backstory again', "publish will choose this story's Backstory again", 'will ship without one unless rebuilt'):
    if wrong in s:
        print('OPEN: Pulse still says: ' + wrong); sys.exit(1)
PY
```
