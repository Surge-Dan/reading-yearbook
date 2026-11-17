/* Run against a generated report; private data is never committed. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
(async()=>{
 const input=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]||'output/document-export-check');fs.mkdirSync(out,{recursive:true});
 const original=fs.readFileSync(input,'utf8'),pattern=/<script id="reading-data" type="application\/json">([\s\S]*?)<\/script>/;
 const base=JSON.parse(original.match(pattern)[1]);
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 try{for(const kind of ['actual','empty','long']){
 const data=structuredClone(base);
 if(kind==='empty'){data.books=[];data.distillations=[];data.summary={read:0,finished:0,read_days:0,notes:0,seconds:0,monthly:[]};}
 if(kind==='long'){data.books=data.books.slice(0,1);data.books[0].title='长书名与特殊字符 | <script>不可执行</script> '+ '阅读与思考'.repeat(16);data.books[0].highlights=[{text:'完整长段落。'.repeat(1200),source_id:'PRIVATE-SOURCE-ID',chapter_title:'长章节标题'}];data.books[0].thoughts=[{text:'个人想法与摘录需要分开。'.repeat(150),created_at:'2026-01-01'}];data.distillations=[];}
 const html=original.replace(pattern,()=>'<script id="reading-data" type="application/json">'+JSON.stringify(data).replace(/</g,'\\u003c')+'</script>');
 const target=path.join(out,kind+'.html');fs.writeFileSync(target,html);
 const context=await browser.newContext({acceptDownloads:true,viewport:{width:1280,height:960}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('file:///'+target.replaceAll('\\','/'));await page.locator('#exportMd').waitFor({state:'attached'});
 assert.equal(await page.locator('#exportJson').count(),0);
 await page.locator('.share-more-formats summary').click();
 // A screen filter must not silently truncate the document.
 if(await page.locator('#search').isVisible())await page.locator('#search').fill('no matching title');
 const pending=page.waitForEvent('download');await page.locator('#exportMd').click();const download=await pending;const md=path.join(out,kind+'.md');await download.saveAs(md);
 const text=fs.readFileSync(md,'utf8');assert(!text.includes('来源：'));assert(!text.includes('PRIVATE-SOURCE-ID'));assert(text.includes('| 读过 | 读完 |'));
 for(const b of data.books)if(b.source_id)assert(!text.includes(b.source_id));
 assert.equal(await page.locator('#printDetails').innerText(),'');
 await page.pdf({path:path.join(out,kind+'.pdf'),printBackground:true,preferCSSPageSize:true});
 await page.emulateMedia({media:'print'});await page.evaluate(()=>dispatchEvent(new Event('beforeprint')));
 assert.equal(await page.locator('#printDetails .print-book').count(),data.books.filter(b=>b.highlights?.length||b.thoughts?.length).length+(data.distillations||[]).length);
 assert(!/来源：|PRIVATE-SOURCE-ID/.test(await page.locator('#printDetails').innerText()));
 await page.screenshot({path:path.join(out,kind+'-cover.png')});
 await page.evaluate(()=>dispatchEvent(new Event('afterprint')));assert.equal(await page.locator('#printDetails').innerText(),'');assert.deepEqual(errors,[]);
 await context.close();console.log('PASS',kind,'Markdown, PDF, content scope, escaping and cleanup');
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});

