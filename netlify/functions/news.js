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

function post(body) {
  return new Promise((resolve) => {
    const bodyStr = JSON.stringify(body);
    const options = {
      hostname: 'eventregistry.org',
      path: '/api/v1/article/getArticles',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
  const mode = q.mode || 'fetch'; // 'scan-ntk' | 'scan-broad' | 'fetch'

  let body;

  if (mode === 'scan-ntk') {
    body = {
      apiKey: process.env.NEWSAPI_KEY,
      action: 'getArticles',
      lang: 'eng',
      articlesCount: 40,
      articlesSortBy: 'date',
      articlesSortByAsc: false,
      resultType: 'articles',
      includeArticleBody: false,
      includeArticleTitle: true,
      includeArticleDate: true,
      includeSourceInfo: true,
      skipDuplicates: true,
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
      includeArticleBody: false,
      includeArticleTitle: true,
      includeSourceInfo: true,
      skipDuplicates: true,
      startSourceRankPercentile: 0,
      endSourceRankPercentile: 15
    };
  } else {
    // Default: fetch full article content for generation
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
      includeSourceInfo: true,
      skipDuplicates: true,
      sourceUri: NTK_SOURCES
    };
  }

  const result = await post(body);

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*'
    },
    body: result.body
  };
};
