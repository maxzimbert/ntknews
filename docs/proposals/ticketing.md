# Proposal — a stateless ticketing system for NTK

**Status: implemented 2026-09-17.** See `docs/tickets/README.md` for what
shipped and `scripts/rot.sh` for the detector. This file is kept as the
argument, not the manual.

Decisions taken from the seven questions at the bottom: tickets are Markdown
files with five frontmatter fields; checks are inline shell; the rot detector
fails rather than opening a PR; seven retroactive tickets, not six, because one
regression guard was worth adding; `prepublish` is filed as T-0008 but held,
since its checks now run on a schedule anyway; the tag vocabulary is eight
areas and four kinds, enforced by the detector rather than by discipline; and
the `.docx` corpus gap is T-0009 and is probably worth more than all of this.

Originally written at the end of a two-day session as the handoff for a
separate conversation that would design this properly.

A note on "stateless": the word that matters is not *ticket*, it is *stateless*.
The requirement is that a session which begins knowing nothing can pick up a
piece of work and finish it correctly. Everything below is in service of that,
and nothing below requires a hosted service, an API key, or a login.

---

# Part I — drawn from this codebase and what actually went wrong

## The evidence

I made five documented errors in two days. They are worth listing precisely,
because four of the five share one cause and that cause is what the system has
to defeat.

| Error | What I believed | What was true | Cause |
|---|---|---|---|
| Sent the editor from GitHub Pages to Netlify for Pulse | `pulse.html` byte-identical across hosts, so the hosts are equivalent | Netlify's copy of `ntk-pulse/data/` was two days stale; the tool worked and quietly recommended worse stories | Verified the **artifact**, not the **system** |
| Journalism Atlas was tabled on editorial grounds | A README said Atlas is analysis, Pulse needs reporting | The feed import failed and it got deprioritized under time pressure | A README recorded a **rationalization** as a decision |
| Em-dash discipline was "prompt-only, on purpose" | `docs/decisions.md` recorded it as a locked decision | There was no em-dash rule anywhere in `pulse.html`, and the prompts held 82 em dashes including in the worked examples | A doc described **intent** as implementation |
| Local-news quality filter shipped | `pulse-digest-technical-state.md` says so | `dataType` appeared in zero files; dedup was URL-only | Same |
| The 56-object curation was blocking | The triage doc treats it as the work | `pick()` already auto-selects four per row | Read the **doc** without reading the **code** |

Three separate documents asserted a fix that was never written. That is not a
documentation-discipline problem you can solve by being more careful. **Prose
claims about code rot silently, and nothing about writing better prose fixes
that.**

Two further structural problems, neither mine:

- **`build_backstory.py` wrote to a tree nothing serves** for the entire life of
  the feature. No artifact connected the generator to the reader, so nothing
  could notice.
- **The READMEs' most authoritative sources are `.docx` files outside the
  repo** — v14, the Editorial Constitution, the Story Selection Brief, the
  Roadmap, the SWOT. A cold agent cannot open any of them. The source of truth
  pointed outside itself.

## What follows from that

### 1. Tickets are files in this repo, in git

Not Linear, not Jira, not GitHub Issues. Reasons, in order of weight:

- A cold agent reads files natively and needs no auth to do it. That is the
  entire stateless requirement, satisfied for free.
- Git already gives you history, attribution and diffs. A hosted tracker gives
  you a second history that drifts from the first.
- The failure mode of this project has been **truth living somewhere the code
  isn't**. Putting tickets anywhere but here repeats it.

GitHub Issues is the closest near-miss and still wrong: an agent needs the API
and a token to read it, and issue bodies are prose with no relationship to the
tree.

### 2. Three states, never collapsed

The single highest-value change. Most of my errors were reading one of these
as another:

- **DECIDED** — the call has been made. Nothing has been built.
- **BUILT** — code exists. Nobody has confirmed it does the thing.
- **VERIFIED** — a check ran and passed.

Every README in this project conflated all three into "here is what we did."

### 3. A ticket's core field is an executable check, not a description

This is the mechanism. Everything else is packaging.

Bad, and what every README did:

> Local news content-quality filtering added.

Good:

```sh
grep -q "dataType: \['news'\]" netlify/functions/news.js
grep -q "LOCAL_NONNEWS_PATH" digest/index.html
```

The second one **cannot** be wrong for six months without anyone noticing.
The first one was.

Not every check is a grep. The useful forms, roughly in order of strength:

| Form | Example from this week |
|---|---|
| A shell assertion | `dataType` present in the proxy |
| A count with a threshold | em dashes in a published digest ≤ 3 |
| A parse | `node --check` on the extracted script block |
| A fixture run | `build_digest.py` against synthetic data |
| A live fetch | `/digest/data/backstory.json` has 21 rows |
| **An honest "manual"** | "the pairing lines read well" — a human must judge |

