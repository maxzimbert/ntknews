#!/usr/bin/env python3
"""
T-0046 — Generate a static, shareable permalink page per Backstory row.

Mirrors ntk-pulse/build_digest.py's per-story permalink pages
(digest/YYYY-MM-DD/<slug>/index.html): real OG/Twitter tags, one static
file per row, no client-side fetch needed for a reader who lands here
from a shared link or a search result.

Reads  digest/data/backstory.json   the 21-row library + todays_pairings
       (todays_pairings entries carry story_permalink once
       ntk-pulse/build_digest.py has run and enriched them — run this
       script AFTER that one, per pulse-publish.yml)
Writes backstory/<row-id>/index.html   one static page per row

Deliberately does NOT render:
  - the long-form narrative essay (narrative[] is empty for every row
    today; out of scope here regardless — see docs/tickets/T-0046)
  - a quote per object (objects only carry {title, author, year, source}
    today; renders the plain citation. Picks up a real `quote` field
    automatically once T-0045 lands — no change needed here for that.)
  - accumulated past episodes (instances[] is empty for every row in
    prod; "In the digest" below shows only today's real pairings)

Why /backstory/<row-id>/ needs no netlify.toml rule: Netlify serves any
folder with an index.html by convention (same reason /digest/YYYY-MM-DD/
needs none), and netlify.toml's existing `/backstory` redirect is an
exact match, not a wildcard — it never intercepts /backstory/<row-id>.
The file just needs to land at backstory/<row-id>/index.html, a sibling
of digest/, not nested under it.

Stdlib only.
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKSTORY_JSON = ROOT / "digest" / "data" / "backstory.json"
OUT_DIR = ROOT / "backstory"
BASE_URL = "https://ntknews.org"

INK = "#261F23"
CREAM = "#EAD9C5"
BLUE_DEEP = "#045E96"
TERRA = "#DC6550"
AMBER_DEEP = "#7A5308"
AMBER = "#F2AE2E"

# Same asset as ntk-pulse/build_digest.py's LOGO_DATA_URI (and the live
# app's own dark header, digest/index.html:2100) — already coloured
# correctly for a dark header, confirmed identical byte-for-byte before
# copying (T-0053). No cross-import across ntk-pulse//editorial on
# purpose, matching how this script already duplicates its handful of
# other constants rather than reaching into build_digest.py.
LOGO_DATA_URI = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB3aWR0aD0iMjY5IiB6b29tQW5kUGFuPSJtYWduaWZ5IiB2aWV3Qm94PSIwIDAgMjAxLjc1IDEwMC40OTk5OTciIGhlaWdodD0iMTM0IiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCBtZWV0IiB2ZXJzaW9uPSIxLjAiPjxkZWZzPjxnLz48Y2xpcFBhdGggaWQ9ImVlZmZkM2ZlNGQiPjxwYXRoIGQ9Ik0gNDIuNjEzMjgxIDAgTCAxNTguMjU3ODEyIDAgTCAxNTguMjU3ODEyIDEzLjc2MTcxOSBMIDQyLjYxMzI4MSAxMy43NjE3MTkgWiBNIDQyLjYxMzI4MSAwICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9IjY0YjZjNWI4MjEiPjxwYXRoIGQ9Ik0gNDUuNjAxNTYyIDAgTCAxNTUuMjQyMTg4IDAgQyAxNTYuODkwNjI1IDAgMTU4LjIyNjU2MiAxLjMzNTkzOCAxNTguMjI2NTYyIDIuOTg0Mzc1IEwgMTU4LjIyNjU2MiAxMC43NzczNDQgQyAxNTguMjI2NTYyIDEyLjQyNTc4MSAxNTYuODkwNjI1IDEzLjc2MTcxOSAxNTUuMjQyMTg4IDEzLjc2MTcxOSBMIDQ1LjYwMTU2MiAxMy43NjE3MTkgQyA0My45NTMxMjUgMTMuNzYxNzE5IDQyLjYxMzI4MSAxMi40MjU3ODEgNDIuNjEzMjgxIDEwLjc3NzM0NCBMIDQyLjYxMzI4MSAyLjk4NDM3NSBDIDQyLjYxMzI4MSAxLjMzNTkzOCA0My45NTMxMjUgMCA0NS42MDE1NjIgMCBaIE0gNDUuNjAxNTYyIDAgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iMTNjNzNjMDllMiI+PHBhdGggZD0iTSAwLjYxMzI4MSAwIEwgMTE2LjIzMDQ2OSAwIEwgMTE2LjIzMDQ2OSAxMy43NjE3MTkgTCAwLjYxMzI4MSAxMy43NjE3MTkgWiBNIDAuNjEzMjgxIDAgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iOTAxYzRhN2I1NyI+PHBhdGggZD0iTSAzLjYwMTU2MiAwIEwgMTEzLjI0MjE4OCAwIEMgMTE0Ljg5MDYyNSAwIDExNi4yMjY1NjIgMS4zMzU5MzggMTE2LjIyNjU2MiAyLjk4NDM3NSBMIDExNi4yMjY1NjIgMTAuNzc3MzQ0IEMgMTE2LjIyNjU2MiAxMi40MjU3ODEgMTE0Ljg5MDYyNSAxMy43NjE3MTkgMTEzLjI0MjE4OCAxMy43NjE3MTkgTCAzLjYwMTU2MiAxMy43NjE3MTkgQyAxLjk1MzEyNSAxMy43NjE3MTkgMC42MTMyODEgMTIuNDI1NzgxIDAuNjEzMjgxIDEwLjc3NzM0NCBMIDAuNjEzMjgxIDIuOTg0Mzc1IEMgMC42MTMyODEgMS4zMzU5MzggMS45NTMxMjUgMCAzLjYwMTU2MiAwIFogTSAzLjYwMTU2MiAwICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9IjAyM2Y2ODE5NTkiPjxyZWN0IHg9IjAiIHdpZHRoPSIxMTciIHk9IjAiIGhlaWdodD0iMTQiLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iY2FhN2JmNjI4OSI+PHBhdGggZD0iTSA0Mi42MTMyODEgMjEuNzg5MDYyIEwgMTU4LjIyNjU2MiAyMS43ODkwNjIgTCAxNTguMjI2NTYyIDI4LjA1ODU5NCBMIDQyLjYxMzI4MSAyOC4wNTg1OTQgWiBNIDQyLjYxMzI4MSAyMS43ODkwNjIgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iNmY5M2QzNmJlMiI+PHBhdGggZD0iTSA0NC4xMDkzNzUgMjEuNzg5MDYyIEwgMTU2LjczNDM3NSAyMS43ODkwNjIgQyAxNTcuNTU4NTk0IDIxLjc4OTA2MiAxNTguMjI2NTYyIDIyLjQ1NzAzMSAxNTguMjI2NTYyIDIzLjI4MTI1IEwgMTU4LjIyNjU2MiAyNi41NjY0MDYgQyAxNTguMjI2NTYyIDI3LjM5MDYyNSAxNTcuNTU4NTk0IDI4LjA1ODU5NCAxNTYuNzM0Mzc1IDI4LjA1ODU5NCBMIDQ0LjEwOTM3NSAyOC4wNTg1OTQgQyA0My4yODUxNTYgMjguMDU4NTk0IDQyLjYxMzI4MSAyNy4zOTA2MjUgNDIuNjEzMjgxIDI2LjU2NjQwNiBMIDQyLjYxMzI4MSAyMy4yODEyNSBDIDQyLjYxMzI4MSAyMi40NTcwMzEgNDMuMjg1MTU2IDIxLjc4OTA2MiA0NC4xMDkzNzUgMjEuNzg5MDYyIFogTSA0NC4xMDkzNzUgMjEuNzg5MDYyICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9ImUwN2ZmZDk1NzciPjxwYXRoIGQ9Ik0gMC42MTMyODEgMC43ODkwNjIgTCAxMTYuMjI2NTYyIDAuNzg5MDYyIEwgMTE2LjIyNjU2MiA3LjA1ODU5NCBMIDAuNjEzMjgxIDcuMDU4NTk0IFogTSAwLjYxMzI4MSAwLjc4OTA2MiAiIGNsaXAtcnVsZT0ibm9uemVybyIvPjwvY2xpcFBhdGg+PGNsaXBQYXRoIGlkPSI1MzczMjAzMTlhIj48cGF0aCBkPSJNIDIuMTA5Mzc1IDAuNzg5MDYyIEwgMTE0LjczNDM3NSAwLjc4OTA2MiBDIDExNS41NTg1OTQgMC43ODkwNjIgMTE2LjIyNjU2MiAxLjQ1NzAzMSAxMTYuMjI2NTYyIDIuMjgxMjUgTCAxMTYuMjI2NTYyIDUuNTY2NDA2IEMgMTE2LjIyNjU2MiA2LjM5MDYyNSAxMTUuNTU4NTk0IDcuMDU4NTk0IDExNC43MzQzNzUgNy4wNTg1OTQgTCAyLjEwOTM3NSA3LjA1ODU5NCBDIDEuMjg1MTU2IDcuMDU4NTk0IDAuNjEzMjgxIDYuMzkwNjI1IDAuNjEzMjgxIDUuNTY2NDA2IEwgMC42MTMyODEgMi4yODEyNSBDIDAuNjEzMjgxIDEuNDU3MDMxIDEuMjg1MTU2IDAuNzg5MDYyIDIuMTA5Mzc1IDAuNzg5MDYyIFogTSAyLjEwOTM3NSAwLjc4OTA2MiAiIGNsaXAtcnVsZT0ibm9uemVybyIvPjwvY2xpcFBhdGg+PGNsaXBQYXRoIGlkPSI0NzY1NGU3M2MyIj48cmVjdCB4PSIwIiB3aWR0aD0iMTE3IiB5PSIwIiBoZWlnaHQ9IjgiLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iMzcwYWU3ODRhMCI+PHBhdGggZD0iTSA0Mi42MTMyODEgNzIuNjA1NDY5IEwgMTU4LjIyNjU2MiA3Mi42MDU0NjkgTCAxNTguMjI2NTYyIDc4Ljg3NSBMIDQyLjYxMzI4MSA3OC44NzUgWiBNIDQyLjYxMzI4MSA3Mi42MDU0NjkgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iNTIzYWRiMGI1NiI+PHBhdGggZD0iTSA0NC4xMDkzNzUgNzIuNjA1NDY5IEwgMTU2LjczNDM3NSA3Mi42MDU0NjkgQyAxNTcuNTU4NTk0IDcyLjYwNTQ2OSAxNTguMjI2NTYyIDczLjI3MzQzOCAxNTguMjI2NTYyIDc0LjA5NzY1NiBMIDE1OC4yMjY1NjIgNzcuMzgyODEyIEMgMTU4LjIyNjU2MiA3OC4yMDcwMzEgMTU3LjU1ODU5NCA3OC44NzUgMTU2LjczNDM3NSA3OC44NzUgTCA0NC4xMDkzNzUgNzguODc1IEMgNDMuMjg1MTU2IDc4Ljg3NSA0Mi42MTMyODEgNzguMjA3MDMxIDQyLjYxMzI4MSA3Ny4zODI4MTIgTCA0Mi42MTMyODEgNzQuMDk3NjU2IEMgNDIuNjEzMjgxIDczLjI3MzQzOCA0My4yODUxNTYgNzIuNjA1NDY5IDQ0LjEwOTM3NSA3Mi42MDU0NjkgWiBNIDQ0LjEwOTM3NSA3Mi42MDU0NjkgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iN2FkNDU3ZGI1NCI+PHBhdGggZD0iTSAwLjYxMzI4MSAwLjYwNTQ2OSBMIDExNi4yMjY1NjIgMC42MDU0NjkgTCAxMTYuMjI2NTYyIDYuODc1IEwgMC42MTMyODEgNi44NzUgWiBNIDAuNjEzMjgxIDAuNjA1NDY5ICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9IjczNThiNWQ1YWUiPjxwYXRoIGQ9Ik0gMi4xMDkzNzUgMC42MDU0NjkgTCAxMTQuNzM0Mzc1IDAuNjA1NDY5IEMgMTE1LjU1ODU5NCAwLjYwNTQ2OSAxMTYuMjI2NTYyIDEuMjczNDM4IDExNi4yMjY1NjIgMi4wOTc2NTYgTCAxMTYuMjI2NTYyIDUuMzgyODEyIEMgMTE2LjIyNjU2MiA2LjIwNzAzMSAxMTUuNTU4NTk0IDYuODc1IDExNC43MzQzNzUgNi44NzUgTCAyLjEwOTM3NSA2Ljg3NSBDIDEuMjg1MTU2IDYuODc1IDAuNjEzMjgxIDYuMjA3MDMxIDAuNjEzMjgxIDUuMzgyODEyIEwgMC42MTMyODEgMi4wOTc2NTYgQyAwLjYxMzI4MSAxLjI3MzQzOCAxLjI4NTE1NiAwLjYwNTQ2OSAyLjEwOTM3NSAwLjYwNTQ2OSBaIE0gMi4xMDkzNzUgMC42MDU0NjkgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iODBhOGRhNDEwYSI+PHJlY3QgeD0iMCIgd2lkdGg9IjExNyIgeT0iMCIgaGVpZ2h0PSI3Ii8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9ImY5ZDA3ZDA0YzgiPjxwYXRoIGQ9Ik0gNDIuNjEzMjgxIDg2LjE2NDA2MiBMIDE1OC4yNTc4MTIgODYuMTY0MDYyIEwgMTU4LjI1NzgxMiA5OS45MjU3ODEgTCA0Mi42MTMyODEgOTkuOTI1NzgxIFogTSA0Mi42MTMyODEgODYuMTY0MDYyICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9IjdjMjM4NWY2ZWQiPjxwYXRoIGQ9Ik0gNDUuNjAxNTYyIDg2LjE2NDA2MiBMIDE1NS4yNDIxODggODYuMTY0MDYyIEMgMTU2Ljg5MDYyNSA4Ni4xNjQwNjIgMTU4LjIyNjU2MiA4Ny41IDE1OC4yMjY1NjIgODkuMTQ4NDM4IEwgMTU4LjIyNjU2MiA5Ni45NDE0MDYgQyAxNTguMjI2NTYyIDk4LjU4OTg0NCAxNTYuODkwNjI1IDk5LjkyNTc4MSAxNTUuMjQyMTg4IDk5LjkyNTc4MSBMIDQ1LjYwMTU2MiA5OS45MjU3ODEgQyA0My45NTMxMjUgOTkuOTI1NzgxIDQyLjYxMzI4MSA5OC41ODk4NDQgNDIuNjEzMjgxIDk2Ljk0MTQwNiBMIDQyLjYxMzI4MSA4OS4xNDg0MzggQyA0Mi42MTMyODEgODcuNSA0My45NTMxMjUgODYuMTY0MDYyIDQ1LjYwMTU2MiA4Ni4xNjQwNjIgWiBNIDQ1LjYwMTU2MiA4Ni4xNjQwNjIgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iYWZhM2JmOTIxYiI+PHBhdGggZD0iTSAwLjYxMzI4MSAwLjE2NDA2MiBMIDExNi4yMzA0NjkgMC4xNjQwNjIgTCAxMTYuMjMwNDY5IDEzLjkyNTc4MSBMIDAuNjEzMjgxIDEzLjkyNTc4MSBaIE0gMC42MTMyODEgMC4xNjQwNjIgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iNDYzMjQ4NTcyMCI+PHBhdGggZD0iTSAzLjYwMTU2MiAwLjE2NDA2MiBMIDExMy4yNDIxODggMC4xNjQwNjIgQyAxMTQuODkwNjI1IDAuMTY0MDYyIDExNi4yMjY1NjIgMS41IDExNi4yMjY1NjIgMy4xNDg0MzggTCAxMTYuMjI2NTYyIDEwLjk0MTQwNiBDIDExNi4yMjY1NjIgMTIuNTg5ODQ0IDExNC44OTA2MjUgMTMuOTI1NzgxIDExMy4yNDIxODggMTMuOTI1NzgxIEwgMy42MDE1NjIgMTMuOTI1NzgxIEMgMS45NTMxMjUgMTMuOTI1NzgxIDAuNjEzMjgxIDEyLjU4OTg0NCAwLjYxMzI4MSAxMC45NDE0MDYgTCAwLjYxMzI4MSAzLjE0ODQzOCBDIDAuNjEzMjgxIDEuNSAxLjk1MzEyNSAwLjE2NDA2MiAzLjYwMTU2MiAwLjE2NDA2MiBaIE0gMy42MDE1NjIgMC4xNjQwNjIgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iZjY1OWMyZTM5YyI+PHJlY3QgeD0iMCIgd2lkdGg9IjExNyIgeT0iMCIgaGVpZ2h0PSIxNCIvPjwvY2xpcFBhdGg+PGNsaXBQYXRoIGlkPSIxODY5ZWRhZjJjIj48cmVjdCB4PSIwIiB3aWR0aD0iMTI2IiB5PSIwIiBoZWlnaHQ9IjQ2Ii8+PC9jbGlwUGF0aD48L2RlZnM+PGcgY2xpcC1wYXRoPSJ1cmwoI2VlZmZkM2ZlNGQpIj48ZyBjbGlwLXBhdGg9InVybCgjNjRiNmM1YjgyMSkiPjxnIHRyYW5zZm9ybT0ibWF0cml4KDEsIDAsIDAsIDEsIDQyLCAwKSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzAyM2Y2ODE5NTkpIj48ZyBjbGlwLXBhdGg9InVybCgjMTNjNzNjMDllMikiPjxnIGNsaXAtcGF0aD0idXJsKCM5MDFjNGE3YjU3KSI+PHBhdGggZmlsbD0iI2YyZjJmMiIgZD0iTSAwLjYxMzI4MSAwIEwgMTE2LjIwMzEyNSAwIEwgMTE2LjIwMzEyNSAxMy43NjE3MTkgTCAwLjYxMzI4MSAxMy43NjE3MTkgWiBNIDAuNjEzMjgxIDAgIiBmaWxsLW9wYWNpdHk9IjEiIGZpbGwtcnVsZT0ibm9uemVybyIvPjwvZz48L2c+PC9nPjwvZz48L2c+PC9nPjxnIGNsaXAtcGF0aD0idXJsKCNjYWE3YmY2Mjg5KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzZmOTNkMzZiZTIpIj48ZyB0cmFuc2Zvcm09Im1hdHJpeCgxLCAwLCAwLCAxLCA0MiwgMjEpIj48ZyBjbGlwLXBhdGg9InVybCgjNDc2NTRlNzNjMikiPjxnIGNsaXAtcGF0aD0idXJsKCNlMDdmZmQ5NTc3KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzUzNzMyMDMxOWEpIj48cGF0aCBmaWxsPSIjZjJmMmYyIiBkPSJNIDAuNjEzMjgxIDAuNzg5MDYyIEwgMTE2LjIyNjU2MiAwLjc4OTA2MiBMIDExNi4yMjY1NjIgNy4wNTg1OTQgTCAwLjYxMzI4MSA3LjA1ODU5NCBaIE0gMC42MTMyODEgMC43ODkwNjIgIiBmaWxsLW9wYWNpdHk9IjEiIGZpbGwtcnVsZT0ibm9uemVybyIvPjwvZz48L2c+PC9nPjwvZz48L2c+PC9nPjxnIGNsaXAtcGF0aD0idXJsKCMzNzBhZTc4NGEwKSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzUyM2FkYjBiNTYpIj48ZyB0cmFuc2Zvcm09Im1hdHJpeCgxLCAwLCAwLCAxLCA0MiwgNzIpIj48ZyBjbGlwLXBhdGg9InVybCgjODBhOGRhNDEwYSkiPjxnIGNsaXAtcGF0aD0idXJsKCM3YWQ0NTdkYjU0KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzczNThiNWQ1YWUpIj48cGF0aCBmaWxsPSIjZjJmMmYyIiBkPSJNIDAuNjEzMjgxIDAuNjA1NDY5IEwgMTE2LjIyNjU2MiAwLjYwNTQ2OSBMIDExNi4yMjY1NjIgNi44NzUgTCAwLjYxMzI4MSA2Ljg3NSBaIE0gMC42MTMyODEgMC42MDU0NjkgIiBmaWxsLW9wYWNpdHk9IjEiIGZpbGwtcnVsZT0ibm9uemVybyIvPjwvZz48L2c+PC9nPjwvZz48L2c+PC9nPjxnIGNsaXAtcGF0aD0idXJsKCNmOWQwN2QwNGM4KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzdjMjM4NWY2ZWQpIj48ZyB0cmFuc2Zvcm09Im1hdHJpeCgxLCAwLCAwLCAxLCA0MiwgODYpIj48ZyBjbGlwLXBhdGg9InVybCgjZjY1OWMyZTM5YykiPjxnIGNsaXAtcGF0aD0idXJsKCNhZmEzYmY5MjFiKSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzQ2MzI0ODU3MjApIj48cGF0aCBmaWxsPSIjZjJmMmYyIiBkPSJNIDAuNjEzMjgxIDAuMTY0MDYyIEwgMTE2LjIwMzEyNSAwLjE2NDA2MiBMIDExNi4yMDMxMjUgMTMuOTI1NzgxIEwgMC42MTMyODEgMTMuOTI1NzgxIFogTSAwLjYxMzI4MSAwLjE2NDA2MiAiIGZpbGwtb3BhY2l0eT0iMSIgZmlsbC1ydWxlPSJub256ZXJvIi8+PC9nPjwvZz48L2c+PC9nPjwvZz48L2c+PGcgdHJhbnNmb3JtPSJtYXRyaXgoMSwgMCwgMCwgMSwgNDIsIDI3KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzE4NjllZGFmMmMpIj48ZyBmaWxsPSIjZjJmMmYyIiBmaWxsLW9wYWNpdHk9IjEiPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEuMjAzMTk4LCAzNy40Nzc5NTMpIj48Zz48cGF0aCBkPSJNIDI0LjI2NTYyNSAtMTIgTCAyNC4yNjU2MjUgLTI3LjczNDM3NSBMIDMxLjY3MTg3NSAtMjcuNzM0Mzc1IEwgMzEuNjcxODc1IDAgTCAyNS4wMzEyNSAwIEwgOS44NDM3NSAtMTcuMjUgTCA5Ljg0Mzc1IDAgTCAyLjQzNzUgMCBMIDIuNDM3NSAtMjcuNzM0Mzc1IEwgMTAuNzE4NzUgLTI3LjczNDM3NSBaIE0gMjQuMjY1NjI1IC0xMiAiLz48L2c+PC9nPjwvZz48ZyBmaWxsPSIjZjJmMmYyIiBmaWxsLW9wYWNpdHk9IjEiPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDQ0LjI0NDI2NiwgMzcuNDc3OTUzKSI+PGc+PHBhdGggZD0iTSAxMS4xMjUgLTIwLjgxMjUgTCAwLjY0MDYyNSAtMjAuODEyNSBMIDAuNjQwNjI1IC0yNy43MzQzNzUgTCAyOS40Njg3NSAtMjcuNzM0Mzc1IEwgMjkuNDY4NzUgLTIwLjgxMjUgTCAxOS4wMzEyNSAtMjAuODEyNSBMIDE5LjAzMTI1IDAgTCAxMS4xMjUgMCBaIE0gMTEuMTI1IC0yMC44MTI1ICIvPjwvZz48L2c+PC9nPjxnIGZpbGw9IiNmMmYyZjIiIGZpbGwtb3BhY2l0eT0iMSI+PGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoODMuMjU4NjEsIDM3LjQ3Nzk1MykiPjxnPjxwYXRoIGQ9Ik0gMzIuNTQ2ODc1IDAgTCAyMi45ODQzNzUgMCBMIDE1LjEyNSAtMTIuMTU2MjUgTCAxMC4yMTg3NSAtNi44NDM3NSBMIDEwLjIxODc1IDAgTCAyLjQzNzUgMCBMIDIuNDM3NSAtMjcuNzM0Mzc1IEwgMTAuMjE4NzUgLTI3LjczNDM3NSBMIDEwLjIxODc1IC0xNS43OTY4NzUgTCAyMS4yNjU2MjUgLTI3LjczNDM3NSBMIDMxLjg3NSAtMjcuNzM0Mzc1IEwgMjEuMzEyNSAtMTYuNjQwNjI1IFogTSAzMi41NDY4NzUgMCAiLz48L2c+PC9nPjwvZz48L2c+PC9nPjwvc3ZnPg=="


def log(msg):
    print(f"[backstory-pages] {msg}", flush=True)


def html_esc(s):
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def elapsed(start_iso, today):
    """(years, months) between an ISO date and today — matches the
    arithmetic already live on ntknews.org/backstory (verified against
    it directly: media's 1987-08-04 start_date produces the same
    "39 yrs, 1 mo" the live modal shows)."""
    y_s, m_s, d_s = (int(x) for x in start_iso.split("-"))
    y = today.year - y_s
    m = today.month - m_s
    if today.day < d_s:
        m -= 1
    if m < 0:
        y -= 1
        m += 12
    return y, m


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_esc} — Backstory — NTK News</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="NTK News">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{milestone_esc}">
<meta property="og:url" content="{canonical_url}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{title_esc}">
<meta name="twitter:description" content="{milestone_esc}">
<link href="https://fonts.googleapis.com/css2?family=Overpass:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500;1,6..72,600&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Newsreader',Georgia,serif; background:{cream}; color:{ink};
    max-width:640px; margin:0 auto; }}
  a {{ color:{blue_deep}; }}
  header {{ background:{ink}; padding:13px 20px; }}
  header a {{ display:block; }}
  header img {{ height:18px; width:auto; display:block; }}
  .bar {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px;
    padding:14px 20px; border-bottom:1px solid {ink}; font-family:'Overpass',sans-serif; }}
  .bar a {{ white-space:nowrap; font-size:16px; font-weight:600; color:{ink}; text-decoration:none; }}
  .bar span {{ font-size:10px; font-weight:600; letter-spacing:.06em; color:rgba(38,31,35,.6); }}
  .hd {{ padding:28px 20px 22px; border-bottom:1px solid {ink}; }}
  .hd h1 {{ font-family:'Newsreader',serif; font-weight:600; font-size:clamp(26px,7vw,34px);
    line-height:1.08; letter-spacing:-.01em; margin:0 0 14px; }}
  .hd .milestone {{ font-family:'Newsreader',serif; font-style:italic; font-size:20px;
    line-height:1.35; color:rgba(38,31,35,.85); }}
  section {{ padding:22px 20px; border-bottom:1px solid rgba(38,31,35,.22); }}
  .hd .by {{ font-family:'Overpass',sans-serif; font-size:13px; color:rgba(38,31,35,.65); }}
  .hd.objhd h1 {{ font-size:26px; }}
  .stakes {{ font-size:16px; line-height:1.55; }}
  .obj a {{ display:block; text-decoration:none; color:inherit; }}
  .more {{ font-family:'Overpass',sans-serif; font-size:13px; font-weight:600; color:{blue_deep}; margin-top:6px; }}
  .ctx {{ font-size:16px; line-height:1.55; margin-bottom:14px; }}
  .pull {{ font-style:italic; font-size:20px; line-height:1.4; border-top:1px solid {ink}; border-bottom:1px solid {ink}; padding:16px 0; margin:6px 0 18px; }}
  .lab {{ font-family:'Overpass',sans-serif; font-size:13px; font-weight:600; margin-bottom:12px; }}
  .kicker {{ font-family:'Overpass',sans-serif; font-size:10px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase; color:{terra}; margin-bottom:10px; }}
  .ind-head {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; }}
  .dir {{ font-family:'Overpass',sans-serif; font-size:10px; font-weight:700; letter-spacing:.1em;
    text-transform:uppercase; color:{terra}; white-space:nowrap; }}
  .ind svg {{ display:block; width:100%; height:auto; margin:10px 0 4px; }}
  .src {{ font-family:'Overpass',sans-serif; font-size:10px; font-weight:600; letter-spacing:.06em;
    color:rgba(38,31,35,.6); }}
  .elapsed {{ text-align:center; padding:16px 0 6px; }}
  .elapsed .num {{ font-family:'Overpass',sans-serif; font-size:42px; font-weight:700; }}
  .elapsed .unit {{ font-size:18px; font-weight:600; }}
  .elapsed .since {{ font-family:'Overpass',sans-serif; font-size:10px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase; color:rgba(38,31,35,.6); margin-top:8px; }}
  .unverified {{ display:inline-block; border:1px solid {terra}; color:{terra};
    font-family:'Overpass',sans-serif; font-size:10px; font-weight:700; letter-spacing:.08em;
    text-transform:uppercase; padding:3px 6px; border-radius:3px; margin-top:12px; }}
  .spine {{ display:flex; gap:12px; align-items:flex-start; }}
  .spine .dot {{ width:8px; height:8px; border-radius:999px; background:{ink}; margin-top:7px; flex:none; }}
  .spine .t {{ font-size:16px; line-height:1.4; }}
  .obj {{ border-top:1px solid rgba(38,31,35,.2); padding:13px 0; }}
  .obj.first {{ border-top:none; padding-top:0; }}
  .obj .t {{ font-family:'Newsreader',serif; font-style:italic; font-size:16px; margin-bottom:4px; }}
  .obj .by {{ font-family:'Overpass',sans-serif; font-size:13px; color:rgba(38,31,35,.65); }}
  .digest {{ background:{ink}; color:{cream}; border-bottom:none; }}
  .digest .kicker {{ color:{amber}; }}
  .ep {{ display:block; border-top:1px solid rgba(234,217,197,.25); padding:13px 0; text-decoration:none; color:{cream}; }}
  .ep.first {{ border-top:none; padding-top:0; }}
  .ep .d {{ font-family:'Overpass',sans-serif; font-size:13px; color:rgba(234,217,197,.65); }}
  .ep .h {{ font-family:'Newsreader',serif; font-size:16px; margin-top:5px; }}
  .back {{ display:block; text-align:center; padding:26px 20px 40px; font-family:'Overpass',sans-serif;
    font-size:13px; font-weight:600; text-decoration:none; }}
  .end {{ font-family:'Newsreader',serif; font-style:italic; font-size:16px; text-align:center;
    color:rgba(38,31,35,.45); padding:26px 0 0; }}
</style>
</head>
<body>
<header><a href="/backstory"><img src="{logo}" alt="NTK"></a></header>
<div class="bar"><a href="/backstory">&larr; Backstory</a><span>ntknews.org/backstory/{row_id}</span></div>
<div class="hd">
  <h1>{title_esc}</h1>
  <div class="milestone">{milestone_esc}</div>
</div>
{body}
<a class="back" href="/backstory">← All of Backstory</a>
</body>
</html>
"""


