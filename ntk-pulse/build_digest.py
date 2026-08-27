#!/usr/bin/env python3
"""NTK Digest — full automated build.

Runs unattended, triggered by a push from Pulse's Publish button. Takes
whatever's currently in the lineup and turns it into the live site: no
paste, no download, no terminal.

What it does, in order:
  1. Reads the published story data (committed by Pulse's Publish button).
  2. Picks today's "fun fact" — grounded in Wikipedia's real On This Day
     feed, never invented (see pick_fun_fact()).
  3. Regenerates digest/v2/index.html's `const stories` and `const funFact`
     blocks in place — the live homepage, not a copy. Everything else in
     that file (the swipe-app shell, styling, JS) is left untouched; this
     only touches the two blocks that used to be hand-pasted.
  4. Decodes each story's base64 image into a real file.
  5. Writes a standalone permalink page per story, real OG/Twitter tags.
  6. Freezes today's edition at a permanent dated path.
  7. Rebuilds the archive index from what's actually on disk.
  8. Writes a last-published timestamp Pulse can read and show you.

Writes DIRECTLY to digest/v2/ — no test-folder detour. That was the right
call while this was unverified; it's a deliberate, later decision to skip
it now that the mechanics are proven and there's no live audience yet.

Stdlib only.
"""
import base64
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TEAL = "#01B2A7"
INK = "#261F23"
CREAM = "#EAD9C5"
GOLD = "#F2AE2E"
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5"


def log(msg):
    print(f"[build] {msg}", flush=True)


# ─── fun fact: grounded in a real source, never invented ───
def fetch_on_this_day():
    """Wikipedia's own editorial pick of the day's most notable historical
    events — same en.wikipedia.org/api/rest_v1 domain Summon Context
    already calls, no new infrastructure, no API key."""
    now = datetime.now(timezone.utc)
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/selected/{now.month:02d}/{now.day:02d}"
    req = urllib.request.Request(url, headers={"User-Agent": "NTK-News-Build/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    events = data.get("selected", [])
    return [{"year": e.get("year"), "text": e.get("text", "")} for e in events if e.get("text")]


def call_claude(api_key, prompt, max_tokens=300):
    body = {"model": MODEL, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read())
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def pick_fun_fact(api_key):
    """One real event, selected and written up — never generated from
    nothing. If Wikipedia or the API call fails, falls back to the
    existing funFact already in the file rather than writing something
    unsourced."""
    try:
        events = fetch_on_this_day()
        if not events:
            return None
        listing = "\n".join(f"- {e['year']}: {e['text']}" for e in events[:20])
        prompt = (
            "Pick ONE event from this real, verified list of things that happened on this "
            "date in history. Choose whichever is most surprising, delightful, or humanizing "
            "— not necessarily the most famous. Write it up in 35-50 words, plain and warm, "
            "in the spirit of a closing 'moment of zen' — something a reader closes the day "
            "on, not more news to process.\n\n"
            "Judge only what's on this list. Do not add detail beyond what's stated. If "
            "nothing here is genuinely delightful, pick the most human one anyway.\n\n"
            f"{listing}\n\n"
            "Return ONLY the 35-50 word write-up, no preamble, no quotation marks around it."
        )
        text = call_claude(api_key, prompt, max_tokens=200).strip()
        return text if text else None
    except Exception as e:
        log(f"  fun fact generation failed, keeping existing: {e}")
        return None


# ─── homepage regeneration: touch only the two blocks that were hand-pasted ───
def jsEsc(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def build_stories_block(stories):
    lines = ["const stories = ["]
    for s in stories:
        img_fields = ""
        if s.get("featuredImage"):
            img_fields = (f',\n    featuredImage: "{jsEsc(s["featuredImage"])}"'
                          f',\n    overlayColor: "{jsEsc(s.get("overlayColor", "#0798F2"))}"'
                          f',\n    overlayOpacity: {s.get("overlayOpacity", 45)}')
        permalink_field = ""
        if s.get("permalink"):
            permalink_field = f',\n    permalink: "{jsEsc(s["permalink"])}"'
        lines.append(f'  {{\n'
                      f'    key: "{jsEsc(s.get("key",""))}",\n'
                      f'    category: "{jsEsc(s.get("category",""))}",\n'
                      f'    headline: "{jsEsc(s.get("headline",""))}",\n'
                      f'    lede: "{jsEsc(s.get("lede",""))}",\n'
                      f'    truth: "{jsEsc(s.get("truth",""))}",\n'
                      f'    prob: "{jsEsc(s.get("prob",""))}",\n'
                      f'    poss: "{jsEsc(s.get("poss",""))}",\n'
                      f'    lies: "{jsEsc(s.get("lies",""))}"{img_fields}{permalink_field}\n'
                      f'  }},')
    lines.append("]; // ← END OF DAILY CONTENT. Do not edit below this line.")
    return "\n".join(lines)


def regenerate_today(html, today):
    """Same pattern as the funFact block: one hand-pasted `const` marker,
    regex-replaced in place. `today` is {"text": "...", "generatedAt": "..."}
    or None if nothing's been generated yet in Pulse — in which case this
    leaves whatever's already live untouched rather than blanking it out,
    same defensive posture as pick_fun_fact's fallback."""
    if not today or not today.get("text"):
        return html
    today_re = re.compile(r'const todayOverview = "[^"]*";')
    new_html, n = today_re.subn(f'const todayOverview = "{jsEsc(today["text"])}";', html)
    if n != 1:
        log(f"  WARNING: expected 1 todayOverview match, found {n} — leaving Today overview untouched")
        return html
    return new_html


def regenerate_homepage(html, stories, fun_fact):
    """Regex-replace the two hand-pasted blocks in place. Everything else
    in the file — the swipe-app shell, all its JS and CSS — is left
    completely untouched. This is deliberately NOT a from-scratch
    regeneration of the page; duplicating that logic here would be a
    second place for it to drift out of sync with the real, working app."""
    stories_re = re.compile(
        r"const stories = \[.*?\];\s*// ← END OF DAILY CONTENT\. Do not edit below this line\.",
        re.DOTALL)
    new_html, n = stories_re.subn(build_stories_block(stories), html)
    if n != 1:
        raise RuntimeError(f"expected exactly 1 stories block match, found {n} — "
                            "homepage template may have changed; refusing to guess")

    if fun_fact:
        fact_re = re.compile(r'const funFact = "[^"]*";')
        new_html, n2 = fact_re.subn(f'const funFact = "{jsEsc(fun_fact)}";', new_html)
        if n2 != 1:
            log(f"  WARNING: expected 1 funFact match, found {n2} — leaving funFact untouched")
            new_html = html if n != 1 else new_html  # safety, though n==1 already checked above

    return new_html


# ─── per-story permalinks (unchanged logic from the earlier build) ───
def slugify(text, max_len=60):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    text = re.sub(r"[\s-]+", "-", text)
    return text[:max_len].strip("-") or "story"


def unique_slugs(stories):
    seen, out = {}, []
    for s in stories:
        base = slugify(s.get("headline", "story"))
        slug, n = base, 2
        while slug in seen:
            slug = f"{base}-{n}"; n += 1
        seen[slug] = True
        out.append(slug)
    return out


def decode_image(data_uri, out_path):
    if not data_uri or not data_uri.startswith("data:image"):
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(data_uri.split(",", 1)[1]))
    return True


def html_esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def strip_html_for_description(html, max_len=200):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:max_len] + "…") if len(text) > max_len else text


