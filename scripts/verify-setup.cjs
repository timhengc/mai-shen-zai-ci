const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
async function main(){
 const file=path.resolve(process.argv[2]||'out/setup/index.html');
 const candidates=[process.env.CHROME_PATH,'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/usr/bin/google-chrome','/usr/bin/chromium'].filter(Boolean);
 const executablePath=candidates.find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
 try{
  const errors=[],requests=[];
  for(const width of [375,1020]){
   const page=await browser.newPage({viewport:{width,height:1100},acceptDownloads:true});
   page.on('pageerror',e=>errors.push(e.message));
   page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
   await page.goto(pathToFileURL(file).href);
   await page.waitForFunction(()=>window.reportReady&&[...document.images].every(i=>i.complete&&i.naturalWidth>0));
   assert.equal(await page.locator('#official-link').getAttribute('href'),'https://open.mcd.cn/mcp');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   assert.equal(await page.locator('#token').getAttribute('type'),'password');
   const token='download-test-token';
   await page.locator('#token').fill(token);
   const pending=page.waitForEvent('download');
   await page.locator('#save').click();
   const download=await pending;
   assert.equal(download.suggestedFilename(),'mcd-token.env');
   assert.equal(fs.readFileSync(await download.path(),'utf8'),'MCD_MCP_TOKEN='+token+'\n');
   assert.equal(await page.locator('#token').inputValue(),'');
   assert.equal((await page.content()).includes(token),false);
   assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
   await page.locator('#token').fill('token with spaces');
   await page.locator('#save').click();
   assert.ok((await page.locator('#status').textContent()).includes('单行 Token'));
   await page.evaluate(()=>scrollTo(0,0));
   await page.screenshot({path:path.join(path.dirname(file),`setup-preview-${width}.png`)});
   await page.close();
  }
  assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
  console.log('PASS: 首次连接页离线打开、双图显示、手机/桌面布局、官方链接、本地配置下载和无网络传输。');
 }finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exit(1)});
