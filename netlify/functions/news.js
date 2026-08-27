const https = require('https');

const NTK_SOURCES = [
  'nytimes.com','bloomberg.com','cbc.ca','bbc.com','france24.com','dw.com',
  'wsj.com','apnews.com','reuters.com','haaretz.com','jpost.com','aljazeera.com',
  'washingtonpost.com','postandcourier.com','miamiherald.com','latimes.com',
  'cnn.com','nbcnews.com','abcnews.go.com','abc.net.au','theaustralian.com.au',
  'dailymail.co.uk','thedailybeast.com','telegraph.co.uk','spectator.org',
  'talkingpointsmemo.com','nhk.or.jp','en.yna.co.kr','koreaherald.com',
  'tuko.co.ke','standardmedia.co.ke','elpais.com.uy','afp.com','rainews.it',
  'ansa.it','corriere.it','independent.co.uk','ft.com','npr.org','foxnews.com',
  'cnbc.com','ny1.com','spectrumnews1.com','spectrumlocalnews.com','ajc.com',
  'atlantablackstar.com','pbs.org','cbsnews.com','theatlantic.com','newyorker.com',
  'economist.com','theweek.com','thebulwark.com','heathercoxrichardson.substack.com',
  'semafor.com','newrepublic.com','fox5dc.com','fox5atlanta.com','wgbh.org',
  'wbur.org','wbez.org','laist.com','chicagoreader.com','houstonchronicle.com',
  'houstonpublicmedia.org','gardenandgun.com','vogue.com','teenvogue.com',
  'vogue.co.uk','glamour.com','glamourmagazine.co.uk','nbcwashington.com',
  'freebeacon.com','mcclatchydc.com','washingtonian.com','usatoday.com',
  'goodmorningamerica.com','gma.yahoo.com','chalkbeat.org','hechingerreport.org',
  'the74million.org','chronicle.com','insidehighered.com','statnews.com',
  'kffhealthnews.org','thetrace.org','themarshallproject.org','propublica.org',
  'mediaite.com','hollywoodreporter.com','deadline.com'
];

const RECENT_WINDOW_DAYS = 7;

// ── Generic HTTPS GET, JSON response ──────────────────────────────────────────
function getJson(hostname, path, extraHeaders) {
  return new Promise((resolve) => {
    const options = {
      hostname,
      path,
      method: 'GET',
      headers: Object.assign({ 'Accept': 'application/json' }, extraHeaders || {})
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location) {
          return resolve({ redirect: res.headers.location });
        }
        try { resolve({ statusCode: res.statusCode, json: JSON.parse(data) }); }
        catch { resolve({ statusCode: res.statusCode, error: 'non-JSON response' }); }
      });
    });
    req.on('error', err => resolve({ statusCode: 500, error: err.message }));
    req.setTimeout(8000, () => { req.destroy(); resolve({ statusCode: 500, error: 'timeout' }); });
    req.end();
  });
}

// ── EventRegistry: POST to eventregistry.org ─────────────────────────────────
function post(path, body) {
  return new Promise((resolve) => {
    const bodyStr = JSON.stringify(body);
    const options = {
      hostname: 'eventregistry.org',
      path,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(bodyStr) }
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ statusCode: res.statusCode, body: data }));
    });
    req.on('error', err => resolve({ statusCode: 500, body: JSON.stringify({ error: err.message }) }));
    req.write(bodyStr);
    req.end();
  });
}

// ── Exa: POST to api.exa.ai ───────────────────────────────────────────────────
function exaPost(body, path='/search') {
  return new Promise((resolve) => {
    const bodyStr = JSON.stringify(body);
    const options = {
      hostname: 'api.exa.ai',
      path,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.EXA_API_KEY,
        'Content-Length': Buffer.byteLength(bodyStr)
      }
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ statusCode: res.statusCode, body: data }));
    });
    req.on('error', err => resolve({ statusCode: 500, body: JSON.stringify({ error: err.message }) }));
    req.write(bodyStr);
    req.end();
  });
}

