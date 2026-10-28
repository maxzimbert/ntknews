/* NTK share panel - framework-free, matches the digest's vanilla-JS style.
 *
 *   NTKShare.open(story)   // story = an entry of the digest's stories[]
 *
 * Expects the build to have published each story's cards next to its
 * permalink:  <permalink>share/{story.png, pin.png, slide-*.png, manifest.json}
 * (see SPEC.md section 6). Uses web intents for link platforms and the Web
 * Share API with files for image platforms (Instagram, and image posts anywhere).
 *
 * Nothing here posts on anyone's behalf: every path ends in the platform's own
 * composer or the phone's share sheet, where the reader confirms.
 *
 * This file is kept pure ASCII so it works whatever charset it is served with;
 * typographic characters in strings are written as \u escapes.
 */
(function () {
  'use strict';

  var SITE = 'https://ntknews.org';
  var UTM = { medium: 'social', campaign: 'reader_share' };
  var ELLIPSIS = '\u2026';

  // -- helpers ---------------------------------------------------------------
  function enc(s) { return encodeURIComponent(s || ''); }
  function withUtm(url, source) {
    var u = new URL(url, SITE);
    u.searchParams.set('utm_source', source);
    u.searchParams.set('utm_medium', UTM.medium);
    u.searchParams.set('utm_campaign', UTM.campaign);
    return u.toString();
  }
  function shareBase(story) { return new URL('share/', new URL(story.permalink, SITE)).toString(); }
  function clip(text, max) { return text.length <= max ? text : text.slice(0, max - 1).replace(/\s+\S*$/, '') + ELLIPSIS; }
  function track(evt, props) { try { if (typeof window.track === 'function') window.track(evt, props); } catch (e) {} }

  function copy(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text).catch(legacy);
    return Promise.resolve(legacy());
    function legacy() {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
    }
  }

  function fetchFiles(urls) {
    return Promise.all(urls.map(function (u) {
      return fetch(u).then(function (r) {
        if (!r.ok) throw new Error('missing ' + u);
        return r.blob();
      }).then(function (b) { return new File([b], u.split('/').pop(), { type: 'image/png' }); });
    }));
  }

  function canShareFiles(files) {
    return !!(navigator.canShare && navigator.share && navigator.canShare({ files: files }));
  }

  function download(files) {
    files.forEach(function (f, i) {
      setTimeout(function () {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(f); a.download = f.name;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
      }, i * 250);
    });
  }

  // -- link platforms (web intents) -------------------------------------------
  // Each returns the URL to open. The link preview comes from the story
  // page's og:image, so these platforms show the 1200x630 card automatically.
  var INTENTS = {
    x: function (s) {
      return 'https://x.com/intent/tweet?text=' + enc(clip(s.headline, 230)) + '&url=' + enc(withUtm(s.permalink, 'x'));
    },
    threads: function (s) {
      return 'https://www.threads.com/intent/post?text=' + enc(clip(s.headline, 400)) + '&url=' + enc(withUtm(s.permalink, 'threads'));
    },
    bluesky: function (s) {
      // Bluesky's intent takes text only; the first link becomes the card. 300-grapheme limit.
      var url = withUtm(s.permalink, 'bluesky');
      return 'https://bsky.app/intent/compose?text=' + enc(clip(s.headline, 300 - url.length - 2) + '\n\n' + url);
    },
    facebook: function (s) {
      return 'https://www.facebook.com/sharer/sharer.php?u=' + enc(withUtm(s.permalink, 'facebook'));
    },
    linkedin: function (s) {
      return 'https://www.linkedin.com/sharing/share-offsite/?url=' + enc(withUtm(s.permalink, 'linkedin'));
    },
    reddit: function (s) {
      return 'https://www.reddit.com/submit?url=' + enc(withUtm(s.permalink, 'reddit')) + '&title=' + enc(clip(s.headline, 300));
    },
    pinterest: function (s) {
      // The one link intent that also carries our image.
      return 'https://www.pinterest.com/pin/create/button/?url=' + enc(withUtm(s.permalink, 'pinterest')) +
        '&media=' + enc(shareBase(s) + 'pin.png') + '&description=' + enc(clip(s.headline, 480));
    },
    whatsapp: function (s) {
      return 'https://wa.me/?text=' + enc(s.headline + ' ' + withUtm(s.permalink, 'whatsapp'));
    },
    email: function (s) {
      return 'mailto:?subject=' + enc(s.headline) + '&body=' + enc((s.lede ? s.lede + '\n\n' : '') + withUtm(s.permalink, 'email'));
    }
  };

  function openIntent(platform, story) {
    track('story_share_platform', { platform: platform });
    var url = INTENTS[platform](story);
    if (platform === 'email') { window.location.href = url; return; }
    window.open(url, '_blank', 'noopener,noreferrer,width=640,height=720');
  }

  // -- image platforms (Web Share API with files) -----------------------------
  // Instagram Story: one 1080x1920 image. Instagram can't take a link from us,
  // so we copy the permalink first; the card itself carries the short address.
  function shareStoryImage(story, setStatus) {
    track('story_share_platform', { platform: 'instagram_story' });
    copy(withUtm(story.permalink, 'instagram'));
    return fetchFiles([shareBase(story) + 'story.png']).then(function (files) {
      if (canShareFiles(files)) {
        setStatus('Link copied. Pick Instagram, then Story. Paste the link in a link sticker if you like.');
        return navigator.share({ files: files });
      }
      download(files);
      setStatus('Image saved. Post it to your Story from the Instagram app.');
    }).catch(function () { setStatus('Couldn\u2019t prepare the image. Try again.'); });
  }

  // Slides: the whole carousel for Instagram feed, Threads, Facebook, LinkedIn,
  // WhatsApp. Whether a given app turns several files into one carousel varies
  // by app and OS (SPEC.md section 7); the fallback is saving them to Photos.
  function shareSlides(story, setStatus) {
    track('story_share_platform', { platform: 'slides' });
    copy(withUtm(story.permalink, 'slides'));
    return fetch(shareBase(story) + 'manifest.json').then(function (r) { return r.json(); }).then(function (m) {
      var urls = m.files.filter(function (f) { return f.slide; }).map(function (f) { return shareBase(story) + f.file; });
      return fetchFiles(urls);
    }).then(function (files) {
      if (canShareFiles(files)) {
        setStatus('Link copied. Choose an app to post the slides.');
        return navigator.share({ files: files, title: story.headline });
      }
      download(files);
      setStatus('Slides saved. Add them as one post in Instagram, Threads or LinkedIn.');
    }).catch(function () { setStatus('Couldn\u2019t prepare the slides. Try again.'); });
  }

  // -- panel ------------------------------------------------------------------
  var ROWS = [
    { id: 'instagram_story', label: 'Instagram Story', kind: 'image' },
    { id: 'slides', label: 'Slides', sub: 'Instagram, Threads, LinkedIn', kind: 'image' },
    { id: 'x', label: 'X' }, { id: 'threads', label: 'Threads' }, { id: 'bluesky', label: 'Bluesky' },
    { id: 'facebook', label: 'Facebook' }, { id: 'linkedin', label: 'LinkedIn' }, { id: 'reddit', label: 'Reddit' },
    { id: 'pinterest', label: 'Pinterest' }, { id: 'whatsapp', label: 'WhatsApp' }, { id: 'email', label: 'Email' },
    { id: 'copy', label: 'Copy link' }
  ];

  var lastFocus = null;

  function open(story) {
    close();
    lastFocus = document.activeElement;
    var root = document.createElement('div');
    root.className = 'ntk-share';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', 'Share this story');
    root.innerHTML =
      '<div class="ntk-share__scrim" data-close></div>' +
      '<div class="ntk-share__sheet">' +
        '<div class="ntk-share__head"><div class="ntk-share__kicker">Share</div>' +
        '<button class="ntk-share__x" type="button" data-close aria-label="Close">\u00d7</button></div>' +
        '<div class="ntk-share__hl"></div>' +
        '<div class="ntk-share__grid"></div>' +
        '<p class="ntk-share__status" aria-live="polite"></p>' +
      '</div>';
    root.querySelector('.ntk-share__hl').textContent = story.headline;
    var grid = root.querySelector('.ntk-share__grid');
    var status = root.querySelector('.ntk-share__status');
    var setStatus = function (t) { status.textContent = t; };

    ROWS.forEach(function (row) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'ntk-share__btn' + (row.kind === 'image' ? ' ntk-share__btn--image' : '');
      b.innerHTML = '<span class="ntk-share__lbl"></span>' + (row.sub ? '<span class="ntk-share__sub"></span>' : '');
      b.querySelector('.ntk-share__lbl').textContent = row.label;
      if (row.sub) b.querySelector('.ntk-share__sub').textContent = row.sub;
      b.addEventListener('click', function () {
        if (row.id === 'instagram_story') return shareStoryImage(story, setStatus);
        if (row.id === 'slides') return shareSlides(story, setStatus);
        if (row.id === 'copy') {
          track('story_share_platform', { platform: 'copy' });
          copy(withUtm(story.permalink, 'copy'));
          return setStatus('Link copied.');
        }
        openIntent(row.id, story);
      });
      grid.appendChild(b);
    });

    root.addEventListener('click', function (e) { if (e.target.hasAttribute('data-close')) close(); });
    document.addEventListener('keydown', onKey);
    document.body.appendChild(root);
    grid.querySelector('button').focus();
  }

  function onKey(e) { if (e.key === 'Escape') close(); }
  function close() {
    var el = document.querySelector('.ntk-share');
    if (el) el.remove();
    document.removeEventListener('keydown', onKey);
    if (lastFocus && typeof lastFocus.focus === 'function') { lastFocus.focus(); lastFocus = null; }
  }

  window.NTKShare = { open: open, close: close, intents: INTENTS, withUtm: withUtm };
})();
