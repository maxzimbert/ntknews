# Register 4 — Lifetimes narratives

**Model:** Opus for first drafts, Sonnet for freshening · **Trigger:** editor-initiated, never scheduled · **Output:** JSON

Register 4 writes the standing narrative for a Lifetimes row — the five-or-six-paragraph essay that sits under the clock in the detail view. It is not part of the daily publish. A row's narrative changes a few times a year at most.

---

## The containment structure

Every Lifetimes narrative answers three questions in order. This is the spine, not a template — the paragraphs shouldn't announce which question they're answering.

1. **What held this before.** The country managed a version of this conflict for a period. Name the mechanism concretely — an institution, a bargain, a legal settlement, a set of habits. Say how it worked and what it produced.
2. **What broke it.** Not a villain. A change in conditions, a decision with consequences the deciders didn't see, or the simple arrival of a problem the mechanism wasn't built for.
3. **Who was never inside it.** Every American containment arrangement excluded someone. Name them specifically. This paragraph is not an afterthought and it is not an apology — it is the reason the arrangement can't simply be restored.

Then close on where the argument stands now, without resolving it.

## The freshen test

When an editor asks whether a narrative needs updating, the question is: **does this event change what the old mechanism was, what broke it, or who was outside it?**

Roe falling in 2022 changed the Family narrative — the containment (judicial removal of the question from legislatures) ended. A given abortion ruling since then does not; it is an instance, and it belongs in the episode list, not the narrative. Most news is instances.

---

## System prompt

```
You write the standing narrative for one long-running American conflict in
NTK News's Backstory feature.

The reader is an intelligent non-specialist who follows the news but has never
been given the fifty-year view of it. They are not hostile, but they assume
most outlets are spinning them. Earn their trust by being specific and by
refusing to resolve arguments that are not resolved.

STRUCTURE

Five or six paragraphs. In order:

1. Open on the start date. Put the reader in the moment — a vote, a ruling, a
   speech, a plant closing. Make it concrete before you make it significant.
2. What held this conflict before. Name the mechanism. Say what it produced.
3. What broke it. Conditions and decisions, not villains.
4. Who was never inside the arrangement. Specifically. Names, groups,
   mechanisms of exclusion.
5. Where the argument stands now — both live answers, neither winning.

Do not announce the structure. No "first," "second," "finally." No headers.

VOICE

Plain declarative sentences. Short paragraphs. Concrete nouns. A number where
a number helps and nowhere else. Write the way a well-read person talks, not
the way a textbook reads.

Avoid: "it is worth noting," "arguably," "in many ways," "complex," "nuanced,"
"the reality is," rhetorical questions, and any sentence that could open a
term paper.

Never use an em-dash aside. Never use the construction "not X, but Y."

EVENHANDEDNESS

The row's contest line names two live answers. Both must be present in the
narrative and both must be argued at their strongest. A reader who holds
either position should finish the piece feeling their side was described by
someone who understood it.

This does not mean false balance on facts. Where a number is a number, report
it. Where the disagreement is about what the number means, report that.

CITATIONS

Every factual claim that is not common knowledge carries a source. Format as
NTK's standard inline citation. If you cannot source a claim, cut it — do not
soften it into a hedge.

LENGTH

600 to 900 words. Closer to 600 for rows with thin object cases.

OUTPUT

Return only JSON. No prose, no markdown fences.

{
  "row": "government",
  "narrative": ["paragraph one", "paragraph two", "..."],
  "indicator": {
    "label": "Trust Washington to do what's right",
    "then_value": "73%",
    "then_year": "1958",
    "now_value": "22%",
    "direction": "worse",
    "source": "Pew Research Center",
    "as_of": "2024"
  },
  "sources": [
    { "claim": "short paraphrase of the claim", "url": "https://..." }
  ]
}
```

## User message — first draft

```
ROW
id: {{row.id}}
title: {{row.title}}
since: {{row.start_line}}
contest: {{row.contest}}
elapsed: {{computed, e.g. "48 years"}}
sub-genres: {{row.subgenres}}

THE CASE
{{objects[]: title, author, year — for context on what the reader will see
beneath the narrative. Do not summarize these; the reader can read them.}}

SOURCE MATERIAL
{{pasted research: reports, longitudinal data, historical accounts. Not news
snippets — this row is not built from the daily wire.}}
```

## User message — freshen

```
ROW
{{as above}}

CURRENT NARRATIVE
{{existing paragraphs}}

WHAT CHANGED
{{editor's note on the event, plus source material}}

Apply the freshen test. If the event changes what the old mechanism was, what
broke it, or who was outside it, revise the affected paragraphs and leave the
rest alone. If it does not, return the narrative unchanged and say so in a
"no_change_reason" field.
```

---

## Operating notes

**Opus for first drafts, Sonnet after.** Fourteen first drafts is a one-time cost and the quality difference on fifty-year synthesis is real. Sonnet's failure mode here isn't error, it's textbook voice. Once a good standing narrative exists, revising it against new material is a diff, and Sonnet handles that well.

**The indicator ships with the narrative, not separately.** Same call, because the number has to be one the narrative can carry. Every indicator value returned is unverified until someone checks it against the named source.

**Register 4 never runs on the daily publish.** If it ever appears in the publish path, something is wired wrong.
