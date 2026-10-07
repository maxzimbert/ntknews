#!/usr/bin/env python3
"""Fixture tests for editorial/categories.py (T-0079). Run: python3 editorial/test_categories.py"""
import copy, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import categories as C

ROOT = Path(__file__).resolve().parent.parent
POOL = {o["id"]: o for o in json.load(open(ROOT / "ntk-pulse/data/backstory-pool.json"))["objects"]}
SPEC = json.load(open(ROOT / "editorial/lenses.json"))
ALTMAN = ("OpenAI's publicist tried to shut down a question about a dead teenager. Altman told a magazine "
          "that some bad things will happen as a result of AI. Lawmakers and the FTC opened probes of the chatbot maker.")


def pid(title_part, pool=None):
    m = [o for o in POOL.values() if title_part.lower() in o["title"].lower() and (pool is None or o["pool"] == pool)]
    assert m, title_part
    return m[0]["id"]


def good():
    return {
        "id": "p-ai", "title": "AI", "status": "approved",
        "contest": "Whether the companies building AI should answer for the harm it causes, or whether its benefits justify letting society absorb some of that harm.",
        "stakes": "Whether, when and by whom this new technology should be regulated, and who should share in its benefits, is still being settled. Companies, courts and lawmakers are each claiming the decision.",
        "lenses": ["tech"], "by": {"contest": "model", "stakes": "model", "lenses": "model"},
        "approved_objects": [pid("Privacy Act of 1974"), pid("Executive Order 14110")],
        "objects": [{"object_id": pid("Privacy Act of 1974")}, {"object_id": pid("Telecommunications Act of 1996")},
                    {"object_id": pid("PATRIOT")}, {"object_id": pid("Executive Order 14110")}],
        "beginnings": [
            {"object_id": pid("Privacy Act of 1974"), "line": "Congress limited what federal agencies may do with personal records after Watergate-era surveillance scandals."},
            {"object_id": pid("Telecommunications Act of 1996"), "line": "Congress rewrote the nation's communications law, covering telephone, cable and broadcast, and for the first time the internet."},
            {"object_id": pid("PATRIOT"), "line": "Congress passed the USA PATRIOT Act soon after the terrorist attacks of that year, widening the government's powers to investigate and watch people."},
            {"object_id": pid("Executive Order 14110"), "line": "President Biden ordered the first broad federal rules on the safety and testing of artificial intelligence systems."},
        ],
    }


def run(cat, texts=(ALTMAN,), origin=2025):
    return C.validate(cat, POOL, SPEC, list(texts), origin)


fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "  " + str(detail)))
    if not ok:
        fails.append(name)


def main():

    c, p = run(good())
    check("a well-formed tech category validates cleanly", not p and len(c["beginnings"]) == 4 and len(c["objects"]) == 4, p)

    x = good(); x["lenses"] = ["tech", "china"]
    c, p = run(x)
    check("a lens the story does not support is dropped (the AI page defect)", c["lenses"] == ["tech"] and any("china" in q for q in p), (c["lenses"], p))

    x = good(); x["lenses"] = ["tech", "china"]; x["by"]["lenses"] = "editor"
    c, p = run(x)
    check("a lens the editor chose is honoured", c["lenses"] == ["tech", "china"], c["lenses"])

    x = good(); x["approved_objects"] = []
    c, p = run(x)
    ids = {o["object_id"] for o in c["objects"]}
    check("an unapproved candidate is dropped, with its Beginning", pid("Privacy Act of 1974") not in ids and len(c["beginnings"]) == 2, (ids, p))

    x = good(); c, p = run(x, origin=2000)
    check("a Beginning dated at or after the origin is dropped", all(int(b["year"]) < 2000 for b in c["beginnings"]) and len(c["beginnings"]) == 2, c["beginnings"])

    x = good(); x["stakes"] = "Billions hang on this — and a landmark ruling could end it all for good now."
    c, p = run(x)
    check("model text with a dash and a banned word is dropped, not repaired", c["stakes"] == "" and any("dash" in q for q in p), p)

    x["by"]["stakes"] = "editor"
    c, p = run(x)
    check("the same text written by the editor is kept", c["stakes"] != "", p)

    x = good(); x["beginnings"][1]["object_id"] = pid("Shanghai Communique", "matrix")
    x["objects"].append({"object_id": pid("Shanghai Communique", "matrix")})
    c, p = run(x)
    check("a Beginning from outside the category's lenses is dropped", not any("Shanghai" in b["line"] for b in c["beginnings"]) and any("lenses" in q for q in p), p)

    x = good(); x["objects"].append({"object_id": "no-such-object"})
    c, p = run(x)
    check("an object not in the pool is dropped", any("not in the pool" in q for q in p) and len(c["objects"]) == 4, p)

    x = good(); x["indicator"] = {"label": "x", "verified": False}
    c, p = run(x)
    check("an unverified indicator is dropped", c["indicator"] is None, p)

    x = good(); x["lenses"] = ["tech"]
    c, p = run(x, texts=())
    check("with no story filed yet, a model-chosen lens is kept (nothing to check it against)", c["lenses"] == ["tech"], c["lenses"])

    print(f"\n{len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