That last row matters. Some things genuinely cannot be automated, and a ticket
that says `check: manual — editor reads six lines` is honest. A ticket that
*pretends* to a check it doesn't have is how you get back to where we started.

**A tension to design for, not resolve.** A check makes a ticket verifiable. A
check alone makes it worthless as corpus material — `grep -q dataType` records
nothing about why that filter matches on path rather than host, which is the
part a future reader needs. So a ticket carries both a check and a why, and
they serve different readers: the check serves the rot detector, the why serves
whoever asks six months out. Neither substitutes for the other. See Part II.

### 4. Every ticket anchors to code

A `file:line` or a grep pattern. A ticket with no anchor is a wish.

This also gives you rot detection nearly free: if the anchor no longer resolves,
something moved and the ticket needs re-reading. That is exactly the signal that
was missing when `build_backstory.py` pointed at a dead directory.

### 5. Run the checks on a schedule, and let them fail loudly

The thing that would have caught four of my five errors.

You already have the infrastructure: a GitHub Action, on cron, running every
ticket's check block and flipping `VERIFIED` to `STALE` on failure. That is a
shell script and a `for` loop.

**One hard-won caution, from this week:** the pairings step is
`continue-on-error: true` and therefore fails quietly by design. A rot detector
must do the opposite. If it fails silently you have built a second layer of
prose claims with extra steps.

### 6. One ticket, one branch, one PR, one deploy preview

You proved this loop works yesterday. Naming the branch for the ticket
(`T-0042-local-news`) and putting the ID in the commit gives you the trail for
free, and makes `git log` answer "why does this line exist."

### 7. What not to build

Ceremony you will abandon, and which would make things worse by being
half-maintained:

- Story points, estimates, velocity. One editor. No sprint.
- More than the three states above, plus `PROPOSED` and `DISCARDED`.
- Epics as a separate object. A ticket can name a parent in a line of text.
- Any field you have to maintain by hand.
- **A migration of the 21 existing READMEs into tickets.** They are frozen
  session records and should stay that way. `docs/` already consolidates what
  was still true. Write tickets going forward only.

### 8. The agent writes the ticket, not you

You are action-biased and you will not maintain a tracker. So don't.

You say what you want. The agent writes the ticket, including the check block,
and you approve or redirect it. A ticket you had to format yourself is a ticket
you will stop writing by Thursday.

---

# Part II — drawn from your five-point riff

## Credentials

Agreed, and worth stating as a rule rather than a preference, because I got
close to the line this week by running `gh auth login` for you.

**The boundary: I can run anything that *uses* a credential. You perform
anything that *establishes* one.** I ran `gh auth login` in your terminal and
deliberately did not press Enter on the device-code step — that was the right
split and it should be the written rule, not a judgment call each time.

Corollary worth adding: **no credential ever passes through a chat message,
including in something you paste to me.** If I need a key, it comes from an
environment variable or an Actions secret you set. `ANTHROPIC_API_KEY` was
never in my environment this week and the work was fine — I built
`build_pairings.py` blind and you ran it. That is the correct shape, not a
limitation.

## The acceptance-criteria gap is the whole thing

This is the sharpest observation in your riff and I think you have already
diagnosed the root cause without naming it as one.

> A.C. has never been stored though so it really ought to be a step in the
> workflow.

Look at the four README failures in Part I through that lens:

| What shipped | The AC that was never stored |
|---|---|
| Em-dash discipline | "No em dashes in published output" |
| Local-news filter | "No classifieds in the local block" |
| `build_backstory.py` | "The app reads what the generator writes" |
| Backstory Slice 1 | "Nothing in Pulse can overwrite the library" |

Every one of those is a one-line check. Every one would have caught its failure
immediately. **Unstored acceptance criteria is the mechanism by which this
project accumulated three documents claiming a fix that didn't exist.**

So: acceptance criteria *is* the ticketing system. The tickets are containers
for it.

### Design for the mood fork, don't try to fix it

You described two modes: enthusiastic, where you skip AC and go build; and
uncertain, where you want to collaborate on it. The instinct would be to make
you always write AC first. Don't — you won't, and a process you route around is
worse than none.

Instead: **when you skip AC going in, the agent derives it coming out.** The
question at the end is not "did we meet the criteria" but *"what would I check
to know this still works six months from now?"* That is answerable from the
diff, it takes one exchange, and it produces exactly the same artifact.

