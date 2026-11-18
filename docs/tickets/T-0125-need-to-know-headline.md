---
id: T-0125
title: Punch-up offers a need-to-know headline, a standing truth and then today's fact
status: BUILT
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Pulse's punch-up button (`punchUpHeadline`) returned three sharper headlines, all in the house shape of fact plus
consequence. It now returns two of those and one **need-to-know** headline (or, when none is both certain and strong, a line saying why): two sentences, the first a standing
truth the coverage skips because it is not new, the second today's fact. The rules are in `NTK_HEADLINE_RULES`. The
Lineup lists it last, labelled "need to know", with a line saying what the first sentence rests on ("in the
sources", or "background:" and the fact to check). The editor picks it or not, as before.

Measured 2026-11-17 against the last edition (2026-11-10, seven stories): every headline stated the event, and
the consequence was the next event ("Shareholders Sued Within Minutes"). None said why the story is need to know.

Tried before shipping on three of the day's Stream clusters, with Sonnet standing in for Pulse's Sonnet 5.5 (no API
key outside the editor's browser):
- Tariff refunds: "Tariffs Are Paid by the Importing Company at the Border. Companies Now Get Billions Back While
  Consumers Keep the Bill." The shape working as meant.
- Nvidia: reused the example's first sentence word for word. True, but it showed the copying risk; a rule was added.
- FBI cyber warning: "The FBI Investigates Cybercrime Against U.S. Companies." A job description that makes nothing
  land harder. The prompt then named this as the weakest kind, and the rerun invented one instead ("The FBI Warns
  Businesses About Threats Only When It Sees Them Spreading"). Forcing a standing truth invites invention, so the
  model may now return none and say why; the Lineup shows "no need-to-know headline:" and the reason. Third run: it
  declined, saying the only certain standing truths restate an actor's job.
- Reruns after the changes: tariffs held ("Importers Pay Tariffs at the Border and Price Them Into What Shoppers
  Buy…", its basis flagging that pass-through is debated); Nvidia kept the example's chip sentence, now with a
  stronger second ("Its Board Just Refused to Take Back the Founder Who Built It").

Not yet seen on prod Sonnet 5.5 with the editor's key. Not changed: the `[HEADLINE]` Generate Jefferson writes in
Truths, triage's headlines, and the house rule in `docs/voice.md` section 3.

## Why

The editor, 2026-11-17: the digest "can feel too incremental and headliney instead of powerful 'statements of the
obvious forcefully'". Talked through the same day: the aim is a need-to-know digest, for people who want to get
clear on what's news and how and why it came to be. Need to know is not personal impact (the editor corrected that
reading): Nvidia is need to know for what it holds up, the Trump and Biden letters for the historical record, a
scandal partly because people will talk about it. The lineup mostly passed that test. What failed was the card:
the headline never said which reason put it there.

Ruled out for now: changing the headline rule outright. It is a written voice rule, and the evidence for changing it
should be the editor choosing this option in real editions, not one conversation. If he keeps picking it, the next
step is the voice rule and Jefferson's `[HEADLINE]`, so the standing truth reaches the Truths and Today.

The risk is the first sentence, which is where spin enters. "Nvidia makes the chips AI runs on" is checkable; "X is
corrupt" is a verdict, and a reader who assumes outlets are spinning her hears a verdict as the con. So the rules:
a reader on either side would agree it is plainly true; background knowledge is allowed but no number, date or
ranking that is not in the sources; and the editor sees what it rests on. The 90-character cap stays for the two
plain headlines; this one may run to 140, which matches what the edition already publishes (every 2026-11-10
headline ran past 90).

Cost: none worth counting. Same single Sonnet call per punch-up, about 200 more tokens out.

Related: T-0126 (standing topics), the other half of the same conversation.

## Check

```sh
node scripts/test_punch_up.js >/dev/null || exit 1
echo "manual: on prod Pulse, punch up three real stories; the need-to-know option is labelled, its first sentence is plainly true and makes the second land harder"
exit 1
```
