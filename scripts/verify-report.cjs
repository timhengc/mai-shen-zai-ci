// 以 file:// 验证离线页面、移动布局、播放控制和静态导出。
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
async function main() {
  const input = path.resolve(process.argv[2] || 'out/demo/annual-report.html');
  const candidates = [process.env.CHROME_PATH, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium'].filter(Boolean);
  const executablePath = candidates.find(p => fs.existsSync(p));
  const browser = await chromium.launch({headless:true,...(executablePath ? {executablePath} : {})});
  try {
    const errors=[],requests=[];
    for (const width of [375,720,1280]) {
      const page=await browser.newPage({viewport:{width,height:900}});
      page.on('pageerror',e=>errors.push(e.message));
      page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
      await page.goto(pathToFileURL(input).href);
      await page.waitForFunction(()=>window.reportReady);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`width ${width} overflow`);
      assert.equal(await page.locator('.month').count(),12);
      assert.equal(await page.locator('.hour-bar').count(),24);
      await page.locator('#play').click();
      await page.waitForTimeout(350);
      assert.ok(await page.evaluate(()=>scrollY>0),'自动播放应推进滚动');
      await page.locator('#pause').click();
      const frozen=await page.evaluate(()=>scrollY);
      await page.waitForTimeout(150);
      assert.equal(await page.evaluate(()=>scrollY),frozen,'暂停应停止自动滚动');
      assert.equal(await page.locator('#pause').getAttribute('aria-pressed'),'true');
      await page.locator('#replay').click();
      await page.waitForTimeout(800);
      assert.equal(await page.evaluate(()=>scrollY),0,'重看回到开头');
      await page.evaluate(()=>document.querySelector('#finale').scrollIntoView());
      await page.waitForFunction(()=>getComputedStyle(document.querySelector('#finale .reveal')).opacity==='1');
      assert.equal(await page.locator('#finale .reveal').evaluate(e=>getComputedStyle(e).opacity),'1');
      await page.screenshot({path:path.join(path.dirname(input),`preview-${width}.png`)});
      await page.close();
    }
    const reduced=await browser.newPage({reducedMotion:'reduce',viewport:{width:375,height:900}});
    await reduced.goto(pathToFileURL(input).href);
    await reduced.waitForFunction(()=>window.reportReady);
    assert.equal(await reduced.locator('.reveal').first().evaluate(e=>getComputedStyle(e).opacity),'1');
    const staticPage=await browser.newPage({viewport:{width:720,height:1080}});
    await staticPage.goto(pathToFileURL(input).href+'?export=1');
    await staticPage.waitForFunction(()=>window.reportReady);
    assert.equal(await staticPage.locator('.controls').isVisible(),false);
    assert.equal(await staticPage.locator('.reveal:not(.visible)').count(),0);
    await staticPage.screenshot({path:path.join(path.dirname(input),'cover-preview.png')});
    assert.deepEqual(errors,[]);assert.deepEqual(requests,[],'离线页面不应发起网络请求');
    console.log('PASS: file:// 离线、375/720/1280 布局、播放/暂停/重看、滚动揭幕、减少动态效果、完整静态帧。');
  } finally { await browser.close(); }
}
main().catch(e=>{console.error(e);process.exit(1)});
