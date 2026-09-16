# NTK News — orientation

Read this first. It is the entry point for every session, human or model.
If something here contradicts a README in `~/Desktop/NTK/ReadMes (post 9:10)/`,
**this wins** — those files are per-conversation records, frozen at the moment
each chat ended, and several are now wrong about the code.

Last verified against the repo: **2026-09-15**.

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

`ntk-production.html` · `ntknews-index.html` · `ntknews-momtest.html` ·
`editor.html` · `article-generator.html` · `ntk-desk/` · `rss-scanner/`

`ntk-desk/` is a **retired** system, kept as a lessons-learned artifact. Its
workflow is manual-dispatch only. Do not revive it, and do not tune its
clustering — that decision is recorded in `docs/decisions.md`.

`ntk-production.html` is a special case: it is an orphan, but it holds a second
copy of the editorial prompt system. See `docs/state.md`.

---

## The docs

| File | What it holds |
|---|---|
| `docs/architecture.md` | How the pipeline actually runs, end to end. |
| `docs/state.md` | What is true right now, and the open defects. **Rots fastest — check the date at the top.** |
| `docs/decisions.md` | Choices that were made deliberately and should not be silently re-decided. |
| `docs/backstory.md` | The Backstory feature, which currently exists as two incompatible designs sharing one name. |

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
6. **Say when something is unverified.** Several READMEs in this project
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
