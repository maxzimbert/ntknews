---
name: ticket
description: Open, close, or verify an NTK ticket in docs/tickets/. Use when the user says "open a ticket", "file this", "log that", "close T-00xx", "mark that verified", or describes a defect or a piece of work that should be recorded rather than done immediately. Also use at the end of a change to derive the check for work that was built without one.
---

# Writing an NTK ticket

Read `docs/tickets/README.md` first — it holds the format and the status
vocabulary. This skill is about how to fill it in well.

Max will not format these by hand and should never be asked to. He says what he
wants; you write the file, including the check block; he approves or redirects.

## Before you write anything, verify

Do not write a ticket from a description, a README, or a previous session's
summary. **Read the code and measure the current state.** This repo has a
documented history of documents asserting fixes that were never written — three
separate cases — and a ticket written from prose inherits that.

Concretely: `grep` the constant, run the parse, count the thing. Put the
measurement and its date in the `What` section. If you could not verify
something, say "unverified" in the ticket rather than asserting it.

## The check block

The check is the only field that cannot rot. Get it right.

**Run it before you commit the ticket.** `bash scripts/rot.sh T-00xx`. A check
you have not executed is a claim, which is the thing this system exists to
replace. Read the failure output too — a check that reports the wrong number is
as bad as no check, and the only way to find that is to look.

**Assert the outcome, not the mechanism.** "No onramp key is dead" survives
three different fixes. "`validate_today()` exists" survives one.

**Pick a threshold that tolerates legitimate exceptions.** A check that fires on
a correct quotation gets ignored, and an ignored check is worse than none.

**Write `manual:` when it is honestly manual.** Netlify dashboard state, whether
a lede lands, whether six pairing lines read well. These are reported and never
passed. A decorative check that always passes is the failure mode.

**Never weaken a check to make it green.** If a VERIFIED check fails, the code
broke or the claim was always false.

## The why block

This is the corpus. A future session with no memory writes a funder memo, a
hiring brief or a crisis statement from these paragraphs, so write for a
stranger.

Include: what it costs or risks; what was ruled out and on what grounds; any
decision in `docs/decisions.md` this touches; what you tried that did not work.
Exclude: restating the check in prose.

An entry earns its place if it would change someone's behaviour. "Fixed local
news" would not. "Comparing the HTML across two hosts and concluding they were
equivalent is what hid a two-day data staleness for days" would.

## Status

Three states, never collapsed: `DECIDED` (called, not built), `BUILT` (code
exists, unconfirmed), `VERIFIED` (a check ran and passed). Plus `PROPOSED` and
`DISCARDED`, both skipped by the rot detector.

Only move a ticket to `VERIFIED` after you have watched its check pass. Never
on the strength of having written the code.

## Deriving a check after the fact

When work was built without acceptance criteria — which is the normal case, and
not worth fighting — derive the check from the diff at the end. The question is
not "did we meet the criteria." It is:

> **What would I check to know this still works six months from now?**

One exchange, and it produces the same artifact as writing it up front.

## Closing the loop

Branch `T-00xx-short-slug`, one PR, Netlify deploy preview, merge, delete. Put
the ID in the commit subject.

If something surprised you — not "this was hard", but "what I believed was
wrong" — add three lines to `docs/log.md`. That file is the learning record and
its only rule is that an entry must be capable of changing someone's behaviour.
