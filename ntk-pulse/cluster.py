#!/usr/bin/env python3
"""NTK Pulse — Layer 2: Cluster.

Groups the 6-hour window into stories using the join logic proven in
the Desk's July 14 patch: TF-IDF cosine + required proper-noun entity
overlap, hard size ceiling, size-penalized bars for big clusters.

What is deliberately NOT here (vs. the Desk):
  - no cross-run persistence, no ledger, no DEVELOPMENT/INCREMENT diffs
  - no angle detection (the Angles pile is retired)
The window is 6 hours and stateless. Every run clusters from scratch.

Ranking (confirmed by Max, July 2026): blend of recency and consensus.
  pulse_score = publisher_count * 0.5 - hours_since_latest_item
Newest-and-most-covered rises; old or thin coverage sinks.

Stdlib only. Reads data/window.json, writes data/clusters.json.
"""
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"

# July 14 patch thresholds — carried forward verbatim. Do not retune casually.
SIM_THRESHOLD = 0.22      # cosine to join a cluster outright (headline-scale docs)
ENTITY_ASSIST = 0.12      # cosine floor when >=2 shared entity tokens
MERGE_THRESHOLD = 0.30    # centroid-vs-centroid cosine for the second-pass merge
MAX_CLUSTER_SIZE = 30     # hard ceiling — beyond this, we're accumulating a topic not an event
CENTROID_JOIN_BONUS = 12  # clusters larger than this require stricter joins (bar +50%)

# Ranking blend (Pulse Briefing v1, Q6, confirmed "blend")
DIVERSITY_WEIGHT = 0.5    # publishers are worth half an hour of freshness each

STOPWORDS = set("""a an and are as at be but by for from has have he her his i if in into is it its
of on or she that the their they this to was were will with you your we our not no new says said
after over more than about up out how what who when why""".split())


def log(msg):
    print(f"[cluster] {msg}", flush=True)


def stem(w):
    """Light suffix stemmer — enough to match headline inflections."""
    for suf, rep in (("ization", "iz"), ("izations", "iz"), ("ized", "iz"), ("izes", "iz"),
                     ("ize", "iz"), ("ational", "ate"), ("ations", "ate"), ("ation", "ate"),
                     ("ies", "y"), ("ing", ""), ("ers", "er"), ("ed", ""), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: len(w) - len(suf)] + rep
    return w


def tokenize(text):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [stem(w) for w in words if w not in STOPWORDS and len(w) > 2]


ENTITY_BLOCKLIST = set("""here here's there this that these those city council report reports
new news today yesterday tomorrow first second third last update updates live also here'
where when what why how who whom whose which world global national local state states
country countries government congress senate house president secretary official officials
top bottom fresh breaking latest exclusive analysis opinion editorial comment view
trump white house administration""".split())  # omnipresent names — not a distinguishing signal

# Common headline abbreviations that split clusters ("Fed" vs "Federal
# Reserve" share zero tokens otherwise). Conservative additive fix —
# expands the alias to its canonical tokens; thresholds untouched.
ENTITY_ALIASES = {
    "fed": {"federal", "reserv"},
    "feds": {"federal", "reserv"},
    "scotus": {"supreme", "court"},
    "gop": {"republican"},
    "dems": {"democrat"},
    "dem": {"democrat"},
}


def entities(title, summary=""):
    """Capitalized tokens from the title AND summary — cheap named-entity proxy.

    Token-level so 'US Supreme Court' and 'Supreme Court' share {'supreme','court'}.
    Keeps sentence-initial proper nouns provided the word isn't a generic
    in ENTITY_BLOCKLIST.

    Reads summary too, not just title (July 21 indie-clustering test): wire
    headlines front-load entities by convention; many indie headlines
    (datelines, literary titles) don't, even when the body plainly does.
    """
    combined = title + " " + (summary or "")
    tokens = re.findall(r"[A-Za-z][a-zA-Z0-9''\.]+", combined)
    ents = set()
    for tok in tokens:
        if not tok[0].isupper():
            continue
        low = tok.lower()
        for suf in ("'s", "\u2019s", "'", "\u2019", "\u2018"):
            if low.endswith(suf):
                low = low[: -len(suf)]
        low = low.rstrip(".")
        if low in ENTITY_ALIASES:
            ents |= {stem(t) for t in ENTITY_ALIASES[low]}
            continue
        if low in STOPWORDS or low in ENTITY_BLOCKLIST or len(low) < 3:
            continue
        ents.add(stem(low))
    return ents


def ts(item, now):
    raw = item.get("published") or item.get("first_seen")
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return now


