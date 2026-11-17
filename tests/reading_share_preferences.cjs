const {chromium}=require('playwright'),assert=require('assert'),path=require('path'),{pathToFileURL}=require('url');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXECUTABLE}),context=await browser.newContext({acceptDownloads:true});
 await context.setOffline(true);const page=await context.newPage(),errors=[],requests=[],folder=process.argv[2];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
 const goto=async name=>{await page.goto(pathToFileURL(path.join(folder,name+'.html')).href);await page.waitForFunction(()=>document.querySelector('#previewTitle').textContent);};
 const stored=()=>page.evaluate(()=>JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.startsWith('reading-yearbook:share:v1:')))));
 const selected=()=>page.locator('[data-page]:checked').count();
 const books=async()=>{if(await page.locator('#bookShareMenu').isHidden())await page.locator('#bookShareTrigger').click();};
 await goto('initial');assert.equal(await selected(),6);let saved=await stored();assert.equal(saved.materials['book-one'].id,'complete');
 // Explicit personal note wins over default highlights, without leaking text into preferences.
 await page.locator('[data-open-book="one"]').first().click();await page.locator('[data-add-note="one"]').click();await page.keyboard.press('Escape');
 await page.locator('#ratio').selectOption('1:1',{force:true});await books();await page.locator('[data-page="book-two"]').uncheck();await page.keyboard.press('Escape');
 saved=await stored();assert.equal(saved.materials['book-one'].kind,'thought');assert.equal(saved.materials['book-one'].id,'personal');assert(!JSON.stringify(saved).includes('真实想法'));
 await page.reload();await page.waitForFunction(()=>document.querySelector('#previewTitle').textContent==='选择测试');assert.equal(await selected(),5);assert.equal(await page.locator('#ratio').inputValue(),'1:1');assert.equal(await page.locator('[data-share-ratio="1:1"]').getAttribute('aria-pressed'),'true');
 await goto('updated');assert.equal(await selected(),5);assert.equal((await stored()).materials['book-one'].id,'personal');assert(!(await page.locator('[data-page="book-three"]').isChecked()));
 await goto('changed');assert.equal((await stored()).materials['book-one'].id,'complete');assert((await page.locator('#exportStatus').textContent()).includes('原选句已变更'));
 await goto('removed');assert.equal(await selected(),4);assert.equal(await page.locator('#previewTitle').textContent(),'封面');
 await goto('other');assert.equal(await selected(),6);assert.equal(await page.locator('#ratio').inputValue(),'3:4');
 await goto('year');assert.equal(await selected(),6);assert.equal(await page.locator('#ratio').inputValue(),'3:4');
 // Start with a clean context for update defaults and explicit empty selections.
 await page.evaluate(()=>localStorage.clear());await goto('initial');await goto('updated');assert.equal(await selected(),7);
 await page.evaluate(()=>document.querySelectorAll('[data-page]').forEach(el=>{if(el.checked){el.checked=false;el.dispatchEvent(new Event('change'));}}));
 assert.equal(await selected(),0);await page.reload();assert.equal(await selected(),0);assert(await page.locator('#exportGroup').isDisabled());assert(!(await page.locator('#exportOne').isDisabled()));
 await books();await page.locator('[data-page="book-one"]').check();await page.keyboard.press('Escape');await page.locator('#undoSelection').click();await page.reload();assert.equal(await selected(),0);
 // Malformed JSON and storage failures are recoverable, with working exports.
 await page.evaluate(()=>localStorage.setItem(Object.keys(localStorage).find(k=>k.includes('a'.repeat(32))&&k.endsWith('2026')),'{broken'));
 await goto('initial');assert.equal(await selected(),6);
 const blocked=await context.newPage();await blocked.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError');}}));
 await blocked.goto(pathToFileURL(path.join(folder,'initial.html')).href);await blocked.waitForFunction(()=>document.querySelector('#previewTitle').textContent);
 assert.equal(await blocked.locator('[data-page]:checked').count(),6);const [download]=await Promise.all([blocked.waitForEvent('download'),blocked.locator('#exportOne').click()]);assert(download.suggestedFilename().endsWith('.png'));
 const quota=await context.newPage();await quota.addInitScript(()=>Storage.prototype.setItem=function(){throw new DOMException('quota','QuotaExceededError');});
 await quota.goto(pathToFileURL(path.join(folder,'initial.html')).href);await quota.waitForFunction(()=>document.querySelector('#previewTitle').textContent);assert((await quota.locator('#exportStatus').textContent()).includes('仍可正常导出'));
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);await browser.close();console.log('PASS: defaults, material ranking, explicit notes, reload, updates, deleted/changed materials, account/year isolation, all/none, undo, corrupt/blocked/quota storage and offline PNG.');
})().catch(e=>{console.error(e);process.exit(1);});
