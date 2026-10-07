#!/usr/bin/env python3
"""The origin step's second round (T-0074): a story whose first answer is only a guess gets new
queries, and the better origin wins. Offline: the model and Wikipedia are stand-ins."""
import json, sys, tempfile, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_origins as bo

ROOT = Path(__file__).resolve().parent.parent
T = Path(tempfile.mkdtemp())
lp = json.load(open(ROOT / "ntk-pulse/data/lineup-publish.json"))
st = [s for s in lp["stories"] if s["key"] == "31b249b6c8ea7c86"][:1]       # the Utah story
lp["stories"] = st
json.dump(lp, open(T / "lineup.json", "w"))
bs = json.load(open(ROOT / "digest/data/backstory.json"))
bs["todays_pairings"] = [p for p in bs["todays_pairings"] if p["story_id"] == "31b249b6c8ea7c86"]
json.dump(bs, open(T / "bs.json", "w"))

def cand(title, year, lead):
    return {"title": title, "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"), "lead": lead, "qid": None,
            "wikidata_year": None, "wikidata_date": None, "years_in_lead": [year]}
WRONG = cand("Artificial Intelligence Act", 2024, "The AI Act is a European Union regulation on artificial intelligence adopted in 2024.")
RIGHT = cand("Utah Artificial Intelligence Policy Act", 2024, "The Utah Artificial Intelligence Policy Act was signed into law in Utah in 2024. It established an Office of Artificial Intelligence Policy.")
calls = {"retrieve": 0}
def fake_retrieve(queries):
    calls["retrieve"] += 1
    return [WRONG] if calls["retrieve"] == 1 else [RIGHT]
def fake_claude(key, model, system, user, max_tokens):
    if model == bo.QUERY_MODEL:
        return {"story_id": "31b249b6c8ea7c86", "row_fit": "good", "queries": ["AI regulation sandbox"] if "PREVIOUS ATTEMPT" not in user else ["Utah Artificial Intelligence Policy Act"]}
    if "Utah Artificial Intelligence Policy Act" in user:
        return {"story_id": "31b249b6c8ea7c86", "choice": RIGHT["title"], "year": 2024, "fit": "direct", "row_fit": "good",
                "line": "When Utah signed the first state law regulating generative AI in 2024, and set up an Office of Artificial Intelligence Policy.",
                "evidence_quote": "was signed into law in Utah in 2024", "why": "Names Utah's office."}
    return {"story_id": "31b249b6c8ea7c86", "choice": WRONG["title"], "year": 2024, "fit": "inferred", "row_fit": "good",
            "line": "When the European Union adopted a common legal framework for artificial intelligence called the AI Act in 2024.",
            "evidence_quote": "adopted in 2024", "why": "General."}
bo.retrieve, bo.call_claude = fake_retrieve, fake_claude
import os; os.environ["ANTHROPIC_API_KEY"] = "dummy"
sys.argv = ["x", "--lineup", str(T / "lineup.json"), "--pairings", str(T / "bs.json"), "--out", str(T / "o.json")]
bo.main()
o = json.load(open(T / "o.json"))["origins"][0]["origin"]
ok = o["status"] == "retrieved" and o["title"] == RIGHT["title"] and o.get("round") == 2 and o["fit"] == "direct"
print(("ok   " if ok else "FAIL ") + "a guess in round one is replaced by the direct origin found in round two", o if not ok else "")
shutil.rmtree(T)
sys.exit(0 if ok else 1)
