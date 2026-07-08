#!/usr/bin/env python3
"""NTK Desk — Layer 4: Triage.

Runs the NTK need-to-know rubric against each cluster via Claude Haiku.
Verdict: YES (need to know) / MAYBE / NO (pablum), with a one-line
rationale, editorial-pillar tags, and a civilian-anchor candidate.

- Skips gracefully if ANTHROPIC_API_KEY is not set (clusters stay unverdicted).
- Caches verdicts by cluster fingerprint (data/triage-cache.json) so re-runs
  only pay for genuinely new or materially grown clusters.
- Caps calls per run to keep cron cost bounded.

NOTE: The rubric prompt below is the generalized NTK verdict. If you prefer
the exact prompt from rss-scanner, swap the RUBRIC string — the plumbing
doesn't change. Stdlib only.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
MODEL = "claude-haiku-4-5-20251001"
MAX_CALLS_PER_RUN = 25
API_URL = "https://api.anthropic.com/v1/messages"

RUBRIC = """You are the triage editor for NTK News, a daily digest for anxious, disengaged, cynical Americans who have largely stopped following the news. NTK's promise: no increments, no pablum — only what a reader needs to know, contextualized.

Judge the news story below (represented by headlines from multiple publishers) against the NTK rubric:
1. PILLAR RELEVANCE — does it connect to structural realities NTK tracks (power & corruption; democracy & society; climate & rights; affordability; the recurring patterns of American history)?
2. NAMED STAKES — are there named actors whose situations change? Not statements — acts.
3. HOUSEHOLD IMPACT — does it touch the reader's money, rights, health, safety, kids, or community, directly or within visible steps?
4. STRUCTURAL SIGNIFICANCE — will this matter in a month? Is it a development in an ongoing story, or noise?

Pablum indicators (vote NO): pure statements/reactions with no act; horse-race framing; celebrity/novelty churn; process increments that change nothing a reader can feel; wire rewrites of a press release.

Respond ONLY with JSON, no preamble, no markdown fences:
{"verdict": "YES"|"MAYBE"|"NO", "rationale": "<one sentence, under 25 words>", "pillars": ["<0-3 short tags>"], "anchor": "<the civilian anchor if one exists: a dollar figure, brand, named institution — else empty string>", "solo": "<ONLY when a single publisher has the story: 'scoop' if it reads like original reporting others will follow, 'pablum' if it reads like churn nobody will follow — argue it from the headline evidence. Empty string when multiple publishers have it.>"}"""


def log(msg):
    print(f"[triage] {msg}", flush=True)


def fingerprint(cluster):
    # Re-triage when a cluster roughly doubles in diversity
    bucket = 1 if cluster["diversity"] < 2 else (2 if cluster["diversity"] < 4 else 4)
    return f"{cluster['key']}:{bucket}"


def call_claude(api_key, cluster):
    headlines = "\n".join(
        f"- [{it['publisher']}] {it['title']}" for it in cluster["items"][:8]
    )
    body = {
        "model": MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": f"{RUBRIC}\n\nSTORY ({cluster['diversity']} publishers, {cluster['age_hours']}h old):\n{headlines}"}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    payload = json.loads((DATA / "clusters.json").read_text())
    cache_path = DATA / "triage-cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    if not api_key:
        log("ANTHROPIC_API_KEY not set — applying cached verdicts only.")

    calls = 0
    for cl in payload["clusters"]:
        fp = fingerprint(cl)
        if fp in cache:
            cl["triage"] = cache[fp]
            continue
        if not api_key or calls >= MAX_CALLS_PER_RUN:
            cl["triage"] = None
            continue
        try:
            verdict = call_claude(api_key, cl)
            verdict["at"] = datetime.now(timezone.utc).isoformat()
            cache[fp] = verdict
            cl["triage"] = verdict
            calls += 1
        except Exception as e:
            log(f"  call failed for {cl['key']}: {type(e).__name__}: {e}")
            cl["triage"] = None

    # Prune cache entries for clusters no longer in the window
    live = {fingerprint(cl) for cl in payload["clusters"]}
    cache = {k: v for k, v in cache.items() if k in live}

    cache_path.write_text(json.dumps(cache, indent=1))
    (DATA / "clusters.json").write_text(json.dumps(payload, indent=1))
    verdicts = sum(1 for cl in payload["clusters"] if cl.get("triage"))
    log(f"{calls} new verdicts this run; {verdicts}/{len(payload['clusters'])} clusters verdicted.")


if __name__ == "__main__":
    main()