def object_href(row, i):
    """4D route, per T-0048: /backstory/<row-id>/objects/<n>/ (n is 1-based)."""
    return f"/backstory/{row['id']}/objects/{i + 1}/"


def _pct(v):
    """'72%' -> 72.0; None if the value is not a plain number."""
    try:
        return float(str(v).strip().rstrip("%").replace(",", ""))
    except ValueError:
        return None


def indicator_svg(ind):
    """Two-point line, then -> now, as the 4C design draws it. Falls back to
    text when a value is not a percentage (a count, a dollar figure): a
    chart with an invented scale would mislead."""
    a, b = _pct(ind["then_value"]), _pct(ind["now_value"])
    if a is None or b is None or "%" not in str(ind["then_value"]) or "%" not in str(ind["now_value"]):
        return (f'<div style="font-family:Overpass,sans-serif;font-size:15px;margin:8px 0">'
                f'{html_esc(ind["then_value"])} ({html_esc(ind["then_year"])}) &rarr; '
                f'<b>{html_esc(ind["now_value"])}</b> (now)</div>')
    W, H, L, R, T, B = 340, 150, 8, 332, 18, 118
    y = lambda v: B - (B - T) * max(0.0, min(100.0, v)) / 100.0
    end_col = TERRA if ind.get("direction") == "worse" else INK
    return f"""<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html_esc(ind['label'])}: {html_esc(ind['then_value'])} in {html_esc(ind['then_year'])}, {html_esc(ind['now_value'])} now">
  <line x1="{L}" y1="{y(50):.0f}" x2="{R}" y2="{y(50):.0f}" stroke="rgba(38,31,35,.2)"/>
  <line x1="{L}" y1="{B}" x2="{R}" y2="{B}" stroke="{INK}"/>
  <line x1="{L}" y1="{y(a):.1f}" x2="{R}" y2="{y(b):.1f}" stroke="{INK}" stroke-width="2"/>
  <circle cx="{L}" cy="{y(a):.1f}" r="4" fill="{INK}"/>
  <circle cx="{R}" cy="{y(b):.1f}" r="5" fill="{end_col}"/>
  <text x="{L+10}" y="{y(a)-8:.0f}" font-family="Overpass,sans-serif" font-size="16" font-weight="700" fill="{INK}">{html_esc(ind['then_value'])}</text>
  <text x="{R}" y="{y(b)+22:.0f}" text-anchor="end" font-family="Overpass,sans-serif" font-size="16" font-weight="700" fill="{end_col}">{html_esc(ind['now_value'])}</text>
  <text x="{L}" y="{B+18}" font-family="Overpass,sans-serif" font-size="10" fill="rgba(38,31,35,.65)">{html_esc(ind['then_year'])}</text>
  <text x="{R}" y="{B+18}" text-anchor="end" font-family="Overpass,sans-serif" font-size="10" fill="rgba(38,31,35,.65)">now</text>
</svg>"""


