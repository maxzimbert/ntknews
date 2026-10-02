---
id: T-0066
title: Consider moving the Object Matrix from a spreadsheet to a database
status: PROPOSED
tags: [backstory, decision]
anchor: editorial/NTK_Backstory_Object_Matrix.xlsx
---

## What

Parking lot, raised by the editor 2026-10-02. The matrix is an xlsx with one
`NTK Row` and one `Sub-genre` per object (384 objects). Two things push toward
a database: objects that could sit under more than one row (Angelina Grimke's
1836 *Appeal* is Equality or Faith), and state that changes by the day, such as
whether an object's link is still live (T-0065).

Workaround that works today: list the object twice, once per row. Link-health
state does not need the matrix at all; a generated file beside it holds it, so
the xlsx stays hand-edited.

Not decided, not started. Revisit when the duplicate-row workaround or the
generated link file starts to hurt.

## Why

Ruled out for now by the editor's own framing ("it can wait"). The spreadsheet
is also what lets candidates be reviewed in a familiar format and graduate into
the matrix by copying rows, which is how 39 objects arrived on 2026-10-02. Any
database has to keep that review path or it costs more than it saves.

## Check

manual: revisit when an object genuinely needs two rows, or when link-health
state outgrows a generated file.
