/* ─────────────────────────────────────────────────────────────
   NTK Backstory — render module
   Replaces the bsr* block in index.html.

   Wiring:
     1. Delete the existing .bsr-* CSS and the bsrFetch/bsrRender/
        bsrFormatDuration/bsrOpenDetail functions from index.html.
     2. <script src="/digest/v2/js/backstory.js"></script>
     3. In switchTab():  if (tab === 'backstory') NTKBackstory.mount('bsrList');

   Reads /digest/v2/data/backstory.json. Clocks compute at render.
   ───────────────────────────────────────────────────────────── */
(function (global) {
  'use strict';

  var DATA = null;

  /* ── clocks ──────────────────────────────────────────────── */

  function daysSince(iso) {
    var d = new Date(iso + 'T00:00:00');
    return Math.floor((Date.now() - d.getTime()) / 86400000);
  }

  // Collapses to whole years above ten so 19,326 days reads as "52 years".
  function formatDuration(days) {
    if (days < 60) return days + (days === 1 ? ' day' : ' days');
    var years = Math.floor(days / 365.25);
    var months = Math.floor((days - years * 365.25) / 30.44);
    if (years >= 10) return years + ' years';
    if (years >= 1) return years + (years === 1 ? ' yr, ' : ' yrs, ') + months + ' mo';
    return months + (months === 1 ? ' month' : ' months');
  }

  function startYear(iso) { return iso.slice(0, 4); }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ── selection ───────────────────────────────────────────── */
  // One entry per digest story. DATA.todays_pairings is the rendered set;
  // DATA.rows is the library each entry draws its clock and case from.

  function rowById(id) {
    return DATA.rows.filter(function (r) { return r.id === id; })[0] || null;
  }

  function entries() {
    return (DATA.todays_pairings || [])
      .map(function (p) {
        var r = rowById(p.row);
        return r ? { pair: p, row: r } : null;
      })
      .filter(Boolean)
      .sort(function (a, b) {
        return daysSince(a.row.start_date) - daysSince(b.row.start_date);
      });
  }

  /* ── 1C: the list ────────────────────────────────────────── */

  function entryHTML(e) {
    var r = e.row, p = e.pair,
        days = daysSince(r.start_date),
        fire = r.stratum === 'fire',
        big  = fire ? days.toLocaleString() : startYear(r.start_date),
        lab  = fire ? (days < 60 ? 'Day' : 'Day · and counting') : 'Since',
        sml  = formatDuration(days) + (fire ? ' · running' : ' held'),
        size = fire ? Math.max(28, 42 - String(big).length * 2) : 32;

    return '<button class="bsr-row ' + (fire ? 'is-fire' : 'is-held') + '"' +
             ' data-id="' + esc(r.id) + '" data-story="' + esc(p.story_id || '') + '">' +
        '<span class="bsr-clock">' +
          '<span class="bsr-lab">' + lab + '</span>' +
          '<span class="bsr-big" style="font-size:' + size + 'px">' + big + '</span>' +
          '<span class="bsr-sml">' + sml + '</span>' +
        '</span>' +
        '<span class="bsr-body">' +
          '<span class="bsr-head"><span class="bsr-title">' + esc(r.title) + '</span></span>' +
          (r.milestone ? '<span class="bsr-contest">' + esc(r.milestone) + '</span>' : '') +
          (p.line ? '<span class="bsr-pair">' + esc(p.line) + '</span>' : '') +
        '</span>' +
      '</button>';
  }

  function renderList(mountId) {
    var el = document.getElementById(mountId);
    if (!el) return;
    if (!DATA) { el.innerHTML = '<div class="bsr-empty">Loading…</div>'; return; }

    var list = entries();
    if (!list.length) {
      el.innerHTML = '<div class="bsr-empty">Nothing paired yet today.</div>';
      return;
    }

    var html = '<div class="bsr-why"><div class="bsr-kick bsr-amber">Behind today</div>' +
      '<p>Every story in today\'s digest is an episode of something older. ' +
      'Shortest running first.</p></div>';

    list.forEach(function (e) { html += entryHTML(e); });
    el.innerHTML = html;

    el.querySelectorAll('.bsr-row').forEach(function (b) {
      b.onclick = function () { openDetail(b.dataset.id, mountId, b.dataset.story); };
    });
  }

  /* ── 1D: the detail view ─────────────────────────────────── */

  function openDetail(id, mountId, storyId) {
    var r = DATA.rows.filter(function (x) { return x.id === id; })[0];
    if (!r) return;
    var days = daysSince(r.start_date),
        fire = r.stratum === 'fire',
        ind  = r.indicator,
        pair = (DATA.todays_pairings || []).filter(function (p) {
                 return p.row === id && (!storyId || p.story_id === storyId);
               })[0] || null,
        html = '';

    html += '<div class="bsd-bar"><button class="bsd-back">&larr; Backstory</button>' +
      '<span>' + esc(r.title) + ' · ' + formatDuration(days) + '</span></div>';

    html += '<div class="bsd-hero">' +
      '<div class="bsr-kick">' + (fire ? 'Still counting' : 'Lifetime · being held') + '</div>' +
      '<div class="bsd-n">' + formatDuration(days) + '</div>' +
      '<div class="bsd-d">' + days.toLocaleString() + ' days' +
        (r.start_line ? ' · ' + esc(r.start_line) : '') + '</div>' +
      '<h2>' + esc(r.title) + '</h2>' +
      (r.milestone ? '<div class="bsd-c">' + esc(r.milestone) + '</div>' : '') +
      (pair ? '<div class="bsd-pair">' + esc(pair.line) + '</div>' : '') +
      '</div>';

    var paras = r.narrative || [], mid = Math.ceil(paras.length / 2);
    if (!paras.length) {
      html += '<div class="bsd-body"><p class="bsd-todo">Narrative not yet written. ' +
        'Generate with Register 4.</p></div>';
    } else {
      html += '<div class="bsd-body">' +
        paras.slice(0, mid).map(function (p) { return '<p>' + esc(p) + '</p>'; }).join('') +
        '</div>';
    }

    if (ind) {
      html += '<div class="bsd-meas"><div class="bsr-kick">One measure</div>' +
        '<div class="bsd-nm">' + esc(ind.label) + '</div><div class="bsd-grid">' +
        '<div><div class="bsd-v">' + esc(ind.then_value) + '</div>' +
          '<div class="bsd-yr">' + esc(ind.then_year) + '</div></div>' +
        '<div class="bsd-arrow">&rarr;</div>' +
        '<div><div class="bsd-v is-' + esc(ind.direction) + '">' + esc(ind.now_value) + '</div>' +
          '<div class="bsd-yr">Today</div></div>' +
        '<div class="bsd-dir"><div class="bsd-dirv is-' + esc(ind.direction) + '">' +
          esc(ind.direction) + '</div><div class="bsd-stamp">Most recent available data' +
          (ind.as_of ? ', ' + esc(ind.as_of) : '') + '</div></div>' +
        '</div></div>';
    }

    if (paras.length) {
      html += '<div class="bsd-body">' +
        paras.slice(mid).map(function (p) { return '<p>' + esc(p) + '</p>'; }).join('') +
        '</div>';
    }

    if ((r.objects || []).length) {
      html += '<div class="bsd-case"><div class="bsd-hd"><span class="bsr-kick">The case</span>' +
        '<span class="bsd-ct">' + r.objects.length + ' objects</span></div>' +
        r.objects.map(function (o) {
          return '<div class="bsd-obj"><p>' + esc(o.title) + '</p>' +
            '<div class="bsd-by">' + esc(o.author) +
            (o.year ? ' · ' + esc(o.year) : '') + '</div></div>';
        }).join('') + '</div>';
    }

    if ((r.instances || []).length) {
      html += '<div class="bsd-eps"><div class="bsd-hd">' +
        '<span class="bsr-kick bsr-amber">Episodes in the digest</span>' +
        '<span class="bsd-ct">Newest first</span></div>' +
        r.instances.map(function (s) {
          return '<a class="bsd-ep" href="' + esc(s.url || '#') + '">' +
            '<div class="bsd-dt">' + esc(s.date) + '</div>' +
            '<p>' + esc(s.headline) + '</p></a>';
        }).join('') + '</div>';
    }

    html += '<div class="bsd-foot"><button class="bsd-back">&larr; Back</button></div>';

    var el = document.getElementById(mountId);
    el.innerHTML = html;
    el.scrollTop = 0;
    el.querySelectorAll('.bsd-back').forEach(function (b) {
      b.onclick = function () { renderList(mountId); };
    });
  }

  /* ── styles ──────────────────────────────────────────────── */

  var CSS = `
.bsr-kick{font:600 9px/1 'Space Grotesk',sans-serif;letter-spacing:.2em;text-transform:uppercase;
  color:rgba(38,31,35,.55)}
.bsr-amber{color:var(--amber)}
.bsr-why{padding:18px 20px 16px;border-bottom:1px solid rgba(38,31,35,.2);background:var(--white)}
.bsr-why p{font-family:'Source Serif 4',serif;font-size:15px;line-height:1.45;margin-top:8px}
.bsr-row{display:grid;grid-template-columns:94px 1fr;gap:14px;width:100%;text-align:left;
  padding:17px 20px;border:0;border-bottom:1px solid rgba(38,31,35,.16);background:none;cursor:pointer}
.bsr-row.is-fire{background:var(--white)}
.bsr-clock{display:block}
.bsr-lab{display:block;font:600 9px/1 'Space Grotesk',sans-serif;letter-spacing:.18em;
  text-transform:uppercase;margin-bottom:4px}
.bsr-row.is-fire .bsr-lab{color:var(--teal)}
.bsr-row.is-held .bsr-lab{color:rgba(38,31,35,.6)}
.bsr-big{display:block;font-family:'Space Grotesk',sans-serif;letter-spacing:-.035em;line-height:.9}
.bsr-row.is-fire .bsr-big{font-weight:700}
.bsr-row.is-held .bsr-big{font-weight:400}
.bsr-sml{display:block;font:500 10px/1.3 'Space Grotesk',sans-serif;letter-spacing:.1em;
  text-transform:uppercase;color:rgba(38,31,35,.65);margin-top:8px}
.bsr-body{min-width:0;border-left:1px solid rgba(38,31,35,.2);padding-left:14px}
.bsr-head{display:flex;align-items:baseline;gap:8px}
.bsr-title{font:600 13px/1.2 'Space Grotesk',sans-serif;letter-spacing:.05em;text-transform:uppercase}
.bsr-contest{display:block;font-family:'Source Serif 4',serif;font-style:italic;font-size:15px;
  line-height:1.42;margin-top:6px;color:rgba(38,31,35,.78)}
.bsr-pair{display:block;font-family:'Source Serif 4',serif;font-size:13px;line-height:1.42;
  margin-top:9px;padding-left:9px;border-left:2px solid var(--amber);color:rgba(38,31,35,.68)}
.bsr-empty{padding:40px 20px;text-align:center;font-family:'Source Serif 4',serif;opacity:.5}

.bsd-bar{position:sticky;top:0;z-index:5;background:var(--cream);border-bottom:1px solid var(--dark);
  padding:12px 20px;display:flex;align-items:center;gap:12px}
.bsd-bar button{border:0;background:none;cursor:pointer;font:600 10px/1 'Space Grotesk',sans-serif;
  letter-spacing:.14em;text-transform:uppercase}
.bsd-bar span{margin-left:auto;font:500 10px/1 'Space Grotesk',sans-serif;letter-spacing:.14em;
  text-transform:uppercase;color:rgba(38,31,35,.55)}
.bsd-hero{padding:28px 20px 24px;border-bottom:1px solid var(--dark)}
.bsd-n{font:400 54px/.86 'Space Grotesk',sans-serif;letter-spacing:-.045em;margin-top:16px}
.bsd-d{font:500 10px/1.4 'Space Grotesk',sans-serif;letter-spacing:.12em;text-transform:uppercase;
  color:rgba(38,31,35,.62);margin-top:12px}
.bsd-hero h2{font:600 15px/1.2 'Space Grotesk',sans-serif;letter-spacing:.08em;
  text-transform:uppercase;margin-top:22px}
.bsd-c{font-family:'Source Serif 4',serif;font-style:italic;font-size:19px;line-height:1.35;
  margin-top:8px;color:rgba(38,31,35,.82)}
.bsd-pair{font-family:'Source Serif 4',serif;font-size:14px;line-height:1.4;margin-top:14px;
  padding-left:10px;border-left:2px solid var(--amber);color:rgba(38,31,35,.7)}
.bsd-body{padding:26px 20px 8px}
.bsd-body p{font-family:'Source Serif 4',serif;font-size:17px;line-height:1.62;margin-bottom:18px}
.bsd-todo{opacity:.5;font-style:italic}
.bsd-meas{margin:14px 20px 22px;border-top:1px solid var(--dark);border-bottom:1px solid var(--dark);
  padding:16px 0 18px}
.bsd-nm{font:600 12px/1.2 'Space Grotesk',sans-serif;letter-spacing:.06em;text-transform:uppercase;
  margin:14px 0 12px}
.bsd-grid{display:flex;align-items:flex-end;gap:14px}
.bsd-v{font:700 32px/1 'Space Grotesk',sans-serif;letter-spacing:-.03em}
.bsd-v.is-worse{color:var(--terra)}
.bsd-v.is-better{color:var(--teal)}
.bsd-yr{font:500 10px/1 'Space Grotesk',sans-serif;letter-spacing:.12em;text-transform:uppercase;
  color:rgba(38,31,35,.62);margin-top:6px}
.bsd-arrow{font-size:20px;color:rgba(38,31,35,.4);padding-bottom:14px}
.bsd-dir{margin-left:auto;text-align:right;padding-bottom:2px}
.bsd-dirv{font:600 10px/1 'Space Grotesk',sans-serif;letter-spacing:.16em;text-transform:uppercase}
.bsd-dirv.is-worse{color:var(--terra)}
.bsd-dirv.is-better{color:var(--teal)}
.bsd-dirv.is-flat,.bsd-dirv.is-contested{color:rgba(38,31,35,.6)}
.bsd-stamp{font:500 9px/1.3 'Space Grotesk',sans-serif;letter-spacing:.1em;text-transform:uppercase;
  color:rgba(38,31,35,.58);margin-top:5px}
.bsd-case{border-top:1px solid var(--dark);padding:24px 20px 8px}
.bsd-hd{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}
.bsd-ct{margin-left:auto;font:500 9px/1 'Space Grotesk',sans-serif;letter-spacing:.14em;
  text-transform:uppercase;color:rgba(38,31,35,.58)}
.bsd-obj{border-top:1px solid rgba(38,31,35,.2);padding:15px 0 14px}
.bsd-obj p{font-family:'Source Serif 4',serif;font-style:italic;font-size:17px;line-height:1.35}
.bsd-by{font:500 10px/1.3 'Space Grotesk',sans-serif;letter-spacing:.12em;text-transform:uppercase;
  color:rgba(38,31,35,.62);margin-top:8px}
.bsd-eps{background:var(--dark);color:var(--cream);margin-top:26px;padding:24px 20px 26px}
.bsd-eps .bsd-ct{color:rgba(234,217,197,.45)}
.bsd-ep{display:block;border-top:1px solid rgba(234,217,197,.28);padding:14px 0 13px;
  color:var(--cream);text-decoration:none}
.bsd-dt{font:500 9px/1 'Space Grotesk',sans-serif;letter-spacing:.14em;text-transform:uppercase;
  color:rgba(234,217,197,.5)}
.bsd-ep p{font-family:'Source Serif 4',serif;font-size:17px;line-height:1.32;margin-top:6px}
.bsd-foot{padding:22px 20px 40px;display:flex;flex-direction:column;gap:12px}
.bsd-foot button{border:0;background:none;cursor:pointer;text-align:left;
  font:600 11px/1 'Space Grotesk',sans-serif;letter-spacing:.14em;text-transform:uppercase}
.bsd-foot span{font:500 9px/1 'Space Grotesk',sans-serif;letter-spacing:.14em;
  text-transform:uppercase;color:rgba(38,31,35,.58)}
`;

  /* ── mount ───────────────────────────────────────────────── */

  function mount(mountId) {
    if (!document.getElementById('bsr-styles')) {
      var s = document.createElement('style');
      s.id = 'bsr-styles'; s.textContent = CSS;
      document.head.appendChild(s);
    }
    if (DATA) { renderList(mountId); return; }
    renderList(mountId);
    fetch('/digest/v2/data/backstory.json?t=' + Date.now())
      .then(function (r) { return r.json(); })
      .then(function (d) { DATA = d; renderList(mountId); })
      .catch(function () {
        var el = document.getElementById(mountId);
        if (el) el.innerHTML = '<div class="bsr-empty">Couldn\'t load Backstory.</div>';
      });
  }

  global.NTKBackstory = { mount: mount, formatDuration: formatDuration, daysSince: daysSince };
})(window);
