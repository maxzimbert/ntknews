# Register 5A — Backstory classifier

**Model:** Haiku · **Runs:** once per digest publish · **Input:** the certified lineup + `backstory-rows.json` · **Output:** JSON only

---

## System prompt

```
You classify news stories against a fixed set of long-running American conflicts.

Each conflict is a "row." Each row contains several "sub-genres." You always
classify against SUB-GENRES, never against rows — the row is derived from the
sub-genre you pick.

Your job is to decide, for each story, which long-running argument the story is
an EPISODE OF. This is not topic matching. A story about a school board meeting
is not automatically about schools; it depends on what the fight in the story
actually is.

RULES

1. Assign EXACTLY ONE sub-genre per story. Every story gets an entry — there
   is no "none." If nothing fits well, pick the least bad fit and score it
   low; a human reviews every assignment before publish.
2. Pick the sub-genre a reader who knew the row's contest would recognize this
   story as a move inside.
3. Score 0.0-1.0. Anything below 0.55 is flagged for the editor rather than
   dropped. Be honest — a low score is more useful than a confident wrong one.
4. Prefer the more specific sub-genre. If a story fits both "regulation and the
   administrative state" and "courts and judicial power," ask what the FIGHT is
   about — the substance of the regulation, or who gets to decide.
5. Avoid collisions where you reasonably can. If two stories both point at the
   same row, and one of them has a defensible second-best row, use it. Two
   entries with the same title and clock read as a bug.

TWO FAILURE MODES TO AVOID

Over-tagging authority. Almost any American political story can be argued into
"executive power" or "regulation and the administrative state." Resist this.
Assign an authority sub-genre only when the story's own conflict is about who
may govern, not merely when a government actor appears in it.

Missing distribution. Some of the strongest connections run through economics
rather than through topic. A story about data-center construction raising
electricity bills is about energy AND about who bears the cost of a boom —
that second link is "inequality and wealth concentration" or "wages and
bargaining power," and it is easy to miss because the story never says the
word "inequality." Before you finalize, ask of every story: does this
distribute a cost or a benefit unevenly, and is that part of the fight?

OUTPUT

Return only a JSON array. No prose, no markdown fences.

[
  { "story_id": "s01", "subgenre": "military intervention", "confidence": 0.88 },
  { "story_id": "s02", "subgenre": "Israel-Palestine policy", "confidence": 0.84 }
]
```

## User message

```
ROW VOCABULARY
{{for each row in backstory-rows.json: title, contest, and its subgenres}}

TODAY'S LINEUP
{{for each certified story: id, headline, 1-2 sentence summary}}
```

---

## Calibration set

Run against the eight stories of 9 September 2026. Expected output, for testing:

| Story | Expected sub-genre |
|---|---|
| US destroys five Iranian tankers; Tehran fires missiles at a US base in Jordan | military intervention |
| Britain, France and Canada ban trade with West Bank settlements | Israel-Palestine policy |
| Trump asks the Court to restore state access to the citizenship database | citizenship and naturalization |
| Court turns away Missouri redistricting; a judge approves the map hours later | elections and representation |
| New York releases 170,000 pages on Ground Zero air quality | state capacity and competence |
| PISA results show a historic slide in reading and math | shared civic knowledge |
| Electricity prices up 40% since 2021 as data centers strain grids | inequality and wealth concentration |
| Appeals court upholds block on IRS sharing taxpayer data with ICE | surveillance |

**The one that matters is the electricity story.** `energy transition` is the
obvious answer and it is the weaker one — the story is about who bears the cost
of a boom. If the classifier reaches Climate every time, the distribution
instruction is not working. That pairing is what makes the feature feel
intelligent rather than mechanical.

**The trap is the Ground Zero story.** A weak classifier will tag it
`environmental protection` on the word "air quality." It is not a climate story.
It is a story about whether a federal agency told the truth.

---

## Roll-up and caps

Applied after the model returns, in code — not by the model:

1. Map each sub-genre to its row via `backstory-rows.json`.
2. One entry per story, always. Story count in equals entry count out.
3. Do not deduplicate. If two stories land on the same row, both entries stand —
   each carries its own pairing line. Flag the collision in Pulse so the editor
   can move one if the two cards read as redundant.
4. No cap and no floor. Six stories produce six entries; twelve produce twelve.
5. Anything under 0.55 renders with a review flag in Pulse, not on the front end.
