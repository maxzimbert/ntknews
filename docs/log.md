# Log

Dated, short, written only when something surprised you. Not a changelog.

**The rule: an entry earns its place only if it would change someone's
behaviour.** "Fixed local news" wouldn't. "Our own documentation asserted fixes
that did not exist, three times" would.

This is corpus material. A future session with no memory draws on it for a
funder memo, a hiring brief, or an explanation of how NTK works. Write for a
stranger.

---

## 2026-10-08 — Netlify's usage limit took ntknews.org down, and credits did not bring the last deploys back

The site returned 503 `usage_exceeded` on every route until credits were added. Builds that fired during the
pause were lost: after the site came back it served a stale build, and Netlify did not replay them. Seven
production deploys and about eight PR deploy previews in one day of copy iteration is a plausible cause
(unverified). Bot commits are not: `netlify.toml`'s ignore rule skips anything confined to `ntk-pulse/data/`.
That same rule means an empty commit does not deploy; it needs a real diff outside the excluded paths.
Batch copy changes into fewer pushes, and after any outage compare the live page to `main` before trusting a 200.

## 2026-10-07 — GitHub Pages had been failing for a day, and Pulse is served from it

A ticket (T-0078) quoting CSS with `{{` landed on 2026-10-06. Jekyll reads `{{` as a Liquid tag and aborts
the whole build, so every GitHub Pages build of this repo failed from then on (23 in a row, last good
2026-10-06 16:12Z). Pulse is served from Pages, so every Pulse change merged since looked deployed and was
not; the same failure hit the staging copy two days running before the cause was found. A root `.nojekyll`
ends it, and the check that would have caught it is `gh api repos/maxzimbert/ntknews/pages/builds/latest`,
not the Netlify preview, which does not run Jekyll.

## 2026-09-29 — the same rot, in the doc that was supposed to be fixed

`docs/backstory.md` still described the `build_backstory.py` output-path bug as
open, twelve days after the 2026-09-17 entry below recorded it fixed. A session
read the doc, repeated the claim to the editor, and proposed a ticket for a
defect that no longer existed. Reading `build_backstory.py:31` first caught it.
**Grep the line before you cite a doc that says a line is wrong.**

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

## 2026-09-18 — a check that edited what it measured

`rot.sh` left the working tree dirty on every run. The file was
`lineup-publish.json`, always data-identical to HEAD and always collapsed to
one line, so it read like an editor or a formatter and got dismissed three
times as somebody else's doing.

It was T-0010's own check. It writes a test `backstory_row` into the published
lineup, runs `build_pairings.py --mock`, and restores in a `finally`. The
restore used `json.dumps(lp)` rather than the bytes it read, so it came back at
Python's default indent instead of the `indent=1` Pulse writes. The same check
backed up `backstory.json` correctly with `read_text()`; only one of the two
was wrong.

Two things worth carrying:

The harmless-looking half is not the point. The same code would have clobbered
a bot publish that landed between the backup and the restore, silently, and the
bots commit to that path roughly 72 times a day.

The diagnosis was delayed by a plausible explanation. "You're probably adding
and removing stories" fit the story and fit nothing in the evidence: the data
was identical every time. The measurement said formatting-only from the first
look. Reproducing it took one command once anyone stopped explaining it.

## 2026-09-23 — a direction recorded in the abstract did not survive being seen

"Nothing but ntknews.org should be dark" was answered yes in a question,
written into the audit and T-0029 as settled, and then took two days and a
full re-theme to get to a preview — where the editor rejected it on sight.
For visual changes that are hard to reverse, put a screenshot or mock in
front of the editor before building, not after.

## 2026-10-05 — the model's recall was not the failure; the link was

The generation pilot wrote 16 documents' text twice, once from the matrix row alone and once
from the fetched source. The matrix-only writing had no factual error I could find, including
for lesser-known documents (the earlier fear, T-0045 and T-0047, was about quotes and numbers,
which the pilot did not test). What went wrong was upstream: a link to the wrong document
(Taft's 26 July speech on the row for his 11 July one) had passed a research agent, a live fetch
and a content check, and was caught only because the grounded version printed a date that
disagreed with the matrix. Check a link against the matrix's date and title, not only that it
loads. `editorial/check_links.py` now notes any matrix year that appears nowhere on the page.

## 2026-10-05 — "verified" from an agent is a claim; re-fetch it

Research agents returned links marked verified. Re-fetching every one and checking the author
or title words on the page found problems they had not reported: a dead state.gov path, an
error page served with a 200, a lending-library copy of an in-copyright book, a catalogue page
standing in for the document. Agents also hit a cap of 200 web searches a session and silently
turned later items into "not found"; slices of about 11 objects stayed inside it. The first
pass linked 120 of 248 and the second only 20 of 87, because archives (Founders Online, loc.gov,
state.gov) refuse scripts.

## 2026-10-05 — a middle dot with zero width, and a selector that matched the label

Two visual bugs came from assumptions about the page, not the CSS. Overpass's middle dot
(U+00B7) has zero advance width, so no spaces or margins separate it from the next word; draw
the dot with CSS. And `.row:first-child` never matched because the section's first child was the
"Beginnings" label (T-0073). Measure the rendered page with `getBoundingClientRect` before
changing CSS.

## 2026-10-05 — Pulse published an old Today overview and the server was right

Symptom: `ntknews.org/today` kept showing the previous essay through any number of hard
refreshes. The first instinct, cache or deploy, was wrong: the live ETag carried the publish
commit's hash and the HTML held the six published stories. The fault was in what Pulse
published: `lineup-publish.json`'s `today.generatedAt` was weeks old. Look at the published
payload before the CDN. The rot suite found the same fault independently (T-0001, dead onramp
keys). I built the guard (T-0072) without first reading `docs/decisions.md`, which already held
a 2026-09-16 decision about this exact gate; the result differs from it in one place, recorded
there. Read decisions before building, as CLAUDE.md rule 2 says.

## 2026-10-05 — a rot check can be wrong; the proof is that it still fails on the broken case

T-0001's check reported dead onramp keys on a good edition because it recognised only 16-hex
story keys, and manual and scoop-imported stories are `manual-<timestamp>`. Widening the pattern
was honest only because the widened check was then run against the broken edition from earlier
the same day and still failed there.