def render_held(row):
    parts = []

    if row.get("stakes"):
        parts.append(f'<section><p class="stakes">{html_esc(row["stakes"])}</p></section>')

    ind = row.get("indicator")
    if ind:
        verified_badge = "" if ind.get("verified") else '<div class="unverified">Unverified</div>'
        parts.append(f"""<section class="ind">
  <div class="ind-head"><div class="lab">{html_esc(ind['label'])}</div><div class="dir">{html_esc(ind['direction'])}</div></div>
  {indicator_svg(ind)}
  <div class="src">{html_esc(ind['source'])} &middot; {html_esc(ind.get('as_of') or 'most recent data')}</div>
  {verified_badge}
</section>""")

    if row.get("start_line"):
        # First-letter capitalize only — str.capitalize() also lowercases
        # every other letter in the string, which mangles a proper noun
        # like "Washington" the moment it's not the first word.
        line = row["start_line"]
        line = line[:1].upper() + line[1:]
        parts.append(f"""<section>
  <div class="lab">Beginnings</div>
  <div class="spine"><span class="dot"></span><div class="t">{html_esc(line)}.</div></div>
</section>""")

    objs = row.get("objects") or []
    if objs:
        rows = []
        for i, o in enumerate(objs):
            cls = "obj first" if i == 0 else "obj"
            # Author is blank on some real objects (e.g. Abrams v U.S. has
            # no author field) — fall back to the row title rather than
            # render a dangling " · 1919" with nothing before it.
            by = o.get("author") or row["title"]
            head = o["quote"] if o.get("quote") else o["title"]
            rows.append(f'<div class="{cls}"><a href="{object_href(row, i)}">'
                        f'<div class="t">{html_esc(head)}</div>'
                        f'<div class="by">{html_esc(by)} · {html_esc(o["year"])}</div>'
                        f'<div class="more">About this</div></a></div>')
        parts.append(f'<section><div class="lab">The case</div>{"".join(rows)}</section>')

    return "\n".join(parts)


