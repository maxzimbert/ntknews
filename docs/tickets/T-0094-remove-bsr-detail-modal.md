---
id: T-0094
title: The old Backstory detail modal (openBsrDetail) is gone from the reader app
status: VERIFIED
tags: [digest, chore]
anchor: digest/index.html
---

## What

Raised by the editor 2026-10-15. `digest/index.html` still carried the pre-4C Backstory detail modal:
`openBsrDetail()`, `closeBsrDetail()`, `bsrDetailHtml()` and its four section renderers (indicator, objects,
episodes, Begins), `dirGlyph()`, the `#bsrDetailModal` markup and about 80 lines of `.bsr-detail-*`,
`.bsr-ind*`, `.bsr-obj*`, `.bsr-ep*` CSS. Measured that day: nothing opened it but the popstate handler, on a
history entry `{kind: 'bsr'}` that only `openBsrDetail()` itself created; cards open the Backstory page
(`showBsrPage` / `bpRowHtml`). It showed an unconditional elapsed-time hero, the same "0 days" problem as
T-0092.

Removed, about 12,300 characters. Checked in a local preview: 7 cards; a card opens its Backstory page; back
and forward close and reopen it; a story opens and closes; a history entry left over from the old modal
lands on the Backstory tab with no error. T-0049's check, which read `openBsrDetail()`, now reads
`bpRowHtml()`, the detail view readers get, with the same assertion.

## Why

Dead code that still renders is a trap: it looked live enough that the editor took it for what produced
"Running for 0 days". Every future change to Backstory would have had to reason about two detail views.

## Check

```sh
! grep -q -E "openBsrDetail|bsrDetailModal|bsrDetailHtml" digest/index.html
```
