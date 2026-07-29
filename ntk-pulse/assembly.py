#!/usr/bin/env python3
"""NTK Pulse — Layer 5: Digest Assembly.

Implements the Digest Assembly & Mix Rubric. This is the layer that decides
what the edition IS, as opposed to what the stream contains.

The problem it exists to solve, stated plainly: publisher_count is
simultaneously the quality signal and a catastrophe filter. Wire services
converge on disaster; a first-in-class drug approval, a school phone-ban
result, or a piece of genuine wonder gets covered once. Sorting by
corroboration therefore produces a digest that is accurate, defensible, and
grim every single day. Assembly fixes that by filling SLOTS and enforcing
SET CONSTRAINTS rather than taking the top N off a ranked list.

Two slot plans, switchable, meant to be A/B tested:

  PLAN A (rubric §3) — slots by reader relationship: Unavoidable, Money & me,
    Body & mind, Work & machines, The group chat, Elsewhere but here, Flex,
    The close.

  PLAN B (Standing Lineup v0.4 R16) — 4 hard news + 4 reserved drawn from
    science / health / tech / longevity / parenting.

Set constraints run AFTER slot filling and do the real editorial work — the
doom-stack cap in particular is the direct fix for "this mix is depressing."

Reads  data/clusters.json  (needs triage scores; ledger annotations optional)
Writes data/lineup.json    (the edition, plus a full audit trail)

Stdlib only. No API calls — every judgment used here was already made and
paid for upstream in triage.py and ledger.py.
"""
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"

# ── config: the A/B switches ──
SLOT_PLAN = os.environ.get("NTK_SLOT_PLAN", "A").upper()          # "A" | "B"
DISPLACEMENT = os.environ.get("NTK_DISPLACEMENT", "MANUAL").upper()  # "AUTO" | "MANUAL"

# ── edition sizing (rubric §7, amended by Max: weekends/holidays 4–6) ──
SIZE_WEEKDAY = (8, 10)
SIZE_WEEKEND = (4, 6)
SIZE_HOLIDAY = (4, 6)

# Drop order when the edition shrinks below the slot floor. Last three
# standing are Unavoidable, Body & mind, The close.
PLAN_A_DROP_ORDER = ["elsewhere", "work_machines", "group_chat", "money_me"]

# ── set constraints (rubric §5) ──
MAX_HIGH_EMOTION = 2        # items with emotional_load >= 4
MAX_PER_TOPIC = 2           # items sharing dominant entities
MIN_EXPLAINABLE = 3         # items with explainability == 5
MIN_NON_POLITICIAN = 2      # items whose primary actor isn't a politician
MIN_ACTIONABLE = 1          # items with actionability >= 4
HIGH_EMOTION_FLOOR = 4


def log(m):
    print(f"[assembly] {m}", flush=True)


# ── US market holidays: "banks and markets closed, or a half day" (A11) ──
# NYSE calendar. Hand-listed rather than computed — a wrong holiday is a
# wrong-sized edition, and a two-year table is cheaper than a date library.
MARKET_HOLIDAYS = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-11-27",
    "2026-12-24", "2026-12-25",
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
    "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-11-26",
    "2027-12-24",
}


def edition_size(now):
    d = now.date()
    if d.isoformat() in MARKET_HOLIDAYS:
        return SIZE_HOLIDAY, "holiday"
    if now.weekday() >= 5:
        return SIZE_WEEKEND, "weekend"
    return SIZE_WEEKDAY, "weekday"


def tri(c, key, default=3):
    t = c.get("triage") or {}
    v = t.get(key, default)
    return default if v is None else v


def beat_of(c):
    t = c.get("triage") or {}
    return t.get("beat") or c.get("beat_hint") or "other"


def ledger_class(c):
    """Worst-case classification across the cluster's items.

    A cluster containing at least one DEVELOPMENT is developing. One with
    items classified but none of them DEVELOPMENT is an increment — exactly
    what set constraint #6 exists to exclude. Unclassified returns None so
    a story is never rejected merely because the ledger hasn't reached it.
    """
    seen = [it.get("ledger", {}).get("class") for it in c.get("items", [])
            if it.get("ledger")]
    if not seen:
        return None
    if "DEVELOPMENT" in seen:
        return "DEVELOPMENT"
    if "INCREMENT" in seen:
        return "INCREMENT"
    return "RECYCLED"


def new_facts(c):
    """The material behind 'N new facts since you last looked' (rubric §10)."""
    out = []
    for it in c.get("items", []):
        l = it.get("ledger") or {}
        if l.get("class") == "DEVELOPMENT" and l.get("what_new"):
            if l["what_new"] not in out:
                out.append(l["what_new"])
    return out


