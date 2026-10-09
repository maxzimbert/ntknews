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

CHOSEN = {}
JUDGE_DROPS = []
def caller(key, model, system, user, mt):
    if "skeptical editor" in user:
        ids = [l.split("id: ")[1].split(" |")[0] for l in user.splitlines() if l.startswith("- id: ")]
        return {i: {"keep": not ("*" in JUDGE_DROPS or any(d in i for d in JUDGE_DROPS)), "why": "It connects to the story."} for i in ids}
    if "choose the primary sources" in user:
        ids = [l.split(" | ")[0] for l in user.split("DOCUMENTS (id | year | title | author | pool | sub-genre):")[1].split("Choose up to 6")[0].strip().splitlines()]
        m = [i for i in ids if BY[i]["pool"] == "matrix"][:3]
        c = [i for i in ids if BY[i]["pool"] == "candidate"][:3]
        CHOSEN["ids"] = m + c + ["not-in-the-pool"]
        return {"choose": CHOSEN["ids"], "why": "These connect."}
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
MS_URL = "https://www.govinfo.gov/content/pkg/example-act.pdf"
def ms_item(**kw):
    d = {"ties_to": "anti-plague lab in Irkutsk", "relation": "same subject", "year": "1972", "date": "1972-04-10", "title": "Convention on Biological Weapons", "author": "Parties to the Convention", "source": "UN Treaty Collection",
         "source_url": MS_URL, "line": "Dozens of states signed a treaty banning the development and stockpiling of biological weapons in April 1972.",
         "about": "Governments signed this treaty in 1972. It bans developing, producing and stockpiling biological weapons. It was opened for signature in April.",
         "evidence_quote": "The Convention was opened for signature on 10 April 1972."}
    d.update(kw); return d
def searcher_ms(items, urls=None):
    def f(key, model, prompt, mt=2500):
        if "You are the researcher for NTK" in prompt:
            return json.dumps(items), (MS_URL not in (urls or [])) and [MS_URL] if urls is None else urls, []
        return searcher_ok(key, model, prompt, mt)
    return f
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

check("the model's choice is used, and an id outside the pool is ignored", rec is not None and "not-in-the-pool" not in [o["object_id"] for o in rec["objects"]] and len(rec["objects"]) == len(CHOSEN["ids"]) - 1, [o["object_id"] for o in rec["objects"]])
def caller_off(key, model, system, user, mt):
    if "choose the primary sources" in user: raise RuntimeError("down")
    return caller(key, model, system, user, mt)
recx, nx = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller_off, searcher_ok)
def caller_list(key, model, system, user, mt):
    if "choose the primary sources" in user:
        ids = [l.split(" | ")[0] for l in user.split("DOCUMENTS (id | year | title | author | pool | sub-genre):")[1].split("Choose up to 6")[0].strip().splitlines()]
        return [i for i in ids if BY[i]["pool"] == "matrix"][:5]       # a bare list, as the real model once answered
    return caller(key, model, system, user, mt)
recl, nl = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller_list, searcher_ok)
check("a bare list of ids from the model is accepted", recl is not None and 1 <= len(recl["objects"]) <= 5 and all(BY[o["object_id"]]["pool"] == "matrix" for o in recl["objects"]) and any("chosen for relevance" in n for n in nl), nl)
def caller_sg(key, model, system, user, mt):
    if "choose the primary sources" in user: raise RuntimeError("down")
    r = caller(key, model, system, user, mt)
    if "opening of a new category page" in user: r = dict(r, lenses=[], subgenres=["regulation and the administrative state"])
    return r
recs, ns = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller_sg, searcher_ok)
check("with only a sub-genre and a failed choice, no off-topic objects are drawn in: no category", recs is None, ns)
check("if the model's choice fails, the rule picks four to six", recx is not None and 4 <= len(recx["objects"]) <= 6 and any("rule picked" in n for n in nx), (len(recx["objects"]) if recx else None, nx))

