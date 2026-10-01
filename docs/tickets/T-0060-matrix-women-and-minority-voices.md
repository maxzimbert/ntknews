---
id: T-0060
title: The Object Matrix has almost no women or minority voices before 1981
status: DECIDED
tags: [backstory, feature]
anchor: editorial/NTK_Backstory_Object_Matrix.xlsx
---

## What

Measured 2026-10-01 on `editorial/NTK_Backstory_Object_Matrix.xlsx`, sheet
`Objects`: 345 objects, of which 217 are Hofstadter (`Era` "Hofstadter
1760-1981"), 38 are "Addition, pre-1981" and 90 are "Extension 1981-2026".
Searching the `Author` column for Addams, Du Bois, Douglass, Truth, Anthony,
Stanton, Wells, Parks, Chisholm and Malcolm finds none. Martin Luther King
appears once (1963, "I Have a Dream"). A Booker T. Washington text is not
present (the three "Washington" hits are George Washington and George
Washington Plunkitt). Hofstadter's anthology is a mid-century selection of
mostly official and male voices, so the gap follows from the source.

The editor wants the matrix widened with women and minority voices, as new
rows in the existing "Addition, pre-1981" mould, running from Jane Addams
through W.E.B. Du Bois and Booker T. Washington to Malcolm X and Martin
Luther King, plus the figures of the 1940s civil rights movement. Each added
object needs the matrix's existing columns (year, title, author, source, NTK
Row, sub-genre) and a citation that resolves to a primary text.

**To confirm with the editor before anyone searches:** the editor wrote "Julia
Dent Grant's litigation". I could not match that to a case I can name with
confidence, and it may be a different person or a different Grant. Not
searched, not in the check below.

Rows most likely to take additions (unverified, from reading the row
contests, not from the data): Equality, Work, Family, Order, The Media,
Government, Faith.

## Why

A Backstory that says "where today's story starts" and draws only on a
mid-century canon will repeat that canon's omissions, and Jamie, who assumes
outlets are spinning her, is the reader most likely to notice. Ruled out:
adding names from memory. The T-0045 and T-0047 sessions both found model
recall wrong on dates, quotes and figures. Every added object needs a real
lookup against a primary or credible secondary source, and the editor
approves the list before it reaches `backstory.json`. Cost note: it is a
research and editing task, so the cost is mostly the editor's review time, not
API spend.

Feeds T-0062 (Beginnings loaded from the matrix) and pairs with T-0061 (the
modern scholarly layer). `build_backstory.py`'s `pick()` takes the two
earliest pre-1981 objects and the two latest, per row (read 2026-10-01), so
added voices from 1900 to 1970 will not render until that selection is
revisited under T-0062.

## Check

```sh
python3 - <<'PY'
import openpyxl, sys
ws = openpyxl.load_workbook("editorial/NTK_Backstory_Object_Matrix.xlsx", read_only=True)["Objects"]
rows = list(ws.iter_rows(values_only=True))
a = rows[0].index("Author")
authors = " | ".join(str(r[a]) for r in rows[1:] if r[a]).lower()
need = ["addams", "du bois", "booker t. washington", "malcolm x"]
missing = [n for n in need if n not in authors]
if missing:
    print("missing from matrix:", missing); sys.exit(1)
PY
```
