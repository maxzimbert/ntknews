# NTK News — orientation

Read this first. It is the entry point for every session, human or model.
If something here contradicts a README in `~/Desktop/NTK/ReadMes (post 9:10)/`,
**this wins** — those files are per-conversation records, frozen at the moment
each chat ended, and several are now wrong about the code.

Last verified against the repo: **2026-09-17**.

---

## What NTK is

A daily news digest for people who have opted out of news. One editor (Max
Zimbert). Nonprofit posture. Every story is written in four sections —
**Truths / Probabilities / Possibilities / Lies** — at a deliberately plain
reading level. The reader persona is "Jamie": time-poor, news-avoidant,
assumes most outlets are spinning her.

The product promise is **closure**. The digest ends. There are no unread
counts and no infinite scroll, on purpose. Sessions-per-day is an anti-metric.

Live at `ntknews.org` (Netlify, continuous deploy from `main`, no build step).

---

## How work reaches production

**Historically:** copy-paste from a Claude chat into GitHub's web editor. That
workflow is the direct cause of the version drift documented throughout this
file — no history, no diff, no way to know which copy was newer.

**Now:** this repo is cloned at `~/Desktop/NTK/ntknews`. Work here, commit here.

**Two automated bots commit to `main` on their own schedule.** `pulse-scan`
runs every 20 minutes and `pulse` every 4 hours, both writing to
`ntk-pulse/data/`. The working tree goes stale fast.

```bash
git pull --rebase
```

Run that before you start and before you push. Always.

---

## The file map

The single most confusing thing about this repo is that eight files look like
the app and only two are.

### Live — changes here reach readers

| Path | What it is |
|---|---|
| `digest/index.html` | **The app.** Today / Digest / Backstory / Profile, real URL routing. ~4,000 lines, one file. |
| `index.html` | Marketing landing page at `ntknews.org/`. Its hero mirrors the current lead story. |
| `ntk-pulse/pulse.html` | **The CMS.** Where the editor certifies stories, generates the four sections, and publishes. Browser-only, ~204KB. |
| `ntk-pulse/*.py` | The pipeline. See `docs/architecture.md`. |
| `netlify.toml` | Routing. Five rules, all load-bearing. |
| `netlify/functions/news.js` | The only server-side code in the stack. |

### Inert — kept so old links resolve, routed to by nothing

| Path | Why it's still here |
|---|---|
| `digest/v2/index.html` | The pre-routing app. Dated editions under `digest/v2/2026-08-*/` still resolve as static files. Do not edit. Do not delete. |
| `digest/v2/data/`, `digest/v2/js/` | Same. See the warning in `docs/backstory.md` — a live script still writes here. |

### Orphans — nothing routes to these

`ntknews-index.html` · `ntknews-momtest.html` ·
`editor.html` · `article-generator.html` · `ntk-desk/` · `rss-scanner/`

`ntk-desk/` is a **retired** system, kept as a lessons-learned artifact. Its
workflow is manual-dispatch only. Do not revive it, and do not tune its
clustering — that decision is recorded in `docs/decisions.md`.

---

## The docs

| File | What it holds |
|---|---|
| `docs/architecture.md` | How the pipeline actually runs, end to end. |
| `docs/state.md` | Narrative state — what is live right now. **Rots fastest — check the date at the top.** |
| `docs/tickets/` | **Open work, each with a check that can fail.** Start here. |
| `docs/log.md` | Dated notes on what turned out to be wrong. Corpus material. |
| `docs/decisions.md` | Choices that were made deliberately and should not be silently re-decided. |
| `docs/backstory.md` | The Backstory feature and its build plan. |
| `docs/backlog.md` | What's next, roughly prioritized. A working list, not a commitment. |

---

## The flow

Open work lives in `docs/tickets/`. Each ticket carries an executable check, so
a claim about this codebase can fail rather than quietly rot. Run them:

```bash
bash scripts/rot.sh
```

`OPEN` is expected — that is work not done yet. `STALE` means something marked
VERIFIED stopped being true, and it exits 1. The same script runs daily and on
every PR (`.github/workflows/rot.yml`).

To open one, ask for it — "open a ticket for X" — and the `ticket` skill writes
it in house format, check block included. Do not format these by hand.

Then: branch `T-00xx-short-slug`, PR, look at the Netlify deploy preview, merge,
delete. Put the ticket ID in the commit subject so `git log` answers "why does
this line exist."

If you built something without saying up front how you'd know it worked — which
is normal — derive the check at the end from the diff. The question is not "did
we meet the criteria," it is **what would I check to know this still works six
months from now.**

If something surprised you, three lines in `docs/log.md`. Only if it would
change someone's behaviour.

---

## Rules for working in this repo

1. **`git pull --rebase` before you touch anything.** Bots commit every 20
   minutes.
2. **Read `docs/decisions.md` before proposing a change.** Much of what looks
   like an oversight here is a decision someone already argued through. The
   reasoning is recorded so it can be re-examined — not so it can be ignored.
3. **Do not delete inert files.** `digest/v2/` holds real reader-facing URLs.
4. **Test generated output by running it, not by reading it.** This codebase
   has a documented history of silent failures: regex substitutions that
   no-op, Python escapes that corrupt JS strings, prompt-only fixes that look
   sufficient and aren't. Run `node --check` on modified JS. Run the real
   pipeline against fixtures for Python.
5. **Never commit API keys.** Anthropic and Recraft keys live in the editor's
   browser `localStorage` and in GitHub Actions secrets. Nowhere else.
6. **A ticket's check must be run, not just written.** `bash scripts/rot.sh
   T-00xx` before you commit it, and read the output — a check that reports the
   wrong number carries the authority of having executed and is worse than no
   check. Never weaken a check to make it pass.
7. **Say when something is unverified.** Several READMEs in this project
   asserted things with more confidence than the evidence supported, and the
   cost was real debugging time. "I haven't checked this" is a useful sentence.

---

## Working with Max

Recorded from prior sessions, and worth honoring:

- **Push back when you disagree.** Sycophancy is explicitly unwanted.
- **Name cost tradeoffs plainly.** API spend is a live constraint.
- **Small ships beat comprehensive plans.** If a discussion has gone three
  turns without a concrete next step, produce something.
- **The editorial vision is stable and considered.** The four-section
  framework, the register ladder, the reader profile — these are not
  up for casual redesign.