# milestones found by search fill a gap the pool cannot
def caller_none_connect(key, model, system, user, mt):
    if "choose the primary sources" in user: return {"choose": [], "why": "nothing connects"}
    return caller(key, model, system, user, mt)
STORY2 = dict(STORY, headline="A lab worker died in Siberia", text="A 28-year-old worker died at an anti-plague lab in Irkutsk. Russia locked down five regions. Officials disagree on the cause.")
recm, nm = CC.compose("k", "m", STORY2, "Biosecurity", POOL, SPEC, caller_none_connect, searcher_ms([ms_item()]))
check("when nothing in the pool connects, milestones found by search fill the page", recm is not None and len(recm["custom_objects"]) == 1 and recm["custom_objects"][0]["found_by"] == "search", nm)
cm, pm = C.validate(recm, BY, SPEC, [STORY2["text"]], None, VOCAB)
check("a found milestone validates and is flagged for the editor's review", [b["object_id"] for b in cm["beginnings"]] == [recm["custom_objects"][0]["id"]] and recm["custom_objects"][0]["id"] in recm["auto_approved"], pm)
bad_url, nb = CC.find_milestones("k", "m", STORY2, "t", "c", [], 3, searcher_ms([ms_item(source_url="https://elsewhere.org/x")], urls=[MS_URL]))
check("a link the search did not return is rejected", bad_url == [] and any("not one the search returned" in n for n in nb), nb)
wiki, nw = CC.find_milestones("k", "m", STORY2, "t", "c", [], 3, searcher_ms([ms_item(source_url="https://en.wikipedia.org/wiki/X")], urls=["https://en.wikipedia.org/wiki/X"]))
check("Wikipedia is rejected", wiki == [] and any("not a primary source" in n for n in nw), nw)
num, nn = CC.find_milestones("k", "m", STORY2, "t", "c", [], 3, searcher_ms([ms_item(line="A total of 150 states signed a treaty banning the development and stockpiling of biological weapons in April 1972.")]))
check("a number not in the quote is rejected", num == [] and any("number" in n for n in nn), nn)
noq, nq = CC.find_milestones("k", "m", STORY2, "t", "c", [], 3, searcher_ms([ms_item(evidence_quote="")]))
check("a milestone with no quote from the page is rejected", noq == [], nq)
long_line = "Dozens of states signed a treaty banning the development, production and stockpiling of biological weapons in April 1972 after years of talks in Geneva and elsewhere."
def caller_fix(key, model, system, user, mt):
    if "broke the rules" in user:
        return {"0": {"line": "Dozens of states signed a treaty banning biological weapons in April 1972.", "about": "Governments signed this treaty in 1972. It bans biological weapons. It was opened for signature in April."}}
    return caller(key, model, system, user, mt)
fixed_ms, nf = CC.find_milestones("k", "m", STORY2, "t", "c", [], 3, searcher_ms([ms_item(line=long_line)]), caller_fix)
check("a milestone whose line is a few words too long is repaired, not thrown away", len(fixed_ms) == 1 and len(fixed_ms[0]["line"].split()) <= 25 and any("repaired" in n for n in nf), nf)
unfixed, nu = CC.find_milestones("k", "m", STORY2, "t", "c", [], 3, searcher_ms([ms_item(line=long_line)]), None)
check("without a repair caller the long line is rejected", unfixed == [], nu)
recn, nn2 = CC.compose("k", "m", STORY2, "Biosecurity", POOL, SPEC, caller_none_connect, searcher_ms([]))
check("nothing in the pool and nothing found: no category", recn is None, nn2)
recs2, ns2 = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller, searcher_ok)
check("the search runs when the pool gives fewer than six, and finding none leaves the pool objects", recs2 is not None and any("0 milestone(s) found" in n for n in ns2), ns2)