LOGO_DATA_URI = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB3aWR0aD0iMjY5IiB6b29tQW5kUGFuPSJtYWduaWZ5IiB2aWV3Qm94PSIwIDAgMjAxLjc1IDEwMC40OTk5OTciIGhlaWdodD0iMTM0IiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCBtZWV0IiB2ZXJzaW9uPSIxLjAiPjxkZWZzPjxnLz48Y2xpcFBhdGggaWQ9ImVlZmZkM2ZlNGQiPjxwYXRoIGQ9Ik0gNDIuNjEzMjgxIDAgTCAxNTguMjU3ODEyIDAgTCAxNTguMjU3ODEyIDEzLjc2MTcxOSBMIDQyLjYxMzI4MSAxMy43NjE3MTkgWiBNIDQyLjYxMzI4MSAwICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9IjY0YjZjNWI4MjEiPjxwYXRoIGQ9Ik0gNDUuNjAxNTYyIDAgTCAxNTUuMjQyMTg4IDAgQyAxNTYuODkwNjI1IDAgMTU4LjIyNjU2MiAxLjMzNTkzOCAxNTguMjI2NTYyIDIuOTg0Mzc1IEwgMTU4LjIyNjU2MiAxMC43NzczNDQgQyAxNTguMjI2NTYyIDEyLjQyNTc4MSAxNTYuODkwNjI1IDEzLjc2MTcxOSAxNTUuMjQyMTg4IDEzLjc2MTcxOSBMIDQ1LjYwMTU2MiAxMy43NjE3MTkgQyA0My45NTMxMjUgMTMuNzYxNzE5IDQyLjYxMzI4MSAxMi40MjU3ODEgNDIuNjEzMjgxIDEwLjc3NzM0NCBMIDQyLjYxMzI4MSAyLjk4NDM3NSBDIDQyLjYxMzI4MSAxLjMzNTkzOCA0My45NTMxMjUgMCA0NS42MDE1NjIgMCBaIE0gNDUuNjAxNTYyIDAgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iMTNjNzNjMDllMiI+PHBhdGggZD0iTSAwLjYxMzI4MSAwIEwgMTE2LjIzMDQ2OSAwIEwgMTE2LjIzMDQ2OSAxMy43NjE3MTkgTCAwLjYxMzI4MSAxMy43NjE3MTkgWiBNIDAuNjEzMjgxIDAgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iOTAxYzRhN2I1NyI+PHBhdGggZD0iTSAzLjYwMTU2MiAwIEwgMTEzLjI0MjE4OCAwIEMgMTE0Ljg5MDYyNSAwIDExNi4yMjY1NjIgMS4zMzU5MzggMTE2LjIyNjU2MiAyLjk4NDM3NSBMIDExNi4yMjY1NjIgMTAuNzc3MzQ0IEMgMTE2LjIyNjU2MiAxMi40MjU3ODEgMTE0Ljg5MDYyNSAxMy43NjE3MTkgMTEzLjI0MjE4OCAxMy43NjE3MTkgTCAzLjYwMTU2MiAxMy43NjE3MTkgQyAxLjk1MzEyNSAxMy43NjE3MTkgMC42MTMyODEgMTIuNDI1NzgxIDAuNjEzMjgxIDEwLjc3NzM0NCBMIDAuNjEzMjgxIDIuOTg0Mzc1IEMgMC42MTMyODEgMS4zMzU5MzggMS45NTMxMjUgMCAzLjYwMTU2MiAwIFogTSAzLjYwMTU2MiAwICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9IjAyM2Y2ODE5NTkiPjxyZWN0IHg9IjAiIHdpZHRoPSIxMTciIHk9IjAiIGhlaWdodD0iMTQiLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iY2FhN2JmNjI4OSI+PHBhdGggZD0iTSA0Mi42MTMyODEgMjEuNzg5MDYyIEwgMTU4LjIyNjU2MiAyMS43ODkwNjIgTCAxNTguMjI2NTYyIDI4LjA1ODU5NCBMIDQyLjYxMzI4MSAyOC4wNTg1OTQgWiBNIDQyLjYxMzI4MSAyMS43ODkwNjIgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iNmY5M2QzNmJlMiI+PHBhdGggZD0iTSA0NC4xMDkzNzUgMjEuNzg5MDYyIEwgMTU2LjczNDM3NSAyMS43ODkwNjIgQyAxNTcuNTU4NTk0IDIxLjc4OTA2MiAxNTguMjI2NTYyIDIyLjQ1NzAzMSAxNTguMjI2NTYyIDIzLjI4MTI1IEwgMTU4LjIyNjU2MiAyNi41NjY0MDYgQyAxNTguMjI2NTYyIDI3LjM5MDYyNSAxNTcuNTU4NTk0IDI4LjA1ODU5NCAxNTYuNzM0Mzc1IDI4LjA1ODU5NCBMIDQ0LjEwOTM3NSAyOC4wNTg1OTQgQyA0My4yODUxNTYgMjguMDU4NTk0IDQyLjYxMzI4MSAyNy4zOTA2MjUgNDIuNjEzMjgxIDI2LjU2NjQwNiBMIDQyLjYxMzI4MSAyMy4yODEyNSBDIDQyLjYxMzI4MSAyMi40NTcwMzEgNDMuMjg1MTU2IDIxLjc4OTA2MiA0NC4xMDkzNzUgMjEuNzg5MDYyIFogTSA0NC4xMDkzNzUgMjEuNzg5MDYyICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9ImUwN2ZmZDk1NzciPjxwYXRoIGQ9Ik0gMC42MTMyODEgMC43ODkwNjIgTCAxMTYuMjI2NTYyIDAuNzg5MDYyIEwgMTE2LjIyNjU2MiA3LjA1ODU5NCBMIDAuNjEzMjgxIDcuMDU4NTk0IFogTSAwLjYxMzI4MSAwLjc4OTA2MiAiIGNsaXAtcnVsZT0ibm9uemVybyIvPjwvY2xpcFBhdGg+PGNsaXBQYXRoIGlkPSI1MzczMjAzMTlhIj48cGF0aCBkPSJNIDIuMTA5Mzc1IDAuNzg5MDYyIEwgMTE0LjczNDM3NSAwLjc4OTA2MiBDIDExNS41NTg1OTQgMC43ODkwNjIgMTE2LjIyNjU2MiAxLjQ1NzAzMSAxMTYuMjI2NTYyIDIuMjgxMjUgTCAxMTYuMjI2NTYyIDUuNTY2NDA2IEMgMTE2LjIyNjU2MiA2LjM5MDYyNSAxMTUuNTU4NTk0IDcuMDU4NTk0IDExNC43MzQzNzUgNy4wNTg1OTQgTCAyLjEwOTM3NSA3LjA1ODU5NCBDIDEuMjg1MTU2IDcuMDU4NTk0IDAuNjEzMjgxIDYuMzkwNjI1IDAuNjEzMjgxIDUuNTY2NDA2IEwgMC42MTMyODEgMi4yODEyNSBDIDAuNjEzMjgxIDEuNDU3MDMxIDEuMjg1MTU2IDAuNzg5MDYyIDIuMTA5Mzc1IDAuNzg5MDYyIFogTSAyLjEwOTM3NSAwLjc4OTA2MiAiIGNsaXAtcnVsZT0ibm9uemVybyIvPjwvY2xpcFBhdGg+PGNsaXBQYXRoIGlkPSI0NzY1NGU3M2MyIj48cmVjdCB4PSIwIiB3aWR0aD0iMTE3IiB5PSIwIiBoZWlnaHQ9IjgiLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iMzcwYWU3ODRhMCI+PHBhdGggZD0iTSA0Mi42MTMyODEgNzIuNjA1NDY5IEwgMTU4LjIyNjU2MiA3Mi42MDU0NjkgTCAxNTguMjI2NTYyIDc4Ljg3NSBMIDQyLjYxMzI4MSA3OC44NzUgWiBNIDQyLjYxMzI4MSA3Mi42MDU0NjkgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iNTIzYWRiMGI1NiI+PHBhdGggZD0iTSA0NC4xMDkzNzUgNzIuNjA1NDY5IEwgMTU2LjczNDM3NSA3Mi42MDU0NjkgQyAxNTcuNTU4NTk0IDcyLjYwNTQ2OSAxNTguMjI2NTYyIDczLjI3MzQzOCAxNTguMjI2NTYyIDc0LjA5NzY1NiBMIDE1OC4yMjY1NjIgNzcuMzgyODEyIEMgMTU4LjIyNjU2MiA3OC4yMDcwMzEgMTU3LjU1ODU5NCA3OC44NzUgMTU2LjczNDM3NSA3OC44NzUgTCA0NC4xMDkzNzUgNzguODc1IEMgNDMuMjg1MTU2IDc4Ljg3NSA0Mi42MTMyODEgNzguMjA3MDMxIDQyLjYxMzI4MSA3Ny4zODI4MTIgTCA0Mi42MTMyODEgNzQuMDk3NjU2IEMgNDIuNjEzMjgxIDczLjI3MzQzOCA0My4yODUxNTYgNzIuNjA1NDY5IDQ0LjEwOTM3NSA3Mi42MDU0NjkgWiBNIDQ0LjEwOTM3NSA3Mi42MDU0NjkgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iN2FkNDU3ZGI1NCI+PHBhdGggZD0iTSAwLjYxMzI4MSAwLjYwNTQ2OSBMIDExNi4yMjY1NjIgMC42MDU0NjkgTCAxMTYuMjI2NTYyIDYuODc1IEwgMC42MTMyODEgNi44NzUgWiBNIDAuNjEzMjgxIDAuNjA1NDY5ICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9IjczNThiNWQ1YWUiPjxwYXRoIGQ9Ik0gMi4xMDkzNzUgMC42MDU0NjkgTCAxMTQuNzM0Mzc1IDAuNjA1NDY5IEMgMTE1LjU1ODU5NCAwLjYwNTQ2OSAxMTYuMjI2NTYyIDEuMjczNDM4IDExNi4yMjY1NjIgMi4wOTc2NTYgTCAxMTYuMjI2NTYyIDUuMzgyODEyIEMgMTE2LjIyNjU2MiA2LjIwNzAzMSAxMTUuNTU4NTk0IDYuODc1IDExNC43MzQzNzUgNi44NzUgTCAyLjEwOTM3NSA2Ljg3NSBDIDEuMjg1MTU2IDYuODc1IDAuNjEzMjgxIDYuMjA3MDMxIDAuNjEzMjgxIDUuMzgyODEyIEwgMC42MTMyODEgMi4wOTc2NTYgQyAwLjYxMzI4MSAxLjI3MzQzOCAxLjI4NTE1NiAwLjYwNTQ2OSAyLjEwOTM3NSAwLjYwNTQ2OSBaIE0gMi4xMDkzNzUgMC42MDU0NjkgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iODBhOGRhNDEwYSI+PHJlY3QgeD0iMCIgd2lkdGg9IjExNyIgeT0iMCIgaGVpZ2h0PSI3Ii8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9ImY5ZDA3ZDA0YzgiPjxwYXRoIGQ9Ik0gNDIuNjEzMjgxIDg2LjE2NDA2MiBMIDE1OC4yNTc4MTIgODYuMTY0MDYyIEwgMTU4LjI1NzgxMiA5OS45MjU3ODEgTCA0Mi42MTMyODEgOTkuOTI1NzgxIFogTSA0Mi42MTMyODEgODYuMTY0MDYyICIgY2xpcC1ydWxlPSJub256ZXJvIi8+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9IjdjMjM4NWY2ZWQiPjxwYXRoIGQ9Ik0gNDUuNjAxNTYyIDg2LjE2NDA2MiBMIDE1NS4yNDIxODggODYuMTY0MDYyIEMgMTU2Ljg5MDYyNSA4Ni4xNjQwNjIgMTU4LjIyNjU2MiA4Ny41IDE1OC4yMjY1NjIgODkuMTQ4NDM4IEwgMTU4LjIyNjU2MiA5Ni45NDE0MDYgQyAxNTguMjI2NTYyIDk4LjU4OTg0NCAxNTYuODkwNjI1IDk5LjkyNTc4MSAxNTUuMjQyMTg4IDk5LjkyNTc4MSBMIDQ1LjYwMTU2MiA5OS45MjU3ODEgQyA0My45NTMxMjUgOTkuOTI1NzgxIDQyLjYxMzI4MSA5OC41ODk4NDQgNDIuNjEzMjgxIDk2Ljk0MTQwNiBMIDQyLjYxMzI4MSA4OS4xNDg0MzggQyA0Mi42MTMyODEgODcuNSA0My45NTMxMjUgODYuMTY0MDYyIDQ1LjYwMTU2MiA4Ni4xNjQwNjIgWiBNIDQ1LjYwMTU2MiA4Ni4xNjQwNjIgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iYWZhM2JmOTIxYiI+PHBhdGggZD0iTSAwLjYxMzI4MSAwLjE2NDA2MiBMIDExNi4yMzA0NjkgMC4xNjQwNjIgTCAxMTYuMjMwNDY5IDEzLjkyNTc4MSBMIDAuNjEzMjgxIDEzLjkyNTc4MSBaIE0gMC42MTMyODEgMC4xNjQwNjIgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iNDYzMjQ4NTcyMCI+PHBhdGggZD0iTSAzLjYwMTU2MiAwLjE2NDA2MiBMIDExMy4yNDIxODggMC4xNjQwNjIgQyAxMTQuODkwNjI1IDAuMTY0MDYyIDExNi4yMjY1NjIgMS41IDExNi4yMjY1NjIgMy4xNDg0MzggTCAxMTYuMjI2NTYyIDEwLjk0MTQwNiBDIDExNi4yMjY1NjIgMTIuNTg5ODQ0IDExNC44OTA2MjUgMTMuOTI1NzgxIDExMy4yNDIxODggMTMuOTI1NzgxIEwgMy42MDE1NjIgMTMuOTI1NzgxIEMgMS45NTMxMjUgMTMuOTI1NzgxIDAuNjEzMjgxIDEyLjU4OTg0NCAwLjYxMzI4MSAxMC45NDE0MDYgTCAwLjYxMzI4MSAzLjE0ODQzOCBDIDAuNjEzMjgxIDEuNSAxLjk1MzEyNSAwLjE2NDA2MiAzLjYwMTU2MiAwLjE2NDA2MiBaIE0gMy42MDE1NjIgMC4xNjQwNjIgIiBjbGlwLXJ1bGU9Im5vbnplcm8iLz48L2NsaXBQYXRoPjxjbGlwUGF0aCBpZD0iZjY1OWMyZTM5YyI+PHJlY3QgeD0iMCIgd2lkdGg9IjExNyIgeT0iMCIgaGVpZ2h0PSIxNCIvPjwvY2xpcFBhdGg+PGNsaXBQYXRoIGlkPSIxODY5ZWRhZjJjIj48cmVjdCB4PSIwIiB3aWR0aD0iMTI2IiB5PSIwIiBoZWlnaHQ9IjQ2Ii8+PC9jbGlwUGF0aD48L2RlZnM+PGcgY2xpcC1wYXRoPSJ1cmwoI2VlZmZkM2ZlNGQpIj48ZyBjbGlwLXBhdGg9InVybCgjNjRiNmM1YjgyMSkiPjxnIHRyYW5zZm9ybT0ibWF0cml4KDEsIDAsIDAsIDEsIDQyLCAwKSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzAyM2Y2ODE5NTkpIj48ZyBjbGlwLXBhdGg9InVybCgjMTNjNzNjMDllMikiPjxnIGNsaXAtcGF0aD0idXJsKCM5MDFjNGE3YjU3KSI+PHBhdGggZmlsbD0iI2YyZjJmMiIgZD0iTSAwLjYxMzI4MSAwIEwgMTE2LjIwMzEyNSAwIEwgMTE2LjIwMzEyNSAxMy43NjE3MTkgTCAwLjYxMzI4MSAxMy43NjE3MTkgWiBNIDAuNjEzMjgxIDAgIiBmaWxsLW9wYWNpdHk9IjEiIGZpbGwtcnVsZT0ibm9uemVybyIvPjwvZz48L2c+PC9nPjwvZz48L2c+PC9nPjxnIGNsaXAtcGF0aD0idXJsKCNjYWE3YmY2Mjg5KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzZmOTNkMzZiZTIpIj48ZyB0cmFuc2Zvcm09Im1hdHJpeCgxLCAwLCAwLCAxLCA0MiwgMjEpIj48ZyBjbGlwLXBhdGg9InVybCgjNDc2NTRlNzNjMikiPjxnIGNsaXAtcGF0aD0idXJsKCNlMDdmZmQ5NTc3KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzUzNzMyMDMxOWEpIj48cGF0aCBmaWxsPSIjZjJmMmYyIiBkPSJNIDAuNjEzMjgxIDAuNzg5MDYyIEwgMTE2LjIyNjU2MiAwLjc4OTA2MiBMIDExNi4yMjY1NjIgNy4wNTg1OTQgTCAwLjYxMzI4MSA3LjA1ODU5NCBaIE0gMC42MTMyODEgMC43ODkwNjIgIiBmaWxsLW9wYWNpdHk9IjEiIGZpbGwtcnVsZT0ibm9uemVybyIvPjwvZz48L2c+PC9nPjwvZz48L2c+PC9nPjxnIGNsaXAtcGF0aD0idXJsKCMzNzBhZTc4NGEwKSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzUyM2FkYjBiNTYpIj48ZyB0cmFuc2Zvcm09Im1hdHJpeCgxLCAwLCAwLCAxLCA0MiwgNzIpIj48ZyBjbGlwLXBhdGg9InVybCgjODBhOGRhNDEwYSkiPjxnIGNsaXAtcGF0aD0idXJsKCM3YWQ0NTdkYjU0KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzczNThiNWQ1YWUpIj48cGF0aCBmaWxsPSIjZjJmMmYyIiBkPSJNIDAuNjEzMjgxIDAuNjA1NDY5IEwgMTE2LjIyNjU2MiAwLjYwNTQ2OSBMIDExNi4yMjY1NjIgNi44NzUgTCAwLjYxMzI4MSA2Ljg3NSBaIE0gMC42MTMyODEgMC42MDU0NjkgIiBmaWxsLW9wYWNpdHk9IjEiIGZpbGwtcnVsZT0ibm9uemVybyIvPjwvZz48L2c+PC9nPjwvZz48L2c+PC9nPjxnIGNsaXAtcGF0aD0idXJsKCNmOWQwN2QwNGM4KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzdjMjM4NWY2ZWQpIj48ZyB0cmFuc2Zvcm09Im1hdHJpeCgxLCAwLCAwLCAxLCA0MiwgODYpIj48ZyBjbGlwLXBhdGg9InVybCgjZjY1OWMyZTM5YykiPjxnIGNsaXAtcGF0aD0idXJsKCNhZmEzYmY5MjFiKSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzQ2MzI0ODU3MjApIj48cGF0aCBmaWxsPSIjZjJmMmYyIiBkPSJNIDAuNjEzMjgxIDAuMTY0MDYyIEwgMTE2LjIwMzEyNSAwLjE2NDA2MiBMIDExNi4yMDMxMjUgMTMuOTI1NzgxIEwgMC42MTMyODEgMTMuOTI1NzgxIFogTSAwLjYxMzI4MSAwLjE2NDA2MiAiIGZpbGwtb3BhY2l0eT0iMSIgZmlsbC1ydWxlPSJub256ZXJvIi8+PC9nPjwvZz48L2c+PC9nPjwvZz48L2c+PGcgdHJhbnNmb3JtPSJtYXRyaXgoMSwgMCwgMCwgMSwgNDIsIDI3KSI+PGcgY2xpcC1wYXRoPSJ1cmwoIzE4NjllZGFmMmMpIj48ZyBmaWxsPSIjZjJmMmYyIiBmaWxsLW9wYWNpdHk9IjEiPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEuMjAzMTk4LCAzNy40Nzc5NTMpIj48Zz48cGF0aCBkPSJNIDI0LjI2NTYyNSAtMTIgTCAyNC4yNjU2MjUgLTI3LjczNDM3NSBMIDMxLjY3MTg3NSAtMjcuNzM0Mzc1IEwgMzEuNjcxODc1IDAgTCAyNS4wMzEyNSAwIEwgOS44NDM3NSAtMTcuMjUgTCA5Ljg0Mzc1IDAgTCAyLjQzNzUgMCBMIDIuNDM3NSAtMjcuNzM0Mzc1IEwgMTAuNzE4NzUgLTI3LjczNDM3NSBaIE0gMjQuMjY1NjI1IC0xMiAiLz48L2c+PC9nPjwvZz48ZyBmaWxsPSIjZjJmMmYyIiBmaWxsLW9wYWNpdHk9IjEiPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDQ0LjI0NDI2NiwgMzcuNDc3OTUzKSI+PGc+PHBhdGggZD0iTSAxMS4xMjUgLTIwLjgxMjUgTCAwLjY0MDYyNSAtMjAuODEyNSBMIDAuNjQwNjI1IC0yNy43MzQzNzUgTCAyOS40Njg3NSAtMjcuNzM0Mzc1IEwgMjkuNDY4NzUgLTIwLjgxMjUgTCAxOS4wMzEyNSAtMjAuODEyNSBMIDE5LjAzMTI1IDAgTCAxMS4xMjUgMCBaIE0gMTEuMTI1IC0yMC44MTI1ICIvPjwvZz48L2c+PC9nPjxnIGZpbGw9IiNmMmYyZjIiIGZpbGwtb3BhY2l0eT0iMSI+PGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoODMuMjU4NjEsIDM3LjQ3Nzk1MykiPjxnPjxwYXRoIGQ9Ik0gMzIuNTQ2ODc1IDAgTCAyMi45ODQzNzUgMCBMIDE1LjEyNSAtMTIuMTU2MjUgTCAxMC4yMTg3NSAtNi44NDM3NSBMIDEwLjIxODc1IDAgTCAyLjQzNzUgMCBMIDIuNDM3NSAtMjcuNzM0Mzc1IEwgMTAuMjE4NzUgLTI3LjczNDM3NSBMIDEwLjIxODc1IC0xNS43OTY4NzUgTCAyMS4yNjU2MjUgLTI3LjczNDM3NSBMIDMxLjg3NSAtMjcuNzM0Mzc1IEwgMjEuMzEyNSAtMTYuNjQwNjI1IFogTSAzMi41NDY4NzUgMCAiLz48L2c+PC9nPjwvZz48L2c+PC9nPjwvc3ZnPg=="