def build_vectors(items):
    docs = {it["id"]: Counter(tokenize(it["title"] + " " + it.get("summary", ""))) for it in items}
    df = Counter()
    for tf in docs.values():
        df.update(tf.keys())
    n = max(len(docs), 1)
    idf = {t: math.log(n / (1 + c)) + 1 for t, c in df.items()}
    vecs = {}
    for iid, tf in docs.items():
        v = {t: (1 + math.log(c)) * idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs[iid] = {t: x / norm for t, x in v.items()}
    return vecs


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def centroid(vec_list):
    agg = defaultdict(float)
    for v in vec_list:
        for t, x in v.items():
            agg[t] += x
    norm = math.sqrt(sum(x * x for x in agg.values())) or 1.0
    return {t: x / norm for t, x in agg.items()}


# Feed-level beat hints. Haiku triage supplies the authoritative beat tag;
# this is the fallback shown before/without a triage verdict.
MARKET_BEAT = {"intl": "international"}


def beat_hint(members, feeds_by_id):
    votes = Counter()
    for m in members:
        f = feeds_by_id.get(m["publisher"], {})
        beat = f.get("beat") or MARKET_BEAT.get(m.get("market", ""), "national")
        votes[beat] += 1
    return votes.most_common(1)[0][0] if votes else "national"


def main():
    now = datetime.now(timezone.utc)
    window = json.loads((DATA / "window.json").read_text())
    feeds_by_id = {f["id"]: f for f in json.loads((ROOT / "feeds.json").read_text())["feeds"]}
    items = sorted(window["items"].values(), key=lambda it: ts(it, now))
    if not items:
        log("Window empty; nothing to cluster.")
        (DATA / "clusters.json").write_text(json.dumps({"updated": now.isoformat(), "clusters": []}))
        return

    vecs = build_vectors(items)
    ents = {it["id"]: entities(it["title"], it.get("summary","")) for it in items}

    clusters = []  # each: {"ids": [...], "centroid": vec, "entities": set}
    for it in items:
        iid = it["id"]
        best, best_sim = None, 0.0
        for cl in clusters:
            if len(cl["ids"]) >= MAX_CLUSTER_SIZE:
                continue
            sim = cosine(vecs[iid], cl["centroid"])
            shared = len(ents[iid] & cl["entities"])
            size_penalty = 1.5 if len(cl["ids"]) >= CENTROID_JOIN_BONUS else 1.0
            # At least one shared proper-noun entity required for any join
            # (the Costco/Israel lesson). More shared entities lower the bar.
            joins = (shared >= 1 and sim >= ENTITY_ASSIST * size_penalty) or \
                    (shared >= 2 and sim >= ENTITY_ASSIST * 0.7 * size_penalty)
            if joins and sim > best_sim:
                best, best_sim = cl, sim
        if best:
            best["ids"].append(iid)
            best["centroid"] = centroid([vecs[i] for i in best["ids"]])
            best["entities"] |= ents[iid]
        else:
            clusters.append({"ids": [iid], "centroid": dict(vecs[iid]), "entities": set(ents[iid])})

    # Second pass: merge clusters the greedy order split apart.
    merged = True
    while merged:
        merged = False
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                a, b = clusters[i], clusters[j]
                if len(a["ids"]) + len(b["ids"]) > MAX_CLUSTER_SIZE:
                    continue
                sim = cosine(a["centroid"], b["centroid"])
                shared = len(a["entities"] & b["entities"])
                if (shared >= 1 and sim >= MERGE_THRESHOLD) or \
                   (shared >= 2 and sim >= ENTITY_ASSIST):
                    a["ids"] += b["ids"]
                    a["centroid"] = centroid([vecs[x] for x in a["ids"]])
                    a["entities"] |= b["entities"]
                    del clusters[j]
                    merged = True
                    break
            if merged:
                break

    by_id = {it["id"]: it for it in items}
    out = []
    members_by_key = {}
    for cl in clusters:
        members = [by_id[i] for i in cl["ids"]]
        times = [ts(m, now) for m in members]
        latest = max(times)
        latest_age_h = max((now - latest).total_seconds() / 3600, 0.0)
        pubs = []  # publisher display names, tier order, deduped
        seen = set()
        for m in sorted(members, key=lambda m: (m["tier"], m["publisher_name"])):
            if m["publisher"] not in seen:
                seen.add(m["publisher"])
                pubs.append(m["publisher_name"])
        # Representative title: prefer English, then lowest tier, then earliest.
        def rep_sort_key(mt):
            member = mt[0]
            lang_penalty = 0 if member.get("language", "en") == "en" else 1
            return (lang_penalty, member["tier"], mt[1])
        rep = sorted(zip(members, times), key=rep_sort_key)[0][0]
        members_by_key[rep["id"]] = members
        pulse_score = len(pubs) * DIVERSITY_WEIGHT - latest_age_h
        out.append({
            "key": rep["id"],
            "title": rep["title"],
            "size": len(members),
            "publishers": pubs,
            "publisher_count": len(pubs),
            "latest": latest.isoformat(),
            "latest_age_hours": round(latest_age_h, 2),
            "pulse_score": round(pulse_score, 3),
            "beat_hint": beat_hint(members, feeds_by_id),
            "entities": sorted(cl["entities"])[:40],
            "items": [{
                "id": m["id"], "title": m["title"], "url": m["url"],
                "publisher": m["publisher_name"],
                "published": m.get("published"),
            } for m, _ in sorted(zip(members, times), key=lambda mt: mt[1], reverse=True)],
        })

    # Echo detection: a cluster with at least one origin:"indie" item AND at
    # least one non-indie item is flagged. Purely additive — a label on
    # clusters the join logic already built, never a change to scoring.
    for c in out:
        origins = {feeds_by_id.get(m["publisher"], {}).get("origin", "rss") for m in members_by_key.get(c["key"], [])}
        c["echo"] = bool(("indie" in origins) and (origins - {"indie"}))

    out.sort(key=lambda c: c["pulse_score"], reverse=True)
    payload = {"updated": now.isoformat(), "window_items": len(items), "clusters": out}
    (DATA / "clusters.json").write_text(json.dumps(payload, indent=1))
    multi = sum(1 for c in out if c["publisher_count"] > 1)
    log(f"{len(items)} items -> {len(out)} clusters ({multi} multi-publisher).")


if __name__ == "__main__":
    main()
