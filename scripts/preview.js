// Local static preview of the site, so changes can be checked before they ship.
// No dependencies. Root is resolved from this file's own location rather than
// the working directory — the launcher's cwd is not always readable.
//
//   node scripts/preview.js [port]      -> http://localhost:8777/digest/
//
// Note: /today, /backstory and /me are Netlify redirect rules and do NOT exist
// here. Locally the app is served at /digest/.

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PORT = Number(process.env.PORT || process.argv[2] || 8777);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
};

http
  .createServer((req, res) => {
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    } catch {
      res.writeHead(400).end('Bad request');
      return;
    }

    let filePath = path.join(ROOT, pathname);
    // Contain every request inside ROOT, whatever the URL claims.
    if (filePath !== ROOT && !filePath.startsWith(ROOT + path.sep)) {
      res.writeHead(403).end('Forbidden');
      return;
    }

    fs.stat(filePath, (err, stat) => {
      if (!err && stat.isDirectory()) filePath = path.join(filePath, 'index.html');
      fs.readFile(filePath, (readErr, body) => {
        if (readErr) {
          res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
          res.end(`404 — ${pathname}\n\nThe app is at /digest/ locally.\n/today is a Netlify redirect and does not exist here.`);
          return;
        }
        res.writeHead(200, {
          'Content-Type': TYPES[path.extname(filePath).toLowerCase()] || 'application/octet-stream',
          'Cache-Control': 'no-store',
        });
        res.end(body);
      });
    });
  })
  .listen(PORT, () => {
    console.log(`NTK preview: http://localhost:${PORT}/digest/`);
    console.log(`serving ${ROOT}`);
  });
