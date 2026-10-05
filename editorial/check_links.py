#!/usr/bin/env python3
"""
Link checker for the Object Matrix (T-0068).

A reader who taps an object leaves NTK for its "Source URL", so a dead link is the
failure the reader sees. This fetches every linked object's URL and records what it
found in editorial/object-links-health.json, beside the matrix, so the xlsx stays
hand-edited.

  python3 editorial/check_links.py                 # check every link
  python3 editorial/check_links.py --stale 7       # only links not checked in 7 days
  python3 editorial/check_links.py --fail-on-dead  # exit 1 if any link is dead (for CI)

Statuses
  live            fetched, and the page looks like a page
  dead            404 or 410, a server error that has repeated, a host that does not
                  resolve, or a "soft 404" (a 200 that is really an error page)
  blocks_scripts  403, 401, 429 or a bot challenge. Many archives refuse scripts
                  (loc.gov, state.gov, Founders Online): this is NOT dead and the
                  object stays eligible. A human has to look.
  paywall         402, or a host that is paywalled
  moved           redirected to a different host or to the host's front page
  unreachable     timeout or network error. Counts as a failure; becomes dead after
                  three runs in a row.

Only `dead` makes an object ineligible (editorial/build_backstory.py).
`note` carries observations that do not change the status, for example a matrix year
that does not appear anywhere on the page, which is how a wrong-document link shows up.
"""
import argparse, html, json, re, ssl, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "editorial" / "NTK_Backstory_Object_Matrix.xlsx"
HEALTH = ROOT / "editorial" / "object-links-health.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; ntknews-linkcheck/1.0; +https://ntknews.org)"}
PAYWALLED = ("theatlantic.com", "harpers.org", "nytimes.com", "newyorker.com", "wsj.com",
             "washingtonpost.com", "ft.com", "foreignaffairs.com", "economist.com")
SOFT_404 = ("page not found", "page cannot be found", "404 not found", "error 404", "has encountered an error",
            "technical difficulties", "no longer available", "this page does not exist", "item not found",
            "we couldn't find", "the page you requested")
CHALLENGE = ("just a moment", "checking your browser", "enable javascript and cookies", "access denied",
             "attention required")
FAILS_TO_DEAD = 3
now = lambda: datetime.now(timezone.utc)


