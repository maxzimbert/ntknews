---
id: T-0073
title: The Beginnings timeline's line starts above the first bullet and runs half a pixel off the bullets' centre
status: VERIFIED
tags: [backstory, defect]
anchor: digest/index.html:593
---

## What

Reported by the editor 2026-10-05 against the live timeline: "the line is off centre through the
bullet point and the line begins above the first bullet point". Measured the same day on
`ntknews.org/backstory/america-abroad/` (the static page; the in-app overlay uses the same rules
under `.bp-` names):

- **Line starts too early.** The first row's line starts at 0px from the top of its row; its
  bullet's top is 7px down, so the line pokes 7px above the first bullet. The rule meant to start
  it at the bullet, `.tr:first-child .td::before { top: 11px }`, never matches: the first child of
  the Beginnings `<section>` is the "Beginnings" label, not a row. The `:last-child` rule is fine
  because the last child is a row.
- **Line off centre.** The 20px column puts the bullet's centre at 10.0px and the 1px line's
  centre at 10.5px (a 9px bullet on `left: 50%` with `margin-left: -4.5px`, and a 1px border drawn
  from `left: 50%`).

Fix in both copies of the markup, which must be kept in step (T-0059): `digest/index.html`
(`.bp-tr`, `.bp-td`) and `editorial/build_backstory_pages.py` (`.tr`, `.td`). Start the first row's
line with a sibling selector (`label + row`) or wrap the rows in their own container; use an
even-width bullet or centre the line on it.

## Why

Small, but it is the one visual on the row page the editor looks at first, and the geometry error
is the kind that reads as "janky" without anyone being able to say why. It came from a selector
assumption (the row is its parent's first child) that was true in the mock, which has no label
above the rows, and false on the real page. Measuring the page rather than eyeballing the
screenshot is what found the 0.5px.

## Check

```sh
python3 - <<'PY'
import re, sys
bad = []
for path, row in (("digest/index.html", "bp-tr"), ("editorial/build_backstory_pages.py", "tr")):
    s = open(path, encoding="utf-8").read()
    # the rule that starts the line at the first bullet must not rely on :first-child of the section
    if re.search(rf"\.{row}:first-child\s+\.(bp-)?td::before", s):
        bad.append(f"{path}: the first-row line rule uses :first-child, which matches the label, not the row")
if bad:
    sys.exit("OPEN: " + "; ".join(bad))
PY
```

After the fix the editor should also look at a row page and the in-app overlay. The check only
proves the broken selector is gone; whether the line looks centred is a judgement.

## Built 2026-10-05

Both copies fixed. The first row's line now starts at the bullet (`label + row` selector); the
bullet (9px at left 6) and line (1px at left 10) share a centre on whole pixels, in a 21px column.
Measured after the change on the static page and in the in-app overlay: bullet centre 10.5px, line
centre 10.5px, first row's line top 11px (bullet centre 11.5px), last row's line ends at 11px. Before:
10.0 and 10.5, and 0px (7px above the bullet). A single-row timeline draws no line. Was BUILT, not
VERIFIED, until the editor has looked at it.

## Shipped 2026-10-06

Merged (#68, #69) and confirmed on ntknews.org: the static pages carry the new timeline rules and the app reserves 88px under the Backstory list. The editor reviewed both on staging before the merge.
