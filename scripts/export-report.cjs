// 一次性导出静态最终帧；页面本身不依赖 Playwright 或本地服务。
const { chromium } = require('playwright');
const { pathToFileURL } = require('node:url');
const fs = require('node:fs');
async function main() {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) throw new Error('Usage: node scripts/export-report.cjs input.html output.png');
  const candidates = [process.env.CHROME_PATH,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium'].filter(Boolean);
  const executablePath = candidates.find(p => fs.existsSync(p));
  const browser = await chromium.launch({ headless: true, ...(executablePath ? {executablePath} : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 720, height: 1080 }, deviceScaleFactor: 1.5, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto(pathToFileURL(input).href + '?export=1');
    await page.waitForFunction(() => window.reportReady === true);
    await page.evaluate(() => document.fonts.ready);
    await page.locator('#report').screenshot({ path: output, animations: 'disabled', timeout: 30000 });
    if (errors.length) throw new Error(errors.join('\n'));
    console.log(`PNG 已生成：${output}`);
  } finally { await browser.close(); }
}
main().catch(err => { console.error(err.message); process.exit(1); });