def host(u):
    h = (urlparse(u).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def linked():
    ws = openpyxl.load_workbook(MATRIX, read_only=True)["Objects"]
    rows = list(ws.iter_rows(values_only=True))
    u = rows[0].index("Source URL")
    out = {}
    for r in rows[1:]:
        if r[u]:
            out.setdefault(str(r[u]).strip(), []).append({"title": str(r[5]), "year": str(r[1] or "")[:4]})
    return out


_gate = {}
_gate_lock = threading.Lock()


def polite(h):
    """At most one request a second to one host."""
    with _gate_lock:
        lock = _gate.setdefault(h, threading.Lock())
    with lock:
        time.sleep(0.8)


class _Redirects(urllib.request.HTTPRedirectHandler):
    """urllib in older Pythons does not follow 308 (permanent redirect)."""
    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_302(req, fp, 302, msg, headers)


_opener = urllib.request.build_opener(_Redirects)


BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0 Safari/537.36"}


def fetch(u, headers=None):
    polite(host(u))
    req = urllib.request.Request(u, headers=headers or UA)
    with _opener.open(req, timeout=25) as r:
        body = r.read(600_000)
        return r.status, r.geturl(), r.headers.get("Content-Type", ""), body


def classify(u, objs, prev):
    rec = {"checked": now().isoformat(timespec="seconds"), "final_url": None, "http": None, "note": None}
    failures = (prev or {}).get("failures", 0)
    try:
        code, final, ctype, body = fetch(u)
        rec["http"], rec["final_url"] = code, final if final != u else None
        is_pdf = body[:4] == b"%PDF" or "pdf" in ctype.lower()
        text = ""
        if not is_pdf:
            raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", body.decode("utf-8", "replace"))
            text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip().lower()
        low = text[:5000]
        if "technical difficulties" in low and "forbidden" in low:
            rec["status"] = "blocks_scripts"; rec["note"] = "the host's bot-block page"
        elif any(c in low for c in CHALLENGE) and len(text) < 3000:
            rec["status"] = "blocks_scripts"
        elif not is_pdf and len(text) < 5000 and any(p in low for p in SOFT_404):
            rec["status"] = "dead"; rec["note"] = "soft 404: the page is an error page"
        elif any(host(u).endswith(p) for p in PAYWALLED):
            rec["status"] = "paywall"
        elif final != u and (host(final) != host(u) and not host(final).endswith(host(u).split(".", 1)[-1])
                             or urlparse(final).path in ("", "/")):
            rec["status"] = "moved"; rec["note"] = f"redirected to {final}"
        else:
            rec["status"] = "live"
        # a wrong-document link shows up as a year that appears nowhere on the page
        if rec["status"] == "live" and text and len(text) > 800:
            years = {o["year"] for o in objs if o["year"].isdigit()}
            if years and not any(y in text for y in years):
                rec["note"] = ("matrix year " + "/".join(sorted(years)) + " does not appear on the page; "
                               "check that this is the right document")
        failures = 0
    except urllib.error.HTTPError as e:
        rec["http"] = e.code
        if e.code in (404, 410):
            # Some hosts (state.gov) answer a script with 404 and a browser with 200 or 403.
            # Ask again the way a browser would before calling a link dead.
            second = None
            try:
                second = fetch(u, BROWSER)[0]
            except urllib.error.HTTPError as e2:
                second = e2.code
            except Exception:
                second = None
            if second is not None and second < 400:
                rec["status"] = "live"; rec["note"] = f"{e.code} to the checker, {second} to a browser"
            elif second in (401, 403, 429, 999):
                rec["status"] = "blocks_scripts"; rec["note"] = f"{e.code} to the checker, {second} to a browser"
            else:
                rec["status"] = "dead"; failures = FAILS_TO_DEAD
        elif e.code == 402:
            rec["status"] = "paywall"
        elif e.code in (401, 403, 429, 999):
            rec["status"] = "blocks_scripts"
        else:
            failures += 1
            rec["status"] = "dead" if failures >= FAILS_TO_DEAD else "unreachable"
            rec["note"] = f"HTTP {e.code}"
    except (ssl.SSLError, ConnectionResetError) as e:
        # A handshake this environment cannot complete, or a host that drops script
        # connections. Typical of bot defences and old TLS; says nothing about the page.
        rec["status"] = "blocks_scripts"; rec["note"] = f"{type(e).__name__}: {str(e)[:60]}"
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), (ssl.SSLError, ConnectionResetError)):
            rec["status"] = "blocks_scripts"; rec["note"] = f"{type(e.reason).__name__}: {str(e.reason)[:60]}"
        else:
            failures += 1
            rec["status"] = "dead" if failures >= FAILS_TO_DEAD else "unreachable"
            rec["note"] = f"{type(e).__name__}: {str(e)[:60]}"
    except Exception as e:  # DNS, timeout
        failures += 1
        rec["status"] = "dead" if failures >= FAILS_TO_DEAD else "unreachable"
        rec["note"] = f"{type(e).__name__}: {str(e)[:60]}"
    rec["failures"] = failures
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale", type=int, help="only links not checked in this many days")
    ap.add_argument("--recheck", help="comma list of statuses: only links last recorded with one of these")
    ap.add_argument("--fail-on-dead", action="store_true")
    a = ap.parse_args()
    prev = json.loads(HEALTH.read_text()) if HEALTH.exists() else {}
    urls = linked()
    todo = []
    for u in urls:
        p = prev.get(u)
        if a.stale and p and datetime.fromisoformat(p["checked"]) > now() - timedelta(days=a.stale):
            continue
        if a.recheck and (not p or p["status"] not in a.recheck.split(",")):
            continue
        todo.append(u)
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda u: classify(u, urls[u], prev.get(u)), todo))
    health = {u: v for u, v in prev.items() if u in urls}          # drop links no longer in the matrix
    for u, r in zip(todo, res):
        health[u] = r
    HEALTH.write_text(json.dumps(dict(sorted(health.items())), indent=1, ensure_ascii=False) + "\n")
    counts = {}
    for u in urls:
        s = health[u]["status"]; counts[s] = counts.get(s, 0) + 1
    print(f"{len(urls)} links, {len(todo)} checked: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for s in ("dead", "moved", "unreachable"):
        for u in urls:
            if health[u]["status"] == s:
                print(f"  {s.upper():12s} {urls[u][0]['year']} {urls[u][0]['title'][:40]:40s} {u[:70]}  {health[u].get('note') or ''}")
    notes = [u for u in urls if health[u].get("note") and health[u]["status"] == "live"]
    if notes:
        print(f"{len(notes)} live links carry a note (open the file to read them)")
    if a.fail_on_dead and counts.get("dead"):
        sys.exit(1)


if __name__ == "__main__":
    main()