STORY_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{headline} — NTK News</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="NTK News">
<meta property="og:title" content="{headline_esc}">
<meta property="og:description" content="{description_esc}">
<meta property="og:url" content="{canonical_url}">
{og_image_tags}
<meta name="twitter:card" content="{twitter_card_type}">
<meta name="twitter:title" content="{headline_esc}">
<meta name="twitter:description" content="{description_esc}">
{twitter_image_tag}
<style>
  :root {{
    --blue:   #0798F2;
    --amber:  #F2AE2E;
    --terra:  #DC6550;
    --purple: #725ABF;
    --teal:   #01B2A7;
    --cream:  {cream};
    --dark:   {ink};
    --white:  #FFFFFF;
  }}

  * {{ margin:0; padding:0; box-sizing:border-box; }}

  body {{
    font-family: 'Source Serif 4', Georgia, serif;
    background: var(--cream);
    max-width: 640px;
    margin: 0 auto;
  }}

  a {{ color: var(--blue); }}

  .story-header {{
    background: var(--dark);
    border-bottom: 3px solid var(--blue);
  }}

  .story-header-inner {{
    padding: 0 20px;
    height: 56px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .back-btn {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: var(--blue);
    text-decoration: none;
  }}

  .story-header-logo {{ margin-left: auto; display: flex; align-items: center; }}
  .ntk-logo-img-sm {{ height: 20px; width: auto; display: block; }}

  .story-hero-wrap {{ background: var(--dark); }}

  .story-hero-image-wrap {{
    width: 100%;
    height: 220px;
    overflow: hidden;
    clip-path: polygon(0 0, 100% 0, 100% 88%, 0 100%);
  }}

  .story-hero-image-wrap img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}

  .story-hero {{
    background: var(--dark);
    padding: 24px 20px 28px;
  }}

  .story-hero-category {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--amber);
    margin-bottom: 10px;
  }}

  .story-hero-headline {{
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: clamp(20px, 5vw, 26px);
    color: var(--white);
    line-height: 1.2;
    margin-bottom: 12px;
  }}

  .story-hero-lede {{
    font-family: 'Source Serif 4', serif;
    font-size: 16px;
    font-weight: 300;
    line-height: 1.65;
    color: rgba(234,217,197,0.75);
  }}

  .story-sections {{ padding: 0 0 60px; }}

  .story-section {{ border-bottom: 1px solid rgba(38,31,35,0.1); }}

  .section-header {{
    padding: 18px 20px 10px;
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--white);
  }}

  .lies-section .section-header {{ background: rgba(220,101,80,0.04); }}

  .section-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}

  .section-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.5px;
    color: var(--dark);
  }}

  .section-body {{
    padding: 0 20px 22px;
    background: var(--white);
  }}

  .lies-section .section-body {{ background: rgba(220,101,80,0.04); }}

  .section-body p {{
    font-family: 'Source Serif 4', serif;
    font-size: 16px;
    line-height: 1.7;
    color: rgba(38,31,35,0.8);
    margin-bottom: 14px;
  }}

  .section-body p:last-child {{ margin-bottom: 0; }}

  .ntk-pullquote {{
    border-left: 3px solid var(--blue);
    margin: 18px 0;
    padding: 12px 16px;
    background: rgba(7,152,242,0.04);
  }}
  .ntk-pq-text {{
    font-family: 'Source Serif 4', serif;
    font-size: 19px !important;
    font-weight: 300;
    font-style: italic;
    line-height: 1.5 !important;
    color: var(--dark);
    margin-bottom: 7px !important;
  }}
  .ntk-pq-cite {{
    display: block;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--blue);
    font-style: normal;
  }}
  .ntk-stat {{
    border-left: 3px solid var(--amber);
    margin: 18px 0;
    padding: 14px 16px;
    background: rgba(242,174,46,0.05);
  }}
  .ntk-stat-num {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 34px;
    font-weight: 700;
    color: var(--amber);
    line-height: 1.1;
    margin-bottom: 5px;
  }}
  .ntk-stat-ctx {{
    font-family: 'Source Serif 4', serif;
    font-size: 14px;
    color: rgba(38,31,35,0.72);
    line-height: 1.5;
  }}

  .back-footer {{
    display: block;
    text-align: center;
    padding: 28px 20px 40px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: var(--blue);
    text-decoration: none;
  }}
