#!/usr/bin/env python3
"""NTK Desk — Layer 2: Cluster.

Groups the 48-hour window into stories using TF-IDF cosine similarity
plus named-entity overlap, then scores each cluster on the two signals
EventRegistry doesn't give you:

  velocity  — distinct publishers picking the story up in the last 6h
              (the homegrown Memeorandum signal: discussion, not volume)
  diversity — distinct publishers across the cluster's life
              (five wire rewrites = commodity; varied outlets = story)

Also flags the ANGLE candidate per cluster: the item whose vector sits
farthest from the cluster centroid while still belonging to the cluster —
almost by definition, the distinctive take.

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

SIM_THRESHOLD = 0.22      # cosine to join a cluster outright (headline-scale docs)
ENTITY_ASSIST = 0.12      # cosine floor when >=2 shared entity tokens
MERGE_THRESHOLD = 0.30    # centroid-vs-centroid cosine for the second-pass merge
RECENT_HOURS = 6

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


def entities(title):
    """Capitalized tokens from the title — cheap named-entity proxy.

    Token-level (not run-level) so 'US Supreme Court' and 'Supreme Court'
    share {'supreme', 'court'}. Drops the sentence-case first word and
    stopword-ish capitals.
    """
    tokens = re.findall(r"[A-Za-z][a-zA-Z0-9''\.]+", title)
    ents = set()
    for i, tok in enumerate(tokens):
        if not tok[0].isupper():
            continue
        low = tok.lower().rstrip(".'")
        # Drop the sentence-case first word — unless it opens a proper-noun
        # phrase (next token also capitalized: "Supreme Court ...").
        leads_phrase = i + 1 < len(tokens) and tokens[i + 1][0].isupper()
        if (i == 0 and not leads_phrase) or low in STOPWORDS or len(low) < 3:
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


def main():
    now = datetime.now(timezone.utc)
    window = json.loads((DATA / "window.json").read_text())
    items = sorted(window["items"].values(), key=lambda it: ts(it, now))
    if not items:
        log("Window empty; nothing to cluster.")
        (DATA / "clusters.json").write_text(json.dumps({"updated": now.isoformat(), "clusters": []}))
        return

    vecs = build_vectors(items)
    ents = {it["id"]: entities(it["title"]) for it in items}

    clusters = []  # each: {"ids": [...], "centroid": vec, "entities": set}
    for it in items:
        iid = it["id"]
        best, best_sim = None, 0.0
        for cl in clusters:
            sim = cosine(vecs[iid], cl["centroid"])
            shared = len(ents[iid] & cl["entities"])
            joins = sim >= SIM_THRESHOLD or (shared >= 2 and sim >= ENTITY_ASSIST)
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
                sim = cosine(a["centroid"], b["centroid"])
                shared = len(a["entities"] & b["entities"])
                if sim >= MERGE_THRESHOLD or (shared >= 2 and sim >= ENTITY_ASSIST):
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
    for cl in clusters:
        members = [by_id[i] for i in cl["ids"]]
        times = [ts(m, now) for m in members]
        age_h = max((now - min(times)).total_seconds() / 3600, 0.1)
        pubs_all = {m["publisher"] for m in members}
        pubs_recent = {m["publisher"] for m, t in zip(members, times)
                       if (now - t).total_seconds() <= RECENT_HOURS * 3600}
        # Angle: farthest-from-centroid member that still belongs (clusters of 3+)
        angle = None
        if len(members) >= 3:
            dists = [(1 - cosine(vecs[m["id"]], cl["centroid"]), m["id"]) for m in members]
            dists.sort(reverse=True)
            angle = dists[0][1]
        # Representative title: from the earliest tier-1 item, else earliest
        members_sorted = sorted(zip(members, times), key=lambda mt: (mt[0]["tier"], mt[1]))
        rep = members_sorted[0][0]
        markets = sorted({m["market"] for m in members})
        out.append({
            "key": rep["id"],
            "title": rep["title"],
            "size": len(members),
            "diversity": len(pubs_all),
            "velocity": len(pubs_recent),
            "age_hours": round(age_h, 1),
            "markets": markets,
            "score": len(pubs_recent) * 3 + len(pubs_all),
            "angle_id": angle,
            "entities": sorted(cl["entities"])[:40],
            "items": [{
                "id": m["id"], "title": m["title"], "url": m["url"],
                "publisher": m["publisher_name"], "market": m["market"],
                "published": m.get("published"),
                "is_angle": m["id"] == angle,
            } for m, _ in sorted(zip(members, times), key=lambda mt: mt[1], reverse=True)],
        })

    out.sort(key=lambda c: c["score"], reverse=True)
    payload = {"updated": now.isoformat(), "window_items": len(items), "clusters": out}
    (DATA / "clusters.json").write_text(json.dumps(payload, indent=1))
    multi = sum(1 for c in out if c["size"] > 1)
    log(f"{len(items)} items -> {len(out)} clusters ({multi} multi-source).")


if __name__ == "__main__":
    main()
