---
id: T-0075
title: At the bottom of the page, the story's Backstory pairing and category cannot be brought fully into view
status: BUILT
tags: [digest, defect]
anchor: digest/index.html
---

## What

Reported by the editor 2026-10-05, with a screen recording: at the bottom of the page the Backstory
link and the category are hidden behind the bottom nav. Reproduced the same day, independently of the
recording (macOS would not let the session open files in Downloads), on `ntknews.org/backstory` at
375x812, scrolled to the true end of the page:

- The last row's footer, which holds the row's category ("The Bomb") and its "Backstory" link, starts
  at 754px; the bottom nav starts at 748px, so the footer is entirely behind it. 40px of the row is
  hidden and the page cannot scroll any further.
- Cause: `.bsr-list` pads 24px under the list and the nav (`.bottom-nav`) is `position: fixed;
  height: 64px`. The other tabs reserve 80px (`#digestView`, `.today-view`, `.profile-view`), which
  is why only the Backstory tab is affected.

Fixed in `digest/index.html`: `.bsr-list { padding: 0 0 88px }`, the nav's 64px plus 24px of air.
Row and object overlays are `position: fixed` above the nav (`z-index: 160`) and are not affected.

## Why

The Backstory list is where the paired story's row, category and link live, so the last row being
unreachable is the one place the feature is cut off at the end of every day. Ruled out as the cause:
the safe-area inset (the nav is `box-sizing: border-box`, so its 64px already includes it).

## Check

```sh
python3 - <<'PY'
import re, sys
s = open("digest/index.html", encoding="utf-8").read()
nav = re.search(r"\.bottom-nav\s*\{[^}]*?height:\s*(\d+)px", s, re.S)
lst = re.search(r"\.bsr-list\s*\{\s*padding:\s*0\s+0\s+(\d+)px", s)
if not nav or not lst:
    sys.exit("STALE: could not read the nav height or the Backstory list padding")
if int(lst.group(1)) < int(nav.group(1)):
    sys.exit(f"OPEN: the Backstory list leaves {lst.group(1)}px under the last row but the fixed nav is {nav.group(1)}px tall")
PY
```

After the fix the editor should scroll the Backstory tab to the end on a phone and confirm the last
row's category and "Backstory" link are fully visible above the nav.

## Measured after, 2026-10-05

Same page, same 375x812 viewport, scrolled to the true end. Before: the last row's footer (category and
Backstory link) at 754 to 771px under a nav starting at 748px, entirely hidden. With 88px of padding:
footer at 690 to 707px, 41px clear of the nav. Checked by applying the one CSS rule to the live page, so
the staging build is the first time the file itself carries it.
