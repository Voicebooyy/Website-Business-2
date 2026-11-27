// Prüft Verhalten der Demo: Start oben beim Neuladen, Reiter starten bei Frühstück, Galerie gleitet beim Reiterwechsel,
// Seite hinter dem Kontakt-Fenster ist gesperrt. Start: node tests/verhalten.test.js   (braucht Playwright)
const { chromium, devices } = require('playwright');
const U = 'file://' + require('path').join(__dirname, '../index.html');
(async () => {
  const b = await chromium.launch(); let bad = 0;
  const chk = (n, ok, extra = '') => { console.log(ok ? 'OK  ' : 'FAIL', n, extra); if (!ok) bad++; };
  for (const [n, o] of [['desktop', { viewport: { width: 1280, height: 800 } }], ['handy', devices['iPhone 13']]]) {
    const c = await b.newContext(o), p = await c.newPage(), errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.clock.setFixedTime(new Date('2026-12-03T15:30:00Z')); // nachmittags: trotzdem Frühstück zuerst
    await p.goto(U); await p.waitForTimeout(1200);
    chk(n + ': Reiter startet bei Frühstück', await p.$eval('[role=tab][aria-selected=true]', e => e.textContent) === 'Frühstück');
    await p.evaluate(() => scrollTo({ top: document.body.scrollHeight, behavior: 'instant' })); await p.waitForTimeout(400);
    await p.reload(); await p.waitForTimeout(1200);
    chk(n + ': Neuladen startet oben', await p.evaluate(() => scrollY) === 0);
    await p.goto('about:blank'); await p.goto(U + '#besuch'); await p.waitForTimeout(1200);
    chk(n + ': Aufruf mit #besuch startet oben', await p.evaluate(() => scrollY) === 0);
    await p.evaluate(() => document.querySelector('.tabs').scrollIntoView({ block: 'center', behavior: 'instant' })); await p.waitForTimeout(300);
    const top = () => p.evaluate(() => Math.round(document.querySelector('.gallery-sec').getBoundingClientRect().top + scrollY));
    const a = await top(); await p.click('#t-mittags');
    const s = []; for (let i = 0; i < 7; i++) { s.push(await top()); await p.waitForTimeout(90); }
    chk(n + ': Galerie gleitet statt zu springen', new Set(s).size >= 3 && s[s.length - 1] < a, `${a} → ${s.join(',')}`);
    await p.click('#t-kuchen'); await p.click('#t-kaltgetraenke'); await p.click('#t-fruehstueck'); await p.waitForTimeout(700);
    chk(n + ': schnelles Klicken räumt auf', await p.$eval('.panels', x => x.style.height === '' && !x.classList.contains('anim')));
    await p.evaluate(() => scrollTo({ top: 0, behavior: 'instant' })); await p.click('.demo-cta'); await p.waitForTimeout(400);
    await p.mouse.move(200, 300); await p.mouse.wheel(0, 800); await p.keyboard.press('PageDown'); await p.waitForTimeout(400);
    chk(n + ': Seite hinter Kontakt-Fenster gesperrt', await p.evaluate(() => scrollY) === 0);
    await p.keyboard.press('Escape'); await p.waitForTimeout(300);
    await p.mouse.wheel(0, 800); await p.waitForTimeout(400);
    chk(n + ': nach Schließen wieder scrollbar', await p.evaluate(() => scrollY) > 0);
    chk(n + ': keine Fehler', !errs.length, errs.join());
    await c.close();
  }
  console.log(bad ? bad + ' FEHLER' : 'alles ok'); await b.close(); process.exitCode = bad ? 1 : 0;
})();