This is what I did retroactively on the em-dash work — measured 33 across 7
stories, wrote the rule, and recorded "measure the next digest" as the check.
That worked. It just happened by accident, and it should be a step.

## agents.md and what Claude can build for itself

Naming this accurately, because the terms differ across tools:

- **`CLAUDE.md`** is the agents.md equivalent here. You have one. It is doing
  real work — this session was materially better after it existed.
- **`.claude/agents/*.md`** defines subagents: a name, a model, a tool
  allowlist, and instructions. These are the "execute for me" primitive.
- **Skills** (`.claude/skills/`) are packaged procedures invoked by name. This
  is the part worth your attention, because skills are how a repeated judgment
  becomes repeatable.

Candidate skills for NTK, all drawn from things that actually happened this
week:

| Skill | What it would do | Why it earns its keep |
|---|---|---|
| `ticket` | Write a ticket in house format, including the check block | Removes the reason you'd stop writing them |
| `rot` | Run every ticket's checks, report what went stale | The thing that catches README drift |
| `prepublish` | Integrity-check the lineup before publish — Today's keys against the stories, em-dash count, image presence | Two publishes shipped a mismatched Today overview |
| `voice` | Run a draft against VOICE_REF and the standing notes, report violations only | Your editorial rules exist as prose and are enforced by hope |

**An honest scoping note.** Subagents are good at bounded, verifiable work with
a clear done condition. They are not good at taste. `voice` can catch a signpost
verb and an em dash; it cannot tell you whether a lede lands. Build skills for
the first category and keep the second.

## Branches, Pages, Projects — the concrete answer

You said you don't know what you're talking about here. Here is the short
version, since you're deciding this with a fresh chat.

**Branches: yes, and you already have the habit.** One per ticket. The value
isn't organizational, it's the Netlify deploy preview — a real URL, with your
change, that isn't production. That is the single most useful piece of
development hygiene available to you and it cost nothing to set up.

**GitHub Pages: no, and actively retire it.** It is a second host serving a
second copy of this repo, and it has already burned you once — it is the only
reason Pulse works there and not on Netlify, which sent me to the wrong
diagnosis. Two hosts means two truths. Fix Pulse's data fetching and shut Pages
off.

**GitHub Projects: no.** It is a board over Issues, and it puts state back in a
place an agent needs a token to read. You would be trading the thing that makes
this stateless for a nicer view you'd check twice.

**What you're actually missing is smaller than any of those:** a check that
runs on a schedule and tells you when a claim went false. That's the Action in
Part I §5.

### On develop — staging — main

Raised 2026-09-17, and the honest answer is that you already have staging and
did not recognise it as such.

**Netlify deploy previews are the staging environment.** Every pull request
gets its own real URL running that change against production data
(`deploy-preview-2--<site>.netlify.app/today`). That is exactly what a staging
branch exists to provide, except one per change rather than one shared queue.

Three reasons gitflow would be worse here, not better:

1. **`main` receives automated commits every 20 minutes.** A long-lived
   `develop` branch would need constant rebasing against bot writes to
   `ntk-pulse/data/`, for no benefit. This is specific to this repo and it is
   disqualifying on its own.
2. **Gitflow coordinates teams shipping versioned releases through QA gates.**
   One editor, one daily digest, no release train. The ceremony has nobody to
   coordinate.
3. **A shared staging branch is a queue.** Put two changes in it and neither
   ships until both are ready. Per-PR previews have no such coupling.

**Recommended: keep `main` as the only long-lived branch.** Short-lived branch
per ticket, PR, preview, merge, delete. That is what shipped four changes on
2026-09-17 without incident.

**The one thing that would genuinely add:** a persistent non-production URL for
the cohort to look at between publishes. If that's wanted, it is a Netlify
branch deploy on a single `staging` branch — a settings change, not a workflow
change, and worth doing only when there is a reason to point someone at a
stable non-prod address. It does not require moving normal work off `main`.

### Canonical vs mirror, resolved

Decided 2026-09-17: **canonical.** When strategy documents come into the repo,
the repo copy becomes the real one.

The reasoning is not that the repo holds code — the Roadmap is not code. It is
that two copies of one truth always drift, and drift between copies is this
project's whole failure history. A mirrored Constitution would fail exactly the
way three READMEs claiming a nonexistent fix failed, only more slowly and with
higher stakes.

Direction of travel matters: generate a `.docx` or PDF **from** the repo copy
when someone needs one to read. Never re-import an edited Word file over the
canonical text.

## The corpus is the asset

Correcting my first pass at this. I had written that tickets will not serve
marketing, legal or hiring, and proposed a separate artifact for those. That
misread the requirement.

