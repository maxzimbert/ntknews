#!/usr/bin/env python3
"""NTK Pulse — Layer 3: The Story Ledger.

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

BODY LIMITATION (still true in Pulse): the diff judges headline + RSS summary,
not full article bodies. Enrichment — the only place Pulse has real bodies —
runs client-side in pulse.html at lineup time, AFTER this pipeline stage has
finished. So the Digest Assembly spec's "extraction must run against enriched
bodies" is NOT satisfied here. News writing frontloads new facts, so this
catches most developments, and it is enough to drive the assembly rubric's
increment constraint and the "N new facts since you last looked" promise.
Full-body diffing requires the ledger to run after enrichment — either moving
it client-side or moving enrichment server-side. Neither is in scope here.
"Judge on evidence" is therefore a hard rule in the prompt: if the summary
shows nothing new, it's an INCREMENT even if the body might contain more.

CONTRADICTIONS (new in Pulse): the diff also flags when an item contradicts
something already established in the ledger — a reversal, a denial, a corrected
figure. This is material the Lies section needs and previously could not see.

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
MODEL = "claude-sonnet-5"
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
- "contradicts": if this item contradicts something already established in THE LEDGER above — a reversal, a denial, a corrected figure, a walked-back commitment — state it in under 25 words: what the ledger held, and what this item asserts instead. Empty string if nothing is contradicted. Be strict: a new development is not a contradiction. Only flag a genuine conflict with an already-established fact.
- ledger_updates must contain ONLY facts evidenced by these items. Rewrite state_of_play ONLY if a DEVELOPMENT changed it; otherwise return an empty string for it.

CRITICAL JSON FORMATTING: your response must be strictly parseable JSON. Inside any string value: escape every double-quote as \\", escape every backslash as \\\\, escape every newline as \\n. Do NOT use smart quotes (\u201c \u201d \u2018 \u2019) inside string values — use straight quotes and escape them. If a source headline contains an apostrophe (Graham's, Trump's), preserve it as-is — apostrophes do not need escaping. If it contains a double-quote, escape it. Failure to produce valid JSON breaks the entire pipeline for this story.

Respond ONLY with JSON, no preamble, no markdown fences:
{{"items": [{{"id": "<item id>", "class": "DEVELOPMENT"|"INCREMENT"|"RECYCLED", "what_new": "<the specific new fact, under 20 words; empty unless DEVELOPMENT>", "unique": "<distinct contribution, under 15 words; else empty>", "credits": ["<outlet>"], "contradicts": "<under 25 words, or empty>"}}], "ledger_updates": {{"actors": [{{"name": "", "role": ""}}], "numbers": [{{"value": "", "what": ""}}], "documents": [""], "quotes": [{{"who": "", "gist": ""}}], "state_of_play": ""}}}}"""


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
        "contradictions": [],   # {at, item_id, publisher, text} — append-only
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


MAX_ITEMS_PER_DIFF_CALL = 12  # a first run against an empty ledger can hand a
    # big story 20+ "new" items at once; capping the batch keeps every response
    # comfortably inside max_tokens instead of gambling on truncation. The
    # remainder is picked up on the NEXT run — it just costs one extra cycle
    # of freshness, not correctness.


