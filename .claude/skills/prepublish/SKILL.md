---
name: prepublish
description: Check an NTK edition before it ships. Use when the user says "check the digest", "am I ready to publish", "prepublish", "run the publish check", or asks whether the lineup is safe to send. Also use straight after a publish that went wrong, to find out what got through.
---

# Checking an edition before it ships

Run the script. Read the output. Report it. Do not re-implement the checks in
conversation, and do not add judgments the script did not make.

```bash
python3 scripts/prepublish.py
```

With no argument it reads `ntk-pulse/data/lineup-publish.json`, which is the
edition **already live**. That is an audit, not a pre-flight.

To check one *before* it goes out, Max clicks **download story data** in Pulse
and passes the file. It is byte-identical to what the publish button sends:

```bash
python3 scripts/prepublish.py ~/Downloads/ntk-stories-2026-09-18.json
```

If he asks to check before publishing and has not downloaded anything, ask for
that file rather than silently auditing the last edition. Reporting the
previous digest as though it were the next one is this project's signature
failure wearing a new hat.

## What the output means

**BLOCKER** — something downstream cannot build, or will build wrong. A story
with no headline, an edition where every section came back
`[INSUFFICIENT SOURCE MATERIAL]`, a Today onramp pointing at no story, em
dashes over T-0004's threshold. Exit code 1. Say plainly that it should not
ship until these are fixed.

**warning** — the editor's call, not the script's. A missing image, a Truths
section with no citation, a story count outside the range in
`docs/decisions.md`. Never fails the run. Report them; do not argue them.

## What this cannot do, and must not pretend to

It counts and it resolves. It cannot tell you whether a lede lands, whether the
lead story is the right lead, or whether the Lies section is fair. A version
that pretended to judge those would be worse than none, because it would be
trusted. If Max asks "is this good?", the honest answer is that the script says
nothing about that and the only way to know is to read it.

## Related

- The same headless-story rule runs in two other places, on purpose:
  `publishPreflight()` in `ntk-pulse/pulse.html` warns at the button, and
  `drop_headless()` in `ntk-pulse/build_digest.py` refuses to build one.
  `docs/decisions.md` records why a prompt rule alone is not enough.
- Several checks here duplicate ticket checks in `docs/tickets/`. That is
  intended. `scripts/rot.sh` answers "has a past claim gone false"; this
  answers "is this edition safe to send", at the moment it matters.
