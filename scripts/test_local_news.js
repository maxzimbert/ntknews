#!/usr/bin/env node
// Local news on /today (T-0121): the pure logic in netlify/functions/news.js, run against what
// EventRegistry actually returned on 2026-11-10 for Los Angeles, Boise and Pittsburgh.
//   node scripts/test_local_news.js
const path = require('path');
const { pickLocation, pickLocal, localQuery, guessLocation } = require(path.resolve(__dirname, '../netlify/functions/news.js'));
let fails = 0;
const check = (name, ok, detail) => { console.log((ok ? 'ok   ' : 'FAIL ') + name + (ok ? '' : '  ' + JSON.stringify(detail))); if (!ok) fails++; };
const place = (label, uri) => ({ type: 'place', label: { eng: label }, wikiUri: 'http://en.wikipedia.org/wiki/' + uri });
const NOW = '2026-11-10T23:59:00Z';
const art = (date, host, title, p) => ({ date, url: 'https://' + host + (p || '/news/') + encodeURIComponent(title.slice(0, 30)), title, source: { title: host } });

// The suggestions as returned, in order.
const LA = [place('Los Angeles County, California', 'Los_Angeles_County,_California'), place('Los Angeles', 'Los_Angeles'),
  place('East Los Angeles, California', 'East_Los_Angeles,_California'), place('Los Ángeles, Chile', 'Los_Ángeles,_Chile'), place('Boyle Heights, Los Angeles', 'Boyle_Heights,_Los_Angeles')];
const BOISE = [place('Boise, Idaho', 'Boise,_Idaho'), place('Boise County, Idaho', 'Boise_County,_Idaho'), place('Boise City, Oklahoma', 'Boise_City,_Oklahoma')];
const PITT = [place('Pittsburgh, North Dakota', 'Pittsburgh,_North_Dakota'), place('Pittsburgh', 'Pittsburgh'), place('East Pittsburgh, Pennsylvania', 'East_Pittsburgh,_Pennsylvania')];
let r = pickLocation(LA, 'Los Angeles', 'California');
check('place: Los Angeles is the city, not the county listed first', r && r.uri.endsWith('/Los_Angeles'), r);
r = pickLocation(BOISE, 'Boise', 'Idaho');
check('place: a city labelled with its state matches on the state', r && r.uri.endsWith('/Boise,_Idaho'), r);
r = pickLocation(PITT, 'Pittsburgh', 'Pennsylvania');
check('place: a namesake in another state is not chosen', r && r.uri.endsWith('/Pittsburgh'), r);
r = pickLocation([place('Los Angeles County, California', 'x'), place('East Los Angeles, California', 'y')], 'Los Angeles', 'California');
check('place: with only a county and a neighbourhood on offer, there is no place', r === null, r);

const TULSA = [place('Tulsa County, Oklahoma', 'Tulsa_County,_Oklahoma'), place('New Tulsa, Oklahoma', 'New_Tulsa,_Oklahoma'), place('West Tulsa, Tulsa', 'West_Tulsa,_Tulsa')];
r = pickLocation(TULSA, 'Tulsa', 'Oklahoma') || guessLocation('Tulsa', 'Oklahoma');
check('place: a city the suggester leaves out is tried by its own address', r && r.uri === 'http://en.wikipedia.org/wiki/Tulsa,_Oklahoma', r);
check('place: with no state there is no guess', guessLocation('Tulsa', '') === null);

// What production showed for Los Angeles on 2026-11-10.
const JUNK = ['2026-10-31', '2026-10-28', '2026-10-27', '2026-10-23', '2026-10-20'].map((d, i) =>
  art(d, 'clasificados.laopinion.com', 'LOS ANGELES COUNTY METROPOLITAN TRAN', '/ad/' + i + '/'))
  .concat([art('2026-10-21', 'legalinsurrection.com', 'Los Angeles County Officials Offer Conflicting Accounts of Voter Citizenship Checks')]);
check('stale: classifieds and three-week-old items produce no block at all', pickLocal(JUNK, { city: 'Los Angeles', state: 'California', now: NOW }).length === 0);
const FRESH_ADS = [0, 1, 2].map(i => art('2026-11-10', 'clasificados.laopinion.com', 'Se vende camioneta ' + i, '/ad/' + i + '/'));
check('classifieds: an ad on a classifieds subdomain is dropped even when it is from today', pickLocal(FRESH_ADS, { city: 'Los Angeles', state: 'California', now: NOW }).length === 0);
check('classifieds: an ad under a classifieds path is dropped', pickLocal([0, 1, 2].map(i => art('2026-11-10', 'laopinion.com', 'Se renta cuarto ' + i, '/clasificados/' + i + '/')), { city: 'Los Angeles', now: NOW }).length === 0);

