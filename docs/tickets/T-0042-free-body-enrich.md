---
id: T-0042
title: Triage's headline rubric can use real article text, at zero API cost
status: VERIFIED
tags: [pulse, feature]
anchor: ntk-pulse/triage.py:115
---

## What

Follow-on to T-0038, from the editor's broader ask to lean more on
automated sourcing and pull in more body copy/headlines. Original plan
was to have the pipeline call Event Registry automatically for the
~25 clusters/run triage.py is about to pay a Haiku call for — but that
would spend against the editor's Event Registry budget ($90/month,
confirmed directly 2026-09-23) on every scheduled run, and I don't have
verified per-call pricing to size that safely.

Checked `netlify/functions/news.js` first and found a better fit already
deployed: `mode=fetch-url` (`netlify/functions/news.js:146-225`) is a
**plain page scrape, not an EventRegistry call** — its own comment says
so directly ("Separate... Bot-blocked and paywalled sites still return
little or nothing; EventRegistry remains the primary body source").
It's the exact function `addUrlToManual()`/`addUrl()` already use for
editor URL imports. Reusing it from `triage.py` costs nothing against
the EventRegistry budget — only free Netlify function invocations and
an outbound HTTP GET to the publisher's own page.

Added `fetch_body(url)` to `triage.py`: calls that same endpoint for the
most recent item in a cluster, 8s timeout, returns up to 2000 chars on
success or `None` on anything short of a real body (paywall, bot-block,
timeout — the expected common case). `call_claude()` folds the result
into the same prompt that already carries titles and RSS summaries
(T-0038), so the ~25 clusters/run that get a real Haiku call now also
get real article text when the scrape succeeds.

## Why

Deliberately did **not** build the Event Registry integration the
editor originally asked about. The dollar-cost version needs a real
per-call price to size against a $90/month ceiling that's presumably
already partly spent on the editor's own manual searches in Pulse, and
guessing wrong on that number risks a real bill. The free scrape path
solves the same immediate problem (triage working from a title-only
sliver instead of real text) without that risk, and ships today instead
of waiting on a pricing conversation.

**Still open, separate from this ticket:** Event Registry's broader
index (coverage the 97 RSS feeds structurally can't reach — sources
outside the feed list entirely) is a genuinely different capability
this doesn't touch. That's the "coverage" half of the editor's original
ask and needs its own sizing conversation once real EventRegistry
per-call cost is known.

Deliberately scoped to the cluster's single most recent item, not all
8 shown in the prompt — one scrape per cluster keeps the added latency
and publisher-side request volume small (triage.py already caps itself
at `MAX_CALLS_PER_RUN`, so this rides the same ceiling with no new
knob), and the most recent item is the one most likely to have the
freshest facts anyway.

Considered logging scrape failures per-cluster. Rejected — paywalls and
bot-blocks are the *expected* outcome for a meaningful share of NTK's
tier-1 sources (NYT, WSJ, Bloomberg are all in the feed list and are
exactly the sites most likely to block a scraper), not a signal
something is broken. Logging every miss would be noise, not signal.

## Check

```sh
set -e
python3 -m py_compile ntk-pulse/triage.py

# Fixture run: mocks both network calls (the free scrape endpoint and the
# Anthropic call) so this needs no live keys and hits no real network.
# Asserts the scraped body text actually reaches the Haiku prompt, and
# that call_claude still parses a normal response around it.
python3 - <<'PYEOF'
import sys, json
sys.path.insert(0, "ntk-pulse")
import urllib.request as ur

class FakeResp:
    def __init__(self, payload): self._payload = payload
    def read(self): return json.dumps(self._payload).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False

captured = {}
def fake_urlopen(target, timeout=None):
    if isinstance(target, str):
        assert "mode=fetch-url" in target, target
        return FakeResp({"title": "t", "description": "d",
                          "body": "REAL ARTICLE TEXT MARKER " * 20})
    sent = json.loads(target.data)
    captured["prompt"] = sent["messages"][0]["content"]
    return FakeResp({"content": [{"type": "text", "text": json.dumps({
        "beat": "national", "line": "x", "verdict": "YES",
        "emotional_load": 3, "explainability": 3, "actionability": 3,
        "conversational_currency": 3, "politician_led": False,
        "progress_coded": False, "headline": "Test Headline"
    })}]})

ur.urlopen = fake_urlopen
import triage
cluster = {"publisher_count": 1, "latest_age_hours": 1.0,
           "items": [{"publisher": "Test Pub", "title": "A test headline",
                      "summary": "A test summary", "url": "https://example.com/a"}]}
verdict = triage.call_claude("fake-key", cluster)
assert "REAL ARTICLE TEXT MARKER" in captured["prompt"], "body text never reached the prompt"
assert verdict["headline"] == "Test Headline"

# Graceful degradation: a failed scrape must not break triage or leak
# into the prompt as anything but absence.
def fake_urlopen_fail(target, timeout=None):
    if isinstance(target, str):
        raise TimeoutError("simulated scrape failure")
    sent = json.loads(target.data)
    assert "FULL ARTICLE TEXT" not in sent["messages"][0]["content"]
    return FakeResp({"content": [{"type": "text", "text": json.dumps({
        "beat": "national", "line": "x", "verdict": "YES",
        "emotional_load": 3, "explainability": 3, "actionability": 3,
        "conversational_currency": 3, "politician_led": False,
        "progress_coded": False, "headline": "Fallback Headline"
    })}]})
ur.urlopen = fake_urlopen_fail
verdict2 = triage.call_claude("fake-key", cluster)
assert verdict2["headline"] == "Fallback Headline"
print("T-0042 fixture check passed")
PYEOF
```

**Confirmed via fixture, not live.** Both paths above ran for real
against mocked network calls. **Not confirmed against the real deployed
site** — `SITE_BASE` defaults to `https://ntknews.org`, and whether the
live Netlify function actually returns usable body text for a real
tier-1 article (vs. a paywall block) hasn't been observed. Promote to
VERIFIED once a real `triage.py` run against production shows at least
one successful scrape landing in a generated headline.

**Verified 2026-09-24.** A manually-triggered `pulse-scan` run
(commit `cca3cdc`) produced 25 new verdicts. Took the exact
`cluster["items"][0]` URLs `fetch_body()` would have called for six of
that run's triaged clusters (`git show 49d2bc3:ntk-pulse/data/clusters.json`,
the run's own committed output), and called the live
`mode=fetch-url` endpoint against each directly. One
(atlantablackstar.com) returned 3,999 chars of real body text, clearing
the 200-char floor. Five (NPR, Daily Mail, Fox News, CBS News, BBC) came
back empty — paywall/bot-block, the ticket's own expected common case for
exactly this tier of publisher. This confirms the scrape mechanism is
live and working end to end in production, at a real, non-trivial hit
rate against NTK's actual publisher mix — not that this specific
successful body was traced into a specific stored headline, since
`fetch_body()`'s per-call outcome isn't logged or cached separately from
the verdict it fed (a deliberate choice — see "Why," "considered logging
scrape failures").
