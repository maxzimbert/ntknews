---
id: T-0047
title: All 14 held-row indicator numbers are unverified against their named source
status: DECIDED
tags: [backstory, chore]
anchor: editorial/build_backstory.py:63
---

## What

Confirmed 2026-09-28, directly from `digest/data/backstory.json`: all 14
`held` rows carry an `indicator` object, and every single one has
`"verified": false`. This isn't a partial rollout — `editorial/build_backstory.py`'s
`IND` dict (`editorial/build_backstory.py:63-77`) says so about itself,
in its own comment: "EVERY VALUE HERE IS UNVERIFIED. Check against the
named source before publishing." Nobody has yet.

The 14, with their claimed source:

| Row | Claim | Source |
|---|---|---|
| climate | Atmospheric CO2, 351→425 ppm, 1988→now | NOAA Global Monitoring Laboratory |
| media | Trust the press, 72%→31%, 1976→now | Gallup |
| immigration | Foreign-born population share, 4.7%→15%, 1970→now | U.S. Census Bureau |
| faith | No religious affiliation, 7%→28%, 1980→now | Pew Research Center |
| taiwan | PLA median-line crossings, ~0→3,000+/yr, 2019→now | Taiwan Ministry of National Defense |
| government | Trust Washington, 73%→22%, 1958→now | Pew Research Center |
| order | Violent crime/100k, 758→370, 1991→now | FBI Uniform Crime Reports |
| america-abroad | Troops stationed abroad, ~1M→~170k, 1970→now | Defense Manpower Data Center |
| power | Other party "threatens the nation," ~20%→~70%, 1994→now | Pew Research Center |
| work | Union membership share, 24%→10%, 1973→now | Bureau of Labor Statistics |
| family | Median first-marriage age (women), 21→28, 1970→now | U.S. Census Bureau |
| equality | Black/white family wealth per $100, ~$16→~$15, 1983→now | Federal Reserve SCF |
| korea | Est. NK nuclear warheads, 0→~50, 2005→now | Federation of American Scientists |
| bomb | Nuclear warheads worldwide, ~70,000→~12,000, 1986→now | Federation of American Scientists |

Live product surface for this: T-0046's new Backstory permalink pages
(`/backstory/<row-id>/`) render an explicit "Unverified" badge next to
every one of these — confirmed by the editor viewing the deploy preview
directly and asking what it meant.

## Why

Raised directly by the editor after seeing the badge on a real page and
asking what it means — an honest signal working as intended, but the
actual goal is clearing it, not leaving 14 rows permanently flagged.

**Scope is smaller than T-0045, and shaped differently.** T-0045 is an
ongoing generation mechanism (quotes for objects, which grow as rows and
objects are added). This is a bounded, one-time backfill: 14 fixed
numbers, checked once, done. It doesn't need a pipeline step — it needs
someone (or an assisted research pass) to actually go look, the same way
T-0045's 8 quotes got checked by hand this session against Gutenberg,
Cornell LII, Wikisource, and the source's own site rather than trusted
from memory.

**The same risk T-0045 named applies here, maybe more sharply.** A
number is easier to misremember confidently than a quote — "72%" and
"73%" both sound plausible for "trust in an institution, mid-20th
century," and being off by a point or a year on a Gallup/Pew figure is a
much quieter failure than a garbled quote, harder to catch on a read-
through. Whatever checks these needs to pull the actual named source
(WebSearch/WebFetch or a human doing the same), not answer from
training-data recall.

**What happens when a checked number turns out wrong.** Not decided
here — options are (a) correct the value and the year to match the real
source, or (b) if the underlying claim doesn't hold up at all (the
metric doesn't exist in that form, or the direction is wrong), replace
the indicator entirely. Either way the row shouldn't ship `verified:
true` on a number that was corrected without someone independently
confirming the correction — same posture as T-0045's "never
auto-promoted by the generation step itself."

**`carry()` in `build_backstory.py` already preserves `indicator.as_of`
and `.verified` across rebuilds** — this is genuinely a one-time cost
per number, not something that resets on the next `build_backstory.py`
run, so it's worth doing properly once rather than treating as
disposable.

## Check

```sh
set -e
python3 - <<'PYEOF'
import json, sys
from pathlib import Path

data = json.loads(Path("digest/data/backstory.json").read_text())
held = [r for r in data["rows"] if r["stratum"] == "held" and r.get("indicator")]
if not held:
    sys.exit("no held rows with an indicator to check")

unverified = [f"{r['id']} ({r['indicator']['label']})" for r in held if not r["indicator"].get("verified")]
if unverified:
    sys.exit(f"OPEN: {len(unverified)}/{len(held)} indicators still unverified: {', '.join(unverified)}")

print(f"all {len(held)} held-row indicators report verified:true")
PYEOF
```

**Not yet run for real.** DECIDED, not started — this check will report
OPEN today, correctly, since all 14 are unverified. Promote to VERIFIED
only once every row above has actually been checked against its named
source (confirmed as-is, or corrected and re-confirmed) — not on the
strength of someone flipping the flags without doing the lookups.
