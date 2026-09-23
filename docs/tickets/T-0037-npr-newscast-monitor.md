---
id: T-0037
title: NPR News Now hourly monitor — capture and threading built, not yet rendered in Pulse
status: BUILT
tags: [pulse, feature]
anchor: ntk-pulse/newscast.py
---

## What

A new signal for the editor, requested directly: a module in Pulse's Lineup
tab, above the candidates panel (`candidatesPanel()`), showing what NPR's
News Now hourly newscast covered and how it changes hour over hour.
Monitoring only — confirmed with the editor 2026-09-23 that this does not
need to feed clusters.json, triage, or assembly.

Built and measured today against a live NPR day (2026-09-22/23, 10 episodes,
15:00–00:00):

- `ntk-pulse/newscast.py capture` — scrapes the show page (not the RSS feed,
  which keeps only ~3 episodes; the page keeps ~10 hours), downloads new
  episodes, transcribes with whisper.cpp. **Ran for real, twice, against
  live audio** — 10/10 episodes transcribed successfully both times, second
  run correctly skipped all 10 as already-captured (idempotency confirmed,
  not assumed).
- `newscast.py label` — Haiku topic extraction per episode, same call
  pattern as `triage.py` (stdlib urllib, `x-api-key` header). **Not run
  against the real API** — no `ANTHROPIC_API_KEY` in the environment this
  was built in. Confirmed it degrades gracefully with no key (logs and
  returns, same posture as `triage.py`), not confirmed against a real
  response.
- `newscast.py thread` — groups today's topics into hour-over-hour rows by
  entity overlap, entities from `cluster.entities()` so the whole pipeline
  shares one vocabulary. **Verified against a hand-built known-answer set**
  (9 real topics reconstructed from the actual transcripts, with known true
  hour patterns) — output matched expected grouping and counts exactly
  (Vance/ACA 5/10, Wells 4/10, Garces 3/10, Guterres 3/10, Curtis 3/10, Polo
  3/10, Zelensky 2/10, Greenland 2/10, Fat Bear 2/10, three correct
  singletons unmerged).
- `.github/workflows/newscast.yml` — 20-minute cron, same `ntk-pulse`
  concurrency group as `pulse-scan.yml`/`pulse.yml` so it never races their
  git push. **Never run on a GitHub Actions runner** — written from
  whisper.cpp's own build docs, not verified, because this was built from a
  macOS sandbox with no Linux runner access.
- `pulse.html` itself: **not touched.** The Lineup-tab module was validated
  as a static mockup in chat (full pulse.html chrome replica: header tabs,
  `.lineup-bar`, an `npr-mod` card, the real `candidatesPanel()` header text
  truncated below it for placement context) and approved by the editor, but
  no code was written against the real file. That is the largest remaining
  piece of this ticket.

## Why

**Cost, decided plainly:** whisper.cpp transcribes a full day of NPR's
hourly audio (~45 min) in minutes on ordinary hardware, for $0 — no hosted
ASR vendor, no new secret. Topic labeling is Haiku, ~1.5k tokens in per
episode, on the order of $1–2/month. Both are rounding errors against the
Sonnet spend `ledger.py` already has budget for (T-0030).

**Matching against Pulse's own clusters.json was tried and abandoned, not
skipped.** The original ask included cross-referencing NPR's coverage
against Pulse's lineup candidates as a corroboration signal. Run for real
against live `clusters.json`: naive entity overlap (≥2 shared entities)
matched every single cluster to every single hour, because two generic
entities like "Trump" and "U.S." clear that bar on nearly any political
story on a heavy news day. Tightening to exclude every-episode-generic
entities cut the false positive rate but still surfaced junk matches
(weekday names, "White" split from "White House"). The editor's own framing
resolved this: *"for now, this is purely monitoring for me, you don't need
to do work off it"* — so this ticket drops the clusters.json cross-reference
entirely rather than shipping a signal known to be unreliable. Revisit only
if a real editorial need for it shows up; `thread()`'s entity-overlap
grouping works well *within* a single day's NPR topics (see the verified
counts above) because Haiku-written topic labels are far less noisy than
raw 800-word transcripts — that finding would carry over if this is ever
revisited.

**A real bug, caught before it reached a cron.** `thread()` originally
scoped "today" by matching the literal date string on each episode. NPR's
own episode ids roll the date digits at local midnight (confirmed against
the real capture: `...-20260922-2300` was immediately followed by
`...-20260923-0000`), so a straight date-string filter silently dropped
every hour before midnight the moment a post-midnight episode existed — on
a normal evening editing session, exactly the failure mode. Caught by the
known-answer smoke test above, not in production. Fixed by windowing to the
most recently captured N episodes (`RECENT_HOURS = 10`) instead of a
calendar-date match, which also matches what the show page itself
effectively bounds this to.

**Timing, asked directly and answered with a real constraint, not a
guess.** The editor asked whether a single per-hour check risks landing a
minute or two before NPR posts and missing that hour's brief for a full
cycle. Answer: nothing is ever permanently lost — the show page keeps ~10
hours of backlog and `capture()` only checks "do I already have this id,"
so a too-early check just gets caught by the next one. What varies is how
stale the "most recent hour" display can get, which is a function of check
frequency, not a fixed cost — hence 20 minutes, reusing `pulse-scan.yml`'s
existing cadence, rather than a slower schedule that would need a precise
(and, per the ticket, unmeasured) NPR publish-time offset to be safe.

