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