exports.handler = async (event) => {
  const q = event.queryStringParameters || {};
  const mode = q.mode || 'fetch-by-uri';

  // National Weather Service — server-side because api.weather.gov's CORS
  // support is unreliable in practice (their own issue tracker has open
  // reports of it failing, and the User-Agent header their API requires
  // turns a simple request into a preflighted one that then fails too).
  // Proxying through here sidesteps that entirely — this is a normal
  // server-to-server call, no CORS involved.
  if (mode === 'weather') {
    const lat = parseFloat(q.lat), lon = parseFloat(q.lon);
    if (!isFinite(lat) || !isFinite(lon)) {
      return { statusCode: 400, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ error: 'lat/lon required' }) };
    }
    const uaHeaders = { 'User-Agent': '(ntknews.org, max.zimbert@icloud.com)' };
    try {
      const points = await getJson('api.weather.gov', `/points/${lat.toFixed(4)},${lon.toFixed(4)}`, uaHeaders);
      const forecastPath = points.json && points.json.properties && points.json.properties.forecast;
      if (!forecastPath) {
        return { statusCode: 200, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ error: 'no forecast for this location (likely outside the US)' }) };
      }
      const forecastUrl = new URL(forecastPath);
      const forecast = await getJson(forecastUrl.hostname, forecastUrl.pathname + forecastUrl.search, uaHeaders);
      const periods = (forecast.json && forecast.json.properties && forecast.json.properties.periods) || [];
      const todayPeriod = periods[0] || null;
      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify(todayPeriod ? {
          name: todayPeriod.name,
          temperature: todayPeriod.temperature,
          temperatureUnit: todayPeriod.temperatureUnit,
          shortForecast: todayPeriod.shortForecast,
          isDaytime: todayPeriod.isDaytime
        } : { error: 'no forecast periods returned' })
      };
    } catch (e) {
      return { statusCode: 200, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ error: e.message }) };
    }
  }

  // ── Simple URL metadata scrape ──────────────────────────────────────────────
  // Fetches a URL server-side (no CORS) and extracts title + meta description.
  // Used by the URL import flow on the Review Sources screen — no Exa needed,
  // no cost, just enough to confirm what the article is before synthesis.
  if (mode === 'fetch-url') {
    const url = q.url || '';
    if (!url) return { statusCode: 400, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ error: 'url required' }) };
    try {
      // Follows up to 2 redirects and reads enough HTML for paragraph extraction.
      const getOnce = (target) => new Promise((resolve) => {
        let parsed;
        try { parsed = new URL(target); } catch { return resolve({ error: 'bad url' }); }
        const options = {
          hostname: parsed.hostname,
          path: parsed.pathname + (parsed.search || ''),
          method: 'GET',
          headers: {
            'User-Agent': 'Mozilla/5.0 (compatible; NTKNews/1.0)',
            'Accept': 'text/html'
          }
        };
        const req = https.request(options, (res) => {
          if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location) {
            res.resume();
            return resolve({ redirect: new URL(res.headers.location, target).href });
          }
          let data = '';
          res.on('data', chunk => { data += chunk; if (data.length > 400000) req.destroy(); });
          res.on('end', () => resolve({ html: data }));
        });
        req.on('error', err => resolve({ error: err.message }));
        req.setTimeout(8000, () => { req.destroy(); resolve({ error: 'timeout' }); });
        req.end();
      });
      let result = await getOnce(url);
      for (let hop = 0; hop < 2 && result.redirect; hop++) result = await getOnce(result.redirect);

      const html = result.html || '';
      const titleMatch = html.match(/<title[^>]*>([^<]{1,200})<\/title>/i);
      const descMatch = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']{1,400})["']/i)
                     || html.match(/<meta[^>]+content=["']([^"']{1,400})["'][^>]+name=["']description["']/i)
                     || html.match(/<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']{1,400})["']/i);
      const ogTitleMatch = html.match(/<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']{1,200})["']/i);

      const title = (ogTitleMatch?.[1] || titleMatch?.[1] || '').trim().replace(/\s+/g,' ');
      const description = (descMatch?.[1] || '').trim().replace(/\s+/g,' ');

      // Crude article-body extraction: concatenated <p> text, scripts/styles
      // stripped, entity-decoded, capped by ?bodyLen (default 4000). Not a
      // readability engine — nav junk sneaks in on some sites — but far more
      // synthesis material than a 400-char meta description. Bot-blocked and
      // paywalled sites still return little or nothing; EventRegistry remains
      // the primary body source.
      const bodyCap = Math.min(parseInt(q.bodyLen) || 4000, 8000);
      const cleaned = html
        .replace(/<script[\s\S]*?<\/script>/gi, '')
        .replace(/<style[\s\S]*?<\/style>/gi, '')
        .replace(/<!--[\s\S]*?-->/g, '');
      const paras = [];
      const pRe = /<p[^>]*>([\s\S]*?)<\/p>/gi;
      let pm, total = 0;
      while ((pm = pRe.exec(cleaned)) && total < bodyCap) {
        const text = pm[1].replace(/<[^>]+>/g, ' ')
          .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"').replace(/&#0?39;|&apos;|&rsquo;|&#8217;/g, "'")
          .replace(/&nbsp;/g, ' ').replace(/&[a-z]+;|&#\d+;/gi, ' ')
          .replace(/\s+/g, ' ').trim();
        if (text.length > 60) { paras.push(text); total += text.length; }
      }
      const bodyText = paras.join('\n\n').slice(0, bodyCap);

      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ title, description, body: bodyText })
      };
    } catch(e) {
      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ title: '', description: '', error: e.message })
      };
    }
  }
  // Separate from EventRegistry — hits api.exa.ai directly.
  // Designed for stories under ~3 hours old that EventRegistry hasn't
  // clustered yet: deaths, resignations, verdicts, major sudden events.
  // Returns Exa's native response shape {results:[{title,url,publishedDate,highlights}]}
  // so the caller can normalize it separately from EventRegistry responses.
  if (mode === 'scan-exa') {
    const query = q.q || 'major breaking news today deaths resignations verdicts attacks';
    const hoursBack = parseInt(q.maxAgeHours) || 3;
    const startPublishedDate = new Date(Date.now() - hoursBack * 60 * 60 * 1000).toISOString();
    const result = await exaPost({
      query,
      type: 'auto',
      category: 'news',
      numResults: parseInt(q.numResults) || 10,
      startPublishedDate,
      contents: {
        highlights: true
      }
    });
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: result.body
    };
  }

  let path = '/api/v1/article/getArticles';
  let body;

  if (mode === 'scan-events') {
    // Pre-clustered events from EventRegistry, ranked by article volume.
    // sourceLocationUri scopes to North American publishers — softer than
    // sourceUri (which would require the 91-domain list) but editorially
    // relevant without the sports/entertainment noise of a true global pull.
    // sortBy:size surfaces stories with real momentum, not announcement noise.
    path = '/api/v1/event/getEvents';
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getEvents',
      sourceLocationUri: 'http://en.wikipedia.org/wiki/North_America',
      lang: 'eng',
      eventsCount: 25,
      eventsSortBy: 'size',
      eventsSortByAsc: false,
      minArticlesInEvent: 3,
      forceMaxDataTimeWindow: 7,
      resultType: 'events',
      includeEventTitle: true,
      includeEventSummary: true,
      includeEventArticleCounts: true,
      includeEventLocation: true,
      includeEventDate: true,
      includeEventCommonDates: true
    };
  } else if (mode === 'scan-more-event') {
    // Fetch articles for a specific event by its eventUri.
    // Used by "Scan more for this title" on left-column event cards.
    // pool=ntk restricts to the 91-source list; omit for broad.
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      eventUri: q.eventUri || '',
      lang: 'eng',
      articlesCount: parseInt(q.articlesCount) || 20,
      articlesSortBy: 'date',
      articlesSortByAsc: false,
      resultType: 'articles',
      includeArticleBody: true,
      articleBodyLen: Math.min(parseInt(q.bodyLen) || 1500, 8000),
      includeArticleDate: true,
      includeSourceInfo: true,
      isDuplicateFilter: 'skipDuplicates'
    };
    if (q.pool === 'ntk') body.sourceUri = NTK_SOURCES;
  } else if (mode === 'scan-ntk') {
    // Scan: return recent articles with short snippets for Claude to select from
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      lang: 'eng',
      articlesCount: 40,
      articlesSortBy: 'date',
      articlesSortByAsc: false,
      resultType: 'articles',
      includeArticleBody: true,
      articleBodyLen: 250,
      includeArticleDate: true,
      includeSourceInfo: true,
      // FIX: `skipDuplicates: true` was never a real EventRegistry parameter —
      // it was silently ignored, so wire-syndication duplicates were never
      // actually filtered. The real parameter is isDuplicateFilter.
      isDuplicateFilter: 'skipDuplicates',
      // NEW: see RECENT_WINDOW_DAYS above.
      forceMaxDataTimeWindow: RECENT_WINDOW_DAYS,
      sourceUri: NTK_SOURCES
    };
  } else if (mode === 'scan-broad') {
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      lang: 'eng',
      articlesCount: 40,
      articlesSortBy: 'date',
      articlesSortByAsc: false,
      resultType: 'articles',
      includeArticleBody: true,
      articleBodyLen: 250,
      includeArticleDate: true,
      includeSourceInfo: true,
      isDuplicateFilter: 'skipDuplicates', // FIX: same bug as scan-ntk
      forceMaxDataTimeWindow: RECENT_WINDOW_DAYS, // NEW
      startSourceRankPercentile: 0,
      // FIX: EventRegistry requires this value be divisible by 10 (valid
      // range 10-100). 15 violated that and may have been silently
      // misbehaving. Rounded up to 20 to stay close to the original
      // "top ~15% of sources" intent — change if you want it tighter.
      endSourceRankPercentile: 20
    };
  } else if (mode === 'resolve-location') {
    // Resolves a city/state string to an EventRegistry location URI — same
    // shape as resolve-concept above, just against the location index
    // instead of the concept index. 'place' covers cities/towns; 'country'
    // is included as a fallback for a reverse-geocode that only manages to
    // resolve a country (rare, but cheaper than failing outright).
    path = '/api/v1/suggestLocationsFast';
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      prefix: q.q || '',
      source: ['place', 'country'],
      lang: 'eng',
      count: 5
    };
  } else if (mode === 'local-news') {
    // Today's local-blend feature. sourceLocationUri (outlets based in the
    // reader's city) and locationUri (articles about an event there) are
    // separate EventRegistry filter dimensions — combining both in one
    // call would almost certainly AND-narrow to near-zero results, same
    // as conceptUri + keyword do elsewhere in this file. The client calls
    // this mode twice, once per filterBy, and merges/dedupes by URL —
    // same client-side-dedupe posture as everywhere else in this codebase.
    const locUri = q.locationUri || '';
    if (!locUri) {
      return { statusCode: 400, headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify({ error: 'locationUri required' }) };
    }
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      lang: 'eng',
      articlesCount: Math.min(parseInt(q.articlesCount) || 8, 15),
      articlesSortBy: 'date',
      articlesSortByAsc: false,
      resultType: 'articles',
      includeArticleBody: false,
      includeArticleDate: true,
      includeSourceInfo: true,
      isDuplicateFilter: 'skipDuplicates',
      forceMaxDataTimeWindow: 2,
    };
    if (q.filterBy === 'source') body.sourceLocationUri = [locUri];
    else body.locationUri = [locUri];
  } else if (mode === 'resolve-concept') {
    // NEW: resolves a person/org/topic name to its EventRegistry concept URI.
    // Use this for stories with no good keyword string to match — named
    // individuals, agencies, ongoing situations — where literal keyword
    // search has no wire-coverage phrase to latch onto (the "RFK Jr. calendar
    // transparency" problem). Returns a ranked list of candidate concepts;
    // pick the right one and pass its uri into scan-by-concept below.
    path = '/api/v1/suggestConceptsFast';
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      prefix: q.q || '',
      source: ['concepts'],
      lang: 'eng',
      conceptLang: 'eng',
      page: 1,
      count: 5
    };
  } else if (mode === 'context-scan') {
    // NEW (Pulse 2b): historical-arc retrieval for Summon Context. Same
    // concept-scoped search as scan-by-concept but with a wide window
    // (default 29 days, capped at 30 = standard archive access), sorted by
    // relevance rather than date, and a small count — this feeds the
    // BACKGROUND block of synthesis, not the source package. Kept as a
    // separate mode so widening this window can never loosen the tight
    // recency window Enrich depends on.
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      conceptUri: q.conceptUri || '',
      lang: 'eng',
      articlesCount: Math.min(parseInt(q.articlesCount) || 5, 10),
      articlesSortBy: 'rel',
      resultType: 'articles',
      includeArticleBody: true,
      articleBodyLen: Math.min(parseInt(q.bodyLen) || 1200, 3000),
      includeArticleDate: true,
      includeSourceInfo: true,
      isDuplicateFilter: 'skipDuplicates',
      forceMaxDataTimeWindow: Math.min(parseInt(q.windowDays) || 29, 30)
    };
    if (q.keyword) body.keyword = q.keyword;
  } else if (mode === 'scan-by-concept') {
    // NEW: searches by resolved concept URI instead of keyword matching.
    // Pass conceptUri (from resolve-concept) and optionally pool=ntk to
    // restrict to the 91-source list; omit pool to search broadly.
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      conceptUri: q.conceptUri || '',
      lang: 'eng',
      articlesCount: parseInt(q.articlesCount) || 20,
      articlesSortBy: 'date',
      articlesSortByAsc: false,
      resultType: 'articles',
      includeArticleBody: true,
      articleBodyLen: Math.min(parseInt(q.bodyLen) || 1500, 8000),
      includeArticleDate: true,
      includeSourceInfo: true,
      isDuplicateFilter: 'skipDuplicates',
      forceMaxDataTimeWindow: RECENT_WINDOW_DAYS
    };
    // Narrows a broad entity down to the specific story (e.g. "Kash Patel" +
    // keyword "UFC") instead of pulling that person's entire news firehose.
    if (q.keyword) body.keyword = q.keyword;
    if (q.pool === 'ntk') body.sourceUri = NTK_SOURCES;
  } else if (mode === 'fetch-by-uri') {
    // Fetch full bodies for specific article URIs selected during the scan
    const uris = (q.uris || '').split(',').filter(Boolean);
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      articleUri: uris,
      resultType: 'articles',
      includeArticleBody: true,
      articleBodyLen: Math.min(parseInt(q.bodyLen) || 1500, 8000),
      includeArticleDate: true,
      includeSourceInfo: true
    };
  } else {
    // Fallback keyword fetch (kept for URL import flow)
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      keyword: q.q || '',
      lang: 'eng',
      articlesCount: parseInt(q.articlesCount) || 5,
      articlesSortBy: 'date',
      articlesSortByAsc: false,
      resultType: 'articles',
      includeArticleBody: true,
      articleBodyLen: Math.min(parseInt(q.bodyLen) || 1500, 8000),
      includeArticleDate: true,
      includeSourceInfo: true,
      isDuplicateFilter: 'skipDuplicates' // FIX: same bug
    };
  }

  const result = await post(path, body);
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    body: result.body
  };
};
