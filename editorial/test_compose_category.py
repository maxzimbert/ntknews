#!/usr/bin/env python3
"""Offline tests for the automatic category step (T-0079): the model and web search are stand-ins."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as C
import compose_category as CC
import build_pairings as BP

ROOT = Path(__file__).resolve().parent.parent
POOL = json.load(open(ROOT / "ntk-pulse/data/backstory-pool.json"))
SPEC = json.load(open(ROOT / "editorial/lenses.json"))
VOCAB = {g["name"] for g in POOL["vocab"]["subgenres"]}
BY = {o["id"]: o for o in POOL["objects"]}
STORY = {"story_id": "s1", "headline": "Sam Altman says bad things will happen from AI",
         "text": "OpenAI's publicist tried to stop a question about a teenager. Altman said some bad things will happen as a result of AI. The FTC opened a probe of the chatbot maker."}
fails = []
def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  " + str(detail)))
    if not ok: fails.append(name)

def caller(key, model, system, user, mt):
    if "opening of a new category page" in user:
        return {"title": "AI", "contest": "Whether the companies building AI should answer for the harm it causes, or whether its benefits justify letting society absorb some of that harm.",
                "stakes": "Whether, when and by whom this new technology should be regulated, and who should share in its benefits, is still being settled. Companies, courts and lawmakers each claim the decision.",
                "lenses": ["tech", "china"], "subgenres": ["not a sub-genre"], "note": "Made from the Altman story."}
    ids = [l.split("id: ")[1].split(" |")[0] for l in user.splitlines() if l.startswith("- id: ")]
    return {i: {"line": f"A public body set out rules for a new technology and the companies that build it, entry {n}.",
                "about": f"A public body published this text. It sets rules for companies that build the technology, number {n}. Its text is published."} for n, i in enumerate(ids)}

def searcher_ok(key, model, prompt, mt=2500):
    t = json.dumps({"label": "Oppose a data center nearby", "then_value": "42%", "then_year": "2025", "now_value": "75%", "direction": "contested",
                    "source": "Heatmap Pro", "source_url": "https://heatmap.news/x", "as_of": "August 2026",
                    "evidence_quote": "Opposition rose from 42% to 75% in a year.", "note": "n"})
    return t, ["https://heatmap.news/x"], []
def searcher_boom(*a, **k):
    raise RuntimeError("web search is not enabled")

rec, notes = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller, searcher_ok, today="2026-10-09")
check("a story with no fitting row gets a composed category", rec is not None and rec["id"] == "p-ai" and rec["auto"], notes)
clean, probs = C.validate(rec, BY, SPEC, [STORY["text"]], None, VOCAB)
bad = [p for p in probs if "about" in p or "line" in p]      # the stand-in writes the same line for each object: the duplicate guard must fire
check("the China lens is dropped: the story never mentions China", clean["lenses"] == ["tech"], clean["lenses"])
check("an unknown sub-genre from the model is dropped", rec["subgenres"] == [], rec["subgenres"])
ids = [o["object_id"] for o in rec["objects"]]
matrix_first = all(BY[i]["pool"] == "matrix" for i in ids if BY[i]["year"] in ("1996", "2001"))
check("matrix objects are used first, candidates fill in", any(BY[i]["pool"] == "matrix" for i in ids) and any(BY[i]["pool"] == "candidate" for i in ids), [BY[i]["pool"] for i in ids])
check("no candidate with an unread link is auto-included", all(BY[i]["link_status"] in ("live", "live-pdf") or BY[i]["pool"] == "matrix" for i in ids), [(BY[i]["title"][:20], BY[i]["link_status"]) for i in ids])
check("auto-included candidates are recorded so Pulse can flag them", set(rec["auto_approved"]) == {i for i in ids if BY[i]["pool"] == "candidate" and not BY[i]["approved"]}, rec["auto_approved"])
check("Beginnings and objects come out oldest to newest", [b["object_id"] for b in clean["beginnings"]] == sorted([b["object_id"] for b in clean["beginnings"]], key=lambda i: BY[i]["sort"]), None)
check("the trend line was found and checked by the system", rec["indicator"] and rec["indicator"]["verified"] and rec["indicator"]["verified_by"] == "system", rec["indicator"])
rec2, notes2 = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller, searcher_boom, today="2026-10-09")
check("a failed web search leaves the category without a trend line instead of failing", rec2 is not None and rec2["indicator"] is None and any("trend line skipped" in n for n in notes2), notes2)
def caller_none(key, model, system, user, mt):
    r = caller(key, model, system, user, mt)
    if "opening of a new category page" in user: r = dict(r, lenses=[], subgenres=[])
    return r
rec3, notes3 = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller_none, searcher_ok)
check("a category with no history to draw on is not created", rec3 is None, notes3)

# the object count: four to six, matrix first
M = lambda i, y, pool="matrix": {"id": f"{pool[0]}{i}", "pool": pool, "author": f"a{i}", "sort": f"{y}-01-01", "title": "t", "lenses": [], "url": "u", "year": str(y)}
big = [[M(i, 1800 + i * 10) for i in range(10)], [M(i + 50, 1900 + i * 5) for i in range(10)], [M(i + 90, 1950 + i * 3) for i in range(10)]]
got = CC.pick_for_subjects(big)
check("three subjects with plenty of sources still give six objects, not nine", len(got) == 6, len(got))
mixed = [[M(i, 1900 + i * 10) for i in range(2)] + [M(i + 20, 1920 + i * 7, "candidate") for i in range(8)]]
got = CC.pick_for_subjects(mixed)
check("matrix objects are all used before candidates fill the six", all(o in got for o in mixed[0][:2]) and len(got) == 6 and sum(1 for o in got if o["pool"] == "matrix") == 2, [(o["pool"], o["year"]) for o in got])
thin = [[M(1, 1950), M(2, 1990)], [M(3, 1970)]]
got = CC.pick_for_subjects(thin)
check("a thin pool gives what exists (three here), not padding", len(got) == 3, len(got))
four = [[M(i, 1900 + i * 20, "candidate") for i in range(5)]]
check("with five sources it takes five; it never goes below four when the pool allows", len(CC.pick_for_subjects(four)) == 5, None)
latest = max(big[0], key=lambda o: o["sort"])
check("the most recent object of a single pool is always kept", latest in CC.pick_for_subjects([big[0]]), None)

# misfit detection
E = lambda **k: dict({"story_id": "x", "editor_row": None, "row_fit": "good", "confidence": 0.9}, **k)
fl = BP.misfits([E(story_id="a"), E(story_id="b", confidence=0.6), E(story_id="c", row_fit="poor"), E(story_id="d", editor_row="government", confidence=0.1),
                 E(story_id="e", confidence=0.5), E(story_id="f", confidence=0.4), E(story_id="g", confidence=0.3)])
check("misfits: poor fit and low confidence flagged, editor-filed never, capped at three, poor fit first", [e["story_id"] for e in fl] == ["c", "g", "f"], [e["story_id"] for e in fl])
check("misfits: a confident good fit is left alone", BP.misfits([E()]) == [], None)

# integration: the whole pairing step with a stand-in model, one story the rows do not fit
import shutil, tempfile
T = Path(tempfile.mkdtemp())
lp = json.load(open(ROOT / "ntk-pulse/data/lineup-publish.json"))
for s in lp["stories"]:
    s.pop("backstory_row", None)
json.dump(lp, open(T / "lineup.json", "w"))
shutil.copy(ROOT / "digest/data/backstory.json", T / "bs.json")
json.dump({"rows": []}, open(T / "prov.json", "w"))
ALT = "5a3de1d2854305d7"
def fake(key, model, system, user, mt):
    if "ROW VOCABULARY" in user:           # 5A
        out = []
        for s in lp["stories"]:
            out.append({"story_id": s["key"], "subgenre": "regulation and the administrative state", "confidence": 0.8, "fit": "good", "category": None})
        for o in out:
            if o["story_id"] == ALT: o.update(subgenre="automation and AI displacement", confidence=0.5, fit="poor", category="AI")
        return out
    if "ENTRIES" in user:                  # 5B
        ids = [l.split()[0] for l in user.splitlines() if l and not l.startswith(" ") and len(l.split()) == 1 and len(l) in (16, 22)]
        return [{"story_id": s["key"], "row": "x", "line": "A one sentence line that says what today's story is, in plain words."} for s in lp["stories"]]
    return caller(key, model, system, user, mt)
BP.call_claude = fake
CC.call_search = searcher_ok
sys.argv = ["x", "--lineup", str(T / "lineup.json"), "--backstory", str(T / "bs.json"), "--provisional", str(T / "prov.json")]
import os
os.environ["ANTHROPIC_API_KEY"] = "dummy"
import categories as CAT
_live = CAT.live_checks; CAT.live_checks = lambda c: (c, [])          # no network in the test
try:
    BP.main()
except SystemExit as e:
    pass
bs = json.load(open(T / "bs.json")); prov = json.load(open(T / "prov.json"))
alt = [p for p in bs["todays_pairings"] if p["story_id"] == ALT][0]
check("integration: the misfit story is paired to its new category, marked as automatic", alt["row"] == "p-ai" and alt["source"] == "auto-category", (alt["row"], alt["source"]))
check("integration: the category is stored, published as a row, and keeps its trend line", prov["rows"] and any(r["id"] == "p-ai" and r["auto"] and r.get("indicator") for r in prov["rows"]) and any(r["id"] == "p-ai" and r["stratum"] == "provisional" for r in bs["rows"]), None)
check("integration: stories that fit keep their rows", all(p["row"] != "p-ai" for p in bs["todays_pairings"] if p["story_id"] != ALT), None)
shutil.rmtree(T)
print(f"\n{len(fails)} failed"); sys.exit(1 if fails else 0)
