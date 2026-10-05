#!/usr/bin/env python3
"""
Validate generated Beginnings lines and object "About this" text, and merge the
ones that pass into editorial/object-notes.json (T-0069).

  python3 editorial/merge_object_notes.py OUT1.json OUT2.json ... --inputs ALL.json

OUT files are lists of {object_id, role, mode, text, unsure, evidence}.
ALL.json is the list built by the fetch step: it holds the matrix fields and the
path to each fetched source text, so every year, number and capitalised name in the
generated text can be traced to the matrix row or the source it was written from.

A note is kept only if it has no HARD flag. Everything is written to the report
(editorial/object-notes-report.json) so the editor can review what was held back.
All kept notes are `verified: false` until the editor spot-checks a sample.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "editorial" / "object-notes.json"
REPORT = ROOT / "editorial" / "object-notes-report.json"
BANNED = ["this document", "this reflects", "underscores", "highlights", "serves as",
          "a reminder that", "pivotal", "landmark", "groundbreaking", "seminal"]
SENT = re.compile(r"[.!?](?:[\"')\]]*)(?:\s|$)")
HARD = {"empty", "dash", "banned phrase", "numbers not traced", "model unsure"}


def words(t):
    return len(t.split())


def facts(text):
    yrs = set(re.findall(r"\b(1[4-9]\d\d|20\d\d)\b", text))
    nums = set(re.findall(r"\b\d[\d,\.]*\d\b|\b\d\b", text)) - yrs
    caps = set(re.findall(r"(?<=[a-z,;] )[A-Z][a-z]{3,}\b", text))
    return yrs, nums, caps


def check(entry, item):
    flags = []
    t = (entry.get("text") or "").strip()
    if not t:
        return ["empty"]
    if "—" in t or "–" in t:
        flags.append("dash")
    low = t.lower()
    if any(b in low for b in BANNED):
        flags.append("banned phrase")
    n, s = words(t), len(SENT.findall(t))
    if item["role"] == "beginning":
        if not 12 <= n <= 25:
            flags.append(f"length {n} words (12-25)")
        if s != 1:
            flags.append(f"{s} sentences (1)")
    else:
        if n > 70:
            flags.append(f"length {n} words (max 70)")
        if not 2 <= s <= 4:
            flags.append(f"{s} sentences (2-4)")
    pool = " ".join(str(item.get(k) or "") for k in ("title", "author", "year", "day_month", "source", "row_title", "contest")).lower()
    if item.get("source_file"):
        pool += " " + Path(item["source_file"]).read_text().lower()
    yrs, nums, caps = facts(t)
    miss = sorted(x for x in (yrs | nums) if x.lower() not in pool)
    if miss:
        flags.append("numbers not traced: " + ", ".join(miss[:8]))
    # Names are a note, not a block: a signing president or a place is often true but
    # absent from the source. Generic institutional words are ignored.
    generic = {"supreme", "court", "congress", "president", "states", "united", "union", "senate", "house",
               "constitution", "britain", "great", "american", "americans", "republic", "committee", "democratic",
               "national", "nations", "government", "federal", "treasury", "secretary", "general", "foreign",
               "affairs", "convention", "foundation", "commission", "king", "parliament", "black", "southerners",
               "asia", "europe", "north", "south", "china", "soviet", "russia", "scottish", "february", "december",
               "june", "july", "august", "october", "november", "april", "september", "public"}
    names = sorted(x for x in caps if x.lower() not in pool and x.lower() not in generic)
    if names:
        flags.append("names not in source or matrix: " + ", ".join(names[:8]))
    if entry.get("unsure"):
        flags.append("model unsure")
    return flags


def main(argv):
    inputs = None
    outs = []
    it = iter(argv)
    for a in it:
        if a == "--inputs":
            inputs = next(it)
        else:
            outs.append(a)
    items = {(o["object_id"], o["role"]): o for o in json.load(open(inputs))}  # an object can be both a Beginning and in The case
    notes = json.loads(NOTES.read_text()) if NOTES.exists() else {}
    report, kept, held = [], 0, 0
    for f in outs:
        for e in json.load(open(f)):
            item = items.get((e.get("object_id"), e.get("role")))
            if not item:
                continue
            flags = check(e, item)
            hard = any(fl.split(":")[0] in HARD for fl in flags)
            report.append({"object_id": e["object_id"], "title": item["title"], "role": item["role"],
                           "mode": item["mode"], "text": e.get("text"), "flags": flags, "kept": not hard})
            if hard:
                held += 1
                continue
            key = "line" if item["role"] == "beginning" else "about"
            # "grounded" only counts if the writer quoted something from the source:
            # a fetched page that held only catalogue metadata is not grounding.
            basis = "grounded" if (item["mode"] == "grounded" and e.get("evidence")) else "matrix-only"
            notes.setdefault(e["object_id"], {}).update({key: e["text"].strip(), "basis": basis,
                                                         "flags": flags, "verified": False})
            kept += 1
    NOTES.write_text(json.dumps(notes, indent=1, ensure_ascii=False) + "\n")
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(f"{kept} notes kept, {held} held back; {len(notes)} objects in {NOTES.name}")


if __name__ == "__main__":
    main(sys.argv[1:])
