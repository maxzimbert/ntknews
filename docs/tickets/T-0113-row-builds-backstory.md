---
id: T-0113
title: The editor types each story's row in Pulse, and filing it builds the story's Backstory there, scoped from the story's headline, description and Truths
status: BUILT
tags: [pulse, feature]
anchor: ntk-pulse/pulse.html
---

## What

Asked for by the editor 2026-10-30: "every story should have a row. I am saying replace row: not set
(classifier picks) with a row I write such as "crypto" or "crime". so there's still a backstory template that
gets made to fit that news category." And, to be exact about scope: "Backstory is scoped from the digest
story's headline, description, and truths. Beginnings and object gathering starts from there and can include
more objects and milestones to make and defend the ntk chronology." And: "dont lose the charts or the rows
that are already made and stood up (gaza, ukraine-russia, others)."

Measured on `main` 2026-10-30 before this: the Backstory tab's row was a dropdown whose default was "row: not
set (classifier picks)"; a story's page could only be composed after GitHub's first draft (classifier, pairing
line, origin), so an unfiled story waited on the classifier and a filed one on a workflow run.

Built 2026-10-30:
- **A typed row.** Each story on the Backstory tab has a text box with suggestions (every fixed row and
  category). A name matching an existing row, ignoring case and punctuation ("ukraine russia" finds
  Ukraine–Russia), files the story there, as it stands: its documents, its trend line, a live conflict's day
  counter. A new name starts a category of that name (`newCategory`), kept in the category store
  (`provisional-rows.json`, via the draft) so it is suggested again and is not archived while stories use it.
- **Filing builds.** Pressing Enter composes the story's page in the browser (`bsxRun` with `build`), with no
  classifier and no GitHub run: `bsxEnsureEntries` gives the draft an entry for the story under that row (and
  starts a draft from the published rows and the category store if none exists), the composer writes "We are
  here" when there is no pairing line, and "It starts in" comes from the page's own Beginnings. "Build Backstory
  for every story" builds all stories with a row; the GitHub draft stays as "Draft with the classifier".
- **Scope.** The compose prompt now says the scope comes from the headline, the description and the Truths,
  that the category is a library to draw on and not the scope, and that Beginnings start from what the story
  establishes and reach further back to make and defend the chronology.
- **Charts and rows kept.** A story under a fixed row keeps that row's trend line; a story under a live
  conflict (Gaza, Ukraine–Russia, which have no trend line) keeps its day counter on its own page
  (`fire_since`, in the app and the static page). The static page builder no longer crashes on a row with no
  `milestone`, which a new category has.

Tested: in a local Pulse with stand-in model and GitHub replies, starting with no draft, five stories typed as
gaza, Crypto, order, Work and "ukraine russia" resolved to the right rows (Crypto new), all five were built,
the draft kept the eight existing categories plus Crypto, and Crypto went into the store; the reader app in
draft view showed five story pages, Gaza's with its counter since 2023-10-07; `backstory_draft.py apply` shipped
the draft; `build_backstory_pages.py` wrote Gaza's story page with the counter and Order's with its chart.
Not run against the live model.

**Lineup tab, 2026-10-30** (the editor: "the row box should mimic what's on backstory"): the Lineup tab's row
dropdown and "+ new category" prompt are replaced by the same typed box, with the same suggestions
(`bsrEnsureRowList`, one list for both tabs) and the same filing (`bsrFileRow`), so filing a story on either tab
builds its Backstory; "Backstory →" opens the story's preview.

## Why

The classifier chose rows the editor would not have (Israel's election under Power, the Ohio ad under The
Media), and the editor knows the right shelf for a story the moment they read it. A typed row makes that
the editor's call and removes a workflow run and a model call from every story. Scope still comes from the
news itself, so a broad row does not make a broad page: the row is a library and a grouping, and since
2026-10-30 readers see no category page.

Ruled out: no row at all, building from the story alone. The editor wants every story filed, so stories
group, a row's trend line or counter reaches its stories, and categories accumulate a library.

Publish ships the Backstory only when every story in the Lineup is built and unchanged since; one unbuilt story
sends publish back to choosing for all of them, and the publish dialog warns first.

## Check

```sh
node - <<'JS'
const s = require('fs').readFileSync('ntk-pulse/pulse.html', 'utf8');
const app = require('fs').readFileSync('digest/index.html', 'utf8');
const bad = [];
const lu = s.slice(s.indexOf('function bsrLineupHtml'), s.indexOf('\n}\n', s.indexOf('function bsrLineupHtml')));
if (!/class="bsr-lu-row"/.test(lu) || /bsr-lu-tag/.test(lu)) bad.push('the Backstory tab still picks a row from a list with "classifier picks"');
const tag = s.slice(s.indexOf('function bsrTagControl'), s.indexOf('\n}\n', s.indexOf('function bsrTagControl')));
if (!/<input class="bsr-tag" list="bsr-row-names"/.test(tag) || /<select/.test(tag)) bad.push('the Lineup tab does not type the row the way the Backstory tab does');
if (!/bsrSel\.addEventListener\('change',e=>bsrFileRow\(s, e\.target\.value\)\)/.test(s)) bad.push('filing a row on the Lineup tab does not build the story');
if (!/Decide the SCOPE from the story itself: its headline, its description \(SUMMARY\) and what is true/.test(s)) bad.push('the compose prompt does not scope from headline, description and Truths');
if (!/async function bsxEnsureEntries\(/.test(s) || !/bsxRun\(\[s\.key\], \{build:true\}\)/.test(s)) bad.push('filing a row does not build the story in Pulse');
const at = s.indexOf('function bsrRowResolve(');
if (at < 0) bad.push('there is no typed-row resolver');
else {
  const names = [{id:'ukraine-russia', title:'Ukraine–Russia'}, {id:'gaza', title:'Gaza'}];
  const resolve = new Function('bsrRowNames', 'newCategory', s.slice(at, s.indexOf('\n}\n', at) + 2) + '; return bsrRowResolve;')(() => names, n => 'NEW:' + n);
  if (resolve('ukraine russia') !== 'ukraine-russia' || resolve('GAZA') !== 'gaza' || resolve('Crypto') !== 'NEW:Crypto') bad.push('a typed row does not resolve to the existing row, or a new name does not start a category');
}
if (!/stratum: row\.stratum === 'fire' \? 'fire' : 'story', fire_since/.test(app)) bad.push("a live conflict's day counter is lost on its stories' pages");
if (bad.length) { console.error(bad.join('\n')); process.exit(1); }
JS
```
