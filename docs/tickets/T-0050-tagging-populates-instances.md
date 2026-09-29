---
id: T-0050
title: Tagging a story to a Backstory row in Pulse never reaches the row's Earlier episodes
status: DECIDED
tags: [backstory, feature]
anchor: editorial/build_pairings.py:283
---

## What

A row's `instances[]` is its "Earlier episodes" list: past digest stories
tagged to that row, each with headline, date and permalink. The detail view
renders it (`bsrEpisodesHtml`, `digest/index.html`). Measured 2026-09-29:
`instances` is empty on all 21 rows of `digest/data/backstory.json`, so the
section never renders.

**Acceptance criterion:** when the editor tags a story to a row with the
Pulse tagging control (T-0010) and publishes, that story is appended to that
row's `instances[]`, once, and stays there across later publishes.

Stories the editor did not tag are not appended. `todays_pairings` is
overwritten every publish and nothing else writes `instances`, which is why it
is empty. `build_backstory.py` already preserves `instances` across rebuilds
(`PRESERVE_ROW`, line 81), so persistence needs no new work.

## Why

This is the link between a Backstory row and the digest articles behind it,
which is the relationship the tab exists to build. `register4-lifetimes.md:23`
puts most news in the episode list rather than the narrative ("Most news is
instances"). With the list empty the detail view is an indicator, some
objects and a "hasn't been written yet" line. Expertise (Profile) also needs
a per-row list of stories to join against, and there is none.

**Why the tagging control and not the classifier.** The editor's hunch, and
the safer path: a tag the editor made is reviewed editorial
(`build_pairings.py` says so at its T-0010 block), while a classifier pick is
a model's guess. An instance is permanent, so a wrong classifier tag becomes
a permanent wrong episode. Cost: the lists fill slowly, since the editor does
not tag eight stories a day (T-0010 keeps blank = "let the classifier decide"
as the default). That is the tradeoff being accepted.

**Other pathways, ruled in or out for later, not for this ticket:**

- *Append every pairing, classifier included.* Fills fastest, no API cost,
  but bakes classifier errors into history. `needs_review` (confidence below
  the threshold) could gate it, at the price of sparse lists. A later slice
  if editor-only proves too thin.
- *Backfill from git history.* `backstory.json` has 8 commits and dated
  digests go back to 2026-09-14, so earlier tags could be reconstructed. Not
  assessed; unverified how clean it is. Only editor tags survive as
  reviewed, and the tagging control is recent.
- *Editor prunes or reorders instances in Pulse.* Not needed until lists
  grow. Suggest capping at the newest 10 to 15 per row so the list stays
  finite.

**Implementation notes, unverified.** The permalink is
`/digest/<date>/<slug>/`, built by `build_digest.py` (`slugify`,
`unique_slugs`). `pulse-publish.yml` runs `build_digest.py` before
`build_pairings.py`, so the slug exists by then, but whether
`lineup-publish.json` carries it or `build_pairings.py` must recompute it was
not checked. Dedupe on `story_id` so a republish does not double-add. The
pairings step is `continue-on-error` by design (T-0013), so a failure here
must not block a publish.

Touches T-0010 (the control), T-0011 (identical cards, unaffected: episodes
only show in the detail view) and T-0014 (classifier pre-fill, which would
make tags easier to review and so supply this list faster).

## Check

```sh
set -e
T=$(mktemp -d)
mkdir -p "$T/editorial" "$T/ntk-pulse/data" "$T/digest/data"
cp editorial/*.py editorial/backstory-rows.json "$T/editorial/"
cp -r editorial/prompts "$T/editorial/"
cp ntk-pulse/data/lineup-publish.json "$T/ntk-pulse/data/"
cp digest/data/backstory.json "$T/digest/data/"

# Fixture: tag exactly one story to a real row, leave the rest untagged,
# and start every row's instances empty.
ROW=$(python3 - "$T" <<'PYEOF'
import json, sys
t = sys.argv[1]
lp = json.load(open(t + '/ntk-pulse/data/lineup-publish.json'))
bs = json.load(open(t + '/digest/data/backstory.json'))
row = bs['rows'][0]['id']
for i, s in enumerate(lp['stories']):
    s.pop('backstory_row', None)
    if i == 0:
        s['backstory_row'] = row
for r in bs['rows']:
    r['instances'] = []
json.dump(lp, open(t + '/ntk-pulse/data/lineup-publish.json', 'w'))
json.dump(bs, open(t + '/digest/data/backstory.json', 'w'))
print(row)
PYEOF
)

# Two publishes: the tagged story must appear once, not twice.
python3 "$T/editorial/build_pairings.py" --mock >/dev/null
python3 "$T/editorial/build_pairings.py" --mock >/dev/null

python3 - "$T" "$ROW" <<'PYEOF'
import json, sys
t, row = sys.argv[1], sys.argv[2]
lp = json.load(open(t + '/ntk-pulse/data/lineup-publish.json'))
bs = json.load(open(t + '/digest/data/backstory.json'))
tagged = lp['stories'][0]['key']
by = {r['id']: r for r in bs['rows']}
ids = [x.get('story_id') for x in by[row].get('instances', [])]
bad = []
if ids.count(tagged) != 1:
    bad.append('tagged story appears %d times in %s instances (want 1)' % (ids.count(tagged), row))
others = sum(len(r.get('instances', [])) for r in bs['rows']) - len(ids)
if others:
    bad.append('%d instance(s) appended for stories the editor did not tag' % others)
if bad:
    sys.exit('\n'.join(bad))
PYEOF
rm -rf "$T"
```
