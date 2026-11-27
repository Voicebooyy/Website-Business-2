// Prüft Türschild, Urlaubshinweis und Events der Demo (Mittagspause, nach Mitternacht, Feiertage, Zeitzone).
// Start im Ordner dieses Repos: node tests/tuerschild.test.js   (braucht Playwright)
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const MITTAG = [['<td>8:00 – 18:00</td>', '<td>8:00 – 12:00, 14:00 – 18:00</td>']];
const NACHT = [['<td>9:00 – 18:00</td>', '<td>17:00 – 1:00</td>']];
// [UTC-Zeit, Ersetzungen, Schild, sichtbare Events, Hinweis sichtbar]
const cases = [
  ['2026-11-27T09:00:00Z', [], 'Geöffnet|bis 18:00'],                       // Fr 10:00
  ['2026-11-30T09:00:00Z', [], 'Geschlossen|morgen ab 8:00'],               // Mo Ruhetag
  ['2026-12-01T06:00:00Z', [], 'Geschlossen|öffnet heute um 8:00'],         // Di 7:00
  ['2026-12-01T18:30:00Z', [], 'Geschlossen|morgen ab 8:00'],               // Di 19:30
  ['2026-12-01T12:00:00Z', MITTAG, 'Geschlossen|öffnet wieder um 14:00'],   // Mittagspause
  ['2026-12-01T13:30:00Z', MITTAG, 'Geöffnet|bis 18:00'],
  ['2026-11-28T20:00:00Z', NACHT, 'Geöffnet|bis 1:00'],                     // Sa 21:00
  ['2026-11-28T23:30:00Z', NACHT, 'Geöffnet|bis 1:00'],                     // So 0:30, noch offen von Sa
  ['2026-11-29T00:30:00Z', NACHT, 'Geschlossen|öffnet heute um 17:00'],     // So 1:30
  ['2026-12-25T09:00:00Z', [], 'Geschlossen|Sonntag ab 9:00'],              // Schließtag
  ['2026-12-03T10:00:00Z', [], 'Geöffnet|bis 18:00', 4, true],              // Events + Hinweis noch da
  ['2026-12-08T10:00:00Z', [], 'Geöffnet|bis 18:00', 3, true],              // Adventsbrunch (6.12.) weg
  ['2027-01-02T10:00:00Z', [], 'Geöffnet|bis 18:00', 1, false],             // nur wöchentliche Musik, Hinweis weg
];
(async () => {
  const b = await chromium.launch(); let fail = 0;
  for (const tz of ['Europe/Berlin', 'America/New_York', 'Asia/Tokyo']) {
    for (const [t, rep, exp, ev, hinweis] of cases) {
      const ctx = await b.newContext({ timezoneId: tz }), p = await ctx.newPage(), errs = [];
      p.on('pageerror', e => errs.push(e.message));
      await p.clock.setFixedTime(new Date(t));
      let h = src; for (const [a, c] of rep) { if (!h.includes(a)) throw new Error('Testvorlage passt nicht: ' + a); h = h.replace(a, c); }
      await p.route('http://x/**', r => r.request().url() === 'http://x/' ? r.fulfill({ body: h, contentType: 'text/html' }) : r.abort());
      await p.goto('http://x/');
      const got = (await p.textContent('#status .s1')).trim() + '|' + (await p.textContent('#status .s2')).trim();
      const n = await p.$$eval('.events li', a => a.filter(x => !x.hidden).length);
      const hv = await p.isVisible('.notice');
      const ok = got === exp && (ev === undefined || n === ev) && (hinweis === undefined || hv === hinweis) && !errs.length;
      if (!ok) fail++;
      console.log(ok ? 'OK  ' : 'FAIL', tz.padEnd(17), t, got, ev === undefined ? '' : `| Events ${n} Hinweis ${hv}`, errs.join(' '));
      await ctx.close();
    }
  }
  console.log(fail ? fail + ' FEHLER' : 'alles ok'); await b.close(); process.exitCode = fail ? 1 : 0;
})();
