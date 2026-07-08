#!/usr/bin/env python3
"""NTK Desk — Layer 3: The Story Ledger.

Epistemic deduplication — the machine version of "no increments."

Each story that survives triage (verdict YES or MAYBE) gets a persistent
ledger: the canonical record of what is already known (actors, numbers,
documents, quotes, state of play). Every new item in the cluster is diffed
against the ledger by Claude Sonnet and classified:

  DEVELOPMENT — evidently adds a new actor, number, document, or on-record
                quote, or changes the state of play. Surfaces to the editor.
  INCREMENT   — restates the ledger with trivial delta. Logged, not surfaced.
  RECYCLED    — aggregation of aggregation. Logged; counts toward velocity only.

Ledgers persist in data/ledgers.json ACROSS the 48h window (long-running
stories keep their memory). Matching: shared item ids first, entity overlap
for stories that resurface after a gap. Inactive ledgers expire after 14 days.

Also extracts per-item "unique contribution" (the LLM angle pass) and
first-reported-by credits, in the same call — one Sonnet call per cluster
per run, only for triage survivors with un-diffed items, capped.

SLICE 2 LIMITATION (by design): the diff judges headline + RSS summary, not
full article bodies. News writing frontloads new facts, so this catches most
developments; full-body diffing arrives when the fetch layer lands (Slice 3).
"Judge on evidence" is therefore a hard rule in the prompt: if the summary
shows nothing new, it's an INCREMENT even if the body might contain more.

Usage:
  python ledger.py          # real run (needs ANTHROPIC_API_KEY)
  python ledger.py --mock   # deterministic offline classifications for testing

Stdlib only.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
MODEL = "claude-sonnet-4-6"
API_URL = "https://api.anthropic.com/v1/messages"
MAX_CALLS_PER_RUN = 15
LEDGER_EXPIRE_DAYS = 14
ENTITY_MATCH = 3          # shared entity tokens to attach a resurfaced story
DEV_RECENT_HOURS = 12     # a cluster is "developing" if a DEVELOPMENT landed within this

DIFF_PROMPT = """You are the ledger editor for NTK News, a daily digest whose core promise to readers is: no increments. Your job is epistemic deduplication — deciding whether each new article adds to what is already known about a story.

THE LEDGER (everything already established about this story; empty fields mean a brand-new story):
{ledger}

NEW ITEMS (headline + RSS summary only):
{items}

Classify each new item:
- DEVELOPMENT — it evidently adds a new named actor, a new number, a new document, a new on-record quote, or it changes the state of play. The first items of a brand-new story are DEVELOPMENTs.
- INCREMENT — it restates the ledger with trivial delta: fresh prose, same knowledge.
- RECYCLED — aggregation of aggregation: it evidently derives entirely from other outlets' coverage (markers: "reports say", "according to [outlet]", roundup framing) and adds nothing.

Hard rules:
- Judge ONLY on evidence in the headline and summary. If they show nothing new, the item is an INCREMENT even if the full article might contain more.
- A different angle on known facts is still an INCREMENT unless it introduces a new fact — angles are captured separately in "unique".
- "unique" answers: what does this piece alone contribute? A source nobody else has, a document, an evidenced contrarian thesis, an on-the-ground scene. Empty if nothing distinctive.
- "credits": outlet names this item credits for the reporting ("first reported by X", "according to X"). Empty list if none.
- ledger_updates must contain ONLY facts evidenced by these items. Rewrite state_of_play ONLY if a DEVELOPMENT changed it; otherwise return an empty string for it.

