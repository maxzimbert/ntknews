---
id: T-0024
title: The orientation toast is only visible if the reader happens to end on the Digest tab
status: DECIDED
tags: [digest, defect]
anchor: digest/index.html:2065
---

## What

`#beatToast` sat inside `#digestView`. `closeStory()` returns the reader to
whichever tab they came from, so the toast only rendered for a reader who both
entered and left from Digest. The Today tab also lists stories and opens them
through `openStoryFromToday()`, and that path returned to Today, where the
element does not exist. Today is also the default landing tab.

Reading happens on Digest; Today is the overview and a different surface. An
earlier draft of this ticket called the Today route "the app's most common
path", which was an assumption and is not something this ticket measured.

Reproduced 2026-09-18 against the live build. Seeded a reader one story below
On the Beat, opened story 0 from Today, closed it:

```
toastFired: true
text: "5 stories on World, and you keep going deeper. You are on the beat."
VISIBLE_TO_READER: false
landedOnTab: today
```

The ladder fired correctly and wrote the session marker. Nothing appeared.

## Why

The editor's report was "I have never seen a toast in prod and it's not clear
how to engage with the digest to achieve one."

**This is a real bug and it is not established that it is the whole answer.**
What is measured: the toast fires, writes its session marker, and renders into
a container that is not on screen unless the reader ends on Digest. What is not
measured: which route the editor actually took, or what their production
`ntk_beats_v1` held. Before 2026-09-18 the toast was also gated at rung 4, which
needed five stories in a single category across two sittings, and localStorage
does not survive a different browser or device. Any of those would produce the
same report. Fixing this removes one certain cause; it does not prove there
were no others, and the next edition is what will tell.

The diagnosis matters more than the fix. This is the third time in this
project that a feature was judged absent when it was present and silent
(T-0015 for the ladder itself, T-0022 for a story that published with no
objection). A surface that fires into a hidden container leaves exactly the
same evidence as a surface that never fires, and the two have completely
different causes. **Check whether it ran before concluding it did not.**

The fix is to lift the element out of the view stack so it is tab-independent,
not to special-case the Today path. A reader can reach a story from the digest
list, the Today list, a Moment of Then circle or a permalink, and every one of
those should be able to show it.

Marking the session with `beatsMarkToast()` while the toast is invisible is
the sharper half of the bug: the reader is charged for a moment they never
got, and the once-per-sitting rule then suppresses the next one.

## Check

```sh
python3 - <<'PY'
import re, sys
s = open('digest/index.html', encoding='utf-8').read()

# Script blocks hold template literals full of <div>, which would wreck the
# nesting walk below. The view stack is plain body markup, so blank the scripts
# out first, keeping offsets honest by replacing them with spaces.
flat = re.sub(r'(?is)<script[^>]*>.*?</script>', lambda m: ' ' * len(m.group(0)), s)

toast = flat.find('id="beatToast"')
if toast < 0: sys.exit('#beatToast not found outside the script blocks')

TAG = re.compile(r'<(/?)div\b', re.I)
for view in ('todayView', 'digestView', 'storyView', 'backstoryView', 'profileView'):
    i = flat.find('id="%s"' % view)
    if i < 0: sys.exit('#%s not found' % view)
    depth, close = 0, None
    for m in TAG.finditer(flat, flat.rfind('<', 0, i)):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            close = m.end()
            break
    if close is None: sys.exit('could not find the close of #%s' % view)
    if i < toast < close:
        sys.exit('#beatToast is inside #%s, so it is invisible from every other tab' % view)
PY
```
