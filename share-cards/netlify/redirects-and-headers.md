# Netlify: short addresses and caching

## Short addresses

`build_card_data.py` writes `_redirects.share`, one line per story:

```
/white-house-ballroom  /digest/2026-10-15/six-tech-companies-put-92-million-into-trumps-ballroom-nvidi/  302
```

Have the publish step append these lines to the site's `_redirects` file, or
turn them into `[[redirects]]` blocks in `netlify.toml`, **above** any
catch-all rules. Use 302, not 301: a slug like `/ballroom` gets reused by a
later story, and browsers cache 301s indefinitely.

Before adding a slug, check that it doesn't shadow a real path (`/today`,
`/digest`, `/backstory`, any landing-page anchor route). Keep a reserved-words
list in the build step.

## Caching for share images

Platforms cache link previews hard. Serve share images with a long cache and
change the **URL** when the image changes, rather than overwriting in place:

```toml
[[headers]]
  for = "/digest/*/share/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
    Access-Control-Allow-Origin = "*"
```

`Access-Control-Allow-Origin` lets `share.js` fetch the PNGs as files for the
Web Share API from any NTK subdomain.

If a card is re-rendered after publication (a corrected headline), write it
as `og.v2.jpg` and update the meta tag, then refresh caches with Facebook's
Sharing Debugger and LinkedIn's Post Inspector. X and Bluesky refetch on
their own schedule.