def render_fire(row, today):
    y, m = elapsed(row["start_date"], today)
    return f"""<section class="elapsed">
  <div><span class="num">{y}</span> <span class="unit">yrs</span> <span class="num">{m}</span> <span class="unit">mo</span></div>
  <div class="since">since {row['start_date']}</div>
</section>"""


def render_episodes(row_id, pairings):
    today_pairs = [p for p in pairings if p.get("row") == row_id]
    if not today_pairs:
        return ""
    items = []
    for i, p in enumerate(today_pairs):
        link = p.get("story_permalink")
        href = link if link else "/today"
        items.append(f'<a class="ep{" first" if i == 0 else ""}" href="{html_esc(href)}"><div class="d">Today</div>'
                      f'<div class="h">&ldquo;{html_esc(p.get("line") or p.get("headline",""))}&rdquo;</div></a>')
    return f'<section class="digest"><div class="kicker">In the digest</div>{"".join(items)}</section>'


def build_object_page(row, i):
    """4D. Renders only the fields that exist: today an object carries
    {title, author, year, source}; context, quote, where_now and source_url
    appear automatically once T-0045 / T-0048 add them."""
    o = row["objects"][i]
    by = o.get("author") or row["title"]
    parts = [f'<div class="kicker">{html_esc(o["year"])}</div>',
             f'<h1>{html_esc(o["title"])}</h1>',
             f'<div class="by" style="margin-top:8px">{html_esc(by)}</div>']
    head = f'<div class="hd objhd">{"".join(parts)}</div>'
    body = []
    ctx = o.get("context") or []
    if ctx:
        body.append("".join(f'<p class="ctx">{html_esc(c)}</p>' for c in ctx))
    if o.get("quote"):
        body.append(f'<p class="pull">{html_esc(o["quote"])}</p>')
    if o.get("where_now"):
        body.append(f'<div class="lab">Where it stands now</div><p class="ctx">{html_esc(o["where_now"])}</p>')
    body.append(f'<div class="src">Source &middot; {html_esc(o["source"])}</div>')
    if o.get("source_url"):
        body.append(f'<p style="margin-top:14px"><a href="{html_esc(o["source_url"])}">Read the original</a></p>')
    sect = f'<section>{"".join(body)}</section>'
    panel = (f'<section class="digest"><a class="ep first" href="/backstory/{row["id"]}/">'
             f'<div class="kicker">In the case for {html_esc(row["title"])}</div>'
             f'<div class="h">{html_esc(row["milestone"])}</div></a></section>')
    page = PAGE_TEMPLATE.format(
        row_id=f'{html_esc(row["id"])}/objects/{i + 1}',
        title_esc=html_esc(o["title"]),
        milestone_esc=html_esc(row["title"]),
        canonical_url=f"{BASE_URL}/backstory/{row['id']}/objects/{i + 1}/",
        cream=CREAM, ink=INK, blue_deep=BLUE_DEEP, terra=TERRA, amber_deep=AMBER_DEEP, amber=AMBER, logo=LOGO_DATA_URI,
        body=sect + panel + '<div class="end">— 30 —</div>',
    )
    # The shared template's header block is the row's (title + milestone);
    # swap it for the object's own, and point the top bar back at the row.
    start = page.index('<div class="hd">')
    end = page.index("</div>\n</div>", start) + len("</div>\n</div>")
    page = page[:start] + head + page[end:]
    page = page.replace('<a href="/backstory">&larr; Backstory</a>',
                        f'<a href="/backstory/{row["id"]}/">&larr; {html_esc(row["title"])}</a>', 1)
    return page


