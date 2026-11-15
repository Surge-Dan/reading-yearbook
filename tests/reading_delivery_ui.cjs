const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('assert/strict'),path=require('path');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
try{for(const [index,input]of process.argv.slice(2).entries()){
 const page=await browser.newPage({viewport:{width:1440,height:950},reducedMotion:'reduce'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file:///'+path.resolve(input).replaceAll('\\','/'));await page.evaluate(()=>document.fonts.ready);
 assert(await page.locator('#ebook').isVisible());assert.equal(await page.locator('#ebookShareToggle').count(),0);
 assert.equal(await page.locator('#ebook-reading-references').count(),0);assert.equal(await page.locator('.ebook-reading-nav summary').count(),0);
 if(index===0)assert.equal(await page.locator('.masthead').count(),1);else assert.equal(await page.locator('.masthead').count(),0);
 for(const width of [1440,900,600]){
  await page.setViewportSize({width,height:950});assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)));
  await page.locator('.ebook-reading-nav a').last().click();
  const bounds=await page.locator('.ebook-reading-nav').evaluate(e=>({top:e.getBoundingClientRect().top,position:getComputedStyle(e).position}));
  assert.equal(bounds.position,'sticky');assert(bounds.top>=0&&bounds.top<120);
 }
 assert.deepEqual(errors,[]);await page.close();console.log('PASS',index===0?'annual report':'standalone book','shared reader, navigation, widths and script execution');
}}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1);});
