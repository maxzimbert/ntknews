#!/usr/bin/env python3
"""NTK Pulse — NPR newscast monitor (T-0037).

Scrapes NPR News Now's show page (not the RSS feed — the feed only keeps
~3 episodes; the page keeps ~10 hours), transcribes each hourly newscast
with whisper.cpp, and extracts the topics it covered. Purely a monitoring
signal for the editor — what NPR's desk is covering and how it changes
hour over hour, surfaced in Pulse's Lineup tab above the recommendations
zone. Deliberately does NOT match against clusters.json or feed anything
back into assembly/triage — see docs/decisions.md before changing that;
it was a live design question, resolved as "monitoring only, for now."

Why local whisper.cpp and not a hosted ASR API: transcribing ten ~5-minute
clips a day costs nothing on a whisper.cpp binary (a full day of audio
transcribes in minutes on ordinary hardware). A hosted per-minute API
would be a new vendor and a new secret for a job that's free to run as
stdlib + one system binary + one model file.

Requires (system, not pip):
  - whisper-cli + a ggml model (path below) — brew install whisper.cpp locally;
    the workflow builds it from source and caches the binary
  - ffmpeg (preferred) or afconvert (macOS-only fallback, local testing)

Topic extraction is Haiku, same call pattern as triage.py (stdlib urllib,
x-api-key header). Skips gracefully with no ANTHROPIC_API_KEY, same as
triage.py — an episode without a key just has no topics until a run with
one reaches it; capture() and thread() both still work on raw transcripts.

Stdlib only otherwise.

Usage:
  python newscast.py capture   # scrape, download, transcribe new episodes
  python newscast.py label     # Haiku: extract topics for un-labeled episodes
  python newscast.py thread    # group today's topics into hour-over-hour rows
  python newscast.py           # all three, in order
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cluster import entities  # noqa: E402 — reuse Pulse's own entity extraction, one vocabulary across the whole pipeline

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "newscasts"
SHOW_URL = "https://www.npr.org/podcasts/500005/npr-news-now"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
TIMEOUT = 20

MODEL = "claude-haiku-4-5-20251001"  # matches triage.py's pin — see T-0005, both should move together
API_URL = "https://api.anthropic.com/v1/messages"

# Not committed — a 487MB model file has no business in git. Set this env
# var (or drop the file at this default path) before running `capture`.
WHISPER_MODEL = os.environ.get("NEWSCAST_WHISPER_MODEL", str(ROOT / "ggml-small.en.bin"))
WHISPER_BIN = os.environ.get("NEWSCAST_WHISPER_BIN", "whisper-cli")

EPISODE_ID_RE = re.compile(r"nx-s1-(\d{8})-(\d{4})-long")
MP3_URL_RE = re.compile(r'https://[^"\'>\s]*\.mp3[^"\'>\s]*')

# Below this, a shared entity between two topic labels is coincidental
# generic vocabulary ("Trump" alone proves nothing on a day when six
# different stories mention him in passing) rather than the same thread.
MIN_SHARED_ENTITIES = 2

# An entity that shows up in more than this fraction of today's topics is
# treated as background noise for matching purposes, not a distinguishing
# signal — same problem cluster.py's own entity IDF solves for wire
# headlines, cheaper version for a much smaller, single-day topic set.
# Found by running this for real against a live NPR day: without this,
# "Trump" + "U.S." alone matched every political story to every other one.
GENERIC_TOPIC_FRACTION = 0.25

# How many of the most recently captured hours the grid covers. Matches
# the show page's own retention (~10 hours) rather than a calendar day —
# see the comment in thread() on why calendar-date filtering breaks at
# midnight.
RECENT_HOURS = 10


def log(msg):
    print(f"[newscast] {msg}", file=sys.stderr)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def list_episodes():
    """Scrape the show page for today's episode ids and their mp3 URLs.

    Returns {episode_id: mp3_url}, one entry per id (the page lists each
    episode once; a duplicate URL is a no-op either way)."""
    html = fetch(SHOW_URL).decode("utf-8", "replace")
    urls = {}
    for m in MP3_URL_RE.finditer(html):
        url = m.group(0).replace("&amp;", "&")
        eid = EPISODE_ID_RE.search(url)
        if eid:
            urls[f"nx-s1-{eid.group(1)}-{eid.group(2)}"] = url
    return urls


def have(binary):
    return subprocess.run(["which", binary], capture_output=True).returncode == 0


def to_wav(mp3_path, wav_path):
    if have("ffmpeg"):
        # -f wav is load-bearing, not decoration: ffmpeg infers the output
        # muxer from the destination filename's extension by default, and
        # the temp file is named *.wav.tmp — ".tmp" isn't a format ffmpeg
        # recognizes, so every conversion failed on the first real Actions
        # run with "Unable to choose an output format." Forcing it removes
        # the dependency on the filename entirely.
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3_path),
               "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path)]
    elif have("afconvert"):
        # macOS only. Fine for local runs; the workflow installs ffmpeg.
        cmd = ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
               str(mp3_path), str(wav_path)]
    else:
        raise RuntimeError("no audio converter found (need ffmpeg or afconvert)")
    subprocess.run(cmd, check=True, capture_output=True)


def transcribe(wav_path, out_prefix):
    subprocess.run(
        [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", str(wav_path),
         "-otxt", "-of", str(out_prefix), "-np", "-t", "8"],
        check=True, capture_output=True,
    )
    txt_path = out_prefix.with_suffix(".txt")
    text = txt_path.read_text().strip()
    txt_path.unlink(missing_ok=True)
    return text


def capture():
    DATA.mkdir(parents=True, exist_ok=True)
    if not Path(WHISPER_MODEL).exists():
        log(f"model not found at {WHISPER_MODEL} — set NEWSCAST_WHISPER_MODEL. Nothing captured.")
        return []
    episodes = list_episodes()
    log(f"{len(episodes)} episodes on the show page")
    new = []
    for eid, url in sorted(episodes.items()):
        out_json = DATA / f"{eid}.json"
        if out_json.exists():
            continue
        log(f"capturing {eid}")
        tmp_mp3 = DATA / f"{eid}.mp3.tmp"
        tmp_wav = DATA / f"{eid}.wav.tmp"
        try:
            mp3_bytes = fetch(url)
            tmp_mp3.write_bytes(mp3_bytes)
            log(f"  downloaded {len(mp3_bytes)} bytes")
            to_wav(tmp_mp3, tmp_wav)
            # Explicit prefix, independent of tmp_wav's own name — whisper-cli
            # appends .txt to whatever -of is given, and tmp_wav carries a
            # .wav.tmp double suffix Path.with_suffix() can't cleanly strip
            # in one call (it only removes the last suffix). Caught by
            # running this against a live episode before it reached a cron.
            text = transcribe(tmp_wav, DATA / eid)
        except subprocess.CalledProcessError as e:
            # stderr is the whole point of capturing it — a bare str(e) is
            # just "exit status N", which is exactly what made the first
            # real Actions run of this unreadable: ffmpeg failed on every
            # episode and the log said nothing about why.
            stderr = (e.stderr or b"").decode("utf-8", "replace").strip()
            log(f"  FAILED {eid}: {e}\n    stderr: {stderr[:600]}")
            continue
        except Exception as e:
            log(f"  FAILED {eid}: {e}")
            continue
        finally:
            tmp_mp3.unlink(missing_ok=True)
            tmp_wav.unlink(missing_ok=True)
        date_str, hhmm = EPISODE_ID_RE.search(url).groups()
        record = {
            "id": eid,
            "date": date_str,
            "hour": f"{hhmm[:2]}:{hhmm[2:]}",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source_url": url,
            "word_count": len(text.split()),
            "transcript": text,
            "topics": None,  # filled in by `label`
        }
        out_json.write_text(json.dumps(record, indent=2))
        new.append(eid)
        log(f"  ok — {record['word_count']} words")
    return new


TOPIC_PROMPT = """You are extracting the story list from an NPR News Now hourly newscast transcript.