def build_page(row, pairings, today):
    body_sections = (render_fire(row, today) if row["stratum"] == "fire" else render_held(row))
    episodes = render_episodes(row["id"], pairings)
    body = body_sections + episodes + '<div class="end">— 30 —</div>'
    return PAGE_TEMPLATE.format(
        row_id=html_esc(row["id"]),
        title_esc=html_esc(row["title"]),
        milestone_esc=html_esc(row["milestone"]),
        canonical_url=f"{BASE_URL}/backstory/{row['id']}/",
        cream=CREAM, ink=INK, blue_deep=BLUE_DEEP, terra=TERRA, amber_deep=AMBER_DEEP, amber=AMBER, logo=LOGO_DATA_URI,
        body=body,
    )


def main():
    if not BACKSTORY_JSON.exists():
        sys.exit(f"{BACKSTORY_JSON} not found — run editorial/build_backstory.py first")
    data = json.loads(BACKSTORY_JSON.read_text())
    rows = data.get("rows", [])
    pairings = data.get("todays_pairings", [])
    today = date.today()

    OUT_DIR.mkdir(exist_ok=True)
    written = 0
    for row in rows:
        page = build_page(row, pairings, today)
        row_dir = OUT_DIR / row["id"]
        row_dir.mkdir(parents=True, exist_ok=True)
        (row_dir / "index.html").write_text(page)
        written += 1
        for i in range(len(row.get("objects") or [])):
            od = row_dir / "objects" / str(i + 1)
            od.mkdir(parents=True, exist_ok=True)
            (od / "index.html").write_text(build_object_page(row, i))
            written += 1

    log(f"{written} permalink pages written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