The point is not that a lawyer reads tickets. It is that development work should
**deposit into a corpus** rich enough for a later session to draw on when the
ask is a funder memo, a hiring brief, a crisis statement, or ad copy that has to
be true. The consumer is a future agent with no memory, and the corpus is what
it has to work from.

That reframes the design question from *what should a ticket record* to **what
makes the accumulated record retrievable and usable by something that wasn't
there.**

### What that changes

**Retrievability becomes a design requirement, not a nicety.** A synthesis task
("write the case for a second editor") needs to find the relevant material
without reading everything. That argues for consistent vocabulary in
frontmatter — a small, fixed tag set reused exactly, not free-text labels that
drift. Three spellings of the same idea is the same failure as three documents
claiming the same fix.

**The "why" field stops being optional.** See the tension noted in Part I: a
check makes a ticket verifiable, and a check alone makes it useless as corpus.
Both fields are load-bearing, for different readers.

**Learning is the highest-value deposit and nothing currently captures it.**
A closed ticket records that local news was fixed. It does not record that
*three separate documents claimed a fix that was never written* — which is the
genuinely interesting thing about how this project has worked, and the kind of
sentence that belongs in a grant application.

A thin `docs/log.md` would hold this: dated, a few lines, written only when
something surprised you. Not a changelog. The rule that keeps it worth reading
is that **an entry only earns its place if it would change someone's
behaviour.** "Fixed local news" wouldn't. "Our own documentation asserted fixes
that did not exist, three times, so we now verify with executable checks" would.

### The real gap in the corpus, which is bigger than ticketing

If the corpus is what a future session draws from, then the most strategically
valuable material NTK has is currently invisible to it.

The READMEs treat these as authoritative. None is in this repo, and no agent can
open any of them:

| Document | What it holds |
|---|---|
| `NTK_Editorial_Prompt_System_v14.docx` | The authoritative editorial system |
| `NTK_Editorial_Standards_Memo_v3_final.docx` | The "NTK Constitution" — the philosophy every prompt derives from |
| `NTK_Story_Selection_Brief_v3.docx` | The selection relay and sourcing rules |
| `NTK_Roadmap_v1.docx` | Monetization, SWIPE LEFT, the paid layer |
| `ntk_swot_v2.html` | Positioning and competitive read |
| `NTK_MomTest_Tracker.numbers` | **The only real audience evidence that exists** |

That last row is the sharpest. Every marketing, funder and hiring conversation
turns on audience evidence, and the Mom Test data is in an Apple Numbers file
outside the repo. It is the single highest-value thing that could enter the
corpus, and right now the answer to "what do we know about our readers" is a
file I cannot read.

**This is worth more than the ticketing system.** Ticketing prevents future
drift. Bringing this material in unlocks every downstream ask you named. They
are different problems and the second one is probably first in line.

Conversion is mechanical and mostly a decision about fidelity: prompts and
standards want to be text or Markdown in the repo, where they can be diffed and
where a check can assert the live copy matches; the Mom Test data wants to be
CSV; the SWOT and Roadmap want to be Markdown. Worth deciding once whether the
repo copy becomes canonical or stays a mirror — a mirror will drift, and this
project's whole failure history is drift between copies.

---

## What the next conversation should decide

1. **Ticket file format.** Frontmatter fields, and the exact shape of the check
   block. Bias toward fewer fields than feel right.
2. **Where checks live** — inline in the ticket, or a sibling script the ticket
   points at. Inline is more stateless; a script is more testable.
3. **Whether the rot detector opens a PR or just fails.** Opening a PR that
   flips `VERIFIED` to `STALE` means the trail is in git. Failing is simpler.
4. **Retroactive tickets: how many.** Recommendation: the six open defects in
   `docs/state.md` and nothing else. They already have anchors and most already
   have implied checks.
5. **Which of the four skills to build first.** Recommendation: `prepublish`,
   because it is the one with a failure that has already shipped twice, and
   because it will teach you what a check block needs to contain.
6. **The tag vocabulary.** A small fixed set, reused exactly, so a synthesis
   task can retrieve by theme. Decide it once and keep it short; drift here
   defeats the corpus.
7. **Whether the `.docx` corpus gap gets its own track.** Recommendation: yes,
   and ahead of this. The Mom Test tracker especially — it is the only real
   audience evidence NTK has and no agent can currently read it. Canonical-vs-
   mirror is already settled (canonical); what remains is conversion order and
   fidelity per document.

## One caution for that conversation

The thing being designed here is a system for catching drift between documents
and code. It would be an unusually bad outcome to design it as a large set of
documents. Whatever is decided should be runnable on day one, even if it starts
as four tickets and a twenty-line shell script.
