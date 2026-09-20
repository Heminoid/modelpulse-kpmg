const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: "new" });
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`PAGE ERROR: ${msg.text()}`);
    }
  });
  
  page.on('pageerror', err => {
    console.log(`UNCAUGHT ERROR: ${err.toString()}`);
  });

  const routes = ['/', '/portfolio', '/registry', '/datasets', '/monitors', '/runs', '/reports'];
  
  for (const route of routes) {
    console.log(`\nVisiting ${route}...`);
    try {
      await page.goto(`http://localhost:5173${route}`, { waitUntil: 'networkidle2', timeout: 5000 });
      // Look for React error overlay
      const hasErrorOverlay = await page.evaluate(() => {
        return !!document.querySelector('vite-error-overlay');
      });
      if (hasErrorOverlay) {
        console.log(`Found Vite Error Overlay on ${route}`);
      }
    } catch (e) {
      console.log(`Navigation to ${route} failed: ${e.message}`);
    }
  }

  await browser.close();
})();
