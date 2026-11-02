// Opens every page in headless Chrome and fails on console errors, CSP violations,
// uncaught exceptions or failed requests. usage: node console_check.js BASE_URL
const { chromium } = require('playwright-core');
const base = process.argv[2].replace(/\/$/, '');
const pages = ['/', '/en/', '/galleria.html', '/en/gallery.html', '/configura.html', '/en/configure.html', '/contatti.html', '/en/contact.html'];
(async () => {
  const browser = await chromium.launch({ channel: process.env.CHROME_PATH ? undefined : 'chrome', executablePath: process.env.CHROME_PATH, args: ['--no-sandbox'] });
  let fail = 0;
  for (const p of pages) {
    const page = await browser.newPage();
    const errs = [];
    page.on('console', m => { if (m.type() === 'error' || /content security policy/i.test(m.text())) errs.push('console: ' + m.text()); });
    page.on('pageerror', e => errs.push('exception: ' + e.message));
    page.on('requestfailed', r => errs.push('request failed: ' + r.url() + ' ' + (r.failure() || {}).errorText));
    page.on('response', r => { if (r.status() >= 400) errs.push('HTTP ' + r.status() + ' ' + r.url()); });
    await page.goto(base + p, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1500);
    if (errs.length) { fail = 1; errs.forEach(e => console.log(`::error::${p} ${e}`)); } else console.log(`ok:   ${p} clean console`);
    await page.close();
  }
  await browser.close();
  process.exit(fail);
})();
