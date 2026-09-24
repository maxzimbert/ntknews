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

Built 2026-09-23, hardened and fully verified end-to-end 2026-09-24
against two consecutive live NPR days (34 real episodes total across
2026-09-22 through 2026-09-24) on real GitHub Actions runs, not just
locally:

- `ntk-pulse/newscast.py capture` — scrapes the show page (not the RSS
  feed, which keeps only ~3 episodes; the page keeps ~10 hours), downloads
  new episodes, transcribes with whisper.cpp. **Fully verified**: idempotent
  (a second run against the same page correctly captures zero), and
  resilient to a show-page fetch failure (a real run crashed outright on an
  uncaught `HTTP 402` from NPR's own site before this was caught and fixed
  — see the incident list below).
- `newscast.py label` — Haiku topic extraction per episode. **Fully
  verified against the real API**: 31 backlogged episodes labeled in one
  run once account credit was in place, 5–19 topics each, zero failures.
- `newscast.py thread` — groups a day's topics into hour-over-hour rows by
  entity overlap, entities from `cluster.entities()` so the whole pipeline
  shares one vocabulary. **Verified twice**: against a hand-built
  known-answer set before any live run existed, and again against the real
  labeled output above (37 threads across 10 real hours, real story
  persistence matching the pattern found by hand on 2026-09-18 — e.g. a
  thread dropping out for hours and reappearing rather than decaying
  smoothly).
- `.github/workflows/newscast.yml` — 20-minute cron, same `ntk-pulse`
  concurrency group as `pulse-scan.yml`/`pulse.yml`. **Fully verified on
  real Actions runners** — see the incident list; every class of failure
  below was found by dispatching real runs and reading real logs, not
  written from docs and trusted.
- `pulse.html` itself: **still not touched.** The Lineup-tab module was
  validated as a static mockup in chat (full pulse.html chrome replica:
  header tabs, `.lineup-bar`, an `npr-mod` card, the real
  `candidatesPanel()` header text truncated below it for placement context)
  and approved by the editor, but no code has been written against the
  real file. This is the entire remaining scope of this ticket — everything
  else is done and proven.

**Six real failures found and fixed by watching live runs, not by
reasoning from docs** (each is its own commit on `main`, git log has the
full detail):

1. ffmpeg's output muxer needs `-f wav` explicit — it infers format from
   the destination filename otherwise, and the temp file's `.tmp` suffix
   broke that inference on every single episode.
2. The dynamically-linked `whisper-cli` binary needs its `.so` files'
   directory on `LD_LIBRARY_PATH` — caching only the binary left it unable
   to find `libwhisper.so.1` at runtime.
3. The default cmake build uses `-march=native`, tuned to whichever exact
   CPU did the build. The binary is cached and reused across the 20-minute
   schedule, and a later run landing on a *different* physical runner in
   GitHub's fleet SIGILL'd on every episode. Fixed with `-DGGML_NATIVE=OFF`.
4. `git push` in the Commit step had no retry — a PR merged to `main`
   mid-run (by the person testing this, not a bot) caused `[rejected]
   (fetch first)` and silently discarded 22 minutes of real capture work.
   Fixed with fetch-rebase-retry, safe here specifically because this step
   only ever touches `ntk-pulse/data/newscasts/`.
5. `list_episodes()`'s show-page fetch had no error handling and crashed
   the whole script on an uncaught `HTTP 402` from NPR's own site
   (unrelated to this codebase). Because the Capture step had no
   `continue-on-error`, that also skipped Label and Build entirely — so the
   first real attempt to test labeling with newly-added API credit never
   even ran. Fixed with both a try/except and step-level
   `continue-on-error`.
6. `thread()` could list the same hour twice for one story (a single
   episode's transcript can produce two topic lines that both match the
   same thread), inflating `count` past the real number of hours captured
   — one thread showed 11 on a 10-hour day. Fixed by deduping.

Two more issues surfaced that are **not code bugs**: the Anthropic account
had insufficient credit (fixed by the editor adding credit directly, not by
any change here), and the `*/20 * * * *` schedule was observed firing only
once in a 3.5-hour window rather than the expected ~10 times — a documented
GitHub Actions behavior (scheduled workflows are best-effort and can be
throttled under load), not a misconfiguration. `capture()`'s own
idempotent, ~10-hour-backlog-tolerant design absorbed this without losing
any episodes; worth knowing about, not worth chasing.

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
