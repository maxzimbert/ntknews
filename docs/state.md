# Current state and open defects

**Verified 2026-09-15** by reading the code, not by trusting a README.
This is the fastest-rotting document in `docs/`. If the date above is old,
re-verify before relying on it.

Each defect below names the file and line. Every claim was checked.

---

## What is live right now

- **The digest contains six stories**, published 2026-09-16T18:12Z. The publish
  path works end to end: dated edition, six permalinks with OG tags, six
  decoded images, archive index, and the root landing-page hero all regenerated
  correctly from one button press. The prior edition (2026-09-14) was a single
  story.
- **Backstory has not been published since 2026-09-14** and is untouched by
  digest publishes — the two are decoupled by design, on separate buttons and
  separate commits. All six rows still carry empty narratives and
  `last_rewritten_at: null`; no Register 3 rewrite pass has ever been run. This
  is why the tab reads as out of date: not a wiring fault, an unpopulated
  feature. See defect #3 and `docs/backstory.md`.
- **v14 editorial prompts are deployed** in `ntk-pulse/pulse.html`. The July
  handoff's open item "v14 has not been deployed yet" is **resolved**.
- **URL routing works.** `/today`, `/backstory`, `/me` all rewrite to
  `digest/index.html`.
- **The Desk is retired**, manual-dispatch only, as decided.
- **Backstory renders six standing rows**, all with empty narratives.

---

## Resolved — READMEs that are now stale

`ReadMes (post 9:10)/ntk-url-routing_readme.md` lists two "manual edits still
outstanding." **Both are done:**

- `pulse.html:1167` — `GH_BACKSTORY_PATH = 'digest/data/backstory.json'` ✅
- `pulse-publish.yml` — commits `git add digest/ index.html …` ✅

---

## Open defects

### 1. The Today overview has no CSS applied — the paragraph breaks are gone

**Severity: high, fix is one word.**

`digest/index.html:1948` is:

```html
<div id="todayList"></div>
```

It has no class. The stylesheet defines the entire Today overview treatment
under `.today-overview` at lines **1719–1729** — padding, serif font, color,
and critically `.today-overview p { margin: 0 0 14px; }`. Nothing ever
receives that class, so **all of it is dead code**.

Combined with the global reset at line **70** (`* { margin: 0; padding: 0 }`),
the overview renders as an unpadded, edge-to-edge wall of run-together text
with no paragraph separation.

`buildToday()` writes the generated HTML into that div at line **2806**. The
`<p>` elements are produced correctly by `renderTodayOverviewHtml()` — they
just have no styling.

**Fix:** add `class="today-overview"` to the div at 1948.

Note the fallback path (when no overview exists) renders `.today-item` cards
that *do* carry their own classes and look fine — which is likely why this went
unnoticed.

---

### 2. Pulse publishes a stale Today overview, and nothing notices

**Severity: high. Confirmed systemic across two consecutive publishes.**

**Root cause, precisely:** Pulse sends whatever `today` object is in its state
at publish time, however old. Nothing — not Pulse, not `build_digest.py` —
checks that the overview was generated *for the lineup shipping beside it*.

Measured on the 2026-09-16 publish:

```
stories:              6   (keys 0443510d…, 4d768292…, 1ca48810…, …)
today.generatedAt:    2026-09-14T17:20:25Z     ← two days old
today onramp refs:    1   →  0 resolve, 1 dead (c9fd58cf808108bb)
```

`c9fd58cf808108bb` was the *September 14* lead story. The overview describes
Monday's AI-regulation news; the digest beneath it contains six unrelated
Tuesday stories.

The prior publish failed the same way and worse — a six-story overview carrying
seven onramp keys, over a one-story digest, **zero** of them resolving.

**Two independent checks are missing:**

1. `today.generatedAt` is never compared against the lineup it ships with.
2. The `[STORY: key]` markers are never validated against `stories[].key`.

