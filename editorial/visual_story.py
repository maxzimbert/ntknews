"""
Each story's visualization (T-0112): the one then-and-now chart that shows where today sits in the long run.

Three ways a story gets one, cheapest first:
  reuse    a series already found and checked (a category's trend line, or one an earlier story's search
           found, kept in editorial/research-ledger.json) that fits this story. No search.
  propose  no checked series fits: the measure that would, named for the editor. Never drawn for readers.
  search   only when the editor asks (Pulse: "search for a source"): one web-search call, the same search
           and the same check as a category's trend line (compose_category.propose_indicator's rule: the link is
           one the search returned and both figures are in a cited or quoted passage). A series that passes
           joins the ledger, so the next story that fits reuses it.
The editor can also supply a series (unchecked until the editor ticks it) or choose no chart.

The visual's shape: {"status": "drawn"|"proposed"|"none", "label", "direction", "source", "source_url", "as_of",
"values": [{"year", "value", "checked"}], "by": "system"|"editor"|"reused", "why"}.
Readers are only ever shown a drawn chart whose every value is checked.
"""
import json
import re
from pathlib import Path

import compose_category as CC
from build_pairings import parse_json_loose

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "editorial" / "research-ledger.json"
SEARCH_MODEL = "claude-sonnet-5-5"


def load_ledger(path=LEDGER):
    p = Path(path)
    d = json.loads(p.read_text()) if p.exists() else {}
    d.setdefault("subjects", {})
    d.setdefault("finds", [])
    d.setdefault("series", [])
    d.setdefault("rejected", [])
    d.setdefault("vetoed", [])
    return d


def save_ledger(d, path=LEDGER):
    Path(path).write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


def known_series(rows, ledger):
    """Every checked series on hand: category trend lines and earlier stories' finds."""
    out = []
    for r in rows:
        i = r.get("indicator")
        if i and i.get("verified") and i.get("then_value") and i.get("now_value"):
            out.append(dict(i, origin=f"category: {r.get('title')}"))
    for s in ledger.get("series", []):
        if s.get("verified"):
            out.append(dict(s, origin=f"found for: {s.get('found_for', '')[:60]}"))
    seen, uniq = set(), []
    for s in out:
        k = (s.get("label"), s.get("source_url"))
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    return uniq


def as_visual(ind, by, why=""):
    return {"status": "drawn", "label": ind.get("label"), "direction": ind.get("direction"),
            "source": ind.get("source"), "source_url": ind.get("source_url"), "as_of": ind.get("as_of"),
            "note": ind.get("note"), "values": [
                {"year": ind.get("then_year"), "value": ind.get("then_value"), "checked": bool(ind.get("verified"))},
                {"year": ind.get("as_of") or "now", "value": ind.get("now_value"), "checked": bool(ind.get("verified"))}],
            "by": by, "why": why, "how_checked": ind.get("how_checked")}


def propose(call, story, scope, known, nudge=None):
    """One small call, no tools: reuse a known series, name the one that would fit, or say none fits."""
    lines = [f"- {n} | {s.get('label')} | {s.get('then_year')} {s.get('then_value')} to {s.get('now_value')} "
             f"({s.get('as_of')}) | {s.get('source')} | {s.get('origin')}" for n, s in enumerate(known)]
    p = f"""NTK's Backstory pages carry at most one chart: a then-and-now pair that shows whether things are getting better, worse, or are contested, on the long argument a news story belongs to. A chart is a claim and is held to the standard of a sentence: only published figures, at their original source.

STORY: {story['headline']}
SCOPE OF ITS HISTORY: {scope}
WHAT IS TRUE: {story.get('truths', '')[:1500]}
{('EDITOR NOTE: ' + nudge) if nudge else ''}

CHECKED SERIES ON HAND (index | measure | figures | publisher | where it came from):
{chr(10).join(lines) or '(none)'}

Answer one of, JSON only:
{{"reuse": index, "why": "one sentence"}}  when a series on hand truly measures this story's argument
{{"measure": "what to measure, as a reader would say it", "publisher": "who would publish it", "why": "one sentence"}}  when none fits but a published series plausibly exists
{{"none": "why no honest chart fits this story"}}"""
    j, usage = call(p)
    if isinstance(j.get("reuse"), int) and 0 <= j["reuse"] < len(known):
        return as_visual(known[j["reuse"]], "reused", j.get("why", "")), usage
    if j.get("measure"):
        return {"status": "proposed", "label": j["measure"], "publisher": j.get("publisher"), "why": j.get("why", ""),
                "values": []}, usage
    return {"status": "none", "why": j.get("none") or "no chart fits", "values": []}, usage


def search(api_key, story, scope, measure, nudge=None, searcher=None):
    """One web-search call for this story's series, checked as a category trend line is. Returns
    (visual, ledger_entry or None, note)."""
    rec = {"title": scope, "contest": (f"Measure wanted: {measure}. " if measure else "") + (f"Editor: {nudge}" if nudge else "")}
    ind, note = CC.propose_indicator(api_key, SEARCH_MODEL, rec, story["headline"], searcher)
    if not ind:
        return {"status": "proposed", "label": measure, "why": note, "values": [], "searched": True}, None, note
    entry = dict(ind, found_for=story["headline"], scope=scope)
    return as_visual(ind, "system", "found by search for this story"), entry, note


def from_editor(v):
    """The editor's own series. Unchecked until the editor ticks it as checked against the source."""
    if v.get("none"):
        return {"status": "none", "why": "the editor chose no chart", "values": [], "by": "editor"}
    need = ("label", "then_value", "then_year", "now_value", "source", "source_url")
    if not all(str(v.get(k) or "").strip() for k in need):
        return None
    ind = {k: v.get(k) for k in need + ("direction", "as_of", "note")}
    ind["verified"] = bool(v.get("verified"))
    vis = as_visual(ind, "editor", "supplied by the editor")
    if not re.match(r"^https://", ind["source_url"]):
        vis["values"] = [dict(x, checked=False) for x in vis["values"]]
    return vis
