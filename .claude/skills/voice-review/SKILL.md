---
name: voice-review
description: Read one NTK edition's published copy on /today, /digest and /backstory against the house rules in docs/voice.md and report every break, with the exact line and the rule. Use when the user says "voice review", "check the copy", "read today's edition against the rules", "did the em dashes come back", "is the writing on voice", or asks how yesterday's or today's prose held up. Reports only; never rewrites.
---

# Reviewing an edition's copy against the house rules

The four sections, Today and Backstory are written by prompts, not by a person in a session.
Nothing else reads what shipped against `docs/voice.md`. This does. It **reports and never
rewrites**: no suggested replacement sentences, no edits to data files, no "fixed version."
The editor decides what to change (T-0104).

## 1. Run the script first

```bash
python3 scripts/voice_review.py --text
```

With no file it reads `ntk-pulse/data/lineup-publish.json`, the edition **already live**, plus
`digest/data/backstory.json`. Say which edition you reviewed (the headline of story 1 is enough)
so nobody mistakes last week's for today's. To review an edition before it ships, Max downloads
story data in Pulse and passes the file, as with `prepublish`:

```bash
python3 scripts/voice_review.py --text ~/Downloads/ntk-stories-YYYY-MM-DD.json
```

Report the script's findings as it gave them. Do not re-run its checks by eye, and do not drop
any. If you think one is a false positive (a "reveals" in a metaphor, a year that is the story
itself), keep it in the list and say why in one clause.

## 2. Then read the text and hold each surface to its own reader

The levels come from `docs/decisions.md`, 2026-10-09, not from the register table's old grades:

| Surface | Reader | What "too hard" looks like |
|---|---|---|
| /today | **middle school** | a sentence that needs rereading, a term of art left unexplained |
| /digest | **high school** | jargon with no gloss, nested clauses, an unexplained acronym |
| /backstory | **AP**, college-educated adults | hand-waving, vagueness, a claim with no dated source. Plainness is fine; condescension is not |

The Flesch-Kincaid numbers are an estimate. Use them to point at passages, never as the finding.

Read the `--text` output and check the rules a script can't, from `docs/voice.md`:

- **Civilian anchor** (§1): each headline carries one brand, dollar figure, named institution or
  cultural touchstone the reader already owns. One, then stop. No years as anchors.
- **Register 1 failure modes** (§1): the Kindergarten Teacher (performed enthusiasm), the
  Explainer-Splainer, the Euphemizer (softening the stakes instead of the sentence).
- **Every number needs a unit** (§5 VOICE_REF).
- **Signpost verbs** (§5): the script finds the words; you judge whether a document or "this" is the
  subject doing nothing. "The judge revealed" is fine. "The memo reveals" is the failure.
- **Cross-section boundary** (§5 GLOBAL): already happened belongs in Truths, likely next step in
  Probabilities, lower-probability in Possibilities, an unsupported claim by an identifiable actor in Lies.
- **Probabilities with conviction** ("will almost certainly", not "might"), each with something to
  watch in 1-14 days.
- **Possibilities** only newly reachable this week; at least one generative, not just risk.
- **Lies** names the claim, who makes it, why someone would believe it, who benefits, the factual
  reality. The lie is the target, never the believers.
- **Today** follows Digest order (the script checks this), excludes Lies, and is a compression of
  the edition, not new writing.
- **The cynic test**: does this sound like someone selling something, or someone telling what happened?

Only report what you can quote. A finding without a quoted line is an impression, and the editor
can't act on it.

## 3. Report format

Group by surface, in this order: /today, /digest, /backstory. For each finding:

```
- story 3 "Dolores Huerta…" Truths ¶7
  "…the late disclosure reflected badly only on Chavez."
  rule: banned signpost verb, the disclosure is the subject doing nothing (voice.md §5 VOICE_REF)
```

Then one line per surface: the reading-level estimate and whether anything you read was pitched
wrong for that reader. End with what you did not check. Keep the whole report scannable; if one rule
breaks in many places, list the places under a single rule rather than repeating it.

## What this must not do

- **No rewrites.** Not in the report, not in the files. Quote and name the rule.
- **The editor's direction wins** (`docs/voice.md` §1, Backstory composer). A part Max revised or
  typed is kept as the editor wanted it, even when it breaks a rule. You can't always tell which parts those
  are, so report the break and say "if this was the editor's call, ignore it" only where the rule is
  one the editor is known to override. Don't re-raise a break the editor has already waved through in this session.
- **No verdict on whether the edition is good.** This checks rules. Whether the lead is the right
  lead or the Lies section is fair is a reading question, and saying otherwise would be trusted.
- **No API spend.** This runs inside a Claude Code session on the editor's plan. Wiring it into CI
  or the publish workflow would start spending API money and needs its own decision (T-0104).

## Known open conflict

The punch-up prompt in `ntk-pulse/pulse.html` and `ntk-pulse/triage.py` still say headlines run
under 90 characters, while published headlines are two sentences (fact plus consequence) and
usually run 120-150. The script reports this as one line per edition instead of one per story so it
doesn't bury everything else. Until the editor decides which rule stands, report it, don't argue it.

## Related

- `prepublish` is the gate: it counts and resolves, and it exits 1 on a blocker. This is the
  reader: it never fails a run.
- `docs/voice.md` is the rulebook. Where it and the prompts in `pulse.html` disagree, the code
  wins, and the doc is what gets fixed.
