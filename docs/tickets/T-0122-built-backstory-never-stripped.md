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

**Step two, built 2026-11-10 on the T-0117 branch** (`claude/t-0117-backstory-build-decides-3d1bae`, on
staging, not on `main`), because it changes the same functions: when a story changes after its page was built,
Pulse judges whether the page still holds instead of demanding a rebuild.

3. `bsxRefreshHere`: one Haiku call reads the page against the revised story. Normally only "We are here" must
   follow the news: it is rewritten (held to its rule: 12 to 30 words, at most two sentences, no number the story
   does not hold), title, contest, stakes, milestones and documents are left alone, and the page is
   re-fingerprinted so it reads as current. If the call judges that the history itself moved, the page says so in
   one line with a **rebuild** button; Pulse never rebuilds on its own. A "We are here" the editor typed or
   directed is never rewritten; the page flags that the story changed. A new line that breaks a rule, or a failed
   call, leaves the page as built and still reading as changed.
4. When it runs: once a built story's headline, description or Truths have changed and then stayed put for 20
   seconds, on the Lineup or the Backstory tab (`bsxWatchChanged`), once per revised text
   (`change_checked_for` on the draft); and before any revise or refile of a changed story. A story-only
   fingerprint (`bs_story_hash`) tells a story change from a row change. An edit with no model call (`bsxPatch`)
   no longer marks a changed story current.
5. The blocking alert "This story changed since its Backstory was built. Rebuild from scratch." is gone; edits
   on a changed story are accepted. The note on the review says what was done ("We are here updated to follow
   the story", "your own We are here was left as you wrote it", or "the history may have moved" with rebuild).

Cost: one Haiku call per changed story, about 1,400 tokens in and 100 out on the seven 2026-11-10 stories
(measured as prompt length, about four characters a token; the live count is unverified until the editor runs one).
Tested with stand-in replies on the real case (the Hegseth page's "within two legislative days" against the
revised story's 211 to 204 vote), in `scripts/test_pulse_backstory.js`. Not covered by a test: the 20-second
watcher and the draft save, which need a browser, a GitHub token and the editor's key. A story published within
20 seconds of its last edit ships as last built, unchecked.

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
# Step two (2026-11-10): Pulse judges a changed story's page itself; never a forced rebuild
out=$(node scripts/test_pulse_backstory.js) || { echo "OPEN: the Pulse Backstory tests fail"; exit 1; }
for want in \
  "change: a revised story refreshes We are here and keeps the milestones" \
  "change: a We are here the editor typed is never rewritten" \
  "change: a changed story never forces a rebuild"
do
  echo "$out" | grep -qF "ok   $want" || { echo "OPEN: no passing test: $want"; exit 1; }
done
```