## Check

```sh
set -e
python3 -m py_compile ntk-pulse/newscast.py

# The workflow exists, shares pulse-scan/pulse's concurrency group (so it
# can never race their git push), and runs on the agreed 20-minute cadence.
grep -q 'group: ntk-pulse' .github/workflows/newscast.yml
grep -q 'cron: "\*/20 \* \* \* \*"' .github/workflows/newscast.yml
grep -q 'contents: write' .github/workflows/newscast.yml

# thread()'s grouping logic, re-run against the same known-answer topic set
# used to catch the midnight bug — asserts the exact counts, not just "ran
# without crashing."
python3 - <<'PYEOF'
import sys, json, tempfile, shutil
from pathlib import Path
sys.path.insert(0, "ntk-pulse")
import newscast as ns
from cluster import entities

by_hour = {
    "15:00": ["Trump and Zelensky meet on the sidelines of the UN General Assembly over ending the war with Russia",
               "Trump signs a security agreement with Greenland and Denmark, expanding U.S. military presence",
               "Nolan Wells' family disputes grand jury declining to bring charges in his death",
               "Wilbur Garces Perez, shot by an ICE officer in Austin, remains in ICE detention with the bullet still in him",
               "DoorDash agrees to pay $131.5 million to settle underpayment claims with NYC delivery workers"],
    "16:00": ["Nolan Wells' family disputes grand jury declining to bring charges in his death",
               "Vice President Vance pulls 750,000 people off ACA marketplace rolls, citing fraud",
               "UN Secretary-General Guterres calls for AI rules and climate accountability in farewell address"],
    "17:00": ["Federal Reserve officials signal caution on further rate cuts this year"],
    "18:00": ["Sen. Curtis (R-UT) asks the Judiciary Committee to investigate Donald Trump Jr.'s business ties"],
    "19:00": ["Trump and Zelensky meet on the sidelines of the UN General Assembly over ending the war with Russia",
               "Vice President Vance pulls 750,000 people off ACA marketplace rolls, citing fraud",
               "Hurricane Polo, a Category 5 storm, moves along Mexico's southwestern coast"],
    "20:00": ["Nolan Wells' family disputes grand jury declining to bring charges in his death",
               "Sen. Curtis (R-UT) asks the Judiciary Committee to investigate Donald Trump Jr.'s business ties",
               "Voting opens for Fat Bear Week at Katmai National Park",
               "Vice President Vance pulls 750,000 people off ACA marketplace rolls, citing fraud"],
    "21:00": ["Wilbur Garces Perez, shot by an ICE officer in Austin, remains in ICE detention with the bullet still in him",
               "UN Secretary-General Guterres calls for AI rules and climate accountability in farewell address",
               "Hurricane Polo, a Category 5 storm, moves along Mexico's southwestern coast"],
    "22:00": ["Trump signs a security agreement with Greenland and Denmark, expanding U.S. military presence",
               "Vice President Vance pulls 750,000 people off ACA marketplace rolls, citing fraud"],
    "23:00": ["Vice President Vance pulls 750,000 people off ACA marketplace rolls, citing fraud"],
    "00:00": ["UN Secretary-General Guterres calls for AI rules and climate accountability in farewell address",
               "Trump meets Venezuela's interim president Rodriguez at UN sidelines",
               "Sen. Curtis (R-UT) asks the Judiciary Committee to investigate Donald Trump Jr.'s business ties",
               "Wilbur Garces Perez, shot by an ICE officer in Austin, remains in ICE detention with the bullet still in him",
               "Nolan Wells' family disputes grand jury declining to bring charges in his death",
               "Hurricane Polo, a Category 5 storm, moves along Mexico's southwestern coast",
               "Voting opens for Fat Bear Week at Katmai National Park"],
}
tmpdir = Path(tempfile.mkdtemp())
ns.DATA = tmpdir
for hour, topics in by_hour.items():
    hh = hour.replace(":", "")
    date = "20260923" if hour == "00:00" else "20260922"
    record = {"id": f"nx-s1-{date}-{hh}", "date": date, "hour": hour,
        "captured_at": "x", "source_url": "x", "word_count": 800, "transcript": "x",
        "topics": [{"text": t, "entities": sorted(entities(t))} for t in topics]}
    (tmpdir / f"nx-s1-{date}-{hh}.json").write_text(json.dumps(record))
ns.thread()
out = json.loads((tmpdir / "today.json").read_text())
shutil.rmtree(tmpdir)
counts = {th["text"]: th["count"] for th in out["threads"]}
expect = {"Vice President Vance pulls 750,000 people off ACA marketplace rolls, citing fraud": 5,
          "Nolan Wells' family disputes grand jury declining to bring charges in his death": 4}
for text, n in expect.items():
    assert counts.get(text) == n, f"expected {n} for {text!r}, got {counts.get(text)}"
assert len(out["episodes"]) == 10, f"expected 10 episodes windowed, got {len(out['episodes'])}"
print("thread() known-answer check passed")
PYEOF

# The largest remaining piece: pulse.html actually rendering this. Currently
# open — this is what promotes the ticket, not the plumbing above.
grep -q "npr-mod\|npr_news_now\|NPR News Now" ntk-pulse/pulse.html
```
