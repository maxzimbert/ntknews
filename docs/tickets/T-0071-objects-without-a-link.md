---
id: T-0071
title: 50 matrix objects still have no primary-source link
status: DECIDED
tags: [backstory, chore]
anchor: editorial/NTK_Backstory_Object_Matrix.xlsx
---

## What

Measured 2026-10-05: 334 of 384 matrix objects have a link; 50 do not (Equality 14, America
Abroad 10, Government 7, Work 5, Power 4, the rest spread). Split out of T-0068, whose
checker and eligibility rule are built. An object without a link is never chosen, so this costs
selection, not correctness, but every row's pool is smaller than it should be, and seven of the
48 sub-genres have fewer than two linked objects.

The list, with what was tried for each and why the earlier links were pulled, is
`editorial/NTK_Backstory_Link_Review.xlsx`, tab "No link yet". Some of its entries are links the
editor or a research pass proposed that did not hold: a lending-library copy of an in-copyright
book, a page about a document rather than the document, a link to a different speech or a
different year, a page that showed an error. Do not put them back without opening them.

## Why

Two earlier research rounds linked 296 objects but the second found only 20 of 87, because the
agents hit a 200-search cap and archives such as Founders Online, loc.gov and state.gov refuse
scripts (T-0067). The remaining objects are the hard ones, so the cheapest route is likely the
editor recognising a document and pasting its link, as happened with 11 of the last 12 supplied.
Any link added is then run through `editorial/check_links.py`, which also reports a matrix year
that does not appear on the page.

## Check

manual: the editor supplies or approves links for the objects on the review sheet's "No link yet"
tab, or decides which can stay unlinked.