# ── slot definitions ──
def slot_defs(plan):
    if plan == "B":
        # Standing Lineup v0.4 R16
        return [
            {"id": "hard1", "label": "Hard news", "min": 1, "max": 1, "test": t_hard},
            {"id": "hard2", "label": "Hard news", "min": 1, "max": 1, "test": t_hard},
            {"id": "hard3", "label": "Hard news", "min": 1, "max": 1, "test": t_hard},
            {"id": "hard4", "label": "Hard news", "min": 1, "max": 1, "test": t_hard},
            {"id": "res1", "label": "Reserved", "min": 1, "max": 1, "test": t_reserved},
            {"id": "res2", "label": "Reserved", "min": 1, "max": 1, "test": t_reserved},
            {"id": "res3", "label": "Reserved", "min": 1, "max": 1, "test": t_reserved},
            {"id": "res4", "label": "Reserved", "min": 1, "max": 1, "test": t_reserved},
        ]
    return [
        {"id": "unavoidable", "label": "Unavoidable", "min": 1, "max": 3, "test": t_unavoidable},
        {"id": "money_me", "label": "Money & me", "min": 1, "max": 1, "test": t_money},
        {"id": "body_mind", "label": "Body & mind", "min": 1, "max": 1, "test": t_body},
        {"id": "work_machines", "label": "Work & machines", "min": 1, "max": 1, "test": t_work},
        {"id": "group_chat", "label": "The group chat", "min": 1, "max": 1, "test": t_culture},
        {"id": "elsewhere", "label": "Elsewhere, but here", "min": 1, "max": 1, "test": t_intl},
        {"id": "flex", "label": "Flex", "min": 0, "max": 2, "test": t_any},
        {"id": "close", "label": "The close", "min": 1, "max": 1, "test": t_close},
    ]


# ── inclusion tests ──
def t_unavoidable(c):
    return tri(c, "conversational_currency") >= 4 or c["publisher_count"] >= 6


def t_money(c):
    return beat_of(c) == "business" or tri(c, "actionability") >= 4


def t_body(c):
    return beat_of(c) in ("health", "science", "longevity")


def t_work(c):
    return beat_of(c) == "tech"


def t_culture(c):
    return beat_of(c) in ("culture", "parenting", "education")


def t_intl(c):
    return beat_of(c) == "international"


def t_close(c):
    """Something that resolves, and doesn't cost the reader anything to carry."""
    return tri(c, "emotional_load") <= 2


def t_any(c):
    return True


def t_hard(c):
    return beat_of(c) in ("national", "international", "business")


def t_reserved(c):
    return beat_of(c) in ("science", "health", "tech", "longevity", "parenting")


# ── scoring ──
def score(c):
    """Ranking within a slot.

    Deliberately NOT publisher_count-dominant. Corroboration still counts,
    but conversational currency and actionability count as much, which is
    what lets a single-publisher ADHD approval beat a fifteen-publisher
    process story for the Body & mind slot.
    """
    base = c.get("pulse_score", 0.0)
    facts = len(new_facts(c))
    return (base
            + facts * 1.5
            + tri(c, "conversational_currency") * 0.6
            + tri(c, "actionability") * 0.4
            + tri(c, "explainability") * 0.3)


def topic_key(c):
    """Crude topic identity for the max-2-per-topic rule: top shared entities."""
    return tuple(sorted(c.get("entities", []))[:4])


def eligible(c):
    """Hard exclusions applied before any slot sees a candidate."""
    if (c.get("triage") or {}).get("verdict") == "NO":
        return False, "triage verdict NO"
    lc = ledger_class(c)
    if lc in ("INCREMENT", "RECYCLED"):
        return False, f"ledger: {lc}"      # set constraint #6
    return True, ""


def assemble(clusters, size_range, plan):
    lo, hi = size_range
    defs = slot_defs(plan)

    # shrink the plan to fit the edition ceiling
    if plan == "A":
        floor = sum(s["min"] for s in defs)
        drop = list(PLAN_A_DROP_ORDER)
        while floor > hi and drop:
            gone = drop.pop(0)
            defs = [s for s in defs if s["id"] != gone]
            floor = sum(s["min"] for s in defs)

    pool = []
    rejected = []
    for c in clusters:
        ok, why = eligible(c)
        (pool if ok else rejected).append(c if ok else {"title": c["title"], "why": why})
    pool.sort(key=score, reverse=True)

    chosen, used, topics = [], set(), {}

    def can_take(c):
        if c["key"] in used:
            return False, "already used"
        tk = topic_key(c)
        if tk and topics.get(tk, 0) >= MAX_PER_TOPIC:
            return False, "topic cap"
        if tri(c, "emotional_load") >= HIGH_EMOTION_FLOOR and \
           sum(1 for x in chosen if tri(x["cluster"], "emotional_load") >= HIGH_EMOTION_FLOOR) >= MAX_HIGH_EMOTION:
            return False, "doom-stack cap"
        return True, ""

    def take(c, slot):
        used.add(c["key"])
        tk = topic_key(c)
        if tk:
            topics[tk] = topics.get(tk, 0) + 1
        chosen.append({"slot": slot["id"], "slot_label": slot["label"], "cluster": c})

    # pass 1 — every slot's minimum
    for s in defs:
        for _ in range(s["min"]):
            for c in pool:
                if not s["test"](c):
                    continue
                ok, _why = can_take(c)
                if ok:
                    take(c, s)
                    break

    # pass 2 — fill toward the target using slot maxima, then flex on merit
    # (rubric §7 merit fallback: an unfillable reserved slot yields to the
    # next best candidate rather than forcing a weak story in)
    for s in defs:
        already = sum(1 for x in chosen if x["slot"] == s["id"])
        while already < s["max"] and len(chosen) < hi:
            picked = None
            for c in pool:
                if not s["test"](c):
                    continue
                ok, _ = can_take(c)
                if ok:
                    picked = c
                    break
            if not picked:
                break
            take(picked, s)
            already += 1

    return chosen, defs, rejected


