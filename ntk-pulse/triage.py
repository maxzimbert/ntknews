#!/usr/bin/env python3
"""NTK Pulse — Layer 3: Triage.

The rubric's job in Pulse is different from the Desk: nothing gets
filtered or killed off-screen. Haiku's output decorates the card:

  - beat   — the vertical tag shown next to the publisher list
  - line   — a one-line "what's at stake" description (or empty:
             if it can't produce one, the card shows nothing)
  - verdict — YES/MAYBE/NO kept as a subtle signal, not a gate

Plumbing carried from the Desk: skips gracefully without an API key,
caches by cluster fingerprint so re-runs only pay for new/grown
clusters, caps calls per run. Clusters are triaged in pulse_score
order, so the top of the surface gets verdicts first when capped.

Stdlib only. Reads/writes data/clusters.json; cache in data/triage-cache.json.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
MODEL = "claude-haiku-4-5-20251001"
MAX_CALLS_PER_RUN = int(os.environ.get("PULSE_MAX_CALLS", "25"))
API_URL = "https://api.anthropic.com/v1/messages"

BEATS = ["national", "international", "tech", "health", "education",
         "science", "business", "culture", "longevity", "parenting", "other"]

RUBRIC = """You are the monitoring editor for NTK News, a daily digest for anxious, disengaged, cynical Americans who have largely stopped following the news. You are annotating a real-time surveillance surface, not filtering it — every story stays visible regardless of your verdict.

For the story below (headlines from one or more publishers), produce:

1. BEAT — exactly one of: national, international, tech, health, education, science, business, culture, other. Pick where the story's center of gravity is, not where a publisher lives.

2. LINE — one plain sentence, under 20 words, saying what is actually happening and what's at stake for a reader. No hype, no exclamation points, no benefit claims. If the headlines don't give you enough to say something true and concrete, return an empty string — an empty line is better than a vague one.

3. VERDICT — YES (a reader needs to know), MAYBE, or NO (pablum: statements without acts, horse-race framing, celebrity churn, process increments, press-release rewrites).

4. SCORES — four 1-5 judgments the digest assembler needs. Score the STORY, not your feelings about it.

   emotional_load — what it costs the reader to carry. 1 = light or joyful. 3 = sober but bearable. 5 = death, violence, cruelty, a child harmed, personal catastrophe. Be honest; do not soften a hard story to be kind.

   explainability — can a reader with ZERO prior knowledge follow this in 150 words? 5 = fully self-contained. 3 = needs one sentence of setup. 1 = incomprehensible without following the story for weeks.

   actionability — is there a decision, deadline, or thing to do? 5 = a concrete action for an ordinary person. 3 = changes how they'd think about a decision. 1 = nothing to do.

   conversational_currency — will this come up in conversation this week? 5 = everyone will reference it. 1 = nobody will mention it.

5. POLITICIAN_LED — true if the story's primary actor is a politician or government official, false otherwise.

Respond ONLY with JSON, no preamble, no markdown fences:
{"beat": "<one of the beats>", "line": "<one sentence or empty string>", "verdict": "YES"|"MAYBE"|"NO", "emotional_load": <1-5>, "explainability": <1-5>, "actionability": <1-5>, "conversational_currency": <1-5>, "politician_led": true|false}"""


def log(msg):
    print(f"[triage] {msg}", flush=True)


def fingerprint(cluster):
    # Re-triage when a cluster roughly doubles in publisher diversity
    d = cluster["publisher_count"]
    bucket = 1 if d < 2 else (2 if d < 4 else 4)
    return f"{cluster['key']}:{bucket}:v2"   # :v2 — cached pre-scoring verdicts must re-run


def _parse_json_lenient(text):
    """Repair Haiku's occasional smart-quote / trailing-comma JSON."""
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    repaired = (text.replace("\u201c", '"').replace("\u201d", '"')
                    .replace("\u2018", "'").replace("\u2019", "'"))
    import re
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return json.loads(repaired)


def call_claude(api_key, cluster):
    headlines = "\n".join(
        f"- [{it['publisher']}] {it['title']}" for it in cluster["items"][:8]
    )
    prompt = (f"{RUBRIC}\n\nSTORY ({cluster['publisher_count']} publishers, "
              f"latest item {cluster['latest_age_hours']}h ago):\n{headlines}")
    body = {
        "model": MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
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
    verdict = _parse_json_lenient(text)
    # Sanity: clamp beat to the known set
    if verdict.get("beat") not in BEATS:
        verdict["beat"] = None
    # Clamp the 1-5 axes; assembly treats a missing score as "unknown" (3)
    # rather than as zero, so a bad parse can't silently make a story look
    # weightless on emotional load.
    for axis in ("emotional_load", "explainability", "actionability",
                 "conversational_currency"):
        try:
            verdict[axis] = max(1, min(5, int(verdict.get(axis, 3))))
        except (TypeError, ValueError):
            verdict[axis] = 3
    verdict["politician_led"] = bool(verdict.get("politician_led", False))
    return verdict


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    payload = json.loads((DATA / "clusters.json").read_text())
    cache_path = DATA / "triage-cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    if not api_key:
        log("ANTHROPIC_API_KEY not set — applying cached verdicts only.")

    calls = 0
    # clusters.json arrives sorted by pulse_score desc — top of surface first
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

    # Prune cache entries for clusters no longer on the surface
    live = {fingerprint(cl) for cl in payload["clusters"]}
    cache = {k: v for k, v in cache.items() if k in live}

    cache_path.write_text(json.dumps(cache, indent=1))
    (DATA / "clusters.json").write_text(json.dumps(payload, indent=1))
    verdicts = sum(1 for cl in payload["clusters"] if cl.get("triage"))
    log(f"{calls} new verdicts this run; {verdicts}/{len(payload['clusters'])} clusters annotated.")


if __name__ == "__main__":
    main()
