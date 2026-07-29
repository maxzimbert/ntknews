#!/usr/bin/env python3
"""NTK Pulse — Layer 2: Cluster (v2, experimental).

Three changes from the live cluster.py, all aimed at under-segmentation
(mega-clusters that glue distinct stories together):

  FIX 1 — IDF-WEIGHTED ENTITIES. The live join gate counts shared entities:
    one shared entity + cosine >= 0.12 joins. But "iran" appears in ~200 of
    today's articles and "Muwaffaq Salti" in 3, and the gate treats them as
    equal evidence. v2 weights each shared entity by its rarity, so a shared
    obscure name is strong evidence and a shared ubiquitous one is nearly
    none. This subsumes the hand-added "trump/white house" blocklist —
    rarity is measured fresh every run instead of maintained by hand.

  FIX 2 — COHESION SPLIT. After clustering, check whether a cluster's
    internal similarity is unimodal. A real single-story cluster is tight;
    a glued-together one shows two dense lumps with a gap between them.
    Where the gap is real, split it. Structural, not tuned to a topic.

  FIX 3 — BRIDGE DETECTION. An article roughly equidistant from two strong
    centroids — high similarity to both, clearly nearer neither — is a piece
    genuinely about both stories. Today it gets force-assigned to whichever
    it's 0.01 closer to. v2 pulls these out into their own cluster, which is
    an editorial primitive, not just cleanup.

Stdlib only. Same I/O contract as cluster.py.
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── thresholds carried from the live cluster.py ──
ENTITY_ASSIST = 0.12
MERGE_THRESHOLD = 0.30
MAX_CLUSTER_SIZE = 30
CENTROID_JOIN_BONUS = 12
DIVERSITY_WEIGHT = 0.5

# ── v2 thresholds ──
# Entity evidence is the summed IDF of shared entities, expressed as a
# fraction of the max possible for the smaller entity set. A shared rare
# name clears this easily; a shared "iran" does not.
ENTITY_EVIDENCE_MIN = 0.28
SPLIT_MIN_SIZE = 8          # don't bother trying to split small clusters
SPLIT_GAP_MIN = 0.55        # how much better the 2-way split must be
BRIDGE_MIN_SIM = 0.14       # must be genuinely close to both
BRIDGE_RATIO_MIN = 0.80     # sim to 2nd-best / sim to best

# ── FIX 4: velocity ──
# Yahoo's "Alike" watched article-volume velocity and social chatter; our
# ranking only ever saw a static snapshot (publisher_count + recency), so a
# story going 2→12 publishers in an hour scored the same as one sitting at
# 12 all day. This computes acceleration from arrival timestamps WITHIN the
# existing window — no cross-run state, no new API calls.
VELOCITY_TAIL = 0.25        # "recent" = last quarter of the window (1.5h of 6h)
VELOCITY_WEIGHT = 0.5       # how hard velocity pushes, as a fraction of the
                            # diversity term. 0.5 => at most ±25% of pubs*0.5.
VELOCITY_CLAMP = 3.0        # cap the raw ratio so a 2-publisher burst can't dominate
BREAKING_MIN = 1.35         # relative-to-median velocity to call something breaking

# NOTE on the null hypothesis: uniform arrival is NOT the right baseline.
# The window always ends "now" (whenever the pipeline ran) and RSS polling
# bunches arrivals near poll time, so on real data the median cluster scores
# ~1.6 against a uniform null — i.e. almost everything looks like it's
# accelerating, which makes the signal useless. Velocity is therefore
# normalized against the median cluster IN THE SAME RUN: self-calibrating,
# adapts to each window's shape, and 1.0 always means "typical for today."

STOPWORDS = set("""a an and are as at be but by for from has have he her his i if in into is it its
of on or she that the their they this to was were will with you your we our not no new says said
after over more than about up out how what who when why""".split())

ENTITY_BLOCKLIST = set("""here here's there this that these those city council report reports
new news today yesterday tomorrow first second third last update updates live also here'
where when what why how who whom whose which world global national local state states
country countries government congress senate house president secretary official officials
top bottom fresh breaking latest exclusive analysis opinion editorial comment view""".split())

ENTITY_ALIASES = {
    "fed": {"federal", "reserv"}, "feds": {"federal", "reserv"},
    "scotus": {"supreme", "court"}, "gop": {"republican"},
    "dems": {"democrat"}, "dem": {"democrat"},
}


def stem(w):
    for suf, rep in (("ization", "iz"), ("izations", "iz"), ("ized", "iz"), ("izes", "iz"),
                     ("ize", "iz"), ("ational", "ate"), ("ations", "ate"), ("ation", "ate"),
                     ("ies", "y"), ("ing", ""), ("ers", "er"), ("ed", ""), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: len(w) - len(suf)] + rep
    return w


def tokenize(text):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [stem(w) for w in words if w not in STOPWORDS and len(w) > 2]


def entities(title, summary=""):
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


# ── FIX 1: entity IDF ──
# Feed-level beat hints. Haiku triage supplies the authoritative beat tag;
# this is the fallback shown before/without a triage verdict. Dropped by
# accident in the first v2 draft — restoring it, since pulse.html renders
# beat badges from it and assembly.py falls back to it for slot tests.
MARKET_BEAT = {"intl": "international"}


def beat_hint(members, feeds_by_id):
    from collections import Counter as _C
    votes = _C()
    for m in members:
        f = feeds_by_id.get(m["publisher"], {})
        votes[f.get("beat") or MARKET_BEAT.get(m.get("market", ""), "national")] += 1
    return votes.most_common(1)[0][0] if votes else "national"


def build_entity_idf(ents_by_id):
    """Rarity weight per entity. 'iran' in 200 headlines ≈ 0; a name in 3 ≈ high."""
    df = Counter()
    for ents in ents_by_id.values():
        df.update(ents)
    n = max(len(ents_by_id), 1)
    return {e: math.log(n / (1 + c)) for e, c in df.items()}


def entity_evidence(a_ents, b_ents, eidf):
    """Shared-entity evidence in [0,1], weighted by rarity.

    Normalized against the smaller set's total weight so that a small,
    precise headline isn't penalized for having fewer entities than a
    sprawling one.
    """
    shared = a_ents & b_ents
    if not shared:
        return 0.0, shared
    shared_w = sum(eidf.get(e, 1.0) for e in shared)
    a_w = sum(eidf.get(e, 1.0) for e in a_ents) or 1.0
    b_w = sum(eidf.get(e, 1.0) for e in b_ents) or 1.0
    return shared_w / min(a_w, b_w), shared


# ── FIX 2: cohesion split ──
def try_split(ids, vecs, depth=0):
    """2-means on the cluster's own vectors; keep the split only if the two
    halves are genuinely far apart relative to their internal tightness.
    Recurses so a 3-story pileup separates fully."""
    if len(ids) < SPLIT_MIN_SIZE or depth > 2:
        return [ids]

    # seed on the two least-similar members
    worst, seeds = 2.0, None
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            s = cosine(vecs[ids[i]], vecs[ids[j]])
            if s < worst:
                worst, seeds = s, (ids[i], ids[j])
    if not seeds:
        return [ids]

    a_seed, b_seed = seeds
    for _ in range(6):
        ca, cb = vecs[a_seed] if isinstance(a_seed, str) else a_seed, \
                 vecs[b_seed] if isinstance(b_seed, str) else b_seed
        A, B = [], []
        for iid in ids:
            (A if cosine(vecs[iid], ca) >= cosine(vecs[iid], cb) else B).append(iid)
        if not A or not B:
            return [ids]
        a_seed = centroid([vecs[i] for i in A])
        b_seed = centroid([vecs[i] for i in B])

    # Is the split real? Compare cross-group similarity against within-group.
    ca = centroid([vecs[i] for i in A])
    cb = centroid([vecs[i] for i in B])
    cross = cosine(ca, cb)
    within_a = sum(cosine(vecs[i], ca) for i in A) / len(A)
    within_b = sum(cosine(vecs[i], cb) for i in B) / len(B)
    within = (within_a + within_b) / 2
    if within <= 0:
        return [ids]

    # A real gap: the halves cohere much better internally than across.
    if cross / within < SPLIT_GAP_MIN and len(A) >= 2 and len(B) >= 2:
        return try_split(A, vecs, depth + 1) + try_split(B, vecs, depth + 1)
    return [ids]


def velocity(members, times, window_start, window_end):
    """Acceleration inside the window, publisher-level.

    Compares publishers filing in the recent tail against what a uniform
    arrival rate would predict. >1 accelerating, <1 decaying, 1 steady.
    Publisher-level rather than item-level so one outlet filing five updates
    doesn't read as a surge.
    """
    span = (window_end - window_start).total_seconds()
    if span <= 0:
        return 1.0
    cutoff = window_end.timestamp() - span * VELOCITY_TAIL
    recent_pubs, all_pubs = set(), set()
    for m, t in zip(members, times):
        all_pubs.add(m["publisher"])
        if t.timestamp() >= cutoff:
            recent_pubs.add(m["publisher"])
    if not all_pubs:
        return 1.0
    expected = len(all_pubs) * VELOCITY_TAIL
    if expected <= 0:
        return 1.0
    return min(len(recent_pubs) / expected, VELOCITY_CLAMP)


ROOT_DIR = Path(__file__).parent


def main(data_dir, out_name="clusters_v2.json", verbose=True):
    DATA = Path(data_dir)
    now = datetime.now(timezone.utc)
    window = json.loads((DATA / "window.json").read_text())
    try:
        feeds_by_id = {f["id"]: f for f in
                       json.loads((ROOT_DIR / "feeds.json").read_text())["feeds"]}
    except Exception:
        feeds_by_id = {}

    def ts(item):
        raw = item.get("published") or item.get("first_seen")
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return now

    items = sorted(window["items"].values(), key=ts)
    vecs = build_vectors(items)
    ents = {it["id"]: entities(it["title"], it.get("summary", "")) for it in items}
    eidf = build_entity_idf(ents)

    # ── pass 1: greedy join, gated on IDF-weighted entity evidence ──
    clusters = []
    for it in items:
        iid = it["id"]
        best, best_sim = None, 0.0
        for cl in clusters:
            if len(cl["ids"]) >= MAX_CLUSTER_SIZE:
                continue
            sim = cosine(vecs[iid], cl["centroid"])
            ev, _ = entity_evidence(ents[iid], cl["entities"], eidf)
            size_penalty = 1.5 if len(cl["ids"]) >= CENTROID_JOIN_BONUS else 1.0
            joins = ev >= ENTITY_EVIDENCE_MIN and sim >= ENTITY_ASSIST * size_penalty
            if joins and sim > best_sim:
                best, best_sim = cl, sim
        if best:
            best["ids"].append(iid)
            best["centroid"] = centroid([vecs[i] for i in best["ids"]])
            best["entities"] |= ents[iid]
        else:
            clusters.append({"ids": [iid], "centroid": dict(vecs[iid]), "entities": set(ents[iid])})

    # ── pass 2: merge clusters the greedy order split apart ──
    merged = True
    while merged:
        merged = False
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                a, b = clusters[i], clusters[j]
                if len(a["ids"]) + len(b["ids"]) > MAX_CLUSTER_SIZE:
                    continue
                sim = cosine(a["centroid"], b["centroid"])
                ev, _ = entity_evidence(a["entities"], b["entities"], eidf)
                if ev >= ENTITY_EVIDENCE_MIN and sim >= MERGE_THRESHOLD:
                    a["ids"] += b["ids"]
                    a["centroid"] = centroid([vecs[x] for x in a["ids"]])
                    a["entities"] |= b["entities"]
                    del clusters[j]
                    merged = True
                    break
            if merged:
                break

    # ── FIX 2: cohesion split (after merge, so we don't re-glue) ──
    split_out = []
    n_splits = 0
    for cl in clusters:
        parts = try_split(cl["ids"], vecs)
        if len(parts) > 1:
            n_splits += 1
        for p in parts:
            split_out.append({"ids": p, "centroid": centroid([vecs[i] for i in p]),
                              "entities": set().union(*[ents[i] for i in p])})
    clusters = split_out

    # ── FIX 3: bridge detection ──
    strong = [c for c in clusters if len(c["ids"]) >= 3]
    bridges = []
    for cl in clusters:
        if len(cl["ids"]) > 2:
            continue  # only reassign small/orphan clusters as bridges
        for iid in list(cl["ids"]):
            sims = sorted(((cosine(vecs[iid], s["centroid"]), k)
                           for k, s in enumerate(strong)), reverse=True)[:2]
            if len(sims) == 2 and sims[0][0] >= BRIDGE_MIN_SIM and \
               sims[1][0] / max(sims[0][0], 1e-9) >= BRIDGE_RATIO_MIN:
                bridges.append({"id": iid, "between": (sims[0][1], sims[1][1])})

    by_id = {it["id"]: it for it in items}
    bridge_ids = {b["id"] for b in bridges}
    all_times = [ts(it) for it in items]
    window_start, window_end = min(all_times), max(all_times)
    out = []
    for cl in clusters:
        members = [by_id[i] for i in cl["ids"]]
        times = [ts(m) for m in members]
        latest = max(times)
        latest_age_h = max((now - latest).total_seconds() / 3600, 0.0)
        pubs, seen = [], set()
        for m in sorted(members, key=lambda m: (m["tier"], m["publisher_name"])):
            if m["publisher"] not in seen:
                seen.add(m["publisher"])
                pubs.append(m["publisher_name"])

        def rep_key(mt):
            m, t = mt
            return (0 if m.get("language", "en") == "en" else 1, m["tier"], t)
        rep = sorted(zip(members, times), key=rep_key)[0][0]
        raw_vel = velocity(members, times, window_start, window_end)
        out.append({
            "key": rep["id"], "title": rep["title"], "size": len(members),
            "publishers": pubs, "publisher_count": len(pubs),
            "latest": latest.isoformat(), "latest_age_hours": round(latest_age_h, 2),
            "raw_velocity": round(raw_vel, 3),
            "pulse_score": 0.0,   # filled in below, once the run median is known
            "is_bridge": any(i in bridge_ids for i in cl["ids"]),
            "beat_hint": beat_hint(members, feeds_by_id),
            "entities": sorted(cl["entities"])[:40],
            "items": [{"id": m["id"], "title": m["title"], "url": m["url"],
                       "publisher": m["publisher_name"], "published": m.get("published")}
                      for m, _ in sorted(zip(members, times), key=lambda mt: mt[1], reverse=True)],
        })

    # ── second pass: normalize velocity against this run's own median ──
    import statistics
    ref = [c["raw_velocity"] for c in out if c["publisher_count"] >= 3]
    median_vel = statistics.median(ref) if ref else 1.0
    if median_vel <= 0:
        median_vel = 1.0
    for c in out:
        c["velocity"] = round(c["raw_velocity"] / median_vel, 2)
        c["breaking"] = c["velocity"] >= BREAKING_MIN and c["publisher_count"] >= 3
        # Bonus scales with cluster size: a surge across 12 publishers is a
        # bigger deal than a surge across 2.
        vel_bonus = c["publisher_count"] * DIVERSITY_WEIGHT * VELOCITY_WEIGHT * (c["velocity"] - 1.0)
        c["pulse_score"] = round(
            c["publisher_count"] * DIVERSITY_WEIGHT - c["latest_age_hours"] + vel_bonus, 3)

    out.sort(key=lambda c: c["pulse_score"], reverse=True)
    payload = {"updated": now.isoformat(), "window_items": len(items),
               "median_velocity": round(median_vel, 3), "clusters": out}
    (DATA / out_name).write_text(json.dumps(payload, indent=1))
    if verbose:
        print(f"[v2] {len(items)} items -> {len(out)} clusters "
              f"({n_splits} clusters split, {len(bridges)} bridge items)")
    return payload


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
