const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 try{
 const input=path.resolve(process.argv[2]||'');assert(process.argv[2],'Pass a generated report HTML path');
 const fixture=JSON.parse(fs.readFileSync(input,'utf8').match(/<script id="reading-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
 const expected=fixture.distillations[0].analysis;
 const context=await browser.newContext({acceptDownloads:true,viewport:{width:1440,height:1000}});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.copiedText='';Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>window.copiedText=text},configurable:true});});
 await page.goto('file:///'+input.replaceAll('\\','/'));
 await page.locator('#ebookBookTitle').waitFor();
 assert.equal(await page.locator('#ebookTitle').innerText(),'蒸馏一本书');
 assert.equal(await page.locator('#ebookShareToggle').count(),0);
 assert.equal(await page.locator('#ebook-reading-references').count(),0);
 assert.equal(await page.locator('.ebook-reading-nav summary').count(),0);
 await page.locator('[data-ebook-copy]').first().click();
 assert(!/基于所提供正文/.test(await page.evaluate(()=>window.copiedText)));
 await page.locator('#ebookCopyAll').click();assert(!/基于所提供正文/.test(await page.evaluate(()=>window.copiedText)));
 let pending=page.waitForEvent('download');await page.locator('#ebookDownloadMd').click();let download=await pending;
 assert(!/基于所提供正文|## 参考资料/.test(fs.readFileSync(await download.path(),'utf8')));
 pending=page.waitForEvent('download');await page.locator('#ebookDownloadHtml').click();download=await pending;
 const target=path.join(fs.mkdtempSync(path.join(require('os').tmpdir(),'reader-delivery-')),'standalone.html');await download.saveAs(target);
 const standalone=await context.newPage();standalone.on('pageerror',e=>errors.push(e.message));await standalone.goto('file:///'+target.replaceAll('\\','/'));
 assert.equal(await standalone.locator('#ebookBookTitle').innerText(),expected.book.title);
 assert.equal(await standalone.locator('.distill-theme-grid article').count(),expected.themes.length);
 assert.equal(await standalone.locator('.ebook-reading-nav summary').count(),0);
 await standalone.locator('.ebook-reading-nav a').last().click();await standalone.waitForTimeout(400);
 assert(await standalone.locator('.ebook-reading-nav').evaluate(e=>e.getBoundingClientRect().top>=0&&e.getBoundingClientRect().top<5));
 for(const width of [1440,900,600]){await standalone.setViewportSize({width,height:900});assert(!(await standalone.evaluate(()=>document.documentElement.scrollWidth>innerWidth)));}
 assert.deepEqual(errors,[]);await page.locator('a[href="#ebook"]').first().click();
 console.log('PASS: copy, Markdown, standalone export, sticky navigation, 3 widths, no script errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});

