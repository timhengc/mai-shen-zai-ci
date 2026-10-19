const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');
async function main(){
  const dir=path.resolve(process.argv[2]||'out/demo');
  const expected=JSON.parse(fs.readFileSync(path.join(dir,'identity.json'),'utf8'));
  const candidates=[process.env.CHROME_PATH,'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/usr/bin/google-chrome','/usr/bin/chromium'].filter(Boolean);
  const executablePath=candidates.find(p=>fs.existsSync(p));
  const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
  try{
    const errors=[],requests=[];
    let portraitSrc;
    const manifestDir=path.resolve(`assets/characters/${expected.gender}-v1`);
    const manifest=JSON.parse(fs.readFileSync(path.join(manifestDir,'manifest.json'),'utf8'));
    const original=fs.readFileSync(path.join(manifestDir,manifest.images.find(i=>i.level===expected.level).file));
    for(const kind of ['annual-report','identity-card','avatar']){
      for(const width of [375,720]){
        const page=await browser.newPage({viewport:{width,height:1080}});
        page.on('pageerror',e=>errors.push(e.message));
        page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
        await page.goto(pathToFileURL(path.join(dir,kind+'.html')).href+'?export=1');
        await page.waitForFunction(()=>window.reportReady);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
        const identity=page.locator('[data-identity-title]').filter({visible:true}).first();
        assert.equal(await identity.getAttribute('data-identity-title'),expected.title);
        assert.equal(await identity.getAttribute('data-identity-serial'),expected.serial);
        assert.equal(await page.locator('.controls').isVisible(),false);
        const portrait=page.locator('.character-image').filter({visible:true});
        assert.equal(await portrait.count(),1);
        assert.equal(await portrait.evaluate(img=>img.complete && img.naturalWidth>0),true);
        const src=await portrait.getAttribute('src');
        if(portraitSrc)assert.equal(src,portraitSrc,'三个功能应使用同一张人物图');
        portraitSrc=src;
        if(kind==='avatar'){
          const box=await page.locator('#report').boundingBox();
          assert.ok(Math.abs(box.width-box.height)<1,'头像应为正方形');
        }
        if(kind!=='annual-report')await page.locator('#report').screenshot({path:path.join(dir,kind+`-preview-${width}.png`)});
        await page.close();
      }
      const image=fs.readFileSync(path.join(dir,kind+'.png'));
      if(kind==='avatar')assert.deepEqual(image,original,'头像应直接输出原始人物图');
      else assert.equal(image.readUInt32BE(16),1080,'年报/名片 PNG 应为1080像素宽');
    }
    assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
    console.log('PASS: 三件套身份/纹章编号一致，375/720离线布局、同一预置人物、头像原图与静态导出。');
  }finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exit(1)});
