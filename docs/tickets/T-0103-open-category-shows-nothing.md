---
id: T-0103
title: Opening a category from a Lineup story selects it off-screen, so the button looks dead
status: BUILT
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html
---

## What

Reported by the editor 2026-10-26: on Pulse's Backstory tab, **open Gun Ownership →** under a Lineup
story "does nothing". It did work. It set the selected category and redrew the tab, but the category
editor is laid out below the whole Lineup list and the page did not move, so nothing visible changed.
The same thing happens with **new category from these** (T-0098): it creates and selects the category
off-screen, which is why the editor earlier said that opening a new category "didn't do much". Both
paths now scroll the editor into view after the redraw.

## Why

A control that works where the editor cannot see it gets read as broken, and it hides the next step.
After making a category from kept objects, the next step is to compose it and approve it, and until
the category is approved the publish does not carry it. Moving the editor above the Lineup list was
ruled out, because the Lineup is what the tab is for and most visits never open a category.

## Check

```sh
python3 - <<'PY'
import re, sys
s = open('ntk-pulse/pulse.html', encoding='utf-8').read()
show = re.search(r'function catShowEditor\(\)\{[\s\S]*?\n\}', s)
if not show or 'cat-editor' not in show.group(0) or 'scrollIntoView' not in show.group(0):
    sys.exit('nothing brings the category editor into view')
op = re.search(r"querySelector\('\.bsr-lu-open'\).*", s)
if not op or 'catShowEditor()' not in op.group(0):
    sys.exit('"open <category>" selects the category without showing it')
mk = re.search(r'function bsrCreateCategory\([\s\S]*?\n\}', s)
if not mk or 'catShowEditor()' not in mk.group(0):
    sys.exit('"new category from these" creates the category without showing it')
PY
# manual: on Pages, "open <category>" under a Lineup story scrolls to that category's editor
```