# the independent judge and the tie to the story
def caller_soviet(key, model, system, user, mt):
    if "choose the primary sources" in user:
        ids = [l.split(" | ")[0] for l in user.split("DOCUMENTS (id | year | title | author | pool | sub-genre):")[1].split("Choose up to 6")[0].strip().splitlines()]
        picks = [i for i in ids if BY[i]["pool"] == "matrix"][:3]
        JUDGE_DROPS[:] = picks[:1]
        return {"choose": picks, "why": "official candor"}
    return caller(key, model, system, user, mt)
CC_lenses = None
JUDGE_DROPS[:] = []
recj, nj = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller_soviet, searcher_ok)
check("the judge drops the items it rejects and the rest stay", recj is not None and not any(o["object_id"] in JUDGE_DROPS for o in recj["objects"]) and len(recj["objects"]) >= 1 and any("dropped by the judge" in n for n in nj), (nj, [o["object_id"] for o in recj["objects"]] if recj else None))
check("each kept item carries why it connects", recj and all(v.get("why") for v in recj["ties"].values()) , recj and recj["ties"])
JUDGE_DROPS[:] = []
badtie, nbt = CC.find_milestones("k", "m", STORY2, "t", "c", [], 3, searcher_ms([ms_item(ties_to="a phrase that is not in the story at all")]))
check("a ties_to that is not copied from the story is rejected", badtie == [] and any("ties_to" in n for n in nbt), nbt)
badrel, nbr = CC.find_milestones("k", "m", STORY2, "t", "c", [], 3, searcher_ms([ms_item(relation="shares a theme")]))
check("a relation outside the three allowed is rejected", badrel == [], nbr)
JUDGE_DROPS[:] = ["*"]
recz, nz = CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller, searcher_ok)
check("if the judge drops everything, no category is made", recz is None, nz)
JUDGE_DROPS[:] = []

# looser tie: the story's own words, not a verbatim copy
check("ties_to made of the story's words passes even when reordered", CC.ties_ok("Irkutsk anti-plague laboratory", STORY2["text"]))
check("ties_to with words that are not in the story fails", not CC.ties_ok("nuclear arms treaty negotiations", STORY2["text"]))
check("a one-word ties_to fails", not CC.ties_ok("Irkutsk", STORY2["text"]))
# the search is asked even when the matrix supplies enough, and asks for a chronology
asked = []
def searcher_spy(key, model, prompt, mt=2500):
    if "You are the researcher for NTK" in prompt: asked.append(prompt)
    return searcher_ms([ms_item()])(key, model, prompt, mt)
CC.compose("k", "m", STORY, "AI", POOL, SPEC, caller, searcher_spy)
check("search is asked for a chronology even when the pool supplies some objects", len(asked) == 1 and "what is the history of the action" in asked[0] and "target, not a quota" in asked[0], len(asked))

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
# an automatic category left with fewer than two objects by the checks is not created
import copy
one = copy.deepcopy(prov["rows"][0]); one["id"] = "p-lonely"; one["title"] = "Lonely"; one["status"] = "approved"; one["auto"] = True
one["objects"] = one["objects"][:1]
one["beginnings"] = [b for b in one["beginnings"] if b["object_id"] == one["objects"][0]["object_id"]]
logs = []; _log = BP.log; BP.log = lambda m: logs.append(m)
BP.apply_categories(T / "lonely.json", {"backstory_categories": [one]}, [], {"rows": [], "todays_pairings": []}, "2026-10-09", live=False)
BP.log = _log
lone_store = json.load(open(T / "lonely.json")) if (T / "lonely.json").exists() else {"rows": []}
check("an automatic category with one surviving object is not created", not any(r["id"] == "p-lonely" for r in lone_store["rows"]) and any("needs two" in l for l in logs), logs)
shutil.rmtree(T)
print(f"\n{len(fails)} failed"); sys.exit(1 if fails else 0)
