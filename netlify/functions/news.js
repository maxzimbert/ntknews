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
function exaPost(body) {
  return new Promise((resolve) => {
    const bodyStr = JSON.stringify(body);
    const options = {
      hostname: 'api.exa.ai',
      path: '/search',
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

  // ── Exa: breaking news scan ─────────────────────────────────────────────────
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
      articleBodyLen: 1500,
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
      articleBodyLen: 1500,
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
      articleBodyLen: 1500,
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
      articleBodyLen: 1500,
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