</style>
</head>
<body>

  <header class="story-header">
    <div class="story-header-inner">
      <a class="back-btn" href="../">← Digest</a>
      <div class="story-header-logo">
        <img src="{logo}" alt="NTK" class="ntk-logo-img-sm">
      </div>
    </div>
  </header>

  <div class="story-hero-wrap">
    {hero_img}
    <div class="story-hero">
      <div class="story-hero-category">{category}</div>
      <div class="story-hero-headline">{headline_esc}</div>
      <div class="story-hero-lede">{lede_esc}</div>
    </div>
  </div>

  <div class="story-sections">

    <div class="story-section">
      <div class="section-header">
        <div class="section-dot" style="background:var(--blue);"></div>
        <span class="section-title">Truths — What Happened</span>
      </div>
      <div class="section-body">{truth}</div>
    </div>

    <div class="story-section">
      <div class="section-header">
        <div class="section-dot" style="background:var(--purple);"></div>
        <span class="section-title">Probabilities — What Will Likely Happen</span>
      </div>
      <div class="section-body">{prob}</div>
    </div>

    <div class="story-section">
      <div class="section-header">
        <div class="section-dot" style="background:var(--teal);"></div>
        <span class="section-title">Possibilities — What Could Happen</span>
      </div>
      <div class="section-body">{poss}</div>
    </div>

    <div class="story-section lies-section">
      <div class="section-header">
        <div class="section-dot" style="background:var(--terra);"></div>
        <span class="section-title">Lies / Narrative Distortions</span>
      </div>
      <div class="section-body">{lies}</div>
    </div>

  </div>

  <a class="back-footer" href="../">← Back to today's digest</a>