def lint(chosen):
    """Rubric §11 — reasons to fail the edition. Reported, never auto-enforced;
    the editor sees the failure and decides."""
    fails = []
    cl = [x["cluster"] for x in chosen]
    if not cl:
        return ["empty edition"]

    doom = [c for c in cl if tri(c, "emotional_load") >= HIGH_EMOTION_FLOOR]
    if len(doom) > MAX_HIGH_EMOTION:
        fails.append(f"doom stack: {len(doom)} items at emotional load {HIGH_EMOTION_FLOOR}+ (max {MAX_HIGH_EMOTION})")

    if sum(1 for c in cl if tri(c, "explainability") == 5) < min(MIN_EXPLAINABLE, len(cl)):
        fails.append(f"under {MIN_EXPLAINABLE} fully self-contained items")

    nonpol = sum(1 for c in cl if not (c.get("triage") or {}).get("politician_led"))
    if nonpol < min(MIN_NON_POLITICIAN, len(cl)):
        fails.append(f"only {nonpol} items not led by a politician (min {MIN_NON_POLITICIAN})")

    if not any(tri(c, "actionability") >= 4 for c in cl):
        fails.append("no item answers 'what do I do with this'")

    beats = [beat_of(c) for c in cl]
    if beats.count("national") == len(cl):
        fails.append("all-Washington lineup")

    tk = {}
    for c in cl:
        k = topic_key(c)
        if k:
            tk[k] = tk.get(k, 0) + 1
    for k, n in tk.items():
        if n > MAX_PER_TOPIC:
            fails.append(f"{n} items on one topic (max {MAX_PER_TOPIC})")

    for c in cl:
        if ledger_class(c) in ("INCREMENT", "RECYCLED"):
            fails.append(f"increment served: {c['title'][:40]}")
    return fails


def main():
    now = datetime.now(timezone.utc)
    payload = json.loads((DATA / "clusters.json").read_text())
    clusters = payload.get("clusters", [])
    (lo, hi), daytype = edition_size(now)
    plan = SLOT_PLAN if SLOT_PLAN in ("A", "B") else "A"

    chosen, defs, rejected = assemble(clusters, (lo, hi), plan)
    fails = lint(chosen)

    edition = {
        "assembled_at": now.isoformat(),
        "slot_plan": plan,
        "displacement": DISPLACEMENT,
        "daytype": daytype,
        "target_size": [lo, hi],
        "actual_size": len(chosen),
        "lint_failures": fails,
        "slots_unfilled": [s["label"] for s in defs
                           if not any(x["slot"] == s["id"] for x in chosen) and s["min"] > 0],
        "stories": [{
            "slot": x["slot"], "slot_label": x["slot_label"],
            "key": x["cluster"]["key"], "title": x["cluster"]["title"],
            "beat": beat_of(x["cluster"]),
            "publisher_count": x["cluster"]["publisher_count"],
            "publishers": x["cluster"].get("publishers", []),
            "scores": {k: tri(x["cluster"], k) for k in
                       ("emotional_load", "explainability", "actionability",
                        "conversational_currency")},
            "politician_led": (x["cluster"].get("triage") or {}).get("politician_led", False),
            "ledger_class": ledger_class(x["cluster"]),
            "new_facts": new_facts(x["cluster"]),
            "line": (x["cluster"].get("triage") or {}).get("line", ""),
            "assembly_score": round(score(x["cluster"]), 2),
        } for x in chosen],
        # Killed-pile principle: what was excluded, and why, stays visible.
        "excluded_sample": rejected[:40],
    }
    (DATA / "lineup.json").write_text(json.dumps(edition, indent=1))
    log(f"plan {plan} · {daytype} · {len(chosen)} stories (target {lo}-{hi})")
    if edition["slots_unfilled"]:
        log(f"  unfilled: {', '.join(edition['slots_unfilled'])}")
    for f in fails:
        log(f"  LINT: {f}")
    return edition


if __name__ == "__main__":
    main()
