"""NTK's approved publishers: the 91 outlets the Stream reads, kept once, in NTK_SOURCES in
netlify/functions/news.js. A news report may stand in a Backstory, and join the Object Matrix marked as news,
only from one of these, and only when no primary source will do (the editor, 2026-11-02; docs/decisions.md).
Pulse keeps a copy (NTK_PUBLISHERS); the T-0114 check holds the two equal."""
import re
from pathlib import Path

NEWS_JS = Path(__file__).resolve().parent.parent / "netlify" / "functions" / "news.js"


def approved_hosts():
    m = re.search(r"NTK_SOURCES\s*=\s*\[([\s\S]*?)\]", NEWS_JS.read_text())
    return tuple(re.findall(r"'([^']+)'", m.group(1))) if m else ()


def is_approved(url):
    host = str(url or "").split("/")[2].lower() if str(url or "").count("/") >= 2 else ""
    return any(host == d or host.endswith("." + d) for d in approved_hosts())
