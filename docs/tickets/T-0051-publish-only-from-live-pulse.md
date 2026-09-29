---
id: T-0051
title: Pulse's Publish button works from any page that holds the token, including a staging copy
status: BUILT
tags: [pulse, defect]
anchor: ntk-pulse/pulse.html:2140
---

## What

`publishToDigest()` PUTs `lineup-publish.json` to `main` of
`maxzimbert/ntknews` using the GitHub token in `localStorage`. Nothing checked
where the page was served from. `localStorage` is shared by every page under
`maxzimbert.github.io`, so any copy of Pulse hosted there, such as a staging
copy running unmerged code, holds the real token and could publish to
production. Verified in the code 2026-09-29 (`GH_REPO` is a constant, the only
gate was `SETTINGS.ghToken`).

Fixed: `pulseMayPublish(location)` allows only `maxzimbert.github.io/ntknews/`
and `ntknews.org`. Anywhere else the button reports "disabled on this copy"
and returns before any network call.

## Why

Prerequisite for a Pulse staging environment (docs/backlog.md, "A
staging/dev environment for Pulse"). The editor can also just avoid pressing
Publish, but a guard that depends on remembering is how a test run ships to
readers. Allow-list rather than deny-list on purpose: a host nobody thought
of must not be able to publish. `ntknews.org` stays allowed because it is the
dormant copy of the same code and this change should not alter it. Chose not
to retarget `GH_REPO` per host: staging does not need to publish, and a
second publish path is more surface to keep correct.

Status is BUILT, not VERIFIED: the check proves the predicate and that the
guard sits before the token check, not that a browser on a staging URL
actually shows the message. Promote after trying it on the staging copy.

## Check

```sh
set -e
grep -q "function pulseMayPublish" ntk-pulse/pulse.html

awk '/<script>/{f=1;next}/<\/script>/{f=0}f' ntk-pulse/pulse.html > "${TMPDIR:-/tmp}/t0051-pulse-script.js"
node --check "${TMPDIR:-/tmp}/t0051-pulse-script.js"
rm -f "${TMPDIR:-/tmp}/t0051-pulse-script.js"

node - <<'NODEEOF'
const fs = require('fs');
const src = fs.readFileSync('ntk-pulse/pulse.html', 'utf8');
const a = src.indexOf('function pulseMayPublish');
const b = src.indexOf('async function publishToDigest', a);
if (a < 0 || b < 0) throw new Error('guard or publishToDigest not found');
const fn = new Function(src.slice(a, b) + '\nreturn pulseMayPublish;')();

const cases = [
  [{hostname:'maxzimbert.github.io', pathname:'/ntknews/ntk-pulse/pulse.html'}, true],
  [{hostname:'ntknews.org', pathname:'/ntk-pulse/pulse.html'}, true],
  [{hostname:'maxzimbert.github.io', pathname:'/ntknews-staging/ntk-pulse/pulse.html'}, false],
  [{hostname:'maxzimbert.github.io', pathname:'/other/pulse.html'}, false],
  [{hostname:'rainbow-sherbet-b2f0e9.netlify.app', pathname:'/ntk-pulse/pulse.html'}, false],
  [{hostname:'localhost', pathname:'/ntk-pulse/pulse.html'}, false],
];
for (const [loc, want] of cases) {
  if (fn(loc) !== want) throw new Error(loc.hostname + loc.pathname + ' expected ' + want);
}

// The guard must come before the token check, so a blocked copy never reaches fetch().
const body = src.slice(b, b + 900);
if (body.indexOf('pulseMayPublish') < 0 || body.indexOf('pulseMayPublish') > body.indexOf('SETTINGS.ghToken'))
  throw new Error('guard must precede the token check in publishToDigest');
console.log('T-0051 check passed');
NODEEOF
```