Respond ONLY with JSON, no preamble, no markdown fences:
{{"items": [{{"id": "<item id>", "class": "DEVELOPMENT"|"INCREMENT"|"RECYCLED", "what_new": "<the specific new fact, under 20 words; empty unless DEVELOPMENT>", "unique": "<distinct contribution, under 15 words; else empty>", "credits": ["<outlet>"]}}], "ledger_updates": {{"actors": [{{"name": "", "role": ""}}], "numbers": [{{"value": "", "what": ""}}], "documents": [""], "quotes": [{{"who": "", "gist": ""}}], "state_of_play": ""}}}}"""


def log(msg):
    print(f"[ledger] {msg}", flush=True)


def now_utc():
    return datetime.now(timezone.utc)


def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def blank_ledger(cluster, ts):
    return {
        "title": cluster["title"],
        "created": ts, "last_active": ts,
        "entities": list(cluster.get("entities", [])),
        "seen_ids": [],
        "facts": {"actors": [], "numbers": [], "documents": [], "quotes": [],
                  "state_of_play": ""},
        "credits": [],
    }


def match_ledger(cluster, ledgers):
    cids = {it["id"] for it in cluster["items"]}
    cents = set(cluster.get("entities", []))
    best, best_score = None, 0
    for lid, led in ledgers.items():
        if cids & set(led["seen_ids"]):
            return lid  # shared items — same story, definitively
        shared = len(cents & set(led["entities"]))
        if shared >= ENTITY_MATCH and shared > best_score:
            best, best_score = lid, shared
    return best


def call_claude(api_key, ledger, new_items, summaries):
    lines = []
    for it in new_items:
        summ = summaries.get(it["id"], "")
        lines.append(f'- id={it["id"]} [{it["publisher"]}] {it["title"]}'
                     + (f' — {summ}' if summ else ""))
    prompt = DIFF_PROMPT.format(
        ledger=json.dumps({"state_of_play": ledger["facts"]["state_of_play"],
                           **{k: ledger["facts"][k] for k in ("actors", "numbers", "documents", "quotes")},
                           "credits": ledger["credits"]}, indent=1),
        items="\n".join(lines))
    body = {"model": MODEL, "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return json.loads(text.replace("```json", "").replace("```", "").strip())


def mock_diff(ledger, new_items, summaries):
    """Deterministic offline classifications — for pipeline/UI testing only."""
    known_nums = {n["value"] for n in ledger["facts"]["numbers"]}
    out_items, updates = [], {"actors": [], "numbers": [], "documents": [],
                              "quotes": [], "state_of_play": ""}
    fresh_story = not ledger["seen_ids"]
    for it in new_items:
        text = f'{it["title"]} {summaries.get(it["id"], "")}'
        low = text.lower()
        credits = re.findall(r"(?:according to|first reported by)\s+(?:the\s+)?([A-Z][\w\s]{2,24}?)[,.]", text, flags=re.IGNORECASE)
        nums = set(re.findall(r"[\d][\d,\.]*", text)) - known_nums
        if "according to" in low or low.startswith("reports"):
            cls, new = "RECYCLED", ""
        elif fresh_story or nums:
            cls, new = "DEVELOPMENT", ("initial report" if fresh_story else f"new figure: {sorted(nums)[0]}")
            for n in sorted(nums)[:2]:
                updates["numbers"].append({"value": n, "what": "from " + it["publisher"]})
        else:
            cls, new = "INCREMENT", ""
        out_items.append({"id": it["id"], "class": cls, "what_new": new,
                          "unique": "", "credits": [c.strip() for c in credits]})
    if any(i["class"] == "DEVELOPMENT" for i in out_items):
        updates["state_of_play"] = f"[mock] {len(out_items)} items diffed for '{ledger['title'][:50]}'."
    return {"items": out_items, "ledger_updates": updates}


def merge_facts(ledger, updates, ts):
    f = ledger["facts"]
    have_actors = {a["name"].lower() for a in f["actors"]}
    for a in updates.get("actors", []):
        if a.get("name") and a["name"].lower() not in have_actors:
            f["actors"].append(a); have_actors.add(a["name"].lower())
    have_nums = {(n["value"], n["what"].lower()) for n in f["numbers"]}
    for n in updates.get("numbers", []):
        if n.get("value") and (n["value"], n.get("what", "").lower()) not in have_nums:
            f["numbers"].append(n)
    have_docs = {d.lower() for d in f["documents"]}
    for d in updates.get("documents", []):
        if d and d.lower() not in have_docs:
            f["documents"].append(d)
    have_q = {q["gist"].lower() for q in f["quotes"]}
    for q in updates.get("quotes", []):
        if q.get("gist") and q["gist"].lower() not in have_q:
            f["quotes"].append(q)
    if updates.get("state_of_play"):
        f["state_of_play"] = updates["state_of_play"]
    ledger["last_active"] = ts


def main():
    mock = "--mock" in sys.argv[1:]
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key and not mock:
        log("ANTHROPIC_API_KEY not set — skipping ledger pass (run with --mock for offline testing).")
        return

    ts = now_utc().isoformat()
    clusters_payload = load_json(DATA / "clusters.json", {"clusters": []})
    window = load_json(DATA / "window.json", {"items": {}})
    summaries = {iid: it.get("summary", "") for iid, it in window["items"].items()}
    ledgers = load_json(DATA / "ledgers.json", {})
    classes = load_json(DATA / "ledger-classes.json", {})  # item_id -> classification

    # Expire stale ledgers
    cutoff = now_utc() - timedelta(days=LEDGER_EXPIRE_DAYS)
    before = len(ledgers)
    ledgers = {k: v for k, v in ledgers.items()
               if datetime.fromisoformat(v["last_active"]) >= cutoff}
    if before - len(ledgers):
        log(f"Expired {before - len(ledgers)} stale ledgers.")

    calls = 0
    for cl in clusters_payload["clusters"]:
        verdict = (cl.get("triage") or {}).get("verdict")
        if verdict not in ("YES", "MAYBE"):
            continue
        lid = match_ledger(cl, ledgers)
        if lid is None:
            lid = cl["key"]
            ledgers[lid] = blank_ledger(cl, ts)
        led = ledgers[lid]
        # keep the entity fingerprint fresh for future matching
        led["entities"] = sorted(set(led["entities"]) | set(cl.get("entities", [])))[:60]

        new_items = [it for it in cl["items"] if it["id"] not in set(led["seen_ids"])]
        if not new_items:
            continue
        if not mock and calls >= MAX_CALLS_PER_RUN:
            continue
        try:
            result = (mock_diff if mock else
                      lambda l, n, s: call_claude(api_key, l, n, s))(led, new_items, summaries)
        except Exception as e:
            log(f"  diff failed for '{cl['title'][:40]}': {type(e).__name__}: {e}")
            continue
        calls += 0 if mock else 1
        for item_res in result.get("items", []):
            item_res["ledger_id"] = lid
            item_res["at"] = ts
            classes[item_res["id"]] = item_res
            for c in item_res.get("credits", []):
                if c and c not in led["credits"]:
                    led["credits"].append(c)
        merge_facts(led, result.get("ledger_updates", {}), ts)
        led["seen_ids"] = list(set(led["seen_ids"]) | {it["id"] for it in new_items})

    # Annotate clusters.json for the Desk view
    dev_cut = now_utc() - timedelta(hours=DEV_RECENT_HOURS)
    for cl in clusters_payload["clusters"]:
        devs_recent = 0
        state = ""
        for it in cl["items"]:
            res = classes.get(it["id"])
            if not res:
                it["ledger"] = None
                continue
            it["ledger"] = {"class": res["class"], "what_new": res.get("what_new", ""),
                            "unique": res.get("unique", ""), "credits": res.get("credits", [])}
            if res["class"] == "DEVELOPMENT" and datetime.fromisoformat(res["at"]) >= dev_cut:
                devs_recent += 1
            lid = res.get("ledger_id")
            if lid and lid in ledgers:
                state = ledgers[lid]["facts"]["state_of_play"]
        cl["developments_recent"] = devs_recent
        cl["state_of_play"] = state

    # Prune classification cache to items still in the window
    live = set(window["items"].keys())
    classes = {k: v for k, v in classes.items() if k in live}

    (DATA / "ledgers.json").write_text(json.dumps(ledgers, indent=1))
    (DATA / "ledger-classes.json").write_text(json.dumps(classes, indent=1))
    (DATA / "clusters.json").write_text(json.dumps(clusters_payload, indent=1))
    devs = sum(c.get("developments_recent", 0) for c in clusters_payload["clusters"])
    log(f"{'mock' if mock else str(calls) + ' Sonnet'} diffs; {len(ledgers)} live ledgers; "
        f"{devs} recent developments on the board.")


if __name__ == "__main__":
    main()
