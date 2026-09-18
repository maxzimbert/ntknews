# Log

Dated, short, written only when something surprised you. Not a changelog.

**The rule: an entry earns its place only if it would change someone's
behaviour.** "Fixed local news" wouldn't. "Our own documentation asserted fixes
that did not exist, three times" would.

This is corpus material. A future session with no memory draws on it for a
funder memo, a hiring brief, or an explanation of how NTK works. Write for a
stranger.

---

## 2026-09-17 — the state doc rotted in two days

`docs/state.md` was written 2026-09-15 and explicitly verified by reading the
code rather than trusting a README. Checked against the repo on 2026-09-17,
**four of its six open defects were already fixed** — the Today overview CSS
class, the Backstory generator's output path, the pairings renderer, and the
duplicated editorial prompts, whose second copy no longer exists.

The document was careful, honest about its own rot risk, and wrong inside 48
hours. That is the argument for executable checks stated as plainly as it can
be: **care is not the variable.** A document cannot notice that the code moved.
Nothing about writing better prose fixes that.

## 2026-09-17 — a check that overstated a defect by 7x

The first version of T-0001's check reported 7 of 7 onramp keys dead in the
2026-09-16 publish. The real number was 1. The marker format is
`[STORY: key | label]` and the regex never stripped the label half.

The wrong number would have supported a much more aggressive fix — refuse the
publish, rebuild the overview — for what is actually a narrow failure: one
story cut from the lineup after the overview was written. The true 09-14
failure (7 of 7 dead over a one-story digest) is real and worse, which is what
made the wrong number plausible.

It was caught only because the check's output was read rather than trusted.
**A check that overstates is the same class of defect as a document that
overstates**, and it is more dangerous because it carries the authority of
having executed. Run a check against real data and read what it says before
believing it.

## 2026-09-17 — the checker read the wrong copy of the thing it was checking

Pulse publishes through GitHub's API. The commit lands on `origin/main`, not on
the editor's laptop. `rot.sh` reads local files. So running the checks straight
after a publish measured the *previous* digest and reported it as current —
T-0001 read `OPEN` while the publish it was judging actually had zero dead
onramp keys.

The system built to catch "the artifact is not the system" made exactly that
error, on its first day, about a publish. `rot.sh` now fetches and refuses to
run on a tree behind `origin/main`.

Worth noticing the shape rather than the instance: **the thing you are holding
is not the thing that is live**, and every version of this project's failures
has been some variant of that sentence. Netlify serving stale data while the
HTML was byte-identical. A generator writing to a tree nothing serves. A doc
describing intent as implementation. Now a checker reading a stale checkout.

## 2026-09-17 — testing a guard by rewinding past the guard

Twice in ten minutes, `git reset --hard` to an earlier commit was used to
simulate a stale tree — which also reverted `rot.sh` to the version that did
not contain the guard being tested. The test passed by testing nothing, and
the first time it silently discarded the uncommitted fix as well.

**Rewinding the tree removes the code under test.** To test behaviour against
an older tree, move the tree and restore the script:
`git checkout origin/main -- scripts/rot.sh`. And commit before any hard reset.

## 2026-09-18 — the exemplar is the rule

Adding "avoid a succession of loose sentences" to `VOICE_REF` would have
failed the same way the em-dash rule failed on 2026-09-17, one week apart.
The BODY worked example the model is told to study closed on three sentences
under nine words. Measured word counts across it: 16, 7, 26, 17, 4, 23, 24,
17, 7, 5, 3.

The generalization is not "check the examples." It is that a prompt has two
channels, the instruction and the demonstration, and the demonstration wins.
Any rule about *how* something is written has to be measured against the
exemplar before it ships, because the exemplar is what gets copied.

Second-order, and worth watching: the em-dash ban's own instruction says a
sentence carrying two ideas "wants to be two sentences." That rule
systematically converts subordination into parataxis. Flat, staccato output
in the next digest is the predicted cost of the 2026-09-17 fix, not a
separate problem.

## 2026-09-18 — Expertise was in the digest the whole time

The working read was that Expertise sat on the Profile tab. It did not. Three
digest-side surfaces were already shipped. What was missing was that
`beatsToastCopy` returned `null` for four of seven rungs and the caller gated
on `newIdx >= 4` on top of that, so the system almost never spoke.

`beatIdx({stories:20, sessions:9})` returned 6. The behaviors the briefing
calls significant — the Lies layer, depth, sharing — were recorded to
localStorage and then never read above rung 2. Sharing was not recorded at
all.

The lesson that changes behaviour: "the feature is not in the UI" and "the
feature is in the UI and silent" look identical from production, and they
have completely different fixes. Check the call sites before the placement.
