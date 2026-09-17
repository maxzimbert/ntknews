# Proposal — a stateless ticketing system for NTK

**Status: proposal, not decided.** Written 2026-09-17 at the end of a two-day
session, as the handoff for a separate conversation that will design this
properly.

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

## The digital trail for everything downstream

Marketing, PR, crisis, legal, hiring, investment. This is a genuinely different
requirement and I want to separate it cleanly, because tickets will not serve
it.

Tickets answer *what changed and is it still true*. Those functions ask
different questions:

- **Why does this exist?** → decision records, which you now have in
  `docs/decisions.md`. Keep the format: the decision, the reasoning, and what
  would have to change to reverse it. That file is already the most useful
  document in the repo for a lawyer or an investor, and neither was its
  intended audience.
- **What happened, in order?** → git log, if commit messages stay narrative.
  The messages from this week ("this was recorded as though a rule existed; it
  did not") are the artifact. Keep writing them that way; a one-line commit
  message is a lost explanation.
- **What did we learn?** → this is the gap, and tickets won't close it. A
  closed ticket records that local news was fixed. It does not record that
  *three separate documents claimed a fix that was never written*, which is the
  thing worth telling anyone about how this project works.

For that third one, consider a thin `docs/log.md` — dated, a few lines per
entry, written only when something surprised you. Not a changelog. The rule
that keeps it useful: **an entry is only worth writing if it would change
someone's behavior.** "Fixed local news" wouldn't. "Our documentation asserted
fixes that didn't exist, three times, and we now verify with executable checks
instead" would — and that is a paragraph you could hand to a funder, a hire, or
a reporter without editing.

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

## One caution for that conversation

The thing being designed here is a system for catching drift between documents
and code. It would be an unusually bad outcome to design it as a large set of
documents. Whatever is decided should be runnable on day one, even if it starts
as four tickets and a twenty-line shell script.
