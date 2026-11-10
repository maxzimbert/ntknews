---
id: T-0121
title: Local news on /today is from outlets in the reader's city, about that city, from the last two days, or it is not shown
status: BUILT
tags: [digest, defect]
anchor: netlify/functions/news.js:152
---

## What

Reported by the editor 2026-11-10: the "Near Los Angeles" block showed one story, from Oct 20, from a
site he did not trust.

Measured the same day by calling the live function (`netlify/functions/news.js`):

- **Los Angeles.** The first location suggestion is Los Angeles County, and the app took the first. With
  the county: 0 articles from outlets based there; 7 of 8 "about there" were ads on
  `clasificados.laopinion.com`, the eighth was dated Oct 21.
- **Boise.** The right place. Outlets based there carried wire copy (an Embraer earnings report, a North
  Carolina cyclist). "About there" was college box scores back to Oct 26.
- **Pittsburgh.** The right place. Outlets based there: eight TribLIVE items, all national wire and NFL
  trades. "About there": box scores back to Nov 6.
- `forceMaxDataTimeWindow: 2` was ignored. EventRegistry accepts only 7 or 31.
- The classifieds filter matched the URL path; the ads were on a subdomain.

Tried through the EventRegistry search, the same day:

| Query | Los Angeles | Boise | Pittsburgh |
|---|---|---|---|
| Outlets based there and tagged as about there | 2 | 0 | 0 |
| Outlets based there, the city named in the text, since yesterday, no sports or entertainment | 161 | 2 | 35 |
| The same, city or state named | not run | 6 | not run |

The second is real local reporting: LAist, the LA Times, KTLA and ABC7 on the council and the
mayor-elect; TribLIVE on the city budget and the schools plan.

Built 2026-11-10 on branch `T-0121-local-news`:

1. `mode=local-news` takes the city and the state by name and does the whole job. `pickLocation` takes
   the suggestion that is the city itself ("Los Angeles", or "Boise, Idaho" when the state matches), never
   a county, a neighbourhood or a namesake. No match means no block.
2. The query is outlets based in the place that name the city, from `dateStart` two days back, without
   the sports and entertainment categories. If that leaves fewer than two, it is asked once more with the
   city or the state.
3. `pickLocal` drops anything older than two days, classifieds by host and by path, and repeated
   headlines; puts headlines that name the place first; allows two per outlet and three in all. Fewer than
   two is shown as none.
4. The app (`digest/index.html`) makes one request and draws what comes back. The cache key is bumped so
   a cached block of old junk is not shown again.
5. Dated editions are frozen copies of the app that send the old request. They get an empty list.

**Unverified:** the function has not run against EventRegistry with these exact parameters. The query was
tested through a different client of the same service, and the selection through `scripts/test_local_news.js`
on the headlines that came back. The deploy preview is the first real run. Boise loses the Idaho Statesman
under the keyword filter, cause unknown (possibly its paywall); it shows public radio only.

## Why

The product's promise is closure, and its reader assumes most outlets are spinning her. A block of
classified ads and a three-week-old item from a partisan site, under the heading "Near Los Angeles", spends
that trust on the one part of /today no editor has read.

Showing nothing is the right failure. Two rules follow from it: no place when the city itself cannot be
matched, and no block for a single surviving headline.

Ruled out: a per-metro list of approved local outlets. It would be the best quality bar and it is a
standing editorial job for every city a reader opens the app in. The query above gets most of the way
with no list. Revisit if the junk that remains (celebrity sites based in Los Angeles whose text names the
city) reaches readers; headlines that name the place are ranked first to keep it out of the top three.

Ruled out: a model call to rank the headlines. It is a per-visitor cost with no login in front of it (the
note above `LOCAL_KEY` in `digest/index.html`).

Cost: three EventRegistry calls per reader per day before; two now, three when the city alone is thin.

## Check

```sh
node scripts/test_local_news.js >/dev/null || { echo "OPEN: the local news tests fail"; exit 1; }
grep -q "forceMaxDataTimeWindow: 2," netlify/functions/news.js && { echo "OPEN: the two-day window that EventRegistry ignores is back"; exit 1; }
grep -q "mode=local-news&city=" digest/index.html || { echo "OPEN: the app does not ask for local news by city"; exit 1; }
# Live: what a reader in Los Angeles gets right now. Two EventRegistry calls. A network failure is not a verdict.
out=$(curl -s -m 40 "https://ntknews.org/.netlify/functions/news?mode=local-news&city=Los%20Angeles&state=California") || { echo "offline: live check skipped"; exit 0; }
printf '%s' "$out" | python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: print("OPEN: the live function did not answer with JSON"); sys.exit(1)
if "place" not in d: print("OPEN: the live function is not the T-0121 one (no place in the answer)"); sys.exit(1)
arts = d.get("articles") or []
if d.get("place") != "Los Angeles": print("OPEN: Los Angeles resolved to", d.get("place")); sys.exit(1)
if len(arts) > 3 or len(arts) == 1: print("OPEN: %d headlines, wants 0, 2 or 3" % len(arts)); sys.exit(1)
bad = [a["url"] for a in arts if "clasificados" in a["url"] or "classifieds" in a["url"]]
if bad: print("OPEN: classifieds are back:", bad[0]); sys.exit(1)
' || exit 1
```