`build_digest.py::regenerate_today()` (line 195) faithfully writes whatever it
is handed; it has no visibility into either question. The `idx === -1`
degradation guard in `renderTodayOverviewHtml()` works correctly — it drops
dead labels to plain text rather than emitting broken links — but that means
the failure is silent and reads as garbled prose rather than an error.

**Immediate operational workaround:** regenerate the Today tab in Pulse
immediately before every publish. There is currently nothing enforcing this.

**Proper fix** requires a decision (see `docs/decisions.md`): the absence of a
publish-time gate was deliberate, chosen so real failure modes would surface.
This one has now surfaced twice. Options are fail-hard (refuse the publish),
warn-and-continue, or auto-regenerate.

---

### 2b. Prior instance, for reference

**Severity: resolved into 2 above — kept because it shows the failure shape.**

`ntk-pulse/data/lineup-publish.json` — the single file that drives a publish —
contains:

- `stories`: **one** story, key `c9fd58cf808108bb`
- `today.text`: 2,696 characters of prose that opens *"Six stories today…"* and
  references **seven** `[STORY: …]` onramp keys

**None of those seven keys is `c9fd58cf808108bb`.**

So every onramp on the live Today tab hits the `idx === -1` branch in
`renderTodayOverviewHtml()` and silently degrades to plain text. The reader gets
four paragraphs about Russia, RFK Jr., Meta, Trump Jr., a UAE bank stake,
Chicago TIF spending, and GTA VI — and then a digest containing one story about
Anthropic.

The degradation guard itself is correct and working as designed. The problem is
upstream: **Pulse generated the overview against one lineup, the lineup was cut
to one story, and nothing at publish time checks that they agree.**

`build_digest.py::regenerate_today()` (line 195) faithfully writes whatever
`today.text` it is handed. It has no visibility into whether those story keys
exist.

**This is the thing to fix properly.** The obvious shape is an integrity check
at publish time: extract the `[STORY: key]` markers from `today.text`, compare
against the keys in `stories`, and either fail loudly or refuse to publish a
mismatched pair. Needs a decision about which — see `docs/decisions.md` on the
deliberate absence of an approval gate.

---

### 3. Backstory: the live feature and the documented feature are different features

**Severity: high. Full detail in `docs/backstory.md`.**

In short:

- Live in `digest/index.html`: six standing conflict rows with day counters.
  **All six narratives are empty strings.** The tab renders six rows that open
  to "No narrative yet."
- Documented as partially implemented in `backstory_part_2-chat-readme.md`: a
  21-row library with per-story pairings. **None of it is in the app.** Zero
  occurrences of `todays_pairings` or `.bsr-pairline` in `digest/index.html`.
- `editorial/build_backstory.py:27` writes to `digest/v2/data/backstory.json` —
  the **inert** tree. The app fetches `/digest/data/backstory.json`
  (`digest/index.html:2684`). The generator and the reader point at different
  files.
- `digest/v2/js/backstory.js` is the Part 2 renderer. Its header comment
  contains wiring instructions that were never followed. **No HTML file loads
  it.**
- `openBsrDetail()` at line **2727** populates kicker, number, title, milestone,
  narrative, and photo. It has no code path for the indicator, the object case,
  or the episode list.

---

### 4. The editorial prompt system exists in two copies, and they have drifted

**Severity: medium.**

`ntk-pulse/pulse.html:706` says:

> v14 EDITORIAL PROMPTS — spliced verbatim from ntk-production.html.
> This is the live production editorial system. Edit there, re-splice here,
> or edit both — but never let them drift silently.

They have drifted:

| Constant | `pulse.html` | `ntk-production.html` |
|---|---|---|
| `GLOBAL` | 4,680 chars | 3,695 chars |
| `VOICE_REF` | 2,559 chars | 1,926 chars |

`ntk-production.html` is an orphan — nothing routes to it — so **`pulse.html` is
the copy that actually runs**. But the comment asserts a sync that doesn't
exist, which will mislead the next person who reads it.

**Decision needed:** either delete the `ntk-production.html` copy and make
`pulse.html` the sole source, or reconcile them. Leaving a stale second copy
with a comment claiming it's authoritative is the worst of the three.