Read the transcript and list each distinct news item it covered, in the order it aired. Skip sponsor messages, anchor intros/outros ("Live from NPR News..."), and station identification — those are not stories.

For each item, write one line: a plain, specific description of what happened, the way an editor would log it — not a dramatic headline. Roughly 8-16 words. Include the person or place involved by name if the transcript names one.

Respond with ONLY a JSON array of strings, nothing else. Example:
["Vice President Vance pulls 750,000 people off ACA marketplace rolls, citing fraud", "Hurricane Polo strengthens to Category 5 off Mexico's southwestern coast"]

TRANSCRIPT:
"""


def _parse_json_lenient(text):
    """Same repair pass as triage.py — Haiku's occasional smart-quote /
    trailing-comma JSON, kept in sync deliberately rather than imported,
    since the two callers are tolerant of slightly different shapes."""
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    repaired = (text.replace("“", '"').replace("”", '"')
                    .replace("‘", "'").replace("’", "'"))
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return json.loads(repaired)


def call_claude_topics(api_key, transcript):
    body = {
        "model": MODEL,
        "max_tokens": 600,
        "messages": [{"role": "user", "content": TOPIC_PROMPT + transcript}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    topics = _parse_json_lenient(text)
    if not isinstance(topics, list):
        raise ValueError(f"expected a JSON array, got {type(topics)}")
    return [str(t).strip() for t in topics if str(t).strip()]


def label():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        log("ANTHROPIC_API_KEY not set — skipping labeling, captured episodes keep topics: null.")
        return
    for f in sorted(DATA.glob("*.json")):
        if f.name in ("signal.json", "today.json"):
            continue
        record = json.loads(f.read_text())
        if record.get("topics") is not None:
            continue  # already labeled — never re-pay for an episode once it's done
        log(f"labeling {record['id']}")
        try:
            topic_strs = call_claude_topics(api_key, record["transcript"])
        except Exception as e:
            log(f"  FAILED {record['id']}: {e}")
            continue
        record["topics"] = [{"text": t, "entities": sorted(entities(t))} for t in topic_strs]
        f.write_text(json.dumps(record, indent=2))
        log(f"  ok — {len(topic_strs)} topics")


def thread():
    """Group today's labeled topics into hour-over-hour rows by entity
    overlap, using only today's own topic set — no clusters.json, no
    Pulse lineup involved. See GENERIC_TOPIC_FRACTION above for why raw
    overlap isn't enough on its own."""
    episodes = []
    for f in sorted(DATA.glob("*.json")):
        if f.name in ("signal.json", "today.json"):
            continue
        record = json.loads(f.read_text())
        if record.get("topics"):
            episodes.append(record)
    episodes.sort(key=lambda e: (e["date"], e["hour"]))
    if not episodes:
        log("no labeled episodes — run `capture` then `label` first")
        return

    # "Today" means "the most recent broadcast stretch," not "matches
    # today's calendar-date string." NPR's own id scheme rolls the date
    # digits at local midnight (confirmed against a real capture: ...-2300
    # was immediately followed by ...-0000 the next date), so a straight
    # date-string filter silently drops every earlier hour the moment a
    # post-midnight episode exists — caught by a smoke test against real
    # hand-verified topics before this ever reached a cron, not in
    # production. Window to the last RECENT_HOURS captured episodes
    # instead, which is what the show page itself effectively bounds this
    # to anyway (~10 hours of retention).
    todays = episodes[-RECENT_HOURS:]

    all_topics = []  # [(hour, text, entity_set)]
    for e in todays:
        for t in e["topics"]:
            all_topics.append((e["hour"], t["text"], set(t["entities"])))

    if not all_topics:
        log("no topics to thread")
        return

    from collections import Counter
    df = Counter()
    for _, _, ents in all_topics:
        df.update(ents)
    cutoff = max(1, int(len(all_topics) * GENERIC_TOPIC_FRACTION))
    generic = {ent for ent, c in df.items() if c > cutoff}

    threads = []  # [{"text": anchor text, "hours": [...], "entities": set}]
    for hour, text, ents in all_topics:
        distinctive = ents - generic
        best = None
        for th in threads:
            shared = distinctive & (th["entities"] - generic)
            if len(shared) >= MIN_SHARED_ENTITIES:
                best = th
                break
        if best:
            best["hours"].append(hour)
            best["entities"] |= ents
        else:
            threads.append({"text": text, "hours": [hour], "entities": set(ents)})

    threads.sort(key=lambda th: -len(th["hours"]))
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": todays[-1]["date"],
        "episodes": [{"id": e["id"], "hour": e["hour"]} for e in todays],
        "latest_hour": todays[-1]["hour"],
        "latest_topics": [t["text"] for t in todays[-1]["topics"]],
        "threads": [{"text": th["text"], "hours": th["hours"], "count": len(th["hours"])}
                    for th in threads],
    }
    (DATA / "today.json").write_text(json.dumps(out, indent=2))
    log(f"{len(threads)} threads across {len(todays)} hours, written to data/newscasts/today.json")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("capture", "all"):
        capture()
    if cmd in ("label", "all"):
        label()
    if cmd in ("thread", "all"):
        thread()