</body>
</html>
"""


def build_story_page(story, image_rel_url, image_abs_url, canonical_url):
    headline = story.get("headline", "")
    description = story.get("lede") or strip_html_for_description(story.get("truth", ""))
    has_image = bool(image_abs_url)
    og_image_tags = (
        f'<meta property="og:image" content="{image_abs_url}">\n'
        f'<meta property="og:image:width" content="1200">\n'
        f'<meta property="og:image:height" content="630">' if has_image else "")
    twitter_image_tag = (f'<meta name="twitter:image" content="{image_abs_url}">' if has_image else "")
    hero_img = (f'<div class="story-hero-image-wrap"><img src="{image_rel_url}" alt=""></div>'
                if has_image else "")
    return STORY_PAGE_TEMPLATE.format(
        headline=headline.replace("<", "").replace(">", ""),
        headline_esc=html_esc(headline), description_esc=html_esc(description),
        canonical_url=canonical_url, og_image_tags=og_image_tags,
        twitter_card_type="summary_large_image" if has_image else "summary",
        twitter_image_tag=twitter_image_tag, ink=INK, cream=CREAM,
        logo=LOGO_DATA_URI,
        category=html_esc(story.get("category", "")), lede_esc=html_esc(description),
        hero_img=hero_img,
        truth=story.get("truth", ""), prob=story.get("prob", ""),
        poss=story.get("poss", ""), lies=story.get("lies", ""))


ARCHIVE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archive — NTK News</title>
<style>
  body {{ background:{cream}; color:{ink}; font-family:'Source Serif 4',Georgia,serif;
    max-width:640px; margin:0 auto; padding:24px 20px 60px; }}
  h1 {{ font-family:'Space Grotesk',sans-serif; }}
  .ed {{ margin-bottom:28px; }}
  .ed-date {{ font-family:'Space Grotesk',sans-serif; font-size:13px; color:{teal};
    text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }}
  .ed a.day {{ font-weight:600; }}
  ul {{ margin:6px 0 0; padding-left:18px; }}
  li {{ margin-bottom:3px; font-size:15px; }}
</style>
</head>
<body>
<h1>Archive</h1>
{editions}
</body>
</html>
"""


