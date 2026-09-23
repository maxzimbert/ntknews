---
id: T-0033
title: The story header has no job now, and nobody has decided what it is for
status: DISCARDED
tags: [digest, decision]
anchor: digest/index.html:2167
---

## Superseded by T-0034

The editor's next question — why can't the share button just send the URL it
already sends — surfaced that `shareStory()` was already pointing at the
permalink, and the only reason two story surfaces existed was the app's own
`#storyView` duplicating a page that already worked. T-0034 deletes
`#storyView` outright. With one reading surface instead of two, there is no
separate in-app header left to design; this ticket's question dissolves
rather than gets answered. Kept below for the reasoning — the constraints it
recorded (closure as the product promise, no unread counts) are still true
and still apply to whatever the permalink's own header does.

## What

T-0029 emptied the story screen's header. It used to hold two buttons — one
duplicating the "Back" at the foot of the share bar, the other opening a modal
that said "Coming soon." Both are gone. What is left is a 56px full-width bar
containing the NTK mark and nothing else, on both story surfaces (`#storyView`
in the app and `STORY_PAGE_TEMPLATE`'s output).

The mark links to `/digest`, which is a real job, but it is a small one for a
bar that spans the screen and stays there while you read. The question this
ticket exists to answer is what that space is **for** — or whether it should
exist at all.

Candidates raised by the editor, none decided:

- **Cut it.** Let the story open at the hero image with no chrome above it,
  and make the mark sticky on scroll so the way home appears once you have
  moved.
- **Keep it, give it work.** Reading progress, the story's position in the
  edition, the section you are currently inside, or the route to the paired
  Backstory once T-0032 exists.
- **Something else a designer proposes.** The editor's own framing: "a
  designer should come up with an idea for it."

## Why

This is a decision ticket, not a defect. Nothing is broken — a bar with a
working logo is a perfectly serviceable thing to ship, and it is what is in
production right now. The risk being recorded is different: **empty space in a
fixed position attracts filler.** The reason the bar held a dead "Coming soon"
button in the first place is that it was there and something had to go in it.
Left undecided, it will collect a share icon, a font-size control, a
bookmark — the same accretion the audit spent T-0029 removing from everywhere
else.

Constraints any proposal has to respect, all of them established rather than
assumed:

1. **Two implementations.** The story screen exists twice — once inside the
   app, once as a standalone static page from `build_digest.py`. Anything
   designed here has to be built twice, or T-0032's consolidation has to
   happen first. That duplication is why the headline typeface drifted, why
   the permalink missed the type scale entirely, and why its accents were
   still failing contrast years later.
2. **The bottom nav is hidden while reading**, on both paths (`openStory()`
   sets `#bottomNav` to `display: none`). So the header is currently the only
   persistent chrome on the story screen. Cutting it leaves none.
3. **A reader arriving from a shared link has no app around them.** The
   permalink is a standalone page. Whatever the header does must still make
   sense to someone who has never seen the digest.
4. **The digest ends, and so should the story.** `docs/decisions.md` records
   closure as the product promise. A progress indicator would reinforce it; a
   "related stories" rail would directly contradict it, and is out of bounds.
5. **No unread counts, ever.** Same source. Anything resembling a backlog
   is out.

Worth stating plainly because it cuts against the instinct to fill: doing
nothing is a legitimate outcome. A quiet nameplate that gets you home is not a
problem to be solved, and "we looked at this and decided the bar earns its
keep as it is" is a valid close for this ticket.

## Check

```sh
manual: the editor and a designer agree what the story header is for, and the
        answer is recorded in docs/decisions.md — including if the answer is
        "nothing, leave it as a nameplate"
```