---

### 5. Pulse served from Netlify reads two-day-stale data

**Severity: high. Affects every editorial decision made in the tool.**

`netlify.toml`'s build-skip rule excludes `ntk-pulse/data/`:

```toml
ignore = "git diff --quiet HEAD^ HEAD -- . ':(exclude)ntk-pulse/data/' …"
```

`pulse-scan` and `pulse` write **only** into that folder, so **every bot commit
is skipped and never deploys.** Netlify's copy of `clusters.json`,
`lineup.json` and `window.json` therefore freezes until a commit touches
something outside the excluded paths — in practice, only a publish.

Measured 2026-09-16:

| | `lineup.json` assembled | lineup entries | window items |
|---|---|---|---|
| `ntknews.org/ntk-pulse/` | 2026-09-14T09:39 | 78 | 703 |
| `maxzimbert.github.io/ntknews/ntk-pulse/` | 2026-09-16T16:28 | 84 | 754 |

Last deploying commit was `8d5a46a` (publish: 6 backstory rows), Sept 14.

**The `pulse.html` file itself is byte-identical across both hosts** — only the
data differs. Comparing the HTML and concluding the hosts are equivalent is the
exact mistake that hid this.

**Workaround: author in Pulse from GitHub Pages**, which deploys every commit.
`?cache=clear` is a genuine cache-buster there (Pages CDN), though `pulse.html`
never reads the parameter.

**Do not "fix" this by removing the ignore rule** — that restores ~72 deploys a
day and the build-credit flood it was written to stop. The real fix is making
Pulse fetch its data from GitHub's API rather than relative paths, so it reads
the source of truth regardless of where the page is served.

---

### 6. Smaller items

- **Haiku model string is inconsistent.** `triage.py:27` pins
  `claude-haiku-4-5-20251001`; `build_digest.py:53` uses `claude-haiku-4-5`.
  Both resolve today. Worth unifying.
- **`handleSubscribeClick()` on permalink pages.** The generated story-page
  header calls a function that only exists in the SPA's JS. Unresolved — needs
  either a standalone implementation or a plain link.
- **Five Substack feeds are blocked** (Heather Cox Richardson, Daniel Larison,
  Mick Ryan, Caitlin Dewey, Casey Lewis). A browser User-Agent did not fix it;
  likely TLS-fingerprint blocking, which needs a real dependency to solve.
- **Two feeds fail XML parsing** — `jatan_mehta` has a known cause (the
  configured URL is a human subscribe page; the real feed is `jatan.space/rss`,
  never applied). `jared_dashevsky`'s cause is still unknown.
- **Two Netlify sites build from this repo — every deploy runs twice.**
  Verified 2026-09-16: `rainbow-sherbet-b2f0e9.netlify.app` and
  `ntknewscms.netlify.app` both serve production and both built a deploy
  preview for PR #2. All three of those and `ntknews.org` return byte-identical
  content. On an account where a deploy flood already consumed ~250 credits,
  this is doubling ongoing build spend for no benefit.

  **Before deleting either, confirm in the Netlify dashboard which site holds
  the `ntknews.org` custom domain.** Content hashes cannot distinguish them,
  and deleting the wrong one takes the site down.

---

## Contradictions between READMEs, resolved

Recorded so they don't get re-litigated:

| Question | Answer |
|---|---|
| Is the story-list `i === 0` image gating a bug? | **No — it's the intended design.** `README-ntk-pulse-automation.md` lists it as an open bug; `ntk-pulse-sonnet5-migration-and-permalinks.md` §6 records Max explicitly clarifying that only story #1 gets the hero treatment in the list view, and that any story with an image shows it in the reading view. The latter is correct. Code at `digest/index.html:2277,2282` matches it. |
| Which app file is canonical? | `digest/index.html`. Not `digest/v2/index.html`. |
| Is v14 deployed? | Yes, in `pulse.html`. |
| Which Backstory design is the plan? | Part 2 (per-story pairings). See `docs/backstory.md`. |