def rebuild_archive(digest_dir, base_url):
    date_dirs = sorted([d for d in digest_dir.iterdir()
                        if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", d.name)], reverse=True)
    blocks = []
    for d in date_dirs:
        meta_path = d / "_headlines.json"
        if not meta_path.exists():
            continue
        headlines = json.loads(meta_path.read_text())
        items = "\n".join(
            f'    <li><a href="{base_url}/digest/v2/{d.name}/{h["slug"]}/">{html_esc(h["headline"])}</a></li>'
            for h in headlines)
        blocks.append(f'<div class="ed"><div class="ed-date">{d.name}</div>'
                       f'<a class="day" href="{base_url}/digest/v2/{d.name}/">Full edition</a>'
                       f'<ul>\n{items}\n  </ul></div>')
    archive_dir = digest_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.html").write_text(
        ARCHIVE_TEMPLATE.format(cream=CREAM, ink=INK, teal=TEAL, editions="\n".join(blocks)))
    log(f"archive rebuilt: {len(date_dirs)} editions listed")


def main():
    repo_root = Path(os.environ.get("GITHUB_WORKSPACE", "."))
    story_json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DEFAULT
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base_url = "https://ntknews.org"
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    digest_dir = repo_root / "digest" / "v2"
    live_index_path = digest_dir / "index.html"

    payload = json.loads(story_json_path.read_text())
    # Back-compat: a bare array is the old (pre-2026-08-27) shape, in case
    # this ever runs against a stale lineup-publish.json left over from
    # before Today overview was wired through the same publish step.
    if isinstance(payload, list):
        stories, today = payload, None
    else:
        stories, today = payload.get("stories", []), payload.get("today")
    log(f"{len(stories)} stories loaded from {story_json_path}"
        + (" (no Today overview in this payload)" if not today else ""))

    # 1. Fun fact — real source, graceful fallback to whatever's already there.
    fun_fact = pick_fun_fact(api_key) if api_key else None
    if fun_fact:
        log(f"fun fact: {fun_fact[:70]}...")
    else:
        log("no fresh fun fact generated — leaving today's existing one in place")

    # 2. Compute this edition's slugs and per-story permalinks FIRST — the
    # homepage regeneration in step 3 needs these already attached to each
    # story dict so the interactive share button has a real URL to use,
    # not the swipe-app's own page. (Previously this ran after step 3,
    # which meant `permalink` didn't exist yet when the stories block was
    # written — the bug behind the share button sharing the wrong URL.)
    slugs = unique_slugs(stories)
    for story, slug in zip(stories, slugs):
        story["permalink"] = f"{base_url}/digest/v2/{date_str}/{slug}/"

    # 3. Regenerate the LIVE homepage in place. This is the piece that
    # makes the whole chain zero-click: no more paste, ever.
    current_html = live_index_path.read_text()
    new_html = regenerate_homepage(current_html, stories, fun_fact)
    new_html = regenerate_today(new_html, today)
    live_index_path.write_text(new_html)
    log(f"live homepage regenerated: {live_index_path}")

    # 4. Freeze today's now-correct homepage at a permanent dated path.
    dated_dir = digest_dir / date_str
    dated_dir.mkdir(parents=True, exist_ok=True)
    (dated_dir / "index.html").write_text(new_html)

    # 5. Per-story permalinks + images. Slugs already computed in step 2 —
    # reused here rather than recomputed, so the permalink written into the
    # homepage's stories array and the actual page built on disk can never
    # drift apart from each other.
    headlines_meta = []
    for story, slug in zip(stories, slugs):
        story_dir = dated_dir / slug
        story_dir.mkdir(parents=True, exist_ok=True)
        canonical_url = story["permalink"]

        image_rel_url = image_abs_url = None
        if story.get("featuredImage"):
            img_name = f"{slug}.jpg"
            if decode_image(story["featuredImage"], digest_dir / "images" / img_name):
                image_rel_url = f"../../images/{img_name}"
                image_abs_url = f"{base_url}/digest/v2/images/{img_name}"

        page = build_story_page(story, image_rel_url, image_abs_url, canonical_url)
        (story_dir / "index.html").write_text(page)
        headlines_meta.append({"slug": slug, "headline": story.get("headline", "")})
        log(f"  story page: {slug}/  (image: {'yes' if image_abs_url else 'no'})")

    (dated_dir / "_headlines.json").write_text(json.dumps(headlines_meta, indent=1))

    # 6. Archive, rebuilt from what's actually on disk.
    rebuild_archive(digest_dir, base_url)

    # 7. Last-published marker — what Pulse's button reads to show you
    # "last published: N ago" without you having to go check GitHub.
    (repo_root / "ntk-pulse" / "data" / "last-published.json").write_text(
        json.dumps({"at": datetime.now(timezone.utc).isoformat(), "stories": len(stories)}, indent=1))

    log("")
    log(f"Done. Live at {base_url}/digest/v2/")


DATA_DEFAULT = Path("ntk-pulse/data/lineup-publish.json")

if __name__ == "__main__":
    main()