def call_claude(api_key, ledger, new_items, summaries):
    # ~150 tokens/item covers class + what_new + unique + credits + contradicts
    # generously; MAX_ITEMS_PER_DIFF_CALL * 150 + headroom stays well inside
    # the cap even for the chattiest responses.
    overflow = len(new_items) > MAX_ITEMS_PER_DIFF_CALL
    batch = new_items[:MAX_ITEMS_PER_DIFF_CALL]
    lines = []
    for it in batch:
        summ = summaries.get(it["id"], "")
        lines.append(f'- id={it["id"]} [{it["publisher"]}] {it["title"]}'
                     + (f' — {summ}' if summ else ""))
    prompt = DIFF_PROMPT.format(
        ledger=json.dumps({"state_of_play": ledger["facts"]["state_of_play"],
                           **{k: ledger["facts"][k] for k in ("actors", "numbers", "documents", "quotes")},
                           "credits": ledger["credits"]}, indent=1),
        items="\n".join(lines))
    body = {"model": MODEL, "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    text = text.replace("```json", "").replace("```", "").strip()
    result = _parse_json_lenient(text)
    # Only the batch actually sent counts as "processed" — the caller must
    # not mark overflow items seen, or they vanish from the ledger forever
    # without ever being classified. (Fixed once already; got lost in a
    # subsequent edit that was built on a stale copy of this file — this
    # time verified against the live deployed source directly, not a local
    # copy, to close that gap.)
    return result, [it["id"] for it in batch]


VALID_CLASSES = {"DEVELOPMENT", "INCREMENT", "RECYCLED"}


def validate_diff_result(result, batch_ids, cluster_title=""):
    """Normalize the model's diff response into something safe to consume.

    Three schema-deviation bugs have now shipped from this one response
    shape — a truncated array, a non-dict top level, and item objects with
    no "id". Rather than defend field-by-field at each use site, everything
    the caller depends on is guaranteed HERE, once:

      - items is a list of dicts
      - every item has an "id" that was actually in the batch we sent
        (a hallucinated id would corrupt classes{} and seen_ids)
      - every item has a valid "class"
      - credits is a list, contradicts is a string

    Anything failing those checks is dropped with a log line rather than
    crashing the run or silently mis-classifying. Partial credit over total
    loss — the same principle as the truncation salvage.
    """
    if not isinstance(result, dict):
        return {"items": [], "ledger_updates": {}}, ["result was not an object"]

    problems = []
    valid_ids = set(batch_ids)
    clean = []
    for raw in result.get("items", []):
        if not isinstance(raw, dict):
            problems.append("item was not an object")
            continue
        iid = raw.get("id")
        if not iid or not isinstance(iid, str):
            problems.append(f"item missing id (class={raw.get('class', '?')})")
            continue
        if iid not in valid_ids:
            # The model invented or mangled an id. Trusting it would write a
            # bogus key into classes{} and mark an item seen that never was.
            problems.append(f"item id not in batch: {iid[:24]}")
            continue
        cls = raw.get("class")
        if cls not in VALID_CLASSES:
            problems.append(f"invalid class '{cls}' for {iid[:16]}")
            continue
        raw["credits"] = [c for c in (raw.get("credits") or []) if isinstance(c, str)]
        contra = raw.get("contradicts")
        raw["contradicts"] = contra if isinstance(contra, str) else ""
        for k in ("what_new", "unique"):
            if not isinstance(raw.get(k), str):
                raw[k] = ""
        clean.append(raw)

    updates = result.get("ledger_updates")
    if not isinstance(updates, dict):
        updates = {}
    return {"items": clean, "ledger_updates": updates}, problems


def _parse_json_lenient(text):
    """Parse Sonnet's JSON, repairing common escaping mistakes it makes.

    Sonnet occasionally emits smart quotes inside string values or leaves
    an internal double-quote unescaped. We try strict parse first, then a
    handful of narrow repairs; give up and raise if none work so the caller
    logs the diff as failed instead of silently mis-classifying.

    CRITICAL: json.loads() succeeding is not the same as getting the shape
    we asked for. A bare JSON string ("Nothing to report.") or a bare
    number parses without error and is perfectly valid JSON — but the
    caller does result.get("items"), which crashes on anything that isn't
    a dict. Every stage below is therefore gated on isinstance(_, dict);
    a non-dict success is treated the same as a parse failure and falls
    through to the next repair, so a model that deviates from the required
    schema produces a logged, caught failure instead of a crash.
    """
    def _as_dict(v):
        if isinstance(v, dict):
            return v
        raise json.JSONDecodeError(f"parsed to {type(v).__name__}, not an object", text, 0)

    try:
        return _as_dict(json.loads(text))
    except json.JSONDecodeError:
        pass
    # Repair 1: replace smart quotes that Sonnet sometimes uses inside strings
    # with plain straight quotes. This won't fix all cases (e.g. unescaped
    # internal straight quotes) but handles the most common failure mode.
    repaired = (text.replace("\u201c", '"').replace("\u201d", '"')
                    .replace("\u2018", "'").replace("\u2019", "'"))
    try:
        return _as_dict(json.loads(repaired))
    except json.JSONDecodeError:
        pass
    # Repair 2: strip trailing commas before ] or }
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    try:
        return _as_dict(json.loads(repaired))
    except json.JSONDecodeError:
        pass
    # Repair 3: whole-object extraction, if the object itself is intact
    m = re.search(r"\{.*\}", repaired, re.DOTALL)
    if m:
        try:
            return _as_dict(json.loads(m.group(0)))
        except json.JSONDecodeError:
            pass
    # Repair 4: the response was cut off mid-array (a raised max_tokens and a
    # capped batch size make this rare, not impossible). Salvage whatever
    # complete {...} objects appear before the truncation point rather than
    # discarding classifications the model actually finished — partial
    # credit over total loss, same principle as "judge on evidence."
    items_match = re.search(r'"items"\s*:\s*\[(.*)', repaired, re.DOTALL)
    if items_match:
        depth, start, objs = 0, None, []
        for i, ch in enumerate(items_match.group(1)):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        objs.append(json.loads(items_match.group(1)[start:i+1]))
                    except json.JSONDecodeError:
                        pass
        if objs:
            return {"items": objs, "ledger_updates": {}}
    raise json.JSONDecodeError("all repair attempts failed", text, 0)


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
    return {"items": out_items, "ledger_updates": updates}, [it["id"] for it in new_items]


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
            result, processed_ids = (mock_diff if mock else
                      lambda l, n, s: call_claude(api_key, l, n, s))(led, new_items, summaries)
        except Exception as e:
            log(f"  diff failed for '{cl['title'][:40]}': {type(e).__name__}: {e}")
            continue
        calls += 0 if mock else 1
        if len(processed_ids) < len(new_items):
            log(f"  batched: {len(processed_ids)}/{len(new_items)} new items for "
                f"'{cl['title'][:40]}' — remainder picked up next run")
        result, problems = validate_diff_result(result, processed_ids, cl.get("title", ""))
        for p in problems[:4]:
            log(f"  dropped malformed item for '{cl['title'][:34]}': {p}")
        processed_set = set(processed_ids)
        pub_by_id = {it["id"]: it.get("publisher", "") for it in new_items}
        for item_res in result.get("items", []):
            item_res["ledger_id"] = lid
            item_res["at"] = ts
            classes[item_res["id"]] = item_res
            for c in item_res.get("credits", []):
                if c and c not in led["credits"]:
                    led["credits"].append(c)
            # Contradictions are append-only and never rewritten — the same
            # immutability principle the canonical facts follow. A reversal is
            # part of the story's record, not a correction to be tidied away.
            contra = (item_res.get("contradicts") or "").strip()
            if contra:
                led.setdefault("contradictions", [])
                if not any(c["text"].lower() == contra.lower()
                           for c in led["contradictions"]):
                    led["contradictions"].append({
                        "at": ts, "item_id": item_res["id"],
                        "publisher": pub_by_id.get(item_res["id"], ""),
                        "text": contra})
        merge_facts(led, result.get("ledger_updates", {}), ts)
        # Only what was actually classified counts as seen. Overflow items
        # stay unseen and get diffed on the next run.
        led["seen_ids"] = list(set(led["seen_ids"]) | processed_set)

    # Annotate clusters.json for the Desk view
    dev_cut = now_utc() - timedelta(hours=DEV_RECENT_HOURS)
    for cl in clusters_payload["clusters"]:
        devs_recent = 0
        latest_dev_at = None  # timestamp of most recent DEVELOPMENT in window (for sort)
        state = ""
        for it in cl["items"]:
            res = classes.get(it["id"])
            if not res:
                it["ledger"] = None
                continue
            it["ledger"] = {"class": res["class"], "what_new": res.get("what_new", ""),
                            "unique": res.get("unique", ""), "credits": res.get("credits", [])}
            if res["class"] == "DEVELOPMENT":
                dev_ts = datetime.fromisoformat(res["at"])
                if dev_ts >= dev_cut:
                    devs_recent += 1
                if latest_dev_at is None or dev_ts > latest_dev_at:
                    latest_dev_at = dev_ts
            lid = res.get("ledger_id")
            if lid and lid in ledgers:
                state = ledgers[lid]["facts"]["state_of_play"]
        cl["developments_recent"] = devs_recent
        cl["latest_development_at"] = latest_dev_at.isoformat() if latest_dev_at else None
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
