const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const path=require('path'),assert=require('assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
try{const page=await browser.newPage({viewport:{width:1280,height:950},reducedMotion:'reduce'});await page.goto('file:///'+path.resolve(process.argv[2]).replaceAll('\\','/'));await page.evaluate(()=>document.fonts.ready);
for(const link of await page.locator('.masthead nav a').all()){await link.hover();await page.waitForTimeout(200);assert.equal(await link.evaluate(e=>getComputedStyle(e).color),'rgb(184, 50, 37)');}
for(const id of ['#copyQuote','#shareQuote','#exportMd']){
 const button=page.locator(id);if(!(await button.isVisible())){if(id==='#exportMd')await page.locator('.share-more-formats summary').click();}
 await button.scrollIntoViewIfNeeded();await page.mouse.move(0,0);await page.waitForTimeout(200);assert.equal(await button.evaluate(e=>getComputedStyle(e).color),'rgb(165, 75, 12)');
 await button.hover();await page.waitForTimeout(200);assert.equal(await button.evaluate(e=>getComputedStyle(e).color),'rgb(131, 59, 9)');
}
await page.locator('.masthead nav a[href="#quotes"]').click();await page.screenshot({path:'output/reading-2026-preview-20261113/action-colors.png'});
console.log('PASS: all top navigation hover states red; quote and export actions warm orange.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1);});