// What the new query returned for Los Angeles on 2026-11-10, newest first.
const GOOD = [
  art('2026-11-10', 'laist.com', "In LA's Little Bangladesh, Raman's visits won votes. Now residents have a to-do list for her"),
  art('2026-11-10', 'mynewsla.com', 'Judge Officially Closes Ballot Segregation Lawsuit'),
  art('2026-11-10', 'mynewsla.com', 'Police Seek Help Locating Hit-and-Run Suspect in Sherman Oaks'),
  art('2026-11-10', 'latimes.com', 'Fighting City Hall will get a lot more expensive under plan backed by L.A. Council'),
  art('2026-11-10', 'theblast.com', "Meghan Markle's Father Back In Custody After Allegedly Cutting Off Ankle Monitor"),
  art('2026-11-10', 'ktla.com', 'Uber driver pleads guilty to kidnapping passenger who fell asleep, sexually assaulting her'),
  art('2026-11-10', 'mynewsla.com', 'LA Gang Member Charged in Ryan Wedding Drug Trafficking Case'),
  art('2026-11-10', 'mynewsla.com', 'LA Board of Police Commissioners Previews LAPD Spending Request for FY 2027-28'),
  art('2026-11-10', 'mynewsla.com', 'LAPD Offers Free Instruction on Proper Child Car Seat Use'),
  art('2026-11-10', 'tmz.com', 'Thomas Markle Cut Off Ankle Monitor, Department of Justice Says'),
  art('2014-06-11', 'latimes.com', 'Hot Property: Donald Sterling asks $15,500 a month for Beverly Hills rental'),
];
let out = pickLocal(GOOD, { city: 'Los Angeles', state: 'California', now: NOW });
check('pick: at most three headlines', out.length === 3, out);
check('pick: headlines that name the place come first, one outlet each', out.map(a => a.source).join() === 'laist.com,latimes.com,mynewsla.com', out.map(a => a.source + ': ' + a.title));
check('pick: an article misdated to 2014 is never shown', !out.some(a => /Sterling/.test(a.title)));
out = pickLocal(GOOD.filter(a => /mynewsla/.test(a.url)), { city: 'Los Angeles', state: 'California', now: NOW });
check('pick: no more than two from one outlet', out.length === 2, out);
out = pickLocal([GOOD[0], Object.assign({}, GOOD[0], { url: GOOD[0].url + '?dup' }), GOOD[3], GOOD[5]], { city: 'Los Angeles', now: NOW });
check('pick: a repeated headline counts once', out.filter(a => /Little Bangladesh/.test(a.title)).length === 1 && out.length === 3, out);
check('pick: a single surviving headline is shown as none', pickLocal([GOOD[0]], { city: 'Los Angeles', now: NOW }).length === 0);
out = pickLocal([art('2026-11-10', 'x.com', 'A la carte dining returns'), art('2026-11-10', 'y.com', 'L.A. council votes'), art('2026-11-10', 'z.com', 'Budget passes')], { city: 'Los Angeles', now: NOW });
check('names: "L.A." names Los Angeles and "la" does not', out[0].title === 'L.A. council votes', out);
out = pickLocal([art('2026-11-09', 'a.org', 'Darigold faces threat of being shut down'), art('2026-11-09', 'b.org', 'Idaho judge orders release of police employment records')], { city: 'Boise', state: 'Idaho', now: NOW });
check('names: a headline that names the state comes first', out[0].title.startsWith('Idaho judge'), out);

const qy = localQuery('http://en.wikipedia.org/wiki/Boise,_Idaho', ['Boise'], new Date(NOW));
check('query: a real start date two days back, and no forceMaxDataTimeWindow', qy.dateStart === '2026-11-08' && !('forceMaxDataTimeWindow' in qy), qy);
check('query: outlets based in the place that name it, with no sports or entertainment', qy.sourceLocationUri[0].endsWith('Boise,_Idaho') && qy.keyword[0] === 'Boise' && !qy.locationUri && qy.ignoreCategoryUri.length === 2, qy);
console.log(fails ? fails + ' failed' : '0 failed');
process.exit(fails ? 1 : 0);
